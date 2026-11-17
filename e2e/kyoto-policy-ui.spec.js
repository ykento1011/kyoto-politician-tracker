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
 await ui.getByRole('link',{name:'このトラッカーの見方・作り方'}).click();
 await expect(ui.getByRole('heading',{name:'このトラッカーの見方・作り方'})).toBeVisible();
 for(const amount of ['85.7%','12/14','91億1,549万円']) await expect(ui).not.toContainText(amount);
 await expect(ui.getByRole('heading',{level:2})).toHaveCount(6);
 await expect(ui).toContainText('公約達成率でも市長への評価でもなく');
});

test('mayor identity and five-stage reference remain distinct from verified achievement',async({page})=>{
 await page.goto('/kyoto/?view=mayor');
 const profile=page.getByLabel('市長プロフィール',{exact:true});
 await expect(profile).toContainText(data.mayor_info.name);
 await expect(profile).toContainText(data.mayor_info.title);
 await expect(profile).toContainText(data.mayor_info.term);
 await expect(profile.getByRole('img')).toHaveAttribute('src',data.mayor_info.profile_image);
 await expect.poll(()=>profile.getByRole('img').evaluate(img=>img.complete&&img.naturalWidth>0)).toBe(true);
 const cards=page.locator('[data-policy-card]');
 await expect(cards.locator('.kp-steps')).toHaveCount(14);
 await expect(cards.locator('[data-stage]')).toHaveCount(70);
 for(const p of data.pledges){
  const card=page.locator(`[data-policy-card="${p.id}"]`);
  await expect(card).toContainText(`旧登録の参考段階：${p.stage_level}`);
  await expect(card).toContainText('到達認定は別');
 }
 await expect(page.locator('[data-policy-card="P-01"] [data-stage="3"]')).toContainText('予算案のみ');
 await expect(page.locator('[data-policy-card="P-02"] [data-stage="4"]')).toHaveAttribute('data-stage-state','hold');
 await expect(page.locator('[data-policy-card="P-03"] [data-stage="4"]')).toHaveAttribute('data-stage-state','legacy');
 await expect(page.locator('[data-policy-card="P-03"] [data-stage="5"]')).toContainText('停止中');
 for(const p of data.pledges.slice(3)) await expect(page.locator(`[data-policy-card="${p.id}"] [data-stage-state="confirmed"]`)).toHaveCount(0);
 for(const id of ['P-01','P-02','P-03']) {
  await page.getByRole('link',{name:`${id} 根拠・履歴`,exact:true}).click();
  await expect(page.getByRole('heading',{name:'5段階の意味と確認状況'})).toBeVisible();
  await expect(page.locator('.kp-step-explanations > li')).toHaveCount(5);
  if(id==='P-01') await expect(page.locator('.kp-step-explanations')).toContainText('予算議決・制度の試験運用・実施は未確認');
  if(id==='P-02') await expect(page.locator('.kp-step-explanations')).toContainText('条例可決を達成済みと認定していません');
  if(id==='P-03') await expect(page.locator('.kp-step-explanations')).toContainText('⑤への到達認定ではありません');
  await page.getByRole('link',{name:'← 政策一覧へ',exact:true}).first().click();
 }
});

test('mayor photo uses the existing fallback once and retains identity if both fail',async({page})=>{
 await page.route('**/councilors/kyoto/matsui_koji.jpg',r=>r.abort());
 await page.goto('/kyoto/?view=mayor');
 const profile=page.getByLabel('市長プロフィール',{exact:true});
 await expect(profile.getByRole('img')).toHaveAttribute('src',data.mayor_info.fallback_image);
 await expect.poll(()=>profile.getByRole('img').evaluate(img=>img.complete&&img.naturalWidth>0)).toBe(true);
 let failures=0;
 await page.route('**/councilors/kyoto/mayor.jpg',r=>{failures++;return r.abort();});
 await page.reload();
 await expect(profile.getByText('写真は表示できません')).toBeVisible();
 await expect(profile).toContainText(data.mayor_info.name);
 await expect(profile.getByRole('img')).toHaveCount(0);
 expect(failures).toBe(1);
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

async function openMayorFromSharedNavigation(page){
 const header=page.locator('header');
 const desktop=header.getByRole('button',{name:/市長政策進捗/});
 if(await desktop.isVisible()) await desktop.click();
 else await header.getByRole('button',{name:'政策進捗',exact:true}).click();
}

test('historic P-03 contract links remain separate from the current pause source',async({page})=>{
 await page.goto('/kyoto/?view=mayor&policy=P-03');
 const history=page.locator('#policy-history');
 await history.getByText('過去の契約・実施記録',{exact:true}).click();
 const contract=history.locator('a[href$="/G07-104.pdf"]');
 await expect(contract).toBeVisible();
 await expect(contract).toHaveAttribute('href','https://www2.city.kyoto.lg.jp/shikai/img/honkaigi/gian/R7-9/G07-104.pdf');
 await expect(contract).toContainText('現在の実施認定とは別');
 await expect(page.getByRole('link',{name:/工事停止の発表を見る/})).toHaveAttribute('href','https://www.city.kyoto.lg.jp/kyoiku/page/0000347372.html');
});

test('shared navigation synchronizes detail and totals with the URL and browser history',async({page})=>{
 for(const suffix of ['policy=P-03','mayorSection=summary']){
  await page.goto(`/kyoto/?view=mayor&${suffix}`);
  const detail=suffix.startsWith('policy=');
  const content=detail?page.locator('#policy-history'):page.getByRole('heading',{name:'このトラッカーの見方・作り方'});
  await expect(content).toBeVisible();
  await openMayorFromSharedNavigation(page);
  await expect(page).toHaveURL(/\/kyoto\/\?view=mayor$/);
  await expect(page.locator('[data-policy-card]')).toHaveCount(14,{timeout:3000});
  await expect(content).toHaveCount(0);
  await page.goBack();await expect(content).toBeVisible();
  await page.reload();await expect(content).toBeVisible();
  await page.goForward();await expect(page.locator('[data-policy-card]')).toHaveCount(14);
  await page.reload();await expect(page.locator('[data-policy-card]')).toHaveCount(14);
 }
});

test('four other cities retain their legacy display and shared navigation',async({page})=>{
 for(const city of ['kobe','osaka','nagoya','yokohama']){
  await page.goto(`/${city}/?view=mayor`);
  const title=page.getByText(/政策ライフサイクル検証基盤/);
  await expect(title).toBeVisible();
  const original=await title.textContent();
  await expect(page.locator('.kyoto-policy-ui')).toHaveCount(0);
  await openMayorFromSharedNavigation(page);
  await expect(page).toHaveURL(new RegExp(`/${city}/\\?view=mayor$`));
  await expect(title).toHaveText(original);
  await expect(page.locator('.kyoto-policy-ui')).toHaveCount(0);
 }
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

test('Kyoto print excludes sticky navigation only while printing this page',async({page})=>{
 for(const id of ['P-01','P-02','P-03']) {
  await page.goto(`/kyoto/?view=mayor&policy=${id}`);
  await expect(page.locator('#policy-budget')).toBeVisible();
  const header=page.locator('[data-kyoto-policy-page] > header');
  await expect(header).toBeVisible();
  await expect(header).toHaveCSS('position','sticky');
  await page.locator('#policy-budget').scrollIntoViewIfNeeded();
  await page.emulateMedia({media:'print'});
  await expect(header).toBeHidden();
  await expect(page.locator('#policy-budget')).toBeVisible();
  await expect(page.locator('#policy-sources')).toBeVisible();
  await page.emulateMedia({media:'screen'});
  await expect(header).toBeVisible();
  await expect(header).toHaveCSS('position','sticky');
 }
 for(const city of ['kobe','osaka','nagoya','yokohama']) {
  await page.goto(`/${city}/?view=mayor`);
  await expect(page.locator('[data-kyoto-policy-page]')).toHaveCount(0);
  const header=page.locator('header').first();
  await expect(header).toBeVisible();
  await page.emulateMedia({media:'print'});
  await expect(header).toBeVisible();
  await expect(header).toHaveCSS('position','sticky');
  await page.emulateMedia({media:'screen'});
  await expect(header).toBeVisible();
 }
});

test('real PDF printing includes closed evidence and restores every policy disclosure',async({page})=>{
 test.setTimeout(90000);
 for(const policy of data.pledges){
  await page.goto(`/kyoto/?view=mayor&policy=${policy.id}`);
  await expect(page.locator('#policy-sources')).toBeVisible();
  const original=await page.locator('.kyoto-policy-ui details').evaluateAll(nodes=>nodes.map(n=>n.open));
  expect(original.every(open=>!open)).toBe(true);
  await page.evaluate(()=>{
   window.printAudit=[];
   for(const type of ['beforeprint','afterprint']) window.addEventListener(type,()=>{
    const root=document.querySelector('.kyoto-policy-ui');
    window.printAudit.push({type,open:[...root.querySelectorAll('details')].map(n=>n.open),
     text:root.innerText,
     visibleBodies:[...root.querySelectorAll('details > :not(summary)')].every(n=>n.getBoundingClientRect().height>0)});
   });
  });
  const pdf=await page.pdf({format:'A4'});
  expect(pdf.subarray(0,5).toString()).toBe('%PDF-');
  const events=await page.evaluate(()=>window.printAudit);
  expect(events.map(e=>e.type)).toEqual(['beforeprint','afterprint']);
  expect(events[0].open.every(Boolean)).toBe(true);
  expect(events[0].visibleBodies).toBe(true);
  expect(events[0].text).toContain('未入力の確認日時や確認者は補完しません');
  if(policy.id==='P-01') for(const text of ['議案の同一性は未確認','議88','2億7,100万円','2億6,900万円','公営企業予算','契約のみ','EX100','制度実施の根拠ではありません']) expect(events[0].text).toContain(text);
  if(policy.id==='P-02') for(const text of ['可決根拠として保留','議145']) expect(events[0].text).toContain(text);
  if(policy.id==='P-03') for(const text of ['一時停止','開始時期は未定','議104','給食センター契約可決・着工']) expect(events[0].text).toContain(text);
  expect(events[1].open).toEqual(original);
  expect(await page.locator('.kyoto-policy-ui details').evaluateAll(nodes=>nodes.map(n=>n.open))).toEqual(original);
 }
});

test('printing preserves mixed disclosure state, repeated events and outside details',async({page})=>{
 await page.goto('/kyoto/?view=mayor&policy=P-01');
 await expect(page.locator('#policy-sources')).toBeVisible();
 const details=page.locator('.kyoto-policy-ui details');
 await details.nth(1).locator('summary').click();
 const original=await details.evaluateAll(nodes=>nodes.map(n=>n.open));
 expect(original.some(Boolean)).toBe(true);expect(original.some(open=>!open)).toBe(true);
 await page.evaluate(()=>{
  const outside=document.createElement('details');outside.id='outside-print-scope';
  outside.innerHTML='<summary>Outside the tracker</summary><p>Unrelated content</p>';
  document.body.append(outside);
 });
 await page.pdf({format:'A4'});
 expect(await details.evaluateAll(nodes=>nodes.map(n=>n.open))).toEqual(original);
 await page.evaluate(()=>{window.dispatchEvent(new Event('beforeprint'));window.dispatchEvent(new Event('beforeprint'));});
 expect(await details.evaluateAll(nodes=>nodes.every(n=>n.open))).toBe(true);
 await expect(page.locator('#outside-print-scope')).not.toHaveAttribute('open');
 await page.evaluate(()=>window.dispatchEvent(new Event('afterprint')));
 expect(await details.evaluateAll(nodes=>nodes.map(n=>n.open))).toEqual(original);
});
