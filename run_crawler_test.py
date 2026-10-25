import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "https://gikai-mikata.jp"

async def main():
    # 1. 巡回対象のURLリストを組み立て
    urls_to_test = [
        f"{BASE_URL}/",
        f"{BASE_URL}/osaka/",
        f"{BASE_URL}/#category=産業・観光・地域経済",
        f"{BASE_URL}/#category=子育て・教育",
        f"{BASE_URL}/#category=財政・行革",
        f"{BASE_URL}/#category=都市再生・交通インフラ",
        f"{BASE_URL}/#about",
        f"{BASE_URL}/#methodology",
        f"{BASE_URL}/#guide",
        f"{BASE_URL}/osaka/#mayor-tracker",
    ]

    # 2. 実データから議員名を抽出してテストURLに追加（京都・大阪）
    data_path = Path("frontend/public/data/statements_summary.json")
    if data_path.exists():
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                speakers = list(dict.fromkeys([item["speaker"] for item in data if "speaker" in item]))
                print(f"📋 検出された議員数: {len(speakers)} 名")
                # 全議員の個別URLを追加
                for spk in speakers:
                    urls_to_test.append(f"{BASE_URL}/?speaker={spk}")
        except Exception as e:
            print(f"⚠️ JSON読み込みスキップ: {e}")

    print(f"🚀 合計 {len(urls_to_test)} ページの自動巡回テストを開始します...\n")

    errors_found = []

    async with async_playwright() as p:
        # ヘッドレスブラウザを起動
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        # コンソールエラーとページ例外を監視・記録
        current_page_errors = []
        page.on("pageerror", lambda exc: current_page_errors.append(f"[PageCrash] {exc}"))
        page.on("console", lambda msg: current_page_errors.append(f"[ConsoleError] {msg.text}") if msg.type == "error" else None)

        for i, url in enumerate(urls_to_test, 1):
            current_page_errors.clear()
            response_status = None

            try:
                # ページ遷移とネットワーク待機
                response = await page.goto(url, wait_until="networkidle", timeout=12000)
                if response:
                    response_status = response.status

                # DOM描画の安定待ち
                await page.wait_for_timeout(500)

                # 白画面チェック（#root の中に子要素が描画されているか）
                root_children_count = await page.evaluate("() => document.getElementById('root')?.childElementCount || 0")
                if root_children_count == 0:
                    current_page_errors.append("[RenderError] 画面が白紙です（root要素が空）")

            except Exception as e:
                current_page_errors.append(f"[NavigationTimeout/Failed] {e}")

            # 異常があった場合のみ記録
            if current_page_errors or (response_status and response_status >= 400):
                errors_found.append({
                    "url": url,
                    "status": response_status,
                    "errors": list(current_page_errors)
                })
                print(f"❌ [{i}/{len(urls_to_test)}] 異常検知: {url}")
            else:
                # 進捗を5件ごとに簡易表示
                if i % 10 == 0 or i == len(urls_to_test):
                    print(f"✅ [{i}/{len(urls_to_test)}] チェック完了")

        await browser.close()

    # 3. 総合結果レポートの出力
    print("\n" + "=" * 60)
    print("📊 自動巡回テスト結果レポート")
    print("=" * 60)
    if not errors_found:
        print("🎉 全ページ正常！ コンソールエラー・404・白画面は検出されませんでした。")
    else:
        print(f"⚠️ {len(errors_found)} 件のページでエラーが検出されました:\n")
        for err in errors_found:
            print(f"■ URL: {err['url']} (HTTP {err['status']})")
            for msg in err["errors"]:
                print(f"   └ {msg}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
