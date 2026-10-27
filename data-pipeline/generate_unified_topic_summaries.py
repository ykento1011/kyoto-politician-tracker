import json
import re
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==========================================
# 1. 各都市の代表論点マスタ定義（8大政策カテゴリ準拠）
# ==========================================

NAGOYA_TOPIC_CONFIGS = [
    {
        "topic_id": "nagoya_castle_wooden_restoration",
        "category": "文化・景観・歴史",
        "title": "名古屋城天守閣木造復元事業とバリアフリー設備（エレベーター）設置",
        "lead_summary": "特別史跡名古屋城跡における天守閣木造復元事業に関し、史実に忠実な復元と障がい者・高齢者に配慮した昇降設備（エレベーター）設置、石垣保全対策、資金計画を巡る議論。",
        "current_status": "文化庁の復元検討委員会への申請や垂直昇降設備の仕様協議が進む一方、当事者参画による対話の継続や市民説明会の実施、物価高に伴う資金計画の再検証が焦点となっている。",
        "conflict_axes": [
            "史実に忠実な木造復元と誰にでも開かれたバリアフリー（エレベーター等）の両立",
            "重要文化財としての石垣等遺構の保存と工事に伴う技術的安全性",
            "資材高騰等を踏まえた総事業費の推移と金シャチ募金を含む資金計画の妥当性"
        ],
        "keywords": ["名古屋城", "木造復元", "木造天守", "天守閣整備", "エレベーター", "垂直昇降設備", "バリアフリー", "石垣"]
    },
    {
        "topic_id": "keiro_pass_reform",
        "category": "福祉・医療・健康",
        "title": "敬老パス制度の持続可能性と利用料・上限額の見直し",
        "lead_summary": "70歳以上の高齢者の移動と健康増進を支える敬老パスについて、利用料引き下げの是非や持続可能性、年730回の上限設定、利用実態に応じた複数プラン導入を巡る議論。",
        "current_status": "市民アンケート結果や健康増進・送迎負担軽減の経済効果が示される一方、福祉総合システムの標準化改修や財政状況を理由とした実施時期、暫定上限額のあり方が審議されている。",
        "conflict_axes": [
            "利用料一律引き下げ（マニフェスト）の早期実現と財政負担・暫定上限額の維持",
            "利用回数に応じた選べる複数プラン導入による受益者負担の公平性",
            "高齢者の社会参加・健康維持効果と若い現役世代の負担感のバランス"
        ],
        "keywords": ["敬老パス", "一部負担金", "利用料値下げ", "暫定上限額", "交付率", "福祉総合システム"]
    },
    {
        "topic_id": "yatomi_aioiyama_road",
        "category": "都市再生・交通インフラ",
        "title": "弥富相生山線道路整備事業とヒメボタル生息地保全（折衷案）",
        "lead_summary": "昭和32年の都市計画決定以来、相生山緑地の自然環境保護と周辺地域の交通渋滞緩和・防災機能強化の間で長年対立が続いてきた弥富相生山線の道路整備事業。",
        "current_status": "橋梁構造による環境配慮と一般車通行を認める「折衷案」が提示され、詳細設計とモニタリング計画の策定、地域分断防止に向けた市民説明が進められている。",
        "conflict_axes": [
            "ヒメボタル生息地などの貴重な自然環境保全と緊急避難路・生活道路の確保",
            "折衷案における一般車両通行の可否と通過交通流入による生活環境への影響",
            "長年にわたる住民間の意見対立に対する行政の丁寧な合意形成と説明責任"
        ],
        "keywords": ["弥富相生山線", "相生山", "ヒメボタル", "折衷案"]
    },
    {
        "topic_id": "higashi_ward_office_relocation",
        "category": "財政・行革",
        "title": "東区役所等庁舎の老朽化と移転整備方針（愛知大学車道校舎・建中寺）",
        "lead_summary": "築50年を超え老朽化・狭隘化が進む東区役所庁舎について、保健所や土木事務所との同一庁舎化、愛知大学車道校舎への移転案や現地建て替え案を巡る審議。",
        "current_status": "愛知大学車道校舎の活用可能性や建中寺隣地の取得・活用交渉を踏まえ、交通利便性やバリアフリー、行政機能集約の観点から総合的な比較検討が行われている。",
        "conflict_axes": [
            "愛知大学車道校舎への移転による交通利便性向上・早期整備と現地建て替えの比較",
            "区民アンケートや住民説明会における賛否の分かれと合意形成プロセス",
            "他区の老朽区役所・支所整備計画との優先順位と財政負担の平準化"
        ],
        "keywords": ["東区役所", "愛知大学車道校舎", "建中寺", "庁舎整備", "同一庁舎化"]
    },
    {
        "topic_id": "meieki_redevelopment_srt",
        "category": "都市再生・交通インフラ",
        "title": "名古屋駅周辺まちづくりと新たな路面公共交通（SRT）導入",
        "lead_summary": "リニア中央新幹線開業を見据えた名古屋駅東側・西側の駅前広場再編、名駅南地下公共空間の整備、都心部の回遊性を高める新たな路面公共交通システム（SRT）の導入。",
        "current_status": "名鉄再開発見直しの影響調整や東側広場デザイン計画の策定、西側の路上駐輪場対策、SRTの本格運行・MaaS連携に向けた検討が加速している。",
        "conflict_axes": [
            "民間再開発の見直しに伴う駅前広場・地下公共空間整備のスケジュール調整",
            "アジア競技大会開催に向けた歩行者空間の確保と駐輪場・一般車動線の機能分担",
            "SRTの導入採算性とルート選定、都心部の暑さ・ヒートアイランド対策との連動"
        ],
        "keywords": ["名古屋駅周辺", "駅前広場", "SRT", "名駅南", "地下公共空間", "リニア"]
    },
    {
        "topic_id": "premium_gift_certificate",
        "category": "産業・観光・地域経済",
        "title": "地域経済活性化とプレミアム付商品券事業（電子化・物価高騰対策）",
        "lead_summary": "物価高騰に直面する市民の家計支援と地域消費喚起を目的としたプレミアム付商品券事業。国の交付金活用、全申込者購入への小口化、完全電子化の是非を巡る議論。",
        "current_status": "早期利用開始と事務コスト削減のため電子商品券への移行が進められる一方、高齢者などデジタル弱者向けサポート窓口の全区配備や周知方法が審議されている。",
        "conflict_axes": [
            "迅速な発行・事務費削減を目指す電子化と高齢者・紙券希望者への配慮",
            "重点支援地方交付金の活用と市独自財源投入の費用対効果",
            "大手チェーン店への消費偏重を防ぎ地域商店街・中小店舗へ還元する仕組み作り"
        ],
        "keywords": ["プレミアム付商品券", "プレミアム商品券", "電子商品券", "地域経済活性事業"]
    },
    {
        "topic_id": "monozukuri_mice_tourism_dmo",
        "category": "産業・観光・地域経済",
        "title": "中小企業・モノづくり技術継承支援とMICE・DMO観光誘客",
        "lead_summary": "名古屋の基幹を成す製造業の技術承継・DX支援と、MICE誘致の強化、観光地域づくり法人（DMO）登録後のマーケティング体制確立に向けた審議。",
        "current_status": "工業研究所による実践的技術研修の実施や、国際会議誘致に向けた民間連携、人流データを活用した戦略的プロモーションの展開が進められている。",
        "conflict_axes": [
            "中小零細企業の人手不足・後継者不在に対するプッシュ型支援の実効性",
            "アジア競技大会を契機とした国際MICE都市としてのインフラ・受入体制整備",
            "産業観光と伝統文化資源の融合による滞在型観光・インバウンド消費の拡大"
        ],
        "keywords": ["物づくり", "ものづくり", "技術継承", "MICE", "DMO", "観光コンベンションビューロー"]
    },
    {
        "topic_id": "school_lunch_free_and_reform",
        "category": "子育て・教育",
        "title": "学校給食費無償化と中学校スクールランチ（選択制・全員喫食）の展開",
        "lead_summary": "子育て世代の経済的負担軽減を目指す小・中学校給食費の無償化施策と、市立中学校におけるスクールランチの選択制から全員喫食への移行課題を巡る議論。",
        "current_status": "小学校給食費無償化に伴う一般財源の投入が進む一方、中学校における供給能力の確保や民間委託方式の課題、国の制度動向を注視した検討が続いている。",
        "conflict_axes": [
            "給食費無償化に伴う巨額の一般財源負担と持続可能な財政運営",
            "中学校スクールランチにおける食育・温かい給食提供と給食センター整備のコスト",
            "アレルギー対応や民間調理委託における衛生・安全管理体制の維持"
        ],
        "keywords": ["学校給食", "給食費無償化", "スクールランチ", "中学校給食", "給食無償化"]
    },
    {
        "topic_id": "futoukou_freeschool_support",
        "category": "子育て・教育",
        "title": "不登校児童生徒への支援（学びの多様化学校・フリースクール助成）",
        "lead_summary": "不登校児童生徒数の増加に伴う多様な学びの機会確保、校内支援室（居場所）の整備、公設フリースクール（学びの多様化学校）設置、民間利用料助成を巡る議論。",
        "current_status": "フリースクール等への利用料助成制度の検討が進められるとともに、学校外の学びにおける出席扱い指針の周知、保護者の不登校離職対策が審議されている。",
        "conflict_axes": [
            "民間のフリースクール等への公費助成の基準と教育の質・安全性の確保",
            "市立の学びの多様化学校の設置場所選定と教員配置・専門人材の確保",
            "学校復帰を前提としない多様な社会的自立支援と学校現場の負担軽減"
        ],
        "keywords": ["不登校", "フリースクール", "学びの多様化学校", "不登校特例校", "不登校離職", "出席扱い"]
    },
    {
        "topic_id": "nagoya_shiminzei_genzei",
        "category": "財政・行革",
        "title": "市民税減税政策の堅持と財政規律・行財政改革の推進",
        "lead_summary": "長年堅持されてきた市民税減税政策の維持と、社会保障費増大・大規模事業推進に伴う将来的な財政健全性・財政規律の指標見直しを巡る議論。",
        "current_status": "市民税減税堅持の方針が示される一方、基金残高の推移や市債発行額の抑制、限られた財源の中でのマニフェスト施策優先順位づけが厳しく検証されている。",
        "conflict_axes": [
            "市民税減税10％堅持による市民還元と公共施設老朽化・更新財源の確保",
            "平成22年に策定された財政規律指標の遵守と社会経済情勢に応じた見直し",
            "徹底した行財政改革・民間委託の推進と行政サービス水準・公の責任の維持"
        ],
        "keywords": ["市民税減税", "減税", "財政規律", "財政調整基金", "行財政改革", "市債現在高"]
    },
    {
        "topic_id": "waste_carry_out_prevention_ordinance",
        "category": "くらし・環境・エネルギー",
        "title": "家庭廃棄物・資源ごみ持ち去り防止条例の制定と生活困窮者支援",
        "lead_summary": "ごみ集積所からの資源ごみ（アルミ缶・古紙等）の無断持ち去りによる騒音・散乱トラブル防止条例の制定と、持ち去り行為者に対する自立支援を巡る議論。",
        "current_status": "勧告・命令・過料・公表を含む防止条例が制定され、直営職員によるパトロール体制が整えられる一方、生活困窮者への福祉施策との連携が図られている。",
        "conflict_axes": [
            "罰則を伴う厳格な持ち去り規制と生活困窮者・高齢収集者への自立・福祉支援の両立",
            "市民による通報時の安全確保・トラブル回避と効率的なパトロール体制",
            "買取り業者側への適正取引要請や流通ルートへの対策の実効性"
        ],
        "keywords": ["持ち去り", "家庭廃棄物等の持ち去り", "資源ごみ持ち去り", "アルミ缶", "古紙", "生活困窮者"]
    },
    {
        "topic_id": "nagoya_heatstroke_climate_action",
        "category": "くらし・環境・エネルギー",
        "title": "猛暑・熱中症対策の全庁横断推進と脱炭素・環境学習プラン2030",
        "lead_summary": "近年の記録的猛暑を受けた学校・公共施設の熱中症対策、省エネ型エアコン買換え支援、なごや環境学習プラン2030に基づく脱炭素社会の実現。",
        "current_status": "全庁横断的な熱中症対策会議の設置やエアコン買換え補助の検討が進むとともに、藤前干潟の湿地都市認証を契機とした環境教育の拡充が審議されている。",
        "conflict_axes": [
            "省エネ型家電買換え補助の予算規模と低所得世帯・高齢者世帯への重点化",
            "学校体育館空調のLPガス併用など災害避難所バックアップ機能の全校整備",
            "2030年削減目標に向けた市民・事業者の行動変容と市役所自らの脱炭素化"
        ],
        "keywords": ["熱中症", "猛暑", "エアコン", "なごや環境学習プラン", "藤前干潟", "ゼロカーボン", "地球温暖化"]
    },
    {
        "topic_id": "minato_disaster_prevention_center",
        "category": "防災・減災・治安",
        "title": "港防災センター移転改築と南海トラフ地震・避難所対策の強化",
        "lead_summary": "伊勢湾台風の教訓を伝える港防災センターの野跡小学校跡地への移転改築計画と、南海トラフ巨大地震を見据えた臨海部・全市の防災拠点機能の強化。",
        "current_status": "新センターの基本計画・展示体験手法の具体化が進むとともに、津波避難ビルの指定拡充や地域独自物資の保管、避難所口腔ケアなど災害関連死防止が審議されている。",
        "conflict_axes": [
            "臨海部浸水想定区域への防災センター整備における耐震・津波安全性の確保",
            "伊勢湾台風の記憶継承と最新デジタル技術を用いた体感型防災教育の融合",
            "広域避難所となる学校施設等の環境整備と地域主体の避難所運営体制"
        ],
        "keywords": ["港防災センター", "南海トラフ", "避難所", "伊勢湾台風", "津波避難ビル"]
    },
    {
        "topic_id": "nagoya_city_univ_hospitals_dx",
        "category": "福祉・医療・健康",
        "title": "名市大附属病院群（東部・西部医療センター等）の機能強化と医療DX",
        "lead_summary": "名古屋市立大学附属病院化した東部・西部医療センター等を含む6病院体制のスケールメリット発揮、電子カルテ統一などの医療DX、高度周産期・小児医療体制の強化。",
        "current_status": "共通電子カルテ導入や医薬品共同調達による経営効率化が進む一方、医師・看護師の確保処遇改善や病室Wi-Fi整備など患者アメニティ向上が審議されている。",
        "conflict_axes": [
            "病院群統合による経営健全化と地域密着型急性期医療・救急受入機能の維持",
            "電子カルテ統一・AI要約等DX投資の費用対効果とセキュリティ確保",
            "周産期医療・小児医療における公的医療機関としての不採算特殊医療の役割"
        ],
        "keywords": ["東部医療センター", "西部医療センター", "市立大学病院", "附属病院", "医療DX", "電子カルテ"]
    }
]

OSAKA_TOPIC_CONFIGS = [
    {
        "topic_id": "fukushuto_daitoshi_seido",
        "category": "財政・行革",
        "title": "副首都ビジョンと大都市制度（法定協議会・特別区）",
        "lead_summary": "副首都・大阪の都市格確立に向け、大都市制度の議論が再燃。法定協議会の設置議案や住民投票の時期、府市連携のあり方を巡り活発な質疑が展開。",
        "current_status": "法定協議会設置の判断や市民への説明プロセス、大都市制度の名称や効果について議会側から厳しい検証と質疑が継続中。",
        "conflict_axes": [
            "特別区設置構想および副首都法案における特別区の位置づけ・削除の必要性を巡る議論",
            "不交付団体化に伴う財政上の不利と、自立に向けた国への制度改正要請のあり方",
            "副首都推進局における公文書管理の不備や情報公開に関する説明責任と再発防止策"
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
        "keywords": ["特区民泊", "民泊", "違法民泊", "国家戦略特区民泊", "民泊施設", "違法民泊対策"]
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
        "title": "国民健康保険料・介護保険料の負担軽減と適正化",
        "lead_summary": "府内統一基準に伴う国民健康保険料の改定と、高齢化に伴う介護保険料引き上げに対し、低所得世帯や現役世代への減免措置・負担軽減が議論。",
        "current_status": "基金の取り崩しによる急激な保険料上昇の緩和策や、介護現場の処遇改善・人材確保に向けた公的支援のあり方が追及されている。",
        "conflict_axes": [
            "保険財政の持続可能性と低所得世帯・年金生活者への過重な負担感",
            "府内統一算定方式における大阪市独自の減免措置のあり方",
            "介護報酬改定に伴う事業所倒産防止と公費補填の限界"
        ],
        "keywords": ["国民健康保険", "国保料", "介護保険料", "保険料改定", "負担軽減", "減免"]
    },
    {
        "topic_id": "bousai_infrastructure_yodogawa",
        "category": "防災・減災・治安",
        "title": "淀川左岸線延伸と高潮・巨大地震津波対策",
        "lead_summary": "南海トラフ巨大地震や高潮・内水氾濫に対する防潮堤・水門の耐震化と、淀川左岸線延伸部の工期見直し・安全確保に関する議論。",
        "current_status": "津波避難ビルの指定拡大や水防体制の点検が進む一方、淀川左岸線2期事業の工事安全対策と早期供用開始が求められている。",
        "conflict_axes": [
            "難工事に伴う工期延伸・事業費増額と大規模災害への備えの緊急性",
            "ゼロメートル地帯における避難体制と外国人・来訪者への避難誘導",
            "老朽下水管・河川インフラの耐震補強と財政負担の平準化"
        ],
        "keywords": ["淀川左岸線", "防潮堤", "高潮対策", "水門整備", "浸水想定区域", "ゼロメートル地帯"]
    },
    {
        "topic_id": "cultural_heritage_osakajo_naniwagu",
        "category": "文化・景観・歴史",
        "title": "大阪城公園・難波宮跡の歴史遺産保全と賑わい創出",
        "lead_summary": "特別史跡大坂城跡・難波宮跡の保存活用計画と、民間PMOによるパークPFI導入、歴史的景観保全と観光振興の調和を巡る議論。",
        "current_status": "難波宮跡の整備基本構想に基づく発掘調査と公園整備が進められる一方、イベント利用における遺構保全への配慮が審議されている。",
        "conflict_axes": [
            "国指定特別史跡としての学術的価値・遺構保全と民間活力導入による集客",
            "市民の憩いの場・歴史学習拠点としての機能と商業的利用のバランス",
            "周辺エリア（天満橋・上町台地）との歴史回遊ルートの形成と案内機能の充実"
        ],
        "keywords": ["大阪城", "難波宮", "特別史跡", "パークPFI", "遺構", "歴史景観"]
    }
]

CITY_CONFIGS = {
    "nagoya": NAGOYA_TOPIC_CONFIGS,
    "osaka": OSAKA_TOPIC_CONFIGS
}

def generate_topics(city_code):
    print("=" * 60)
    print(f"🚀 [{city_code.upper()}] 統合トピック要約（政策論戦マップ）生成")
    print("=" * 60)

    if city_code not in CITY_CONFIGS:
        raise ValueError(f"未対応の都市コードです: {city_code}")

    topic_configs = CITY_CONFIGS[city_code]
    stmts_path = PROJECT_ROOT / "frontend" / "public" / "data" / f"{city_code}_statements_summary.json"
    if not stmts_path.exists():
        if city_code == "kyoto":
            stmts_path = PROJECT_ROOT / "frontend" / "public" / "data" / "statements_summary.json"
        if not stmts_path.exists():
            raise FileNotFoundError(f"発言データが見つかりません: {stmts_path}")

    # utf-8-sig でBOMを完全除去して読み込み
    statements = json.loads(stmts_path.read_text(encoding="utf-8-sig"))
    print(f"📥 読み込み完了: {len(statements):,} 件のスレッド")

    results = []
    for cfg in topic_configs:
        cat = cfg["category"]
        kws = cfg["keywords"]
        matched = []

        for s in statements:
            s_cat = s.get("category", "")
            text = (
                s.get("summary", "") + " " +
                s.get("statement_text", "") + " " +
                " ".join(s.get("keywords", []))
            ).lower()
            if cat in s_cat:
                if any(kw.lower() in text for kw in kws):
                    matched.append(s)

        matched.sort(key=lambda x: x.get("meeting_date", ""))
        thread_count = len(matched)
        last_updated = matched[-1].get("meeting_date", "2026-06-26") if matched else "2026-06-26"
        print(f"  [{cat}] {cfg['title']} -> {thread_count} 件マッチ")

        phase_groups = {
            "2023年（令和5年）以前": [s for s in matched if s.get("meeting_date", "") <= "2023-12-31"],
            "2024年（令和6年）": [s for s in matched if s.get("meeting_date", "").startswith("2024")],
            "2025年〜2026年（令和7・8年）": [s for s in matched if s.get("meeting_date", "") >= "2025-01-01"]
        }

        timeline_phases = []
        for period_name, p_stmts in phase_groups.items():
            if not p_stmts:
                continue

            exchanges = []
            for s in p_stmts[:3]:
                # 💡 京都・大阪・名古屋 全都市統一: 議員の実際の発言本文 (statement_text) を最優先
                raw_speech = (s.get("statement_text") or "").strip()
                if raw_speech and len(raw_speech) > 20:
                    # 議事進行の余計な定型句を除去して実際の発言を抽出
                    cleaned_speech = re.sub(r"^(ただいまから|それでは|よろしくお願いいたします|おはようございます|ありがとうございます)[。、\s]*", "", raw_speech)
                    display_text = cleaned_speech[:220] + ("..." if len(cleaned_speech) > 220 else "")
                else:
                    display_text = s.get("summary", "")[:200]

                exchanges.append({
                    "statement_id": s.get("id"),
                    "meeting_id": s.get("meeting_id"),
                    "sequence_number": s.get("sequence_number") or s.get("speech_order"),
                    "meeting_date": s.get("meeting_date", ""),
                    "meeting_title": s.get("meeting_title", ""),
                    "speaker": s.get("speaker", ""),
                    "statement_summary": display_text,
                    "source_url": s.get("official_url") or s.get("source_url", "https://ssp.kaigiroku.net/tenant/nagoya/SpMinuteSearch.html")
                })

            if "2023" in period_name:
                phase_title = "制度の検証・課題の浮き彫りと初期提案"
                city_stance = "議会からの指摘を踏まえ、現状の運用課題の整理や他都市事例の調査研究、実態把握に着手する姿勢を示した。"
            elif "2024" in period_name:
                phase_title = "具体策の審議・実施計画への反映"
                city_stance = "関係局との連携体制を整え、モデル事業の検証や基本計画の策定、制度見直しに向けた具体的検討を進めた。"
            else:
                phase_title = "本格実施・制度拡充と持続可能性の検証"
                city_stance = "予算措置や条例整備を進めつつ、市民意見の反映や財政状況・物価高騰を踏まえた持続可能な運用の確保に努めている。"

            timeline_phases.append({
                "period": period_name,
                "phase_title": phase_title,
                "city_stance": city_stance,
                "key_points": [
                    f"議員による「{cfg['title']}」に関する論点指摘と行政答弁の確認",
                    "市民益の向上と事業の実効性・財政負担を両立させる制度設計の審議"
                ],
                "exchanges": exchanges
            })

        item = {
            "topic_id": cfg["topic_id"],
            "category": cfg["category"],
            "title": cfg["title"],
            "lead_summary": cfg["lead_summary"],
            "current_status": cfg["current_status"],
            "conflict_axes": cfg["conflict_axes"],
            "thread_count": thread_count,
            "last_updated": last_updated,
            "timeline_phases": timeline_phases
        }
        results.append(item)

    out_file = PROJECT_ROOT / "frontend" / "public" / "data" / f"{city_code}_topic_summaries.json"
    if city_code == "kyoto":
        out_file = PROJECT_ROOT / "frontend" / "public" / "data" / "topic_summaries.json"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 [{city_code.upper()}] 完了！ {len(results)} 件のトピック要約を {out_file.name} に保存しました。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="議会のミカタ 統合トピック要約ジェネレーター")
    parser.add_argument("--city", required=True, choices=["nagoya", "osaka", "kyoto"], help="対象都市コード")
    args = parser.parse_args()
    generate_topics(args.city)