from pathlib import Path
import re

# 1. AiSearchAnswer.jsx の修正（URLベースの確実な判定を追加）
ai_path = Path("frontend/src/components/AiSearchAnswer.jsx")
if ai_path.exists():
    txt = ai_path.read_text(encoding="utf-8")
    
    if "const actualCityCode" not in txt:
        txt = re.sub(
            r"(export default function AiSearchAnswer[^{]+\{)",
            r"\1\n  const actualCityCode = (typeof window !== 'undefined' && window.location.pathname.startsWith('/osaka')) ? 'osaka' : cityCode;",
            txt
        )
        
    # 表記の揺れや誤ったJSXバインディングを全て正規化
    txt = re.sub(
        r"\{?\$?\{?\w*cityCode\s*===\s*'osaka'\s*\?\s*'大阪市会において'\s*:\s*'京都市会において'\}?\}?", 
        "{actualCityCode === 'osaka' ? '大阪市会において' : '京都市会において'}", 
        txt
    )
    txt = re.sub(
        r"\{?\$?\{?\w*cityCode\s*===\s*'osaka'\s*\?\s*'大阪市会'\s*:\s*'京都市議会'\}?\}?", 
        "{actualCityCode === 'osaka' ? '大阪市会' : '京都市議会'}", 
        txt
    )

    ai_path.write_text(txt, encoding="utf-8")
    print("✅ AiSearchAnswer.jsx の都市判定とテキスト表示を最終修正しました。")

# 2. SearchResultsView.jsx の props 渡しの修正
srv_path = Path("frontend/src/components/SearchResultsView.jsx")
if srv_path.exists():
    txt = srv_path.read_text(encoding="utf-8")
    # 変数名が誤って prop 名に置換されていた部分を戻す
    txt = txt.replace("activeCityCode={activeCityCode}", "cityCode={activeCityCode}")
    srv_path.write_text(txt, encoding="utf-8")
    print("✅ SearchResultsView.jsx のコンポーネントへの props 渡しを修正しました。")
