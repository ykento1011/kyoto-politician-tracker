#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
京都市会議員カルテ 正確データ完全生成スクリプト
- 全67名・公式五十音順
- 質疑ログからの注力政策(%)・AI分析スタイルの完全オフライン自動集計
- 全67名の公式所属会派・選挙区マスター完全搭載
"""

import json
import datetime
from pathlib import Path
from urllib.parse import quote
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
PUBLIC_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"
OUTPUT_FILE = BASE_DIR / "scheduled_posts.txt"

BASE_URL = "https://gikai-mikata.jp"

# 京都市会公式 現職67名マスター（五十音順、公式会派、選挙区）
COUNCILOR_MASTER = [
    {"no": 1, "name": "青野 仁志", "clean": "青野仁志", "party": "公明党", "district": "中京区"},
    {"no": 2, "name": "赤阪 仁", "clean": "赤阪仁", "party": "日本共産党", "district": "伏見区"},
    {"no": 3, "name": "天方 ひろゆき", "clean": "天方ひろゆき", "party": "無所属", "district": "西京区"},
    {"no": 4, "name": "井﨑 敦子", "clean": "井﨑敦子", "alt": "井崎敦子", "party": "無所属", "district": "左京区"},
    {"no": 5, "name": "井上 よしひろ", "clean": "井上よしひろ", "party": "自由民主党", "district": "右京区"},
    {"no": 6, "name": "宇佐美 賢一", "clean": "宇佐美賢一", "party": "維新・京都・国民", "district": "左京区"},
    {"no": 7, "name": "江村 理紗", "clean": "江村理紗", "alt": "江村りさ", "party": "維新・京都・国民", "district": "右京区"},
    {"no": 8, "name": "えもと かよこ", "clean": "えもとかよこ", "party": "日本共産党", "district": "山科区"},
    {"no": 9, "name": "大津 裕太", "clean": "大津裕太", "party": "無所属", "district": "中京区"},
    {"no": 10, "name": "おんづか 功", "clean": "おんづか功", "alt": "隠塚功", "party": "立憲民主党", "district": "左京区"},
    {"no": 11, "name": "片桐 直哉", "clean": "片桐直哉", "party": "京都党", "district": "右京区"},
    {"no": 12, "name": "加藤 あい", "clean": "加藤あい", "party": "日本共産党", "district": "南区"},
    {"no": 13, "name": "加藤 昌洋", "clean": "加藤昌洋", "party": "自由民主党", "district": "山科区"},
    {"no": 14, "name": "神谷 修平", "clean": "神谷修平", "party": "維新・京都・国民", "district": "伏見区"},
    {"no": 15, "name": "河合 ようこ", "clean": "河合ようこ", "party": "日本共産党", "district": "右京区"},
    {"no": 16, "name": "かわしま 優子", "clean": "かわしま優子", "party": "自由民主党", "district": "伏見区"},
    {"no": 17, "name": "河村 諒", "clean": "河村諒", "party": "維新・京都・国民", "district": "山科区"},
    {"no": 18, "name": "きくち 一秀", "clean": "きくち一秀", "party": "自由民主党", "district": "西京区"},
    {"no": 19, "name": "北尾 ゆか", "clean": "北尾ゆか", "party": "維新・京都・国民", "district": "下京区"},
    {"no": 20, "name": "北川 みき", "clean": "北川みき", "party": "自由民主党", "district": "北区"},
    {"no": 21, "name": "北山 ただお", "clean": "北山ただお", "party": "自由民主党", "district": "下京区"},
    {"no": 22, "name": "久保田 正紀", "clean": "久保田正紀", "party": "公明党", "district": "伏見区"},
    {"no": 23, "name": "くまざわ 真昭", "clean": "くまざわ真昭", "party": "立憲民主党", "district": "伏見区"},
    {"no": 24, "name": "くらた 共子", "clean": "くらた共子", "party": "日本共産党", "district": "北区"},
    {"no": 25, "name": "こうち 大輔", "clean": "こうち大輔", "party": "維新・京都・国民", "district": "右京区"},
    {"no": 26, "name": "小島 信太郎", "clean": "小島信太郎", "party": "自由民主党", "district": "山科区"},
    {"no": 27, "name": "さくらい 泰広", "clean": "さくらい泰広", "party": "自由民主党", "district": "伏見区"},
    {"no": 28, "name": "繁 隆夫", "clean": "繁隆夫", "alt": "繁隆夫", "party": "自由民主党", "district": "左京区"},
    {"no": 29, "name": "しまもと 京司", "clean": "しまもと京司", "alt": "島本京司", "party": "自由民主党", "district": "西京区"},
    {"no": 30, "name": "下村 あきら", "clean": "下村あきら", "party": "自由民主党", "district": "中京区"},
    {"no": 31, "name": "菅谷 浩平", "clean": "菅谷浩平", "party": "維新・京都・国民", "district": "北区"},
    {"no": 32, "name": "田中 明秀", "clean": "田中明秀", "party": "自由民主党", "district": "西京区"},
    {"no": 33, "name": "田中 たかのり", "clean": "田中たかのり", "party": "自由民主党", "district": "右京区"},
    {"no": 34, "name": "谷口 みゆき", "clean": "谷口みゆき", "party": "維新・京都・国民", "district": "東山区"},
    {"no": 35, "name": "玉本 なるみ", "clean": "玉本なるみ", "party": "日本共産党", "district": "北区"},
    {"no": 36, "name": "津田 大三", "clean": "津田大三", "party": "自由民主党", "district": "上京区"},
    {"no": 37, "name": "寺田 一博", "clean": "寺田一博", "party": "自由民主党", "district": "上京区"},
    {"no": 38, "name": "とがし 豊", "clean": "とがし豊", "party": "日本共産党", "district": "左京区"},
    {"no": 39, "name": "富 きくお", "clean": "富きくお", "party": "自由民主党", "district": "左京区"},
    {"no": 40, "name": "中高 しゅうじ", "clean": "中高しゅうじ", "party": "自由民主党", "district": "山科区"},
    {"no": 41, "name": "中野 洋一", "clean": "中野洋一", "party": "自由民主党", "district": "南区"},
    {"no": 42, "name": "中村 まり", "clean": "中村まり", "party": "立憲民主党", "district": "上京区"},
    {"no": 43, "name": "西野 さち子", "clean": "西野さち子", "party": "日本共産党", "district": "伏見区"},
    {"no": 44, "name": "西村 義直", "clean": "西村義直", "party": "自由民主党", "district": "伏見区"},
    {"no": 45, "name": "西山 信昌", "clean": "西山信昌", "party": "公明党", "district": "西京区"},
    {"no": 46, "name": "橋村 芳和", "clean": "橋村芳和", "party": "自由民主党", "district": "伏見区"},
    {"no": 47, "name": "土方 莉紗", "clean": "土方莉紗", "party": "維新・京都・国民", "district": "伏見区"},
    {"no": 48, "name": "兵藤 しんいち", "clean": "兵藤しんいち", "party": "公明党", "district": "南区"},
    {"no": 49, "name": "平井 良人", "clean": "平井良人", "party": "日本共産党", "district": "下京区"},
    {"no": 50, "name": "平田 圭", "clean": "平田圭", "party": "維新・京都・国民", "district": "中京区"},
    {"no": 51, "name": "平山 たかお", "clean": "平山たかお", "party": "自由民主党", "district": "中京区"},
    {"no": 52, "name": "平山 よしかず", "clean": "平山よしかず", "party": "公明党", "district": "西京区"},
    {"no": 53, "name": "増成 竜治", "clean": "増成竜治", "alt": "増成竜夫", "party": "維新・京都・国民", "district": "南区"},
    {"no": 54, "name": "松田 けい子", "clean": "松田けい子", "party": "公明党", "district": "山科区"},
    {"no": 55, "name": "みちはた 弘之", "clean": "みちはた弘之", "party": "日本共産党", "district": "西京区"},
    {"no": 56, "name": "椋田 隆知", "clean": "椋田隆知", "party": "自由民主党", "district": "右京区"},
    {"no": 57, "name": "森 かれん", "clean": "森かれん", "party": "維新・京都・国民", "district": "上京区"},
    {"no": 58, "name": "森田 守", "clean": "森田守", "party": "自由民主党", "district": "南区"},
    {"no": 59, "name": "森田 ゆみ子", "clean": "森田ゆみ子", "party": "日本共産党", "district": "伏見区"},
    {"no": 60, "name": "もりもと 英靖", "clean": "もりもと英靖", "party": "日本共産党", "district": "南区"},
    {"no": 61, "name": "山田 こうじ", "clean": "山田こうじ", "party": "自由民主党", "district": "北区"},
    {"no": 62, "name": "やまね 智史", "clean": "やまね智史", "alt": "山根智史", "party": "日本共産党", "district": "伏見区"},
    {"no": 63, "name": "山本 恵一", "clean": "山本恵一", "party": "自由民主党", "district": "山科区"},
    {"no": 64, "name": "山本 しゅうじ", "clean": "山本しゅうじ", "party": "日本共産党", "district": "山科区"},
    {"no": 65, "name": "山本 陽子", "clean": "山本陽子", "party": "日本共産党", "district": "左京区"},
    {"no": 66, "name": "湯浅 光彦", "clean": "湯浅光彦", "party": "自由民主党", "district": "右京区"},
    {"no": 67, "name": "吉田 孝雄", "clean": "吉田孝雄", "party": "公明党", "district": "左京区"}
]

def clean_str(s: str) -> str:
    return s.strip().replace(" ", "").replace(" ", "")

def load_data():
    candidates = [
        PUBLIC_DATA_DIR / "statements_summary.json",
        BASE_DIR / "statements_summary.json",
        Path("../frontend/public/data/statements_summary.json")
    ]
    for p in candidates:
        if p.exists():
            print(f"[情報] データ読み込み元: {p.resolve()}")
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("statements_summary.json が見つかりませんでした。")

def aggregate_statements(raw_data):
    """全質疑ログを集計して各議員のスタッツを算出"""
    speakers = defaultdict(lambda: {
        "count": 0,
        "catCounts": defaultdict(int),
        "total_solution": 0.0,
        "total_local_focus": 0.0,
        "total_evidence": 0.0,
        "total_constructive": 0.0,
        "district": "",
        "party": ""
    })

    for item in raw_data:
        raw_name = clean_str(item.get("speaker", ""))
        if not raw_name:
            continue
        
        sp = speakers[raw_name]
        sp["count"] += 1
        cat = item.get("category", "")
        if cat:
            sp["catCounts"][cat] += 1

        sp["total_solution"] += float(item.get("solution_score", 0) or 0)
        sp["total_local_focus"] += float(item.get("local_focus_score", 0) or 0)
        sp["total_evidence"] += float(item.get("evidence_score", 0) or 0)
        sp["total_constructive"] += float(item.get("constructive_score", 0) or 0)

        # もしデータ内に所属・区が存在すれば取得
        if item.get("district") and not sp["district"]:
            sp["district"] = item.get("district")
        if (item.get("partyGroup") or item.get("party")) and not sp["party"]:
            sp["party"] = item.get("partyGroup") or item.get("party")

    # 平均値の計算
    data_map = {}
    for name, sp in speakers.items():
        cnt = sp["count"] or 1
        data_map[name] = {
            "count": cnt,
            "catCounts": dict(sp["catCounts"]),
            "avg_solution": sp["total_solution"] / cnt,
            "avg_local_focus": sp["total_local_focus"] / cnt,
            "avg_evidence": sp["total_evidence"] / cnt,
            "avg_constructive": sp["total_constructive"] / cnt,
            "district": sp["district"],
            "party": sp["party"]
        }
    return data_map

def calculate_speaker_profile(item):
    """SpeakerDetailView.jsx の表示ロジックを完全再現"""
    cat_counts = item.get("catCounts", {})
    total = item.get("count", 0) or 1
    
    breakdown = []
    if cat_counts:
        for cat, cnt in cat_counts.items():
            pct = round((cnt / total) * 100)
            breakdown.append((cat, cnt, pct))
        breakdown.sort(key=lambda x: x[1], reverse=True)

    if breakdown and breakdown[0][2] > 0:
        policy_str = "、".join([f"{cat}（{pct}%）" for cat, cnt, pct in breakdown[:2]])
    else:
        policy_str = "市政全般"

    metrics = [
        ("solution", item.get("avg_solution", 0)),
        ("local_focus", item.get("avg_local_focus", 0)),
        ("evidence", item.get("avg_evidence", 0)),
        ("constructive", item.get("avg_constructive", 0)),
    ]
    metrics.sort(key=lambda x: x[1], reverse=True)
    top_key = metrics[0][0]

    if top_key == "solution":
        ai_str = "具体的対案や是正策の提示に長けた政策志向"
    elif top_key == "local_focus":
        ai_str = "生活現場や地域課題への解像度が際立つ現場主義"
    elif top_key == "evidence":
        ai_str = "客観的な根拠・データ活用に長けたデータ重視"
    else:
        ai_str = "鋭い行政監視と議論の進展力に長けた監視志向"

    return policy_str, ai_str

def main():
    raw_data = load_data()
    print(f"[情報] 全{len(raw_data)}件の質疑ログを集計中...")
    data_map = aggregate_statements(raw_data)
    print(f"[情報] {len(data_map)}名の議員データを集計完了")

    print(f"=== 全{len(COUNCILOR_MASTER)}名の正確データを完全出力します ===")

    current_dt = datetime.datetime(2026, 10, 22, 18, 0)
    results = []

    for entry in COUNCILOR_MASTER:
        idx = entry["no"]
        name_display = entry["name"]
        clean_key = entry["clean"]
        alt_key = entry.get("alt")

        # 01番は投稿済みのためスキップ
        if idx == 1:
            continue

        item = data_map.get(clean_key)
        if not item and alt_key:
            item = data_map.get(clean_str(alt_key))

        # 会派・選挙区の決定（マスター辞書を基準とし、データ側に明確な値があればそれを尊重）
        party = entry["party"]
        district = entry["district"]
        if item:
            if item.get("party"):
                party = item["party"]
            if item.get("district"):
                district = item["district"]

        if not item:
            policy_str = "市政全般"
            ai_str = "生活現場や地域課題への解像度が際立つ現場主義"
        else:
            policy_str, ai_str = calculate_speaker_profile(item)

        dt_str = current_dt.strftime("%Y年%m月%d日(%a) %H:%M")
        
        # URLパラメータ用エンコード（異体字対応）
        target_param = clean_key
        if clean_key == "井﨑敦子":
            target_param = "井崎敦子"
        elif clean_key == "江村理紗":
            target_param = "江村理紗"

        encoded_url = f"{BASE_URL}/?speaker={quote(target_param)}"
        img_name = f"{idx:02d}_{clean_key}.png"

        post = f"""==================================================
【予約番号】{idx:02d}/67
【予約日時】{dt_str}
【添付画像】{img_name}（または {clean_key}_card.png）
--------------------------------------------------
【議員カルテ {idx}/67（公式五十音順）】
{name_display} 議員（{party}／{district}）

◆注力政策：{policy_str}
◆AI分析：{ai_str}

▼看板公約・議案採決のファクト照合
{encoded_url}
#京都市会 #京都市政
"""
        results.append(post)

        if current_dt.hour == 12:
            current_dt = current_dt.replace(hour=18)
        else:
            current_dt = (current_dt + datetime.timedelta(days=1)).replace(hour=12)

    OUTPUT_FILE.write_text("\n".join(results), encoding="utf-8")
    print(f"✅ 完了！ {OUTPUT_FILE.resolve()} に出力しました。")

if __name__ == "__main__":
    main()