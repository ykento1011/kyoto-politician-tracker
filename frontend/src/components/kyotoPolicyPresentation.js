// Display-only choices accepted for Kyoto TASK-0012. Never infer a primary source
// from array order, an old stage, a matching amount or an unreviewed bill.
const PREPARATION = 'https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000349/349867/kaikenshiryo.pdf';
const PLEDGE = 'https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf';
const PAUSE = 'https://www.city.kyoto.lg.jp/kyoiku/page/0000347372.html';

export function officialKyotoUrl(value) {
  try {
    const u = new URL(value);
    return u.protocol === 'https:' && u.hostname === 'www.city.kyoto.lg.jp' &&
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
