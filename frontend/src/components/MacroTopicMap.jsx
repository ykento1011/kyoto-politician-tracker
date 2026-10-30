// 全都市の正規論点マスター（各都市の topic_summaries.json と完全連動）
const ALL_CITY_TOPICS = {
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

export const KYOTO_CATEGORY_TOPICS = ALL_CITY_TOPICS.kyoto || {};
export const OSAKA_CATEGORY_TOPICS = ALL_CITY_TOPICS.osaka || {};
export const NAGOYA_CATEGORY_TOPICS = ALL_CITY_TOPICS.nagoya || {};
export const YOKOHAMA_CATEGORY_TOPICS = ALL_CITY_TOPICS.yokohama || {};
export const KOBE_CATEGORY_TOPICS = ALL_CITY_TOPICS.kobe || {};

import React, { useMemo } from 'react';
import { PieChart, Flame, ArrowRight } from 'lucide-react';

export default function MacroTopicMap({
  topicStats = [],
  cityCode = 'kyoto',
  selectedCategory,
  onOpenCategoryDetail,
  getIssueCountForCategory,
  onOpenTopicDetail
}) {
  const totalThreadsCount = useMemo(() => {
    return topicStats.reduce((sum, t) => sum + (t.count || 0), 0);
  }, [topicStats]);

  const ALL_CITY_TOPICS = {
    kyoto: KYOTO_CATEGORY_TOPICS,
    osaka: OSAKA_CATEGORY_TOPICS,
    nagoya: NAGOYA_CATEGORY_TOPICS,
    yokohama: YOKOHAMA_CATEGORY_TOPICS,
    kobe: KOBE_CATEGORY_TOPICS,
  };
  const activeCategoryTopicsMap = ALL_CITY_TOPICS[cityCode] || ALL_CITY_TOPICS.kyoto || {};

  return (
    <section className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-extrabold text-slate-800 flex items-center">
            <PieChart className="w-4 h-4 mr-1.5 text-indigo-500" />
            市議会マクロ論戦マップ
          </h3>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
            全{totalThreadsCount.toLocaleString()}スレッドの質疑量と、8大分野の重要政策タイムライン
          </p>
        </div>
      </div>
      
      {/* 8大カテゴリーのグリッド */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
        {topicStats.map(topic => {
          const issueCount = getIssueCountForCategory ? getIssueCountForCategory(topic.name) : 0;
          const coreTopics = activeCategoryTopicsMap[topic.name] || [];

          return (
            <div 
              key={topic.name} 
              onClick={() => onOpenCategoryDetail && onOpenCategoryDetail(topic.name)}
              className="flex flex-col justify-between p-3.5 rounded-xl border bg-white border-slate-200 hover:border-indigo-400 hover:shadow-md transition-all cursor-pointer group"
            >
              {/* カード上部：カテゴリ名と激論議案バッジ */}
              <div>
                <div className="flex items-center justify-between w-full mb-1">
                  <span className="text-xs font-bold text-slate-800 group-hover:text-indigo-600 transition-colors truncate">
                    {topic.name}
                  </span>
                  {issueCount > 0 ? (
                    <span className="text-[9px] font-black px-1.5 py-0.5 rounded bg-rose-50 text-rose-600 border border-rose-200 shrink-0 flex items-center gap-0.5">
                      <Flame className="w-2.5 h-2.5 fill-rose-500 text-rose-500" />
                      激論議案 {issueCount}
                    </span>
                  ) : (
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-slate-50 text-slate-400 border border-slate-200 shrink-0">
                      合意
                    </span>
                  )}
                </div>
                
                <div className="flex items-end justify-between mt-1">
                  <span className="text-lg font-black text-slate-900 group-hover:text-indigo-600 transition-colors">
                    {topic.percentage}<span className="text-[10px] text-slate-400 font-medium ml-0.5">%</span>
                  </span>
                  <span className="text-[10px] text-slate-400 font-medium">{topic.count}質疑</span>
                </div>
                
                <div className="w-full bg-slate-100 h-1 mt-2 rounded-full overflow-hidden">
                  <div className="bg-indigo-500 h-full rounded-full transition-all duration-500" style={{ width: `${topic.percentage}%` }}></div>
                </div>
              </div>

              {/* カード下部：代表トピックのリンク */}
              <div className="mt-3 pt-2.5 border-t border-slate-100 space-y-1">
                {coreTopics.map((ct, idx) => (
                  <div
                    key={idx}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onOpenTopicDetail) onOpenTopicDetail(ct.id);
                    }}
                    className="text-[11px] text-slate-600 hover:text-indigo-600 flex items-center justify-between group/link py-0.5 transition-colors"
                  >
                    <span className="truncate pr-1">• {ct.title}</span>
                    <ArrowRight className="w-3 h-3 text-slate-300 group-hover/link:text-indigo-500 shrink-0 transition-transform group-hover/link:translate-x-0.5" />
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
