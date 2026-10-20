import React, { useMemo } from 'react';
import { PieChart, Flame, Info, ChevronDown, Sparkles, ArrowRight } from 'lucide-react';

// 8大カテゴリー全網羅・論点マップ
const CATEGORY_TOPICS_MAP = {
  '都市再生・交通インフラ': [
    { id: 'bus_fare_priority', title: '市バス混雑・市民優先価格' },
    { id: 'vacant_house_tax', title: '空き家税・若者定住' },
    { id: 'urban_planning_height_relax', title: '高さ規制緩和・産業用地' }
  ],
  '産業・観光・地域経済': [
    { id: 'accommodation_tax_revision', title: '宿泊税引き上げ・使途拡大' },
    { id: 'overtourism_clean_manners', title: 'オーバーツーリズム・散乱ごみ' },
    { id: 'traditional_industry_succession', title: '伝統産業・事業承継' }
  ],
  '子育て・教育': [
    { id: 'school_lunch_free', title: '全員制中学校給食・無償化' },
    { id: 'children_medical_subsidy', title: '子ども医療費助成の拡充' },
    { id: 'teacher_workload_ict', title: '教員の多忙化・学校ICT' }
  ],
  '福祉・医療・健康': [
    { id: 'senior_bus_pass_reform', title: '敬老乗車証・制度見直し' },
    { id: 'national_health_insurance_burden', title: '国保料・介護保険料の軽減' },
    { id: 'vaccine_public_subsidy', title: '帯状疱疹ワクチン公費助成' }
  ],
  '財政・行革': [
    { id: 'fiscal_reform_reconstruction', title: '行財政改革・財政健全化' },
    { id: 'council_reform_transparency', title: '議員定数・政務活動費公開' },
    { id: 'public_facility_management_privatization', title: '公共施設包括管理・資産売却' }
  ],
  'くらし・環境・エネルギー': [
    { id: 'waste_charging_recycling', title: '指定ごみ袋・プラ資源循環' },
    { id: 'water_tariff_earthquake_pipe', title: '水道料金改定・管路耐震化' },
    { id: 'decarbonization_solar_obligation', title: '脱炭素・太陽光パネル義務化' }
  ],
  '防災・減災・治安': [
    { id: 'wooden_houses_earthquake_retrofitting', title: '木密・京町家耐震・路地防災' },
    { id: 'flood_control_urban_inundation', title: '鴨川・桂川水系の内水氾濫対策' }
  ],
  '文化・景観・歴史': [
    { id: 'culture_agency_relocation_impact', title: '文化庁移転の波及効果創出' },
    { id: 'townscape_wire_undergrounding', title: '歴史的景観・無電柱化' }
  ]
};

export default function MacroTopicMap({
  topicStats,
  selectedCategory,
  onSelectCategory,
  getIssueCountForCategory,
  onOpenTopicDetail
}) {
  const totalThreadsCount = useMemo(() => {
    return topicStats.reduce((sum, t) => sum + (t.count || 0), 0);
  }, [topicStats]);

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
        {selectedCategory && (
          <button 
            onClick={() => onSelectCategory('')}
            className="text-xs font-bold text-indigo-600 hover:underline cursor-pointer"
          >
            選択解除
          </button>
        )}
      </div>
      
      {/* 8大カテゴリーのグリッド */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
        {topicStats.map(topic => {
          const isSelected = selectedCategory === topic.name;
          const issueCount = getIssueCountForCategory(topic.name);
          const coreTopics = CATEGORY_TOPICS_MAP[topic.name] || [];

          return (
            <div 
              key={topic.name} 
              className={`flex flex-col justify-between p-3.5 rounded-xl border transition-all ${
                isSelected 
                  ? 'bg-indigo-50/50 border-indigo-400 shadow-sm ring-2 ring-indigo-500/20' 
                  : 'bg-white border-slate-200 hover:border-slate-300 hover:shadow-xs'
              }`}
            >
              {/* カード上部：カテゴリ名と激論バッジ */}
              <div 
                onClick={() => onSelectCategory(topic.name)} 
                className="cursor-pointer"
              >
                <div className="flex items-center justify-between w-full mb-1">
                  <span className={`text-xs font-bold truncate ${isSelected ? 'text-indigo-800' : 'text-slate-800'}`}>
                    {topic.name}
                  </span>
                  {issueCount > 0 ? (
                    <span className="text-[9px] font-black px-1.5 py-0.5 rounded bg-rose-50 text-rose-600 border border-rose-200 shrink-0 flex items-center gap-0.5">
                      <Flame className="w-2.5 h-2.5 fill-rose-500 text-rose-500" />
                      激論 {issueCount}
                    </span>
                  ) : (
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-slate-50 text-slate-400 border border-slate-200 shrink-0">
                      合意
                    </span>
                  )}
                </div>
                
                <div className="flex items-end justify-between mt-1">
                  <span className="text-lg font-black text-slate-900">
                    {topic.percentage}<span className="text-[10px] text-slate-400 font-medium ml-0.5">%</span>
                  </span>
                  <span className="text-[10px] text-slate-400 font-medium">{topic.count}質疑</span>
                </div>
                
                <div className="w-full bg-slate-100 h-1 mt-2 rounded-full overflow-hidden">
                  <div className="bg-indigo-500 h-full rounded-full transition-all duration-500" style={{ width: `${topic.percentage}%` }}></div>
                </div>
              </div>

              {/* カード下部：注目の重要論点詳細ページへの直通バッジ */}
              {coreTopics.length > 0 && onOpenTopicDetail && (
                <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-col gap-1.5">
                  <span className="text-[9px] font-black text-indigo-900/60 uppercase tracking-wider flex items-center gap-1">
                    <Sparkles className="w-2.5 h-2.5 text-indigo-500" /> 注目の政策タイムライン
                  </span>
                  {coreTopics.map(ct => (
                    <button
                      key={ct.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpenTopicDetail(ct.id);
                      }}
                      className="text-left text-[11px] font-bold text-slate-700 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50/80 px-2 py-1 rounded-md border border-slate-200 hover:border-indigo-200 transition-colors flex items-center justify-between group/btn cursor-pointer"
                    >
                      <span className="truncate">{ct.title}</span>
                      <ArrowRight className="w-3 h-3 text-slate-400 group-hover/btn:text-indigo-600 shrink-0 ml-1" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <details className="text-xs text-slate-500 bg-slate-50 rounded-lg border border-slate-200/80 p-2.5 group">
        <summary className="flex items-center gap-1.5 font-bold text-slate-700 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
          <Info className="w-4 h-4 text-indigo-500 shrink-0" />
          <span>対象データとAI分類の特性について</span>
          <ChevronDown className="w-3.5 h-3.5 ml-auto text-slate-400 group-open:rotate-180 transition-transform" />
        </summary>
        <div className="mt-2.5 pl-1 pt-2 border-t border-slate-200">
          <ul className="list-disc list-inside space-y-1.5 leading-relaxed">
            <li><strong className="text-slate-600">質疑データ:</strong> 現任期（2023年5月〜2026年）の本会議・常任委員会・特別委員会の会議録からAI抽出した実質質疑スレッド</li>
            <li><strong className="text-slate-600">激論議案バッジ:</strong> 全議案中、全会一致とならず各会派の賛成・反対が分かれた議案の件数です。</li>
            <li><strong className="text-slate-600">政策タイムライン:</strong> 8大カテゴリーの主要争点について、年度・会期をまたぐ議論の変遷と公式原本リンクをAIが構造化しています。</li>
          </ul>
        </div>
      </details>
    </section>
  );
}