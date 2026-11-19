const {test,expect}=require('@playwright/test');
const fs=require('node:fs'),path=require('node:path');
const cities=[['osaka',4,'OSAKA-M01'],['nagoya',5,'nagoya_p2'],['yokohama',12,'YOKOHAMA-M01']];
test.beforeEach(async({page})=>{
 await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
});
for(const [city,count,id] of cities)for(const width of [320,375,1440])test(`${city} shared route and evidence at ${width}px`,async({page})=>{
 const data=require(`../frontend/public/data/${city}_mayor_tracker.json`);
 const policy=data.pledges.find(p=>p.id===id);
 await page.setViewportSize({width,height:900});
 await page.goto(`/${city}/?view=mayor`);
 const ui=page.locator(`[data-mayor-city="${city}"]`);
 const capture=async name=>{
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  if(process.env.THREE_CITY_SCREENSHOT_DIR){
   await page.evaluate(()=>window.scrollTo(0,0));
   fs.mkdirSync(process.env.THREE_CITY_SCREENSHOT_DIR,{recursive:true});
   await page.screenshot({path:path.join(process.env.THREE_CITY_SCREENSHOT_DIR,`${city}-${name}-${width}.png`),fullPage:true});
  }
 };
 await expect(ui.locator('[data-policy-card]')).toHaveCount(count);
 await expect(ui.locator('[data-stage-state="confirmed"]')).toHaveCount(0);
 await capture('list');
 await page.getByLabel('政策名で探す',{exact:true}).fill(policy.headline);
 await page.getByLabel('分野',{exact:true}).selectOption(policy.category);
 await expect(ui.locator('[data-policy-card]')).toHaveCount(1);
 const link=page.getByRole('link',{name:`${id} 根拠・履歴`,exact:true});
 await link.click();
 await expect(ui.getByRole('heading',{name:'予算資料',exact:true})).toBeVisible();
 await expect(ui.locator('[data-budget-relation]')).toHaveCount(policy.budget_records.length);
 for(const record of policy.budget_records)await expect(ui.locator('#policy-budget')).toContainText(record.amount_display);
 await ui.getByText('登録計画・資料・確認情報',{exact:true}).click();
 if(city==='osaka'){
  await expect(ui).toContainText('配信元は未認証');
  await expect(ui).toContainText(policy.election_promise.bulletin_url);
  await expect(ui.locator(`a[href="${policy.election_promise.bulletin_url}"]`)).toHaveCount(0);
 }
 if(city==='nagoya')for(const text of ['120〜130億円','102億円','対応は未確認'])await expect(ui).toContainText(text);
 if(city==='yokohama'){
  await expect(ui).toContainText('404として追跡中');
  await expect(ui).toContainText('2026年1月の当初予算を同年10月');
  const broken=policy.budget_records[0].doc_url;
  await expect(ui).toContainText(broken);await expect(ui.locator(`a[href="${broken}"]`)).toHaveCount(0);
 }
 for(const href of await ui.locator('a[target="_blank"]').evaluateAll(nodes=>nodes.map(n=>n.href)))expect(new URL(href).hostname).toBe(`www.city.${city==='nagoya'?'nagoya.jp':city+'.lg.jp'}`);
 await capture('detail');
 await page.getByRole('link',{name:'← 政策一覧へ',exact:true}).first().click();
 await expect(link).toBeFocused();
 await expect(page.getByLabel('政策名で探す',{exact:true})).toHaveValue(policy.headline);
 await page.goForward();await expect(ui.getByRole('heading',{name:'予算資料',exact:true})).toBeVisible();
 await page.reload();await expect(ui.getByRole('heading',{name:'予算資料',exact:true})).toBeVisible();
 await page.locator('header').first().getByRole('button',{name:/市長政策進捗|^政策進捗$/}).filter({visible:true}).click();
 await expect(ui.locator('[data-policy-card]')).toHaveCount(count);
 await page.getByRole('link',{name:'このトラッカーの見方・作り方',exact:true}).click();
 await expect(ui).toContainText('公約達成率でも市長への評価でもなく');
 await capture('guide');
 await page.goto(`/${city}/?view=mayor&policy=${id}`);
 await expect(ui.getByRole('heading',{name:'予算資料',exact:true})).toBeVisible();
});
