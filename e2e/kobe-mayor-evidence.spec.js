const {test,expect}=require('@playwright/test');
const data=require('../frontend/public/data/kobe_mayor_tracker.json');
test('Kobe M01 keeps unconfirmed amount and source without showing funding as confirmed',async({page})=>{
 await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():route.abort());
 await page.goto('/kobe/?view=mayor');
 const record=page.locator('section[data-budget-relation="unconfirmed"]');
 await expect(record).toHaveCount(1);
 await expect(record.getByText('14億2,000万円',{exact:true})).toBeVisible();
 await expect(record).toContainText('原典未確認');
 await expect(record).toContainText('未照合');
 await expect(record.locator('[data-budget-aggregation="excluded"]')).toHaveCount(1);
 await expect(record).not.toContainText('財源内訳：');
 await expect(record).not.toContainText('8億5,000万円');
 await expect(record).not.toContainText('5億7,000万円');
 await expect(record.getByRole('link',{name:'公式資料（PDF）を確認'})).toHaveAttribute('href',data.pledges[0].budget_records[0].doc_url);
 await expect(page.getByText('掲載答弁記録',{exact:true})).toBeVisible();
 await expect(page.getByText('関連予算総額',{exact:true})).toHaveCount(0);
 for(const policy of data.pledges.slice(1)) {
  const card=page.locator('div.rounded-2xl').filter({has:page.getByText(policy.id,{exact:true})});
  const amount=card.locator('span.text-base.font-black');
  await expect(amount).toHaveText(policy.budget_records[0].amount_display);
  await expect(amount).toBeVisible();
 }
});
