import json, os, sys
from pathlib import Path
from google.cloud import bigquery

def dump_meeting_stmts(client, meeting_id, title):
    print(f"\n==================================================")
    print(f"🏛️ 会議: {title} (ID: {meeting_id})")
    print(f"==================================================")
    q = f"""
        SELECT c.sequence_number, c.speaker_name, c.speaker_header, SUBSTR(c.comment, 1, 90) AS snippet
        FROM `gen-lang-client-0253904061.sagebase_data.conversations` c
        JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON c.minutes_id = min.id
        WHERE min.meeting_id = {meeting_id}
        ORDER BY c.sequence_number ASC
        LIMIT 40
    """
    rows = list(client.query(q).result())
    print(f"取得件数: {len(rows)} 件")
    for r in rows:
        snip = (r.snippet or "").replace('\n', ' ')
        spk = r.speaker_name or "不明"
        hdr = r.speaker_header or "None"
        print(f"[{r.sequence_number:2d}] {spk:<12} ({hdr}): {snip}...")

def main():
    client = bigquery.Client(project="gen-lang-client-0253904061")
    
    # 1. 直前の ID: 5336584 の全容
    dump_meeting_stmts(client, 5336584, "令和８年５・６月定例会（市政改革）")
    
    # 2. 発言数が30件以上ある本番質疑の会議を1件特定
    q_dense = """
        SELECT m.id AS meeting_id, m.name AS meeting_name, COUNT(c.id) AS stmt_count
        FROM `gen-lang-client-0253904061.sagebase_data.meetings` m
        JOIN `gen-lang-client-0253904061.sagebase_data.conferences` conf ON m.conference_id = conf.id
        JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON m.id = min.meeting_id
        JOIN `gen-lang-client-0253904061.sagebase_data.conversations` c ON min.id = c.minutes_id
        WHERE conf.governing_body_id = 532 
          AND m.name LIKE '%常任委員会%'
        GROUP BY m.id, m.name
        HAVING stmt_count >= 30
        ORDER BY m.id DESC
        LIMIT 1
    """
    dense_mtg = list(client.query(q_dense).result())
    if dense_mtg:
        dump_meeting_stmts(client, dense_mtg[0].meeting_id, f"{dense_mtg[0].meeting_name} (総発言数: {dense_mtg[0].stmt_count})")

if __name__ == "__main__":
    main()
