const { test, expect } = require('@playwright/test');
const { createRequire } = require('node:module');
const { pathToFileURL } = require('node:url');
const path = require('node:path');

const frontend = path.resolve(__dirname, '../frontend');
const localRequire = createRequire(path.join(frontend, 'package.json'));
const guideUrl = 'https://www2.city.kyoto.lg.jp/shikai/kaigiroku/index.html';
const guideName = '京都市会公式の会議録検索';
const source = 'https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6359&schedule_id=1#minute_7';
const statement = { id: 'guide-test', speaker: '確認用議員', meeting_id: 'ssp_6359_1',
  meeting_date: '2026-01-20', sequence_number: 7, meeting_title: '確認用会議',
  source_url: source, summary: '病院の改善について質問', category: '医療' };
let script;

test.beforeAll(async () => {
  // Reuse Vite's installed bundler; no app/config/.env, source HTTP, or dependency installation.
  const viteRequire = createRequire(localRequire.resolve('vite'));
  const { rolldown } = await import(pathToFileURL(viteRequire.resolve('rolldown')).href);
  const entry = path.join(frontend, '__minute_guide_test__.jsx').replace(/\\/g, '/');
  const bundle = await rolldown({
    cwd: frontend, input: entry, platform: 'browser',
    transform: { jsx: 'react', define: { 'process.env.NODE_ENV': '"test"' } },
    plugins: [{
      name: 'minute-guide-test',
      resolveId(id) { if (id.replace(/\\/g, '/') === entry) return entry; },
      load(id) {
        if (id.replace(/\\/g, '/') === entry) return `
          import React from 'react';
          import { createRoot } from 'react-dom/client';
          import Guide from './src/components/KyotoMinuteGuideLink.jsx';
          import Card from './src/components/ThreadCard.jsx';
          import Modal from './src/components/TimelineModal.jsx';
          import Search from './src/components/AiSearchAnswer.jsx';
          const components = { Guide, Card, Modal, Search };
          let root;
          window.mount = (name, props) => {
            if (root) root.unmount();
            root = createRoot(document.getElementById('root'));
            root.render(React.createElement(components[name], {
              onClose() {}, onViewContext() {}, onSpeakerClick() {}, ...props,
            }));
          };
          window.__opens = [];
          window.open = url => { window.__opens.push(String(url)); return null; };
          window.fetch = async url => ({ ok: true, json: async () =>
            String(url).includes('topic_summaries') ? window.__topics || [] : {} });
        `;
      },
    }],
  });
  try { script = (await bundle.generate({ format: 'iife' })).output[0].code; }
  finally { await bundle.close(); }
});

test.beforeEach(async ({ page }) => {
  await page.route('**/*', route => route.abort());
  await page.setContent('<div id="root"></div>');
  await page.addScriptTag({ content: script });
});

async function mount(page, name, props) {
  await page.evaluate(({ name, props }) => window.mount(name, props), { name, props });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}
async function checkGuide(page) {
  const link = page.getByRole('link', { name: guideName, exact: true });
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute('href', guideUrl);
  await expect(link).toHaveAttribute('target', '_blank');
  await expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  await expect(page.getByText(/原典を直接開けない場合は/)).toBeVisible();
}

test('Kyoto SSP titled member follow-ups remain questions without relabeling officials', async ({ page }) => {
  const target = { ...statement, speaker: '確認太郎' };
  const context = [
    { speaker: '副委員長（確認 太郎）', is_target: true, is_admin: false, statement_text: '最初の質問' },
    { speaker: '事務局次長（回答花子）', is_admin: true, statement_text: '行政の答弁' },
    { speaker: '副委員長（確認 太郎）', is_admin: false, statement_text: '同じ議員の再質問' },
    { speaker: '委員長（進行一郎）', is_admin: false, is_short_procedural: true, statement_text: '議事進行のみ' },
  ];
  await mount(page, 'Modal', { cityCode: 'kyoto', isOpen: true, selectedContext: { statement: target, context } });
  await expect(page.getByText('質問', { exact: true })).toHaveCount(2);
  await expect(page.getByText('答弁 / 進行', { exact: true })).toHaveCount(1);
  await expect(page.getByText('副委員長（確認 太郎）', { exact: true })).toHaveCount(2);
  await expect(page.getByText('議事進行のみ', { exact: true })).toHaveCount(0);

  for (const cityCode of ['osaka', 'nagoya', 'yokohama', 'kobe']) {
    await mount(page, 'Modal', { cityCode, isOpen: true, selectedContext: { statement: target, context } });
    await expect(page.getByText('質問', { exact: true })).toHaveCount(1);
    await expect(page.getByText('答弁', { exact: true })).toHaveCount(1);
  }
});

test('guide is restricted to recorded Kyoto SSP links', async ({ page }) => {
  for (const cityCode of ['kyoto', 'osaka', 'nagoya', 'yokohama', 'kobe']) {
    await mount(page, 'Guide', { statement, cityCode });
    if (cityCode === 'kyoto') await checkGuide(page);
    else await expect(page.getByRole('link', { name: guideName })).toHaveCount(0);
  }
  for (const url of [undefined, 'invalid', 'https://www.city.kyoto.lg.jp/budget.html',
    'https://ssp.kaigiroku.net/tenant/cityosaka/MinuteView.html',
    'https://ssp.kaigiroku.net.example.org/tenant/kyoto/MinuteView.html']) {
    await mount(page, 'Guide', { statement: { source_url: url }, cityCode: 'kyoto' });
    await expect(page.getByRole('link', { name: guideName })).toHaveCount(0);
  }
});

test('card and timeline keep the original minute URL beside the guide', async ({ page }) => {
  for (const name of ['Card', 'Modal']) {
    await mount(page, name, { stmt: statement, cityCode: 'kyoto', isOpen: true,
      selectedContext: { statement, context: [{ ...statement, is_target: true }] } });
    await checkGuide(page);
    const label = name === 'Card' ? '議事録原本を確認' : '一次公文書を確認';
    await page.getByRole('button', { name: label, exact: true }).click();
    const url = await page.evaluate(() => window.__opens.at(-1));
    const parsed = new URL(url);
    expect(parsed.searchParams.get('council_id')).toBe('6359');
    expect(parsed.searchParams.get('schedule_id')).toBe('1');
    expect(parsed.searchParams.get('is_search')).toBe('false');
    expect(parsed.hash).toBe('#minute_7');
    expect(url.slice(url.indexOf('#'))).toBe('#minute_7');
  }
});

test('other city cards retain their source links without a Kyoto guide', async ({ page }) => {
  for (const cityCode of ['osaka', 'nagoya', 'yokohama', 'kobe']) {
    const original = `https://example.org/${cityCode}/record.html#speech-7`;
    await mount(page, 'Card', { stmt: { ...statement, source_url: original }, cityCode });
    await expect(page.getByRole('link', { name: guideName })).toHaveCount(0);
    await page.getByRole('button', { name: /議事録原本を確認$/ }).click();
    expect(await page.evaluate(() => window.__opens.at(-1))).toBe(original);
  }
});

for (const topic of [false, true]) {
  test('search original links include the guide: ' + (topic ? 'saved topic' : 'dynamic timeline'), async ({ page }) => {
    await page.evaluate(({ topic, statement }) => {
      window.__topics = topic ? [{ title: '病院', keywords: ['病院'], lead_summary: '病院の改善',
        timeline_phases: [{ period: '2026年', exchanges: [statement] }] }] : [];
    }, { topic, statement });
    await mount(page, 'Search', { query: '病院', filteredThreads: [statement], cityCode: 'kyoto' });
    await checkGuide(page);
    await page.getByRole('button', { name: topic ? '議事録原本を確認' : '原本を確認', exact: true }).click();
    expect(new URL(await page.evaluate(() => window.__opens.at(-1))).hash).toBe('#minute_7');
  });
}
