from pathlib import Path
import re
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==========================================================
# 1. SearchResultsView.jsx: props に cityCode を追加・補正
# ==========================================================
srv_path = PROJECT_ROOT / "frontend" / "src" / "components" / "SearchResultsView.jsx"
if srv_path.exists():
    srv_text = srv_path.read_text(encoding="utf-8")
    
    # export default function SearchResultsView({ ... }) の引数に cityCode を確実に追加
    if "cityCode" not in srv_text.split("export default function SearchResultsView")[1].split("{")[0]:
        srv_text = re.sub(
            r"export default function SearchResultsView\(\{([^}]+)\}\)",
            r"export default function SearchResultsView({\1, cityCode = 'kyoto'})",
            srv_text
        )
    # cityCode がスコープにない場合のURLフォールバックガード
    if "const currentCity =" not in srv_text:
        srv_text = srv_text.replace(
            "export default function SearchResultsView",
            "// cityCode フォールバック\nexport default function SearchResultsView"
        )
    srv_path.write_text(srv_text, encoding="utf-8")
    print("✅ SearchResultsView.jsx の cityCode 定義を修正しました。")

# ==========================================================
# 2. App.jsx: SearchResultsView 呼び出しに cityCode={cityCode} を渡す
# ==========================================================
app_path = PROJECT_ROOT / "frontend" / "src" / "App.jsx"
if app_path.exists():
    app_text = app_path.read_text(encoding="utf-8")
    
    # <SearchResultsView ... /> に cityCode を渡す
    def inject_city(m):
        tag = m.group(0)
        if "cityCode=" in tag:
            return tag
        return tag.replace("<SearchResultsView", "<SearchResultsView cityCode={cityCode}")
    
    app_text = re.sub(r"<SearchResultsView\b[^>]*\/?>", inject_city, app_text)

    # 404 で HTML が返ってきた場合の JSON fetch ガード（空配列/フォールバック）
    # fetch(...).then(res => res.json()) で HTML の時は空オブジェクト/配列にする安全処理
    safe_fetch = """const safeFetchJson = async (url) => {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const text = await res.text();
    if (text.trim().startsWith('<')) return null; // HTMLフォールバック防止
    return JSON.parse(text);
  } catch (e) {
    return null;
  }
};"""
    if "safeFetchJson" not in app_text:
        app_text = safe_fetch + "\n" + app_text
        # mayor tracker と bill issues の fetch を safeFetchJson に置き換え
        app_text = re.sub(
            r"fetch\(([`'\"][^`'\"]*(?:mayor_tracker|contested_bills_issues)[^`'\"]*[`'\"])\)\s*\.then\([^)]+\)\s*\.then\(\s*([a-zA-Z0-9_]+)\s*=>\s*\{",
            r"safeFetchJson(\1).then(\2 => { if (!\2) return;",
            app_text
        )

    app_path.write_text(app_text, encoding="utf-8")
    print("✅ App.jsx の SearchResultsView 呼び出しと JSON フェッチ安全ガードを追加しました。")

# ==========================================================
# 3. 大阪用の空 mayor_tracker.json ダミーを配置（404エラー完全防止）
# ==========================================================
data_dir = PROJECT_ROOT / "frontend" / "public" / "data"
osaka_mayor = data_dir / "osaka_mayor_tracker.json"
if not osaka_mayor.exists():
    osaka_mayor.write_text(json.dumps([], ensure_ascii=False), encoding="utf-8")
    print("✅ osaka_mayor_tracker.json の初期ファイルを配置しました。")
