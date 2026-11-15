const { test, expect } = require('@playwright/test');
const { readFileSync } = require('node:fs');
const path = require('node:path');

let getOfficialMinuteUrl;
test.beforeAll(async () => {
  ({ getOfficialMinuteUrl } = await import('../frontend/src/utils/officialLink.js'));
});

test('all 21 published Kyoto 6360 links preserve the exact minute anchor', () => {
  const file = path.resolve(__dirname, '../frontend/public/data/kyoto_statements_summary.json');
  const statements = JSON.parse(readFileSync(file, 'utf8'));
  const added = statements.filter(s => s.meeting_id === 'ssp_6360_1');
  expect(added).toHaveLength(21);

  for (const stmt of added) {
    const link = getOfficialMinuteUrl(stmt, 'kyoto');
    const parsed = new URL(link);
    expect(parsed.origin).toBe('https://ssp.kaigiroku.net');
    expect(parsed.pathname).toBe('/tenant/kyoto/MinuteView.html');
    expect(parsed.searchParams.get('council_id')).toBe('6360');
    expect(parsed.searchParams.get('schedule_id')).toBe('1');
    expect(parsed.searchParams.get('is_search')).toBe('false');
    expect(parsed.searchParams.get('view_years')).toBe('2026');
    expect(parsed.hash).toBe('#minute_' + stmt.sequence_number);
    expect(link.slice(link.indexOf('#'))).toBe('#minute_' + stmt.sequence_number);
  }
});

test('existing MinuteView query parameters stay intact and fragment stays last', () => {
  const stmt = {
    meeting_date: '2026-03-12',
    source_url: 'https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=99&schedule_id=2&is_search=true#minute_8',
  };
  const result = getOfficialMinuteUrl(stmt, 'kyoto');
  expect(result).toBe('https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=99&schedule_id=2&is_search=true&view_years=2026#minute_8');
});

test('legacy links without a fragment and non-minute documents are unchanged', () => {
  const base = 'https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=42&schedule_id=3';
  expect(getOfficialMinuteUrl({ source_url: base, meeting_date: '2025-06-01' }, 'kyoto'))
    .toBe(base + '&is_search=false&view_years=2025');

  const document = 'https://www.city.kyoto.lg.jp/document.html#section';
  expect(getOfficialMinuteUrl({ source_url: document }, 'kyoto')).toBe(document);

  expect(getOfficialMinuteUrl({
    council_id: 42, schedule_id: 3, meeting_date: '2025-06-01',
  }, 'kyoto')).toBe(base + '&is_search=false&view_years=2025');
});
