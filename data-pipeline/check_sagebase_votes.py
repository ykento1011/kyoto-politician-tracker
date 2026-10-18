from google.cloud import bigquery

PROJECT_ID = "gen-lang-client-0253904061"
DATASET_ID = "sagebase_data"
KYOTO_GOV_ID = "gov_5aa370b2fe3f4dbf916a989810440ab8"

client = bigquery.Client(project=PROJECT_ID)

def check_tables():
    print("🔍 1. データセット内の関連テーブルを探索中...")
    query = f"""
        SELECT table_name
        FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.TABLES`
        WHERE table_name LIKE '%proposal%' 
           OR table_name LIKE '%vote%' 
           OR table_name LIKE '%judge%'
        ORDER BY table_name
    """
    tables = [r.table_name for r in client.query(query).result()]
    print(f"発見されたテーブル: {tables}\n")
    return tables

def check_kyoto_proposals(tables):
    if "proposals" not in tables:
        print("❌ proposals テーブルが見つかりませんでした。")
        return

    print("🔍 2. 京都市会の議案・賛否データの存在を確認中...")
    # proposals テーブルのカラムを確認
    cols_query = f"""
        SELECT column_name 
        FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = 'proposals'
    """
    cols = [r.column_name for r in client.query(cols_query).result()]
    print(f"proposals カラム: {cols}")

    # 自治体IDや会議IDで絞り込めるかテスト
    test_query = f"""
        SELECT COUNT(1) AS count
        FROM `{PROJECT_ID}.{DATASET_ID}.proposals` p
        LIMIT 10
    """
    result = list(client.query(test_query).result())
    print(f"proposals 総件数: {result[0].count} 件")

if __name__ == "__main__":
    tables = check_tables()
    check_kyoto_proposals(tables)