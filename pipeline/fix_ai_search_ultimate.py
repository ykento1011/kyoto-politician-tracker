import subprocess
from pathlib import Path
import re

p = Path("frontend/src/components/AiSearchAnswer.jsx")
success_git = False

try:
    # 1. Gitのコミット履歴から、壊れる前の完全なソースコードを取得
    original = subprocess.check_output(
        ['git', 'show', 'HEAD:frontend/src/components/AiSearchAnswer.jsx'], 
        stderr=subprocess.STDOUT
    ).decode('utf-8')
    txt = original
    success_git = True
except Exception:
    # 2. 万が一Gitが使えない場合のフォールバック（破壊されたJSON構文の直接修復）
    txt = p.read_text(encoding="utf-8")
    txt = re.sub(r"\}\s*本議会において「", "},\n        { role: 'user', content: `本議会において「", txt)

# 3. 過去に挿入された複雑な条件分岐（三項演算子）が残っていれば一掃する
txt = re.sub(r"\{?\$?\{?\w*cityCode\s*===\s*'osaka'\s*\?\s*'[^']+'\s*:\s*'[^']+'\}?\}?", "本議会において", txt)

# 4. 単純な単語置換で「本議会」に統一（構文を一切壊さない安全な処理）
txt = txt.replace("京都市会において", "本議会において")
txt = txt.replace("京都市議会において", "本議会において")
txt = txt.replace("京都市会", "本議会")
txt = txt.replace("京都市議会", "本議会")

p.write_text(txt, encoding="utf-8")

if success_git:
    print("✅ Git履歴から AiSearchAnswer.jsx をクリーンな状態に復元し、「本議会」表記に統一しました。")
else:
    print("✅ AiSearchAnswer.jsx の構文エラー箇所を強制修復し、「本議会」表記に統一しました。")
