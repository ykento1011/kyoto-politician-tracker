const {test,expect}=require('@playwright/test');
const data=require('../frontend/public/data/kyoto_mayor_tracker.json');
test.beforeEach(async({page})=>{
 await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
});

test('Kyoto overview keeps four fields, safe sources and unchanged figures in totals',async({page})=>{
 await page.goto('/kyoto/?view=mayor');
 const ui=page.locator('.kyoto-policy-ui');
 await expect(ui.locator('[data-policy-card]')).toHaveCount(14);
 await expect(ui.locator('[data-important-uncertainty]')).toHaveCount(14);
 await expect(ui.locator('a[target="_blank"]')).toHaveCount(3);
 for(const amount of ['85.7%','91億1,549万円','2億7,100万円']) await expect(ui.getByText(amount,{exact:true})).toHaveCount(0);
 await expect(ui.locator('[data-policy-card="P-01"]')).toContainText('試験運用・条例成立・国認可・正式実施は未確認');
 await expect(ui.locator('[data-policy-card="P-02"]')).toContainText('議決根拠を確認中');
 await expect(ui.locator('[data-policy-card="P-03"]')).toContainText('令和10年度中の開始は不可');
 await expect(ui.locator('[data-policy-card="P-14"]')).toContainText('原典未確認');
 await expect(ui.getByRole('link',{name:/準備予算案を見る/})).toHaveAttribute('href',/kaikenshiryo.pdf#page=22$/);
 await ui.getByRole('link',{name:'集計・算定方法を見る'}).click();
 await expect(ui.getByRole('heading',{name:'登録情報の集計・算定方法'})).toBeVisible();
 for(const amount of ['85.7%','91億1,549万円']) await expect(ui.getByText(amount,{exact:true})).toBeVisible();
 await expect(ui).toContainText('48億8,215万8,000円');
 await expect(ui).toContainText('確定済み件数・公約達成率ではありません');
});

test('all policies and 27 budget records remain reachable without external requests',async({page})=>{
 await page.goto('/kyoto/?view=mayor');let count=0;
 for(const p of data.pledges){
  await page.getByRole('link',{name:`${p.id} 根拠・履歴`,exact:true}).click();
  const records=page.locator('[data-budget-relation]');
  await expect(records).toHaveCount(p.budget_records.length); count+=await records.count();
  await expect(page.locator('#policy-history')).toBeVisible();
  await page.getByRole('link',{name:'← 政策一覧へ',exact:true}).first().click();
  await expect(page.locator('[data-policy-list]')).toBeVisible();
 }
 expect(count).toBe(27);
});

test('filters, scroll and focus survive detail, back, forward and reload',async({page})=>{
 await page.goto('/kyoto/?view=mayor');
 const link=page.getByRole('link',{name:'P-14 根拠・履歴',exact:true});
 await link.scrollIntoViewIfNeeded();await link.focus();
 const scroll=await page.evaluate(()=>window.scrollY);
 await link.click();
 await page.getByRole('link',{name:'← 政策一覧へ',exact:true}).first().click();
 await expect(link).toBeFocused();
 await expect.poll(()=>page.evaluate(()=>window.scrollY)).toBeCloseTo(scroll,0);
 await page.goForward();await expect(page.locator('#policy-budget')).toBeVisible();
 await page.goBack();await expect(link).toBeFocused();
 const p=data.pledges.find(p=>p.id==='P-03');
 await page.getByLabel('分野',{exact:true}).selectOption(p.category);
 await page.getByLabel('政策名で探す',{exact:true}).fill('給食');
 await page.getByRole('link',{name:'P-03 根拠・履歴',exact:true}).click();
 await page.reload();
 await expect(page.locator('#policy-history')).toContainText('工事が一時停止');
 await page.getByRole('link',{name:'← 政策一覧へ',exact:true}).first().click();
 await expect(page.getByLabel('政策名で探す',{exact:true})).toHaveValue('給食');
 await expect(page.getByLabel('分野',{exact:true})).toHaveValue(p.category);
 await expect(page.locator('[data-policy-card]')).toHaveCount(1);
});

for(const width of [1440,375,320]) test(`responsive ${width}px, 200% text and accessible controls`,async({page})=>{
 await page.setViewportSize({width,height:900});
 await page.goto('/kyoto/?view=mayor');
 const cards=page.locator('[data-policy-card]');await expect(cards).toHaveCount(14);
 const a=await cards.nth(0).boundingBox(),b=await cards.nth(1).boundingBox();
 if(width===1440){expect(a.y).toBe(b.y);expect(b.x).toBeGreaterThan(a.x)}
 else{expect(a.x).toBe(b.x);expect(b.y).toBeGreaterThan(a.y)}
 for(const size of [16,32]){
  await page.addStyleTag({content:`html {font-size:${size}px !important}`});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  const targets=page.locator('.kp-actions .kp-button');
  for(let i=0;i<await targets.count();i++) expect((await targets.nth(i).boundingBox()).height).toBeGreaterThanOrEqual(44);
  await page.getByRole('link',{name:'P-01 根拠・履歴',exact:true}).click();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  await expect(page.locator('h1')).toContainText('市民優先価格');
  await page.getByRole('link',{name:'← 政策一覧へ',exact:true}).first().click();
 }
});

test('keyboard and accessibility tree expose holds, purpose and disclosure state',async({page})=>{
 await page.goto('/kyoto/?view=mayor');
 const skip=page.getByRole('link',{name:'政策の本文へ',exact:true});await skip.focus();
 await page.keyboard.press('Enter');await expect(page.locator('#kyoto-policy-content')).toBeFocused();
 const link=page.getByRole('link',{name:'P-01 根拠・履歴',exact:true});await link.focus();
 await page.keyboard.press('Enter');
 const summary=page.getByText('内訳・関連性・金額の注記',{exact:true}).first();await summary.focus();
 await page.keyboard.press('Enter');await expect(page.getByText(/後者は公営企業予算/)).toBeVisible();
 await page.keyboard.press('Space');await expect(page.getByText(/後者は公営企業予算/)).not.toBeVisible();
 const tree=await page.locator('.kyoto-policy-ui').ariaSnapshot();
 for(const text of ['議案は保留','準備予算案を見る','新しいタブ','内訳・関連性・金額の注記']) expect(tree).toContain(text);
 await expect(page.locator('[data-legislative-status="hold"]')).toBeVisible();
 await expect(page.locator('[data-milestone-relation="contextual"]')).toContainText('制度実施の根拠ではありません');
 const source=page.getByRole('link',{name:/内訳（印刷p.31/});await expect(source).toHaveAttribute('href',/#page=32$/);
 // Local href/AX checks do not attest external responses or PDF page jumps.
 await page.emulateMedia({media:'print'});
 await expect(page.locator('[data-legislative-status="hold"]')).toBeVisible();
});
