import os
import sys
import re
import json
import time
import argparse
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai
from google.genai import types

# --- パス設定 ---
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
ENV_FILE = BASE_DIR / ".env"
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist" / "data"

# 都市別設定マッピング
CITY_CONFIG = {
    "kyoto": {
        "name": "京都市会",
        "votes_file": FRONTEND_DATA / "votes_summary.json",
        "statements_file": FRONTEND_DATA / "statements_summary.json",
        "output_files": [
            FRONTEND_DATA / "bill_issues.json",
            FRONTEND_DIST / "bill_issues.json"
        ]
    },
    "osaka": {
        "name": "大阪市会",
        "votes_file": FRONTEND_DATA / "osaka_votes_summary.json",
        "statements_file": FRONTEND_DATA / "osaka_statements_summary.json",
        "output_files": [
            FRONTEND_DATA / "osaka_bill_issues.json",
            FRONTEND_DIST / "osaka_bill_issues.json",
            FRONTEND_DATA / "osaka" / "bill_issues.json"
        ]
    },
    "nagoya": {
        "name": "名古屋市会",
        "votes_file": FRONTEND_DATA / "nagoya_votes_summary.json",
        "statements_file": FRONTEND_DATA / "nagoya_statements_summary.json",
        "output_files": [
            FRONTEND_DATA / "nagoya_bill_issues.json",
            FRONTEND_DIST / "nagoya_bill_issues.json"
        ]
    }
}

CATEGORIES = [
    "財政・行革", "福祉・医療・健康", "子育て・教育",
    "都市再生・交通インフラ", "産業・観光・地域経済",
    "くらし・環境・エネルギー", "防災・減災・治安", "文化・景観・歴史"
]

cache_lock = threading.Lock()

def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                os.environ["GEMINI_API_KEY"] = line.split("=", 1)[1].strip().strip("'"")

def load_json(p):
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def find_context_stmts(bill, stmts):
    b_num = bill.get("bill_number", "").strip()
    title = bill.get("title", "").strip()
    clean_title = re.sub(r'京都市|大阪市|名古屋市|に関する|について|の一部を改正する|条例の制定|予算|会計|議案', '', title)
    nouns = [w for w in re.split(r'[（）\s、。]', clean_title) if len(w) >= 3]
    keywords = [b_num] if len(b_num) >= 2 else []
    keywords.extend(nouns[:2])

    hits = []
    if keywords:
        for s in stmts:
            txt = (s.get("question_text", "") or s.get("statement_text", "")) + " " + s.get("answer_text", "")
            if any(k in txt for k in keywords):
                spk = s.get("speaker", "議員")
                hits.append(f"【{spk}の発言ログ】\n{txt[:350]}")
                if len(hits) >= 3:
                    break
    return hits

def analyze_bill(client, model_name, city_name, bill, ctx):
    session = bill.get("session_name", "")
    bill_num = bill.get("bill_number", "")
    title = bill.get("title", "")
    result = bill.get("result", "")
    votes_dict = bill.get("votes", {})

    agree_gps = [g for g, v in votes_dict.items() if v == "賛成"]
    disagree_gps = [g for g, v in votes_dict.items() if v == "反対"]
    ctx_str = "\n\n".join(ctx) if ctx else "（議事録抜粋なし）"

    prompt = f"""以下の{city_name}の議案について、なぜ各会派の賛否が分かれたのか、その「対立軸」と「双方の政治的論理」を客観的・中立的に整理してください。

【議案情報】
- 定例会: {session}
- 議案番号: {bill_num}
- 件名: {title}
- 議決結果: {result}
- 賛成会派: {', '.join(agree_gps)}
- 反対会派: {', '.join(disagree_gps)}

【議場発言ログ抜粋】
{ctx_str}

【分析・出力要件】
1. 政治的中立性を厳格に維持し、特定の会派に肩入れしないこと。
2. 「賛成派の論理」と「反対派の論理」の双方が、それぞれの理念や政策的優先度に基づき合理的であると理解できるように整理すること。
3. カテゴリは必ず以下の8大カテゴリから1つのみを選択すること:
   ［{' / '.join(CATEGORIES)}］
4. 必ず以下のJSON構造のみを出力してください:

{{
  "category": "上記8大カテゴリから1つ",
  "key_conflict": "対立軸の端的な要約（30字以内）",
  "background": "この議案が提出された背景と概要（100字前後）",
  "agree_logic": "賛成派（{', '.join(agree_gps[:3])}等）が賛成した主な理由・政策意図（120字前後）",
  "disagree_logic": "反対派（{', '.join(disagree_gps[:3])}等）が反対した主な理由・懸念点（120字前後）"
}}
"""
    for attempt in range(4):
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                )
            )
            return json.loads(res.text)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                time.sleep((attempt + 1) * 3)
            else:
                time.sleep(1.5)
    return None

def main():
    parser = argparse.ArgumentParser(description="3都市共通 対立議案AI論点解説パイプライン")
    parser.add_argument("--city", default="kyoto", choices=["kyoto", "osaka", "nagoya"], help="対象都市コード")
    parser.add_argument("--workers", type=int, default=8, help="並列ワーカー数")
    parser.add_argument("--model", default="gemini-2.5-flash", help="使用モデル名")
    args = parser.parse_args()

    city_cfg = CITY_CONFIG[args.city]
    city_name = city_cfg["name"]

    print("=" * 60)
    print(f"🚀 【{city_name}】対立議案AI論点解説パイプライン（統一エンジン）")
    print(f"⚡ ワーカー並列数: {args.workers} / モデル: {args.model}")
    print("=" * 60)

    load_env()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY が見つかりません。")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    votes = load_json(city_cfg["votes_file"])
    statements = load_json(city_cfg["statements_file"])

    if not votes:
        print(f"⚠️ 議決ファイルが存在しないか空です: {city_cfg['votes_file']}")
        sys.exit(0)

    # 賛否分裂（contested）議案の抽出
    contested_bills = []
    for b in votes:
        v_vals = list(b.get("votes", {}).values())
        if "賛成" in v_vals and "反対" in v_vals:
            contested_bills.append(b)

    total_target = len(contested_bills)
    print(f"🎯 賛否が分かれた対立議案: {total_target} 件 / 総議案数: {len(votes)} 件")

    # 既存データのキャッシュ復元
    existing_issues = {}
    for out_p in city_cfg["output_files"]:
        if out_p.exists():
            d = load_json(out_p)
            if isinstance(d, list):
                for item in d:
                    k = f"{item.get('session_name')}_{item.get('bill_number')}"
                    if k not in existing_issues and item.get("key_conflict"):
                        existing_issues[k] = item

    print(f"📦 既存キャッシュ: {len(existing_issues)} 件")

    def process_bill(bill):
        b_key = f"{bill.get('session_name')}_{bill.get('bill_number')}"
        with cache_lock:
            if b_key in existing_issues:
                return b_key, True

        ctx = find_context_stmts(bill, statements)
        res = analyze_bill(client, args.model, city_name, bill, ctx)

        with cache_lock:
            if res:
                existing_issues[b_key] = {
                    "id": f"{b_key}_{bill.get('title', '')[:10]}",
                    "session_name": bill.get("session_name"),
                    "bill_number": bill.get("bill_number"),
                    "title": bill.get("title"),
                    "category": res.get("category", "財政・行革"),
                    "key_conflict": res.get("key_conflict", ""),
                    "background": res.get("background", ""),
                    "agree_logic": res.get("agree_logic", ""),
                    "disagree_logic": res.get("disagree_logic", ""),
                    "updated_at": time.strftime("%Y-%m-%d")
                }
                curr = len(existing_issues)
                print(f"[{curr}/{total_target}] ✅ {b_key}: {bill.get('title')[:16]}... -> {res.get('key_conflict')}")

                # 5件ごと、または全完了時にチェックポイント保存
                if curr % 5 == 0 or curr == total_target:
                    payload = list(existing_issues.values())
                    for out_p in city_cfg["output_files"]:
                        out_p.parent.mkdir(parents=True, exist_ok=True)
                        out_p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                print(f"❌ {b_key} の解析に失敗しました")

        return b_key, res is not None

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(process_bill, bill) for bill in contested_bills]
        for f in as_completed(futures):
            pass

    # 最終同期保存
    payload = list(existing_issues.values())
    for out_p in city_cfg["output_files"]:
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n🎉 【{city_name}】全{len(payload)}件 の対立議案AI論点解説を保存完了しました。")

if __name__ == "__main__":
    main()
