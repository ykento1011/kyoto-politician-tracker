import json
import re
from pathlib import Path

CUR = Path(__file__).resolve().parent
DATA_DIR = CUR / "data"

VALID_CATEGORIES = [
    "子育て・教育", "福祉・医療・健康", "都市再生・交通インフラ",
    "産業・観光・地域経済", "財政・行革", "くらし・環境・エネルギー",
    "防災・減災・治安", "文化・景観・歴史"
]

# 議会マスタ（statements_summary.json）の正確な名前に合流させる
CANONICAL_NAME_MAP = {
    # 京都市（マスタ名がひらがなの議員をマスタ表記に統一）
    "富樫豊": "とがし豊",
    "下村明": "下村あきら",
    "津田大造": "津田大三",
    "熊沢昭真": "くまざわ真昭",
    "熊澤昭真": "くまざわ真昭",
    "片桐直哉": "かたぎり直哉",
    "菊地一秀": "きくち一秀",
    "島本京司": "しまもと京司",
    "菅谷浩平": "すがや浩平",
    "青野仁志": "青野ひとし",
    "湯浅光彦": "ゆあさ光彦",
    "井崎敦子": "井﨑敦子",
    "山添啓": "やまずえ",
    "やまずえあきら": "やまずえ",
    "やまずえ啓": "やまずえ",
    
    # 横浜市
    "古谷やすひこ": "古谷靖彦",
    "青木りょうすけ": "青木亮祐",
    "関たかふみ": "関嵩史",
    "竹内康洋": "竹内やすひろ",
    "みやぎすえん": "宮城素延"
}

def clean_text(t: str) -> str:
    return re.sub(r"[\s\u3000\r\n]+", "", str(t or ""))

def normalize_category(cat: str) -> str:
    cat = (cat or "").strip().replace("インफ्रा", "インフラ")
    
    # 短縮形・部分一致の正規化
    if "防災" in cat or "治安" in cat: return "防災・減災・治安"
    if "福祉" in cat or "医療" in cat or "健康" in cat: return "福祉・医療・健康"
    if "子育て" in cat or "教育" in cat: return "子育て・教育"
    if "都市" in cat or "交通" in cat or "インフラ" in cat: return "都市再生・交通インフラ"
    if "産業" in cat or "経済" in cat or "観光" in cat: return "産業・観光・地域経済"
    if "財政" in cat or "行革" in cat or "改革" in cat: return "財政・行革"
    if "環境" in cat or "エネルギー" in cat or "くらし" in cat: return "くらし・環境・エネルギー"
    if "文化" in cat or "景観" in cat or "歴史" in cat: return "文化・景観・歴史"
    
    for valid in VALID_CATEGORIES:
        if valid in cat: return valid
    return "くらし・環境・エネルギー"

def clean_city(city: str):
    p = DATA_DIR / f"{city}_councilor_pledges.json"
    if not p.exists():
        return

    data = json.loads(p.read_text(encoding="utf-8"))
    cleaned = {}

    for raw_spk, info in data.items():
        spk = CANONICAL_NAME_MAP.get(clean_text(raw_spk), raw_spk)

        if spk not in cleaned:
            cleaned[spk] = {
                "district": info.get("district", ""),
                "party": info.get("party", ""),
                "bulletin_pdf": info.get("bulletin_pdf", ""),
                "pledges": []
            }

        seen_quotes = {clean_text(p.get("exact_quote", "")) for p in cleaned[spk]["pledges"]}
        seen_heads = {clean_text(p.get("headline", "")) for p in cleaned[spk]["pledges"]}

        for pledge in info.get("pledges", []):
            raw_q = pledge.get("exact_quote", "").strip()
            raw_h = pledge.get("headline", "").strip()
            nq, nh = clean_text(raw_q), clean_text(raw_h)

            if (nq and nq in seen_quotes) or (nh and nh in seen_heads):
                continue
            if nq: seen_quotes.add(nq)
            if nh: seen_heads.add(nh)

            pledge["headline"] = raw_h
            pledge["exact_quote"] = raw_q
            pledge["category"] = normalize_category(pledge.get("category", ""))
            cleaned[spk]["pledges"].append(pledge)

    p.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ [{city.upper()}] 正規化完了: {len(cleaned)} 名")

clean_city("kyoto")
clean_city("yokohama")
