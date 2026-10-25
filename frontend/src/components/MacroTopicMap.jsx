import React, { useMemo } from 'react';
import { PieChart, Flame, ArrowRight } from 'lucide-react';

const KYOTO_CATEGORY_TOPICS = {
  '都市再生・交通インフラ': [
    { id: 'bus_fare_priority', title: '市バス混雑・市民優先価格' },
    { id: 'hokuriku_shinkansen_extension', title: '北陸新幹線延伸・地下水と財政負担' },
    { id: 'vacant_house_tax', title: '空き家税・若者定住' },
    { id: 'urban_planning_height_relax', title: '高さ規制緩和・産業用地' }
  ],
  '産業・観光・地域経済': [
    { id: 'accommodation_tax_revision', title: '宿泊税引き上げ・使途拡大' },
    { id: 'overtourism_clean_manners', title: 'オーバーツーリズム・散乱ごみ' },
    { id: 'traditional_industry_succession', title: '伝統産業・事業承継' },
    { id: 'central_market_redevelopment', title: '中央卸売市場・食肉市場再整備' }
  ],
  '子育て・教育': [
    { id: 'school_lunch_free', title: '全員制中学校給食・無償化' },
    { id: 'children_medical_subsidy', title: '子ども医療費助成の拡充' },
    { id: 'teacher_workload_ict', title: '教員の多忙化・学校ICT' },
    { id: 'nursery_teacher_subsidy_reform', title: '民間保育所独自給与補助見直し' }
  ],
  '福祉・医療・健康': [
    { id: 'senior_bus_pass_reform', title: '敬老乗車証・制度見直し' },
    { id: 'national_health_insurance_burden', title: '国保料・介護保険料の軽減' },
    { id: 'vaccine_public_subsidy', title: '帯状疱疹ワクチン公費助成' },
    { id: 'poverty_hikikomori_support', title: '生活困窮・ひきこもり相談' }
  ],
  '財政・行革': [
    { id: 'fiscal_reform_reconstruction', title: '行財政改革・財政健全化' },
    { id: 'council_reform_transparency', title: '議員定数・政務活動費公開' },
    { id: 'public_facility_management_privatization', title: '公共施設包括管理・資産売却' },
    { id: 'city_hall_reconstruction_cost', title: '市役所新庁舎整備・分庁舎集約' }
  ],
  'くらし・環境・エネルギー': [
    { id: 'waste_charging_recycling', title: '指定ごみ袋・プラ資源循環' },
    { id: 'water_tariff_earthquake_pipe', title: '水道料金改定・管路耐震化' },
    { id: 'decarbonization_solar_obligation', title: '脱炭素・太陽光パネル義務化' },
    { id: 'bike_sharing_illegal_parking', title: '放置自転車対策・シェアサイクル' }
  ],
  '防災・減災・治安': [
    { id: 'wooden_houses_earthquake_retrofitting', title: '木密・京町家耐震・路地防災' },
    { id: 'flood_control_urban_inundation', title: '鴨川・桂川水系の内水氾濫対策' },
    { id: 'landslide_disaster_prevention', title: '土砂災害警戒区域・砂防対策' },
    { id: 'evacuation_center_bed_women', title: '避難所段ボールベッド・女性視点防災' }
  ],
  '文化・景観・歴史': [
    { id: 'culture_agency_relocation_impact', title: '文化庁移転の波及効果創出' },
    { id: 'townscape_wire_undergrounding', title: '歴史的景観・無電柱化' },
    { id: 'world_heritage_buffer_zone', title: '世界遺産バッファーゾーン保全' },
    { id: 'kyoto_arts_univ_sujin_impact', title: '京都芸大崇仁移転・地域活性化' }
  ]
};

const OSAKA_CATEGORY_TOPICS = {
  '財政・行革': [
    { id: 'fukushuto_daitoshi_seido', title: '副首都ビジョン・法定協議会・特別区' }
  ],
  '都市再生・交通インフラ': [
    { id: 'osaka_expo_legacy_yumeshima', title: '夢洲第2期マスタープラン・万博跡地活用' }
  ],
  '産業・観光・地域経済': [
    { id: 'special_minpaku_regulation', title: '特区民泊の立入検査・違法民泊対策' }
  ],
  'くらし・環境・エネルギー': [
    { id: 'street_smoking_ban_spread', title: '市内全域路上喫煙禁止・喫煙所整備' }
  ],
  '子育て・教育': [
    { id: 'school_heatstroke_ssr_support', title: '学校 熱中症・校内SSR拡充' }
  ],
  '福祉・医療・健康': [
    { id: 'kokuho_kaigo_premium_burden', title: '国民健康保険 統一・第9期介護保険料' }
  ],
  '防災・減災・治安': [
    { id: 'sewage_accident_disaster_digital', title: '下水道工事事故・防災デジタル計画' }
  ],
  '文化・景観・歴史': [
    { id: 'traditional_culture_outdoor_ad', title: '上方伝統芸能継承・屋外広告景観' }
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

  const activeCategoryTopicsMap = cityCode === 'osaka' ? OSAKA_CATEGORY_TOPICS : KYOTO_CATEGORY_TOPICS;

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
