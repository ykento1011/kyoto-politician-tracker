import json
import os
import re
import hashlib
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CRAWLED_PATH = os.path.join(BASE_DIR, "sagebase_crawled_data.json")
SUMMARY_PATH = os.path.join(BASE_DIR, "..", "frontend", "public", "data", "statements_summary.json")
TIMELINES_DIR = os.path.join(BASE_DIR, "..", "frontend", "public", "data", "timelines")
OLD_FILE = os.path.join(BASE_DIR, "..", "frontend", "public", "data", "timeline_contexts.json")

# 💡 制限オーバーの原因だった旧巨大ファイルを削除
if os.path.exists(OLD_FILE):
    os.remove(OLD_FILE)
    print(f"旧ファイル {OLD_FILE} を削除しました。")

VALID_COUNCILORS = {
    "青野仁志", "赤阪仁", "あさのえりか", "浅野枝里加", "天方浩之", "天方ひろゆき", "井上けんじ", "井上耕司",
    "井坂博文", "伊佐坂博文", "今枝徳蔵", "宇佐美賢一", "江村理紗", "大津裕太", "大西けんじ",
    "大西ケンジ", "岡田ちか", "小田史絵", "加藤あい", "神谷修平", "川那部守", "河合ようこ",
    "木村順吉", "久保田正紀", "蔵田共子", "くらた共子", "国本友利", "小林あかね", "小林貴美子",
    "小林琢児", "こうち大輔", "河内大輔", "桜井泰広", "しなの浩世", "下村あきら", "菅谷浩樹",
    "鈴木マサホ", "鈴木正穂", "高神晃", "田中たかのり", "田中学", "平良竜成", "中野洋一",
    "西山信昌", "西村よしなお", "橋村芳和", "長谷川拓也", "兵藤しんいち", "平田圭", "平山たかお",
    "福田陽介", "ほり信子", "松井ようこ", "増成竜治", "増成竜夫", "松平峰男", "椋田隆知",
    "村山祥栄", "森川央", "森田守", "安井つとむ", "やまね智史", "山手守", "山本陽子", "吉田孝雄"
}

print("1. データを読み込み中...")
with open(CRAWLED_PATH, "r", encoding="utf-8") as f:
    raw_statements = json.load(f)

with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
    summary_statements = json.load(f)

print("2. 会議ごとに発言をインデックス化中...")
meetings_map = {}
for s in raw_statements:
    mid = s.get("meeting_id") or s.get("meeting_title")
    if not mid:
        continue
    if mid not in meetings_map:
        meetings_map[mid] = []
    meetings_map[mid].append(s)

for mid in meetings_map:
    meetings_map[mid].sort(key=lambda x: int(x.get("sequence_number") or 0))

print("3. 会議単位でタイムライン文脈を抽出中...")
# 会議ID -> { seq_number: formatted_context }
meetings_timelines = {}
total_threads = 0

for stmt in summary_statements:
    mid = stmt.get("meeting_id")
    if not mid:
        mtitle = stmt.get("meeting_title")
        if not mtitle:
            continue
        mid = "mtg_" + hashlib.md5(mtitle.encode('utf-8')).hexdigest()

    target_seq = int(stmt.get("sequence_number") or 0)
    target_speaker = (stmt.get("speaker") or "").strip()

    lookup_key = stmt.get("meeting_id") or stmt.get("meeting_title")
    if not lookup_key or target_seq == 0 or lookup_key not in meetings_map:
        continue

    meeting_list = meetings_map[lookup_key]
    
    target_idx = -1
    for idx, s in enumerate(meeting_list):
        if int(s.get("sequence_number") or 0) == target_seq:
            target_idx = idx
            break

    if target_idx == -1:
        continue

    start = max(0, target_idx - 1)
    collected = []
    if start < target_idx:
        collected.append(meeting_list[start])

    for s in meeting_list[target_idx:]:
        seq = int(s.get("sequence_number") or 0)
        spk = re.sub(r"[\s\u3000]+", "", s.get("speaker") or "")
        txt = (s.get("statement_text") or "").strip()

        is_councilor = spk in VALID_COUNCILORS or "議員" in s.get("speaker", "")
        clean_target = re.sub(r"[\s\u3000]+", "", target_speaker)

        if seq > target_seq and is_councilor and spk != clean_target and len(txt) > 30:
            break

        collected.append(s)
        if len(collected) >= 12:
            break

    formatted_context = []
    for s in collected:
        seq = int(s.get("sequence_number") or 0)
        spk = (s.get("speaker") or "").strip()
        txt = (s.get("statement_text") or "").strip()
        clean_spk = re.sub(r"[\s\u3000]+", "", spk)

        is_councilor = clean_spk in VALID_COUNCILORS or "議員" in spk
        is_admin = not is_councilor

        is_procedural = (
            (len(txt) <= 25 and (txt.endswith("。") or txt.endswith("どうぞ。") or txt.endswith("願います。"))) or
            ("休憩" in txt and "再開" in txt) or
            txt.startswith("［") or
            "進行いたします" in txt
        )

        formatted_context.append({
            "sequence_number": seq,
            "speaker": spk,
            "statement_text": txt,
            "is_target": (seq == target_seq),
            "is_admin": is_admin,
            "is_short_procedural": is_procedural
        })

    if mid not in meetings_timelines:
        meetings_timelines[mid] = {}

    meetings_timelines[mid][str(target_seq)] = formatted_context
    total_threads += 1

print(f"4. 会議ごとの個別JSONファイルを出力中 -> {TIMELINES_DIR}")
if os.path.exists(TIMELINES_DIR):
    shutil.rmtree(TIMELINES_DIR)
os.makedirs(TIMELINES_DIR, exist_ok=True)

for mid, seq_map in meetings_timelines.items():
    file_path = os.path.join(TIMELINES_DIR, f"{mid}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(seq_map, f, ensure_ascii=False, separators=(',', ':'))

print(f"完了: 全 {len(meetings_timelines)} 会議（計 {total_threads} 件の質疑）を分割ファイルとして生成しました！")