from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 1. AiSearchAnswer.jsx の重複引数の修正
ai_path = PROJECT_ROOT / "frontend" / "src" / "components" / "AiSearchAnswer.jsx"
if ai_path.exists():
    ai_text = ai_path.read_text(encoding="utf-8")
    # 引数リストの重複 cityCode を1つにまとめる
    ai_text = re.sub(
        r"export default function AiSearchAnswer\(\{([^}]+)\}\)",
        lambda m: "export default function AiSearchAnswer({" + 
                  ", ".join(dict.fromkeys(re.findall(r"[\w]+(?:\s*=\s*[^,]+)?", m.group(1)))) + 
                  "})",
        ai_text
    )
    ai_path.write_text(ai_text, encoding="utf-8")
    print("✅ AiSearchAnswer.jsx の引数重複を修正しました。")

# 2. TopicDetailPage.jsx の壊れた三項演算子を直接修正
tdp_path = PROJECT_ROOT / "frontend" / "src" / "components" / "TopicDetailPage.jsx"
if tdp_path.exists():
    lines = tdp_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        if "公式原本で確認" in line:
            # 該当行を安全・正常な JSX 表記に置き換え
            new_lines.append("                              <span>{cityCode === 'osaka' ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認'}</span>")
        else:
            new_lines.append(line)
    tdp_path.write_text("\n".join(new_lines), encoding="utf-8")
    print("✅ TopicDetailPage.jsx の構文エラーを修正しました。")
