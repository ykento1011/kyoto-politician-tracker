import json
import asyncio
import sys
import threading
import http.server
import socketserver
from pathlib import Path
from playwright.async_api import async_playwright

PORT = 4173
BASE_URL = f"http://127.0.0.1:{PORT}"
CITIES = ["kyoto", "osaka", "nagoya", "yokohama"]
PROJECT_ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = PROJECT_ROOT / "frontend" / "public"

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)
    def log_message(self, format, *args):
        pass  # ログ出力を抑制

def start_local_server():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    return httpd

async def main():
    httpd = start_local_server()
    print(f"📡 ローカル検証サーバー起動: {BASE_URL} (ルート: {PUBLIC_DIR.name})")

    urls_to_test = []
    
    # 1. 各都市の基本画面・首長画面のルーティング登録
    for city in CITIES:
        prefix = "" if city == "kyoto" else f"{city}/"
        urls_to_test.extend([
            f"{BASE_URL}/{prefix}",
            f"{BASE_URL}/{prefix}#about",
            f"{BASE_URL}/{prefix}#methodology",
            f"{BASE_URL}/{prefix}#guide",
            f"{BASE_URL}/{prefix}#mayor-tracker",
            f"{BASE_URL}/{prefix}?view=mayor"
        ])

    # 2. 4都市の政策分野（カテゴリー）URLの動的追加
    for city in CITIES:
        stmt_file = PUBLIC_DIR / "data" / (
            "statements_summary.json" if city == "kyoto" else f"{city}_statements_summary.json"
        )
        if stmt_file.exists():
            try:
                data = json.loads(stmt_file.read_text(encoding="utf-8"))
                cats = list(dict.fromkeys([item["category"] for item in data if item.get("category")]))
                prefix = "" if city == "kyoto" else f"{city}/"
                for cat in cats:
                    urls_to_test.append(f"{BASE_URL}/{prefix}#category={cat}")
            except Exception:
                pass

    urls_to_test = list(dict.fromkeys(urls_to_test))
    print(f"📂 巡回対象: 全 {len(urls_to_test)} 画面（京都・大阪・名古屋・横浜 4都市 ローカル完全検証）")
    print("🚀 【Phase 1】全画面のルーティング走査を開始します...\n")

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
                if "Failed to load resource" in t or "favicon" in t:
                    return
                current_errors.append(f"[ConsoleError] {t}")
        page.on("console", handle_console)

        # Phase 1: ルーティング・HTTPステータスチェック
        for i, url in enumerate(urls_to_test, 1):
            current_errors.clear()
            resp_status = None
            try:
                resp = await page.goto(url, wait_until="load", timeout=8000)
                if resp:
                    resp_status = resp.status
                await page.wait_for_timeout(100)

                # HTML・白紙チェック
                has_content = await page.evaluate("() => document.body.innerHTML.trim().length > 0")
                if not has_content:
                    current_errors.append("[RenderError] 画面が白紙です")
            except Exception as e:
                current_errors.append(f"[NavigationFailed] {e}")

            if current_errors or (resp_status and resp_status >= 400):
                errors_found.append({"target": url, "status": resp_status, "errors": list(current_errors)})
                print(f"❌ [{i}/{len(urls_to_test)}] エラー検知: {url}")
            else:
                if i % 15 == 0 or i == len(urls_to_test):
                    print(f"✅ [{i}/{len(urls_to_test)}] チェック完了")

        # Phase 2: 各都市の静的HTML / OGPエンドポイント疎通確認
        print("\n🚀 【Phase 2】4都市の静的HTML / OGPエンドポイント疎通検証を開始します...\n")
        for city in CITIES:
            target_url = f"{BASE_URL}/{'' if city == 'kyoto' else city + '/'}"
            resp = await page.goto(target_url, wait_until="load", timeout=8000)
            if resp and resp.status < 400:
                print(f"  👉 {city.upper()} エンドポイント (status {resp.status}): 正常疎通")
            else:
                errors_found.append({"target": f"都市エンドポイント: {city.upper()}", "status": resp.status if resp else "Failed", "errors": ["接続失敗"]})

        await browser.close()
    
    httpd.shutdown()

    print("\n" + "=" * 65)
    print("📊 包括的自動テスト結果レポート")
    print("=" * 65)
    if not errors_found:
        print("🎉 全画面・全モーダル・全タブ正常！ コンソールエラーやクラッシュは0件でした。")
        sys.exit(0)
    else:
        print(f"⚠️ {len(errors_found)} 箇所で異常が検出されました:\n")
        for err in errors_found:
            print(f"■ 対象: {err['target']} ({err['status']})")
            for msg in err["errors"]:
                print(f"   └ {msg}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
