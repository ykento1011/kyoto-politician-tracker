import json
from pathlib import Path
from google.cloud import bigquery
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / "data-pipeline" / ".env")

SUMMARY_FILE = PROJECT_ROOT / "frontend" / "public" / "data" / "osaka_statements_summary.json"

def main():
    if not SUMMARY_FILE.exists():
        print(f"❌ {SUMMARY_FILE} が見つかりません。")
        return

    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        summary_data = json.load(f)

    target_meetings = set(str(item.get("meeting_id")) for item in summary_data if item.get("meeting_id"))
    print(f"🎯 対象会議数: {len(target_meetings)} 件")

    client = bigquery.Client(project="gen-lang-client-0253904061")
    meeting_ids_str = ", ".join(target_meetings)

    q = f"""
        SELECT 
            CAST(min.meeting_id AS STRING) AS meeting_id,
            min.url AS source_url
        FROM `gen-lang-client-0253904061.sagebase_data.minutes` min
        WHERE min.meeting_id IN ({meeting_ids_str}) AND min.url IS NOT NULL
    """

    print("📥 BigQuery から公式原本URLを取得中...")
    rows = list(client.query(q).result())
    url_map = {r["meeting_id"]: r["source_url"] for r in rows}
    print(f"✅ 取得できた原本URL数: {len(url_map)} / {len(target_meetings)} 会議")

    matched_count = 0
    for item in summary_data:
        mid = str(item.get("meeting_id"))
        if mid in url_map:
            item["source_url"] = url_map[mid]
            matched_count += 1

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    print(f"🎉 {matched_count:,} 件の発言スレッドに source_url を付与しました。")

if __name__ == "__main__":
    main()
