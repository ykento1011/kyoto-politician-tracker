const {test,expect}=require('@playwright/test');
const cities={kyoto:'京都市',osaka:'大阪市',nagoya:'名古屋市',yokohama:'横浜市',kobe:'神戸市'};
for(const width of [320,375,1440]) test(`shared Navbar remains usable across five cities at ${width}px`,async({page})=>{
 await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
 await page.setViewportSize({width,height:900});
 for(const [city,label] of Object.entries(cities)){
  for(const size of [16,32]){
   await page.goto(`/${city}/?view=mayor`);
   const header=page.locator('header').first();
   await expect(header).toBeVisible();
   await page.addStyleTag({content:`html {font-size:${size}px !important}`});
   // Check the shared navigation, not the unrelated cities' policy content.
   const bounds=await header.evaluate(el=>[...el.querySelectorAll('button')].filter(b=>b.getBoundingClientRect().width>0).map(b=>{const r=b.getBoundingClientRect();return {left:r.left,right:r.right}}));
   for(const r of bounds){expect(r.left).toBeGreaterThanOrEqual(0);expect(r.right).toBeLessThanOrEqual(width);}
   await header.getByRole('button',{name:label,exact:true}).filter({visible:true}).click();
   const portal=page.getByRole('button',{name:'← 総合ポータルへ戻る',exact:true}).filter({visible:true});
   await expect(portal).toBeVisible();
   expect(await portal.evaluate(el=>el.scrollWidth<=el.clientWidth)).toBe(true);
   await portal.click();
   await expect(page).toHaveURL(/\/$/);
  }
 }
});
