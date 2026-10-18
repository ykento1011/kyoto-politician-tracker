from google.cloud import bigquery

PROJECT_ID = "gen-lang-client-0253904061"
DATASET_ID = "sagebase_data"
KYOTO_GOV_ID = "gov_5aa370b2fe3f4dbf916a989810440ab8"

client = bigquery.Client(project=PROJECT_ID)

def check_owner():
    print("🔍 1. 京都市会の自治体内部ID（数値）を確認中...")
    kyoto_gb_query = f"""
        SELECT id, name, sagebase_id
        FROM `{PROJECT_ID}.{DATASET_ID}.governing_bodies`
        WHERE sagebase_id = '{KYOTO_GOV_ID}'
           OR name LIKE '%京都%'
    """
    kyoto_rows = list(client.query(kyoto_gb_query).result())
    kyoto_ids = []
    for r in kyoto_rows:
        print(f"  - 名称: {r.name} | id: {r.id} | sagebase_id: {r.sagebase_id}")
        kyoto_ids.append(r.id)

    print("\n🔍 2. proposals（議案テーブル）の登録先上位自治体を集計中...")
    query = f"""
        SELECT 
            COALESCE(gb.name, '名称不明（ID: ' || CAST(p.governing_body_id AS STRING) || '）') AS governing_body_name,
            COUNT(1) AS proposal_count
        FROM `{PROJECT_ID}.{DATASET_ID}.proposals` p
        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.governing_bodies` gb
          ON CAST(p.governing_body_id AS STRING) = CAST(gb.id AS STRING)
        GROUP BY governing_body_name
        ORDER BY proposal_count DESC
        LIMIT 10
    """
    for row in client.query(query).result():
        print(f"  - {row.governing_body_name}: {row.proposal_count:,} 件")

    print("\n🔍 3. 京都市のIDで議案が存在するか最終判定中...")
    if kyoto_ids:
        ids_str = ",".join(str(i) for i in kyoto_ids)
        kyoto_check_query = f"""
            SELECT COUNT(1) AS cnt
            FROM `{PROJECT_ID}.{DATASET_ID}.proposals`
            WHERE governing_body_id IN ({ids_str})
        """
        cnt = list(client.query(kyoto_check_query).result())[0].cnt
        print(f"  => 京都市の議案件数: {cnt} 件")
    else:
        print("  => 京都市の自治体IDが特定できませんでした。")

if __name__ == "__main__":
    check_owner()