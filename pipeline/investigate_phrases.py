from google.cloud import bigquery
import re
from collections import Counter

def main():
    client = bigquery.Client(project="gen-lang-client-0253904061")
    
    print("🔍 大阪市会（現任期）の頻出フレーズ・発言開始パターンを調査中...\n")
    
    # 議事進行・短文発言の傾向を掴むため、文字数100文字以下の発言を抽出
    q = """
        SELECT c.speaker_name, c.speaker_header, SUBSTR(c.comment, 1, 80) AS start_phrase
        FROM `gen-lang-client-0253904061.sagebase_data.conversations` c
        JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON c.minutes_id = min.id
        JOIN `gen-lang-client-0253904061.sagebase_data.meetings` m ON min.meeting_id = m.id
        JOIN `gen-lang-client-0253904061.sagebase_data.conferences` conf ON m.conference_id = conf.id
        WHERE conf.governing_body_id = 532 
          AND (m.name LIKE '%委員会%' OR m.name LIKE '%定例会%' OR m.name LIKE '%本会議%')
          AND m.name NOT LIKE '%市会運営%'
          AND m.date >= '2023-05-01'
          AND LENGTH(c.comment) <= 120
    """
    
    rows = list(client.query(q).result())
    print(f"対象発言数（短文・進行系候補）: {len(rows):,} 件")
    
    # フレーズの頻出パターンを集計
    phrase_counter = Counter()
    for r in rows:
        text = (r.start_phrase or "").strip().replace("\n", " ")
        # 冒頭の定型的な文節を抽出（30文字程度）
        phrase = text[:35]
        phrase_counter[phrase] += 1
        
    print("\n【大阪市会で最も頻出する短文・進行フレーズ Top 40】")
    print("-" * 70)
    for phrase, count in phrase_counter.most_common(40):
        print(f"{count:4d} 回 : {phrase}")

if __name__ == "__main__":
    main()
