import React from 'react';
import { Flame, Check, CheckCircle2, XCircle, ArrowRight, ExternalLink, Sparkles, Scale } from 'lucide-react';

export default function BillsSection({ filteredBills, onlyContestedBills, setOnlyContestedBills, issuesMap, onSelectBill }) {
  return (
    <section className="space-y-6 animate-in fade-in duration-300">
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setOnlyContestedBills(!onlyContestedBills)}
            className={`inline-flex items-center px-3.5 py-2 rounded-xl text-xs font-black transition-all border ${
              onlyContestedBills
                ? 'bg-rose-50 text-rose-700 border-rose-300 shadow-2xs'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            <Flame className={`w-3.5 h-3.5 mr-1.5 ${onlyContestedBills ? 'text-rose-600 fill-rose-500' : 'text-slate-400'}`} />
            賛否が分かれた激論議案のみ
            {onlyContestedBills && <Check className="w-3.5 h-3.5 ml-1 text-rose-600" />}
          </button>
          
          <span className="text-xs font-bold text-slate-400">
            {filteredBills.length} 件表示中
          </span>
        </div>

        <div className="text-[11px] text-slate-400 font-medium">
          ※地方議会の慣例（会派拘束）に基づき会派単位で賛否を集計しています
        </div>
      </div>

      <div className="space-y-4">
        {filteredBills.map((bill, idx) => {
          const issue = issuesMap[`${bill.session_name}_${bill.bill_number}`];
          const votes = bill.votes || {};
          const vValues = Object.values(votes);
          const isContested = vValues.includes('賛成') && vValues.includes('反対');

          return (
            <article key={idx} className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pb-3 border-b border-slate-100">
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-black text-slate-500 bg-slate-100 px-2 py-0.5 rounded font-mono">
                      {bill.session_name} ({bill.bill_number})
                    </span>
                    {isContested ? (
                      <span className="text-[10px] font-black px-2 py-0.5 rounded bg-rose-50 text-rose-600 border border-rose-200 flex items-center gap-1">
                        <Flame className="w-2.5 h-2.5 fill-rose-500 text-rose-500" />激論議案
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-50 text-slate-400 border border-slate-200">
                        全会一致
                      </span>
                    )}
                    {bill.result && (
                      <span className={`text-[10px] font-black px-2 py-0.5 rounded ${
                        bill.result.includes('可決') || bill.result.includes('認定') || bill.result.includes('同意')
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}>
                        結果: {bill.result}
                      </span>
                    )}
                  </div>
                  <h2 className="text-base font-black text-slate-900 leading-snug">
                    {bill.title}
                  </h2>
                </div>

                <div className="flex items-center gap-2 shrink-0 self-start sm:self-auto">
                  <button
                    onClick={() => onSelectBill(bill)}
                    className="text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg border border-indigo-200 transition-all flex items-center gap-1"
                  >
                    <span>全議員の賛否・詳細</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                  {bill.source_url && (
                    <a 
                      href={bill.source_url || (cityCode === "osaka" ? "https://www.city.osaka.lg.jp/shikai/page/0000001592.html" : "https://www.city.kyoto.lg.jp/shikai/")} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="text-[11px] font-bold text-slate-400 hover:text-indigo-600 inline-flex items-center gap-1 bg-slate-50 hover:bg-slate-100 px-2.5 py-1.5 rounded-lg border border-slate-200 transition-colors"
                    >
                      公式 <ExternalLink className="w-3 h-3 opacity-60" />
                    </a>
                  )}
                </div>
              </div>

              {issue && (
                <div className="bg-indigo-50/40 p-4 rounded-xl border border-indigo-100 space-y-3">
                  <div>
                    <div className="flex items-center gap-1.5 text-xs font-black text-indigo-900 mb-1">
                      <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                      対立の核心: {issue.key_conflict}
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">
                      {issue.background}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
                    <div className="bg-emerald-50/70 p-3 rounded-lg border border-emerald-100">
                      <span className="text-[11px] font-black text-emerald-800 block mb-1">賛成派の主な論理</span>
                      <p className="text-slate-700 text-xs leading-relaxed">{issue.agree_logic}</p>
                    </div>
                    <div className="bg-rose-50/70 p-3 rounded-lg border border-rose-100">
                      <span className="text-[11px] font-black text-rose-800 block mb-1">反対派の主な論理</span>
                      <p className="text-slate-700 text-xs leading-relaxed">{issue.disagree_logic}</p>
                    </div>
                  </div>
                </div>
              )}

              {Object.keys(votes).length > 0 && (
                <div className="pt-2 border-t border-slate-100">
                  <span className="text-[10px] font-bold text-slate-400 block mb-2">各会派・無所属の評決態度</span>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                    {Object.entries(votes).map(([grp, v]) => {
                      const isAgree = v === '賛成';
                      return (
                        <div key={grp} className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100 text-xs">
                          <span className="font-bold text-slate-700 truncate mr-2" title={grp}>{grp}</span>
                          <span className={`font-black shrink-0 inline-flex items-center gap-0.5 text-[11px] ${
                            isAgree ? 'text-emerald-600' : 'text-rose-600'
                          }`}>
                            {isAgree ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                            {v}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </article>
          );
        })}

        {filteredBills.length === 0 && (
          <div className="text-center py-24 bg-white rounded-2xl border border-dashed border-slate-300">
            <Scale className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-slate-500 font-bold text-sm">条件に一致する議案が見つかりませんでした。</p>
            <p className="text-slate-400 text-xs mt-1">「賛否が分かれた議案のみ」のチェックを外すか、検索条件を変更してください。</p>
          </div>
        )}
      </div>
    </section>
  );
}