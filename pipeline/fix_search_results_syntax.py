from pathlib import Path
import re

p = Path("frontend/src/components/SearchResultsView.jsx")
txt = p.read_text(encoding="utf-8")

# 1. 誤って props の中に入ってしまった宣言を削除
txt = re.sub(
    r"\s*const activeCityCode = [^;]+;", 
    "", 
    txt
)

# 2. 関数本体の開始位置 `) {` を見つけて、その直下に正しく宣言を挿入
def inject_to_body(match):
    return match.group(0) + "\n  const activeCityCode = typeof cityCode !== 'undefined' ? cityCode : (typeof window !== 'undefined' && window.location.pathname.startsWith('/osaka') ? 'osaka' : 'kyoto');"

# export default function SearchResultsView({ ... }) { のマッチ
txt = re.sub(
    r"(export\s+default\s+function\s+SearchResultsView\s*\([^)]+\)\s*\{)", 
    inject_to_body, 
    txt
)

p.write_text(txt, encoding="utf-8")
print("✅ SearchResultsView.jsx の構文エラーを修正しました。")
