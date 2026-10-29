import json
import re
import sys
from pathlib import Path

CUR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR.parent
DATA_DIR = CUR / "data"
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"

VALID_CATEGORIES = {
    "子育て・教育", "福祉・医療・健康", "都市再生・交通インフラ",
    "産業・観光・地域経済", "財政・行革", "くらし・環境・エネルギー",
    "防災・減災・治安", "文化・景観・歴史"
}

# 会議録から抽出された行政理事者（局長・副市長等で議員ではない発言者）
NON_COUNCILOR_OFFICIALS = {
    "osaka": {
        "上村", "中小路大阪", "丸山大阪", "寺本", "尾植", "尾植万博",
        "山向", "彌園万博", "本屋副首都", "西島副首都", "長沢", "高橋万博", "高橋大阪"
    }
}

def clean_name(name: str) -> str:
    return re.sub(r"[\s\u3000]+", "", str(name or ""))

def load_master_speakers(city: str) -> set:
    candidates = [
        FRONTEND_DATA / f"{city}_statements_summary.json",
        FRONTEND_DATA / f"statements_summary_{city}.json",
        FRONTEND_DATA / "statements_summary.json" if city == "kyoto" else None
    ]
    officials = NON_COUNCILOR_OFFICIALS.get(city, set())
    for path in filter(None, candidates):
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return {
                    clean_name(d.get("speaker", ""))
                    for d in data
                    if d.get("speaker") and clean_name(d.get("speaker", "")) not in officials
                }
            except Exception:
                pass
    return set()

def audit_city(city: str):
    print("=" * 70)
    print(f"📊 【公約データ品質監査レポート: {city.upper()}】")
    print("=" * 70)

    pledge_file = DATA_DIR / f"{city}_councilor_pledges.json"
    if not pledge_file.exists():
        print(f"⚠️ 公約抽出データが見つかりません: {pledge_file.name}")
        return

    data = json.loads(pledge_file.read_text(encoding="utf-8"))
    pledge_dict = {}
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and ("speaker" in item or "name" in item):
                spk = item.get("speaker") or item.get("name")
                pledge_dict[clean_name(spk)] = item
    elif isinstance(data, dict):
        for k, v in data.items():
            pledge_dict[clean_name(k)] = v

    master_speakers = load_master_speakers(city)
    
    zero_pledge_councillors = []
    missing_councillors = []
    schema_errors = []
    suspicious_quotes = []

    for spk in sorted(master_speakers):
        if spk not in pledge_dict:
            missing_councillors.append(spk)
        else:
            pledges = pledge_dict[spk].get("pledges", [])
            if len(pledges) == 0:
                zero_pledge_councillors.append(spk)

    total_candidates = len(pledge_dict)
    total_pledges = 0

    for spk, info in pledge_dict.items():
        pledges = info.get("pledges", [])
        total_pledges += len(pledges)
        
        seen_quotes_spk = set()
        for p in pledges:
            cat = p.get("category", "")
            head = p.get("headline", "")
            quote = p.get("exact_quote", "")

            if cat not in VALID_CATEGORIES:
                schema_errors.append(f"[{spk}] 不正なカテゴリ: '{cat}'")

            if not quote or len(quote.strip()) < 3:
                suspicious_quotes.append(f"[{spk}] 原文引用が短すぎる/空: '{quote}'")
            elif quote in seen_quotes_spk:
                suspicious_quotes.append(f"[{spk}] 同一議員内での重複: '{head}'")
            seen_quotes_spk.add(quote)

    print(f"・解析対象 候補者総数: {total_candidates} 名")
    print(f"・抽出公約 総件数    : {total_pledges} 件 (1人平均: {total_pledges / (total_candidates or 1):.1f} 件)")
    print(f"・現任期議員マスタ   : {len(master_speakers)} 名中、未照合: {len(missing_councillors)} 名")
    
    print("\n--- 🚨 検出された問題点 ---")
    if zero_pledge_councillors:
        print(f"【要再抽出: 公約0件の現職議員 ({len(zero_pledge_councillors)}名)】")
        for name in zero_pledge_councillors:
            print(f"  ❌ {name}")
    else:
        print("✅ 公約0件の現職議員: なし")

    if missing_councillors:
        print(f"\n【マスタ照合漏れ議員 ({len(missing_councillors)}名)】")
        print(f"  ⚠️ {', '.join(missing_councillors)}")
    else:
        print("✅ 現任期マスタ議員のカバレッジ: 100%")

    if schema_errors:
        print(f"\n【スキーマ違反 ({len(schema_errors)}件)】")
        for err in schema_errors[:5]:
            print(f"  ⚠️ {err}")
    else:
        print("✅ カテゴリスキーマ: 正常")

    if suspicious_quotes:
        print(f"\n【不審な原文引用・議員内重複 ({len(suspicious_quotes)}件)】")
        for sus in suspicious_quotes[:5]:
            print(f"  ⚠️ {sus}")
    else:
        print("✅ 原文引用テキストの整合性: 正常")

    print("=" * 70 + "\n")

if __name__ == "__main__":
    cities = sys.argv[1:] if len(sys.argv) > 1 else ["kyoto", "yokohama", "osaka", "nagoya"]
    for c in cities:
        audit_city(c)
