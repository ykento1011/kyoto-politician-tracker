import React, {useEffect, useRef, useState} from 'react';
import BudgetEvidence from './BudgetEvidence';
import ProgressEvidence from './ProgressEvidence';
import PolicyEvidenceHold, {hasProgressReview} from './PolicyEvidenceHold';
import ReportIssueButton from './ReportIssueButton';
import {officialKyotoUrl, policyPresentation, policyDocumentNote, policyProgress, PROGRESS_STATES, policyRouteHref, readPolicyRoute, sourceMedia} from './kyotoPolicyPresentation';
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
    <PolicyProgress pledge={pledge} />
    {detail && view.source && <SourceLink primary url={view.source.url}>{view.source.label}</SourceLink>}
  </>;
}

function MayorProfile({mayor = {}}) {
  const [photo,setPhoto]=useState(mayor.profile_image || mayor.fallback_image);
  useEffect(()=>setPhoto(mayor.profile_image || mayor.fallback_image),[mayor.profile_image,mayor.fallback_image]);
  return <div className="kp-mayor" aria-label="市長プロフィール">
    {photo ? <img src={photo} alt={`${mayor.name || '京都市長'}の顔写真`} width="112" height="112"
      onError={()=>setPhoto(photo!==mayor.fallback_image ? mayor.fallback_image : null)} />
      : <span className="kp-photo-fallback">写真は表示できません</span>}
    <div><p className="kp-muted">{mayor.title}</p><p className="kp-mayor-name">{mayor.name}</p><p>任期：{mayor.term}</p></div>
  </div>;
}

function PolicyProgress({pledge, expanded = false}) {
  const progress=policyProgress(pledge);
  return <div className={'kp-progress'+(expanded?' kp-progress-expanded':'')} data-policy-progress={pledge.id}>
    {!expanded && <p className="kp-reference">根拠を確認している段階：{progress.reference ? `${progress.reference} ${progress.referenceLabel}` : progress.referenceLabel}</p>}
    {!expanded && <ol className="kp-steps" aria-label="5段階の進捗と確認状況">
      {progress.steps.map(step=><li key={step.number} className={`kp-step kp-step-${step.state}`} data-stage={step.number} data-stage-state={step.state}>
        <span className="kp-step-number">{step.number}</span><span className="kp-step-title">{step.label}</span>
        <span className="kp-step-state"><span aria-hidden="true">{PROGRESS_STATES[step.state].symbol} </span>{step.short || PROGRESS_STATES[step.state].compact || PROGRESS_STATES[step.state].label}</span>
      </li>)}
    </ol>}
    {!expanded && <p className="kp-progress-note">◇は資料で確認できた範囲。破線の段階は政策との対応を確認中です。</p>}
    {expanded && <ol className="kp-step-explanations">{progress.steps.map(step=><li key={step.number}>
      <h3>{step.number} {step.label}</h3>
      <p className={`kp-state-tag kp-step-${step.state}`}><span aria-hidden="true">{PROGRESS_STATES[step.state].symbol} </span>{PROGRESS_STATES[step.state].label}{step.short && `：${step.short}`}</p>
      <p>{step.note}</p><p className="kp-muted">段階の意味：{step.meaning}</p>
    </li>)}</ol>}
  </div>;
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
        <h3>{p.milestone.policy_relation === 'contextual' ? '関連する別施策の過去記録' : '登録された過去の記録'}</h3>
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
  const note = policyDocumentNote(p);
  return <>
    <section className="kp-card" aria-label={`${p.id} 現況`}><PolicyIntro pledge={p} detail /></section>
    <section className="kp-block" aria-labelledby="progress-heading"><h2 id="progress-heading">5段階の意味と確認状況</h2>
      <p>資料確認済みは、その資料が示す範囲だけの確認です。前後の段階の達成を推測しません。</p>
      <PolicyProgress pledge={p} expanded />
    </section>
    <details><summary>元の公約名・分野</summary><p>{p.headline}</p><p>{p.category}</p></details>
    <nav className="kp-links kp-navigation" aria-label="詳細内の移動">
      <a className="kp-button" href="#policy-budget">予算</a>
      <a className="kp-button" href="#policy-history">議決・関連施策・履歴</a>
      <a className="kp-button" href="#policy-sources">出典・確認履歴</a>
    </nav>
    <section className="kp-block kp-evidence" id="policy-budget" aria-labelledby="budget-heading">
      <h2 id="budget-heading">予算資料</h2>
      {note && <article className="kp-source" data-source-fact={note.fact_type} aria-labelledby="proposal-fact-heading">
        <h3 id="proposal-fact-heading">{note.submeasure}：予算案で確認できたこと</h3>
        <p>{note.document}に、<strong>{note.amount_display}</strong>の計上案が記載されています。</p>
        {p.id === 'P-03' ? <>
          <p>全員制中学校給食への言及があり、献立の充実・食育・情報発信などの関連施策です。</p>
          <p>7,000万円は事業全体の予算案額であり、給食センター整備の直接予算とは認定していません。既存の予算記録・集計には加算しません。</p>
          <p><strong>予算議決・実施実績は、この原典だけでは未確認です。</strong>③予算措置への到達や公約達成の認定ではありません。</p>
          <p>予算案当時の開始予定は、現在の工事一時停止・開始時期未定を変更する根拠にしていません。</p>
        </> : <>
        <p>対象は認可保育施設を利用する世帯内の第2子以降です。所得や同時入所等の要件を問わない説明になっています。</p>
        <p>必要経費「約13.5億円」は、市が徴収する保育料の収入減約9.3億円と、施設の保育料収入減を市が補填する追加経費約4.2億円の説明です。表頭の4億1,880万円と約13.5億円を別々の予算として足し合わせません。</p>
        <p><strong>令和7年4月からの実施は、予算案作成時点の予定です。</strong>予算成立・実際の施行・利用実績はこの資料だけでは確認できません。③予算措置への到達や公約全体の達成を認定する表示ではありません。</p>
        <p>登録14億円との対応、別年度の私立幼稚園2歳児支援5,900万円との対応は未確認です。この説明は既存の予算記録・集計に加算せず、子ども医療費や議案の確認状態も変更しません。</p>
        </>}
        <p>{note.locator}</p>
        <SourceLink url={note.url}>{p.id === 'P-03' ? '学校給食未来プロジェクトの予算案記載を確認する' : '保育料無償化の予算案記載を確認する'}</SourceLink>
      </article>}
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

// Keep the summary export and URL for existing bookmarks.
export function KyotoPolicyTotals({data}) {
  const stages=policyProgress({}).steps;
  const states=[
    ['confirmed','資料確認済み','その資料に書かれた内容を確認した範囲です。公約全体の実現や、次の段階の達成を意味しません。'],
    ['legacy','政策との対応を確認中','段階や記録と政策との関係を確認中です。到達を認定したものではありません。'],
    ['hold','保留','議案の番号・会期・件名などの対応を確認中です。可決済みの証拠には使いません。'],
    ['paused','停止中','最新の発表で事業が一時停止しています。過去の契約を取り消した、事業を中止したという意味ではありません。'],
    ['unverified','未確認','必要な根拠を確認できていません。予算や事業が存在しないと断定する表示ではありません。'],
  ];
  return <div className="kp-guide">
    <h1>このトラッカーの見方・作り方</h1>
    <p className="kp-guide-lead">これは公約達成率でも市長への評価でもなく、公式資料から確認できる政策プロセスの案内です。</p>
    <section className="kp-block"><h2>1. このトラッカーは何を示すのか</h2>
      <p>公約が計画・予算・議会の審議・実施へどう進んでいるかを、資料とともにたどれます。まず各カードの現況と重要な未確認事項をご覧ください。</p>
      <p>5段階は点数ではありません。資料で分かったことと、まだ分からないことを分けて表示します。</p>
    </section>
    <section className="kp-block kp-evidence"><h2>2. どの公約を、どの資料から調べているのか</h2>
      <p>{data.mayor_info?.name}市長の選挙公報などをもとに登録した京都の14政策を掲載しています。市長の発言や政策をすべて網羅した一覧ではありません。</p>
      <p>選挙公報で公約の原文、市の計画で位置付け、予算資料で事業と金額、議案・結果資料で審議の経緯、公式発表で最新状況を調べます。資料があるだけで、公約との直接の対応を認定しません。</p>
      <SourceLink url={data.mayor_info?.bulletin_pdf}>公約の出発点：選挙公報</SourceLink>
      <SourceLink url={data.mayor_info?.strategy_main_pdf}>登録された市の基本構想</SourceLink>
      <p>各政策の「根拠・履歴」に、原文・予算・議案・確認情報を残しています。全件の照合が完了しているわけではありません。</p>
    </section>
    <section className="kp-block"><h2>3. 5段階は何を意味するのか</h2>
      <ol className="kp-step-explanations">{stages.map(step=><li key={step.number}><h3>{step.number} {step.label}</h3><p>{step.meaning}</p></li>)}</ol>
      <p>破線の段階は根拠を確認中で、達成認定ではありません。例えば、P-01の準備予算案は制度の実施と区別し、P-02の議決は保留、P-03は過去契約より最新の工事停止を優先しています。</p>
    </section>
    <section className="kp-block"><h2>4. 確認状態の違い</h2>
      <dl className="kp-state-definitions">{states.map(([key,label,note])=><div key={key}><dt className={'kp-state-tag kp-step-'+key}><span aria-hidden="true">{PROGRESS_STATES[key].symbol} </span>{label}</dt><dd>{note}</dd></div>)}</dl>
      <p>色に加えて文字・記号・枠の形・線で区別します。資料確認済みの範囲は、各政策の説明も合わせてご確認ください。</p>
    </section>
    <section className="kp-block"><h2>5. 予算はどう読むのか</h2>
      <p><strong>予算案</strong>は提案段階です。議会で議決された予算、実際に使った額、政策の実現は、それぞれ別に確認します。</p>
      <p><strong>直接対応</strong>は資料で政策との直接の関係を確認したもの、<strong>関連参考</strong>は同じ分野などの文脈で関連するものです。参考予算や未確認額を直接予算に合算しません。</p>
      <p>年度・事業範囲・当初額と補正額にも注意が必要です。異なる年度や重なる事業を足して、公約の総費用とはしません。</p>
      <p>従来の集計値は元データと履歴に保持していますが、確認済みの達成率や単年度の確定予算としては示しません。</p>
    </section>
    <section className="kp-block"><h2>6. 更新・原典確認・訂正の方法</h2>
      <p>新しい資料や誤りが見つかった際は、政策との対応と確認状態を見直す必要があります。公式資料の取得・変更検知と、公開内容の確認・反映は別工程です。この画面が常に最新、全件確認済み、自動的に訂正済みと保証するものではありません。</p>
      <p>各政策の「根拠・履歴」から資料の用途・年度・ページを確認し、公式原典を開いて前後の文脈もお読みください。原典は新しいタブで開きます。外部URLの応答やPDFの目的ページへの移動は、未検証のものがあります。</p>
      <p>出典の誤りやリンク切れは、詳細の「出典・確認履歴」にある旗の「一次資料の不備を報告」からお知らせください。その他のご意見はページ下部のフォームで受け付けます。報告だけで自動的に公開情報が修正されるわけではありません。</p>
      <p>サイト全体の分析手法は共通ナビの「分析方法」にあります。京都の政策表示では、ここで説明する個別の確認状態を優先してお読みください。</p>
      <p className="kp-muted">AIは入口。判断するのは市民です。</p>
    </section>
  </div>;
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
    const onLocationChange = ()=>{
      restore.current = window.history.state?.kyotoPolicyList || {scrollY:0};
      setRoute(readPolicyRoute(window.location.search)); setRevision(n=>n+1);
    };
    window.addEventListener('popstate',onLocationChange);
    window.addEventListener('app-navigate',onLocationChange);
    return ()=>{
      window.removeEventListener('popstate',onLocationChange);
      window.removeEventListener('app-navigate',onLocationChange);
    };
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
        <header className="kp-header"><MayorProfile mayor={data.mayor_info}/><div><h1>京都市長政策</h1><p>公式資料から政策の現在地を確認できます。</p><p className="kp-muted">掲載 {pledges.length}件</p></div></header>
        <div className="kp-toolbar">
          <div className="kp-field"><label htmlFor="policy-query">政策名で探す</label><input id="policy-query" type="search" value={route.query} onChange={e=>filter({query:e.target.value})} placeholder="公約名・施策を検索" /></div>
          <div className="kp-field"><label htmlFor="policy-category">分野</label><select id="policy-category" value={route.category} onChange={e=>filter({category:e.target.value})}>
            <option value="ALL">すべての分野</option>{categories.map(cat=><option key={cat}>{cat}</option>)}
          </select></div>
          <a id="policy-totals-link" className="kp-button" href={href({section:'summary',policy:''})} onClick={e=>navigate(e,{section:'summary',policy:''},'policy-totals-link')}>このトラッカーの見方・作り方</a>
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
