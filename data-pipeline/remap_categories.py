import os
import json
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE = os.path.join(BASE_DIR, "frontend", "public", "data", "statements_summary.json")

INDUSTRY_KEYWORDS = [
    "中小企業", "伝統産業", "地場産業", "観光", "インバウンド", "オーバーツーリズム",
    "商店街", "商業", "宿泊税", "スタートアップ", "事業承継", "雇用", "地域経済", "物価高騰対策"
]
CULTURE_KEYWORDS = [
    "文化庁", "文化芸術", "伝統文化", "京町家", "景観", "歴史的風土", "文化財", "博物館", "美術館", "芸術家"
]
TRANSIT_KEYWORDS = [
    "市バス", "地下鉄", "敬老乗車証", "歩いて暮らせる", "公共交通", "混雑対策", "運賃"
]
FINANCE_KEYWORDS = [
    "財政", "行革", "行財政", "予算", "決算", "市債", "借金", "人件費", "議員定数", "報酬", "外部監査", "補助金"
]

def normalize_category_value(cat_val):
    if isinstance(cat_val, list):
        return ", ".join(str(x) for x in cat_val)
    if cat_val is None:
        return ""
    return str(cat_val)

def refine_category(item):
    summary = str(item.get("summary") or "")
    title = str(item.get("meeting_title") or "")
    current_cat = normalize_category_value(item.get("category"))
    full_text = f"{title} {summary}"

    # 1. 委員会・キーワード優先判定
    if "産業交通水道" in title:
        if any(k in full_text for k in TRANSIT_KEYWORDS):
            return "都市再生・交通インフラ"
        return "産業・観光・地域経済"

    if any(k in full_text for k in CULTURE_KEYWORDS):
        return "文化・景観・歴史"

    if any(k in full_text for k in INDUSTRY_KEYWORDS):
        return "産業・観光・地域経済"

    if any(k in full_text for k in FINANCE_KEYWORDS) or "総務消防" in title and "財政" in full_text:
        return "財政・行革"

    # 2. 既存カテゴリの名称正規化
    if "都市計画" in current_cat or "交通" in current_cat or "道路" in full_text:
        return "都市再生・交通インフラ"
    if "福祉" in current_cat or "医療" in current_cat or "健康" in current_cat:
        return "福祉・医療・健康"
    if "環境" in current_cat or "エネルギー" in current_cat or "ごみ" in full_text:
        return "くらし・環境・エネルギー"
    if "教育" in current_cat or "子育て" in current_cat or "学校" in full_text or "保育" in full_text:
        return "子育て・教育"
    if "防災" in current_cat or "消防" in title or "防犯" in full_text:
        return "防災・減災・治安"
    if "財政" in current_cat or "行政" in current_cat:
        return "財政・行革"

    return "産業・観光・地域経済" if "産業" in current_cat else (current_cat if current_cat else "市政全般")

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ {INPUT_FILE} が見つかりません。")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        item["category"] = refine_category(item)

    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    cat_counts = {}
    for item in data:
        c = normalize_category_value(item.get("category"))
        cat_counts[c] = cat_counts.get(c, 0) + 1

    print("\n=== 再マッピング完了: カテゴリ別件数 ===")
    for c, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(data)) * 100
        print(f"{c}: {count:,}件 ({pct:.1f}%)")

if __name__ == "__main__":
    main()