from pathlib import Path

p = Path("frontend/src/components/AiSearchAnswer.jsx")
if p.exists():
    txt = p.read_text(encoding="utf-8")
    
    # テンプレートリテラル内で正しく評価されるよう `$` を追加
    txt = txt.replace(
        "{cityCode === 'osaka' ? '大阪市会において' : '京都市会において'}",
        "${cityCode === 'osaka' ? '大阪市会において' : '京都市会において'}"
    )
    txt = txt.replace(
        "{cityCode === 'osaka' ? '大阪市会' : '京都市議会'}",
        "${cityCode === 'osaka' ? '大阪市会' : '京都市議会'}"
    )

    p.write_text(txt, encoding="utf-8")
    print("✅ AiSearchAnswer.jsx のテンプレートリテラル構文（$）を修正しました。")
