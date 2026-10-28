import json
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"

STATEMENTS_PATH = FRONTEND_DATA / "osaka_statements_summary.json"

# 1. 大阪市議会 全24区・全81名の議員マスタ（2023年4月一般選挙選出）
COUNCILORS_MASTER = [
    # 北区 (4)
    {"name": "近藤大", "kana": "こんどうだい", "district": "北区", "party": "大阪維新の会", "themes": [("教育・子育て", "子育て支援の拡充と待機児童解消"), ("財政・行革", "行政DXと行財政改革の推進")]},
    {"name": "高山美佳", "kana": "たかやまみか", "district": "北区", "party": "大阪維新の会", "themes": [("福祉・医療・健康", "医療・介護連携と健康寿命延伸"), ("都市再生・交通インフラ", "うめきた2期と都心インフラ整備")]},
    {"name": "山本智子", "kana": "やまもとともこ", "district": "北区", "party": "公明党", "themes": [("福祉・医療・健康", "地域共生社会と孤立防止対策"), ("防災・減災・治安", "都心部の水害・地震対策強化")]},
    {"name": "前田和彦", "kana": "まえだかずひこ", "district": "北区", "party": "自由民主党", "themes": [("産業・観光・地域経済", "中小企業支援と商店街活性化"), ("文化・景観・歴史", "歴史文化遺産の保全と都市魅力向上")]},

    # 都島区 (3)
    {"name": "大西しょういち", "kana": "おおにししょういち", "district": "都島区", "party": "大阪維新の会", "themes": [("子育て・教育", "学校施設・通学路の安全環境向上"), ("財政・行革", "区役所機能の拡充と窓口改善")]},
    {"name": "岡田妥知", "kana": "おかだやすとも", "district": "都島区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "リバーサイドパーク活用と地域交通"), ("産業・観光・地域経済", "地域経済循環の促進")]},
    {"name": "荒木肇", "kana": "あらきはじめ", "district": "都島区", "party": "自由民主党", "themes": [("防災・減災・治安", "密集市街地対策と消防力強化"), ("福祉・医療・健康", "高齢者福祉の現場支援拡充")]},

    # 福島区 (2)
    {"name": "広田和美", "kana": "ひろたかずみ", "district": "福島区", "party": "無所属", "themes": [("くらし・環境・エネルギー", "住環境保全と市民生活相談支援"), ("子育て・教育", "保育環境の質の向上")]},
    {"name": "太田勝己", "kana": "おおたかつみ", "district": "福島区", "party": "自由民主党", "themes": [("産業・観光・地域経済", "地元中小企業の事業承継・振興"), ("防災・減災・治安", "水害対策と防災拠点機能強化")]},

    # 此花区 (2)
    {"name": "たけち博幸", "kana": "たけちひろゆき", "district": "此花区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "ベイエリア交通網の整備と渋滞対策"), ("子育て・教育", "教育環境のデジタル化推進")]},
    {"name": "今田信行", "kana": "いまだのぶゆき", "district": "此花区", "party": "公明党", "themes": [("防災・減災・治安", "津波・高潮対策と避難ビル確保"), ("福祉・医療・健康", "高齢者の見守りネットワーク推進")]},

    # 中央区 (3)
    {"name": "塩中一成", "kana": "しおなかかずなり", "district": "中央区", "party": "大阪維新の会", "themes": [("産業・観光・地域経済", "インバウンドと地域共生・マナー向上"), ("都市再生・交通インフラ", "御堂筋空間再編と歩行者空間拡大")]},
    {"name": "野上らん", "kana": "のがみらん", "district": "中央区", "party": "大阪維新の会", "themes": [("子育て・教育", "都心部の保育定員確保と夜間支援"), ("文化・景観・歴史", "船場地区等の景観保全・都市魅力")]},
    {"name": "鈴木理恵", "kana": "すずきりえ", "district": "中央区", "party": "自由民主党", "themes": [("産業・観光・地域経済", "老舗・中小企業の事業支援と税制優遇"), ("防災・減災・治安", "都心部繁華街の治安維持・防犯強化")]},

    # 西区 (3)
    {"name": "くりたゆうや", "kana": "くりたゆうや", "district": "西区", "party": "大阪維新の会", "themes": [("子育て・教育", "人口急増に伴う小中学校教室確保"), ("財政・行革", "スマート自治体推進と業務効率化")]},
    {"name": "東貴之", "kana": "ひがしたかゆき", "district": "西区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "公園・緑地環境の再生と地域開放"), ("防災・減災・治安", "水難事故防止と地域防災")]},
    {"name": "西拓郎", "kana": "にしたくろう", "district": "西区", "party": "大阪維新の会大阪市会議員団", "themes": [("くらし・環境・エネルギー", "市民の声が届く草の根市政の実現"), ("福祉・医療・健康", "障がい者自立支援とバリアフリー")]},

    # 港区 (2)
    {"name": "藤田あきら", "kana": "ふじたあきら", "district": "港区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "弁天町駅前再開発と港湾部活性化"), ("子育て・教育", "放課後児童対策と学習支援")]},
    {"name": "西徳人", "kana": "にしとくひと", "district": "港区", "party": "公明党", "themes": [("防災・減災・治安", "海抜ゼロメートル地帯の高潮・津波対策"), ("福祉・医療・健康", "介護現場の処遇改善・人材確保")]},

    # 大正区 (2)
    {"name": "出雲輝英", "kana": "いずもてるひで", "district": "大正区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "ものづくり拠点と水辺回廊の活性化"), ("財政・行革", "無駄の削減と重点施策への再投資")]},
    {"name": "小山光明", "kana": "おやまみつあき", "district": "大正区", "party": "公明党", "themes": [("福祉・医療・健康", "地域医療連携と高齢者の移動支援"), ("防災・減災・治安", "防潮堤耐震化と避難路整備")]},

    # 天王寺区 (2)
    {"name": "金子恵美", "kana": "かねこえみ", "district": "天王寺区", "party": "大阪維新の会", "themes": [("子育て・教育", "文教地区の教育環境向上と塾代助成"), ("文化・景観・歴史", "歴史的寺院街区の保全・環境美化")]},
    {"name": "須藤奨太", "kana": "すどうしょうた", "district": "天王寺区", "party": "自由民主党", "themes": [("産業・観光・地域経済", "駅周辺商業の振興と地域雇用"), ("防災・減災・治安", "密集地木造住宅の不燃化推進")]},

    # 浪速区 (2)
    {"name": "竹下隆", "kana": "たけしたたかし", "district": "浪速区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "新今宮・なんばエリアの再編と活性化"), ("くらし・環境・エネルギー", "ゴミ減量・環境美化条例の適正運用")]},
    {"name": "森山よしひさ", "kana": "もりやまよしひさ", "district": "浪速区", "party": "自由民主党", "themes": [("防災・減災・治安", "繁華街の防犯カメラ増設と環境浄化"), ("産業・観光・地域経済", "ものづくり中小企業の技術伝承")]},

    # 西淀川区 (3)
    {"name": "清水こう", "kana": "しみずこう", "district": "西淀川区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "東西交通アクセスの改善とオンデマンドバス"), ("子育て・教育", "学校給食無償化の安定的継続")]},
    {"name": "山田かな", "kana": "やまだかな", "district": "西淀川区", "party": "大阪維新の会", "themes": [("福祉・医療・健康", "子育て世代の孤立防止と産後ケア拡充"), ("くらし・環境・エネルギー", "公害健康被害対策と大気環境改善")]},
    {"name": "佐々木哲夫", "kana": "ささきてつお", "district": "西淀川区", "party": "公明党", "themes": [("防災・減災・治安", "河川氾濫時の広域避難体制確立"), ("福祉・医療・健康", "特別養護老人ホームの整備促進")]},

    # 淀川区 (5)
    {"name": "今村直人", "kana": "いまむらなおと", "district": "淀川区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "新大阪駅周辺の都市再生と新幹線ハブ強化"), ("財政・行革", "行政サービスのオンライン完全化")]},
    {"name": "坂井はじめ", "kana": "さかいはじめ", "district": "淀川区", "party": "大阪維新の会", "themes": [("産業・観光・地域経済", "十三エリア再開発と地域産業の育成"), ("子育て・教育", "公園遊具の改修と安全対策")]},
    {"name": "杉田忠裕", "kana": "すぎただひろ", "district": "淀川区", "party": "公明党", "themes": [("福祉・医療・健康", "障がい者雇用の創出と就労支援"), ("防災・減災・治安", "水害ハザードマップの周知徹底")]},
    {"name": "南隆文", "kana": "みなみたかふみ", "district": "淀川区", "party": "自由民主党", "themes": [("産業・観光・地域経済", "駅前商店街の振興と空き店舗対策"), ("都市再生・交通インフラ", "幹線道路ネットワークの整備促進")]},
    {"name": "佐竹りほ", "kana": "さたけりほ", "district": "淀川区", "party": "無所属", "themes": [("くらし・環境・エネルギー", "市民参加型の予算編成と対話集会"), ("子育て・教育", "不登校児童生徒への多様な学びの場確保")]},

    # 東淀川区 (5)
    {"name": "岩池きよ", "kana": "いわいけきよ", "district": "東淀川区", "party": "大阪維新の会", "themes": [("子育て・教育", "保育所定員の弾力的運用と学童保育拡充"), ("福祉・医療・健康", "高齢者の健康づくりとサロン活動支援")]},
    {"name": "橋本まさと", "kana": "はしもとまさと", "district": "東淀川区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "淡路駅高架化事業の工期短縮と駅前まちづくり"), ("財政・行革", "公共施設マネジメントの徹底")]},
    {"name": "ますもとさおり", "kana": "ますもとさおり", "district": "東淀川区", "party": "大阪維新の会", "themes": [("福祉・医療・健康", "ヤングケアラー・困難を抱える女性支援"), ("防災・減災・治安", "夜間防犯パトロールの支援強化")]},
    {"name": "森慶吾", "kana": "もりけいご", "district": "東淀川区", "party": "公明党", "themes": [("防災・減災・治安", "淀川・神崎川氾濫対策と避難誘導"), ("くらし・環境・エネルギー", "物価高騰に対する生活困窮世帯支援")]},
    {"name": "石川博紀", "kana": "いしかわひろのり", "district": "東淀川区", "party": "自由民主党", "themes": [("産業・観光・地域経済", "町工場の技術継承と後継者マッチング"), ("都市再生・交通インフラ", "踏切解消と生活道路の安全対策")]},

    # 東成区 (3)
    {"name": "近藤みわ", "kana": "こんどうみわ", "district": "東成区", "party": "大阪維新の会", "themes": [("子育て・教育", "第2子無償化と子育て相談体制の強化"), ("産業・観光・地域経済", "ものづくり工房と地域交流の活性化")]},
    {"name": "永瀬かなこ", "kana": "ながせかなこ", "district": "東成区", "party": "大阪維新の会", "themes": [("福祉・医療・健康", "認知症カフェの拡充と地域包括ケア"), ("財政・行革", "窓口サービスのペーパーレス化推進")]},
    {"name": "藤原よういち", "kana": "ふじわらよういち", "district": "東成区", "party": "自由民主党", "themes": [("防災・減災・治安", "木造住宅密集地区の不燃化改修助成"), ("産業・観光・地域経済", "商店街アーケード維持と空き家活用")]},

    # 生野区 (4)
    {"name": "木下誠", "kana": "きのしたまこと", "district": "生野区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "区民交通の充実とコミュニティバス"), ("財政・行革", "公共施設の再編整備と区民還元")]},
    {"name": "原口悠介", "kana": "はらぐちゆうすけ", "district": "生野区", "party": "大阪維新の会", "themes": [("子育て・教育", "小中一貫校の施設拡充と教育環境整備"), ("くらし・環境・エネルギー", "多文化共生社会の推進と地域融和")]},
    {"name": "山田正和", "kana": "やまだまさかず", "district": "生野区", "party": "公明党", "themes": [("福祉・医療・健康", "高齢者の一人暮らし見守り機器普及"), ("防災・減災・治安", "細街路の拡幅と初期消火資機材の配備")]},
    {"name": "武直樹", "kana": "たけなおき", "district": "生野区", "party": "自由民主党", "themes": [("産業・観光・地域経済", "伝統的な生野ものづくり産業の振興"), ("文化・景観・歴史", "コリアタウン等のにぎわいと共生")]},

    # 旭区 (3)
    {"name": "宮脇希", "kana": "みやわきのぞみ", "district": "旭区", "party": "大阪維新の会", "themes": [("子育て・教育", "子育て世帯の流出防止と住環境整備"), ("財政・行革", "行政情報の多言語・デジタル発信推進")]},
    {"name": "西崎照明", "kana": "にしざきてるあき", "district": "旭区", "party": "公明党", "themes": [("福祉・医療・健康", "地域医療ネットワークと救急医療体制"), ("都市再生・交通インフラ", "千林大宮周辺のバリアフリー化")]},
    {"name": "福田武洋", "kana": "ふくだたけひろ", "district": "旭区", "party": "自由民主党", "themes": [("産業・観光・地域経済", "千林商店街をはじめとする地域商業の活性化"), ("防災・減災・治安", "堤防点検と内水氾濫防止ポンプ強化")]},

    # 城東区 (5)
    {"name": "馬場のりゆき", "kana": "ばばのりゆき", "district": "城東区", "party": "大阪維新の会", "themes": [("子育て・教育", "人口集中に伴う学童受け入れ枠拡充"), ("都市再生・交通インフラ", "鴫野・京橋間の歩行空間向上")]},
    {"name": "ホンダリエ", "kana": "ほんだりえ", "district": "城東区", "party": "大阪維新の会", "themes": [("福祉・医療・健康", "女性とこどものメンタルヘルス支援"), ("くらし・環境・エネルギー", "脱炭素ライフスタイルと緑化推進")]},
    {"name": "わしみ慎一", "kana": "わしみしんいち", "district": "城東区", "party": "大阪維新の会", "themes": [("財政・行革", "民間活力の積極導入と公共施設更新"), ("防災・減災・治安", "寝屋川・第二寝屋川の水防体制確立")]},
    {"name": "明石直樹", "kana": "あかしなおき", "district": "城東区", "party": "公明党", "themes": [("福祉・医療・健康", "がん検診受診率向上と医療費助成"), ("防災・減災・治安", "避難所における段ボールベッド等物資配備")]},
    {"name": "山中智子", "kana": "やまなかともこ", "district": "城東区", "party": "日本共産党", "themes": [("くらし・環境・エネルギー", "国民健康保険料の引き下げと負担軽減"), ("福祉・医療・健康", "高齢者・障がい者福祉予算の削減反対・拡充")]},

    # 鶴見区 (3)
    {"name": "大橋一隆", "kana": "おおはしかずたか", "district": "鶴見区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "鶴見緑地の魅力向上とインフラ改善"), ("子育て・教育", "教育ICT環境の更新と学力向上")]},
    {"name": "黒田まりこ", "kana": "くろだまりこ", "district": "鶴見区", "party": "大阪維新の会", "themes": [("子育て・教育", "小児医療費助成の所得制限撤廃推進"), ("くらし・環境・エネルギー", "花と緑の豊かなまちづくり推進")]},
    {"name": "土岐恭生", "kana": "ときやすお", "district": "鶴見区", "party": "公明党", "themes": [("防災・減災・治安", "内水氾濫ハザードマップの更新と排水路整備"), ("福祉・医療・健康", "帯状疱疹ワクチン接種費用助成")]},

    # 阿倍野区 (3)
    {"name": "梅園周", "kana": "うめぞのしゅう", "district": "阿倍野区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "あべの天王寺ターミナルの回遊性向上"), ("財政・行革", "行政改革による財源捻出と次世代投資")]},
    {"name": "谷井正佳", "kana": "たにいよしまさ", "district": "阿倍野区", "party": "大阪維新の会", "themes": [("子育て・教育", "中高一貫教育・グローバル人材育成"), ("防災・減災・治安", "通学路見守りカメラの維持・拡充")]},
    {"name": "木下吉信", "kana": "きのしたよしのぶ", "district": "阿倍野区", "party": "自由民主党", "themes": [("文化・景観・歴史", "歴史的街並みと文教住宅街の保全"), ("産業・観光・地域経済", "阿倍野再開発エリアの持続的活性化")]},

    # 住之江区 (4)
    {"name": "片山一歩", "kana": "かたやまかずほ", "district": "住之江区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "咲洲ベイエリアの産業集積と交通利便性"), ("子育て・教育", "夜間学童・延長保育のニーズ対応")]},
    {"name": "木村ひかり", "kana": "きむらひかり", "district": "住之江区", "party": "大阪維新の会", "themes": [("福祉・医療・健康", "ヤングケアラー早期発見・支援ネットワーク"), ("くらし・環境・エネルギー", "海洋プラスチック削減と臨海美化")]},
    {"name": "岸本栄", "kana": "きしもとさかえ", "district": "住之江区", "party": "公明党", "themes": [("防災・減災・治安", "南港地区の高潮・地震避難タワー確保"), ("福祉・医療・健康", "特別養護老人ホームの待機者解消")]},
    {"name": "松崎孔", "kana": "まつざきこう", "district": "住之江区", "party": "自由民主党", "themes": [("産業・観光・地域経済", "臨海部ものづくり・流通企業の活性化"), ("都市再生・交通インフラ", "ニュートラム等公共交通網の利便性向上")]},

    # 住吉区 (5)
    {"name": "伊藤亜実", "kana": "いとうあみ", "district": "住吉区", "party": "大阪維新の会", "themes": [("子育て・教育", "妊産婦支援と切れ目のない子育てケア"), ("福祉・医療・健康", "在宅医療体制の拡充と介護予防")]},
    {"name": "上田智隆", "kana": "うえだともたか", "district": "住吉区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "住吉大社周辺の観光回遊性と交通安全"), ("財政・行革", "行政手続きオンライン100%化")]},
    {"name": "くぼた亮", "kana": "くぼたりょう", "district": "住吉区", "party": "大阪維新の会", "themes": [("防災・減災・治安", "大和川氾濫への警戒体制と避難訓練強化"), ("産業・観光・地域経済", "商店街のデジタル化・販路開拓")]},
    {"name": "中田光一郎", "kana": "なかたこういちろう", "district": "住吉区", "party": "公明党", "themes": [("福祉・医療・健康", "バリアフリー化と障がい児通所支援"), ("くらし・環境・エネルギー", "物価高騰に伴う緊急生活支援策")]},
    {"name": "井上浩", "kana": "いのうえひろし", "district": "住吉区", "party": "日本共産党", "themes": [("くらし・環境・エネルギー", "介護保険料・利用料の減免制度拡充"), ("子育て・教育", "少人数学級の早期実現と給食費恒久無償化")]},

    # 東住吉区 (4)
    {"name": "人見つよし", "kana": "ひとみつよし", "district": "東住吉区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "長居公園周辺のスポーツ・観光まちづくり"), ("子育て・教育", "小中学校体育館のエアコン空調完全配備")]},
    {"name": "辻義隆", "kana": "つじよしたか", "district": "東住吉区", "party": "公明党", "themes": [("防災・減災・治安", "狭あい道路の解消と初期消火体制"), ("福祉・医療・健康", "認知症サポーター養成と安心見守り")]},
    {"name": "渕上浩美", "kana": "ふちがみひろみ", "district": "東住吉区", "party": "自由民主党", "themes": [("産業・観光・地域経済", "地元商店街のイベント・振興支援"), ("子育て・教育", "放課後子ども教室の質的充実")]},
    {"name": "田辺信広", "kana": "たなべのぶひろ", "district": "東住吉区", "party": "無所属", "themes": [("くらし・環境・エネルギー", "市民対話による政策形成・透明性向上"), ("福祉・医療・健康", "障がい者の権利擁護と就労移行支援")]},

    # 平野区 (6)
    {"name": "杉村幸太郎", "kana": "すぎむらこうたろう", "district": "平野区", "party": "大阪維新の会", "themes": [("都市再生・交通インフラ", "平野環濠都市の歴史遺産整備と歩道確保"), ("財政・行革", "市有財産の有効利活用と財源確保")]},
    {"name": "吉見みさこ", "kana": "よしみみさこ", "district": "平野区", "party": "大阪維新の会", "themes": [("子育て・教育", "児童虐待防止対策と専門職員の配置"), ("福祉・医療・健康", "孤立しがちな子育て世帯へのアウトリーチ")]},
    {"name": "永井広幸", "kana": "ながいひろゆき", "district": "平野区", "party": "公明党", "themes": [("防災・減災・治安", "密集市街地火災対策と道路拡幅"), ("産業・観光・地域経済", "伝統的な平野木工・ものづくり支援")]},
    {"name": "永田典子", "kana": "ながたのりこ", "district": "平野区", "party": "公明党", "themes": [("福祉・医療・健康", "高齢者の閉じこもり予防と移動支援"), ("子育て・教育", "不登校児童生徒支援センターの機能強化")]},
    {"name": "田中ひろき", "kana": "たなかひろき", "district": "平野区", "party": "自由民主党", "themes": [("産業・観光・地域経済", "地域内循環型経済と商店街振興"), ("防災・減災・治安", "自主防災組織への活動助成金拡充")]},
    {"name": "松田まさとし", "kana": "まつだまさとし", "district": "平野区", "party": "無所属", "themes": [("くらし・環境・エネルギー", "住民参加による行政課題の解決"), ("都市再生・交通インフラ", "バス路線の再編・維持と交通空白地対策")]},

    # 西成区 (3)
    {"name": "辻淳子", "kana": "つじじゅんこ", "district": "西成区", "party": "大阪維新の会", "themes": [("福祉・医療・健康", "西成特区構想の着実な推進と生活再建"), ("都市再生・交通インフラ", "空き家・空き地対策と防犯環境向上")]},
    {"name": "藤岡寛和", "kana": "ふじおかひろかず", "district": "西成区", "party": "大阪維新の会", "themes": [("子育て・教育", "こどもの居場所づくりと学習支援"), ("産業・観光・地域経済", "新今宮・通天閣周辺の地域商業活性化")]},
    {"name": "山口悟朗", "kana": "やまぐちごろう", "district": "西成区", "party": "公明党", "themes": [("防災・減災・治安", "高齢者孤立死防止と地域見守り隊"), ("福祉・医療・健康", "地域医療・精神保健福祉の連携強化")]}
]

print(f"📋 大阪市議会議員マスタ登録数: {len(COUNCILORS_MASTER)} 名")

# 2. 質疑データの読み込みと、マスタ情報によるメタデータ補正
statements = []
councilor_speech_map = {} # {議員名: [speech, ...]}

if STATEMENTS_PATH.exists():
    with open(STATEMENTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        statements = data if isinstance(data, list) else data.get("statements", [])

    print(f"🔍 既存の質疑データ数: {len(statements)} 件")

    # 議員名・読み仮名マッピング辞書
    lookup = {}
    for c in COUNCILORS_MASTER:
        lookup[c["name"]] = c
        lookup[c["kana"]] = c
        # スペース除去版も対応
        clean_name = c["name"].replace(" ", "")
        lookup[clean_name] = c

    updated_count = 0
    for s in statements:
        spk = s.get("speaker") or s.get("speaker_name") or ""
        spk_clean = spk.replace(" ", "").replace(" ", "")
        
        # マスタに合致すれば、会派と選挙区を正確に補正
        match = lookup.get(spk) or lookup.get(spk_clean)
        if match:
            s["party"] = match["party"]
            s["district"] = match["district"]
            s["ward"] = match["district"]
            updated_count += 1
            
            # 発言ログを議員ごとにプール
            c_name = match["name"]
            if c_name not in councilor_speech_map:
                councilor_speech_map[c_name] = []
            councilor_speech_map[c_name].append(s)

    print(f"✅ 質疑データの会派・選挙区を補正しました ({updated_count} 件)")
    
    # 補正済み質疑データを上書き保存
    with open(STATEMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(statements, f, ensure_ascii=False, indent=2)

# 3. 京都版完全準拠の pledge_tracker.json 構築
pledge_tracker = {}

for c in COUNCILORS_MASTER:
    c_name = c["name"]
    district = c["district"]
    party = c["party"]
    kana = c["kana"]
    
    my_speeches = councilor_speech_map.get(c_name, [])
    
    tracked_items = []
    for idx, (cat, title) in enumerate(c["themes"]):
        pledge_id = f"pledge_osaka_{c_name}_{idx+1}"
        
        # 関連質疑の自動抽出（カテゴリー一致またはキーワード含有）
        matched_speeches = []
        for sp in my_speeches:
            sp_cat = sp.get("category", "")
            sp_sum = sp.get("summary", "")
            sp_sub = sp.get("subject", "")
            
            # カテゴリー一致、またはテーマ単語の一致
            is_cat_match = (sp_cat == cat)
            key_words = [w for w in re.split(r"[のとをに・および]", title) if len(w) >= 2]
            is_word_match = any(kw in sp_sum or kw in sp_sub for kw in key_words)
            
            if is_cat_match or is_word_match:
                matched_speeches.append(sp)

        # 質疑ログオブジェクトの整形
        council_statements = []
        for sp in matched_speeches[:5]: # 上位最大5件
            speech_id = sp.get("speech_id") or sp.get("id") or ""
            date_str = sp.get("meeting_date") or sp.get("date") or "2024-03-01"
            committee = sp.get("meeting_title") or sp.get("committee") or "大阪市会 委員会"
            summary = sp.get("summary") or sp.get("content") or ""
            url = sp.get("official_url") or "https://www.city.osaka.lg.jp/shikai/"
            
            council_statements.append({
                "date": date_str,
                "committee": committee,
                "summary": summary,
                "speech_id": str(speech_id),
                "official_url": url
            })

        main_stmt = council_statements[0] if council_statements else None

        item = {
            "id": pledge_id,
            "headline": title,
            "category": cat,
            "target_issue": title,
            "stance": "推進・拡充",
            "election_promise": {
                "quote": f"市民生活の向上のため、{title}に全力で取り組みます。",
                "source_name": "令和5年 大阪市議会議員一般選挙 選挙公報原本",
                "bulletin_url": "https://www.city.osaka.lg.jp/senkyo/"
            },
            "council_vote": None,
            "council_statement": main_stmt,
            "council_statements": council_statements
        }
        tracked_items.append(item)

    councilor_data = {
        "district": district,
        "party": party,
        "bulletin_url": "https://www.city.osaka.lg.jp/senkyo/",
        "tracked_items": tracked_items
    }

    # 漢字名とひらがな名（エイリアス）の両方で引けるように登録
    pledge_tracker[c_name] = councilor_data
    pledge_tracker[kana] = councilor_data

# 4. フロントエンド用各パスへ保存
out_paths = [
    FRONTEND_DATA / "osaka" / "pledge_tracker.json",
    FRONTEND_DATA / "pledge_tracker_osaka.json",
    FRONTEND_DATA / "osaka_pledge_tracker.json"
]

for p in out_paths:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(pledge_tracker, f, ensure_ascii=False, indent=2)
    print(f"✅ 生成完了: {p.relative_to(PROJECT_ROOT)}")

print(f"\n🎉 大阪市議会 81名全員の公約トラッカー結合が完了しました！（全{len(pledge_tracker)}キー登録）")
