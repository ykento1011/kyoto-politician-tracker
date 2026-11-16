import React, {useEffect, useRef, useState} from 'react';
import BudgetEvidence from './BudgetEvidence';
import ProgressEvidence from './ProgressEvidence';
import PolicyEvidenceHold, {hasProgressReview} from './PolicyEvidenceHold';
import ReportIssueButton from './ReportIssueButton';
import {officialKyotoUrl, policyPresentation, policyRouteHref, readPolicyRoute, sourceMedia} from './kyotoPolicyPresentation';
import './KyotoPolicyTracker.css';

function SourceLink({url, children, primary = false, broken = false}) {
  const safe = !broken && officialKyotoUrl(url);
  if (!safe) return <p className="kp-muted">原典未確認（登録出典は追跡中）</p>;
  return <a className={'kp-button' + (primary ? ' kp-primary' : '')} href={safe}
    target="_blank" rel="noopener noreferrer">
    {children} · {sourceMedia(safe)} <span aria-hidden="true">↗</span><span className="sr-only">（新しいタブ）</span>
  </a>;
}

function PolicyIntro({pledge, detail = false}) {
  const view = policyPresentation(pledge);
  const Heading = detail ? 'h1' : 'h2';
  return <>
    <p className="kp-muted">{pledge.id}</p>
    <Heading>{view.title}</Heading>
    <p className="kp-status">{view.status}</p>
    <p className="kp-warning" data-important-uncertainty>{view.warning}</p>
    {detail && view.source && <SourceLink primary url={view.source.url}>{view.source.label}</SourceLink>}
  </>;
}

function RegisteredHistory({pledge: p}) {
  return <>
    {hasProgressReview(p) && <PolicyEvidenceHold pledge={p} headingLevel={3} />}
    {p.progress_evidence?.status === 'hold' && <p data-progress-held>
      登録上の到達段階は根拠確認中のため、確定した進捗として表示していません。
    </p>}
    <details>
      <summary>{p.latest_update ? '過去の契約・実施記録' : '過去の登録段階・議案・実績'}</summary>
      <p>これまでの到達段階（登録情報）：{p.stage_level}／{p.stage_label}</p>
      <p>以下は元の登録内容です。未確認・保留の記録を、議決成立や現在の実施状況の認定には使いません。</p>
      {p.legislative_bill && <div className="kp-source">
        <h3>登録議案</h3>
        <p>{p.legislative_bill.session_name}／{p.legislative_bill.bill_number}</p>
        <p>{p.legislative_bill.bill_title}</p>
        <p>元登録の結果：{p.legislative_bill.result || '記載なし'}（原典の同一性・確認状態を優先）</p>
        {p.legislative_bill.verification_note && <p>{p.legislative_bill.verification_note}</p>}
        {Object.entries(p.legislative_bill.party_votes || {}).map(([name,vote]) => <p key={name}>元登録：{name}／{vote}</p>)}
        {p.legislative_bill.doc_url && <SourceLink url={p.legislative_bill.doc_url}>登録議案の出典（対応関係は確認中）</SourceLink>}
      </div>}
      {p.milestone && <div className="kp-source">
        <h3>{p.milestone.policy_relation === 'contextual' ? '関連する別施策の旧登録' : '登録された過去の記録'}</h3>
        <p>{p.milestone.date}：{p.milestone.title}</p>
        {p.milestone.verification_note && <p>{p.milestone.verification_note}</p>}
        <SourceLink url={p.milestone.evidence_url} broken={p.milestone.is_broken}>登録実績の出典（現在の実施認定とは別）</SourceLink>
        {p.milestone.is_broken && p.milestone.evidence_url && <p>追跡中の登録URL：{p.milestone.evidence_url}</p>}
      </div>}
    </details>
  </>;
}

function SourceWithReport({url, title, broken, pledge, mayor}) {
  return <div className="kp-source">
    <SourceLink url={url} broken={broken}>{title}</SourceLink>
    {broken && url && <p>追跡中の登録URL：{url}</p>}
    <ReportIssueButton targetUrl={url} docTitle={`${pledge.headline}（${title}）`}
      targetId={`${pledge.id}_${title}`} speaker={mayor?.name} municipality="京都市" />
  </div>;
}

export function KyotoPolicyDetail({pledge: p, mayorInfo}) {
  return <>
    <section className="kp-card" aria-label={`${p.id} 現況`}><PolicyIntro pledge={p} detail /></section>
    <details><summary>元の公約名・分野</summary><p>{p.headline}</p><p>{p.category}</p></details>
    <nav className="kp-links kp-navigation" aria-label="詳細内の移動">
      <a className="kp-button" href="#policy-budget">予算</a>
      <a className="kp-button" href="#policy-history">議決・関連施策・履歴</a>
      <a className="kp-button" href="#policy-sources">出典・確認履歴</a>
    </nav>
    <section className="kp-block kp-evidence" id="policy-budget" aria-labelledby="budget-heading">
      <h2 id="budget-heading">予算資料</h2>
      <BudgetEvidence records={p.budget_records || []} pledge={p} mayorInfo={mayorInfo} compactNotes />
      {!p.budget_records?.length && <p>登録された予算資料はありません。予算がないことを示すものではありません。</p>}
      {p.id === 'P-01' && policyPresentation(p).source && <div className="kp-source">
        <SourceLink url={policyPresentation(p).source.url}>準備・参考予算の原文（印刷p.21／PDF物理22）</SourceLink>
        <SourceLink url={policyPresentation(p).source.url.replace('#page=22','#page=32')}>内訳（印刷p.31／PDF物理32）</SourceLink>
      </div>}
    </section>
    <section className="kp-block kp-evidence" id="policy-history" aria-labelledby="history-heading">
      <h2 id="history-heading">議決・関連する別施策・過去履歴</h2>
      <ProgressEvidence event={p.latest_update} headingLevel={3} />
      {p.progress_evidence && <p data-progress-review={p.progress_evidence.status}>{p.progress_evidence.summary}</p>}
      <RegisteredHistory pledge={p} />
    </section>
    <section className="kp-block kp-evidence" id="policy-sources" aria-labelledby="sources-heading">
      <h2 id="sources-heading">出典・確認履歴</h2>
      <p>公約・計画の記載は、条例成立や制度実施の証拠とは区別します。各資料の用途・年度・確認状態をご確認ください。</p>
      <details><summary>公約の全文・計画資料・確認情報</summary>
        <h3>公約原文</h3>
        <p>{p.election_promise?.source_name}</p>
        {p.election_promise?.quote && <blockquote>{p.election_promise.quote}</blockquote>}
        <SourceWithReport url={p.election_promise?.bulletin_url} title="公約の原文" broken={p.election_promise?.is_broken} pledge={p} mayor={mayorInfo} />
        <h3>登録された公式計画</h3>
        <p>{p.official_plan?.date} {p.official_plan?.plan_name}</p>
        <p>{p.official_plan?.summary}</p>
        <SourceWithReport url={p.official_plan?.doc_url} title="登録計画の原文（政策対応の確認状態は別）" broken={p.official_plan?.is_broken} pledge={p} mayor={mayorInfo} />
        {(p.budget_records || []).map((r,i)=><div className="kp-source" key={i}><p>登録予算資料：{r.doc_source}</p><p>{r.department}</p><p>登録URL：{r.doc_url}</p></div>)}
        <p>未入力の確認日時や確認者は補完しません。原本と取得履歴は既存の監査記録に保持しています。</p>
      </details>
      {p.debate_statements?.length > 0 && <details><summary>登録された市長答弁・公式議事録</summary>
        {p.debate_statements.map((stmt,index)=><div key={index} className="kp-source">
          <h3>{stmt.speaker}</h3><p>{stmt.date}／{stmt.session_name}</p><blockquote>{stmt.quote_summary}</blockquote>
          <SourceLink url={stmt.official_url || stmt.url}>登録答弁の原典</SourceLink>
        </div>)}
      </details>}
    </section>
  </>;
}

export function KyotoPolicyTotals({data}) {
  const stats = data.summary_stats || {};
  return <>
    <h1>登録情報の集計・算定方法</h1>
    <p className="kp-warning">公約達成率や、確認済みの単年度予算総額ではありません。</p>
    {(data.kpis || []).map((kpi,i)=><section className="kp-block" key={i}>
      <h2>{kpi.label}（元の登録指標）</h2><p className="kp-value">{kpi.value}</p><p>{kpi.subtext}</p>
      {kpi.badge && <p>元の補助表示：{kpi.badge}</p>}
      {kpi.evidence_note && <p className="kp-warning" data-kpi-evidence-note>{kpi.evidence_note}</p>}
    </section>)}
    <section className="kp-block"><h2>算定方法と限界</h2>
      <p>件数・割合は従来の登録stage_levelに基づく参考値です。予算措置以上の登録件数÷登録政策数を小数第1位で表示しています。議案同一性の未確認項目を含み、確定済み件数・公約達成率ではありません。</p>
      <ul className="kp-stage-list">{Object.entries(stats.stages || {}).map(([key,value]) => <li key={key}>{({enacted:'成立段階',bill_submitted:'議案提出',budgeted:'予算化',official_plan_only:'公式計画のみ',reviewing:'検討中'})[key] || key}：{value}件（旧登録）</li>)}</ul>
      <p>登録政策数：{stats.total_pledges}件</p>
      <p>関連予算集計の元値：{stats.total_allocated_budget_raw?.toLocaleString('ja-JP')}円／表示：{stats.total_allocated_budget_jpy}</p>
      <p data-budget-total-note>{stats.budget_total_note}</p>
      <p>複数年度を含み、確認区分未付与の従来登録額48億8,215万8,000円を含みます。全額が原典認証済みの総額ではなく、令和8年度の確定予算・決算・実際の支出額ではありません。</p>
      <p>宿泊税の登録見込：{stats.accommodation_tax_revenue_jpy}／財源規律の登録値：{stats.debt_repayment_jpy}</p>
    </section>
    <section className="kp-block kp-evidence"><h2>市長・公約の出典と表示の見方</h2>
      <p>{data.mayor_info?.name}／{data.mayor_info?.title}／{data.mayor_info?.party}／{data.mayor_info?.term}</p>
      <SourceLink url={data.mayor_info?.bulletin_pdf}>{data.mayor_info?.bulletin_label || '市長公約の原文'}</SourceLink>
      <SourceLink url={data.mayor_info?.strategy_main_pdf}>{data.mayor_info?.strategy_main_label || '登録された基本構想'}</SourceLink>
      <p>直接確認・文脈上の関連・未確認を区別します。参考・未確認額を直接額へ合算しません。旧登録の表示は、新たな原典認証を意味しません。</p>
      <p>外部原典は新しいタブで開きます。リンク先の応答やPDFのページ移動は閲覧環境によって異なります。</p>
    </section>
  </>;
}

// URL state supports sharing/reloading. History entries retain the originating
// list position and focused card without changing application-wide routing.
export default function KyotoPolicyTracker({data, onBack, initialSearch}) {
  const [route,setRoute] = useState(()=>readPolicyRoute(initialSearch ?? (typeof window === 'undefined' ? '' : window.location.search)));
  const [revision,setRevision] = useState(0);
  const restore = useRef(null);
  const heading = useRef(null);
  useEffect(()=>{
    // Closed native details are omitted by print-to-PDF. Expand only this
    // tracker during printing, then restore the exact screen disclosure state.
    let saved = null;
    const beforePrint = ()=>{
      if (saved) return;
      saved = [...(heading.current?.querySelectorAll('details') || [])].map(node=>[node,node.open]);
      saved.forEach(([node])=>{node.open=true;});
    };
    const afterPrint = ()=>{
      saved?.forEach(([node,open])=>{node.open=open;});
      saved=null;
    };
    window.addEventListener('beforeprint',beforePrint);
    window.addEventListener('afterprint',afterPrint);
    return ()=>{
      window.removeEventListener('beforeprint',beforePrint);
      window.removeEventListener('afterprint',afterPrint);
      afterPrint();
    };
  },[]);
  useEffect(()=>{
    const onPop = ()=>{
      restore.current = window.history.state?.kyotoPolicyList || {scrollY:0};
      setRoute(readPolicyRoute(window.location.search)); setRevision(n=>n+1);
    };
    window.addEventListener('popstate',onPop);
    return ()=>window.removeEventListener('popstate',onPop);
  },[]);
  useEffect(()=>{
    if (!restore.current) return;
    const saved = restore.current;
    const frame = requestAnimationFrame(()=>{
      if (route.policy || route.section) heading.current?.focus({preventScroll:true});
      else if(saved.focusId) document.getElementById(saved.focusId)?.focus({preventScroll:true});
      else heading.current?.focus({preventScroll:true});
      window.scrollTo(0, saved.scrollY || 0); restore.current=null;
    });
    return ()=>cancelAnimationFrame(frame);
  },[route.policy, route.section, revision]);
  const search = typeof window === 'undefined' ? (initialSearch || '') : window.location.search;
  const href = next=>policyRouteHref({...route,...next}, search);
  const navigate = (event,next,focusId)=>{
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    window.history.replaceState({...window.history.state,kyotoPolicyList:{scrollY:window.scrollY,focusId}},'');
    window.history.pushState({...window.history.state,kyotoPolicyFromList:true,kyotoPolicyList:null},'',href(next));
    restore.current={scrollY:0}; setRoute({...route,...next}); setRevision(n=>n+1);
  };
  const back = event=>{
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if(window.history.state?.kyotoPolicyFromList) window.history.back();
    else {
      window.history.replaceState({...window.history.state,kyotoPolicyFromList:false},'',href({policy:'',section:''}));
      restore.current={scrollY:0};setRoute({...route,policy:'',section:''});setRevision(n=>n+1);
    }
  };
  const filter = next=>{
    const updated={...route,...next};setRoute(updated);
    window.history.replaceState({...window.history.state,kyotoPolicyList:null},'',policyRouteHref(updated,window.location.search));
  };
  const pledges=data.pledges || [];
  const selected=pledges.find(p=>p.id===route.policy);
  const detail=Boolean(route.policy || route.section);
  const categories=[...new Set(pledges.map(p=>p.category).filter(Boolean))];
  const filtered=pledges.filter(p=>(route.category==='ALL'||p.category===route.category) &&
    [p.headline,p.id,p.election_promise?.quote,p.official_plan?.plan_name].some(t=>(t||'').toLowerCase().includes(route.query.toLowerCase())));
  return <div className="kyoto-policy-ui">
    <a className="kp-skip" href="#kyoto-policy-content">政策の本文へ</a>
    <main className={'kp-shell'+(detail?' kp-detail':'')} id="kyoto-policy-content" tabIndex={-1} ref={heading}>
      {detail ? <>
        <a className="kp-button kp-navigation" href={href({policy:'',section:''})} onClick={back}>← 政策一覧へ</a>
        {route.section==='summary' ? <KyotoPolicyTotals data={data}/> : selected
          ? <KyotoPolicyDetail pledge={selected} mayorInfo={data.mayor_info}/>
          : <div className="kp-block"><h1>政策が見つかりません</h1><p>政策一覧から選び直してください。</p></div>}
        <a className="kp-button kp-navigation" href={href({policy:'',section:''})} onClick={back}>← 政策一覧へ</a>
      </> : <>
        <button className="kp-home kp-navigation" onClick={onBack}>← トップへ戻る</button>
        <header className="kp-header"><h1>京都市長政策</h1><p>公式資料から政策の現在地を確認できます。</p><p className="kp-muted">{data.mayor_info?.name} 市長 ／ 掲載 {pledges.length}件</p></header>
        <div className="kp-toolbar">
          <div className="kp-field"><label htmlFor="policy-query">政策名で探す</label><input id="policy-query" type="search" value={route.query} onChange={e=>filter({query:e.target.value})} placeholder="公約名・施策を検索" /></div>
          <div className="kp-field"><label htmlFor="policy-category">分野</label><select id="policy-category" value={route.category} onChange={e=>filter({category:e.target.value})}>
            <option value="ALL">すべての分野</option>{categories.map(cat=><option key={cat}>{cat}</option>)}
          </select></div>
          <a id="policy-totals-link" className="kp-button" href={href({section:'summary',policy:''})} onClick={e=>navigate(e,{section:'summary',policy:''},'policy-totals-link')}>集計・算定方法を見る</a>
        </div>
        <p role="status" aria-live="polite">{filtered.length}件を表示</p>
        <div className="kp-grid" data-policy-list>{filtered.map(p=>{
          const view=policyPresentation(p);const id=`policy-open-${p.id}`;
          return <article className="kp-card" key={p.id} data-policy-card={p.id} aria-label={`${p.id} ${view.title}`}>
            <PolicyIntro pledge={p}/>
            <div className="kp-actions">
              {view.source ? <SourceLink primary url={view.source.url}>{view.source.label}</SourceLink> : <p className="kp-muted">原典未確認</p>}
              <a className="kp-button" id={id} href={href({policy:p.id,section:''})} onClick={e=>navigate(e,{policy:p.id,section:''},id)} aria-label={`${p.id} 根拠・履歴`}>根拠・履歴</a>
            </div>
          </article>;
        })}</div>
        {filtered.length===0 && <p className="kp-block">条件に一致する政策はありません。検索語や分野を変更してください。</p>}
      </>}
    </main>
  </div>;
}
