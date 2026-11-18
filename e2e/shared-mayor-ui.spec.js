const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
const path=require('node:path');
test.beforeEach(async({page})=>{
 await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
});
for(const width of [320,375,1440]) test(`shared Kobe and Kyoto pages fit ${width}px`,async({page},testInfo)=>{
 await page.setViewportSize({width,height:900});
 for(const [city,count,policy] of [['kyoto',14,'P-03'],['kobe',5,'KOBE-M01']]) {
  await page.goto(`/${city}/?view=mayor`);
  await expect(page.locator('[data-policy-card]')).toHaveCount(count);
  const ui=page.locator(`[data-mayor-city="${city}"]`);
  await expect(page.getByRole('complementary',{name:'ご意見・改善要望フォーム'})).toHaveCSS('position','static');
  await expect(ui.getByLabel('市長プロフィール',{exact:true})).toBeVisible();
  await expect(ui.locator('[data-stage-state="confirmed"]')).toHaveCount(city==='kyoto'?2:0);
  const save=async name=>{
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
   if(process.env.MAYOR_SCREENSHOT_DIR){
    fs.mkdirSync(process.env.MAYOR_SCREENSHOT_DIR,{recursive:true});
    await page.screenshot({path:path.join(process.env.MAYOR_SCREENSHOT_DIR,`${city}-${name}-${width}.png`),fullPage:true});
   }
  };
  await save('list');
  await page.getByRole('link',{name:`${policy} 根拠・履歴`,exact:true}).click();
  await expect(ui.getByRole('heading',{name:'予算資料',exact:true})).toBeVisible();
  await save('detail');
  const links=await ui.locator('a[target="_blank"]').evaluateAll(els=>els.map(e=>e.href));
  for(const link of links) expect(new URL(link).hostname).toMatch(city==='kyoto'?/^www2?\.city\.kyoto\.lg\.jp$/:/^www\.city\.kobe\.lg\.jp$/);
  await page.getByRole('link',{name:'← 政策一覧へ',exact:true}).first().click();
  await page.getByRole('link',{name:'このトラッカーの見方・作り方',exact:true}).click();
  await expect(ui.getByRole('heading',{name:'このトラッカーの見方・作り方',exact:true})).toBeVisible();
  await expect(ui).not.toContainText('91億1,549万円');
  await save('guide');
 }
});
test('Kobe restores search, category, focus and browser URL navigation',async({page})=>{
 await page.goto('/kobe/?view=mayor');
 await page.getByLabel('政策名で探す',{exact:true}).fill('人間');
 await page.getByLabel('分野',{exact:true}).selectOption('子育て・教育・福祉');
 await expect(page.locator('[data-policy-card]')).toHaveCount(1);
 const link=page.getByRole('link',{name:'KOBE-M02 根拠・履歴',exact:true});
 await link.click();await expect(page).toHaveURL(/policy=KOBE-M02/);
 await page.reload();await expect(page.getByRole('heading',{name:'予算資料',exact:true})).toBeVisible();
 await page.goBack();await expect(page.locator('[data-policy-card]')).toHaveCount(1);
 await expect(page.getByLabel('政策名で探す',{exact:true})).toHaveValue('人間');
 await expect(page.getByLabel('分野',{exact:true})).toHaveValue('子育て・教育・福祉');
 await expect(link).toBeFocused();
 await page.goForward();await expect(page.getByRole('heading',{name:'予算資料',exact:true})).toBeVisible();
 await page.goto('/kobe/?view=mayor&policy=KOBE-M01');
 await expect(page.getByRole('heading',{name:'予算資料',exact:true})).toBeVisible();
 await page.evaluate(()=>{history.pushState({},'', '/kobe/?view=mayor');window.dispatchEvent(new Event('app-navigate'));});
 await expect(page.locator('[data-policy-card]')).toHaveCount(5);
});

test('foreign city keeps hold, pause and missing evidence distinct',async({page})=>{
 const data=require('../frontend/public/data/kobe_mayor_tracker.json');
 const copy=structuredClone(data);copy.pledges[0].progress_evidence={status:'hold',summary:'TEST議決保留'};
 copy.pledges[1].latest_update={kind:'construction_paused',summary:'TEST停止',source_url:'https://www.city.kobe.lg.jp/test.html'};
 copy.pledges[2].budget_records=[];
 await page.route('**/data/kobe_mayor_tracker.json',r=>r.fulfill({json:copy}));
 await page.goto('/kobe/?view=mayor');
 await expect(page.locator('[data-policy-card="KOBE-M01"] [data-stage="4"]')).toHaveAttribute('data-stage-state','hold');
 await expect(page.locator('[data-policy-card="KOBE-M02"] [data-stage="5"]')).toHaveAttribute('data-stage-state','paused');
 await page.getByRole('link',{name:'KOBE-M03 根拠・履歴',exact:true}).click();
 await expect(page.locator('#policy-budget')).toContainText('予算資料未確認');
 await expect(page.locator('[data-budget-relation]')).toHaveCount(0);
});
