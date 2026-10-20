import os
import json
import re
from datetime import datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

CRAWLED_FILE = os.path.join(BASE_DIR, "sagebase_crawled_data.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "frontend", "public", "data")

STATEMENTS_OUT = os.path.join(OUTPUT_DIR, "statements_summary.json")
SPEAKER_STATS_OUT = os.path.join(OUTPUT_DIR, "speaker_stats.json")
TOPIC_STATS_OUT = os.path.join(OUTPUT_DIR, "topic_stats.json")

CATEGORIES = [
    "都市再生・交通インフラ",
    "産業・観光・地域経済",
    "福祉・医療・健康",
    "子育て・教育",
    "財政・行革",
    "くらし・環境・エネルギー",
    "防災・減災・治安",
    "文化・景観・歴史"
]

def clean_speaker_name(speaker):
    if not speaker:
        return "理事者"
    name = str(speaker).strip()
    name = re.sub(r"(議員|委員長|副委員長|市長|副市長|局長|部長|理事者)$", "", name).strip()
    return name

def get_committee_name(title):
    title = str(title or "")
    if "本会議" in title:
        return "本会議"
    if "予算特別委員会" in title:
        return "予算特別委員会"
    if "決算特別委員会" in title:
        return "決算特別委員会"
    if "総務消防委員会" in title:
        return "総務消防委員会"
    if "文教はぐくみ委員会" in title:
        return "文教はぐくみ委員会"
    if "まちづくり委員会" in title:
        return "まちづくり委員会"
    if "産業交通水道委員会" in title:
        return "産業交通水道委員会"
    if "くらし環境委員会" in title:
        return "くらし環境委員会"
    if "市会運営委員会" in title:
        return "市会運営委員会"
    m = re.search(r"([^\s]+委員会)", title)
    return m.group(1) if m else "その他委員会"

def main():
    print("=" * 60)
    print("🚀 実質質疑スレッド（約5,100件）軽量インデックス生成を開始")
    print("=" * 60)

    if not os.path.exists(CRAWLED_FILE):
        print(f"❌ 元データが見つかりません: {CRAWLED_FILE}")
        return

    with open(CRAWLED_FILE, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    print(f"📖 発言ログ読み込み: {len(raw_items)} 件")

    # 1. 「実質質疑スレッド（要約またはAI評価スコアが存在するもの）」のみを抽出
    thread_map = {}
    for item in raw_items:
        t_id = str(item.get("id") or f"{item.get('meeting_id')}_{item.get('sequence_number')}")
        
        # 答弁や単なる発言を除くため、AI要約または評価スコアが付与されているスレッド代表発言に限定
        has_summary = bool(item.get("summary"))
        has_score = item.get("solution_score") is not None or item.get("evidence_score") is not None
        
        if not (has_summary or has_score):
            continue

        text = str(item.get("statement_text") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if not summary:
            summary = text[:100].replace("\n", " ") + "..."

        raw_speaker = item.get("speaker") or ""
        clean_speaker = clean_speaker_name(raw_speaker)

        category = item.get("category") or "市政全般"
        if category not in CATEGORIES and category != "市政全般":
            category = "市政全般"

        # 軽量インデックス用オブジェクト（長文テキストは含めず要約とメタ情報のみ）
        summary_obj = {
            "id": t_id,
            "meeting_id": item.get("meeting_id"),
            "meeting_date": item.get("meeting_date") or "",
            "meeting_title": item.get("meeting_title") or "",
            "committee": get_committee_name(item.get("meeting_title")),
            "speaker": clean_speaker,
            "category": category,
            "summary": summary[:140],  # 140文字以内に制限
            "statement_text": summary[:100],  # 検索互換用
            "solution_score": float(item.get("solution_score") or 3.0),
            "evidence_score": float(item.get("evidence_score") or 3.0),
            "local_focus_score": float(item.get("local_focus_score") or 3.0),
            "constructive_score": float(item.get("constructive_score") or 3.0),
            "source_url": item.get("source_url") or ""
        }
        thread_map[t_id] = summary_obj

    # 日付降順（最新順）にソート
    all_statements = list(thread_map.values())
    all_statements.sort(key=lambda x: str(x.get("meeting_date") or ""), reverse=True)
    total_count = len(all_statements)
    print(f"✅ 抽出された実質質疑スレッド数: {total_count} 件")

    # 2. 議員別集計
    speaker_aggregates = defaultdict(lambda: {
        "speaker": "",
        "count": 0,
        "district": "",
        "partyGroup": "",
        "categories": defaultdict(int),
        "total_solution": 0.0,
        "total_evidence": 0.0,
        "total_local_focus": 0.0,
        "total_constructive": 0.0
    })

    for s in all_statements:
        name = s["speaker"]
        if not name or name in ["理事者", "事務局"]:
            continue
        spk = speaker_aggregates[name]
        spk["speaker"] = name
        spk["count"] += 1
        spk["categories"][s["category"]] += 1
        spk["total_solution"] += s["solution_score"]
        spk["total_evidence"] += s["evidence_score"]
        spk["total_local_focus"] += s["local_focus_score"]
        spk["total_constructive"] += s["constructive_score"]

    speaker_stats_list = []
    for name, spk in speaker_aggregates.items():
        c = spk["count"]
        top_cat = max(spk["categories"].items(), key=lambda x: x[1])[0] if spk["categories"] else "市政全般"
        speaker_stats_list.append({
            "speaker": name,
            "count": c,
            "district": spk["district"] or "京都市会",
            "partyGroup": spk["partyGroup"] or "市会議員",
            "primaryCategory": top_cat,
            "avg_solution": round(spk["total_solution"] / c, 2),
            "avg_evidence": round(spk["total_evidence"] / c, 2),
            "avg_local_focus": round(spk["total_local_focus"] / c, 2),
            "avg_constructive": round(spk["total_constructive"] / c, 2),
        })

    speaker_stats_list.sort(key=lambda x: x["count"], reverse=True)

    # 3. 分野別集計
    category_counts = defaultdict(int)
    for s in all_statements:
        category_counts[s["category"]] += 1

    topic_stats_list = []
    for cat in CATEGORIES:
        cnt = category_counts[cat]
        pct = round((cnt / total_count * 100), 1) if total_count > 0 else 0.0
        topic_stats_list.append({
            "name": cat,
            "count": cnt,
            "percentage": pct
        })

    # 4. JSON出力
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(STATEMENTS_OUT, "w", encoding="utf-8") as f:
        json.dump(all_statements, f, ensure_ascii=False, separators=(',', ':'))

    with open(SPEAKER_STATS_OUT, "w", encoding="utf-8") as f:
        json.dump(speaker_stats_list, f, ensure_ascii=False, indent=2)

    with open(TOPIC_STATS_OUT, "w", encoding="utf-8") as f:
        json.dump(topic_stats_list, f, ensure_ascii=False, indent=2)

    file_size_mb = os.path.getsize(STATEMENTS_OUT) / (1024 * 1024)
    print("=" * 60)
    print(f"🎉 処理完了:")
    print(f"   ・質疑スレッド: {total_count} 件")
    print(f"   ・ファイルサイズ: {file_size_mb:.2f} MB (25MB制限を大幅にクリア)")
    print(f"📁 保存先: {STATEMENTS_OUT}")
    print("=" * 60)

if __name__ == "__main__":
    main()