from google.cloud import bigquery

def main():
    client = bigquery.Client(project="gen-lang-client-0253904061")
    
    # 2023年5月以降の大阪市会の全会議名・会議数・総発言数を集計
    q = """
        SELECT 
            m.name AS meeting_name_pattern,
            COUNT(DISTINCT m.id) AS meeting_count,
            COUNT(c.id) AS statement_count,
            MIN(m.date) AS earliest_date,
            MAX(m.date) AS latest_date
        FROM `gen-lang-client-0253904061.sagebase_data.meetings` m
        JOIN `gen-lang-client-0253904061.sagebase_data.conferences` conf ON m.conference_id = conf.id
        LEFT JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON m.id = min.meeting_id
        LEFT JOIN `gen-lang-client-0253904061.sagebase_data.conversations` c ON min.id = c.minutes_id
        WHERE conf.governing_body_id = 532 
          AND m.date >= '2023-05-01'
        GROUP BY meeting_name_pattern
        ORDER BY statement_count DESC
    """
    
    print("🔍 大阪市会（2023-05-01〜現在）の会議体一覧を集計中...\n")
    results = list(client.query(q).result())
    
    print(f"{'会議名 / パターン':<45} | {'会議数':<6} | {'総発言数':<8} | {'期間'}")
    print("-" * 85)
    
    total_meetings = 0
    total_stmts = 0
    for r in results:
        total_meetings += r.meeting_count
        total_stmts += r.statement_count
        name = r.meeting_name_pattern[:43]
        period = f"{r.earliest_date} ~ {r.latest_date}"
        print(f"{name:<45} | {r.meeting_count:<6} | {r.statement_count:<8} | {period}")
        
    print("-" * 85)
    print(f"合計: {len(results)} 種類の会議体 / {total_meetings} 会議 / {total_stmts:,} 発言")

if __name__ == "__main__":
    main()
