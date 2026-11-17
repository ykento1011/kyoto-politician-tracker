// Display-only choices accepted for Kyoto TASK-0012. Never infer a primary source
// from array order, an old stage, a matching amount or an unreviewed bill.
const PREPARATION = 'https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000349/349867/kaikenshiryo.pdf';
const PLEDGE = 'https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf';
const PAUSE = 'https://www.city.kyoto.lg.jp/kyoiku/page/0000347372.html';

export function officialKyotoUrl(value) {
  try {
    const u = new URL(value);
    // Check the original authority too: URL parsing removes an explicit :443.
    const authority = typeof value === 'string' ? value.match(/^https:\/\/([^/?#]+)/)?.[1] : null;
    return u.protocol === 'https:' && ['www.city.kyoto.lg.jp', 'www2.city.kyoto.lg.jp'].includes(authority) && u.hostname === authority &&
      !u.username && !u.password && !u.port ? u.href : null;
  } catch { return null; }
}

export function sourceMedia(url = '') {
  try { return new URL(url).pathname.toLowerCase().endsWith('.pdf') ? 'PDF' : 'HTML'; }
  catch { return '資料'; }
}

export function policyPresentation(p) {
  const fallback = {
    title: p.headline || p.id, status: '根拠を確認中',
    warning: '原典未確認。現況と代表原典の対応を確認中です。登録内容は「根拠・履歴」に保持しています。',
    source: null,
  };
  if (p.id === 'P-01') {
    const record = p.budget_records?.find(r => r.doc_url === PREPARATION && !r.is_broken &&
      r.policy_relation === 'direct' && r.fiscal_year === '令和8年度当初予算（案）');
    if (record && p.progress_evidence?.status === 'preparation') return {
      title: '市バス等の「市民優先価格」', status: p.stage_label,
      warning: '議案は保留。制度の試験運用・条例成立・国認可・正式実施は未確認。',
      source: {url: PREPARATION + '#page=22', label: '準備予算案を見る', locator: '印刷p.21／PDF物理22ページ'},
    };
  }
  if (p.id === 'P-02' && p.progress_evidence?.status === 'hold') return {
    title: p.headline, status: '議決根拠を確認中',
    warning: '登録議案の同一性は未確認です。公約原文は条例可決の証拠ではありません。',
    source: p.election_promise?.bulletin_url === PLEDGE && !p.election_promise.is_broken
      ? {url: PLEDGE, label: '公約の原文を見る', locator: '公約表明の資料'} : null,
  };
  const event = p.latest_update;
  if (p.id === 'P-03' && event?.kind === 'construction_paused' && event.source_url === PAUSE) return {
    title: '全員制中学校給食の早期完全実施', status: event.label,
    warning: `${event.announced_at}発表。令和10年度中の開始は不可。新たな開始時期は未定です。`,
    source: {url: event.source_url, label: '工事停止の発表を見る', locator: event.announced_at + ' 公式発表'},
  };
  return fallback;
}

export function readPolicyRoute(search = '') {
  const q = new URLSearchParams(search);
  return {policy: q.get('policy') || '', section: q.get('mayorSection') || '',
    query: q.get('policyQuery') || '', category: q.get('policyCategory') || 'ALL'};
}

export function policyRouteHref(route, search = '') {
  const q = new URLSearchParams(search);
  q.set('view', 'mayor');
  for (const [key, value] of Object.entries({policy: route.policy, mayorSection: route.section,
    policyQuery: route.query, policyCategory: route.category === 'ALL' ? '' : route.category})) {
    if (value) q.set(key, value); else q.delete(key);
  }
  return '?' + q.toString();
}

const STAGES = [
  ['公約表明', '選挙公報などに記載された公約。実現したことを示す段階ではありません。'],
  ['市公式確定計画', '市の公式計画への位置付け。計画の確定と当該公約との対応を確認します。'],
  ['予算措置', '当該施策への予算措置。予算案の記載と議決済み予算は区別します。'],
  ['条例提出・可決', '条例等の議案の提出・議決。議案の同一性と審議結果をそれぞれ確認します。'],
  ['成立・執行', '制度の施行・事業の実施。関連する別施策や過去の実績とは区別します。'],
];
export const PROGRESS_STATES = {
  confirmed: {symbol:'◇', label:'資料確認済み'},
  legacy: {symbol:'○', label:'政策との対応を確認中', compact:'確認中'},
  hold: {symbol:'?', label:'確認中・保留', compact:'保留'},
  paused: {symbol:'Ⅱ', label:'停止中'},
  unverified: {symbol:'・', label:'未確認'},
};

// stage_level is only a historical reference, never a completion/verification
// count. The few evidence-scoped descriptions reuse accepted presentation gates.
export function policyProgress(p) {
  const reference = Number.isInteger(p.stage_level) && p.stage_level >= 1 && p.stage_level <= 5 ? p.stage_level : null;
  const steps = STAGES.map(([label, meaning], i)=>({number:i+1, label, meaning,
    state:reference && i<reference ? 'legacy' : 'unverified',
    note:reference && i<reference ? 'この段階の根拠と政策との対応を確認中です。到達を認定したものではありません。' : '到達を確認できていません。未実施と断定するものではありません。'}));
  const view = policyPresentation(p);
  if (p.id==='P-01' && p.progress_evidence?.status==='preparation') {
    if(view.source) Object.assign(steps[2],{state:'confirmed', short:'予算案のみ',
      note:'確認済みなのは導入準備の予算案への記載です。予算議決・制度の試験運用・実施は未確認です。'});
    Object.assign(steps[3],{state:'hold',note:'議案の同一性は保留中です。条例可決の実績として扱いません。'});
  }
  if(p.id==='P-02' && p.progress_evidence?.status==='hold') {
    if(view.source) Object.assign(steps[0],{state:'confirmed',short:'公約原文',note:'公約原文の資料を確認できます。条例可決の証拠ではありません。'});
    Object.assign(steps[3],{state:'hold',note:'④に関する議案の同一性は保留中です。条例可決を達成済みと認定していません。'});
  }
  if(p.id==='P-03' && p.latest_update?.kind==='construction_paused' && view.source) {
    Object.assign(steps[3],{note:'④にあるのは過去契約の履歴です。現在の工事進行や制度開始を示しません。'});
    Object.assign(steps[4],{state:'paused',note:'2026-11-05の発表では工事一時停止、令和10年度中の開始不可、開始時期未定です。⑤への到達認定ではありません。'});
  }
  const historicalContract = p.id==='P-03' && reference===4 && steps[4].state==='paused';
  return {reference, referenceLabel:historicalContract ? '過去契約の履歴' : reference ? STAGES[reference-1][0] : '段階未登録', steps};
}
