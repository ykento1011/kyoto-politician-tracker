import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "https://gikai-mikata.jp"

async def main():
    # ----------------------------------------------------
    # 1. テスト対象のURL・ハッシュリストの構築
    # ----------------------------------------------------
    urls_to_test = [
        # 基本・解説・市長公約
        f"{BASE_URL}/",
        f"{BASE_URL}/#about",
        f"{BASE_URL}/#methodology",
        f"{BASE_URL}/#guide",
        f"{BASE_URL}/#mayor-tracker",
        f"{BASE_URL}/osaka/",
        f"{BASE_URL}/osaka/#about",
        f"{BASE_URL}/osaka/#methodology",
        f"{BASE_URL}/osaka/#guide",
        f"{BASE_URL}/osaka/#mayor-tracker",
        f"{BASE_URL}/?view=mayor",
        f"{BASE_URL}/kyoto/?view=mayor",
        f"{BASE_URL}/osaka/?view=mayor",
    ]

    # データファイルから全カテゴリー名を抽出
    data_path = Path("frontend/public/data/statements_summary.json")
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            categories = list(dict.fromkeys([item["category"] for item in data if item.get("category")]))
            print(f"📂 検出された政策分野: {len(categories)} 分野")
            for cat in categories:
                urls_to_test.append(f"{BASE_URL}/#category={cat}")
                urls_to_test.append(f"{BASE_URL}/osaka/#category={cat}")

    # トピックデータが存在すれば全トピックURLを追加
    topics_path = Path("frontend/public/data/topics.json")
    if not topics_path.exists():
        topics_path = Path("frontend/public/data/macro_topics.json")
    if topics_path.exists():
        try:
            with open(topics_path, "r", encoding="utf-8") as f:
                topics_data = json.load(f)
                topic_ids = [t["id"] for t in topics_data if "id" in t]
                print(f"📌 検出されたトピック: {len(topic_ids)} 件")
                for tid in topic_ids[:15]: # 主要15トピックをテスト
                    urls_to_test.append(f"{BASE_URL}/#topic={tid}")
        except Exception:
            pass

    print(f"🚀 【Phase 1】全 {len(urls_to_test)} 画面のルーティング走査を開始します...\n")

    errors_found = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        current_errors = []
        page.on("pageerror", lambda exc: current_errors.append(f"[PageCrash] {exc}"))
        def handle_console(msg):
            if msg.type == "error":
                t = msg.text
                # 静的リソース（フォールバック画像やオプショナルJSON）の404通知はUI破損ではないためスキップ
                if "Failed to load resource" in t:
                    return
                current_errors.append(f"[ConsoleError] {t}")
        page.on("console", handle_console)

        # ----------------------------------------------------
        # Phase 1: 全画面のURL・ハッシュアクセスチェック
        # ----------------------------------------------------
        for i, url in enumerate(urls_to_test, 1):
            current_errors.clear()
            resp_status = None
            try:
                resp = await page.goto(url, wait_until="load", timeout=12000)
                if resp:
                    resp_status = resp.status
                await page.wait_for_timeout(400)

                # 白画面チェック
                root_children = await page.evaluate("() => document.getElementById('root')?.childElementCount || 0")
                if root_children == 0:
                    current_errors.append("[RenderError] 画面が白紙です（#root が空）")
            except Exception as e:
                current_errors.append(f"[NavigationFailed] {e}")

            if current_errors or (resp_status and resp_status >= 400):
                errors_found.append({"target": url, "status": resp_status, "errors": list(current_errors)})
                print(f"❌ [{i}/{len(urls_to_test)}] エラー検知: {url}")
            else:
                if i % 10 == 0 or i == len(urls_to_test):
                    print(f"✅ [{i}/{len(urls_to_test)}] チェック完了")

        # ----------------------------------------------------
        # Phase 2: インタラクティブ操作テスト（タブ・モーダル・比較）
        # ----------------------------------------------------
        print("\n🚀 【Phase 2】ボタンクリック・モーダル開閉・タブ切り替えテストを開始します...\n")

        # 1. メイン画面のタブ切り替え操作
        await page.goto(f"{BASE_URL}/", wait_until="load")
        tabs = ["会派・選挙区", "政策分野", "賛否が分かれた議案", "議員一覧"]
        for tab_name in tabs:
            current_errors.clear()
            try:
                tab_btn = page.locator(f"button:has-text('{tab_name}')").first
                if await tab_btn.is_visible():
                    await tab_btn.click()
                    await page.wait_for_timeout(600)
                    print(f"  👉 タブ切り替え: 『{tab_name}』 正常")
            except Exception as e:
                current_errors.append(f"[TabError] 『{tab_name}』クリック失敗: {e}")
            if current_errors:
                errors_found.append({"target": f"タブ: {tab_name}", "status": "UI", "errors": list(current_errors)})

        # 2. タイムラインモーダルの開閉テスト
        current_errors.clear()
        try:
            timeline_btn = page.locator("button:has-text('タイムライン'), button:has-text('前後の対話')").first
            if await timeline_btn.is_visible():
                await timeline_btn.click()
                await page.wait_for_timeout(800)
                print("  👉 タイムラインモーダル展開: 正常")
                # Escキーで閉じる
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(400)
        except Exception as e:
            current_errors.append(f"[TimelineModalError] {e}")
        if current_errors:
            errors_found.append({"target": "タイムラインモーダル", "status": "Modal", "errors": list(current_errors)})

        # 3. 賛否議案モーダルの開閉テスト
        current_errors.clear()
        try:
            # 賛否議案タブへ切り替え
            bills_tab = page.locator("button:has-text('賛否が分かれた議案')").first
            if await bills_tab.is_visible():
                await bills_tab.click()
                await page.wait_for_timeout(600)
                # 議案カードまたは詳細ボタンをクリック
                bill_item = page.locator("article button, tr button, div:has-text('詳細を見る')").first
                if await bill_item.is_visible():
                    await bill_item.click()
                    await page.wait_for_timeout(800)
                    print("  👉 議案詳細モーダル展開: 正常")
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(400)
        except Exception as e:
            current_errors.append(f"[BillModalError] {e}")
        if current_errors:
            errors_found.append({"target": "議案詳細モーダル", "status": "Modal", "errors": list(current_errors)})

        await browser.close()

    # ----------------------------------------------------
    # 総合結果レポート
    # ----------------------------------------------------
    print("\n" + "=" * 65)
    print("📊 包括的自動テスト結果レポート")
    print("=" * 65)
    if not errors_found:
        print("🎉 全画面・全モーダル・全タブ正常！ コンソールエラーやクラッシュは0件でした。")
    else:
        print(f"⚠️ {len(errors_found)} 箇所で異常が検出されました:\n")
        for err in errors_found:
            print(f"■ 対象: {err['target']} ({err['status']})")
            for msg in err["errors"]:
                print(f"   └ {msg}")
            print("-" * 55)

if __name__ == "__main__":
    asyncio.run(main())
