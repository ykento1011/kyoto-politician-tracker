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
const issueSnapshots = cities.map(city => {
  const file = path.join(frontend, 'public/data', city + '_bill_issues.json');
  const bytes = readFileSync(file);
  return { city, file, hash: createHash('sha256').update(bytes).digest('hex'), issues: JSON.parse(bytes.toString('utf8')) };
});

let vite;
let components;
let archiveScript;
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
  // Use Vite's installed bundler in memory for real React interactions; no server,
  // App, project build/config, generated files, or new dependency is needed.
  const viteRequire = createRequire(frontendRequire.resolve('vite'));
  const { rolldown } = await import(pathToFileURL(viteRequire.resolve('rolldown')).href);
  const entry = path.join(frontend, '__archive_test__.jsx').replace(/\\/g, '/');
  const bundle = await rolldown({
    cwd: frontend, input: entry, platform: 'browser',
    transform: { jsx: 'react', define: { 'process.env.NODE_ENV': '"test"' } },
    plugins: [{
      name: 'archive-test-entry',
      resolveId(id) { if (id.replace(/\\/g, '/') === entry) return entry; },
      load(id) {
        if (id.replace(/\\/g, '/') === entry) return `
          import React from 'react';
          import { createRoot } from 'react-dom/client';
          import Archive from './src/components/ContestedBillsView.jsx';
          window.mountArchive = props => createRoot(document.getElementById('root'))
            .render(React.createElement(Archive, { ...props, onClose() {} }));
        `;
      },
    }],
  });
  try {
    archiveScript = (await bundle.generate({ format: 'iife' })).output[0].code;
  } finally {
    await bundle.close();
  }
});
test.afterAll(async () => {
  if (vite) await vite.close();
  for (const saved of [...snapshots, ...issueSnapshots]) {
    expect(createHash('sha256').update(readFileSync(saved.file)).digest('hex')).toBe(saved.hash);
  }
});
test.beforeEach(async ({ page }) => {
  // Only local HTML and in-memory scripts. No source sites or external APIs.
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

async function mountArchive(page, billIssues, votesData) {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.setContent('<div id="root"></div>');
  await page.addScriptTag({ content: archiveScript });
  await page.evaluate(props => window.mountArchive(props), { billIssues, votesData });
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('市議会 賛否が分かれた議案');
  return errors;
}

const otherButton = page => page.getByRole('button', { name: /^その他・照合未確認の議案/ });
const contestedButton = page => page.getByRole('button', { name: /^賛否が分かれた議案/ });
const archiveCounts = { kyoto: [422, 314, 108, 89], osaka: [99, 99, 0, 0], nagoya: [30, 30, 0, 0], yokohama: [125, 125, 0, 0], kobe: [230, 219, 11, 0] };

for (const city of cities) {
  test(city + ': both archive views preserve every original issue without duplication', async ({ page }) => {
    const issues = issueSnapshots.find(s => s.city === city).issues;
    const votesData = snapshots.find(s => s.city === city).bills;
    const byKey = new Map(votesData.map(v => [v.session_name + '_' + v.bill_number, v]));
    const divided = [], other = [];
    for (const issue of issues) {
      const values = Object.values(byKey.get(issue.session_name + '_' + issue.bill_number)?.votes || {});
      (values.some(v => v === '賛成' || v === '〇') && values.some(v => v === '反対' || v === '×') ? divided : other).push(issue);
    }
    const [total, dividedCount, otherCount, unmatchedCount] = archiveCounts[city];
    expect([issues.length, divided.length, other.length]).toEqual([total, dividedCount, otherCount]);
    const errors = await mountArchive(page, issues, votesData);
    await expect(contestedButton(page)).toHaveAttribute('aria-pressed', 'true');
    const rendered = [];
    for (const [button, expected] of [[contestedButton(page), divided], [otherButton(page), other]]) {
      await button.click();
      await expect(page.locator('article')).toHaveCount(expected.length);
      const rows = await page.locator('article').evaluateAll(nodes => nodes.map(node => ({
        title: node.querySelector('h2').textContent.trim(), text: node.textContent,
        links: [...node.querySelectorAll('a')].map(a => a.getAttribute('href')),
      })));
      expect(rows.map(row => row.title)).toEqual(expected.map(issue => issue.title));
      expected.forEach((issue, i) => {
        for (const field of ['session_name', 'bill_number', 'key_conflict', 'background', 'agree_logic', 'disagree_logic']) {
          if (issue[field]) expect(rows[i].text).toContain(issue[field]);
        }
        const vote = byKey.get(issue.session_name + '_' + issue.bill_number);
        const urls = [...new Set([vote?.source_url, issue.official_url, issue.url, issue.source_url]
          .filter(url => typeof url === 'string' && /^https?:\/\//i.test(url)))];
        expect(rows[i].links).toEqual(urls);
      });
      rendered.push(...expected);
    }
    expect(rendered.length).toBe(total);
    expect(new Set(rendered).size).toBe(total);
    expect(issues.every(issue => rendered.includes(issue))).toBe(true);
    await expect(page.getByText('照合未確認（対応する議決データなし）', { exact: true })).toHaveCount(unmatchedCount);
    await expect(page.getByText('議決データあり：賛否対立を確認できない', { exact: true })).toHaveCount(otherCount - unmatchedCount);
    expect(errors).toEqual([]);
  });
}

function archiveFixtures() {
  const make = (number, title, session, votes, extras = {}) => ({
    ...fixture(votes), bill_number: number, title, session_name: session,
    key_conflict: title + 'の論点', background: title + 'の背景',
    agree_logic: '保存された賛成側記述', disagree_logic: '保存された反対側記述', ...extras,
  });
  const bills = [
    make('1', '学校・賛否両方', '会期A', { 会派A: '賛成', 会派B: '反対' }),
    make('2', '学校・未照合', '会期A', { 架空の照合候補: '反対' }, {
      official_url: 'https://example.invalid/saved/1', url: 'https://example.invalid/saved/1', source_url: 'https://example.invalid/saved/2',
    }),
    make('3', '学校・賛成のみ', '会期A', { 会派A: '賛成' }),
    make('4', '環境・退席棄権', '会期B', { 会派A: '賛成', 中立記録: '退席・棄権' }, { source_url: 'https://example.invalid/saved/3' }),
    make('5', '道路・賛否両方', '会期B', { 会派A: '賛成', 会派B: '反対' }, { result: '否決' }),
  ];
  return { issues: bills, votes: bills.filter(b => b.bill_number !== '2') };
}

test('real React switching preserves search/session/category and clears the result filter', async ({ page }) => {
  const { issues, votes } = archiveFixtures();
  const errors = await mountArchive(page, issues, votes);
  await expect(page.locator('article')).toHaveCount(2);
  await page.getByLabel('議決結果', { exact: true }).selectOption('可決');
  await expect(page.locator('article')).toHaveCount(1);
  await contestedButton(page).focus();
  await page.keyboard.press('Tab');
  await expect(otherButton(page)).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(otherButton(page)).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('article')).toHaveCount(3);
  await expect(page.getByLabel('議決結果', { exact: true })).toBeDisabled();
  await expect(page.getByLabel('議決結果', { exact: true })).toHaveValue('');
  await page.getByLabel('議案を検索', { exact: true }).fill('学校');
  await page.getByLabel('分野', { exact: true }).selectOption('子育て・教育');
  await page.getByLabel('会期', { exact: true }).selectOption('会期A');
  await expect(page.locator('article')).toHaveCount(2);
  await contestedButton(page).press('Space');
  await expect(page.locator('article h2')).toHaveText(['学校・賛否両方']);
  await expect(page.getByLabel('議決結果', { exact: true })).toBeEnabled();
  await expect(page.getByLabel('議決結果', { exact: true })).toHaveValue('');
  await otherButton(page).click();
  await page.getByLabel('会期', { exact: true }).selectOption('会期B');
  await expect(page.locator('article')).toHaveCount(0);
  await expect(page.getByText('「その他・照合未確認の議案」に該当する議案は見つかりませんでした。', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '条件をリセット', exact: true }).click();
  await expect(page.locator('article')).toHaveCount(3);
  await expect(otherButton(page)).toHaveAttribute('aria-pressed', 'true');
  expect(errors).toEqual([]);
});

test.describe('mobile archive controls', () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  test('tap exposes unverified content and only existing references without claiming a vote', async ({ page }) => {
    const { issues, votes } = archiveFixtures();
    const errors = await mountArchive(page, issues, votes);
    await otherButton(page).tap();
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('市議会 その他・照合未確認の議案');
    const unmatched = page.locator('article').filter({ has: page.getByRole('heading', { name: '学校・未照合', exact: true }) });
    await expect(unmatched.getByText('照合未確認（対応する議決データなし）', { exact: true })).toBeVisible();
    await expect(unmatched.getByText('学校・未照合の背景', { exact: true })).toBeVisible();
    await expect(unmatched.getByText(/結果:|各会派・無所属の評決態度/)).toHaveCount(0);
    await expect(unmatched.getByText('既存の論点整理（議決賛否の確認ではない）', { exact: true })).toBeVisible();
    expect(await unmatched.getByRole('link').evaluateAll(links => links.map(a => a.getAttribute('href'))))
      .toEqual(['https://example.invalid/saved/1', 'https://example.invalid/saved/2']);
    const agree = page.locator('article').filter({ has: page.getByRole('heading', { name: '学校・賛成のみ', exact: true }) });
    await expect(agree.getByText('議決データあり：賛否対立を確認できない', { exact: true })).toBeVisible();
    await expect(agree.getByRole('link')).toHaveCount(0);
    const neutral = page.getByText('退席・棄権', { exact: true });
    await expect(neutral).toHaveClass(/text-slate-600/);
    await expect(neutral.locator('svg')).toHaveClass(/minus/);
    await expect(page.getByText(/全会一致|対立確定|反対した議案/)).toHaveCount(0);
    await contestedButton(page).tap();
    await expect(page.locator('article')).toHaveCount(2);
    expect(errors).toEqual([]);
  });
});

test('real React archive search ignores surrounding ASCII and fullwidth spaces', async ({ page }) => {
  const { issues, votes } = archiveFixtures();
  const errors = await mountArchive(page, issues, votes);
  const search = page.getByLabel('議案を検索', { exact: true });

  for (const query of ['  学校  ', '　学校　']) {
    await search.fill(query);
    await expect(search).toHaveValue(query);
    await expect(page.locator('article h2')).toHaveText(['学校・賛否両方']);
    await otherButton(page).click();
    await expect(page.locator('article h2')).toHaveText(['学校・未照合', '学校・賛成のみ']);
    await contestedButton(page).click();
  }
  expect(errors).toEqual([]);
});
