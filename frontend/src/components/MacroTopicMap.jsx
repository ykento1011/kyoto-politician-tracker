import React from 'react';
import { PieChart, Flame, Info, ChevronDown } from 'lucide-react';

export default function MacroTopicMap({ topicStats, selectedCategory, onSelectCategory, getIssueCountForCategory }) {
  return (
    <section className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-extrabold text-slate-800 flex items-center">
            <PieChart className="w-4 h-4 mr-1.5 text-indigo-500" />市議会マクロ論戦マップ
          </h3>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
            全5,128スレッドの質疑量と、議決で賛否が分かれた激論議案の分布
          </p>
        </div>
        {selectedCategory && (
          <button 
            onClick={() => onSelectCategory('')}
            className="text-xs font-bold text-indigo-600 hover:underline"
          >
            選択解除
          </button>
        )}
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {topicStats.map(topic => {
          const isSelected = selectedCategory === topic.name;
          const issueCount = getIssueCountForCategory(topic.name);
          return (
            <button 
              key={topic.name} 
              onClick={() => onSelectCategory(topic.name)} 
              className={`flex flex-col p-3 rounded-xl border text-left transition-all ${
                isSelected 
                  ? 'bg-indigo-50 border-indigo-400 shadow-sm ring-2 ring-indigo-500/20' 
                  : 'bg-white border-slate-200 hover:border-indigo-300 hover:shadow-sm'
              }`}
            >
              <div className="flex items-center justify-between w-full mb-1">
                <span className={`text-xs font-bold truncate ${isSelected ? 'text-indigo-800' : 'text-slate-700'}`}>
                  {topic.name}
                </span>
                {issueCount > 0 ? (
                  <span className="text-[9px] font-black px-1.5 py-0.2 rounded bg-rose-50 text-rose-600 border border-rose-200 shrink-0 flex items-center gap-0.5">
                    <Flame className="w-2.5 h-2.5 fill-rose-500 text-rose-500" />
                    激論 {issueCount}
                  </span>
                ) : (
                  <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-slate-50 text-slate-400 border border-slate-200 shrink-0">
                    合意
                  </span>
                )}
              </div>
              
              <div className="flex items-end justify-between mt-1">
                <span className="text-lg font-black text-slate-900">{topic.percentage}<span className="text-[10px] text-slate-400 font-medium ml-0.5">%</span></span>
                <span className="text-[10px] text-slate-400 font-medium">{topic.count}質疑</span>
              </div>
              
              <div className="w-full bg-slate-100 h-1 mt-2 rounded-full overflow-hidden">
                <div className="bg-indigo-400 h-full rounded-full" style={{ width: `${topic.percentage}%` }}></div>
              </div>
            </button>
          );
        })}
      </div>

      <details className="mt-4 group text-xs text-slate-500 bg-slate-50 rounded-lg border border-slate-200/80 p-2.5">
        <summary className="flex items-center gap-1.5 font-bold text-slate-700 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
          <Info className="w-4 h-4 text-indigo-500 shrink-0" /><span>対象データとAI分類の特性について</span>
          <ChevronDown className="w-3.5 h-3.5 ml-auto text-slate-400 group-open:rotate-180 transition-transform" />
        </summary>
        <div className="mt-2.5 pl-1 pt-2 border-t border-slate-200">
          <ul className="list-disc list-inside space-y-1.5 leading-relaxed">
            <li><strong className="text-slate-600">質疑データ:</strong> 現任期（2023年5月〜2026年）の本会議・常任委員会・特別委員会の会議録からAI抽出した実質質疑スレッド</li>
            <li><strong className="text-slate-600">激論議案バッジ:</strong> 全議案中、全会一致とならず各会派の賛成・反対が分かれた議案の件数です。</li>
          </ul>
        </div>
      </details>
    </section>
  );
}