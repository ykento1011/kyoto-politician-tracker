import React from 'react';
import BudgetEvidence from './BudgetEvidence';
import ReportIssueButton from './ReportIssueButton';

export function GenericPolicyGuide({cityName}) {
  return <div className="kp-explanation"><h1>このトラッカーの見方・作り方</h1>
    <p>これは公約達成率でも市長への評価でもなく、公式資料から確認できる政策プロセスの案内です。</p>
    <section className="kp-block"><h2>公約と資料を分けて読む</h2><p>{cityName}の登録公約を掲載しています。全資料の照合が完了しているわけではありません。URLの登録・原本の保存・原文の確認・政策との対応・公開の承認は別々です。</p></section>
    <section className="kp-block"><h2>5段階と確認状態</h2><p>公約表明、市公式確定計画、予算措置、条例提出・可決、成立・執行の5段階です。破線は根拠確認中で、登録された段階まで全部確認済みという意味ではありません。条例が不要な制度に議案が必要と決め付けません。</p><p>資料確認済みは資料の範囲だけの確認です。保留・停止中・未確認は、未実施や未達成とは区別します。</p></section>
    <section className="kp-block"><h2>予算と公開情報</h2><p>予算案・議決済み予算・実際の支出は別です。直接対応・関連参考・未確認を区別し、重複や異なる年度を足して公約総額としません。登録された集計値と履歴は元データに保持していますが、認証済み総額や達成率とは表示しません。</p></section>
    <section className="kp-block"><h2>更新・訂正</h2><p>自動取得や全件照合の完了を保証する画面ではありません。「出典・確認履歴」で資料の用途と未確認事項を確認し、不備は旗ボタンから報告できます。外部応答・PDFページ遷移は未検証です。</p><p>AIは入口。判断するのは市民です。</p></section>
  </div>;
}

export default function GenericPolicyDetail({pledge:p,mayorInfo,adapter,Progress,Source}) {
  const view=adapter.presentation(p);
  const records=(p.budget_records || []).map(r=>({...r,
    // Conservative display projection; the registered records remain untouched.
    policy_relation:r.evidence_status==='source_checked' ? r.policy_relation : 'unconfirmed',
    funding_verification_status:r.funding_verification_status==='verified' ? 'verified' : 'unverified',
    doc_url:!r.is_broken ? adapter.officialUrl(r.doc_url) || undefined : undefined}));
  const sources=[['公約の原文',p.election_promise?.bulletin_url,p.election_promise?.is_broken],
    ['登録計画（政策対応は確認中）',p.official_plan?.doc_url,p.official_plan?.is_broken],
    ['過去の登録議案（同一性・議決は未確認）',p.legislative_bill?.doc_url,p.legislative_bill?.is_broken],
    ['登録実績（現在の実施認定とは別）',p.milestone?.evidence_url,p.milestone?.is_broken],
    ...(p.budget_records || []).map(r=>[r.doc_source || '登録予算資料',r.doc_url,r.is_broken])];
  return <>
    <section className="kp-card"><p className="kp-muted">{p.id}</p><h1>{view.title}</h1><p className="kp-status">{view.status}</p><p className="kp-warning">{view.warning}</p><Progress pledge={p}/>{view.source && <Source primary url={view.source.url}>{view.source.label}</Source>}</section>
    <section className="kp-block"><h2>5段階の意味と確認状況</h2><p>前段階の確認や達成を推測しません。制度に条例が必要かも個別に確認します。</p><Progress pledge={p} expanded/></section>
    <section className="kp-block kp-evidence" id="policy-budget"><h2>予算資料</h2><p>登録額を保持しています。確認区分のない額は原典との対応を確認中です。未確認を0円には置き換えません。</p>
      {records.length ? <BudgetEvidence records={records} pledge={p} mayorInfo={mayorInfo} compactNotes/> : <p>予算資料未確認（予算がないことを示しません）。</p>}
    </section>
    <section className="kp-block" id="policy-history"><h2>議決・関連施策・過去履歴</h2>
      {p.latest_update && <article className="kp-warning"><h3>最新の登録発表</h3><p>{p.latest_update.announced_at} {p.latest_update.summary}</p><Source url={p.latest_update.source_url}>発表の原文</Source></article>}
      <p>議案番号や過去の登録結果だけで可決・実施を確定しません。確認済みの同一性照合が必要です。</p>
      {p.progress_evidence && <p>{p.progress_evidence.summary}</p>}
      <details><summary>過去の登録記録（未確認情報を含む）</summary><p>登録段階：{p.stage_level}／{p.stage_label}</p>
        {p.legislative_bill && <><h3>登録議案</h3><p>{p.legislative_bill.session_name}／{p.legislative_bill.bill_number}／{p.legislative_bill.bill_title}</p><p>元の登録結果：{p.legislative_bill.result || '記載なし'}（可決の認定ではありません）</p></>}
        {p.milestone && <><h3>関連施策を含む登録記録</h3><p>{p.milestone.date} {p.milestone.title}</p><p>{p.milestone.verification_note}</p></>}
      </details>
    </section>
    <section className="kp-block" id="policy-sources"><h2>出典・確認履歴</h2><h3>公約原文</h3><blockquote>{p.election_promise?.quote || '公約原文未確認'}</blockquote>
      <details><summary>登録計画・資料・確認情報</summary><p>{p.official_plan?.date} {p.official_plan?.plan_name}</p><p>以下は登録時の説明です。政策との対応や実施を確認したものとは限りません。</p><p>{p.official_plan?.summary}</p>
        <p>{p.election_promise?.note}</p>
        {sources.map(([title,url,broken],i)=><div className="kp-source" key={i}><p>{title}</p><Source url={url} broken={broken}>{title}</Source>
          {url && <p className="kp-muted">登録URL：{url}</p>}
          {adapter.officialUrl(url) && <ReportIssueButton targetUrl={url} targetId={`${adapter.cityName}:${p.id}:${i}`} municipality={adapter.cityName} speaker={mayorInfo?.name} docTitle={title}/>}
        </div>)}
        <p>確認日時・確認者・取得履歴が公開データにない箇所は補完しません。資料が保存されていることだけで政策との対応を確認済みにはしません。</p>
      </details>
      {p.debate_statements?.length>0 && <details><summary>登録された答弁・出典（政策対応は確認中）</summary>{p.debate_statements.map((s,i)=><div className="kp-source" key={i}><h3>{s.speaker}</h3><p>{s.date} {s.session_name}</p><blockquote>{s.quote_summary}</blockquote><Source url={s.official_url || s.url}>登録答弁の原典</Source></div>)}</details>}
    </section>
  </>;
}
