import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "data-pipeline"))

try:
    from yokohama_adapter import YokohamaAdapter
except ImportError:
    YokohamaAdapter = None

try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None

def load_councilors(city_code):
    stats_filename = f"{city_code}_speaker_stats.json" if city_code != "kyoto" else "speaker_stats.json"
    stats_path = PROJECT_ROOT / "frontend" / "public" / "data" / stats_filename
    
    councilors = set()
    if stats_path.exists():
        with open(stats_path, "r", encoding="utf-8") as f:
            stats = json.load(f)
        for s in stats:
            name = (s.get("speaker") or s.get("name") or "").strip()
            if name:
                clean_name = re.sub(r"[\s\u3000]+", "", name)
                councilors.add(name)
                councilors.add(clean_name)
    return councilors

def fetch_raw_statements(city_code):
    cache_path = PROJECT_ROOT / "data-pipeline" / f"{city_code}_raw_statements.json"
    if cache_path.exists():
        print(f"📦 [キャッシュ検出] {cache_path.name} から発言データを読み込みます...")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    if city_code == "yokohama":
        if YokohamaAdapter is None or bigquery is None:
            raise RuntimeError("YokohamaAdapter または google.cloud.bigquery がインポートできません。")
        client = bigquery.Client()
        raw = YokohamaAdapter.fetch_data(client)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
        print(f"💾 発言データを次回高速化のため {cache_path.name} に保存しました。")
        return raw
    elif city_code == "kyoto":
        kyoto_path = PROJECT_ROOT / "data-pipeline" / "sagebase_crawled_data.json"
        with open(kyoto_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise ValueError(f"未対応の都市コードです: {city_code}")

def build_timelines(city_code):
    print("=" * 60)
    print(f"🚀 [{city_code.upper()}] 質疑文脈タイムライン生成を開始します")
    print("=" * 60)
    
    summary_filename = f"{city_code}_statements_summary.json" if city_code != "kyoto" else "statements_summary.json"
    summary_path = PROJECT_ROOT / "frontend" / "public" / "data" / summary_filename
    
    if not summary_path.exists():
        raise FileNotFoundError(f"要約データが見つかりません: {summary_path}")
        
    with open(summary_path, "r", encoding="utf-8") as f:
        summary_statements = json.load(f)
    print(f"✅ 要約データ読み込み: {len(summary_statements):,} 件の質疑")

    valid_councilors = load_councilors(city_code)
    print(f"✅ 議員名簿読み込み: {len(valid_councilors):,} 名（正規化含む）")

    raw_statements = fetch_raw_statements(city_code)
    print(f"✅ 原本発言データ読み込み: {len(raw_statements):,} 件")

    print("📊 会議ごとに発言をグループ化・ソート中...")
    meetings_map = {}
    for s in raw_statements:
        mid = str(s.get("meeting_id") or "")
        if not mid:
            continue
        meetings_map.setdefault(mid, []).append(s)

    for mid in meetings_map:
        meetings_map[mid].sort(key=lambda x: int(x.get("sequence_number") or 0))

    print("🧵 各質疑の文脈（タイムライン）を抽出中...")
    meetings_timelines = {}
    total_threads = 0
    skipped_threads = 0

    for stmt in summary_statements:
        mid = str(stmt.get("meeting_id") or "")
        if not mid or mid not in meetings_map:
            skipped_threads += 1
            continue

        raw_seq = stmt.get("sequence_number")
        if not raw_seq and stmt.get("id"):
            parts = str(stmt["id"]).split("_")
            raw_seq = parts[-1]
        
        try:
            target_seq = int(raw_seq)
        except (ValueError, TypeError):
            skipped_threads += 1
            continue

        target_speaker = (stmt.get("speaker") or "").strip()
        meeting_list = meetings_map[mid]

        target_idx = -1
        for idx, s in enumerate(meeting_list):
            if int(s.get("sequence_number") or 0) == target_seq:
                target_idx = idx
                break

        if target_idx == -1:
            skipped_threads += 1
            continue

        start = max(0, target_idx - 1)
        collected = []
        if start < target_idx:
            collected.append(meeting_list[start])

        clean_target = re.sub(r"[\s\u3000]+", "", target_speaker)
        for s in meeting_list[target_idx:]:
            seq = int(s.get("sequence_number") or 0)
            spk = re.sub(r"[\s\u3000]+", "", s.get("speaker") or "")
            txt = (s.get("statement_text") or "").strip()

            is_councilor = spk in valid_councilors or "議員" in s.get("speaker", "") or "委員" in s.get("speaker", "")
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

            is_councilor = clean_spk in valid_councilors or "議員" in spk or "委員" in spk
            is_admin = not is_councilor

            is_procedural = (
                (len(txt) <= 25 and (txt.endswith("。") or txt.endswith("どうぞ。") or txt.endswith("願います。"))) or
                ("休憩" in txt and "再開" in txt) or
                txt.startswith("［") or
                "進行いたします" in txt or
                "お諮りいたします" in txt or
                "さよう決定いたします" in txt
            )

            formatted_context.append({
                "sequence_number": seq,
                "speaker": spk,
                "statement_text": txt,
                "is_target": (seq == target_seq),
                "is_admin": is_admin,
                "is_short_procedural": is_procedural
            })

        meetings_timelines.setdefault(mid, {})[str(target_seq)] = formatted_context
        total_threads += 1

    timelines_dir_name = f"{city_code}_timelines" if city_code != "kyoto" else "timelines"
    timelines_dir = PROJECT_ROOT / "frontend" / "public" / "data" / timelines_dir_name

    print(f"📁 会議別個別JSONファイルを出力中 -> {timelines_dir}")
    if timelines_dir.exists():
        shutil.rmtree(timelines_dir)
    timelines_dir.mkdir(parents=True, exist_ok=True)

    for mid, seq_map in meetings_timelines.items():
        file_path = timelines_dir / f"{mid}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(seq_map, f, ensure_ascii=False, separators=(',', ':'))

    print("=" * 60)
    print(f"🎉 完了: 全 {len(meetings_timelines)} 会議（計 {total_threads:,} 件の質疑タイムライン）を分割ファイルとして生成しました！")
    if skipped_threads > 0:
        print(f"ℹ️ スキップされた質疑: {skipped_threads} 件")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="質疑文脈タイムライン生成")
    parser.add_argument("--city", required=True, choices=["kyoto", "osaka", "nagoya", "yokohama"], help="対象都市コード")
    args = parser.parse_args()
    build_timelines(args.city)
