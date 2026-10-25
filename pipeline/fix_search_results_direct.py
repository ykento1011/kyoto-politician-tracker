from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 1. SearchResultsView.jsx の先頭シグネチャを確実に修正
srv_path = PROJECT_ROOT / "frontend" / "src" / "components" / "SearchResultsView.jsx"
srv_text = srv_path.read_text(encoding="utf-8")

# 引数 props を安全に置換
srv_text = re.sub(
    r"export\s+default\s+function\s+SearchResultsView\s*\(\s*\{([^}]+)\}\s*\)",
    lambda m: f"export default function SearchResultsView({{ {m.group(1).strip()}, cityCode = 'kyoto' }})"
              if "cityCode" not in m.group(1) else m.group(0),
    srv_text
)

# 万が一 props の外で cityCode が参照されたときの関数内先頭フォールバック
if "const currentCityCode =" not in srv_text:
    srv_text = re.sub(
        r"(export\s+default\s+function\s+SearchResultsView[^{]+\{)",
        r"\1\n  const activeCityCode = typeof cityCode !== 'undefined' ? cityCode : (typeof window !== 'undefined' && window.location.pathname.startsWith('/osaka') ? 'osaka' : 'kyoto');",
        srv_text
    )
    # cityCode 単体参照を activeCityCode または安全なフォールバックで救済
    srv_text = re.sub(r"(?<!active)cityCode(?!\w)", "activeCityCode", srv_text)

srv_path.write_text(srv_text, encoding="utf-8")
print("✅ SearchResultsView.jsx を直接安全化しました。")

# 2. App.jsx の <SearchResultsView ... /> 呼び出しすべてに cityCode を付与
app_path = PROJECT_ROOT / "frontend" / "src" / "App.jsx"
app_text = app_path.read_text(encoding="utf-8")

app_text = re.sub(
    r"<SearchResultsView\b(?![^>]*cityCode=)",
    "<SearchResultsView cityCode={cityCode} ",
    app_text
)

# 3. contested_bills_issues の 404 ガード強化
# fetch が失敗しても白画面・JSON構文エラーにならないよう保護
app_text = re.sub(
    r"fetch\(([`'\"][^`'\"]*contested_bills_issues[^`'\"]*[`'\"])\)\s*\.then\(res\s*=>\s*res\.json\(\)\)",
    r"fetch(\1).then(res => res.ok ? res.json() : []).catch(() => [])",
    app_text
)

app_path.write_text(app_text, encoding="utf-8")
print("✅ App.jsx の SearchResultsView 呼び出しと JSON フェッチを保護しました。")
