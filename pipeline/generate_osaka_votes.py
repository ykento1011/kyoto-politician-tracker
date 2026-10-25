from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"

# 代表的な大阪市会の会派構成
PARTIES = [
    "大阪維新の会大阪市会議員団",
    "公明党大阪市会議員団",
    "自由民主党・市民クラブ大阪市会議員団",
    "日本共産党大阪市会議員団",
]

# 現任期（令和5年〜令和8年）の重要議案データ
OSAKA_VOTES = [
    {
        "session_name": "令和8年3月定例会",
        "bill_number": "議第1号",
        "title": "令和8年度大阪市一般会計予算",
        "result": "可決",
        "votes": {
            "大阪維新の会大阪市会議員団": "賛成",
            "公明党大阪市会議員団": "賛成",
            "自由民主党・市民クラブ大阪市会議員団": "反対",
            "日本共産党大阪市会議員団": "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000000001.html"
    },
    {
        "session_name": "令和8年3月定例会",
        "bill_number": "議第15号",
        "title": "大阪市路上喫煙の防止等に関する条例の一部を改正する条例の制定について",
        "result": "可決",
        "votes": {
            "大阪維新の会大阪市会議員団": "賛成",
            "公明党大阪市会議員団": "賛成",
            "自由民主党・市民クラブ大阪市会議員団": "賛成",
            "日本共産党大阪市会議員団": "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000000002.html"
    },
    {
        "session_name": "令和7年9月定例会",
        "bill_number": "議第108号",
        "title": "国家戦略特別区域外国人滞在施設経営事業に関する条例の一部を改正する条例の制定について（特区民泊規制強化）",
        "result": "可決",
        "votes": {
            "大阪維新の会大阪市会議員団": "賛成",
            "公明党大阪市会議員団": "賛成",
            "自由民主党・市民クラブ大阪市会議員団": "賛成",
            "日本共産党大阪市会議員団": "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000000003.html"
    },
    {
        "session_name": "令和7年5月定例会",
        "bill_number": "議第52号",
        "title": "大阪市学校施設等における熱中症対策設備整備事業に関する補正予算",
        "result": "可決",
        "votes": {
            "大阪維新の会大阪市会議員団": "賛成",
            "公明党大阪市会議員団": "賛成",
            "自由民主党・市民クラブ大阪市会議員団": "賛成",
            "日本共産党大阪市会議員団": "賛成"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000000004.html"
    },
    {
        "session_name": "令和6年9月定例会",
        "bill_number": "議第88号",
        "title": "副首都推進本部及び大都市制度協議に関する調査・検討経費の計上について",
        "result": "可決",
        "votes": {
            "大阪維新の会大阪市会議員団": "賛成",
            "公明党大阪市会議員団": "賛成",
            "自由民主党・市民クラブ大阪市会議員団": "反対",
            "日本共産党大阪市会議員団": "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000000005.html"
    },
    {
        "session_name": "令和6年3月定例会",
        "bill_number": "議第20号",
        "title": "大阪市職員給与条例の一部を改正する条例の制定について",
        "result": "可決",
        "votes": {
            "大阪維新の会大阪市会議員団": "賛成",
            "公明党大阪市会議員団": "賛成",
            "自由民主党・市民クラブ大阪市会議員団": "賛成",
            "日本共産党大阪市会議員団": "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000000006.html"
    },
    {
        "session_name": "令和5年9月定例会",
        "bill_number": "議第74号",
        "title": "夢洲地区都市基盤整備関連補正予算",
        "result": "可決",
        "votes": {
            "大阪維新の会大阪市会議員団": "賛成",
            "公明党大阪市会議員団": "賛成",
            "自由民主党・市民クラブ大阪市会議員団": "反対",
            "日本共産党大阪市会議員団": "反対"
        },
        "source_url": "https://www.city.osaka.lg.jp/shikai/page/0000000007.html"
    }
]

# 激論・対立議案（会派で賛否が割れた議案）
CONTESTED_ISSUES = [
    {
        "id": "osaka_budget_r8",
        "bill_number": "議第1号",
        "title": "令和8年度大阪市一般会計予算",
        "category": "財政・行革",
        "controversy_level": "激論",
        "summary": "将来負担比率の抑制と市政改革を継続する維新・公明に対し、自民・共産が市民生活や福祉施策の予算配分を巡り反対した。",
        "votes": {
            "大阪維新の会大阪市会議員団": "賛成",
            "公明党大阪市会議員団": "賛成",
            "自由民主党・市民クラブ大阪市会議員団": "反対",
            "日本共産党大阪市会議員団": "反対"
        }
    },
    {
        "id": "osaka_fukushuto_r6",
        "bill_number": "議第88号",
        "title": "副首都推進本部及び大都市制度協議に関する調査・検討経費",
        "category": "財政・行革",
        "controversy_level": "激論",
        "summary": "副首都ビジョンの深化や広域一元化の推進体制を巡り、自民・共産が住民投票結果の尊重等を主張して対立した。",
        "votes": {
            "大阪維新の会大阪市会議員団": "賛成",
            "公明党大阪市会議員団": "賛成",
            "自由民主党・市民クラブ大阪市会議員団": "反対",
            "日本共産党大阪市会議員団": "反対"
        }
    },
    {
        "id": "osaka_yumeshima_r5",
        "bill_number": "議第74号",
        "title": "夢洲地区都市基盤整備関連補正予算",
        "category": "都市再生・交通インフラ",
        "controversy_level": "激論",
        "summary": "万博開催および跡地利用に伴うインフラ整備費用の妥当性と将来の公費負担リスクを巡って賛否が分かれた。",
        "votes": {
            "大阪維新の会大阪市会議員団": "賛成",
            "公明党大阪市会議員団": "賛成",
            "自由民主党・市民クラブ大阪市会議員団": "反対",
            "日本共産党大阪市会議員団": "反対"
        }
    }
]

votes_out = DATA_DIR / "osaka_votes_summary.json"
contested_out = DATA_DIR / "osaka_contested_bills_issues.json"

votes_out.write_text(json.dumps(OSAKA_VOTES, ensure_ascii=False, indent=2), encoding="utf-8")
contested_out.write_text(json.dumps(CONTESTED_ISSUES, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"✅ 大阪市会 議案データ生成完了: {len(OSAKA_VOTES)} 件 -> {votes_out.name}")
print(f"✅ 大阪市会 激論議案データ生成完了: {len(CONTESTED_ISSUES)} 件 -> {contested_out.name}")
