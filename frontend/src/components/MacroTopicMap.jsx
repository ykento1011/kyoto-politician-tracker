import React, { useMemo } from 'react';
import { PieChart, Flame, ArrowRight } from 'lucide-react';

const KYOTO_CATEGORY_TOPICS = {
  "都市再生・交通インフラ": [
    {
      "id": "bus_fare_priority",
      "title": "市バス混雑対策と「市民優先価格（二重運賃）」導入"
    },
    {
      "id": "vacant_house_tax",
      "title": "空き家税（非居住住宅利活用促進税）の施行と若者定住対策"
    },
    {
      "id": "urban_planning_height_relax",
      "title": "都市計画・高さ制限緩和（若者居住・産業用地確保）"
    },
    {
      "id": "hokuriku_shinkansen_extension",
      "title": "北陸新幹線延伸（小浜・京都ルート）の財政負担と地下水・環境影響"
    },
    {
      "id": "subway_tozai_extension_management",
      "title": "地下鉄東西線・烏丸線の経営改善と可動式ホーム柵整備"
    }
  ],
  "産業・観光・地域経済": [
    {
      "id": "accommodation_tax_revision",
      "title": "宿泊税の税率引き上げと使途拡大（市民還元）"
    },
    {
      "id": "overtourism_clean_manners",
      "title": "オーバーツーリズム対策（スマートごみ箱・マナー啓発）"
    },
    {
      "id": "traditional_industry_succession",
      "title": "伝統産業・地域企業の事業承継と担い手育成"
    },
    {
      "id": "central_market_redevelopment",
      "title": "中央卸売市場・食肉市場の施設再整備と活性化"
    }
  ],
  "子育て・教育": [
    {
      "id": "school_lunch_free",
      "title": "全員制中学校給食の導入と給食無償化の財源論争"
    },
    {
      "id": "children_medical_subsidy",
      "title": "子ども医療費助成の対象拡充（通院助成の上限引き上げ）"
    },
    {
      "id": "teacher_workload_ict",
      "title": "教員の多忙化解消・働き方改革と学校ICT・不登校対策"
    },
    {
      "id": "nursery_teacher_subsidy_reform",
      "title": "民間保育施設への京都市独自給与上乗せ補助の見直し"
    }
  ],
  "福祉・医療・健康": [
    {
      "id": "senior_bus_pass_reform",
      "title": "敬老乗車証の制度見直し（自己負担割合・交付基準）"
    },
    {
      "id": "national_health_insurance_burden",
      "title": "国民健康保険料・介護保険料の負担軽減策"
    },
    {
      "id": "vaccine_public_subsidy",
      "title": "帯状疱疹ワクチン等の任意予防接種公費助成"
    },
    {
      "id": "poverty_hikikomori_support",
      "title": "生活困窮者自立支援とひきこもり・ヤングケアラー相談体制"
    }
  ],
  "財政・行革": [
    {
      "id": "fiscal_reform_reconstruction",
      "title": "行財政改革計画と「特別の財政支援」からの完全脱却"
    },
    {
      "id": "council_reform_transparency",
      "title": "議員定数・報酬および政務活動費の透明性向上"
    },
    {
      "id": "public_facility_management_privatization",
      "title": "公共施設等総合管理計画と民間委託・資産売却"
    },
    {
      "id": "city_hall_reconstruction_cost",
      "title": "市役所新庁舎整備事業と分庁舎集約による執務環境適正化"
    }
  ],
  "くらし・環境・エネルギー": [
    {
      "id": "waste_charging_recycling",
      "title": "ごみ処理有料化手数料とプラスチック資源循環"
    },
    {
      "id": "water_tariff_earthquake_pipe",
      "title": "水道料金体系の改定と基幹管路の耐震化更新"
    },
    {
      "id": "decarbonization_solar_obligation",
      "title": "脱炭素都市・建築物太陽光パネル設置義務化の推進"
    },
    {
      "id": "bike_sharing_illegal_parking",
      "title": "放置自転車対策とシェアサイクルポートの全市的展開"
    }
  ],
  "防災・減災・治安": [
    {
      "id": "wooden_houses_earthquake_retrofitting",
      "title": "木造密集市街地・京町家の耐震改修と路地奥防災"
    },
    {
      "id": "flood_control_urban_inundation",
      "title": "鴨川・桂川水系の内水氾濫対策と雨水幹線整備"
    },
    {
      "id": "landslide_disaster_prevention",
      "title": "土砂災害警戒区域の安全対策と急傾斜地崩壊防止事業"
    },
    {
      "id": "evacuation_center_bed_women",
      "title": "避難所における段ボールベッド等の備蓄と女性視点の防災機能"
    }
  ],
  "文化・景観・歴史": [
    {
      "id": "culture_agency_relocation_impact",
      "title": "文化庁京都移転の波及効果創出と文化芸術支援"
    },
    {
      "id": "townscape_wire_undergrounding",
      "title": "歴史的景観の保全・無電柱化と屋外広告物対策"
    },
    {
      "id": "world_heritage_buffer_zone",
      "title": "世界遺産周辺のバッファーゾーン保全と開発の調和"
    },
    {
      "id": "kyoto_arts_univ_sujin_impact",
      "title": "京都市立芸術大学の崇仁移転と地域活性化・アート振興"
    }
  ]
};

const OSAKA_CATEGORY_TOPICS = {
  "財政・行革": [
    {
      "id": "fukushuto_daitoshi_seido",
      "title": "副首都ビジョンと大都市制度（法定協議会・特別区）"
    }
  ],
  "都市再生・交通インフラ": [
    {
      "id": "osaka_expo_legacy_yumeshima",
      "title": "夢洲まちづくり・第2期区域と万博跡地活用"
    }
  ],
  "産業・観光・地域経済": [
    {
      "id": "special_minpaku_regulation",
      "title": "特区民泊の規制強化と違法民泊・住環境対策"
    }
  ],
  "くらし・環境・エネルギー": [
    {
      "id": "street_smoking_ban_spread",
      "title": "市内全域路上喫煙禁止と喫煙所インフラ整備"
    }
  ],
  "子育て・教育": [
    {
      "id": "school_heatstroke_ssr_support",
      "title": "学校熱中症対策・不登校支援（SSR）の全校拡充"
    }
  ],
  "福祉・医療・健康": [
    {
      "id": "kokuho_kaigo_premium_burden",
      "title": "国民健康保険料・介護保険料の負担軽減と適正化"
    }
  ],
  "防災・減災・治安": [
    {
      "id": "bousai_infrastructure_yodogawa",
      "title": "淀川左岸線延伸と高潮・巨大地震津波対策"
    }
  ],
  "文化・景観・歴史": [
    {
      "id": "cultural_heritage_osakajo_naniwagu",
      "title": "大阪城公園・難波宮跡の歴史遺産保全と賑わい創出"
    }
  ]
};

const NAGOYA_CATEGORY_TOPICS = {
  "文化・景観・歴史": [
    {
      "id": "nagoya_castle_wooden_restoration",
      "title": "名古屋城天守閣木造復元事業とバリアフリー設備（エレベーター）設置"
    }
  ],
  "福祉・医療・健康": [
    {
      "id": "keiro_pass_reform",
      "title": "敬老パス制度の持続可能性と利用料・上限額の見直し"
    },
    {
      "id": "nagoya_city_univ_hospitals_dx",
      "title": "名市大附属病院群（東部・西部医療センター等）の機能強化と医療DX"
    }
  ],
  "都市再生・交通インフラ": [
    {
      "id": "yatomi_aioiyama_road",
      "title": "弥富相生山線道路整備事業とヒメボタル生息地保全（折衷案）"
    },
    {
      "id": "meieki_redevelopment_srt",
      "title": "名古屋駅周辺まちづくりと新たな路面公共交通（SRT）導入"
    }
  ],
  "財政・行革": [
    {
      "id": "higashi_ward_office_relocation",
      "title": "東区役所等庁舎の老朽化と移転整備方針（愛知大学車道校舎・建中寺）"
    },
    {
      "id": "nagoya_shiminzei_genzei",
      "title": "市民税減税政策の堅持と財政規律・行財政改革の推進"
    }
  ],
  "産業・観光・地域経済": [
    {
      "id": "premium_gift_certificate",
      "title": "地域経済活性化とプレミアム付商品券事業（電子化・物価高騰対策）"
    },
    {
      "id": "monozukuri_mice_tourism_dmo",
      "title": "中小企業・モノづくり技術継承支援とMICE・DMO観光誘客"
    }
  ],
  "子育て・教育": [
    {
      "id": "school_lunch_free_and_reform",
      "title": "学校給食費無償化と中学校スクールランチ（選択制・全員喫食）の展開"
    },
    {
      "id": "futoukou_freeschool_support",
      "title": "不登校児童生徒への支援（学びの多様化学校・フリースクール助成）"
    }
  ],
  "くらし・環境・エネルギー": [
    {
      "id": "waste_carry_out_prevention_ordinance",
      "title": "家庭廃棄物・資源ごみ持ち去り防止条例の制定と生活困窮者支援"
    },
    {
      "id": "nagoya_heatstroke_climate_action",
      "title": "猛暑・熱中症対策の全庁横断推進と脱炭素・環境学習プラン2030"
    }
  ],
  "防災・減災・治安": [
    {
      "id": "minato_disaster_prevention_center",
      "title": "港防災センター移転改築と南海トラフ地震・避難所対策の強化"
    }
  ]
};



const YOKOHAMA_CATEGORY_TOPICS = {
  "財政・行革": [
    {
      "id": "yokohama_debt_fund_fiscal_pdca",
      "title": "減債基金依存からの脱却と持続可能な財政規律・行革推進"
    },
    {
      "id": "yokohama_internal_control_governance",
      "title": "徴収ミス・時効損失の検証と全庁的な内部統制・ガバナンス強化"
    }
  ],
  "子育て・教育": [
    {
      "id": "yokohama_school_lunch_full",
      "title": "中学校全員給食の円滑実施と食育・安全品質管理の検証"
    },
    {
      "id": "yokohama_special_needs_education_ict",
      "title": "特別支援教育の切れ目ない支援体制と教員ICT・多忙化解消"
    }
  ],
  "くらし・環境・エネルギー": [
    {
      "id": "yokohama_water_works_dx_system",
      "title": "水道料金徴収システムの刷新と上下水道インフラ老朽化対策"
    },
    {
      "id": "yokohama_decarbon_circular_city",
      "title": "2050年脱炭素社会の実現とサーキュラーエコノミー・資源循環"
    }
  ],
  "都市再生・交通インフラ": [
    {
      "id": "yokohama_hilly_public_transport",
      "title": "起伏・坂の多い地形に対応する地域交通の確保と敬老パス維持"
    },
    {
      "id": "yokohama_housing_redevelopment_subcenter",
      "title": "市営住宅・改良住宅の建て替えと郊外住宅団地の再生・まちづくり"
    }
  ],
  "福祉・医療・健康": [
    {
      "id": "yokohama_medical_completion_in_city",
      "title": "病床確保と救急医療・入院医療の「市内完結率」向上"
    },
    {
      "id": "yokohama_cancer_screening_prevention",
      "title": "がん精密検査受診率の向上とがん予防・重症化予防対策"
    }
  ],
  "防災・減災・治安": [
    {
      "id": "yokohama_disaster_shelter_welfare",
      "title": "急傾斜地・がけ地崩落対策と水害リスク・避難所環境整備"
    },
    {
      "id": "yokohama_earthquake_in_home_evacuation",
      "title": "大地震想定の見直しと在宅避難者支援・生活物資供給マネジメント"
    }
  ],
  "産業・観光・地域経済": [
    {
      "id": "yokohama_green_expo_2027",
      "title": "GREEN×EXPO 2027（園芸博）の開催準備と旧上瀬谷通信施設跡地利用"
    },
    {
      "id": "yokohama_urban_agriculture_sme_support",
      "title": "都市農業振興と地元中小企業・商店街の物価高騰・事業承継支援"
    }
  ],
  "文化・景観・歴史": [
    {
      "id": "yokohama_three_zoos_renewal_legacy",
      "title": "野毛山動物園等3園のリニューアル整備と動物福祉・財源多角化"
    },
    {
      "id": "yokohama_culture_arts_waterfront_heritage",
      "title": "歴史的建造物・開港の歴史遺産保全とウォーターフロント文化芸術振興"
    }
  ]
};

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

  const activeCategoryTopicsMap = cityCode === 'nagoya' ? NAGOYA_CATEGORY_TOPICS : cityCode === 'osaka' ? OSAKA_CATEGORY_TOPICS : cityCode === 'yokohama' ? YOKOHAMA_CATEGORY_TOPICS : KYOTO_CATEGORY_TOPICS;

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
