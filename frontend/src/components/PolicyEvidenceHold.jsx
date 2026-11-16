import React from 'react';

// Opt-in only: historical registrations remain in data, not as confirmed results.
export function hasProgressReview(p) {
  return Boolean(p.progress_evidence || p.legislative_bill?.verification_status ||
    p.milestone?.verification_status || p.milestone?.policy_relation);
}

export default function PolicyEvidenceHold({ pledge: p, headingLevel = 4 }) {
  const Heading = `h${headingLevel}`;
  const Subheading = `h${headingLevel + 1}`;
  const bill = p.legislative_bill;
  const event = p.milestone;
  return <section className="bg-slate-50 rounded-xl p-3.5 border border-slate-200"
    data-policy-evidence="review">
    <Heading className="text-xs font-bold text-slate-800">議決・実績の確認状況</Heading>
    {bill && <div className="mt-2 text-xs" data-legislative-status={bill.verification_status || 'unverified'}>
      <p className="font-bold text-amber-800">議案の同一性は未確認（可決根拠として保留）</p>
      <p className="mt-1">{bill.verification_note}</p>
      <details className="mt-2 text-slate-600">
        <summary>未確認の登録議案</summary>
        <p>{bill.session_name}・{bill.bill_number}</p>
        <p>{bill.bill_title}</p>
      </details>
    </div>}
    {event && <div className="mt-3 text-xs" data-milestone-relation={event.policy_relation || 'unconfirmed'}>
      <Subheading className="font-bold text-slate-800">{event.policy_relation === 'contextual'
        ? '関連する別施策（制度実施の根拠ではありません）' : '未確認の登録実績'}</Subheading>
      <p className="mt-1">{event.verification_note}</p>
      <details className="mt-2 text-slate-600">
        <summary>元の登録内容（未確認）</summary>
        <p>{event.date}：{event.title}</p>
        {event.evidence_url && !event.is_broken &&
          <a href={event.evidence_url} target="_blank" rel="noopener noreferrer"
            className="underline">登録出典（対応関係は未確認）</a>}
        {event.is_broken && <p>登録出典は追跡中</p>}
      </details>
    </div>}
  </section>;
}
