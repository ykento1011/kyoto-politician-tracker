import React, { useState, useMemo, useEffect } from 'react';
import {
    ArrowLeft, PieChart, Sparkles, Milestone,
    MessageSquare, ArrowRight, SlidersHorizontal, ArrowUpDown,
    Search, ChevronDown, User, Calendar, Landmark
} from 'lucide-react';
import ThreadCard from './ThreadCard';
import { cleanName } from '../utils/styleHelpers';


// 会議体名抽出ヘルパー
function getMeetingBodyName(stmt) {
    if (!stmt) return '本会議・委員会';
    if (stmt.meeting_title) {
        return stmt.meeting_title.split(' ')[0] || stmt.meeting_title;
    }
    return stmt.committee || stmt.meeting_name || '本会議';
}

// 8大カテゴリーの都市別包括政策総括マスター
const CITY_CATEGORY_OVERVIEWS = {
    kyoto: {
        '財政・行革': {
            lead: '財政破綻（特別の財政支援団体転落）の危機からの脱却と、行財政改革計画の着地が最大の焦点。敬老乗車証や保育料の見直しなど「身を切る改革・市民負担増」の是非と、市債残高圧縮・公債償還基金の回復状況を巡り、全会派で激しい攻防が交わされました。',
            key_points: [
                '「特別の財政支援」依存からの完全脱却と、単年度収支の黒字化達成度の評価',
                '市民サービス削減・負担増（敬老パス、保育料、施設利用料）の市民生活への影響',
                '市有資産の売却・民間包括委託（アウトソーシング）による行革効果と公共性の維持'
            ]
        },
        '都市再生・交通インフラ': {
            lead: '観光客急増に伴う市バスの慢性的大混雑への市民生活対策と、人口流出抑制に向けた都市構造の転換が二大テーマ。市民優先価格（二重運賃）導入への挑戦や、高さ・容積率規制の緩和による若者定住・産業用地確保、空き家税の施行準備が議論の中心となりました。',
            key_points: [
                '市バス混雑に対する「観光特急バス」の効果検証と「市民優先価格」導入の線引き',
                '京都駅南側やらくなん進都における高さ規制緩和と、歴史的景観保全のバランス',
                '空き家税（非居住住宅利活用促進税）の施行準備と、若年・子育て世帯向け定住支援策'
            ]
        },
        '産業・観光・地域経済': {
            lead: '急回復したインバウンド観光の恩恵をいかに市民生活に還元し、生活環境悪化を防ぐかという「オーバーツーリズムとの調和」が焦点。宿泊税の税率引き上げ・使途拡大の議論と、後継者不足が深刻化する伝統産業・中小企業への実効的な承継支援が争われました。',
            key_points: [
                '宿泊税の引き上げ（最高額改定）と、その税収使途の市民還元（道路・交通整備等）',
                '祇園・清水など特定地域における散乱ごみ（スマートごみ箱）、マナー問題対策',
                '西陣織・京友禅をはじめとする伝統産業の担い手育成と、新商品開発・販路開拓'
            ]
        },
        '子育て・教育': {
            lead: '長年の懸案であった全員制中学校給食の実現方式（大規模給食センター方式）を巡る議論が白熱。500億円規模に上る巨額投資や避難所機能の喪失への懸念と、給食費無償化の財源論争、さらに教員の多忙化・不登校対策が連動して追及されました。',
            key_points: [
                '塔南高校跡地の大規模給食センター建設計画と、学校調理方式を求める市民の声',
                '小中学校給食費の完全無償化に向けた財源確保と、国への制度化要望',
                '教員の長時間労働是正、学校ICT端末（GIGAスクール）の活用と不登校児童への支援'
            ]
        },
        '福祉・医療・健康': {
            lead: '高齢化と社会保障費増大が進む中、持続可能なセーフティネットのあり方が議論されました。敬老乗車証の自己負担率改定の影響検証、国民健康保険料・介護保険料の負担軽減策、帯状疱疹ワクチンの公費助成化などが主要な論点となりました。',
            key_points: [
                '敬老乗車証の制度見直しに伴う高齢者の外出機会・健康寿命への影響',
                '国保料の均等割引き下げなど低所得・子育て世帯の保険料負担軽減',
                '帯状疱疹ワクチンや子宮頸がんワクチンなど任意予防接種に対する助成拡充'
            ]
        },
        'くらし・環境・エネルギー': {
            lead: '2050年カーボンニュートラル実現に向けた脱炭素条例の推進と、市民生活インフラの維持が論点。新築建築物への太陽光パネル設置義務化やプラスチック資源一括回収の開始、老朽化した水道管路の耐震更新と料金体系のあり方が議論されました。',
            key_points: [
                '建築物への太陽光発電設備設置義務化と、歴史都市・景観基準との整合性',
                'プラスチック資源の一括分別回収開始に伴う収集体制・市民周知の徹底',
                '耐震基準を満たさない老朽水道管の破裂防止と、将来的な料金改定議論'
            ]
        },
        '防災・減災・治安': {
            lead: '能登半島地震の発生を受け、木造密集市街地や細街路（路地奥）を多く抱える京都特有の都市防災が再クローズアップ。京町家の耐震・防火改修支援や、桂川・鴨川水系の内水氾濫対策、避難所機能の強化が精力的に議論されました。',
            key_points: [
                '密集市街地・路地奥住宅の接道問題と、延焼遮断・耐震化への公的助成',
                'ゲリラ豪雨・線状降水帯による内水氾濫防止に向けた雨水幹線・貯留施設の整備',
                '避難所における段ボールベッド・プライバシー確保と女性・要支援者への配慮'
            ]
        },
        '文化・景観・歴史': {
            lead: '文化庁の京都全面移転を果たしたことを受け、その政策効果をいかに全国・地域に波及させるかが焦点。文化芸術活動への公的支援、歴史的街並みを支える無電柱化（電柱地中化）の推進とコスト縮減、屋外広告物規制の継承が討議されました。',
            key_points: [
                '文化庁移転に伴う文化政策のイノベーションと、市民・芸術家への恩恵波及',
                '観光地・歴史地区における無電柱化の推進ペースと事業費の抑制策',
                '伝統的な町並みを守る新景観政策の維持と、地域産業の活力維持の両立'
            ]
        }
    },
    osaka: {
        '財政・行革': {
            lead: '大阪都構想否決後の府市一体（広域一元化）による行財政運営の成果検証と、身を切る改革の継続が主眼。万博関連予算や大型インフラ投資に対するチェック機能、公の施設の指定管理者制度や民営化の是非が議論されました。',
            key_points: [
                '府市連携・一元化による二重行政解消の具体的効果と財政検証',
                '大阪・関西万博の関連整備費および将来負担の検証と財源マネジメント',
                '市役所業務のDX推進と外郭団体・公有財産の効率的運用'
            ]
        },
        '都市再生・交通インフラ': {
            lead: 'うめきた2期（グラングリーン大阪）や夢洲まちづくり、なにわ筋線の整備などメガプロジェクトが目白押し。ベイエリアのIR（統合型リゾート）整備に向けた液状化・土壌汚染対策、自動運転バスや空飛ぶクルマの実証が論点となりました。',
            key_points: [
                'うめきた・中之島・夢洲を結ぶ新たな交通軸（なにわ筋線・中央線延伸）の整備',
                '夢洲IR誘致に伴う公費負担リスク（土壌対策費・インフラ整備費）の監査',
                '市内全域の歩行者空間化（御堂筋側道歩道化）と公共交通網の再編'
            ]
        },
        '産業・観光・地域経済': {
            lead: '大阪・関西万博を契機とした地域経済の活性化と、国内外からの投資・観光客誘致が二大柱。商店街・町工場の活性化やスタートアップ支援、宿泊税の見直しやナイトタイムエコノミーの創出が活発に論じられました。',
            key_points: [
                '万博開催効果の市内全24区・地元中小企業・商店街への波及策',
                'ものづくり・スタートアップ・ライフサイエンス分野への集中投資',
                'インバウンド増加に伴うマナー向上と宿泊税の税率・免税点見直し'
            ]
        },
        '子育て・教育': {
            lead: '大阪市が先行する「教育・子育ての完全無償化」政策の拡充と持続可能性が最大焦点。0〜2歳児保育無償化、塾代助成の所得制限撤廃、高校・大阪公立大学等の完全無償化に伴う財政負担と教育格差是正が追及されました。',
            key_points: [
                '塾代助成事業（月額1万円）の全学年・所得制限撤廃に伴う利用状況と学習効果',
                '0〜2歳児保育料の第2子・第1子無償化に向けた財源確保と保育士確保策',
                '学校給食の全員喫食・無償化継続と、学校施設・体育館エアコンの維持管理'
            ]
        },
        '福祉・医療・健康': {
            lead: '急速な少子高齢化を背景に、敬老優待乗車証（敬老パス）の負担あり方や、地方独立行政法人大阪市民病院機構の経営強化が議論。地域包括ケアシステムの構築、認知症施策、医療的ケア児支援が争点となりました。',
            key_points: [
                '敬老優待乗車証（年額負担＋利用時負担）の持続可能な制度設計',
                '急性期病院の再編・公立病院機構の経営健全化と地域医療の確保',
                '孤独・孤立対策、ヤングケアラー・医療的ケア児世帯への伴走型支援'
            ]
        },
        'くらし・環境・エネルギー': {
            lead: '2050年ゼロカーボンシティの実現に向け、水素エネルギー活用や新技術実証が推進。ごみ処理施設の再編、プラスチックごみ一括回収、老朽下水道管路の耐震更新やウォーターPPPの導入方針が問われました。',
            key_points: [
                'ベイエリアにおける脱炭素港湾（カーボンニュートラルポート）と水素エネルギー実証',
                'ごみ減量・プラスチック分別一括収集の全市展開と市民周知',
                '上下水道管の老朽化対策とウォーターPPP（官民連携手法）導入の是非'
            ]
        },
        '防災・減災・治安': {
            lead: '南海トラフ巨大地震に伴う大津波警報を想定した三大水門耐震補強や、海抜ゼロメートル地帯の浸水対策が緊急課題。木造住宅密集地域の不燃化、防犯カメラ整備や客引き適正化が討議されました。',
            key_points: [
                '三大水門（木津川・安治川・尻無川）の更新・津波防潮堤の耐震化進捗',
                '危険密集住宅市街地における延焼遮断帯の形成と建替え助成',
                '避難所（学校体育館）への空調機配備前倒しと指定津波避難ビルの確保'
            ]
        },
        '文化・景観・歴史': {
            lead: '水都大阪の都市魅力創出と、中之島ミュージアムリンクをはじめとする国際的文化拠点づくりがテーマ。大阪城公園のパークPFIの評価、重要文化財の保存活用、国際都市にふさわしい都市景観誘導が議論されました。',
            key_points: [
                '水辺空間（中之島・道頓堀・大川）の回遊性向上と水上交通の活性化',
                '御堂筋沿道の景観誘導・ウォーカブル推進と歩道空間の民間活用',
                '大阪の歴史的建造物・近代建築の保存と観光資源化'
            ]
        }
    },
    nagoya: {
        '財政・行革': {
            lead: '全国唯一の恒久的「市民税5%減税」政策の継続・検証と、市長・市議会の政策決定プロセスが最大の争点。東区役所等の老朽庁舎移転整備方針、議員報酬・政務活動費の透明化、持続可能な行財政運営が議論の中心となりました。',
            key_points: [
                '市民税減税による市民生活・市内経済への効果検証と税収財源の確保',
                '東区役所等庁舎の老朽化と移転整備候補地（愛知大学車道校舎等）の選定論争',
                '行政手続きのオンライン化・生成AI活用と外郭団体を含む行財政改革'
            ]
        },
        '都市再生・交通インフラ': {
            lead: 'リニア中央新幹線開業を見据えた名古屋駅周辺の大規模再開発と、都心部の新たな路面公共交通「SRT（Smart Rapid Transit）」の導入が焦点。名東区・天白区を結ぶ弥富相生山線道路事業と自然保護の両立も重要論点です。',
            key_points: [
                '名古屋駅周辺のスーパーターミナル化と駅前広場・地下街の再整備',
                '都心部を結ぶ新たな路面公共交通（SRT）の実証運行とルート設計',
                '弥富相生山線道路整備事業におけるヒメボタル生息地保全と折衷案の推進'
            ]
        },
        '産業・観光・地域経済': {
            lead: '中部圏の産業首都としての中小企業・ものづくり技術の承継支援と、プレミアム付商品券による物価高騰・消費刺激策が柱。国際展示場（ポートメッセなごや）や愛知県と連携したMICE・観光誘客戦略が議論されました。',
            key_points: [
                'プレミアム付商品券事業（電子マネー「金シャチマネー」）の効果と検証',
                '次世代モビリティ・航空宇宙・スタートアップへの総合支援',
                'アジア・アジアパラ競技大会（2026年）の開催準備とインバウンド誘致'
            ]
        },
        '子育て・教育': {
            lead: '小中学校の給食費無償化の段階的実施と、中学校スクールランチ（選択制から全員喫食への移行）のあり方が激論。不登校児童生徒の増加に対応する「学びの多様化学校」の増設やフリースクール助成が重要視されました。',
            key_points: [
                '学校給食費の無償化推進と中学校における全員制給食への抜本的見直し',
                '不登校対策としての特命校（学びの多様化学校）設置と民間施設連携',
                '教員の多忙化解消、部活動の地域移行、小中学校体育館への空調整備'
            ]
        },
        '福祉・医療・健康': {
            lead: '日本一の手厚い高齢者移動支援である「敬老パス」の持続可能性と利用範囲（名鉄・近鉄・JR・タクシー）の拡大・上限見直しが焦点。名古屋市立大学附属病院群の再編・医療DXや認知症支援策が審議されました。',
            key_points: [
                '敬老パス制度の利用実績・財政負担と私鉄・タクシー利用拡充に伴う制度維持',
                '名古屋市立大学病院群（東部・西部医療センター等）の高度医療機能強化',
                '在宅医療・介護連携の推進と単身高齢者・孤独死ゼロに向けた見守り体制'
            ]
        },
        'くらし・環境・エネルギー': {
            lead: 'ごみ減量先進都市としての家庭廃棄物・資源ごみ持ち去り防止条例の制定と、近年の猛暑に伴う全庁横断の熱中症対策が論点。脱炭素・環境学習プラン2030に基づく太陽光・再エネ導入と生活基盤の維持が討議されました。',
            key_points: [
                '資源ごみ持ち去り防止条例の厳格化と生活困窮者・収集従事者への配慮',
                '記録的猛暑に対応するクーリングシェルター（指定暑熱避難施設）の確保',
                '水道料金の体系見直しと老朽上下水道管路の更新・耐震化ペース'
            ]
        },
        '防災・減災・治安': {
            lead: '南海トラフ巨大地震・風水害（伊勢湾台風クラス）に備えた浸水対策と港防災センターの移転改築が最優先課題。能登半島地震を踏まえた避難所環境改善（空調・マンホールトイレ・簡易ベッド）が集中審議されました。',
            key_points: [
                '港防災センターの老朽化に伴う移転新築計画と体験型防災教育機能の強化',
                '南海トラフ地震に備えた津波・液状化対策および宅地内給排水管の復旧体制',
                '指定避難所となる学校施設への通信インフラ（衛星等）・空調・備蓄拡充'
            ]
        },
        '文化・景観・歴史': {
            lead: '長年の市政最大テーマである「名古屋城天守閣木造復元事業」における特別史跡現状変更許可と、昇降技術（エレベーター・新技術）によるバリアフリーの両立を巡り、市議会全体で激しい論戦が続いています。',
            key_points: [
                '名古屋城天守閣の木造復元に向けた文化庁許可の取得状況と工事工程',
                '障がい者団体等との対話に基づく昇降技術・バリアフリー設備のあり方',
                '名古屋城周辺の魅力向上（金シャチ横丁等）と歴史的文化財の保存継承'
            ]
        }
    }
};

// 8大カテゴリーの都市別主要論点マスター（正規ID準拠）
const CITY_CATEGORY_TOPICS = {
  "kyoto": {
    "観光・交通 / 市民生活": [
      {
        "id": "kyoto-mayor-P-01",
        "title": "市バス等の「市民優先価格（2階建て運賃）」導入への挑戦"
      }
    ],
    "財政・税制": [
      {
        "id": "kyoto-mayor-P-02",
        "title": "宿泊税上限引き上げおよび使途の拡大"
      }
    ],
    "子育て・教育": [
      {
        "id": "kyoto-mayor-P-03",
        "title": "全員制中学校給食の早期完全実施（京都方式）"
      },
      {
        "id": "kyoto-core-childcare-support-burden",
        "title": "子育て世帯の経済的負担軽減（医療費・給食費無償化）と待機児童対策"
      },
      {
        "id": "kyoto-core-school-education-environment",
        "title": "公立小中学校の教員不足対策・ICT教育推進と不登校支援"
      }
    ],
    "子育て・福祉": [
      {
        "id": "kyoto-mayor-P-04",
        "title": "府市協調子ども医療費助成拡充と第2子以降保育料無償化"
      }
    ],
    "景観・居住": [
      {
        "id": "kyoto-mayor-P-05",
        "title": "京町家保全継承・若年子育て世帯居住支援"
      }
    ],
    "都市計画": [
      {
        "id": "kyoto-mayor-P-06",
        "title": "京都駅周辺・三条京阪都市再生・ビジネス集積"
      }
    ],
    "産業振興": [
      {
        "id": "kyoto-mayor-P-07",
        "title": "スタートアップ創出・京都シリコンバレー化構想"
      }
    ],
    "行政改革": [
      {
        "id": "kyoto-mayor-P-08",
        "title": "しごとの仕方改革・行政DX・BPR推進"
      }
    ],
    "財政規律": [
      {
        "id": "kyoto-mayor-P-09",
        "title": "持続可能な行財政運営・過去負債返済の堅持"
      }
    ],
    "文化政策": [
      {
        "id": "kyoto-mayor-P-10",
        "title": "「双京構想」推進・文化財修理拠点誘致"
      }
    ],
    "環境・美化": [
      {
        "id": "kyoto-mayor-P-11",
        "title": "観光地美化・スマートごみ箱・交通抑制"
      }
    ],
    "郊外再生": [
      {
        "id": "kyoto-mayor-P-12",
        "title": "洛西・向島ニュータウン等郊外再生"
      }
    ],
    "文化・都市": [
      {
        "id": "kyoto-mayor-P-13",
        "title": "北山エリア文化交流拠点化・音楽祭"
      }
    ],
    "保健福祉": [
      {
        "id": "kyoto-mayor-P-14",
        "title": "精神障害者医療費支給・AYA世代支援"
      }
    ],
    "財政・行革": [
      {
        "id": "kyoto-core-fiscal-discipline-reform",
        "title": "持続可能な財政規律の堅持と公共施設マネジメント・行革推進"
      },
      {
        "id": "kyoto-core-digital-gov-dx",
        "title": "行政DXの推進と窓口ワンストップ化・市民利便性向上"
      }
    ],
    "くらし・環境・エネルギー": [
      {
        "id": "kyoto-core-zero-carbon-renewable",
        "title": "脱炭素社会（ゼロカーボン）推進と再エネ導入・省エネ支援"
      },
      {
        "id": "kyoto-core-waste-reduction-recycling",
        "title": "一般廃棄物減量・プラスチック資源循環とごみ収集体制"
      }
    ],
    "都市再生・交通インフラ": [
      {
        "id": "kyoto-core-public-transport-reorganization",
        "title": "地域公共交通（地下鉄・市バス・コミュニティバス）の維持と利便性向上"
      },
      {
        "id": "kyoto-core-urban-development-infrastructure",
        "title": "主要駅周辺まちづくり・都市再生と老朽道路・橋梁の長寿命化"
      }
    ],
    "産業・観光・地域経済": [
      {
        "id": "kyoto-core-sme-business-support",
        "title": "中小企業・商店街の物価高騰対策と事業承継・賃上げ支援"
      },
      {
        "id": "kyoto-core-tourism-local-economy",
        "title": "観光振興とオーバーツーリズム（混雑・マナー問題）対策の両立"
      }
    ],
    "福祉・医療・健康": [
      {
        "id": "kyoto-core-elderly-care-welfare",
        "title": "高齢者介護基盤の確保（介護人材・施設）と健康寿命延伸・孤立防止"
      },
      {
        "id": "kyoto-core-community-medical-system",
        "title": "地域医療体制（小児・周産期・救急医療）の確保と予防医療・ワクチン助成"
      }
    ],
    "防災・減災・治安": [
      {
        "id": "kyoto-core-disaster-prevention-resilience",
        "title": "大規模地震・風水害対策（耐震化・無電柱化・治水対策）と避難所環境改善"
      },
      {
        "id": "kyoto-core-community-safety-crime-prevention",
        "title": "地域防犯体制（防犯カメラ設置・通学路安全確保）と特殊詐欺対策"
      }
    ],
    "文化・景観・歴史": [
      {
        "id": "kyoto-core-historical-landscape-conservation",
        "title": "歴史的景観・伝統的建造物の保全と調和ある都市利用"
      },
      {
        "id": "kyoto-core-arts-culture-sports-promotion",
        "title": "文化芸術・スポーツ振興と文化施設の老朽化対策・利活用"
      }
    ]
  },
  "osaka": {
    "子育て・教育": [
      {
        "id": "osaka-mayor-osaka-m01",
        "title": "0〜2歳児保育料の第2子完全無償化（所得制限撤廃）"
      },
      {
        "id": "osaka-mayor-osaka-m02",
        "title": "塾代助成事業の全学年・所得制限完全撤廃への拡充"
      },
      {
        "id": "osaka-mayor-osaka-m03",
        "title": "高等学校・大阪公立大学等の授業料完全無償化（府市協調推進）"
      },
      {
        "id": "osaka-mayor-osaka-m04",
        "title": "市立小中学校全員給食費の完全無償化の継続定着"
      },
      {
        "id": "osaka-core-childcare-support-burden",
        "title": "子育て世帯の経済的負担軽減（医療費・給食費無償化）と待機児童対策"
      },
      {
        "id": "osaka-core-school-education-environment",
        "title": "公立小中学校の教員不足対策・ICT教育推進と不登校支援"
      }
    ],
    "都市再生・交通インフラ": [
      {
        "id": "osaka-mayor-osaka-m05",
        "title": "淀川左岸線延伸部およびベイエリア幹線道路ネットワークの整備"
      },
      {
        "id": "osaka-core-public-transport-reorganization",
        "title": "地域公共交通（地下鉄・市バス・コミュニティバス）の維持と利便性向上"
      },
      {
        "id": "osaka-core-urban-development-infrastructure",
        "title": "主要駅周辺まちづくり・都市再生と老朽道路・橋梁の長寿命化"
      }
    ],
    "財政・行革": [
      {
        "id": "osaka-mayor-osaka-m06",
        "title": "区役所機能の強化と「書かない窓口」デジタル市役所の推進"
      },
      {
        "id": "osaka-core-fiscal-discipline-reform",
        "title": "持続可能な財政規律の堅持と公共施設マネジメント・行革推進"
      },
      {
        "id": "osaka-core-digital-gov-dx",
        "title": "行政DXの推進と窓口ワンストップ化・市民利便性向上"
      }
    ],
    "福祉・医療・健康": [
      {
        "id": "osaka-mayor-osaka-m07",
        "title": "児童虐待防止体制の強化・専任児童心理司およびケースワーカーの大幅増員"
      },
      {
        "id": "osaka-core-elderly-care-welfare",
        "title": "高齢者介護基盤の確保（介護人材・施設）と健康寿命延伸・孤立防止"
      },
      {
        "id": "osaka-core-community-medical-system",
        "title": "地域医療体制（小児・周産期・救急医療）の確保と予防医療・ワクチン助成"
      }
    ],
    "防災・減災・治安": [
      {
        "id": "osaka-mayor-osaka-m08",
        "title": "防犯カメラの市内集中増設および通学路防犯体制の強化"
      },
      {
        "id": "osaka-core-disaster-prevention-resilience",
        "title": "大規模地震・風水害対策（耐震化・無電柱化・治水対策）と避難所環境改善"
      },
      {
        "id": "osaka-core-community-safety-crime-prevention",
        "title": "地域防犯体制（防犯カメラ設置・通学路安全確保）と特殊詐欺対策"
      }
    ],
    "くらし・環境・エネルギー": [
      {
        "id": "osaka-core-zero-carbon-renewable",
        "title": "脱炭素社会（ゼロカーボン）推進と再エネ導入・省エネ支援"
      },
      {
        "id": "osaka-core-waste-reduction-recycling",
        "title": "一般廃棄物減量・プラスチック資源循環とごみ収集体制"
      }
    ],
    "産業・観光・地域経済": [
      {
        "id": "osaka-core-sme-business-support",
        "title": "中小企業・商店街の物価高騰対策と事業承継・賃上げ支援"
      },
      {
        "id": "osaka-core-tourism-local-economy",
        "title": "観光振興とオーバーツーリズム（混雑・マナー問題）対策の両立"
      }
    ],
    "文化・景観・歴史": [
      {
        "id": "osaka-core-historical-landscape-conservation",
        "title": "歴史的景観・伝統的建造物の保全と調和ある都市利用"
      },
      {
        "id": "osaka-core-arts-culture-sports-promotion",
        "title": "文化芸術・スポーツ振興と文化施設の老朽化対策・利活用"
      }
    ]
  },
  "nagoya": {
    "都市魅力・歴史文化財保全": [
      {
        "id": "nagoya-mayor-nagoya_p1",
        "title": "名古屋城天守閣の木造本物復元推進"
      }
    ],
    "税制・行財政改革": [
      {
        "id": "nagoya-mayor-nagoya_p2",
        "title": "市民税減税の推進と税率拡大検証（5%から10%へ）"
      }
    ],
    "高齢者福祉・移動支援": [
      {
        "id": "nagoya-mayor-nagoya_p3",
        "title": "敬老パス改善（回数制限緩和・翌年繰越・タクシー併給）"
      }
    ],
    "行政改革・特別職報酬適正化": [
      {
        "id": "nagoya-mayor-nagoya_p4",
        "title": "市長給料年額800万円の継続および退職手当の全額不支給"
      }
    ],
    "子育て支援・学校教育相談体制": [
      {
        "id": "nagoya-mayor-nagoya_p5",
        "title": "第2子以降・0歳児からの保育料無償化と子ども応援委員会の拡充"
      }
    ],
    "財政・行革": [
      {
        "id": "nagoya-core-fiscal-discipline-reform",
        "title": "持続可能な財政規律の堅持と公共施設マネジメント・行革推進"
      },
      {
        "id": "nagoya-core-digital-gov-dx",
        "title": "行政DXの推進と窓口ワンストップ化・市民利便性向上"
      }
    ],
    "くらし・環境・エネルギー": [
      {
        "id": "nagoya-core-zero-carbon-renewable",
        "title": "脱炭素社会（ゼロカーボン）推進と再エネ導入・省エネ支援"
      },
      {
        "id": "nagoya-core-waste-reduction-recycling",
        "title": "一般廃棄物減量・プラスチック資源循環とごみ収集体制"
      }
    ],
    "都市再生・交通インフラ": [
      {
        "id": "nagoya-core-public-transport-reorganization",
        "title": "地域公共交通（地下鉄・市バス・コミュニティバス）の維持と利便性向上"
      },
      {
        "id": "nagoya-core-urban-development-infrastructure",
        "title": "主要駅周辺まちづくり・都市再生と老朽道路・橋梁の長寿命化"
      }
    ],
    "子育て・教育": [
      {
        "id": "nagoya-core-childcare-support-burden",
        "title": "子育て世帯の経済的負担軽減（医療費・給食費無償化）と待機児童対策"
      },
      {
        "id": "nagoya-core-school-education-environment",
        "title": "公立小中学校の教員不足対策・ICT教育推進と不登校支援"
      }
    ],
    "産業・観光・地域経済": [
      {
        "id": "nagoya-core-sme-business-support",
        "title": "中小企業・商店街の物価高騰対策と事業承継・賃上げ支援"
      },
      {
        "id": "nagoya-core-tourism-local-economy",
        "title": "観光振興とオーバーツーリズム（混雑・マナー問題）対策の両立"
      }
    ],
    "福祉・医療・健康": [
      {
        "id": "nagoya-core-elderly-care-welfare",
        "title": "高齢者介護基盤の確保（介護人材・施設）と健康寿命延伸・孤立防止"
      },
      {
        "id": "nagoya-core-community-medical-system",
        "title": "地域医療体制（小児・周産期・救急医療）の確保と予防医療・ワクチン助成"
      }
    ],
    "防災・減災・治安": [
      {
        "id": "nagoya-core-disaster-prevention-resilience",
        "title": "大規模地震・風水害対策（耐震化・無電柱化・治水対策）と避難所環境改善"
      },
      {
        "id": "nagoya-core-community-safety-crime-prevention",
        "title": "地域防犯体制（防犯カメラ設置・通学路安全確保）と特殊詐欺対策"
      }
    ],
    "文化・景観・歴史": [
      {
        "id": "nagoya-core-historical-landscape-conservation",
        "title": "歴史的景観・伝統的建造物の保全と調和ある都市利用"
      },
      {
        "id": "nagoya-core-arts-culture-sports-promotion",
        "title": "文化芸術・スポーツ振興と文化施設の老朽化対策・利活用"
      }
    ]
  },
  "yokohama": {
    "防災・減災・治安": [
      {
        "id": "yokohama-mayor-YH-P-01",
        "title": "災害に強く、危機管理に優れた横浜"
      },
      {
        "id": "yokohama-core-disaster-prevention-resilience",
        "title": "大規模地震・風水害対策（耐震化・無電柱化・治水対策）と避難所環境改善"
      },
      {
        "id": "yokohama-core-community-safety-crime-prevention",
        "title": "地域防犯体制（防犯カメラ設置・通学路安全確保）と特殊詐欺対策"
      }
    ],
    "福祉・医療・健康": [
      {
        "id": "yokohama-mayor-YH-P-02",
        "title": "必要な人に必要な支援が届く福祉"
      },
      {
        "id": "yokohama-core-elderly-care-welfare",
        "title": "高齢者介護基盤の確保（介護人材・施設）と健康寿命延伸・孤立防止"
      },
      {
        "id": "yokohama-core-community-medical-system",
        "title": "地域医療体制（小児・周産期・救急医療）の確保と予防医療・ワクチン助成"
      }
    ],
    "都市再生・交通インフラ": [
      {
        "id": "yokohama-mayor-YH-P-03",
        "title": "暮らしを支えるインフラを守ります"
      },
      {
        "id": "yokohama-core-public-transport-reorganization",
        "title": "地域公共交通（地下鉄・市バス・コミュニティバス）の維持と利便性向上"
      },
      {
        "id": "yokohama-core-urban-development-infrastructure",
        "title": "主要駅周辺まちづくり・都市再生と老朽道路・橋梁の長寿命化"
      }
    ],
    "子育て・教育": [
      {
        "id": "yokohama-mayor-YH-P-04",
        "title": "子育て支援を充実させ、安心して子育て"
      },
      {
        "id": "yokohama-core-childcare-support-burden",
        "title": "子育て世帯の経済的負担軽減（医療費・給食費無償化）と待機児童対策"
      },
      {
        "id": "yokohama-core-school-education-environment",
        "title": "公立小中学校の教員不足対策・ICT教育推進と不登校支援"
      }
    ],
    "産業・観光・地域経済": [
      {
        "id": "yokohama-mayor-YH-P-05",
        "title": "18区の個性を生かし、地域活力向上"
      },
      {
        "id": "yokohama-mayor-YH-P-07",
        "title": "GREEN EXPO 2027で横浜の未来を"
      },
      {
        "id": "yokohama-mayor-YH-P-08",
        "title": "企業誘致で働く場所と新たな雇用創出"
      },
      {
        "id": "yokohama-mayor-YH-P-09",
        "title": "滞在型観光の拠点化"
      },
      {
        "id": "yokohama-mayor-YH-P-10",
        "title": "横浜を世界に誇るエンタメ一大拠点に"
      },
      {
        "id": "yokohama-core-sme-business-support",
        "title": "中小企業・商店街の物価高騰対策と事業承継・賃上げ支援"
      },
      {
        "id": "yokohama-core-tourism-local-economy",
        "title": "観光振興とオーバーツーリズム（混雑・マナー問題）対策の両立"
      }
    ],
    "財政・行革": [
      {
        "id": "yokohama-mayor-YH-P-06",
        "title": "財政基盤強化、将来世代に責任持つ市政"
      },
      {
        "id": "yokohama-mayor-YH-P-11",
        "title": "公正・適正な官民連携で民間の力活用"
      },
      {
        "id": "yokohama-mayor-YH-P-12",
        "title": "市職員の笑顔を取り戻し、市民のための市役所"
      },
      {
        "id": "yokohama-core-fiscal-discipline-reform",
        "title": "持続可能な財政規律の堅持と公共施設マネジメント・行革推進"
      },
      {
        "id": "yokohama-core-digital-gov-dx",
        "title": "行政DXの推進と窓口ワンストップ化・市民利便性向上"
      }
    ],
    "くらし・環境・エネルギー": [
      {
        "id": "yokohama-core-zero-carbon-renewable",
        "title": "脱炭素社会（ゼロカーボン）推進と再エネ導入・省エネ支援"
      },
      {
        "id": "yokohama-core-waste-reduction-recycling",
        "title": "一般廃棄物減量・プラスチック資源循環とごみ収集体制"
      }
    ],
    "文化・景観・歴史": [
      {
        "id": "yokohama-core-historical-landscape-conservation",
        "title": "歴史的景観・伝統的建造物の保全と調和ある都市利用"
      },
      {
        "id": "yokohama-core-arts-culture-sports-promotion",
        "title": "文化芸術・スポーツ振興と文化施設の老朽化対策・利活用"
      }
    ]
  },
  "kobe": {
    "都市再生・交通インフラ": [
      {
        "id": "kobe-mayor-sannomiya_redevelopment",
        "title": "都心・三宮再整備（三宮クロススクエア・新バスターミナル）"
      },
      {
        "id": "kobe-mayor-kobe_airport_international",
        "title": "神戸空港の国際化・機能強化（新サブターミナル整備）"
      },
      {
        "id": "kobe-mayor-tower_mansion_regulation",
        "title": "都心部タワーマンション建築規制・都心居住適正化"
      },
      {
        "id": "kobe-mayor-suburban_revitalization",
        "title": "郊外拠点のリノベーション（名谷・西神中央・垂水等の駅前再編）"
      },
      {
        "id": "kobe-core-public-transport-reorganization",
        "title": "地域公共交通（地下鉄・市バス・コミュニティバス）の維持と利便性向上"
      },
      {
        "id": "kobe-core-urban-development-infrastructure",
        "title": "主要駅周辺まちづくり・都市再生と老朽道路・橋梁の長寿命化"
      }
    ],
    "子育て・教育": [
      {
        "id": "kobe-mayor-childcare_education_support",
        "title": "子育て環境・教育無償化（高校生通学定期代全額補助）"
      },
      {
        "id": "kobe-core-childcare-support-burden",
        "title": "子育て世帯の経済的負担軽減（医療費・給食費無償化）と待機児童対策"
      },
      {
        "id": "kobe-core-school-education-environment",
        "title": "公立小中学校の教員不足対策・ICT教育推進と不登校支援"
      }
    ],
    "産業・観光・地域経済": [
      {
        "id": "kobe-mayor-biomedical_innovation",
        "title": "神戸医療産業都市（KBIC）の高度化とスタートアップ支援"
      },
      {
        "id": "kobe-core-sme-business-support",
        "title": "中小企業・商店街の物価高騰対策と事業承継・賃上げ支援"
      },
      {
        "id": "kobe-core-tourism-local-economy",
        "title": "観光振興とオーバーツーリズム（混雑・マナー問題）対策の両立"
      }
    ],
    "福祉・医療・健康": [
      {
        "id": "kobe-mayor-hospital_reorganization",
        "title": "公立・公的病院の再編統合（済生会兵庫県病院・三田市民病院）"
      },
      {
        "id": "kobe-core-elderly-care-welfare",
        "title": "高齢者介護基盤の確保（介護人材・施設）と健康寿命延伸・孤立防止"
      },
      {
        "id": "kobe-core-community-medical-system",
        "title": "地域医療体制（小児・周産期・救急医療）の確保と予防医療・ワクチン助成"
      }
    ],
    "財政・行革": [
      {
        "id": "kobe-mayor-fiscal_administrative_reform",
        "title": "行財政改革・市債残高圧縮と行政手続きオンライン化"
      },
      {
        "id": "kobe-core-fiscal-discipline-reform",
        "title": "持続可能な財政規律の堅持と公共施設マネジメント・行革推進"
      },
      {
        "id": "kobe-core-digital-gov-dx",
        "title": "行政DXの推進と窓口ワンストップ化・市民利便性向上"
      }
    ],
    "くらし・環境・エネルギー": [
      {
        "id": "kobe-core-zero-carbon-renewable",
        "title": "脱炭素社会（ゼロカーボン）推進と再エネ導入・省エネ支援"
      },
      {
        "id": "kobe-core-waste-reduction-recycling",
        "title": "一般廃棄物減量・プラスチック資源循環とごみ収集体制"
      }
    ],
    "防災・減災・治安": [
      {
        "id": "kobe-core-disaster-prevention-resilience",
        "title": "大規模地震・風水害対策（耐震化・無電柱化・治水対策）と避難所環境改善"
      },
      {
        "id": "kobe-core-community-safety-crime-prevention",
        "title": "地域防犯体制（防犯カメラ設置・通学路安全確保）と特殊詐欺対策"
      }
    ],
    "文化・景観・歴史": [
      {
        "id": "kobe-core-historical-landscape-conservation",
        "title": "歴史的景観・伝統的建造物の保全と調和ある都市利用"
      },
      {
        "id": "kobe-core-arts-culture-sports-promotion",
        "title": "文化芸術・スポーツ振興と文化施設の老朽化対策・利活用"
      }
    ]
  }
};

const INITIAL_VISIBLE_COUNT = 15;

export default function CategoryDetailPage({
    categoryName,
    onBack,
  
    topicStats,
    filteredThreads = [],
    filteredBills = [],
    speakerStats = [],
    issuesMap = {},
    onlyContestedBills,
    setOnlyContestedBills,
    onSpeakerClick,
    onViewContext,
    onSelectBill,
    onOpenMethodology,
    onOpenTopicDetail, cityCode = 'kyoto'
}) {
    const stat = topicStats.find(t => t.name === categoryName) || { count: filteredThreads.length, percentage: 0 };
    
  const [dynamicOverview, setDynamicOverview] = useState(null);

  useEffect(() => {
    fetch(`/data/${cityCode}_category_overviews.json`)
      .then(r => r.json())
      .then(data => {
        if(data[categoryName]) {
          setDynamicOverview(data[categoryName]);
        }
      })
      .catch(e => console.error("overview fetch error", e));
  }, [cityCode, categoryName]);

  const cityNameLabel = cityCode === 'kobe' ? '神戸市会' : cityCode === 'nagoya' ? '名古屋市会' : cityCode === 'yokohama' ? '横浜市会' : (cityCode === 'osaka' ? '大阪市会' : '京都市会');
  const overview = dynamicOverview || {
    lead: `${cityNameLabel}において「${categoryName}」分野に関する質疑が多数記録されています。`,
    key_points: []
  };

  
  const [topicSummaries, setTopicSummaries] = React.useState([]);
  React.useEffect(() => {
    fetch(`/data/${cityCode}_topic_summaries.json`)
      .then(r => r.json())
      .then(d => setTopicSummaries(d))
      .catch(e => console.error(e));
  }, [cityCode]);

  const coreTopics = useMemo(() => {
    if (!Array.isArray(topicSummaries)) return [];
    return topicSummaries
      .filter(t => t.category === categoryName)
      .map(t => ({ id: t.id || t.topic_id, title: t.title }));
  }, [topicSummaries, categoryName]);


    // 絞り込みフィルター用のステート
    const [selectedYear, setSelectedYear] = useState('');
    const [selectedCommittee, setSelectedCommittee] = useState('');
    const [selectedSpeaker, setSelectedSpeaker] = useState('');
    const [filterQuery, setFilterQuery] = useState('');
    const [sortOrder, setSortOrder] = useState('recent'); // 'recent' | 'score'
    const [visibleCount, setVisibleCount] = useState(INITIAL_VISIBLE_COUNT);

    // カテゴリー内の全質疑から、選択肢リスト（年次・会議体・発言者）を動的に生成
    const availableYears = useMemo(() => {
        const set = new Set();
        filteredThreads.forEach(s => {
            if (s.meeting_date && s.meeting_date.length >= 4) {
                set.add(s.meeting_date.slice(0, 4));
            }
        });
        return Array.from(set).sort((a, b) => b.localeCompare(a));
    }, [filteredThreads]);

    const availableCommittees = useMemo(() => {
        const counts = {};
        filteredThreads.forEach(s => {
            const name = getMeetingBodyName(s);
            counts[name] = (counts[name] || 0) + 1;
        });
        return Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .map(([name]) => name);
    }, [filteredThreads]);

    const availableSpeakers = useMemo(() => {
        const counts = {};
        filteredThreads.forEach(s => {
            const name = cleanName(s.speaker);
            if (name) counts[name] = (counts[name] || 0) + 1;
        });
        return Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .map(([name, count]) => ({ name, count }));
    }, [filteredThreads]);

    // フィルター変更時に表示件数をリセット
    useEffect(() => {
        setVisibleCount(INITIAL_VISIBLE_COUNT);
    }, [selectedYear, selectedCommittee, selectedSpeaker, filterQuery, sortOrder]);

    // 絞り込み ＆ ソート処理
    const processedThreads = useMemo(() => {
        let list = [...filteredThreads];

        if (selectedYear) {
            list = list.filter(s => (s.meeting_date || '').startsWith(selectedYear));
        }

        if (selectedCommittee) {
            list = list.filter(s => getMeetingBodyName(s) === selectedCommittee);
        }

        if (selectedSpeaker) {
            list = list.filter(s => cleanName(s.speaker) === selectedSpeaker);
        }

        if (filterQuery.trim()) {
            const q = filterQuery.trim().toLowerCase();
            list = list.filter(s =>
                (s.statement_text && s.statement_text.toLowerCase().includes(q)) ||
                (s.summary && s.summary.toLowerCase().includes(q)) ||
                (s.meeting_title && s.meeting_title.toLowerCase().includes(q))
            );
        }

        if (sortOrder === 'recent') {
            list.sort((a, b) => String(b.meeting_date || '').localeCompare(String(a.meeting_date || '')));
        } else if (sortOrder === 'score') {
            list.sort((a, b) => {
                const scoreA = (a.solution_score || 0) + (a.evidence_score || 0) + (a.local_focus_score || 0) + (a.constructive_score || 0);
                const scoreB = (b.solution_score || 0) + (b.evidence_score || 0) + (b.local_focus_score || 0) + (b.constructive_score || 0);
                return scoreB - scoreA;
            });
        }

        return list;
    }, [filteredThreads, selectedYear, selectedCommittee, selectedSpeaker, filterQuery, sortOrder]);

    const displayedThreads = useMemo(() => {
        return processedThreads.slice(0, visibleCount);
    }, [processedThreads, visibleCount]);

    const isFiltered = Boolean(selectedYear || selectedCommittee || selectedSpeaker || filterQuery);

    const handleResetFilters = () => {
        setSelectedYear('');
        setSelectedCommittee('');
        setSelectedSpeaker('');
        setFilterQuery('');
    };

    return (
        <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans pb-24 selection:bg-indigo-500 selection:text-white">
            {/* 画面上部固定バー */}
            <div className="bg-white border-b border-slate-200 sticky top-0 z-30 px-6 py-3.5 shadow-2xs">
                <div className="max-w-5xl mx-auto flex items-center justify-between">
                    <button
                        onClick={onBack}
                        className="inline-flex items-center text-xs font-bold text-slate-600 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50 border border-slate-200 px-3.5 py-2 rounded-xl transition-colors cursor-pointer"
                    >
                        <ArrowLeft className="w-4 h-4 mr-1.5" />
                        マクロ論戦マップへ戻る
                    </button>

                    <span className="text-xs font-bold text-slate-400">
                        市政マクロ分析 / 分野別詳細
                    </span>
                </div>
            </div>

            <main className="max-w-5xl mx-auto px-6 pt-8 space-y-8">

                {/* ① ヘッダー部 */}
                <header className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-100 flex items-center gap-1">
                            <PieChart className="w-3.5 h-3.5" />
                            政策カテゴリー
                        </span>
                        <span className="text-xs text-slate-500 font-bold">
                            市議会全体の <span className="text-indigo-600 font-black">{stat.percentage}%</span>（{filteredThreads.length}質疑スレッド）
                        </span>
                    </div>

                    <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight">
                        {categoryName}
                    </h1>
                </header>

                {/* ② AI包括解説カード */}
                <section className="bg-white rounded-3xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-5">
                    <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
                        <Sparkles className="w-4 h-4 fill-indigo-100" />
                        AI包括解説：この任期における「{categoryName}」の論戦総括
                    </div>

                    <p className="text-sm md:text-base leading-relaxed text-slate-700 font-medium">
                        {overview.lead}
                    </p>

                    {overview?.key_points?.length > 0 && (
                        <div className="pt-4 border-t border-slate-100 space-y-2.5">
                            <span className="text-[11px] font-black text-slate-400 uppercase tracking-wider block">
                                この分野における主な対立軸・重要争点
                            </span>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                                {overview?.key_points?.map((pt, i) => (
                                    <div key={i} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs font-bold text-slate-700 leading-relaxed flex items-start gap-2">
                                        <span className="w-2 h-2 rounded-full bg-indigo-500 mt-1 shrink-0" />
                                        <span>{pt}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </section>

                {/* ③ 注目の政策タイムライン（Policy Timeline導線） */}
                {coreTopics.length > 0 && (
                    <section className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                                <Milestone className="w-4 h-4 text-indigo-600" />
                                この分野の注目の政策タイムライン（年代別の議論の変遷）
                            </h2>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            {coreTopics.map((ct) => (
                                <button
                                    key={ct.id}
                                    onClick={() => onOpenTopicDetail(ct.id)}
                                    className="p-4 bg-white rounded-2xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all text-left flex flex-col justify-between group cursor-pointer"
                                >
                                    <div>
                                        <span className="text-[10px] font-black text-indigo-600 uppercase tracking-wider block mb-1">
                                            Policy Timeline
                                        </span>
                                        <h3 className="text-sm font-extrabold text-slate-900 group-hover:text-indigo-600 transition-colors">
                                            {ct.title}
                                        </h3>
                                    </div>
                                    <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-slate-400 group-hover:text-indigo-600">
                                        <span>詳細タイムラインを見る</span>
                                        <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                                    </div>
                                </button>
                            ))}
                        </div>
                    </section>
                )}

                {/* ④ 質疑スレッド一覧（全件対象の高度フィルターバー付き） */}
                <section className="space-y-5 pt-4 border-t border-slate-200">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                            <h2 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                                <MessageSquare className="w-4 h-4 text-indigo-600" />
                                「{categoryName}」に関する質疑スレッド
                            </h2>
                            <p className="text-xs text-slate-400 font-bold mt-0.5">
                                該当: <span className="text-indigo-600">{processedThreads.length}</span> 件 / 全 {filteredThreads.length} 件
                            </p>
                        </div>
                    </div>

                    {/* フィルターバー */}
                    <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs space-y-3 text-xs">
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5">

                            {/* 年次フィルター */}
                            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5">
                                <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                <select
                                    value={selectedYear}
                                    onChange={(e) => setSelectedYear(e.target.value)}
                                    className="w-full bg-transparent font-bold text-slate-700 outline-none cursor-pointer"
                                >
                                    <option value="">すべての年次</option>
                                    {availableYears.map(y => (
                                        <option key={y} value={y}>{y}年</option>
                                    ))}
                                </select>
                            </div>

                            {/* 会議体フィルター */}
                            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5">
                                <Landmark className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                <select
                                    value={selectedCommittee}
                                    onChange={(e) => setSelectedCommittee(e.target.value)}
                                    className="w-full bg-transparent font-bold text-slate-700 outline-none cursor-pointer truncate"
                                >
                                    <option value="">すべての会議体</option>
                                    {availableCommittees.map(c => (
                                        <option key={c} value={c}>{c}</option>
                                    ))}
                                </select>
                            </div>

                            {/* 発言者フィルター（肩書を省いた氏名表記） */}
                            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5">
                                <User className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                <select
                                    value={selectedSpeaker}
                                    onChange={(e) => setSelectedSpeaker(e.target.value)}
                                    className="w-full bg-transparent font-bold text-slate-700 outline-none cursor-pointer truncate"
                                >
                                    <option value="">すべての発言者</option>
                                    {availableSpeakers.map(spk => (
                                        <option key={spk.name} value={spk.name}>
                                            {spk.name} ({spk.count}件)
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* キーワード内検索 */}
                            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5">
                                <Search className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                <input
                                    type="text"
                                    value={filterQuery}
                                    onChange={(e) => setFilterQuery(e.target.value)}
                                    placeholder="キーワードで絞り込み..."
                                    className="w-full bg-transparent font-bold text-slate-700 outline-none placeholder:text-slate-400"
                                />
                            </div>

                        </div>

                        {/* ソート順 ＆ リセット */}
                        <div className="flex items-center justify-between pt-2 border-t border-slate-100 flex-wrap gap-2">
                            <div className="flex items-center gap-1.5">
                                <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                                <select
                                    value={sortOrder}
                                    onChange={(e) => setSortOrder(e.target.value)}
                                    className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 font-bold text-slate-700 outline-none cursor-pointer"
                                >
                                    <option value="recent">登壇日が新しい順</option>
                                    <option value="score">AI評価スコア順</option>
                                </select>
                            </div>

                            {isFiltered && (
                                <button
                                    onClick={handleResetFilters}
                                    className="text-xs font-bold text-rose-600 hover:underline cursor-pointer"
                                >
                                    条件をすべてリセット
                                </button>
                            )}
                        </div>
                    </div>

                    {/* スレッドカードのレンダリング */}
                    <div className="space-y-6">
                        {displayedThreads.length > 0 ? (
                            displayedThreads.map((stmt) => (
                                <ThreadCard cityCode={cityCode}
                                    key={stmt.id}
                                    stmt={stmt}
                                    speakerInfo={speakerStats.find(s => s.speaker === cleanName(stmt.speaker))}
                                    onSpeakerClick={onSpeakerClick}
                                    onViewContext={onViewContext}
                                    showSpeakerHeader={true}
                                    onOpenMethodology={onOpenMethodology}
                                />
                            ))
                        ) : (
                            <div className="text-center py-16 bg-white rounded-2xl border border-slate-200 text-xs font-bold text-slate-400">
                                選択した条件に一致する質疑スレッドは見つかりませんでした。
                            </div>
                        )}
                    </div>

                    {/* ページネーション（さらに表示ボタン） */}
                    {visibleCount < processedThreads.length && (
                        <div className="text-center pt-4">
                            <button
                                onClick={() => setVisibleCount(prev => prev + 15)}
                                className="inline-flex items-center gap-1.5 px-6 py-3 rounded-xl bg-white hover:bg-slate-50 border border-slate-300 text-xs font-bold text-slate-700 shadow-2xs hover:shadow-xs transition-all cursor-pointer"
                            >
                                <span>さらに質疑を表示する（残り {processedThreads.length - visibleCount} 件）</span>
                                <ChevronDown className="w-4 h-4 text-slate-400" />
                            </button>
                        </div>
                    )}
                </section>

            </main>
        </div>
    );
}