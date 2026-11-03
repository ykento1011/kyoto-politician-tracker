const { test, expect } = require('@playwright/test');

test.describe('Mobile & Desktop Modal Integrity Test', () => {
  test('Top page: open timeline modal and close it', async ({ page }) => {
    await page.goto('/kyoto/');
    await page.waitForLoadState('networkidle');

    // 「質疑スレッド」タブをクリックして発言録カードを表示
    const threadTab = page.locator('button:has-text("質疑スレッド")').first();
    await expect(threadTab).toBeVisible({ timeout: 10000 });
    await threadTab.click();

    // タイムライン起動ボタンをクリック
    const openBtn = page.locator('button:has-text("タイムラインを表示"), button:has-text("文脈を見る")').locator('visible=true').first();
    await expect(openBtn).toBeVisible({ timeout: 10000 });
    await openBtn.click();

    // モーダルが表示されること
    const modal = page.locator('[data-testid="statement-modal"]');
    await expect(modal).toBeVisible({ timeout: 5000 });

    // 一次公文書 / 原本リンクが存在すること（デスクトップ・モバイル双方の可視要素）
    const docBtn = modal.locator('button:has-text("原本"), button:has-text("一次公文書を確認")').locator('visible=true').first();
    await expect(docBtn).toBeVisible();

    // 閉じるボタンをタップ
    const closeBtn = modal.locator('button:has-text("閉じる")').locator('visible=true').first();
    await expect(closeBtn).toBeVisible();
    await closeBtn.click();

    // モーダルが閉じたこと
    await expect(modal).not.toBeVisible({ timeout: 5000 });
  });

  test('Category page: open timeline modal and close it (including swipe)', async ({ page, isMobile }) => {
    // カテゴリー詳細画面 (産業・観光・地域経済)
    const categoryUrl = '/kyoto/#category=' + encodeURIComponent('産業・観光・地域経済');
    await page.goto(categoryUrl);
    await page.waitForLoadState('networkidle');

    // カテゴリー画面内のタイムラインボタンをクリック
    const openBtn = page.locator('button:has-text("タイムラインを表示"), button:has-text("文脈を見る")').locator('visible=true').first();
    await expect(openBtn).toBeVisible({ timeout: 10000 });
    await openBtn.click();

    // モーダルが正常に表示されること
    const modal = page.locator('[data-testid="statement-modal"]');
    await expect(modal).toBeVisible({ timeout: 5000 });

    // 可視公文書リンクの存在確認
    const docBtn = modal.locator('button:has-text("原本"), button:has-text("一次公文書を確認")').locator('visible=true').first();
    await expect(docBtn).toBeVisible();

    if (isMobile) {
      // モバイル端末ではスワイプ（タッチ操作）によるクローズを検証
      const box = await modal.boundingBox();
      if (box) {
        const startX = box.x + box.width / 2;
        const startY = box.y + 20; // ヘッダー付近
        await page.touchscreen.tap(startX, startY);
        // 下方向へ 120px スワイプ
        await page.mouse.move(startX, startY);
        await page.mouse.down();
        await page.mouse.move(startX, startY + 120, { steps: 5 });
        await page.mouse.up();
      }
    }

    // 閉じるボタンによる確実なクローズ処理
    const closeBtn = modal.locator('button:has-text("閉じる")').locator('visible=true').first();
    if (await closeBtn.isVisible()) {
      await closeBtn.click();
    }

    await expect(modal).not.toBeVisible({ timeout: 5000 });
  });
});
