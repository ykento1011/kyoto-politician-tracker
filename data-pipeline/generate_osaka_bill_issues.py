import os
import re
import json
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai
from google.genai import types

ROOT = Path(".").resolve()
ENV_FILE = ROOT / "data-pipeline" / ".env"
VOTES_FILE = ROOT / "frontend" / "public" / "data" / "osaka_votes_summary.json"
STATEMENTS_FILE = ROOT / "frontend" / "public" / "data" / "osaka_statements_summary.json"
OUTPUT_FILES = [
    ROOT / "frontend" / "public" / "data" / "osaka_bill_issues.json",
    ROOT / "frontend" / "dist" / "data" / "osaka_bill_issues.json",
    ROOT / "frontend" / "public" / "data" / "osaka" / "bill_issues.json"
]

MAX_WORKERS = 8
cache_lock = threading.Lock()

# APIキー読み込み
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            os.environ["GEMINI_API_KEY"] = line.split("=", 1)[1].strip().strip("'\"")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError(f"❌ GEMINI_API_KEY が見つかりません。")

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"

def load_json(p):
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except:
            return []
    return []

# 既存の出力があれば読み込んでキャッシュ再開
existing_issues = {}
for p in OUTPUT_FILES:
    if p.exists():
        data = load_json(p)
        if isinstance(data, list):
            for item in data:
                k = f"{item.get('session_name')}_{item.get('bill_number')}"
                if k not in existing_issues and item.get("key_conflict"):
                    existing_issues[k] = item

print(f"📦 既存の論点解説キャッシュ: {len(existing_issues)} 件")

votes = load_json(VOTES_FILE)
statements = load_json(STATEMENTS_FILE)

# 賛否が割れた議案（contested）を抽出
contested_bills = []
for b in votes:
    v_vals = list(b.get("votes", {}).values())
    if "賛成" in v_vals and "反対" in v_vals:
        contested_bills.append(b)

total_target = len(contested_bills)
print(f"🎯 大阪市会 賛否が分かれた対立議案: {total_target} 件")

def find_context_stmts(bill, stmts):
    b_num = bill.get("bill_number", "").strip()
    title = bill.get("title", "").strip()
    clean_title = re.sub(r'大阪市|に関する|について|の一部を改正する|条例の制定|予算|会計', '', title)
    nouns = [w for w in re.split(r'[（）\s、。]', clean_title) if len(w) >= 3]
    keywords = [b_num] if len(b_num) > 2 else []
    keywords.extend(nouns[:2])
    
    hits = []
    if keywords:
        for s in stmts:
            txt = s.get("question_text", "") + " " + s.get("answer_text", "")
            if any(k in txt for k in keywords):
                spk = s.get("speaker", "議員")
                hits.append(f"【{spk}の質疑・討論】\n{txt[:350]}")
                if len(hits) >= 3:
                    break
    return hits

def analyze_bill(bill, ctx):
    session = bill.get("session_name")
    bill_num = bill.get("bill_number")
    title = bill.get("title")
    result = bill.get("result", "")
    votes_dict = bill.get("votes", {})
    
    agree_gps = [g for g, v in votes_dict.items() if v == "賛成"]
    disagree_gps = [g for g, v in votes_dict.items() if v == "反対"]
    
    ctx_str = "\n\n".join(ctx) if ctx else "（議事録抜粋なし）"
    
    prompt = f"""
以下の大阪市会の議案について、なぜ各会派の賛否が分かれたのか、その「対立軸」と「双方の政治的論理」を客観的・中立的に整理してください。

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
1. 政治的中立性を厳格に維持し、特定の立場に偏らないこと。
2. 「賛成派の論理」と「反対派の論理」の双方が、それぞれの理念や政策優先度に基づき合理的であると理解できるように整理すること。
3. カテゴリは必ず以下の8つの中から最も適切なものを1つだけ選択すること:
   ［財政・行革 / 福祉・医療・健康 / 子育て・教育 / 都市再生・交通インフラ / 産業・観光・地域経済 / くらし・環境・エネルギー / 防災・減災・治安 / 文化・景観・歴史］
4. 必ず以下のJSON構造のみを出力してください:

{{
  "category": "上記8大カテゴリから1つ",
  "key_conflict": "対立軸の端的な要約（30字以内、例: 一般会計予算の配分と事業優先度）",
  "background": "この議案が提出された背景と概要（100字前後）",
  "agree_logic": "賛成派（{', '.join(agree_gps[:3])}等）が賛成した主な理由・政策意図（120字前後）",
  "disagree_logic": "反対派（{', '.join(disagree_gps[:3])}等）が反対した主な理由・懸念点（120字前後）"
}}
"""
    for attempt in range(4):
        try:
            res = client.models.generate_content(
                model=MODEL_NAME,
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

def process_bill(bill, idx):
    b_key = f"{bill.get('session_name')}_{bill.get('bill_number')}"
    
    with cache_lock:
        if b_key in existing_issues:
            return b_key, True

    ctx = find_context_stmts(bill, statements)
    res = analyze_bill(bill, ctx)
    
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
            print(f"[{curr}/{total_target}] ✅ {b_key}: {bill.get('title')[:18]}... -> {res.get('key_conflict')}")
            
            # 5件ごと、または完了時に中間保存
            if curr % 5 == 0 or curr == total_target:
                payload = list(existing_issues.values())
                for out_p in OUTPUT_FILES:
                    out_p.parent.mkdir(parents=True, exist_ok=True)
                    out_p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            print(f"❌ {b_key} の解析に失敗しました")
            
    return b_key, res is not None

print(f"\n🚀 解析開始（並列度: {MAX_WORKERS} / モデル: {MODEL_NAME}）...")
start_time = time.time()

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(process_bill, bill, i) for i, bill in enumerate(contested_bills)]
    for f in as_completed(futures):
        pass

# 最終保存
final_payload = list(existing_issues.values())
for out_p in OUTPUT_FILES:
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")

elapsed = time.time() - start_time
print(f"\n🎉 大阪市会 全{len(final_payload)}件 の対立議案AI論点解説の生成・保存が完了しました（所要時間: {elapsed:.1f}秒）")