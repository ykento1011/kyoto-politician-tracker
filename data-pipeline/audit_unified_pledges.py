import json
import re
import math
import argparse
from pathlib import Path

CUR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR.parent
DATA_DIR = CUR / "data"
CONFIG_DIR = CUR / "config"
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"

RULES_FILE = CONFIG_DIR / "pledge_matching_rules.json"
RULES = json.loads(RULES_FILE.read_text(encoding="utf-8")) if RULES_FILE.exists() else {}

def clean_name(name):
    return re.sub(r"[\s\u3000]+", "", str(name or ""))

def cosine_similarity(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

def audit_city(city):
    print(f"\n================================================================================")
    print(f" 🔬 【{city.upper()}】 公約トラッカー 精度＆インテグリティ監査 (セマンティック評価対応)")
    print(f"================================================================================")

    data_candidates = [
        FRONTEND_DATA / f"pledge_tracker_{city}.json",
        FRONTEND_DATA / f"{city}" / "pledge_tracker.json"
    ]
    if city == "kyoto":
        data_candidates.append(FRONTEND_DATA / "pledge_tracker.json")

    data_file = next((p for p in data_candidates if p.exists()), None)
    if not data_file:
        print(f"❌ データファイルが見つかりません（検索先: {[str(p) for p in data_candidates]}）")
        return

    tracker_data = json.loads(data_file.read_text(encoding="utf-8"))

    stmt_emb_file = DATA_DIR / f"embeddings_{city}_statements.json"
    pledge_emb_file = DATA_DIR / f"embeddings_{city}_pledges.json"
    stmt_emb = json.loads(stmt_emb_file.read_text(encoding="utf-8")) if stmt_emb_file.exists() else {}
    pledge_emb = json.loads(pledge_emb_file.read_text(encoding="utf-8")) if pledge_emb_file.exists() else {}

    city_rules = RULES.get(city, [])

    seen_ids = set()
    total_pledges = 0
    total_quotes = 0
    high_conf = []
    med_conf = []
    low_conf = []
    no_stmts = []

    for raw_spk, spk_data in tracker_data.items():
        spk = clean_name(raw_spk)
        for idx, item in enumerate(spk_data.get("tracked_items", [])):
            p_id = item.get("id")
            if p_id in seen_ids:
                continue
            seen_ids.add(p_id)
            total_pledges += 1

            if item.get("election_promise", {}).get("quote"):
                total_quotes += 1

            stmts = item.get("council_statements", [])
            if not stmts:
                no_stmts.append((spk, item.get("headline", "")))
                continue

            headline = item.get("headline", "")
            target_issue = item.get("target_issue", "")
            full_p_id = f"{spk}_{idx+1}"

            for s in stmts:
                summary = s.get("summary", "")
                committee = s.get("committee", "")
                full_stmt = f"{committee} {summary}"
                speech_id = str(s.get("speech_id", ""))

                sim = 0.0
                if full_p_id in pledge_emb and speech_id in stmt_emb:
                    sim = cosine_similarity(pledge_emb[full_p_id], stmt_emb[speech_id])

                is_rule_high = False
                core_p_text = f"{target_issue} {headline}"
                for r in city_rules:
                    if any(t in core_p_text for t in r.get("triggers", [])):
                        reqs = r.get("required", [])
                        if not reqs or any(req in full_stmt for req in reqs):
                            is_rule_high = True
                            break

                entry = {
                    "speaker": spk,
                    "headline": headline,
                    "date": s.get("date"),
                    "summary": summary,
                    "sim": sim
                }

                if sim >= 0.68 or is_rule_high:
                    high_conf.append(entry)
                elif sim >= 0.65:
                    med_conf.append(entry)
                else:
                    words = [w for w in re.findall(r"[\u4e00-\u9fa5]{2,}", core_p_text) if w not in {"推進", "支援", "実現", "対策", "安心", "安全", "向上", "強化"}]
                    if any(w in full_stmt for w in words):
                        med_conf.append(entry)
                    else:
                        low_conf.append(entry)

    total_bound = len(high_conf) + len(med_conf) + len(low_conf)

    print(f"📊 【登録メタデータ】")
    print(f"  ・ユニーク公約数: {total_pledges} 件")
    print(f"  ・公報原本引用率: {total_quotes} / {total_pledges} ({(total_quotes/total_pledges*100) if total_pledges else 0:.1f}%)")

    print(f"\n📈 【質疑紐づけレーティング】 (結合質疑総数: {total_bound} 件)")
    if total_bound > 0:
        print(f"  🟢 高精度（主題完全一致 / sim >= 0.68）: {len(high_conf)} 件 ({len(high_conf)/total_bound*100:.1f}%)")
        print(f"  🟡 中精度（文脈合致・同義語 / sim >= 0.65）: {len(med_conf)} 件 ({len(med_conf)/total_bound*100:.1f}%)")
        print(f"  🔴 低精度／ノイズ疑い                    : {len(low_conf)} 件 ({len(low_conf)/total_bound*100:.1f}%)")
    print(f"  ⚪ 質疑なし（継続監視中）                : {len(no_stmts)} 件")

    if low_conf:
        print(f"\n🚨 【低精度／ノイズ疑い例 (上位3件)】")
        for ex in low_conf[:3]:
            print(f"  ・[{ex['speaker']}] 公約: {ex['headline']}")
            print(f"    └ 質疑 ({ex['date']}): {ex['summary'][:60]}...")

def main():
    parser = argparse.ArgumentParser(description="セマンティック公約トラッカー精度監査")
    parser.add_argument("--city", default="all", help="都市コード (kyoto, osaka, nagoya または all)")
    args = parser.parse_args()
    
    city_arg = args.city.lower()
    targets = ["kyoto", "osaka", "nagoya"] if city_arg == "all" else [city_arg]
    for c in targets:
        audit_city(c)

if __name__ == "__main__":
    main()
