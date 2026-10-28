import json
import re
import argparse
from pathlib import Path

CUR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR.parent
CONFIG_DIR = CUR / "config"
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"

RULES_FILE = CONFIG_DIR / "pledge_matching_rules.json"
RULES = json.loads(RULES_FILE.read_text(encoding="utf-8")) if RULES_FILE.exists() else {}

def audit_city(city):
    print(f"\n================================================================================")
    print(f" 🔬 【{city.upper()}】 公約トラッカー 精度＆インテグリティ監査")
    print(f"================================================================================")

    data_file = FRONTEND_DATA / f"pledge_tracker_{city}.json"
    if not data_file.exists():
        if city == "kyoto":
            data_file = FRONTEND_DATA / "pledge_tracker.json"
        elif city == "osaka":
            data_file = FRONTEND_DATA / "osaka" / "pledge_tracker.json"

    if not data_file.exists():
        print(f"❌ データファイルが見つかりません: {data_file}")
        return

    data = json.loads(data_file.read_text(encoding="utf-8"))

    seen_ids = set()
    unique_items = []
    total_quotes = 0
    total_pledges = 0

    for spk, spk_data in data.items():
        for item in spk_data.get("tracked_items", []):
            p_id = item.get("id")
            if p_id not in seen_ids:
                seen_ids.add(p_id)
                unique_items.append((spk, item))
                total_pledges += 1
                if item.get("election_promise", {}).get("quote"):
                    total_quotes += 1

    city_rules = RULES.get(city, [])
    
    high_conf = []
    med_conf = []
    low_conf = []
    no_stmts = []

    for spk, item in unique_items:
        headline = item.get("headline", "")
        target_issue = item.get("target_issue", "")
        quote = item.get("election_promise", {}).get("quote", "")
        stmts = item.get("council_statements", [])
        
        if not stmts:
            no_stmts.append((spk, headline))
            continue

        core_text = f"{target_issue} {headline} {quote}"

        for s in stmts:
            summary = s.get("summary", "")
            committee = s.get("committee", "")
            full = f"{committee} {summary}"

            # 1. ルールアンカーによる判定
            is_high = False
            for r in city_rules:
                triggers = r.get("triggers", [])
                reqs = r.get("required", [])
                if any(t in core_text for t in triggers):
                    if not reqs or any(req in full for req in reqs):
                        is_high = True
                        break

            entry = {
                "speaker": spk,
                "headline": headline,
                "target_issue": target_issue,
                "date": s.get("date"),
                "summary": summary
            }

            if is_high:
                high_conf.append(entry)
            else:
                words = [w for w in re.findall(r"[\u4e00-\u9fa5]{2,}", core_text) if w not in {"推進", "支援", "実現", "対策", "安心", "安全", "向上", "強化", "京都", "大阪", "名古屋"}]
                hits = [w for w in words if w in full]
                if len(hits) >= 1:
                    med_conf.append(entry)
                else:
                    low_conf.append(entry)

    total_bound = len(high_conf) + len(med_conf) + len(low_conf)

    print(f"📊 【登録メタデータ】")
    print(f"  ・ユニーク公約数: {total_pledges} 件")
    print(f"  ・公報原本引用率: {total_quotes} / {total_pledges} ({(total_quotes/total_pledges*100) if total_pledges else 0:.1f}%)")

    print(f"\n📈 【質疑紐づけレーティング】 (結合質疑総数: {total_bound} 件)")
    if total_bound > 0:
        print(f"  🟢 高精度（主題・アンカー完全一致）: {len(high_conf)} 件 ({len(high_conf)/total_bound*100:.1f}%)")
        print(f"  🟡 中精度（個別キーワード一致）    : {len(med_conf)} 件 ({len(med_conf)/total_bound*100:.1f}%)")
        print(f"  🔴 低精度／ノイズ疑い              : {len(low_conf)} 件 ({len(low_conf)/total_bound*100:.1f}%)")
    print(f"  ⚪ 質疑なし（継続監視中）          : {len(no_stmts)} 件")

    if low_conf:
        print(f"\n🚨 【低精度／ノイズ疑い例 (上位3件)】")
        for ex in low_conf[:3]:
            print(f"  ・[{ex['speaker']}] 公約: {ex['headline']}")
            print(f"    └ 質疑 ({ex['date']}): {ex['summary'][:60]}...")

def main():
    parser = argparse.ArgumentParser(description="全都市公約トラッカー精度監査")
    parser.add_argument("--city", default="all", help="kyoto, osaka, nagoya または all")
    args = parser.parse_args()

    targets = ["kyoto", "osaka", "nagoya"] if args.city == "all" else [args.city]
    for c in targets:
        audit_city(c)

if __name__ == "__main__":
    main()