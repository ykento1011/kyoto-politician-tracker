import json
import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabaseの接続情報が設定されていません。")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BATCH_SIZE = 500

def main():
    input_file = "analyzed_kyoto_politicians_term.json"
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"{input_file} が見つかりません。")

    print(f"📖 読み込みファイル: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        statements = json.load(f)

    # 実質政策質疑（5,128件）を抽出
    targets = [s for s in statements if s.get("analysis", {}).get("is_evaluated")]
    total = len(targets)
    print(f"🎯 投入対象レコード数（実質政策質疑）: {total:,} 件")
    print(f"🚀 {BATCH_SIZE} 件ごとのバッチで UPSERT を開始します...\n")

    start_time = time.time()
    success_count = 0

    for i in range(0, total, BATCH_SIZE):
        batch = targets[i:i + BATCH_SIZE]
        records = []

        for stmt in batch:
            analysis = stmt.get("analysis", {})
            scores = analysis.get("scores", {})

            records.append({
                "meeting_id": stmt.get("meeting_id"),
                "sequence_number": stmt.get("sequence_number"),
                "meeting_title": stmt.get("meeting_title"),
                "meeting_date": stmt.get("meeting_date"),
                "speaker": stmt.get("speaker"),
                "statement_text": stmt.get("statement_text"),
                "is_evaluated": True,
                "evidence_score": int(scores.get("evidence", 0)),
                "solution_score": int(scores.get("solution", 0)),
                "local_focus_score": int(scores.get("local_focus", 0)),
                "constructive_score": int(scores.get("constructive", 0)),
                "scoring_reasoning": analysis.get("reasoning", ""),
                "summary": analysis.get("summary", ""),
                "category": analysis.get("category", "政策質疑")
            })

        max_retries = 3
        for attempt in range(max_retries):
            try:
                supabase.table("statements").upsert(
                    records,
                    on_conflict="meeting_id,sequence_number"
                ).execute()
                success_count += len(records)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"\n⚠️ バッチエラー: {e}")
                time.sleep(2)

        print(f"[{min(i + BATCH_SIZE, total):,}/{total:,}] 投入中...", end="\r")

    elapsed = int(time.time() - start_time)
    print(f"\n\n🎉 UPSERT完了！")
    print(f"✅ 成功件数: {success_count:,} / {total:,} 件（所要時間: {elapsed}秒）")

if __name__ == "__main__":
    main()