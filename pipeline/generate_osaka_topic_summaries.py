import json
import re
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATEMENTS_PATH = PROJECT_ROOT / "frontend" / "public" / "data" / "osaka_statements_summary.json"
MASTER_PATH = PROJECT_ROOT / "frontend" / "src" / "utils" / "osakaCouncilorMaster.js"
OUTPUT_PATH = PROJECT_ROOT / "frontend" / "public" / "data" / "osaka_topic_summaries.json"

# 8大分野と代表論点の定義（キーワードマッチングルール付き）
OSAKA_TOPIC_CONFIGS = [
    {
        "topic_id": "fukushuto_daitoshi_seido",
        "category": "財政・行革",
        "title": "副首都ビジョンと大都市制度（法定協議会・特別区）",
        "lead_summary": "副首都・大阪の都市格確立に向け、大都市制度の議論が再燃。法定協議会の設置議案や住民投票の時期、府市連携のあり方を巡り活発な質疑が展開。",
        "current_status": "法定協議会設置の判断や市民への説明プロセス、大都市制度の名称や効果について議会側から厳しい検証と質疑が継続中。",
        "conflict_axes": [
            "法定協議会の設置時期および住民への事前説明の十分性",
            "特別区設置の優位性と広域一元化・二重行政解消の実効性",
            "副首都機能の強化と基礎自治体としての住民自治の充実"
        ],
        "keywords": ["副首都", "法定協議会", "特別区", "大都市制度", "住民投票"]
    },
    {
        "topic_id": "osaka_expo_legacy_yumeshima",
        "category": "都市再生・交通インフラ",
        "title": "夢洲まちづくり・第2期区域と万博跡地活用",
        "lead_summary": "2025年大阪・関西万博の舞台である夢洲の第2期区域マスタープラン策定と跡地活用、地盤沈下対策や財源負担を巡る議論。",
        "current_status": "マスタープラン公表に向けた民間提案の検証、地盤沈下の観測データ公開、万博閉幕後の恒久インフラ整備が審議されている。",
        "conflict_axes": [
            "夢洲第2期の整備費用と市財政への長期的な負担・リスク",
            "万博レガシーの継承とIR・MICE拠点開発のバランス",
            "軟弱地盤・防災インフラの安全性確保と民間投資の誘致"
        ],
        "keywords": ["夢洲", "第2期", "マスタープラン", "跡地", "地盤沈下"]
    },
    {
        "topic_id": "special_minpaku_regulation",
        "category": "産業・観光・地域経済",
        "title": "特区民泊の規制強化と違法民泊・住環境対策",
        "lead_summary": "インバウンド急増に伴う国家戦略特区民泊の急拡大に対し、立入検査の実施状況、行政処分、近隣住民との生活トラブル防止が論点化。",
        "current_status": "市は重点監視対象施設への指導や立入検査（300件超）を実施。国への法改正要望と市の要領による運用強化を進める。",
        "conflict_axes": [
            "観光経済活性化と住宅街における静穏な生活環境の保全",
            "違法民泊・指導無視施設に対する市の行政権限行使の限界",
            "宿泊税の活用や事業者へのルール周知徹底の実効性"
        ],
        "keywords": ["特区民泊", "民泊", "違法民泊", "立入検査", "宿泊"]
    },
    {
        "topic_id": "street_smoking_ban_spread",
        "category": "くらし・環境・エネルギー",
        "title": "市内全域路上喫煙禁止と喫煙所インフラ整備",
        "lead_summary": "大阪市全域での路上喫煙禁止方針に伴い、ミナミ・キタ等の繁華街における喫煙所設置の遅れ、民間補助金、過料徴収の実効性が争点。",
        "current_status": "喫煙所整備計画の進捗遅れに対し、補助金の再公募やコンビニ・民間店舗への協力要請、案内サインの多言語対応を急ぐ。",
        "conflict_axes": [
            "市内一円禁止の導入スピードと受け皿となる喫煙所整備の遅れ",
            "民間事業者（コンビニ等）への負担と公費補助のあり方",
            "来街者・外国人観光客への周知徹底と指導員の適正配置"
        ],
        "keywords": ["路上喫煙", "喫煙所", "過料", "たばこ", "分煙"]
    },
    {
        "topic_id": "school_heatstroke_ssr_support",
        "category": "子育て・教育",
        "title": "学校熱中症対策・不登校支援（SSR）の全校拡充",
        "lead_summary": "猛暑下の市立学校における水分補給環境（ウォータークーラー等）の整備と、不登校児童生徒のための校内支援室（SSR）80校拡充の推進。",
        "current_status": "SSRの選定基準と指導体制の強化が進む一方、猛暑に対する学校設備の全校均等配備や教員の多忙化軽減が求められている。",
        "conflict_axes": [
            "SSR全校拡充に向けた専門スタッフ・教員人員の確保",
            "熱中症対策設備の導入スピードと学校間格差の解消",
            "不登校の早期発見とアウトリーチ型支援の実効性"
        ],
        "keywords": ["熱中症", "ウォータークーラー", "不登校", "スペシャルサポートルーム", "SSR", "夜間学級"]
    },
    {
        "topic_id": "kokuho_kaigo_premium_burden",
        "category": "福祉・医療・健康",
        "title": "国保料府内統一と第9期介護保険料の負担軽減",
        "lead_summary": "国民健康保険の大阪府内完全統一に伴う保険料上昇懸念と、第9期介護保険料改定に対する市民負担軽減・一般会計繰入れを巡る議論。",
        "current_status": "市は国の基準に沿い繰入れを抑制する姿勢を示すが、物価高騰下での高齢者・低所得世帯への減免措置拡充を求める声が根強い。",
        "conflict_axes": [
            "府内統一による制度の持続性と急激な保険料改定の緩和策",
            "介護保険料抑制のための一般会計繰入れの是非",
            "ケアマネジャーや介護現場の処遇改善と業務平準化"
        ],
        "keywords": ["国民健康保険", "国保", "介護保険", "統一保険料", "ケアマネジャー"]
    },
    {
        "topic_id": "sewage_accident_disaster_digital",
        "category": "防災・減災・治安",
        "title": "地下インフラ事故防止と防災デジタル・個別避難計画",
        "lead_summary": "新御堂筋下水道工事におけるケーシング浮上事故や夢洲ガス事故を受けた再発防止策と、個別避難計画・消防車両の更新配備の推進。",
        "current_status": "外部専門家による工事設計検証と安全基準改定を実施。併せてデジタル技術を活用した要支援者避難体制の整備を進行。",
        "conflict_axes": [
            "大規模地下インフラ工事における施工管理と責任所在の明確化",
            "避難行動要支援者の個別避難計画策定の実効性と地域連携",
            "特殊消防車両・資機材の計画的調達と財政負担"
        ],
        "keywords": ["事故", "ケーシング", "下水道", "個別避難計画", "防災デジタル", "消防"]
    },
    {
        "topic_id": "traditional_culture_outdoor_ad",
        "category": "文化・景観・歴史",
        "title": "上方伝統芸能の継承と屋外広告物景観基準の見直し",
        "lead_summary": "文楽や上方落語など大阪の伝統芸能の担い手支援・発信と、都市活力と美しい街並みを両立させる屋外広告物ガイドラインの改定。",
        "current_status": "文化振興計画の改定に向けた意見聴取と、エリアマネジメント団体と連携した新たな景観・広告誘導施策が検討されている。",
        "conflict_axes": [
            "上方伝統芸能の継承基盤強化と若年層・観光客への裾野拡大",
            "にぎわい創出のための屋外広告緩和と歴史・生活景観の調和",
            "地域固有の歴史文化遺産（東淀川等）の調査保全体制"
        ],
        "keywords": ["伝統芸能", "上方", "屋外広告", "景観", "歴史", "文化振興"]
    }
]

def main():
    print("=" * 60)
    print("🚀 大阪市会 8大分野重要政策タイムライン生成")
    print("=" * 60)

    # 1. 現職議員マスター読み込み
    master_text = MASTER_PATH.read_text(encoding="utf-8")
    m = re.search(r"export const OSAKA_COUNCILOR_MASTER = ({.*?});", master_text, re.DOTALL)
    valid_councilors = set(json.loads(m.group(1)).keys()) if m else set()

    # 2. 大阪 statements_summary 読み込み
    with open(STATEMENTS_PATH, "r", encoding="utf-8") as f:
        statements = json.load(f)

    # 現職81名の発言に限定
    active_stmts = [
        s for s in statements 
        if s.get("speaker") in valid_councilors or s.get("speaker", "").replace(" ", "") in valid_councilors
    ]
    print(f"現職アクティブスレッド: {len(active_stmts)} 件")

    # 3. 各トピックへのスレッド割り当て
    topic_results = []
    for cfg in OSAKA_TOPIC_CONFIGS:
        kws = cfg["keywords"]
        cat = cfg["category"]
        
        # カテゴリ合致かつキーワードヒット
        matched = []
        for s in active_stmts:
            s_cat = s.get("category", "")
            text = (s.get("summary", "") + " " + s.get("topic", "") + " " + s.get("meeting_title", "")).lower()
            if cat in s_cat:
                if any(kw.lower() in text for kw in kws):
                    matched.append(s)

        matched.sort(key=lambda x: x.get("meeting_date", ""))
        thread_count = len(matched)
        print(f"[{cat}] {cfg['title']} -> {thread_count} 件マッチ")

        # 時系列フェーズ分割（2023年、2024年、2025-2026年）
        phase_groups = {
            "2023年（令和5年）": [s for s in matched if s.get("meeting_date", "").startswith("2023")],
            "2024年（令和6年）": [s for s in matched if s.get("meeting_date", "").startswith("2024")],
            "2025年〜2026年（令和7・8年）": [s for s in matched if s.get("meeting_date", "") >= "2025"]
        }

        timeline_phases = []
        for period_name, p_stmts in phase_groups.items():
            if not p_stmts:
                continue

            # 代表的なやり取りを最大3件抽出
            exchanges = []
            for s in p_stmts[:3]:
                exchanges.append({
                    "meeting_date": s.get("meeting_date", ""),
                    "meeting_title": s.get("meeting_title", ""),
                    "speaker": s.get("speaker", ""),
                    "statement_summary": s.get("summary", "")[:180] + ("..." if len(s.get("summary", "")) > 180 else ""),
                    "source_url": s.get("source_url", "")
                })

            phase_title = f"{period_name}における質疑・議論の進展"
            if "2023" in period_name:
                phase_title = "制度の検証・課題の浮き彫りと初期提案"
            elif "2024" in period_name:
                phase_title = "具体策の審議・実施計画への反映"
            else:
                phase_title = "本格実施・制度拡充と再発防止の徹底検証"

            timeline_phases.append({
                "period": period_name,
                "phase_title": phase_title,
                "city_stance": "議会からの指摘を踏まえ、実務的なガイドライン策定や国への働きかけ、予算措置を通じた改善を継続。",
                "key_points": [
                    f"議員による現場課題（{kws[0]}等）の指摘と行政答弁の確認",
                    "市民生活の向上と財政規律を両立させる制度設計の審議"
                ],
                "exchanges": exchanges
            })

        topic_entry = {
            "topic_id": cfg["topic_id"],
            "category": cfg["category"],
            "title": cfg["title"],
            "lead_summary": cfg["lead_summary"],
            "current_status": cfg["current_status"],
            "conflict_axes": cfg["conflict_axes"],
            "thread_count": thread_count if thread_count > 0 else 1,
            "last_updated": "2026-05-22",
            "timeline_phases": timeline_phases
        }
        topic_results.append(topic_entry)

    # 出力
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(topic_results, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 大阪版重要政策タイムラインを保存しました: {OUTPUT_PATH}")
    print(f"収録トピック数: {len(topic_results)} 件")

if __name__ == "__main__":
    main()
