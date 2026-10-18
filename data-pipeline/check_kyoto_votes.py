from google.cloud import bigquery

PROJECT_ID = "gen-lang-client-0253904061"
DATASET_ID = "sagebase_data"
KYOTO_GOV_ID = "gov_5aa370b2fe3f4dbf916a989810440ab8"

client = bigquery.Client(project=PROJECT_ID)

def check_kyoto_records():
    print("🔍 京都市会の議案・採決データを照合中...")

    # 1. proposals テーブルにおける京都市会の議案数
    query_proposals = f"""
        SELECT 
            COUNT(1) AS total_proposals,
            COUNTIF(p.voted_date >= '2023-05-01' OR p.submitted_date >= '2023-05-01') AS current_term_proposals,
            MIN(p.voted_date) AS oldest_vote,
            MAX(p.voted_date) AS latest_vote
        FROM `{PROJECT_ID}.{DATASET_ID}.proposals` p
        JOIN `{PROJECT_ID}.{DATASET_ID}.governing_bodies` gb
          ON p.governing_body_id = gb.id
        WHERE gb.sagebase_id = '{KYOTO_GOV_ID}'
    """

    try:
        res = list(client.query(query_proposals).result())[0]
        print(f"\n【1. 議案データ (proposals)】")
        print(f"- 京都市会の全議案数: {res.total_proposals:,} 件")
        print(f"- 現任期（2023年5月〜）の議案数: {res.current_term_proposals:,} 件")
        print(f"- 記録期間: {res.oldest_vote} 〜 {res.latest_vote}")
    except Exception as e:
        print(f"❌ proposals クエリエラー: {e}")
        return

    # 2. 会派別賛否（proposal_vote_parliamentary_groups）の件数
    query_group_votes = f"""
        SELECT 
            COUNT(1) AS total_votes,
            COUNT(DISTINCT vg.proposal_id) AS voted_proposals
        FROM `{PROJECT_ID}.{DATASET_ID}.proposal_vote_parliamentary_groups` vg
        JOIN `{PROJECT_ID}.{DATASET_ID}.proposals` p
          ON vg.proposal_id = p.id
        JOIN `{PROJECT_ID}.{DATASET_ID}.governing_bodies` gb
          ON p.governing_body_id = gb.id
        WHERE gb.sagebase_id = '{KYOTO_GOV_ID}'
          AND (p.voted_date >= '2023-05-01' OR p.submitted_date >= '2023-05-01')
    """
    try:
        res_g = list(client.query(query_group_votes).result())[0]
        print(f"\n【2. 会派別賛否 (proposal_vote_parliamentary_groups)】")
        print(f"- 現任期の会派採決レコード数: {res_g.total_votes:,} 件")
        print(f"- 採決データがある議案件数: {res_g.voted_proposals:,} 件")
    except Exception as e:
        print(f"❌ proposal_vote_parliamentary_groups エラー: {e}")

    # 3. 議員別賛否（proposal_vote_politicians）の件数
    query_pol_votes = f"""
        SELECT 
            COUNT(1) AS total_votes,
            COUNT(DISTINCT vp.proposal_id) AS voted_proposals
        FROM `{PROJECT_ID}.{DATASET_ID}.proposal_vote_politicians` vp
        JOIN `{PROJECT_ID}.{DATASET_ID}.proposals` p
          ON vp.proposal_id = p.id
        JOIN `{PROJECT_ID}.{DATASET_ID}.governing_bodies` gb
          ON p.governing_body_id = gb.id
        WHERE gb.sagebase_id = '{KYOTO_GOV_ID}'
          AND (p.voted_date >= '2023-05-01' OR p.submitted_date >= '2023-05-01')
    """
    try:
        res_p = list(client.query(query_pol_votes).result())[0]
        print(f"\n【3. 議員別賛否 (proposal_vote_politicians)】")
        print(f"- 現任期の議員採決レコード数: {res_p.total_votes:,} 件")
        print(f"- 採決データがある議案件数: {res_p.voted_proposals:,} 件")
    except Exception as e:
        print(f"❌ proposal_vote_politicians エラー: {e}")

    # 4. サンプルレコードの表示（取得できた場合）
    sample_query = f"""
        SELECT 
            p.title,
            p.voted_date,
            p.deliberation_result
        FROM `{PROJECT_ID}.{DATASET_ID}.proposals` p
        JOIN `{PROJECT_ID}.{DATASET_ID}.governing_bodies` gb
          ON p.governing_body_id = gb.id
        WHERE gb.sagebase_id = '{KYOTO_GOV_ID}'
          AND p.voted_date >= '2023-05-01'
        ORDER BY p.voted_date DESC
        LIMIT 3
    """
    try:
        samples = list(client.query(sample_query).result())
        if samples:
            print(f"\n【4. 最新の議案サンプル（直近3件）】")
            for s in samples:
                print(f"- [{s.voted_date}] {s.title} （結果: {s.deliberation_result}）")
    except Exception as e:
        print(f"❌ sample query エラー: {e}")

if __name__ == "__main__":
    check_kyoto_records()