import json
import re
from pathlib import Path
from google.cloud import bigquery
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / "data-pipeline" / ".env")

SUMMARY_FILE = PROJECT_ROOT / "frontend" / "public" / "data" / "osaka_statements_summary.json"
TIMELINES_DIR = PROJECT_ROOT / "frontend" / "public" / "data" / "osaka_timelines"
TIMELINES_DIR.mkdir(parents=True, exist_ok=True)

OFFICIAL_ROLES = [
    "市長", "副市長", "局長", "区長", "部長", "室長", "課長", "次長", 
    "理事者", "教育長", "技監", "参事", "主査", "担当部長", "担当課長", "副首都"
]

PROCEDURAL_PATTERNS = [
    r"君登壇\）$",
    r"御異議なしと認め",
    r"お諮りいたします",
    r"動議に御異議",
    r"動議を提出いたします",
    r"(説明|見解表明|報告)は以上であります",
    r"理事者の(説明|答弁)を(求め|許し)ます",
    r"これより(議事に入り|委員会を再開|採決に入り)",
    r"審査の報告は終了",
    r"本日の日程は以上で終了",
    r"暫時休憩",
    r"協議会を(開き|閉じ)",
    r"撮影の?(申出|申し出|許可)",
    r"開会に先立ち",
    r"原案のとおり可決"
]
PROCEDURAL_REGEX = re.compile("|".join(PROCEDURAL_PATTERNS))

def is_official(speaker):
    return any(role in speaker for role in OFFICIAL_ROLES)

def is_procedural(text):
    text_clean = text.replace("\n", " ").strip()
    return len(text_clean) < 120 and bool(PROCEDURAL_REGEX.search(text_clean))

def main():
    print("=" * 60)
    print("🚀 大阪市会 タイムライン（会話ログ）一括生成パイプライン")
    print("=" * 60)

    if not SUMMARY_FILE.exists():
        print(f"❌ {SUMMARY_FILE} が見つかりません。")
        return

    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        summary_data = json.load(f)

    # 1. sequence_number の補完
    updated = False
    target_meetings = set()
    for item in summary_data:
        if "sequence_number" not in item:
            parts = item.get("id", "").split("_")
            if len(parts) >= 3 and parts[-1].isdigit():
                item["sequence_number"] = int(parts[-1])
                updated = True
        mid = str(item.get("meeting_id", "")).strip()
        if mid:
            target_meetings.add(mid)

    if updated:
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        print(f"✅ {SUMMARY_FILE} に sequence_number を補完しました。")

    print(f"🎯 対象会議数: {len(target_meetings)} 件 / 対象スレッド数: {len(summary_data)} 件")

    # 2. BigQuery から対象会議の発言をまとめて取得
    client = bigquery.Client(project="gen-lang-client-0253904061")
    meeting_ids_str = ", ".join(target_meetings)

    print("📥 BigQuery から対象会議の発言データを一括取得中...")
    query = f"""
        SELECT 
            CAST(min.meeting_id AS STRING) AS meeting_id,
            c.sequence_number,
            c.speaker_name AS speaker,
            c.comment AS statement_text
        FROM `gen-lang-client-0253904061.sagebase_data.conversations` c
        JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON c.minutes_id = min.id
        WHERE min.meeting_id IN ({meeting_ids_str})
        ORDER BY min.meeting_id, c.sequence_number ASC
    """
    
    rows = list(client.query(query).result())
    print(f"✅ 発言レコード取得完了: {len(rows):,} 件")

    # 会議ごとの発言マップ
    meetings_map = {}
    for r in rows:
        mid = r["meeting_id"]
        if mid not in meetings_map:
            meetings_map[mid] = []
        meetings_map[mid].append({
            "sequence_number": int(r["sequence_number"]),
            "speaker": r["speaker"] or "",
            "statement_text": r["statement_text"] or ""
        })

    # 3. 各会議のタイムライン（各質疑ごとの前天文脈・答弁往復）を構造化
    # 構造: { str(sequence_number): [ { sequence_number, speaker, statement_text, is_target, is_admin, is_short_procedural }, ... ] }
    timelines_by_meeting = {mid: {} for mid in target_meetings}

    for item in summary_data:
        mid = str(item.get("meeting_id"))
        seq = item.get("sequence_number")
        target_spk = item.get("speaker", "").strip()

        if mid not in meetings_map or seq is None:
            continue

        stmt_list = meetings_map[mid]
        target_idx = next((i for i, s in enumerate(stmt_list) if s["sequence_number"] == seq), None)
        if target_idx is None:
            continue

        # 直前の文脈1件（委員長・議長の指名等）を含める
        start_idx = max(0, target_idx - 1)
        conversation = []

        # 直前発言の追加
        if start_idx < target_idx:
            prev_s = stmt_list[start_idx]
            prev_txt = prev_s["statement_text"]
            conversation.append({
                "sequence_number": prev_s["sequence_number"],
                "speaker": prev_s["speaker"],
                "statement_text": prev_txt,
                "is_target": False,
                "is_admin": is_official(prev_s["speaker"]),
                "is_short_procedural": is_procedural(prev_txt)
            })

        # 質疑本体と答弁往復の抽出
        for s in stmt_list[target_idx:]:
            s_seq = s["sequence_number"]
            spk = s["speaker"]
            txt = s["statement_text"]
            is_target_speaker = (target_spk in spk) or (spk in target_spk)
            admin = is_official(spk)

            # 別議員の新しい質問に移ったら打ち切り
            if s_seq > seq and not admin and not is_target_speaker and len(txt) > 50:
                break

            conversation.append({
                "sequence_number": s_seq,
                "speaker": spk,
                "statement_text": txt,
                "is_target": (s_seq == seq),
                "is_admin": admin,
                "is_short_procedural": is_procedural(txt)
            })

            # 最大20往復でリミット
            if len(conversation) >= 20:
                break

        timelines_by_meeting[mid][str(seq)] = conversation

    # 4. JSONファイルとして書き出し
    saved_count = 0
    for mid, t_data in timelines_by_meeting.items():
        if t_data:
            out_file = TIMELINES_DIR / f"{mid}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(t_data, f, ensure_ascii=False, indent=2)
            saved_count += 1

    print(f"🎉 タイムラインファイル生成完了: {saved_count} 会議分を {TIMELINES_DIR} に出力しました。")

if __name__ == "__main__":
    main()
