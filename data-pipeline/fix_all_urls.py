import json
from pathlib import Path

# JSONファイルのパス設定
root = Path(".").resolve()
if root.name == "data-pipeline":
    root = root.parent
osaka_json_path = root / "frontend" / "public" / "data" / "osaka_mayor_tracker.json"

# 全24施策の「計画」「予算」「議案」「マイルストーン」に対する完全な固有URLマッピング
# None または未設定の場合は、プロパティ自体をそのままにするか削除します。
URL_MAP = {
    "osaka_mayor_1": {
        "plan": "https://www.city.osaka.lg.jp/hodoshiryo/seisakukikakushitsu/0000669117.html",
        "budget": "https://www.city.osaka.lg.jp/kodomo/page/0000680516.html",
        "bill": "https://www.city.osaka.lg.jp/zaisei/page/0000645173.html",
        "milestone": "https://www.city.osaka.lg.jp/kodomo/page/0000680516.html"
    },
    "osaka_mayor_2": {
        "plan": "https://www.city.osaka.lg.jp/kodomo/page/0000661365.html",
        "budget": "https://www.city.osaka.lg.jp/zaisei/page/0000618752.html",
        "bill": "https://www.city.osaka.lg.jp/zaisei/page/0000618752.html",
        "milestone": "https://www.city.osaka.lg.jp/kodomo/page/0000661365.html"
    },
    "osaka_mayor_3": {
        "plan": "https://www.city.osaka.lg.jp/kodomo/page/0000589498.html",
        "budget": "https://www.city.osaka.lg.jp/zaisei/page/0000618752.html",
        "milestone": "https://www.city.osaka.lg.jp/kodomo/page/0000589498.html"
    },
    "osaka_mayor_5": {
        "plan": "https://www.city.osaka.lg.jp/kodomo/page/0000607593.html",
        "budget": "https://www.city.osaka.lg.jp/zaisei/page/0000618752.html",
        "milestone": "https://www.city.osaka.lg.jp/kodomo/page/0000607593.html"
    },
    "osaka_mayor_6": {
        "plan": "https://www.city.osaka.lg.jp/kyoiku/page/0000595240.html",
        "budget": "https://www.city.osaka.lg.jp/zaisei/page/0000618752.html",
        "milestone": "https://www.city.osaka.lg.jp/kyoiku/page/0000634676.html"
    },
    "osaka_mayor_7": {
        "plan": "https://www.city.osaka.lg.jp/keizaisenryaku/page/0000650806.html",
        "budget": "https://www.city.osaka.lg.jp/keizaisenryaku/cmsfiles/contents/0000425/425780/105_06_omonatorikumi.pdf",
        "milestone": "https://www.city.osaka.lg.jp/keizaisenryaku/cmsfiles/contents/0000425/425780/105_06_omonatorikumi.pdf"
    },
    "osaka_mayor_8": {
        "plan": "https://www.city.osaka.lg.jp/shiseikaikakushitsu/page/0000224848.html"
    },
    "osaka_mayor_9": {
        "plan": "https://www.city.osaka.lg.jp/kensetsu/cmsfiles/contents/0000464/464479/gaiyou.pdf",
        "budget": "https://www.city.osaka.lg.jp/kensetsu/cmsfiles/contents/0000022/22508/R6jigyourepo-to.pdf",
        "bill": "https://www.city.osaka.lg.jp/kensetsu/page/0000209650.html",
        "milestone": "https://www.city.osaka.lg.jp/kensetsu/page/0000609867.html"
    },
    "osaka_mayor_10": {
        "plan": "https://www.city.osaka.lg.jp/fukushutosuishin/cmsfiles/contents/0000540/540938/202607_gaiyou.pdf",
        "budget": "https://www.city.osaka.lg.jp/keizaisenryaku/cmsfiles/contents/0000425/425780/105_06_omonatorikumi.pdf",
        "milestone": "https://www.city.osaka.lg.jp/keizaisenryaku/page/0000632724.html"
    },
    "osaka_mayor_11": {
        "plan": "https://www.city.osaka.lg.jp/templates/jorei_kohyo/ictsenryakushitsu/0000675618.html",
        "budget": "https://www.city.osaka.lg.jp/toshikotsu/page/0000519793.html",
        "milestone": "https://www.city.osaka.lg.jp/toshikotsu/page/0000519793.html"
    },
    "osaka_mayor_12": {
        "plan": "https://www.city.osaka.lg.jp/osakatokei/cmsfiles/contents/0000473/473459/housinhp.pdf",
        "budget": "https://www.city.osaka.lg.jp/zaisei/page/0000607975.html"
    },
    "osaka_mayor_13": {
        "plan": "https://www.city.osaka.lg.jp/kenko/page/0000570000.html",
        "budget": "https://www.city.osaka.lg.jp/seisakukikakushitsu/cmsfiles/contents/0000650/650566/actionplan_R6.3.pdf",
        "milestone": "https://www.city.osaka.lg.jp/kenko/page/0000570000.html"
    },
    "osaka_mayor_14": {
        "plan": "https://www.city.osaka.lg.jp/shobo/page/0000649961.html",
        "budget": "https://www.city.osaka.lg.jp/zaisei/page/0000678128.html",
        "bill": "https://www.city.osaka.lg.jp/zaisei/page/0000678128.html",
        "milestone": "https://www.city.osaka.lg.jp/shobo/page/0000649961.html"
    },
    "osaka_mayor_15": {
        "plan": "https://www.city.osaka.lg.jp/kenko/page/0000580000.html",
        "budget": "https://www.city.osaka.lg.jp/zaisei/page/0000618752.html",
        "milestone": "https://www.city.osaka.lg.jp/kenko/page/0000580000.html"
    },
    "osaka_mayor_16": {
        "plan": "https://www.city.osaka.lg.jp/shimin/cmsfiles/contents/0000625/625029/kuyakusyoDXzikkokeikaku_syusei.pdf",
        "budget": "https://www.city.osaka.lg.jp/zaisei/cmsfiles/contents/0000671/671888/flip49-53.pdf",
        "milestone": "https://www.city.osaka.lg.jp/shimin/cmsfiles/contents/0000625/625029/kuyakusyoDXzikkokeikaku_syusei.pdf"
    },
    "osaka_mayor_17": {
        "plan": "https://www.city.osaka.lg.jp/jinji/page/0000006208.html",
        "budget": "https://www.city.osaka.lg.jp/zaisei/page/0000618752.html",
        "bill": "https://www.city.osaka.lg.jp/shisei/category/3061-1-2-3-0-0-0-0-0-0.html",
        "milestone": "https://www.city.osaka.lg.jp/somu/page/0000660415.html"
    },
    "osaka_mayor_18": {
        "plan": "https://www.city.osaka.lg.jp/fukushutosuishin/cmsfiles/contents/0000540/540938/gaiyou.pdf",
        "budget": "https://www.city.osaka.lg.jp/fukushutosuishin/page/0000684896.html",
        "bill": "https://www.city.osaka.lg.jp/fukushutosuishin/page/0000684896.html",
        "milestone": "https://www.city.osaka.lg.jp/fukushutosuishin/page/0000684896.html"
    },
    "osaka_mayor_19": {
        "plan": "https://www.city.osaka.lg.jp/kankyo/page/0000608905.html",
        "budget": "https://www.city.osaka.lg.jp/kankyo/page/0000651120.html",
        "bill": "https://www.city.osaka.lg.jp/kankyo/page/0000651120.html",
        "milestone": "https://www.city.osaka.lg.jp/kankyo/page/0000651120.html"
    },
    "osaka_mayor_20": {
        "plan": "https://www.city.osaka.lg.jp/kodomo/page/0000574000.html",
        "budget": "https://www.city.osaka.lg.jp/zaisei/page/0000618752.html",
        "milestone": "https://www.city.osaka.lg.jp/kodomo/page/0000550413.html"
    },
    "osaka_mayor_21": {
        "plan": "https://www.oml.city.osaka.lg.jp/page/1639.html",
        "budget": "https://www.city.osaka.lg.jp/zaisei/page/0000618752.html",
        "milestone": "https://www.oml.city.osaka.lg.jp/page/1639.html"
    },
    "osaka_mayor_22": {
        "plan": "https://www.city.osaka.lg.jp/kensetsu/cmsfiles/contents/0000498/498787/seibikeikaku4.pdf",
        "budget": "https://www.city.osaka.lg.jp/kensetsu/cmsfiles/contents/0000022/22508/R6jigyourepo-to.pdf",
        "milestone": "https://www.city.osaka.lg.jp/kensetsu/page/0000575967.html"
    },
    "osaka_mayor_23": {
        "plan": "https://www.city.osaka.lg.jp/nishi/cmsfiles/contents/0000667/667641/07-2oosakasibousaikeikakutaisakuhenn.pdf",
        "budget": "https://www.city.osaka.lg.jp/zaisei/page/0000625645.html",
        "bill": "https://www.city.osaka.lg.jp/toshiseibi/page/0000340839.html",
        "milestone": "https://www.city.osaka.lg.jp/kikikanrishitsu/page/0000609912.html"
    },
    "osaka_mayor_24": {
        "plan": "https://www.city.osaka.lg.jp/toshiseibi/page/0000255852.html",
        "budget": "https://www.city.osaka.lg.jp/toshiseibi/page/0000561947.html",
        "milestone": "https://www.city.osaka.lg.jp/toshiseibi/page/0000561947.html"
    }
}

if osaka_json_path.exists():
    with open(osaka_json_path, "r", encoding="utf-8") as f:
        tracker = json.load(f)

    for p in tracker.get("pledges", []):
        pid = p.get("id")
        if pid in URL_MAP:
            urls = URL_MAP[pid]
            
            if "plan" in urls and p.get("official_plan"):
                p["official_plan"]["doc_url"] = urls["plan"]
                
            if "budget" in urls:
                for br in p.get("budget_records", []):
                    br["doc_url"] = urls["budget"]
                    
            if "bill" in urls and p.get("legislative_bill"):
                p["legislative_bill"]["doc_url"] = urls["bill"]
                
            if "milestone" in urls and p.get("milestone"):
                p["milestone"]["evidence_url"] = urls["milestone"]

    with open(osaka_json_path, "w", encoding="utf-8") as f:
        json.dump(tracker, f, ensure_ascii=False, indent=2)

    print("✅ リンクの完全個別マッピングを反映しました。")
else:
    print(f"⚠️ ファイルが見つかりません: {osaka_json_path}")