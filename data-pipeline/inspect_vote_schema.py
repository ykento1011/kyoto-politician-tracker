from google.cloud import bigquery

PROJECT_ID = "gen-lang-client-0253904061"
DATASET_ID = "sagebase_data"
KYOTO_INTERNAL_ID = 88  # 先ほど確認できた京都市の内部ID

client = bigquery.Client(project=PROJECT_ID)

def check_schema_and_votes():
    target_tables = [
        'proposal_vote_parliamentary_groups',
        'proposal_vote_politicians',
        'proposal_vote_records',
        'proposal_judges'
    ]

    print("🔍 1. 各投票関連テーブルのカラム定義を確認中...")
    schema_query = f"""
        SELECT table_name, column_name, data_type
        FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name IN UNNEST({target_tables})
        ORDER BY table_name, ordinal_position
    """
    columns_by_table = {}
    for r in client.query(schema_query).result():
        columns_by_table.setdefault(r.table_name, []).append(r.column_name)

    for t, cols in columns_by_table.items():
        print(f"\n📁 【{t}】\n  カラム: {cols}")

    print("\n" + "="*60 + "\n")
    print("🔍 2. 京都市（ID: 88）の現任期（2023年5月〜）議案の件数・日付確認中...")

    proposals_query = f"""
        SELECT 
            COUNT(1) AS total_kyoto,
            COUNTIF(voted_date >= '2023-05-01' OR submitted_date >= '2023-05-01') AS current_term_count,
            MIN(COALESCE(voted_date, submitted_date)) AS oldest_date,
            MAX(COALESCE(voted_date, submitted_date)) AS latest_date
        FROM `{PROJECT_ID}.{DATASET_ID}.proposals`
        WHERE governing_body_id = {KYOTO_INTERNAL_ID}
    """
    res = list(client.query(proposals_query).result())[0]
    print(f"  - 京都市 累計議案数: {res.total_kyoto:,} 件")
    print(f"  - 現任期（2023年5月〜）議案数: {res.current_term_count:,} 件")
    print(f"  - 記録期間: {res.oldest_date} 〜 {res.latest_date}")

    print("\n🔍 3. 京都市の直近議案サンプル（5件）...")
    sample_query = f"""
        SELECT 
            id,
            title,
            COALESCE(voted_date, submitted_date) AS bill_date,
            deliberation_result,
            proposal_category
        FROM `{PROJECT_ID}.{DATASET_ID}.proposals`
        WHERE governing_body_id = {KYOTO_INTERNAL_ID}
          AND (voted_date >= '2023-05-01' OR submitted_date >= '2023-05-01')
        ORDER BY bill_date DESC
        LIMIT 5
    """
    samples = list(client.query(sample_query).result())
    for s in samples:
        print(f"  - [ID:{s.id}] {s.bill_date} | {s.proposal_category or '種別無'} | {s.title} (結果: {s.deliberation_result})")

if __name__ == "__main__":
    check_schema_and_votes()