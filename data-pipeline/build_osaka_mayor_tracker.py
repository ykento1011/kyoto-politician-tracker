import json
import re
from pathlib import Path

root = Path(".").resolve()
if root.name == "data-pipeline":
    root = root.parent

# 1. 横山英幸市長 公約マニフェスト・マスターデータ定義
MAYOR_PLEDGES = [
    # --- 子育て・教育 ---
    {
        "id": "osaka_mayor_1",
        "category": "子育て・教育",
        "title": "0〜2歳児保育料の無償化（所得制限撤廃）",
        "exact_quote": "0歳〜2歳の保育料無償に関する所得制限撤廃（市）",
        "target_issue": "保育料無償化",
        "stance": "推進・拡充",
        "detail": "第1子を含めた所得制限撤廃による完全無償化の推進と待機児童対策。",
        "keywords": ["保育", "保育料", "保育所", "0歳", "待機児童", "無償化"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_2",
        "category": "子育て・教育",
        "title": "塾代助成事業の所得制限完全撤廃",
        "exact_quote": "塾代助成の所得制限の撤廃（市）",
        "target_issue": "塾代助成",
        "stance": "推進・拡充",
        "detail": "市内中学生等への月額1万円助成における所得制限を完全撤廃。",
        "keywords": ["塾代", "助成", "学校外教育バウチャー", "習い事"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_3",
        "category": "子育て・教育",
        "title": "保険外先進不妊治療への公費助成",
        "exact_quote": "保険適用で賄えない不妊治療への助成（市）",
        "target_issue": "不妊治療支援",
        "stance": "推進・拡充",
        "detail": "保険適用外となる先進生殖医療費に対する市独自の公費助成創設。",
        "keywords": ["不妊治療", "生殖医療", "特定治療"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_4",
        "category": "子育て・教育",
        "title": "インフルエンザワクチンの子育て世帯助成",
        "exact_quote": "インフルエンザワクチンの子育て世帯への助成（市）",
        "target_issue": "小児予防接種",
        "stance": "推進・拡充",
        "detail": "乳幼児・学童期の子どもを対象とした季節性インフルエンザ予防接種費用の軽減。",
        "keywords": ["インフルエンザ", "ワクチン", "予防接種", "小児接種"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_5",
        "category": "子育て・教育",
        "title": "市立保育所における紙おむつの無償提供",
        "exact_quote": "【市】公立保育所での無償おむつ補助",
        "target_issue": "保育所負担軽減",
        "stance": "推進・拡充",
        "detail": "公立保育所において紙おむつを公費調達・無償提供し持ち帰り負担を撤廃。",
        "keywords": ["おむつ", "オムツ", "紙おむつ", "保育所"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_6",
        "category": "子育て・教育",
        "title": "動画授業開発・民間連携と不登校特例校新設",
        "exact_quote": "【市】動画授業の開発・全生徒展開 / 【市】生きる力重視の不登校特例校の設置",
        "target_issue": "公教育改革・不登校支援",
        "stance": "推進・拡充",
        "detail": "GIGAスクール端末を活用した動画授業配信および不登校特例校（学びの多様化学校）設置。",
        "keywords": ["動画授業", "不登校", "特例校", "学びの多様化", "GIGA", "端末"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },

    # --- 成長戦略・副首都圏 ---
    {
        "id": "osaka_mayor_7",
        "category": "都市再生・交通インフラ",
        "title": "会社設立数日本一の推進（設立無償化・融資）",
        "exact_quote": "会社設立数日本一を目指すための設立無償化・融資制度の構築（市）",
        "target_issue": "スタートアップ・創業支援",
        "stance": "推進・拡充",
        "detail": "法人登記関連費用の実質無償化および低利創業融資制度の新設。",
        "keywords": ["創業", "起業", "スタートアップ", "設立", "融資", "中小企業"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_8",
        "category": "都市再生・交通インフラ",
        "title": "大阪メトロ（Osaka Metro）の株式上場準備",
        "exact_quote": "大阪メトロの上場に向けた準備",
        "target_issue": "地下鉄民営化・上場",
        "stance": "推進・拡充",
        "detail": "自立的都市経営と企業価値向上のためのガバナンス強化および株式上場準備。",
        "keywords": ["大阪メトロ", "Osaka Metro", "上場", "株式", "高速電気軌道"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_9",
        "category": "都市再生・交通インフラ",
        "title": "御堂筋フルモール化と都心部再開発",
        "exact_quote": "御堂筋のフルモール化、新大阪の再整備、うめきた2期開発",
        "target_issue": "歩行者空間・都市再生",
        "stance": "推進・拡充",
        "detail": "御堂筋の歩行者専用空間化、うめきた2期（グラングリーン大阪）開発の加速。",
        "keywords": ["御堂筋", "フルモール", "歩行者空間", "うめきた", "グラングリーン", "都市再生"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_10",
        "category": "産業・観光・地域経済",
        "title": "国際金融都市構想とスマートシティ推進",
        "exact_quote": "スマートシティの実現、国際金融都市の実現へ",
        "target_issue": "国際金融都市・都市OS",
        "stance": "推進・拡充",
        "detail": "特区税制等を活用した外資VC誘致と都市データ連携基盤（都市OS）の実装。",
        "keywords": ["国際金融都市", "スマートシティ", "フィンテック", "都市OS", "データ連携"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },

    # --- 万博・IR ---
    {
        "id": "osaka_mayor_11",
        "category": "産業・観光・地域経済",
        "title": "万博先端モビリティ社会実装と大阪版MaaS",
        "exact_quote": "万博時に利用した無人バス等の新型交通を大阪に実装するための部署の創設",
        "target_issue": "自動運転・大阪版MaaS",
        "stance": "推進・拡充",
        "detail": "万博で実証された自動運転バス・新型交通の市内実装専管組織とMaaS網確立。",
        "keywords": ["万博", "MaaS", "自動運転", "オンデマンドバス", "モビリティ", "新型交通"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_12",
        "category": "都市再生・交通インフラ",
        "title": "大阪パビリオンのハードレガシー活用と夢洲まちづくり",
        "exact_quote": "大阪館を活用した夢洲街づくりを / 万博跡地と統合型リゾートの相乗効果",
        "target_issue": "夢洲開発・万博レガシー",
        "stance": "推進・拡充",
        "detail": "大阪ヘルスケアパビリオン資産の会期後活用と統合型リゾート（IR）との相乗拠点化。",
        "keywords": ["夢洲", "大阪館", "パビリオン", "万博跡地", "IR", "統合型リゾート", "MICE"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_13",
        "category": "福祉・医療・健康",
        "title": "包括的依存症対策センターの設置前倒し",
        "exact_quote": "依存症対策センター設置前倒し、総合依存症対策（ゲーム・ネット・スマホ・ギャンブル等）",
        "target_issue": "依存症対策",
        "stance": "推進・拡充",
        "detail": "ギャンブル・ネット等の総合依存症対策拠点の整備スケジュール前倒し。",
        "keywords": ["依存症", "ギャンブル", "ゲーム依存", "相談拠点"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },

    # --- 行財政改革・統治機構改革 ---
    {
        "id": "osaka_mayor_14",
        "category": "財政・行革",
        "title": "府域消防指令機能の統合（大阪消防庁構想）",
        "exact_quote": "大阪市消防局を中心とした府域消防の一元化（司令機能統合）",
        "target_issue": "広域消防・司令一元化",
        "stance": "推進・拡充",
        "detail": "大阪市消防局の指令システムを核とした府内自治体消防の指令機能統合。",
        "keywords": ["消防", "消防局", "指令", "消防司令", "広域化"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_15",
        "category": "福祉・医療・健康",
        "title": "府市公立病院機構の完全統合",
        "exact_quote": "府市病院機構の統合",
        "target_issue": "病院統合・高度医療",
        "stance": "推進・拡充",
        "detail": "大阪府立病院機構と大阪市民病院機構の一本化による高度医療機能集約。",
        "keywords": ["病院機構", "市民病院", "府立病院", "公立病院", "地方独立行政法人"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_16",
        "category": "財政・行革",
        "title": "デジタル統括室の強化と行政窓口DX（書かない窓口）",
        "exact_quote": "【市】デジタル統括室へのIT人材積極採用、役所窓口のオンライン化",
        "target_issue": "行政DX・窓口改革",
        "stance": "推進・拡充",
        "detail": "民間高度IT人材の採用と区役所申請手続きの完全オンライン化・ペーパーレス推進。",
        "keywords": ["DX", "デジタル", "オンライン化", "窓口", "情報化", "ペーパーレス"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_17",
        "category": "財政・行革",
        "title": "身を切る改革と市議会定数の適正化",
        "exact_quote": "知事、市長、町村長の退職金の廃止 / 議員定数削減",
        "target_issue": "政治改革・定数削減",
        "stance": "推進・拡充",
        "detail": "市長退職金の不支給および将来の人口推計を見据えた市議会議員定数削減。",
        "keywords": ["退職金", "定数", "身を切る改革", "議員定数", "報酬"],
        "source_name": "日本維新の会 統一地方選挙2023 政策集",
        "source_url": "https://o-ishin.jp/about/touitsuchihou/"
    },
    {
        "id": "osaka_mayor_18",
        "category": "財政・行革",
        "title": "大阪都構想への再挑戦と任期内住民投票（2026出直し選公約）",
        "exact_quote": "副首都大阪、都構想の設計図作りを大阪の成長につなげる。任期内に3度目の住民投票を実施",
        "target_issue": "大阪都構想・特別区設置",
        "stance": "推進・拡充",
        "detail": "府市の二重行政を恒久的に解消する特別区設置の設計図作成および任期内住民投票の実施。",
        "keywords": ["都構想", "特別区", "大都市地域", "法定協議会", "副首都", "住民投票"],
        "source_name": "2026年出直し大阪市長選 公約",
        "source_url": "https://mainichi.jp/articles/20260517/k00/00m/010/100000c"
    },

    # --- 市民生活・福祉・公衆衛生 ---
    {
        "id": "osaka_mayor_19",
        "category": "くらし・環境・エネルギー",
        "title": "大阪市内全域の路上喫煙禁止と指定喫煙所の整備",
        "exact_quote": "大阪市内全面禁煙に向けた喫煙所整備",
        "target_issue": "路上喫煙禁止・分煙環境",
        "stance": "推進・拡充",
        "detail": "2025年万博前の市内全域（全24区）路上喫煙禁止条例施行と指定喫煙所インフラ増設。",
        "keywords": ["喫煙", "路上喫煙", "たばこ", "タバコ", "受動喫煙", "喫煙所"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_20",
        "category": "福祉・医療・健康",
        "title": "ヤングケアラー・ダブルケア支援と買い物難民対策",
        "exact_quote": "特定検診の拡充、ヤングケアラー／ダブルケア対策の充実、買い物難民対策",
        "target_issue": "多重介護支援・生活支援",
        "stance": "推進・拡充",
        "detail": "多重ケア世帯の実態調査と相談支援窓口の強化、住宅地・団地の移動販売支援。",
        "keywords": ["ヤングケアラー", "ダブルケア", "買い物難民", "移動販売", "介護支援"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_21",
        "category": "文化・景観・歴史",
        "title": "電子図書館サービス拡充と図書宅配推進",
        "exact_quote": "図書館のオンライン化・宅配サービス、犬猫の理由なき殺処分ゼロ",
        "target_issue": "電子図書館・文化施策",
        "stance": "推進・拡充",
        "detail": "市立図書館の電子書籍蔵書拡充および移動困難者に対する宅配スキーム構築。",
        "keywords": ["図書館", "電子図書館", "図書", "オンライン化"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },

    # --- 防災・都市基盤・治安 ---
    {
        "id": "osaka_mayor_22",
        "category": "防災・減災・治安",
        "title": "緊急輸送道路等の無電柱化（電柱地中化）加速",
        "exact_quote": "無電柱化（電柱地中化）の加速",
        "target_issue": "無電柱化・防災インフラ",
        "stance": "推進・拡充",
        "detail": "広域避難路や緊急交通路における電柱地中化の優先施工と整備加速。",
        "keywords": ["無電柱化", "電柱", "地中化", "緊急輸送道路", "防災道路"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_23",
        "category": "防災・減災・治安",
        "title": "指定避難所のインフラ強化（空調・電源・Wi-Fi）",
        "exact_quote": "避難所（公共施設）のインフラ強化、ICT活用の災害情報発信・収集",
        "target_issue": "避難所機能強化",
        "stance": "推進・拡充",
        "detail": "市立小中学校等の指定避難所に非常用Wi-Fi、蓄電池、体育館空調設備等を整備。",
        "keywords": ["避難所", "体育館", "空調", "蓄電池", "防災拠点", "防災対策"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    },
    {
        "id": "osaka_mayor_24",
        "category": "防災・減災・治安",
        "title": "木造住宅密集市街地対策と街頭防犯カメラ網拡充",
        "exact_quote": "密集市街地整備・耐震化、防犯カメラの増設による犯罪抑止",
        "target_issue": "密集市街地・防犯カメラ",
        "stance": "推進・拡充",
        "detail": "木密地域の老朽家屋解体支援・耐震化と通学路等への街頭防犯カメラ増設。",
        "keywords": ["密集市街地", "木密", "耐震化", "防犯カメラ", "老朽家屋", "防犯"],
        "source_name": "大阪維新の会 2023 大阪府市政策集（マニフェスト）",
        "source_url": "https://oneosaka.jp/touitsu2023/pdf/ishinfugidan_manifesto2023_compressed.pdf"
    }
]

# 2. 議決・議案データの探索と照合
bills_file = root / "data-pipeline" / "data" / "osaka_bills.json"
votes_file = root / "data-pipeline" / "data" / "osaka_council_votes.json"

bills = []
if bills_file.exists():
    with open(bills_file, "r", encoding="utf-8") as f:
        bills = json.load(f)
elif votes_file.exists():
    with open(votes_file, "r", encoding="utf-8") as f:
        votes_data = json.load(f)
        if isinstance(votes_data, list):
            bills = votes_data
        elif isinstance(votes_data, dict):
            bills = votes_data.get("bills", [])

print(f"📋 参照議案数: {len(bills)} 件")

# 3. 公約ごとの議案マッチングと進捗判定
tracked_mayor_pledges = []
for p in MAYOR_PLEDGES:
    matched_bills = []
    keywords = p.get("keywords", [])
    
    for b in bills:
        title = b.get("title", "") or b.get("bill_name", "") or ""
        summary = b.get("summary", "") or b.get("reason", "") or ""
        text = f"{title} {summary}"
        
        # キーワード照合（複数キーワードのうち1つ以上ヒット）
        hit = any(kw.lower() in text.lower() for kw in keywords)
        if hit:
            matched_bills.append({
                "bill_id": b.get("id") or b.get("bill_id") or "",
                "title": title,
                "result": b.get("result", "可決"),
                "date": b.get("date", "")
            })
            
    # ステータス判定ロジック
    if len(matched_bills) >= 2:
        status = "着手済・進展中"
        status_color = "green"
    elif len(matched_bills) == 1:
        status = "着手済"
        status_color = "blue"
    else:
        status = "検討・推進中"
        status_color = "orange"
        
    p_copy = dict(p)
    del p_copy["keywords"]
    p_copy["status"] = status
    p_copy["status_color"] = status_color
    p_copy["matched_bills_count"] = len(matched_bills)
    p_copy["related_bills"] = matched_bills[:5] # 最大5件を表示用に格納
    tracked_mayor_pledges.append(p_copy)

# 4. 市長政策トラッカーのペイロード構築
mayor_payload = {
    "mayor_name": "横山 英幸",
    "term": "2023年4月〜（2026年出直し選を経て続投）",
    "party": "大阪維新の会",
    "slogan": "大阪を前へ、維新は挑戦をやめない",
    "total_pledges": len(tracked_mayor_pledges),
    "categories": [
        "子育て・教育",
        "都市再生・交通インフラ",
        "産業・観光・地域経済",
        "財政・行革",
        "くらし・環境・エネルギー",
        "福祉・医療・健康",
        "防災・減災・治安",
        "文化・景観・歴史"
    ],
    "pledges": tracked_mayor_pledges
}

# 5. フロントエンド向けJSONの書き出し
targets = [
    root / "frontend" / "public" / "data" / "mayor_pledge_tracker_osaka.json",
    root / "frontend" / "public" / "data" / "osaka" / "mayor_pledge_tracker.json",
    root / "frontend" / "dist" / "data" / "mayor_pledge_tracker_osaka.json",
    root / "frontend" / "dist" / "data" / "osaka" / "mayor_pledge_tracker.json",
    root / "data-pipeline" / "data" / "mayor_pledge_tracker_osaka.json"
]

for t in targets:
    t.parent.mkdir(parents=True, exist_ok=True)
    with open(t, "w", encoding="utf-8") as f:
        json.dump(mayor_payload, f, ensure_ascii=False, indent=2)

print(f"🎉 横山市長政策トラッカー（全 {len(tracked_mayor_pledges)} 項目）の生成が完了しました！")
print("出力先:", targets[0])
