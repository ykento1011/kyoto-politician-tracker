import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import react from '@vitejs/plugin-react';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const server = await createServer({
  root, configFile: false, envFile: false, plugins: [react()],
  server: { middlewareMode: true }, appType: 'custom',
});
after(() => server.close());
const { default: BudgetEvidence, hasBudgetEvidence, budgetSourceLabel } =
  await server.ssrLoadModule('/src/components/BudgetEvidence.jsx');
const data = JSON.parse(fs.readFileSync(path.join(root, 'public/data/kyoto_mayor_tracker.json')));
const pledge = data.pledges.find(p => p.id === 'P-01');
const render = records => renderToStaticMarkup(React.createElement(BudgetEvidence, {
  records, pledge, mayorInfo: data.mayor_info,
}));

test('both reviewed amounts, locations and proposal/contract notes are rendered separately', () => {
  const markup = render(pledge.budget_records);
  assert.equal((markup.match(/data-budget-relation=/g) || []).length, 2);
  for (const text of ['直接確認', '文脈上の関連', '2億7,100万円', '2億6,900万円',
    '令和8年度当初予算（案）', '印刷p.21', '印刷p.31', '公営企業予算', '契約のみ', '四捨五入']) {
    assert.ok(markup.includes(text), text);
  }
  assert.ok(!markup.includes('5億4,000万円'));
  assert.ok(!markup.includes('540000000'));
  assert.equal((markup.match(/href="https:\/\/www.city.kyoto.lg.jp\/sogo\/cmsfiles\/contents\/0000349\/349867\/kaikenshiryo.pdf"/g) || []).length, 2);
});
test('unreviewed financing is not presented as verified', () => {
  const markup = render(pledge.budget_records);
  assert.ok(!markup.includes('財源内訳'));
  assert.ok(!markup.includes('100%'));
  assert.ok(!markup.includes('1億8,000万円'));
  const approved = { ...pledge.budget_records[0], funding_verification_status: 'verified' };
  assert.ok(render([approved]).includes('財源内訳'));
});
test('source links distinguish PDF, HTML and unspecified formats', () => {
  assert.equal(budgetSourceLabel('https://example.invalid/a.PDF?download=1#page=2'), '公式資料（PDF）を確認');
  assert.equal(budgetSourceLabel('https://example.invalid/a.html#section'), '公式資料（HTML）を確認');
  assert.equal(budgetSourceLabel('https://example.invalid/document/123'), '公式資料を確認');
  const markup = render([{ ...pledge.budget_records[1], doc_url: 'https://example.invalid/a.html' }]);
  assert.ok(markup.includes('公式資料（HTML）を確認'));
  assert.ok(!markup.includes('公式資料（PDF）を確認'));
});
test('missing, unexpected and mixed review metadata never imply direct confirmation', () => {
  assert.equal(hasBudgetEvidence(), false);
  assert.equal(hasBudgetEvidence(null), false);
  assert.equal(hasBudgetEvidence([{ amount_jpy: 1 }]), false);
  assert.equal(hasBudgetEvidence([{ policy_relation: 'unconfirmed' }]), true);
  for (const value of [undefined, null, 'unexpected', '__proto__']) {
    const markup = render([{ ...pledge.budget_records[0], policy_relation: value }]);
    assert.ok(markup.includes('data-budget-relation="unconfirmed"'));
    assert.ok(!markup.includes('data-budget-relation="direct"'));
  }
});
test('broken sources are disabled without changing the recorded URL', () => {
  const markup = render([{ ...pledge.budget_records[0], is_broken: true }]);
  assert.ok(markup.includes('aria-disabled="true"'));
  assert.ok(markup.includes('href="#"'));
  assert.ok(markup.includes('サイト改編のため追跡中'));
});
