import os
import sys
import re
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist" / "data"

PLEDGES_EXTRACTED = BASE_DIR / "data" / "nagoya_councilor_pledges.json"
STATS_FILE = FRONTEND_DATA / "nagoya_speaker_stats.json"
STATEMENTS_FILE = FRONTEND_DATA / "nagoya_statements_summary.json"
VOTES_FILE = FRONTEND_DATA / "nagoya_votes_summary.json"

OUTPUT_FILES = [
    FRONTEND_DATA / "pledge_tracker_nagoya.json",
    FRONTEND_DIST / "pledge_tracker_nagoya.json"
]

def main():
    print("=== 名古屋市議 看板公約トラッカー結合パイプライン ===")
    if not PLEDGES_EXTRACTED.exists() or not STATS_FILE.exists():
        print("⚠️ 必要なデータファイルが見つかりません。")
        return

    extracted_pledges = json.loads(PLEDGES_EXTRACTED.read_text(encoding="utf-8"))
    stats = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    statements = json.loads(STATEMENTS_FILE.read_text(encoding="utf-8")) if STATEMENTS_FILE.exists() else []

    stmts_by_speaker = {}
    for s in statements:
        spk = s.get("speaker", "").strip()
        stmts_by_speaker.setdefault(spk, []).append(s)

    pledges_by_speaker = {item["speaker"]: item for item in extracted_pledges if item.get("is_incumbent_elected")}

    def find_evidence(speaker, target_issue, headline):
        user_stmts = stmts_by_speaker.get(speaker, [])
        keywords = [k for k in re.split(r'[（）\s、。・/]', f"{target_issue} {headline}") if len(k) >= 2]
        stop_words = {"推進", "拡充", "実現", "目指す", "対策", "支援", "強化", "向上", "整備", "見直し"}
        keywords = [k for k in keywords if k not in stop_words]
        
        hits = []
        for s in user_stmts:
            q_text = s.get("question_text", "")
            matched = [k for k in keywords if k in q_text]
            if matched:
                hits.append({
                    "statement_id": s.get("id"),
                    "date": s.get("meeting_date", ""),
                    "meeting_title": s.get("meeting_title", ""),
                    "summary": s.get("question_summary") or q_text[:120] + "...",
                    "matched_keywords": matched
                })
                if len(hits) >= 3:
                    break
        return hits

    councilors = []
    for s in stats:
        spk = s.get("speaker")
        c_pledge = pledges_by_speaker.get(spk, {})
        raw_pledges = c_pledge.get("pledges", [])
        bulletin_url = c_pledge.get("bulletin_url", "")

        built = []
        for idx, p in enumerate(raw_pledges):
            evidences = find_evidence(spk, p.get("target_issue", ""), p.get("headline", ""))
            built.append({
                "id": f"p_{idx+1}",
                "category": p.get("category", "くらし・環境・エネルギー"),
                "target_issue": p.get("target_issue", ""),
                "headline": p.get("headline", ""),
                "stance": p.get("stance", "推進"),
                "exact_quote": p.get("exact_quote", ""),
                "bulletin_url": bulletin_url,
                "progress_status": "in_progress" if evidences else "monitoring",
                "progress_label": f"市議会で{len(evidences)}回 質疑・論戦を展開" if evidences else "議会での関連質疑を継続監視中",
                "evidences": evidences
            })

        councilors.append({
            "speaker": spk,
            "district": s.get("district", ""),
            "party": s.get("partyGroup", ""),
            "role": s.get("role", "市会議員"),
            "bulletin_url": bulletin_url,
            "pledge_count": len(built),
            "pledges": built
        })

    payload = {
        "metadata": {
            "city": "nagoya",
            "city_name": "名古屋市",
            "term": "2023-2027（令和5年4月改選）",
            "election_date": "2023-04-09",
            "official_bulletin_source": "名古屋市選挙管理委員会 公式選挙公報（国立国会図書館WARPアーカイブ）",
            "total_councilors": len(councilors),
            "total_pledges": sum(len(c["pledges"]) for c in councilors),
            "updated_at": time.strftime("%Y-%m-%d")
        },
        "councilors": councilors
    }

    for out_p in OUTPUT_FILES:
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 保存完了: {out_p.relative_to(PROJECT_ROOT)}")

if __name__ == "__main__":
    main()
