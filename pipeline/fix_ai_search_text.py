from pathlib import Path

p = Path("frontend/src/components/AiSearchAnswer.jsx")
if p.exists():
    txt = p.read_text(encoding="utf-8")
    
    # 入れ子になってしまった構文を元の正しい三項演算子に直接置換
    bad_string = "{cityCode === 'osaka' ? '大阪市会において' : '{cityCode === 'osaka' ? '大阪市会' : '京都市議会'}において'}"
    correct_string = "{cityCode === 'osaka' ? '大阪市会において' : '京都市会において'}"
    
    if bad_string in txt:
        txt = txt.replace(bad_string, correct_string)
    
    # 万が一別のパターンで入れ子になっている場合の保険
    bad_string_2 = "{cityCode === 'osaka' ? '大阪市会' : '{cityCode === 'osaka' ? '大阪市会' : '京都市議会'}'}"
    correct_string_2 = "{cityCode === 'osaka' ? '大阪市会' : '京都市議会'}"
    
    if bad_string_2 in txt:
        txt = txt.replace(bad_string_2, correct_string_2)

    p.write_text(txt, encoding="utf-8")
    print("✅ AiSearchAnswer.jsx のテキストの二重置換を修正しました。")
