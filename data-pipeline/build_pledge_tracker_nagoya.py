import json
import re
import sys
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

def clean_str(s):
    return re.sub(r"[\s\u3000]+", "", str(s or ""))

def main():
    print("=== 名古屋市議 看板公約トラッカー結合パイプライン (京都・大阪仕様準拠) ===")
    
    # 元公約ファイルの探索
    if not PLEDGES_EXTRACTED.exists():
        fallback_pledges = FRONTEND_DATA / "pledge_tracker_nagoya_2.json"
        if fallback_pledges.exists():
            pledges_path = fallback_pledges
        else:
            print("⚠️ 公約元データが見つかりません。")
            return
    else:
        pledges_path = PLEDGES_EXTRACTED

    raw_pledge_data = json.loads(pledges_path.read_text(encoding="utf-8"))
    
    # リスト形式またはcouncilors内包形式を吸収
    if isinstance(raw_pledge_data, dict) and "councilors" in raw_pledge_data:
        councilor_pledges_list = raw_pledge_data["councilors"]
    elif isinstance(raw_pledge_data, list):
        councilor_pledges_list = raw_pledge_data
    else:
        print("⚠️ 公約データの形式が不正です。")
        return

    statements = json.loads(STATEMENTS_FILE.read_text(encoding="utf-8")) if STATEMENTS_FILE.exists() else []
    print(f"🔍 読み込み完了: 公約データ {len(councilor_pledges_list)} 名分 / 議事録発言 {len(statements)} 件")

    # 発言ログを議員ごとにプール（スペース無視で突合可能にする）
    stmts_by_speaker = {}
    for s in statements:
        spk = s.get("speaker", "").strip()
        c_spk = clean_str(spk)
        stmts_by_speaker.setdefault(c_spk, []).append(s)

    pledge_tracker = {}

    for c in councilor_pledges_list:
        raw_name = c.get("speaker") or c.get("name") or ""
        clean_name = clean_str(raw_name)
        if not clean_name:
            continue

        district = c.get("district", "")
        party = c.get("party") or c.get("partyGroup", "")
        bulletin_url = c.get("bulletin_url", "")
        raw_pledges = c.get("pledges", [])

        # 議員本人の発言ログ取得
        my_stmts = []
        for k, v in stmts_by_speaker.items():
            if clean_name in k or k in clean_name:
                my_stmts.extend(v)

        tracked_items = []
        for idx, p in enumerate(raw_pledges):
            p_id = p.get("id") or f"p_{idx+1}"
            cat = p.get("category", "くらし・環境・エネルギー")
            target_issue = p.get("target_issue", "")
            headline = p.get("headline", "")
            exact_quote = p.get("exact_quote") or p.get("quote") or ""
            stance = p.get("stance", "推進・拡充")
            item_bulletin_url = p.get("bulletin_url") or bulletin_url

            # キーワードマッチングによる関連質疑の抽出
            keywords = [k for k in re.split(r'[（）\s、。・/,]+', f"{target_issue} {headline}") if len(k) >= 2]
            stop_words = {"推進", "拡充", "実現", "目指す", "対策", "支援", "強化", "向上", "整備", "見直し"}
            keywords = [k for k in keywords if k not in stop_words]

            matched = []
            for s in my_stmts:
                s_text = s.get("statement_summary") or s.get("statement_text") or s.get("summary") or s.get("question_text") or ""
                s_cat = s.get("category", "")
                
                score = 0
                if s_cat and s_cat == cat:
                    score += 1
                for kw in keywords:
                    if kw in s_text:
                        score += 2

                if score > 0:
                    matched.append((score, s))

            # スコア順にソートして上位を抽出
            matched.sort(key=lambda x: (x[0], x[1].get("meeting_date", "")), reverse=True)
            top_stmts = [item[1] for item in matched[:5]]

            # 京都・大阪完全準拠の council_statements 整形
            council_statements = []
            for s in top_stmts:
                s_id = s.get("speech_id") or s.get("id") or ""
                s_date = s.get("meeting_date") or s.get("date") or ""
                s_committee = s.get("meeting_name") or s.get("committee") or s.get("meeting_title") or "名古屋市会 本会議・委員会"
                s_sum = s.get("statement_summary") or s.get("statement_text") or s.get("summary") or s.get("question_summary") or ""
                s_url = s.get("official_url") or s.get("source_url") or ""

                council_statements.append({
                    "date": s_date,
                    "committee": s_committee,
                    "summary": s_sum[:200] + ("..." if len(s_sum) > 200 else ""),
                    "speech_id": str(s_id),
                    "official_url": s_url
                })

            main_stmt = council_statements[0] if council_statements else None

            tracked_items.append({
                "id": f"pledge_nagoya_{clean_name}_{idx+1}",
                "headline": headline,
                "category": cat,
                "target_issue": target_issue,
                "stance": stance,
                "election_promise": {
                    "quote": exact_quote,
                    "source_name": "令和5年 名古屋市議会議員一般選挙 公式選挙公報",
                    "bulletin_url": item_bulletin_url
                },
                "council_vote": None,
                "council_statement": main_stmt,
                "council_statements": council_statements
            })

        councilor_data = {
            "district": district,
            "party": party,
            "bulletin_url": bulletin_url,
            "tracked_items": tracked_items
        }

        # 漢字名・スペースなし名の両方をキーに登録
        pledge_tracker[raw_name] = councilor_data
        if clean_name != raw_name:
            pledge_tracker[clean_name] = councilor_data

    # 各出力ファイルへ書き込み
    for out_p in OUTPUT_FILES:
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(pledge_tracker, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 保存完了: {out_p.resolve()}")

    print(f"🎉 名古屋市議 公約トラッカー結合が完了しました！（全 {len(councilor_pledges_list)} 名分）")

if __name__ == "__main__":
    main()