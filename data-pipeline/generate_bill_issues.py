import os
import re
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai
from google.genai import types

# パス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
VOTES_FILE = os.path.join(BASE_DIR, "..", "frontend", "public", "data", "votes_summary.json")
MINUTES_FILE = os.path.join(BASE_DIR, "sagebase_crawled_data.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "..", "frontend", "public", "data", "bill_issues.json")

# 並列ワーカー数（Rate Limit と安定性を考慮して 6〜8 を推奨）
MAX_WORKERS = 6
cache_lock = threading.Lock()

# 💡 .env ファイルから自動ロード
if os.path.exists(ENV_FILE):
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
                os.environ["GEMINI_API_KEY"] = key

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError(f"❌ {ENV_FILE} または環境変数に GEMINI_API_KEY が見つかりません。")

# Gemini クライアントの初期化（高速・高品質な 2.5-flash を使用）
client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def get_conflicted_bills(votes):
    """賛成と反対が両方存在する対立議案のみを抽出"""
    conflicted = []
    for bill in votes:
        v_values = list(bill.get("votes", {}).values())
        if "賛成" in v_values and "反対" in v_values:
            conflicted.append(bill)
    return conflicted

def find_related_statements(bill, all_minutes):
    """会議録データから該当議案に関連する討論・発言を抽出"""
    if not all_minutes:
        return []

    bill_num = bill.get("bill_number", "").strip()
    title = bill.get("title", "").strip()
    
    keywords = [bill_num] if bill_num and len(bill_num) > 1 else []
    cleaned_title = re.sub(r'京都市|に関する|について|の一部を改正する|条例の制定|意見書の提出', '', title)
    nouns = [w for w in re.split(r'[（）\s、。]', cleaned_title) if len(w) >= 3]
    keywords.extend(nouns[:2])

    matched_texts = []
    for stmt in all_minutes:
        text = stmt.get("statement_text", "")
        if any(k in text for k in keywords):
            speaker = stmt.get("speaker", "議員")
            matched_texts.append(f"【{speaker}の発言】\n{text[:400]}")
            if len(matched_texts) >= 4:
                break

    return matched_texts

def analyze_bill_issue(bill, related_texts):
    """Gemini APIを用いて議案の対立軸・双方の論理を構造化（リトライ機構付き）"""
    title = bill.get("title")
    bill_number = bill.get("bill_number")
    session = bill.get("session_name")
    votes = bill.get("votes", {})
    result = bill.get("result", "")

    agree_groups = [g for g, v in votes.items() if v == "賛成"]
    disagree_groups = [g for g, v in votes.items() if v == "反対"]

    context_str = "\n\n".join(related_texts) if related_texts else "（該当する詳細な討論発言ログなし）"

    prompt = f"""
以下の京都市議会の議案について、なぜ各会派の賛否が分かれたのか、その「対立軸」と「双方の政治的論理」を客観的・中立的に整理してください。

【議案情報】
- 定例会: {session}
- 議案番号: {bill_number}
- 件名: {title}
- 議決結果: {result}
- 賛成会派: {', '.join(agree_groups)}
- 反対会派: {', '.join(disagree_groups)}

【会議録からの参考抜粋】
{context_str}

【分析・出力要件】
1. 政治的中立性を厳格に維持し、特定の会派に肩入れしないこと。
2. 「賛成派の論理」と「反対派の論理」の双方が、それぞれの理念や政策的優先順位に基づき合理的であると理解できるように書くこと。
3. 出力は以下のJSON形式のみとし、Markdownのコードブロック（```json ... ```）で出力してください。

{{
  "key_conflict": "対立軸の端的な要約（30字以内、例: 防衛費増額に伴う財源確保のあり方）",
  "background": "この議案が提出された背景と概要（100字前後）",
  "agree_logic": "賛成派（{', '.join(agree_groups[:3])}など）が賛成した主な理由・政策意図（120字前後）",
  "disagree_logic": "反対派（{', '.join(disagree_groups[:3])}など）が反対した主な理由・懸念点（120字前後）"
}}
"""
    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait_time = (attempt + 1) * 4
                time.sleep(wait_time)
            else:
                time.sleep(2)
    return None

def process_single_bill(bill, all_minutes, issues_dict, total_count):
    """1つの議案を解析し、スレッドセーフにキャッシュ保存"""
    bill_id = f"{bill.get('session_name')}_{bill.get('bill_number')}_{bill.get('title')[:10]}"
    title_short = bill.get("title", "")[:20]
    
    related_texts = find_related_statements(bill, all_minutes)
    analysis = analyze_bill_issue(bill, related_texts)

    with cache_lock:
        if analysis:
            issues_dict[bill_id] = {
                "id": bill_id,
                "session_name": bill.get("session_name"),
                "bill_number": bill.get("bill_number"),
                "title": bill.get("title"),
                "key_conflict": analysis.get("key_conflict", ""),
                "background": analysis.get("background", ""),
                "agree_logic": analysis.get("agree_logic", ""),
                "disagree_logic": analysis.get("disagree_logic", ""),
                "updated_at": time.strftime("%Y-%m-%d")
            }
        completed = len(issues_dict)
        conflict_label = analysis.get("key_conflict", "解析失敗") if analysis else "エラー"
        print(f"[{completed}/{total_count}] {bill.get('session_name')} {bill.get('bill_number')} - {title_short} -> {conflict_label}")

        # 3件完了ごと、または全件完了時にチェックポイント保存
        if completed % 3 == 0 or completed == total_count:
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(list(issues_dict.values()), f, ensure_ascii=False, indent=2)

    return bill_id

def main():
    print("==================================================")
    print("🚀 対立議案 争点分析バッチパイプライン（並列化版）")
    print(f"⚡ ワーカー並列数: {MAX_WORKERS} / 使用モデル: {MODEL_NAME}")
    print("==================================================")

    votes = load_json(VOTES_FILE)
    if not votes:
        print(f"❌ {VOTES_FILE} が見つかりません。")
        return

    all_minutes = load_json(MINUTES_FILE)
    conflicted_bills = get_conflicted_bills(votes)
    print(f"📊 全議案数: {len(votes)} 件 / 会議録ログ: {len(all_minutes)} 件")
    print(f"🎯 賛否が分かれた対立議案: {len(conflicted_bills)} 件")

    # 既存キャッシュの読み込み
    existing_issues = load_json(OUTPUT_FILE)
    if isinstance(existing_issues, list):
        issues_dict = {item["id"]: item for item in existing_issues if "id" in item}
    elif isinstance(existing_issues, dict):
        issues_dict = existing_issues
    else:
        issues_dict = {}

    print(f"🔄 既存解析済み: {len(issues_dict)} 件")

    # 未処理の議案を抽出
    unprocessed_bills = []
    for b in conflicted_bills:
        b_id = f"{b.get('session_name')}_{b.get('bill_number')}_{b.get('title')[:10]}"
        if b_id not in issues_dict:
            unprocessed_bills.append(b)

    print(f"⚡ 新規解析対象: {len(unprocessed_bills)} 件")
    print("==================================================")

    if not unprocessed_bills:
        print("✅ すべての対立議案は既に解析済みです。")
        return

    start_time = time.time()

    # マルチスレッド並列実行
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(process_single_bill, bill, all_minutes, issues_dict, len(conflicted_bills))
            for bill in unprocessed_bills
        ]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"    ⚠️ ワーカーエラー: {e}")

    # 最終保存
    with cache_lock:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(list(issues_dict.values()), f, ensure_ascii=False, indent=2)

    elapsed = int(time.time() - start_time)
    print("==================================================")
    print(f"🎉 全対立議案の並列解析が完了しました！（所要時間: {elapsed//60}分{elapsed%60}秒）")
    print(f"📁 保存先: {os.path.abspath(OUTPUT_FILE)}")
    print("==================================================")

if __name__ == "__main__":
    main()