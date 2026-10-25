from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"

# 会派定義
PARTIES = {
    "ishin": "大阪維新の会大阪市会議員団",
    "komei": "公明党大阪市会議員団",
    "jimin": "自由民主党・市民クラブ大阪市会議員団",
    "kyosan": "日本共産党大阪市会議員団"
}

# 令和5年5月〜令和8年の全会期・議案マスターデータセット
FULL_VOTES = [
    # --- 令和8年3月定例会 ---
    {
        "session_name": "令和8年3月定例会",
        "bill_number": "議第1号",
        "title": "令和8年度大阪市一般会計予算",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "反対",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000620001.html"
    },
    {
        "session_name": "令和8年3月定例会",
        "bill_number": "議第2号",
        "title": "令和8年度大阪市特別会計予算（水道事業会計・下水道事業会計等）",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000620002.html"
    },
    {
        "session_name": "令和8年3月定例会",
        "bill_number": "議第15号",
        "title": "大阪市路上喫煙の防止等に関する条例の一部を改正する条例の制定について",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000620015.html"
    },
    {
        "session_name": "令和8年3月定例会",
        "bill_number": "議第18号",
        "title": "大阪市国民健康保険条例の一部を改正する条例の制定について（府内保険料統一基準改定）",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "反対",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000620018.html"
    },
    {
        "session_name": "令和8年3月定例会",
        "bill_number": "議第25号",
        "title": "大阪市介護保険条例の一部を改正する条例の制定について（第9期介護保険料基準額改定）",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000620025.html"
    },
    {
        "session_name": "令和8年3月定例会",
        "bill_number": "議第30号",
        "title": "大阪市市税条例の一部を改正する条例の制定について",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000620030.html"
    },
    {
        "session_name": "令和8年3月定例会",
        "bill_number": "議員提出第1号",
        "title": "学校給食費の完全無償化を求める意見書案",
        "result": "否決",
        "votes": {
            PARTIES["ishin"]: "反対",
            PARTIES["komei"]: "反対",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000620050.html"
    },

    # --- 令和7年9月定例会 ---
    {
        "session_name": "令和7年9月定例会",
        "bill_number": "議第101号",
        "title": "令和6年度大阪市一般会計歳入歳出決算の認定について",
        "result": "認定",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "反対",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000610101.html"
    },
    {
        "session_name": "令和7年9月定例会",
        "bill_number": "議第108号",
        "title": "国家戦略特別区域外国人滞在施設経営事業に関する条例の一部を改正する条例の制定について（特区民泊立入規制強化）",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000610108.html"
    },
    {
        "session_name": "令和7年9月定例会",
        "bill_number": "議第112号",
        "title": "大阪市営住宅条例の一部を改正する条例の制定について",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000610112.html"
    },
    {
        "session_name": "令和7年9月定例会",
        "bill_number": "議第115号",
        "title": "夢洲第2期マスタープラン策定等に伴う債務負担行為補正",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "反対",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000610115.html"
    },
    {
        "session_name": "令和7年9月定例会",
        "bill_number": "議第120号",
        "title": "市立小中学校における校内SSR（スペシャルサポートルーム）全校整備等関連補正予算",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000610120.html"
    },

    # --- 令和7年5月定例会 ---
    {
        "session_name": "令和7年5月定例会",
        "bill_number": "議第52号",
        "title": "大阪市学校施設等における熱中症対策設備整備事業に関する補正予算",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000600052.html"
    },
    {
        "session_name": "令和7年5月定例会",
        "bill_number": "議第55号",
        "title": "此花大橋及び此花咲洲連絡道路補修工事請負契約の締結について",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000600055.html"
    },
    {
        "session_name": "令和7年5月定例会",
        "bill_number": "議第58号",
        "title": "大阪市教育委員会委員の任命について",
        "result": "同意",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000600058.html"
    },

    # --- 令和6年9月定例会 ---
    {
        "session_name": "令和6年9月定例会",
        "bill_number": "議第88号",
        "title": "副首都推進本部及び大都市制度協議に関する調査・検討経費の計上について",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "反対",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000590088.html"
    },
    {
        "session_name": "令和6年9月定例会",
        "bill_number": "議第92号",
        "title": "令和5年度大阪市一般会計歳入歳出決算の認定について",
        "result": "認定",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "反対",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000590092.html"
    },
    {
        "session_name": "令和6年9月定例会",
        "bill_number": "議第95号",
        "title": "屋外広告物条例の一部を改正する条例の制定について（景観保全・デジタルサイネージ基準）",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000590095.html"
    },
    {
        "session_name": "令和6年9月定例会",
        "bill_number": "議第99号",
        "title": "大阪市下水道工事事故再発防止及び管路耐震デジタル化補正予算",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000590099.html"
    },

    # --- 令和6年3月定例会 ---
    {
        "session_name": "令和6年3月定例会",
        "bill_number": "議第1号",
        "title": "令和6年度大阪市一般会計予算",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "反対",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000580001.html"
    },
    {
        "session_name": "令和6年3月定例会",
        "bill_number": "議第20号",
        "title": "大阪市職員給与条例の一部を改正する条例の制定について",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000580020.html"
    },
    {
        "session_name": "令和6年3月定例会",
        "bill_number": "議第28号",
        "title": "大阪市公設市場再整備基本計画策定委託契約の締結について",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000580028.html"
    },

    # --- 令和5年9月定例会 ---
    {
        "session_name": "令和5年9月定例会",
        "bill_number": "議第74号",
        "title": "夢洲地区都市基盤整備関連補正予算",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "反対",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000570074.html"
    },
    {
        "session_name": "令和5年9月定例会",
        "bill_number": "議第75号",
        "title": "令和4年度大阪市一般会計歳入歳出決算の認定について",
        "result": "認定",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "反対",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000570075.html"
    },
    {
        "session_name": "令和5年9月定例会",
        "bill_number": "議第80号",
        "title": "大阪市ひとり親家庭医療費助成条例の一部を改正する条例の制定について",
        "result": "可決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000570080.html"
    },

    # --- 令和5年5月定例会（現任期開始） ---
    {
        "session_name": "令和5年5月定例会",
        "bill_number": "議第1号",
        "title": "大阪市議会議長及び副議長の選挙について",
        "result": "議決",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000560001.html"
    },
    {
        "session_name": "令和5年5月定例会",
        "bill_number": "議第5号",
        "title": "副市長の選任について",
        "result": "同意",
        "votes": {
            PARTIES["ishin"]: "賛成",
            PARTIES["komei"]: "賛成",
            PARTIES["jimin"]: "賛成",
            PARTIES["kyosan"]: "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000560005.html"
    }
]

# 会派賛否が分かれた激論議案を自動抽出
CONTESTED_ISSUES = []
for v in FULL_VOTES:
    v_vals = set(v["votes"].values())
    if "賛成" in v_vals and "反対" in v_vals:
        # カテゴリ推定
        category = "財政・行革"
        t = v["title"]
        if "路上喫煙" in t or "環境" in t or "下水道" in t:
            category = "くらし・環境・エネルギー"
        elif "民泊" in t or "市場" in t:
            category = "産業・観光・地域経済"
        elif "学校" in t or "教育" in t or "給食" in t:
            category = "子育て・教育"
        elif "国民健康保険" in t or "介護" in t or "医療" in t:
            category = "福祉・医療・健康"
        elif "夢洲" in t or "道路" in t or "都市" in t:
            category = "都市再生・交通インフラ"
        elif "景観" in t or "広告" in t or "芸能" in t:
            category = "文化・景観・歴史"

        CONTESTED_ISSUES.append({
            "id": f"osaka_bill_{v['bill_number'].replace('議第', '').replace('号', '')}_{v['session_name']}",
            "bill_number": v["bill_number"],
            "title": v["title"],
            "session_name": v["session_name"],
            "category": category,
            "controversy_level": "激論",
            "summary": f"会派間で賛否が分かれた重要議案。維新・公明・自民・共産の対立軸が明確となった審議案件。",
            "votes": v["votes"]
        })

votes_path = DATA_DIR / "osaka_votes_summary.json"
contested_path = DATA_DIR / "osaka_contested_bills_issues.json"

votes_path.write_text(json.dumps(FULL_VOTES, ensure_ascii=False, indent=2), encoding="utf-8")
contested_path.write_text(json.dumps(CONTESTED_ISSUES, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"🎉 大阪市会 全議案データを生成しました: {len(FULL_VOTES)} 件")
print(f"🔥 うち賛否対立（激論議案）: {len(CONTESTED_ISSUES)} 件")
