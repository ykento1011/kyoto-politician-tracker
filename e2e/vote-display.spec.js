const { test, expect } = require('@playwright/test');
const { createRequire } = require('node:module');
const { readFileSync } = require('node:fs');
const { createHash } = require('node:crypto');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

// Reuse installed React/Vite/Playwright. Do not load vite.config.js, .env or App.
const frontend = path.resolve(__dirname, '../frontend');
const frontendRequire = createRequire(path.join(frontend, 'package.json'));
const React = frontendRequire('react');
const { renderToStaticMarkup } = frontendRequire('react-dom/server');
const cities = ['kyoto', 'osaka', 'nagoya', 'yokohama', 'kobe'];
const snapshots = cities.map(city => {
  const file = path.join(frontend, 'public/data', city + '_votes_summary.json');
  const bytes = readFileSync(file);
  return { city, file, hash: createHash('sha256').update(bytes).digest('hex'), bills: JSON.parse(bytes.toString('utf8')) };
});

let vite;
let components;
test.beforeAll(async ({}, testInfo) => {
  const { createServer } = await import(pathToFileURL(frontendRequire.resolve('vite')).href);
  vite = await createServer({
    configFile: false,
    envFile: false,
    root: frontend,
    publicDir: false,
    cacheDir: path.join(testInfo.project.outputDir, 'vite-cache'),
    server: { middlewareMode: true, watch: null, hmr: false },
    optimizeDeps: { noDiscovery: true, include: [] },
    logLevel: 'error',
  });
  components = {};
  for (const name of ['BillsSection', 'BillDetailModal', 'ContestedBillsView']) {
    components[name] = (await vite.ssrLoadModule('/src/components/' + name + '.jsx')).default;
  }
});
test.afterAll(async () => {
  if (vite) await vite.close();
  for (const saved of snapshots) {
    expect(createHash('sha256').update(readFileSync(saved.file)).digest('hex')).toBe(saved.hash);
  }
});
test.beforeEach(async ({ page }) => {
  // The browser only receives rendered HTML. No source sites or external APIs.
  await page.route('**/*', route => route.abort());
});

const fixture = votes => ({
  session_name: '表示検証会期', bill_number: '試験1', title: '議決表示の合成テスト',
  result: '可決', votes,
});
const cases = [
  { name: 'agree only', votes: { 賛成会派: '賛成' }, label: '賛成の記録のみ', divided: false },
  { name: 'agree and oppose', votes: { 賛成会派: '賛成', 反対会派: '反対' }, label: '賛否が分かれた議案', divided: true },
  { name: 'agree and abstain/leave', votes: { 賛成会派: '賛成', 中立記録: '退席・棄権' }, label: '棄権・退席等あり', divided: false },
  { name: 'chair absent unknown', votes: { 記録A: '議長', 記録B: '欠席', 記録C: '不明', 記録D: '不参加' }, label: '棄権・退席等あり', divided: false },
  { name: 'empty votes', votes: {}, label: '賛否記録なし', divided: false },
  { name: 'oppose only', votes: { 反対会派: '反対' }, label: '反対の記録のみ', divided: false },
  { name: 'divided with neutral records', votes: { 賛成会派: '賛成', 反対会派: '反対', 記録A: '議長', 記録B: '除斥', 記録C: '採決時に不在', 記録D: '対応割れ' }, label: '賛否が分かれた議案', divided: true },
  { name: 'explicit symbols and missing value', votes: { 賛成会派: '〇', 反対会派: '×', 中立記録: null }, label: '賛否が分かれた議案', divided: true },
];

async function checkScreen(page, screen, bill, divided, label) {
  const noop = () => {};
  const issue = { ...bill, key_conflict: '試験用論点', background: '試験用説明', agree_logic: '試験用説明', disagree_logic: '試験用説明' };
  const props = screen === 'BillsSection'
    ? { filteredBills: [bill], issuesMap: {}, onlyContestedBills: false, setOnlyContestedBills: noop, onSelectBill: noop }
    : screen === 'BillDetailModal'
      ? { isOpen: true, bill, onClose: noop, onSpeakerClick: noop,
          speakerStats: Object.keys(bill.votes || {}).map(speaker => ({ speaker, partyGroup: '無所属' })) }
      : { billIssues: [issue], votesData: [bill], onClose: noop };
  await page.setContent(renderToStaticMarkup(React.createElement(components[screen], props)));
  await expect(page.getByText(/全会一致/)).toHaveCount(0);
  if (screen === 'ContestedBillsView') {
    await expect(page.locator('article')).toHaveCount(divided ? 1 : 0);
    if (!divided) return;
  } else if (label) {
    await expect(page.getByText(label, { exact: true })).toBeVisible();
  }
  if (screen === 'BillDetailModal') {
    await expect(page.getByText(/反対議員なし/)).toHaveCount(0);
    const values = Object.values(bill.votes || {});
    const oppositeCount = values.filter(v => v === '反対' || v === '×').length;
    await expect(page.getByText('反対した議員 (' + oppositeCount + '名)', { exact: true })).toBeVisible();
  }
  if (!Object.keys(bill.votes || {}).length) return;
  const heading = screen === 'BillDetailModal' ? '会派・無所属別の評決結果' : '各会派・無所属の評決態度';
  const table = page.getByText(heading, { exact: true }).locator('..');
  for (const [group, value] of Object.entries(bill.votes)) {
    const badge = table.getByText(group, { exact: true }).locator('..').locator('span').last();
    await expect(badge).toHaveText(value == null || String(value).trim() === '' ? '不明' : String(value));
    const agree = value === '賛成' || value === '〇';
    const oppose = value === '反対' || value === '×';
    await expect(badge).toHaveClass(agree ? /text-emerald-600/ : oppose ? /text-rose-600/ : /text-slate-600/);
    await expect(badge.locator('svg')).toHaveClass(agree ? /check/ : oppose ? /(?:circle-x|x-circle)/ : /minus/);
  }
}

for (const sample of cases) {
  for (const screen of ['BillsSection', 'BillDetailModal', 'ContestedBillsView']) {
    test(screen + ': ' + sample.name, async ({ page }) => {
      await checkScreen(page, screen, fixture(sample.votes), sample.divided, sample.label);
    });
  }
}

test('Kyoto 議92 keeps 退席・棄権 neutral without unanimity', async ({ page }) => {
  const bill = snapshots.find(s => s.city === 'kyoto').bills.find(b =>
    b.bill_number === '議92' && Object.values(b.votes || {}).includes('退席・棄権'));
  expect(bill).toBeTruthy();
  expect(Object.values(bill.votes)).not.toContain('反対');
  for (const screen of Object.keys(components)) {
    await checkScreen(page, screen, bill, false, '棄権・退席等あり');
  }
});

test('Nagoya 議長 stays neutral in all three screens', async ({ page }) => {
  const bill = snapshots.find(s => s.city === 'nagoya').bills.find(b =>
    Object.values(b.votes || {}).includes('議長') && Object.values(b.votes || {}).includes('反対'));
  expect(bill).toBeTruthy();
  for (const screen of Object.keys(components)) {
    await checkScreen(page, screen, bill, true);
  }
});

test('all stored vote labels from five cities retain their text and color category', async ({ page }) => {
  const values = [...new Set(snapshots.flatMap(s => s.bills.flatMap(b => Object.values(b.votes || {}))))];
  expect(values).toEqual(expect.arrayContaining(['賛成', '反対', '議長', '退席・棄権', '対応割れ']));
  for (const value of values) {
    for (const screen of Object.keys(components)) {
      await checkScreen(page, screen, fixture({ 賛成会派: '賛成', 反対会派: '反対', 対象記録: value }), true, '賛否が分かれた議案');
    }
  }
});


test('BillsSection contested filter requires both explicit positions', async ({ page }) => {
  const bills = cases.map((sample, index) => ({ ...fixture(sample.votes), bill_number: String(index) }));
  await page.setContent(renderToStaticMarkup(React.createElement(components.BillsSection, {
    filteredBills: bills, issuesMap: {}, onlyContestedBills: true,
    setOnlyContestedBills() {}, onSelectBill() {},
  })));
  await expect(page.locator('article')).toHaveCount(3);
  await expect(page.getByText('3 件表示中', { exact: true })).toBeVisible();
});

test('closed detail modal accepts a missing bill', () => {
  expect(renderToStaticMarkup(React.createElement(components.BillDetailModal, {
    isOpen: false, bill: null, onClose() {},
  }))).toBe('');
});


test('individual neutral and affirmative records override a party opposition record', async ({ page }) => {
  const bill = fixture({
    会派A: '反対', 議長甲: '議長', 欠席乙: '欠席', 棄権丙: '退席・棄権', 賛成丁: '賛成', 不明戊: null,
  });
  const speakerStats = ['議長甲', '欠席乙', '棄権丙', '賛成丁', '不明戊', '会派所属者']
    .map(speaker => ({ speaker, partyGroup: '会派A' }));
  await page.setContent(renderToStaticMarkup(React.createElement(components.BillDetailModal, {
    isOpen: true, bill, speakerStats, onClose() {}, onSpeakerClick() {},
  })));
  await expect(page.getByText('賛成した議員 (1名)', { exact: true })).toBeVisible();
  await expect(page.getByText('反対した議員 (1名)', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '賛成丁', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '会派所属者', exact: true })).toBeVisible();
  for (const name of ['議長甲', '欠席乙', '棄権丙', '不明戊']) {
    await expect(page.getByRole('button', { name, exact: true })).toHaveCount(0);
  }
});
