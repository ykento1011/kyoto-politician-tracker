import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist" / "data"

PLEDGES_EXTRACTED = BASE_DIR / "data" / "nagoya_councilor_pledges.json"
STATEMENTS_FILE = FRONTEND_DATA / "nagoya_statements_summary.json"

OUTPUT_FILES = [
    FRONTEND_DATA / "pledge_tracker_nagoya.json",
    FRONTEND_DIST / "pledge_tracker_nagoya.json"
]

# 名古屋市議会の看板公約に特化した厳格な照合ルール（京都版TOPIC_RULES準拠）
NAGOYA_TOPIC_RULES = {
    "市民税減税": {
        "positive": ["市民税減税", "5%減税", "減税", "恒久減税", "減税効果"],
        "negative": []
    },
    "名古屋城天守閣木造復元": {
        "positive": ["名古屋城", "天守閣", "木造復元", "木造化", "バリアフリー", "エレベーター設置"],
        "negative": []
    },
    "敬老パス": {
        "positive": ["敬老パス", "利用回数", "上限回数", "名鉄", "JR", "近鉄", "敬老乗車証"],
        "negative": []
    },
    "学校給食無償化": {
        "positive": ["学校給食", "給食費無償化", "給食無償", "給食費", "オーガニック給食", "完全給食"],
        "negative": []
    },
    "議員報酬・身を切る改革": {
        "positive": ["議員報酬", "800万円", "政務活動費", "身を切る改革", "定数削減"],
        "negative": []
    },
    "地下鉄・交通インフラ": {
        "positive": ["地下鉄", "ホーム柵", "可動式ホーム柵", "駅エレベーター", "市バス", "名鉄本線高架化", "あおなみ線"],
        "negative": []
    },
    "防災・雨水・治水対策": {
        "positive": ["雨水貯留", "治水", "ゲリラ豪雨", "浸水対策", "南海トラフ", "防潮壁", "避難所", "防災教育"],
        "negative": []
    },
    "子ども医療費助成": {
        "positive": ["子ども医療費", "医療費無償化", "通院無料", "18歳まで無料"],
        "negative": ["高齢者"]
    },
    "トワイライト・放課後児童対策": {
        "positive": ["トワイライト", "学童保育", "放課後児童クラブ", "待機児童"],
        "negative": []
    },
    "体育館エアコン設置": {
        "positive": ["体育館空調", "体育館エアコン", "空調設備", "普通教室空調"],
        "negative": []
    },
    "図書館・文化施設": {
        "positive": ["アクティブライブラリー", "千種図書館", "図書館整備", "瑞穂スポーツパーク"],
        "negative": []
    }
}

def clean_name(name: str) -> str:
    return re.sub(r"[\s\u3000]+", "", name)

def find_related_statements(pledge, speaker_stmts, max_count=2):
    """京都版完全準拠の厳格照合ロジック"""
    if not speaker_stmts:
        return []

    target_text = f"{pledge.get('target_issue', '')} {pledge.get('headline', '')} {pledge.get('exact_quote', '')}"

    search_keywords = []
    # 1. ルールベースの主題キーワード抽出
    for topic_name, rule in NAGOYA_TOPIC_RULES.items():
        if topic_name in target_text or any(p in target_text for p in rule["positive"]):
            search_keywords.extend(rule["positive"])
            break

    # 2. 一般キーワード抽出（抽象語・市会頻出の無意味語を徹底除外）
    if not search_keywords:
        words = re.findall(r"[\u4e00-\u9fa5]{2,}", target_text)
        unique_words = list(dict.fromkeys(words))
        stop_words = {
            "推進", "支援", "実現", "対策", "安心", "安全", "向上", "強化", 
            "名古屋", "要望", "市民", "取組", "充実", "創設", "見直し", "徹底",
            "促進", "目指す", "課題", "問題", "事業", "地域", "社会", "生活"
        }
        filtered = [w for w in unique_words if w not in stop_words]
        search_keywords = filtered[:6] if filtered else []

    if not search_keywords:
        return []

    matched_stmts = []
    for stmt in speaker_stmts:
        summary = stmt.get("statement_summary") or stmt.get("summary") or stmt.get("question_summary") or ""
        text = stmt.get("statement_text") or stmt.get("question_text") or stmt.get("text") or ""
        topic = stmt.get("topic") or stmt.get("category") or ""
        full_text = f"{summary} {topic} {text}"

        hit_count = sum(1 for kw in search_keywords if kw in full_text)
        if hit_count > 0:
            # キーワード一致数に強い重み付け
            score = (
                hit_count * 20 +
                (stmt.get("solution_score", 0) or 0) +
                (stmt.get("evidence_score", 0) or 0) +
                (stmt.get("constructive_score", 0) or 0)
            )
            matched_stmts.append((score, stmt))

    if not matched_stmts:
        return []

    matched_stmts.sort(key=lambda x: (x[0], x[1].get("meeting_date", "")), reverse=True)
    
    results = []
    for _, best_stmt in matched_stmts[:max_count]:
        official_url = (
            best_stmt.get("official_url") or 
            best_stmt.get("source_url") or 
            best_stmt.get("url") or 
            ""
        )
        s_date = best_stmt.get("meeting_date") or best_stmt.get("date") or ""
        s_committee = best_stmt.get("meeting_name") or best_stmt.get("committee") or best_stmt.get("meeting_title") or "名古屋市会 本会議・委員会"
        s_sum = best_stmt.get("statement_summary") or best_stmt.get("summary") or best_stmt.get("question_summary") or best_stmt.get("statement_text", "")
        
        results.append({
            "date": s_date,
            "committee": s_committee,
            "summary": s_sum[:200] + ("..." if len(s_sum) > 200 else ""),
            "speech_id": str(best_stmt.get("id") or best_stmt.get("speech_id") or ""),
            "official_url": official_url
        })
    return results

def main():
    print("=== 名古屋市議 公約・質疑結合パイプライン (京都完全準拠・厳格照合) ===")

    if not PLEDGES_EXTRACTED.exists():
        fallback_pledges = FRONTEND_DATA / "pledge_tracker_nagoya_2.json"
        pledges_path = fallback_pledges if fallback_pledges.exists() else None
    else:
        pledges_path = PLEDGES_EXTRACTED

    if not pledges_path:
        print("❌ 公約元データが見つかりません。")
        return

    raw_pledge_data = json.loads(pledges_path.read_text(encoding="utf-8"))
    councilor_pledges_list = raw_pledge_data.get("councilors", []) if isinstance(raw_pledge_data, dict) else raw_pledge_data

    statements = json.loads(STATEMENTS_FILE.read_text(encoding="utf-8")) if STATEMENTS_FILE.exists() else []
    print(f"🔍 データロード: 公約対象 {len(councilor_pledges_list)} 名 / 質疑レコード {len(statements)} 件")

    stmts_by_speaker = {}
    for s in statements:
        spk = s.get("speaker", "").strip()
        c_spk = clean_name(spk)
        stmts_by_speaker.setdefault(c_spk, []).append(s)

    pledge_tracker = {}

    for c in councilor_pledges_list:
        raw_name = c.get("speaker") or c.get("name") or ""
        c_name = clean_name(raw_name)
        if not c_name:
            continue

        district = c.get("district", "")
        party = c.get("party") or c.get("partyGroup", "")
        bulletin_url = c.get("bulletin_url", "")
        raw_pledges = c.get("pledges", [])

        # 議員本人の発言レコード
        my_stmts = stmts_by_speaker.get(c_name, [])

        tracked_items = []
        for idx, p in enumerate(raw_pledges):
            p_id = p.get("id") or f"p_{idx+1}"
            cat = p.get("category", "くらし・環境・エネルギー")
            target_issue = p.get("target_issue", "")
            headline = p.get("headline", "")
            exact_quote = p.get("exact_quote") or p.get("quote") or ""
            stance = p.get("stance", "推進・拡充")
            item_bulletin_url = p.get("bulletin_url") or bulletin_url

            # 京都準拠の厳格照合を実行
            related_stmts = find_related_statements(p, my_stmts, max_count=2)
            main_stmt = related_stmts[0] if related_stmts else None

            tracked_items.append({
                "id": f"pledge_nagoya_{c_name}_{idx+1}",
                "headline": headline,
                "category": cat,
                "target_issue": target_issue,
                "stance": stance,
                "election_promise": {
                    "quote": exact_quote,
                    "source_name": "令和5年 名古屋市議会議員一般選挙 公式選挙公報",
                    "bulletin_url": item_bulletin_url
                },
                "council_vote": None,
                "council_statement": main_stmt,
                "council_statements": related_stmts
            })

        councilor_data = {
            "district": district,
            "party": party,
            "bulletin_url": bulletin_url,
            "tracked_items": tracked_items
        }

        # 原名とスペース除去名の両キーを登録（検索耐性確保）
        pledge_tracker[raw_name] = councilor_data
        if c_name != raw_name:
            pledge_tracker[c_name] = councilor_data

    for out_p in OUTPUT_FILES:
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(pledge_tracker, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 生成・保存完了: {out_p.resolve()}")

    print(f"🎉 厳格照合による結合が完了しました！（全 {len(councilor_pledges_list)} 名）")

if __name__ == "__main__":
    main()