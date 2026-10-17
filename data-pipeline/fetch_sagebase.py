import json
from google.cloud import bigquery

PROJECT_ID = "gen-lang-client-0253904061"
DATASET_ID = "sagebase_data"
KYOTO_GOV_ID = "gov_5aa370b2fe3f4dbf916a989810440ab8"

def inspect_schema(client):
    schema_query = f"""
        SELECT table_name, column_name, data_type
        FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name IN ('minutes', 'conferences')
        ORDER BY table_name, ordinal_position
    """
    results = list(client.query(schema_query).result())
    return {f"{r.table_name}.{r.column_name}" for r in results}

def fetch_kyoto_data():
    client = bigquery.Client(project=PROJECT_ID)
    columns = inspect_schema(client)

    conf_gb_col = "governing_body_id" if "conferences.governing_body_id" in columns else "governing_body_sagebase_id"
    min_meeting_col = "meeting_id" if "minutes.meeting_id" in columns else "meeting_sagebase_id"

    print("\n🚀 現任期（2023年5月〜現在）の京都市会全発言データを抽出中...")

    # 💡 2023年5月以降（現任期）を全件取得。非質疑の会議体は事前に除外
    query = f"""
        SELECT 
            m.name AS meeting_name,
            m.date AS meeting_date,
            c.speaker_name,
            c.speaker_id,
            c.speaker_header,
            c.comment AS statement_text,
            c.sequence_number,
            c.sagebase_id AS conversation_id,
            m.sagebase_id AS meeting_id,
            m.url AS meeting_url
        FROM `{PROJECT_ID}.{DATASET_ID}.conversations` c
        JOIN `{PROJECT_ID}.{DATASET_ID}.minutes` min
          ON c.minutes_id = min.id
        JOIN `{PROJECT_ID}.{DATASET_ID}.meetings` m
          ON min.{min_meeting_col} = m.id
        JOIN `{PROJECT_ID}.{DATASET_ID}.conferences` conf
          ON m.conference_id = conf.id
        JOIN `{PROJECT_ID}.{DATASET_ID}.governing_bodies` gb
          ON conf.{conf_gb_col} = gb.id
        WHERE gb.sagebase_id = '{KYOTO_GOV_ID}'
          AND m.date >= '2023-05-01'
          AND m.name NOT LIKE '%市会運営委員会%'
          AND m.name NOT LIKE '%理事会%'
        ORDER BY m.date ASC, m.id ASC, c.sequence_number ASC
    """

    try:
        query_job = client.query(query)
        results = query_job.result()

        formatted_data = []
        for row in results:
            formatted_data.append({
                "meeting_title": row.meeting_name,
                "meeting_date": str(row.meeting_date) if row.meeting_date else "",
                "speaker": row.speaker_name,
                "speaker_id": str(row.speaker_id) if row.speaker_id else None,
                "speaker_header": row.speaker_header,
                "statement_text": row.statement_text,
                "sequence_number": row.sequence_number,
                "conversation_id": row.conversation_id,
                "meeting_id": row.meeting_id,
                "source_url": row.meeting_url
            })
        return formatted_data

    except Exception as e:
        print(f"❌ クエリエラー: {e}")
        return []

def main():
    data = fetch_kyoto_data()
    if data:
        output_file = "sagebase_crawled_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n🎉 抽出成功: 合計 {len(data):,} 件の発言データを {output_file} に保存しました。")
    else:
        print("\nデータが0件、またはクエリ修正が必要です。")

if __name__ == "__main__":
    main()