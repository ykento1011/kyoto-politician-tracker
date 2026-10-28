import json
import re
import argparse
from pathlib import Path

def get_paths(city):
    CUR = Path(__file__).resolve().parent
    PROJECT_ROOT = CUR.parent
    DATA_DIR = CUR / "data"
    CONFIG_DIR = CUR / "config"
    FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"
    FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist" / "data"

    # 質疑データのパス探索（プレフィックス有無に対応）
    stmt_candidates = [
        FRONTEND_DATA / f"{city}_statements_summary.json",
        FRONTEND_DATA / f"{city}_statements.json"
    ]
    if city == "kyoto":
        stmt_candidates.extend([
            FRONTEND_DATA / "statements_summary.json",
            FRONTEND_DATA / "statements.json"
        ])

    stmt_path = None
    for p in stmt_candidates:
        if p.exists():
            stmt_path = p
            break

    # 出力先（京都の pledge_tracker.json、大阪の osaka/pledge_tracker.json 互換対応）
    out_files = [
        FRONTEND_DATA / f"pledge_tracker_{city}.json",
        FRONTEND_DIST / f"pledge_tracker_{city}.json"
    ]
    if city == "kyoto":
        out_files.extend([
            FRONTEND_DATA / "pledge_tracker.json",
            FRONTEND_DIST / "pledge_tracker.json"
        ])
    elif city == "osaka":
        out_files.extend([
            FRONTEND_DATA / "osaka" / "pledge_tracker.json",
            FRONTEND_DIST / "osaka" / "pledge_tracker.json"
        ])

    return {
        "rules": CONFIG_DIR / "pledge_matching_rules.json",
        "pledges": DATA_DIR / f"{city}_councilor_pledges.json",
        "pledges_alt": DATA_DIR / "councilor_pledges.json" if city == "kyoto" else None,
        "pledges_fallback": FRONTEND_DATA / f"pledge_tracker_{city}_2.json",
        "statements": stmt_path,
        "out_files": out_files
    }

def clean_name(name: str) -> str:
    return re.sub(r"[\s\u3000]+", "", str(name or ""))

def get_stop_words():
    return {
        "推進", "支援", "実現", "対策", "安心", "安全", "向上", "強化", 
        "要望", "市民", "取組", "充実", "創設", "見直し", "徹底",
        "促進", "目指す", "課題", "問題", "事業", "地域", "社会", "生活", "対応",
        "挑戦", "発展", "確立", "確保", "継続", "整備", "福祉", "環境", "経済", "教育", "施策"
    }

def match_statements(pledge, speaker_stmts, city_rules, max_count=2):
    if not speaker_stmts:
        return []

    target_text = f"{pledge.get('target_issue', '')} {pledge.get('headline', '')} {pledge.get('exact_quote', '')}"
    
    # 1. 外部ルールベース照合
    matched_rule = None
    for rule in city_rules:
        if any(trig in target_text for trig in rule.get("triggers", [])):
            matched_rule = rule
            break

    candidates = []
    if matched_rule:
        reqs = matched_rule.get("required", [])
        for stmt in speaker_stmts:
            s_sum = stmt.get("statement_summary") or stmt.get("summary") or stmt.get("question_summary") or ""
            s_txt = stmt.get("statement_text") or stmt.get("question_text") or stmt.get("text") or ""
            full_text = f"{s_sum} {s_txt[:350]}"
            
            if not reqs or any(r in full_text for r in reqs):
                score = sum(full_text.count(t) for t in matched_rule.get("triggers", [])) * 10
                if score > 0:
                    candidates.append((score, stmt))
    else:
        # 2. 汎用フォールバック
        stop_words = get_stop_words()
        words = re.findall(r"[\u4e00-\u9fa5]{3,}|[ァ-ンヴー]{3,}|[A-Za-z]{3,}", target_text)
        core_keywords = [w for w in words if w not in stop_words]
        
        if core_keywords:
            for stmt in speaker_stmts:
                s_sum = stmt.get("statement_summary") or stmt.get("summary") or stmt.get("question_summary") or ""
                s_txt = stmt.get("statement_text") or stmt.get("question_text") or stmt.get("text") or ""
                full_text = f"{s_sum} {s_txt[:300]}"
                
                hits = [kw for kw in core_keywords if kw in full_text]
                if len(hits) >= 2:
                    score = sum(len(h) * 2 for h in hits)
                    candidates.append((score, stmt))

    if not candidates:
        return []

    candidates.sort(key=lambda x: (x[0], x[1].get("meeting_date", "")), reverse=True)

    results = []
    for _, best_stmt in candidates[:max_count]:
        official_url = best_stmt.get("official_url") or best_stmt.get("source_url") or best_stmt.get("url") or ""
        s_date = best_stmt.get("meeting_date") or best_stmt.get("date") or ""
        s_committee = best_stmt.get("meeting_name") or best_stmt.get("committee") or best_stmt.get("meeting_title") or "本会議・委員会"
        s_sum = best_stmt.get("statement_summary") or best_stmt.get("summary") or best_stmt.get("question_summary") or best_stmt.get("statement_text", "")
        
        results.append({
            "date": s_date,
            "committee": s_committee,
            "summary": s_sum[:200] + ("..." if len(s_sum) > 200 else ""),
            "speech_id": str(best_stmt.get("id") or best_stmt.get("speech_id") or ""),
            "official_url": official_url
        })
    return results

def main():
    parser = argparse.ArgumentParser(description="統一公約トラッカービルダー")
    parser.add_argument("--city", required=True, help="対象都市コード (kyoto, osaka, nagoya 等)")
    args = parser.parse_args()
    city = args.city.lower()

    print(f"=== {city.upper()} 公約トラッカー 統一ビルドパイプライン ===")
    paths = get_paths(city)

    # ルールのロード
    city_rules = []
    if paths["rules"].exists():
        all_rules = json.loads(paths["rules"].read_text(encoding="utf-8"))
        city_rules = all_rules.get(city, [])

    # 公約データファイルのロード
    pledges_path = None
    for p in [paths["pledges"], paths["pledges_alt"], paths["pledges_fallback"]]:
        if p and p.exists():
            pledges_path = p
            break

    if not pledges_path:
        print(f"❌ 公約元データが見つかりません。")
        return

    raw_data = json.loads(pledges_path.read_text(encoding="utf-8"))
    
    # 辞書形式（京都）、配列形式（大阪）、councilors内包形式（名古屋）を全て正規化
    councilor_list = []
    if isinstance(raw_data, dict):
        if "councilors" in raw_data:
            councilor_list = raw_data["councilors"]
        else:
            # 京都形式: { "議員名": { "district": ..., "pledges": [...] } }
            for name, val in raw_data.items():
                item = dict(val)
                item["speaker"] = name
                councilor_list.append(item)
    elif isinstance(raw_data, list):
        councilor_list = raw_data

    # 質疑データのロード
    statements = []
    if paths["statements"] and paths["statements"].exists():
        raw_stmts = json.loads(paths["statements"].read_text(encoding="utf-8"))
        statements = raw_stmts if isinstance(raw_stmts, list) else raw_stmts.get("statements", [])
        print(f"🔍 質疑データロード完了: {paths['statements'].name} ({len(statements)} 件)")
    else:
        print("⚠️ 質疑データが見つかりません（監視中として処理します）")

    stmts_by_speaker = {}
    for s in statements:
        spk = clean_name(s.get("speaker") or s.get("speaker_name") or "")
        if spk:
            stmts_by_speaker.setdefault(spk, []).append(s)

    pledge_tracker = {}
    for c in councilor_list:
        raw_name = c.get("speaker") or c.get("name") or ""
        c_name = clean_name(raw_name)
        if not c_name:
            continue

        district = c.get("district", "")
        party = c.get("party") or c.get("partyGroup", "")
        bulletin_url = c.get("bulletin_url") or c.get("bulletin_pdf") or ""
        raw_pledges = c.get("pledges", [])
        my_stmts = stmts_by_speaker.get(c_name, [])

        tracked_items = []
        for idx, p in enumerate(raw_pledges):
            related_stmts = match_statements(p, my_stmts, city_rules, max_count=2)
            
            tracked_items.append({
                "id": f"pledge_{city}_{c_name}_{idx+1}",
                "headline": p.get("headline", ""),
                "category": p.get("category", "くらし・環境・エネルギー"),
                "target_issue": p.get("target_issue", ""),
                "stance": p.get("stance", "推進・拡充"),
                "election_promise": {
                    "quote": p.get("exact_quote") or p.get("quote") or "",
                    "source_name": "公式選挙公報 / 政策マニフェスト",
                    "bulletin_url": p.get("bulletin_url") or p.get("bulletin_pdf") or bulletin_url
                },
                "council_vote": None,
                "council_statement": related_stmts[0] if related_stmts else None,
                "council_statements": related_stmts
            })

        c_data = {
            "district": district,
            "party": party,
            "bulletin_url": bulletin_url,
            "tracked_items": tracked_items
        }

        pledge_tracker[raw_name] = c_data
        if c_name != raw_name:
            pledge_tracker[c_name] = c_data

    # 各所へ保存
    for out_p in paths["out_files"]:
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(pledge_tracker, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 保存完了: {out_p.resolve()}")

    print(f"🎉 {city.upper()} の統一ビルドが完了しました！（対象: {len(councilor_list)} 名）\n")

if __name__ == "__main__":
    main()