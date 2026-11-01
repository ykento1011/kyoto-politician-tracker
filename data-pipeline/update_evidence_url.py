import os
import sys
import re
import json
import time
import argparse
import urllib.parse
from datetime import datetime
from urllib.parse import urlparse
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
FRONTEND_DATA_DIR = os.path.join(PROJECT_ROOT, "frontend", "public", "data")
ENV_FILE = os.path.join(BASE_DIR, ".env")
ROOT_ENV_FILE = os.path.join(PROJECT_ROOT, ".env")
QUEUE_FILE = os.path.join(BASE_DIR, "data", "evidence_health_queue.json")

USER_AGENT = "GikaiNoMikata-EvidenceAgent/1.0 (+https://gikai-mikata.jp)"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 自治体正規公式ドメインホワイトリスト（Rule 3）
CITY_DOMAINS = {
    "kyoto": ["city.kyoto.lg.jp"],
    "osaka": ["city.osaka.lg.jp", "pref.osaka.lg.jp"],
    "nagoya": ["city.nagoya.jp", "nagoyajo.city.nagoya.jp", "kodomo-ouen.city.nagoya.jp"],
    "yokohama": ["city.yokohama.lg.jp"],
    "kobe": ["city.kobe.lg.jp"]
}

# 包括資料トークン除外リスト（Rule 2）
COMPREHENSIVE_TOKENS = [
    "hakusyo", "whitepaper", "all.pdf", "honbun.pdf",
    "keikaku_zenpen", "zenpen.pdf", "annual_report", "annual-report",
    "sougou_keikaku_all", "kessan_all", "gaiyo_all"
]

COMPREHENSIVE_TITLE_TOKENS = [
    "白書", "全編", "一括ダウンロード", "全体版", "本編一括", "年報", "包括版"
]

STOP_WORDS = {
    "推進", "向上", "強化", "充実", "実現", "導入", "挑戦", "早期", "完全",
    "および", "に向けた", "について", "による", "活用", "拡充", "促進",
    "支援", "育成", "対策", "創出", "検討", "見直し", "整備", "改修",
    "づくり", "つくります", "します", "ます", "等", "への", "から", "まで",
    "令和", "年度", "事業", "方針", "計画", "実施", "方式", "拡大", "上限",
    "引き上げ", "引上げ", "世帯", "制度", "関係", "対応", "京都", "大阪", "名古屋", "横浜", "神戸"
}

def load_api_key():
    for fpath in [ENV_FILE, ROOT_ENV_FILE]:
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val
            except Exception:
                pass
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

def extract_core_entities(headline):
    blocks = re.findall(r'[一-龥]{2,}|[ァ-ヶー]{2,}', headline)
    words = set()
    for b in blocks:
        if b not in STOP_WORDS:
            words.add(b)
        for n in [4, 3, 2]:
            if len(b) >= n:
                for i in range(len(b) - n + 1):
                    sub = b[i:i+n]
                    if sub not in STOP_WORDS:
                        words.add(sub)
    return sorted(list(words), key=lambda x: len(x), reverse=True)

def resolve_redirect_url(url):
    """Google Grounding のリダイレクトURL (vertexaisearch) を実URLに解決"""
    if "vertexaisearch.cloud.google.com" in url or "google.com/url" in url:
        try:
            r = requests.head(url, headers={"User-Agent": USER_AGENT}, timeout=(3.0, 5.0), allow_redirects=True, verify=False)
            if r.url and "vertexaisearch" not in r.url and "google.com" not in r.url:
                return r.url
        except Exception:
            pass
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=(3.0, 5.0), allow_redirects=True, stream=True, verify=False)
            if r.url and "vertexaisearch" not in r.url and "google.com" not in r.url:
                r.close()
                return r.url
        except Exception:
            pass
    return url

# =========================================================================
# 4重 Fail-Closed バリデータ
# =========================================================================
def validate_candidate_url(url, city, headline, title="", check_entity=True, mock_content=None):
    # Rule 3: 公式ドメイン完全一致検証
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    allowed_domains = CITY_DOMAINS.get(city, [])
    is_domain_ok = any(hostname == d or hostname.endswith("." + d) for d in allowed_domains)
    if not is_domain_ok:
        return False, "RULE3_FAIL", f"ドメイン不一致: '{hostname}' は {city} の公式ドメインではありません"

    # Rule 1: ルート／浅い階層の遮断（トップページ逃げ完全防止）
    path = parsed.path.strip("/")
    if not path:
        return False, "RULE1_FAIL", f"トップページ（ルートURL）のため破棄: {url}"
    parts = [p for p in path.split("/") if p]
    if len(parts) <= 1:
        return False, "RULE1_FAIL", f"パス深度が浅すぎるため破棄 (depth={len(parts)}): /{path}"
    
    last = parts[-1].lower()
    if last in ["index.html", "index.htm", "default.html", "default.htm"] and len(parts) <= 2:
        return False, "RULE1_FAIL", f"個別記事IDのない局・部トップページのため破棄: /{path}"
    if url.endswith("/") and len(parts) <= 2:
        return False, "RULE1_FAIL", f"個別記事IDのないディレクトリトップのため破棄: /{path}"

    # Rule 2: 包括資料キーワード除外（白書・全編PDF破棄）
    url_lower = url.lower()
    for tok in COMPREHENSIVE_TOKENS:
        if tok in url_lower:
            return False, "RULE2_FAIL", f"包括資料トークン '{tok}' を検知したため破棄: {url}"
    for tt in COMPREHENSIVE_TITLE_TOKENS:
        if tt in title:
            return False, "RULE2_FAIL", f"包括資料タイトル '{tt}' を検知したため破棄: {title}"

    # Rule 4: 本文エンティティ照合（コア固有名詞が2回以上出現するか）
    if check_entity:
        entities = extract_core_entities(headline)
        if entities:
            content_text = ""
            if mock_content is not None:
                content_text = mock_content
            else:
                try:
                    resp = requests.get(url, headers=HEADERS, timeout=(5.0, 8.0), verify=False)
                    if resp.status_code >= 400:
                        return False, "RULE4_FAIL", f"候補URLアクセスエラー (HTTP {resp.status_code})"
                    
                    # 文字化け対策: UTF-8 -> apparent_encoding でデコード
                    try:
                        content_text = resp.content.decode("utf-8")
                    except UnicodeDecodeError:
                        enc = resp.apparent_encoding or "cp932"
                        content_text = resp.content.decode(enc, errors="ignore")
                except Exception as e:
                    return False, "RULE4_FAIL", f"本文検証通信失敗: {e}"

            total_hits = 0
            hit_terms = []
            for ent in entities:
                hits = content_text.count(ent)
                if hits > 0:
                    total_hits += hits
                    hit_terms.append(f"{ent}({hits})")

            if total_hits < 2:
                return False, "RULE4_FAIL", f"本文エンティティ出現数不足 (合計 {total_hits}回): 探索キー {entities[:5]}"

    return True, "PASS", "4重バリデーション完全合格"

# =========================================================================
# Gemini Search Grounding による候補探索
# =========================================================================
def search_replacement_url(city, headline, field, current_url):
    api_key = load_api_key()
    primary_domain = CITY_DOMAINS.get(city, ["lg.jp"])[0]

    entities = extract_core_entities(headline)
    main_keyword = entities[0] if entities else headline[:10]
    sub_keyword = entities[1] if len(entities) > 1 else ""
    
    prompt = f"""あなたは自治体政策トラッカーの厳密なデータ監査官です。
以下の自治体（{city}）の施策について、一般市民が1クリックで施策の事実・制度内容を確認できる【単体公式Webページ（HTML）】または単体発表資料を1件特定してください。

自治体: {city}
施策名: {headline}
失効中URL: {current_url}
対象フィールド: {field}

【厳守事項】
- 必ず site:{primary_domain} 内の実在するURLを提示してください。
- 自治体のトップページ、局のトップページ（例: .../index.html）、大部な白書（hakusyo）、包括計画PDFは【採択厳禁】です。
- 見つからない場合は「NOT_FOUND」と答えてください。
- 該当する公式単体ページのURLとタイトルを回答してください。"""

    candidates = []

    if api_key:
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "tools": [{"google_search": {}}]
                }
                res = requests.post(endpoint, json=payload, timeout=40)
                if res.status_code == 200:
                    data = res.json()
                    cand = data.get("candidates", [{}])[0]
                    
                    # 1. Grounding Metadata からのURL抽出
                    chunks = cand.get("groundingMetadata", {}).get("groundingChunks", [])
                    for ch in chunks:
                        web = ch.get("web", {})
                        if web.get("uri"):
                            candidates.append({"url": web["uri"], "title": web.get("title", ""), "source": "grounding"})
                            
                    # 2. 生成テキスト内のURL抽出
                    for part in cand.get("content", {}).get("parts", []):
                        text_content = part.get("text", "")
                        found_urls = re.findall(r"https?://[^\s\)\"\'<>]+", text_content)
                        for u in found_urls:
                            candidates.append({"url": u, "title": "", "source": "text"})
                    break
            except Exception as e:
                if attempt == 0:
                    time.sleep(2)
                    continue
                print(f"⚠️ Gemini API呼び出し警告: {e}")

    unique_candidates = []
    seen = set()
    for c in candidates:
        raw_u = c["url"]
        real_u = resolve_redirect_url(raw_u).rstrip("/")
        if real_u not in seen:
            seen.add(real_u)
            unique_candidates.append({**c, "url": real_u})

    return unique_candidates

def process_item(item, dry_run=False):
    city = item.get("city", "kyoto")
    hl = item.get("headline", "—")
    field = item.get("field", "doc_url")
    cur_url = item.get("url", "")

    print(f"\n🔍 探索実行: [{city.upper()}] {hl[:28]}...")
    print(f"   失効URL: {cur_url} ({field})")

    candidates = search_replacement_url(city, hl, field, cur_url)
    if not candidates:
        print("   ❌ 候補URLが特定できませんでした (NOT_FOUND)")
        item["agent_status"] = "MANUAL_REVIEW_REQUIRED"
        item["agent_note"] = "Gemini Search で該当候補なし"
        return False, None

    print(f"   📋 探索候補検出: {len(candidates)} 件")
    
    for cand in candidates:
        c_url = cand["url"]
        c_title = cand.get("title", "")
        print(f"   🧪 バリデータ検証中: {c_url}")
        
        ok, rule, reason = validate_candidate_url(c_url, city, hl, title=c_title, check_entity=True)
        if ok:
            print(f"   ✅ 【4重バリデータ合格】: {c_url}")
            print(f"      判定: {reason}")
            item["agent_status"] = "AUTO_FIX_CANDIDATE"
            item["new_url"] = c_url
            item["new_title"] = c_title
            item["verified_at"] = datetime.now().isoformat()
            return True, c_url
        else:
            print(f"   🛡️ 【Fail-Closed 破棄 ({rule})】: {reason}")

    item["agent_status"] = "MANUAL_REVIEW_REQUIRED"
    item["agent_note"] = "全候補がFail-Closedバリデータで遮断されました"
    return False, None

def run_defense_test():
    print("=" * 75)
    print(" 🛡️ 4重 Fail-Closed 防御テスト（悪質・曖昧URLの遮断検証）")
    print("=" * 75)
    
    test_cases = [
        ("Rule 1: ルート遮断", "https://www.city.kyoto.lg.jp/", "kyoto", "宿泊税", "京都市公式", True, None),
        ("Rule 1: 浅い局トップ遮断", "https://www.city.kyoto.lg.jp/kotsu/", "kyoto", "市バス", "交通局", True, None),
        ("Rule 1: ID無index遮断", "https://www.city.kyoto.lg.jp/kotsu/index.html", "kyoto", "市バス", "交通局", True, None),
        ("Rule 2: 白書PDF除外", "https://www.city.kyoto.lg.jp/kotsu/cmsfiles/contents/0000073/73257/hakusyo06.pdf", "kyoto", "市バス", "交通局白書", True, None),
        ("Rule 2: 全編PDF除外", "https://www.city.yokohama.lg.jp/city-info/keikaku_zenpen.pdf", "yokohama", "防災", "横浜市計画全編", True, None),
        ("Rule 3: 外部ニュース除外", "https://news.yahoo.co.jp/articles/12345678", "kyoto", "宿泊税", "Yahooニュース", True, None),
        ("Rule 4: 無関係ページ除外", "https://www.city.kyoto.lg.jp/bunshi/page/0000001234.html", "kyoto", "市バス等の市民優先価格", "文化市民局のおしらせ", True, "こちらは伝統文化財保護に関するページです。仏像修復や指定に関するお知らせを掲載しています。")
    ]

    passed_count = 0
    for name, url, city, hl, title, check_ent, mock_text in test_cases:
        ok, rule, reason = validate_candidate_url(url, city, hl, title=title, check_entity=check_ent, mock_content=mock_text)
        if not ok:
            print(f" ✅ PASS [{name}] -> 正常に遮断されました: {rule} ({reason})")
            passed_count += 1
        else:
            print(f" ❌ FAIL [{name}] -> 遮断をすり抜けました！ ({url})")

    print("-" * 75)
    print(f" 🛡️ 防御テスト結果: {passed_count} / {len(test_cases)} 遮断成功")
    print("=" * 75)
    return passed_count == len(test_cases)

def main():
    parser = argparse.ArgumentParser(description="一次公文書エビデンス自律探索エージェント")
    parser.add_argument("--city", help="都市コード")
    parser.add_argument("--pledge_id", help="施策ID")
    parser.add_argument("--field", help="対象フィールド名")
    parser.add_argument("--from-queue", help="要調査キューJSONファイルパス")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（結果を保存しない）")
    parser.add_argument("--test-defense", action="store_true", help="4重Fail-Closed防御テストを実行")
    args = parser.parse_args()

    if args.test_defense:
        success = run_defense_test()
        sys.exit(0 if success else 1)

    if args.from_queue:
        q_path = args.from_queue
        if not os.path.exists(q_path):
            print(f"❌ キューファイルが存在しません: {q_path}")
            sys.exit(1)
            
        with open(q_path, "r", encoding="utf-8") as f:
            queue_items = json.load(f)

        print(f"📋 要調査キューから {len(queue_items)} 件を読み込みました。")
        success_count = 0
        
        # 実データ検証（先頭3件をサンプリング実行）
        for item in queue_items[:3]:
            ok, new_url = process_item(item, dry_run=args.dry_run)
            if ok:
                success_count += 1

        print("\n" + "=" * 75)
        print(f" 🏁 キュー検証サマリー: 3件中 {success_count} 件で新公式ページを安全に特定")
        print("=" * 75)

        if not args.dry_run:
            with open(q_path, "w", encoding="utf-8") as f:
                json.dump(queue_items, f, ensure_ascii=False, indent=2)
            print(f"📝 キューの状態を更新しました: {q_path}")
            
        sys.exit(0)

    elif args.city and args.field:
        item = {
            "city": args.city,
            "pledge_id": args.pledge_id or "1",
            "headline": f"{args.city}の施策",
            "field": args.field,
            "url": "https://example.com/404"
        }
        process_item(item, dry_run=args.dry_run)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
