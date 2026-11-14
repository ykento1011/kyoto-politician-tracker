import React from 'react';
import { ExternalLink, Landmark } from 'lucide-react';
import ReportIssueButton from './ReportIssueButton';

const RELATIONS = {
  direct: { label: '直接確認', title: '直接対応を確認した予算', style: 'bg-emerald-50 text-emerald-800' },
  contextual: { label: '文脈上の関連', title: '関連予算（参考）', style: 'bg-indigo-50 text-indigo-800' },
  unconfirmed: { label: '未確認', title: '対応関係が未確認の予算', style: 'bg-slate-100 text-slate-700' },
};

export function hasBudgetEvidence(records = []) {
  return Array.isArray(records) && records.some(record => record && Object.hasOwn(record, 'policy_relation'));
}

export function budgetSourceLabel(url = '') {
  const path = url.split(/[?#]/)[0].toLowerCase();
  if (path.endsWith('.pdf')) return '公式資料（PDF）を確認';
  if (/\.html?$/.test(path)) return '公式資料（HTML）を確認';
  return '公式資料を確認';
}

export default function BudgetEvidence({ records, pledge, mayorInfo }) {
  return (
    <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-100">
      <div className="font-bold text-slate-700 flex items-center gap-1.5 mb-3">
        <Landmark className="w-3.5 h-3.5 text-amber-600" />
        ③ 予算資料（確認状況）
      </div>
      <p className="text-[11px] text-slate-600 mb-3">
        予算資料の確認と、議決成立・事業の実施・達成の確認は別です。
      </p>
      <div className="space-y-4">
        {records.map((record, index) => {
          const relation = Object.hasOwn(RELATIONS, record.policy_relation) ? RELATIONS[record.policy_relation] : RELATIONS.unconfirmed;
          return (
            <section key={(record.doc_url || 'budget') + '-' + index} className="bg-white rounded-lg border border-slate-200 p-3" data-budget-relation={Object.hasOwn(RELATIONS, record.policy_relation) ? record.policy_relation : 'unconfirmed'}>
              <span className={'inline-block text-[10px] font-bold px-2 py-0.5 rounded ' + relation.style}>{relation.label}</span>
              <h3 className="text-xs font-bold text-slate-900 mt-2">{relation.title}</h3>
              <p className="text-[11px] text-slate-600 mt-1">{record.fiscal_year}</p>
              <p className="text-xs text-slate-800 mt-2">{record.project_name}</p>
              <p className="text-lg font-black text-slate-900 mt-2">{record.amount_display}</p>
              {record.budget_note && <p className="text-[11px] text-slate-600 leading-relaxed mt-2">{record.budget_note}</p>}
              {record.funding_verification_status === 'verified' && record.funding_sources?.length > 0 && (
                <div className="text-[11px] text-slate-600 mt-2">
                  財源内訳：
                  {record.funding_sources.map((source, i) => <span key={i} className="block">{source.label}：{source.amount}</span>)}
                </div>
              )}
              <div className="border-t border-slate-100 mt-3 pt-2">
                <p className="text-[10px] text-slate-500 leading-relaxed">{record.doc_source}</p>
                {record.doc_url && (
                  <div className="flex items-center justify-between gap-2 mt-2">
                    <a href={record.is_broken ? '#' : record.doc_url} target="_blank" rel="noopener noreferrer"
                      aria-disabled={record.is_broken || undefined}
                      onClick={event => record.is_broken && event.preventDefault()}
                      className={'text-[11px] inline-flex items-center gap-1 font-bold ' + (record.is_broken ? 'text-slate-400 cursor-not-allowed' : 'text-amber-700 hover:underline')}>
                      {record.is_broken ? 'サイト改編のため追跡中' : budgetSourceLabel(record.doc_url)}
                      {!record.is_broken && <ExternalLink className="w-3 h-3" />}
                    </a>
                    <ReportIssueButton targetUrl={record.doc_url} speaker={mayorInfo?.name}
                      docTitle={pledge.headline + '（' + (record.doc_source || '予算資料') + '）'}
                      targetId={'pledge_' + (pledge.pledge_id || pledge.id || pledge.headline) + '_budget_' + index}
                      municipality={mayorInfo?.city_label || ''} />
                  </div>
                )}
              </div>
            </section>
          );
        })}
      </div>
      {records.some(record => record.policy_relation !== 'direct') && (
        <p className="text-[11px] text-slate-600 mt-3">参考・未確認の予算は、直接対応を確認した予算額には合算していません。</p>
      )}
    </div>
  );
}
