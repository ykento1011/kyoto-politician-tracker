import json, os, sys
from pathlib import Path
from google.cloud import bigquery

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def main():
    client = bigquery.Client(project="gen-lang-client-0253904061")
    # 質問が噛み合っていなかった西崎照明議員の会議を調査
    q = """
        SELECT c.sequence_number, c.speaker_name, c.speaker_header, SUBSTR(c.comment, 1, 100) AS text_snippet
        FROM `gen-lang-client-0253904061.sagebase_data.conversations` c
        JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON c.minutes_id = min.id
        JOIN `gen-lang-client-0253904061.sagebase_data.meetings` m ON min.meeting_id = m.id
        WHERE c.speaker_name LIKE '%西崎%'
        ORDER BY m.date DESC, c.sequence_number ASC
        LIMIT 1
    """
    rows = list(client.query(q).result())
    if not rows:
        print("該当なし")
        return
        
    target_seq = rows[0].sequence_number
    # その発言の前後5件を表示
    q_context = f"""
        SELECT c.sequence_number, c.speaker_name, c.speaker_header, SUBSTR(c.comment, 1, 120) AS text_snippet
        FROM `gen-lang-client-0253904061.sagebase_data.conversations` c
        JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON c.minutes_id = min.id
        WHERE min.meeting_id = (
            SELECT min2.meeting_id FROM `gen-lang-client-0253904061.sagebase_data.conversations` c2
            JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min2 ON c2.minutes_id = min2.id
            WHERE c2.speaker_name LIKE '%西崎%' ORDER BY c2.id DESC LIMIT 1
        )
        AND c.sequence_number BETWEEN {max(1, target_seq - 2)} AND {target_seq + 5}
        ORDER BY c.sequence_number ASC
    """
    print(f"=== 西崎議員の発言 (Seq: {target_seq}) 前後の生データ ===")
    for r in client.query(q_context).result():
        snippet = r.text_snippet.replace('\n', ' ')
        print(f"[{r.sequence_number}] {r.speaker_name} ({r.speaker_header}): {snippet}...")

if __name__ == "__main__":
    main()
