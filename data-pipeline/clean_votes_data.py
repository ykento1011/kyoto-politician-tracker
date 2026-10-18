import os
import json
import re
import unicodedata

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOTES_FILE = os.path.join(BASE_DIR, "..", "frontend", "public", "data", "votes_summary.json")

# 京都市議会議員のホワイトリスト（正規名）
VALID_COUNCILORS = [
    "青野仁志", "赤阪仁", "天方ひろゆき", "井﨑敦子", "井崎敦子", "井上よしひろ", "宇佐美賢一",
    "江村理紗", "えもとかよこ", "大津裕太", "おんづか功", "片桐直哉", "加藤あい",
    "加藤昌洋", "神谷修平", "河合ようこ", "かわしま優子", "河村諒", "きくち一秀",
    "北尾ゆか", "北川みき", "北山ただお", "久保田正紀", "くまざわ真昭", "くらた共子",
    "こうち大輔", "小島信太郎", "さくらい泰広", "繁隆夫", "しまもと京司", "下村あきら",
    "菅谷浩平", "田中明秀", "田中たかのり", "谷口みゆき", "玉本なるみ", "津田大三",
    "寺田一博", "とがし豊", "富きくお", "中高しゅうじ", "中野洋一", "中村まり",
    "西野さち子", "西村義直", "西山信昌", "橋村芳和", "土方莉紗", "兵藤しんいち",
    "平井良人", "平田圭", "平山たかお", "平山よしかず", "増成竜治", "松田けい子",
    "みちはた弘之", "椋田隆知", "森かれん", "森田守", "森田ゆみ子", "もりもと英靖",
    "山田こうじ", "やまね智史", "山本恵一", "山本しゅうじ", "山本陽子", "湯浅光彦",
    "吉田孝雄"
]

def clean_key_name(raw_key):
    """会派名および議員名を完全正規化"""
    k = unicodedata.normalize('NFKC', str(raw_key)).strip()
    
    # 1. 会派名の正規化
    if "自由民主" in k or "自民" in k:
        return "自由民主党京都市会議員団"
    if "日本共産" in k or "共産" in k:
        return "日本共産党京都市会議員団"
    if "維新" in k or "維京国" in k:
        return "維新・京都・国民市会議員団"
    if "公明" in k:
        return "公明党京都市会議員団"
    if "改新" in k:
        return "改新京都"
    if "京都党" in k:
        return "地域政党京都党市会議員団"
    if "民主" in k or "フォーラム" in k:
        return "民主・市民フォーラム"

    # 2. 議員個人名（無所属）のマッチング
    for c in VALID_COUNCILORS:
        if c in k:
            return "井﨑敦子" if c == "井崎敦子" else c

    # 3. 未知の記号・不要な表記
    if "付帯決議" in k or "件名" in k or "番号" in k or "結果" in k:
        return None

    # 「無所属1」「無所属2」などの未解決記号は None を返して後で処理
    if re.match(r'^無所属\d*$', k):
        return k

    return k

def main():
    if not os.path.exists(VOTES_FILE):
        print(f"❌ {VOTES_FILE} が見つかりません。")
        return

    with open(VOTES_FILE, "r", encoding="utf-8") as f:
        bills = json.load(f)

    print(f"📖 読み込み件数: {len(bills)} 件")

    cleaned_count = 0
    for bill in bills:
        raw_votes = bill.get("votes", {})
        cleaned_votes = {}
        unresolved_votes = {}

        # ステップ1: 各キーの正規化と振り分け
        for k, v in raw_votes.items():
            norm_k = clean_key_name(k)
            if not norm_k:
                continue

            if norm_k in ["賛成", "反対", "退席・棄権"]:
                continue

            # 個人名（または会派名）が特定できた場合
            if norm_k in VALID_COUNCILORS or "議員団" in norm_k or norm_k in ["改新京都", "民主・市民フォーラム"]:
                cleaned_votes[norm_k] = v
            elif re.match(r'^無所属\d*$', norm_k):
                unresolved_votes[norm_k] = v

        # ステップ2: 未解決の「無所属2」「無所属4」などの処理
        # もし実名（天方ひろゆき、井﨑敦子等）が既に1人以上登録されている場合、
        # 重複して残っている「無所属2」等はゴミなので捨てる
        # まだ1人も個人名がない場合のみ、特定を試みるか除外
        bill["votes"] = cleaned_votes
        cleaned_count += 1

    with open(VOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(bills, f, ensure_ascii=False, indent=2)

    print(f"🎉 完了: 全 {cleaned_count} 件の議案データをクレンジング・保存しました！")

if __name__ == "__main__":
    main()