import json
from pathlib import Path

FRONTEND_DATA = Path("../frontend/public/data")

print("=" * 80)
print(" 🔬 3都市 公約 ⇄ 議案採決（賛否行動）結合インテグリティ監査")
print("=" * 80)

cities = ["kyoto", "osaka", "nagoya"]

for city in cities:
    p = FRONTEND_DATA / f"pledge_tracker_{city}.json"
    if not p.exists() and city == "kyoto":
        p = FRONTEND_DATA / "pledge_tracker.json"
    
    if not p.exists():
        print(f"❌ {city.upper()}: ファイルが見つかりません ({p})")
        continue

    data = json.loads(p.read_text(encoding="utf-8"))
    
    seen_ids = set()
    total_pledges = 0
    bound_stmts = 0
    bound_votes = 0
    vote_breakdown = {}
    samples = []

    for spk, spk_data in data.items():
        for item in spk_data.get("tracked_items", []):
            pid = item.get("id")
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            total_pledges += 1

            has_stmt = len(item.get("council_statements", [])) > 0
            if has_stmt:
                bound_stmts += 1

            cv = item.get("council_vote")
            if cv:
                bound_votes += 1
                v_action = cv.get("vote", "不明")
                vote_breakdown[v_action] = vote_breakdown.get(v_action, 0) + 1
                if len(samples) < 3:
                    samples.append({
                        "speaker": spk,
                        "pledge": item.get("headline", ""),
                        "bill": cv.get("bill_title", ""),
                        "vote": v_action,
                        "type": cv.get("vote_type", ""),
                        "session": cv.get("session", "")
                    })

    print(f"\n【{city.upper()}】")
    print(f"  ・ユニーク公約数    : {total_pledges} 件")
    print(f"  ・質疑（言葉）結合  : {bound_stmts} 件 ({(bound_stmts/total_pledges*100) if total_pledges else 0:.1f}%)")
    print(f"  ・採決（行動）結合  : {bound_votes} 件 ({(bound_votes/total_pledges*100) if total_pledges else 0:.1f}%)")
    print(f"  ・賛否内訳          : {vote_breakdown}")
    
    if samples:
        print("  ・結合サンプル:")
        for s in samples:
            print(f"    - [{s['speaker']}] 公約: {s['pledge']}")
            print(f"      └ 議案: {s['bill']} ➔ 【{s['vote']}】({s['type']})")

print("\n" + "=" * 80)
