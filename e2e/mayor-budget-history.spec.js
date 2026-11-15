const {test,expect}=require('@playwright/test');
const data=require('../frontend/public/data/kyoto_mayor_tracker.json');
test('Kyoto budget history separates annual totals, deltas and unconfirmed amounts',async({page})=>{
 await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():route.abort());
 await page.goto('/kyoto/?view=mayor');
 await expect(page.getByText(data.summary_stats.total_allocated_budget_jpy,{exact:true})).toBeVisible();
 await expect(page.locator('[data-budget-role="delta"]')).toHaveCount(3);
 await expect(page.locator('[data-budget-role="after_change"]')).toHaveCount(1);
 const after=page.locator('section').filter({has:page.locator('[data-budget-role="after_change"]')});
 await expect(after.getByText('35億円',{exact:true})).toBeVisible();
 await expect(after.locator('[data-budget-aggregation="included"]')).toHaveCount(1);
 await expect(after.getByRole('link',{name:'公式資料（PDF）を確認'})).toHaveAttribute('href',/0809ippann.pdf$/);
 const unconfirmed=page.locator('section').filter({hasText:'スタートアップ支援及び企業立地促進強化事業'});
 await expect(unconfirmed.getByText('7億1,500万円',{exact:true})).toBeVisible();
 await expect(unconfirmed.locator('[data-budget-aggregation="excluded"]')).toHaveCount(1);
 await expect(unconfirmed).not.toContainText('財源内訳：');
 await expect(page.getByText('4億6,232万9,000円',{exact:true})).toBeVisible();
 await expect(page.getByText('＋2億5,800万円',{exact:true})).toBeVisible();
});
