from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
tc_path = PROJECT_ROOT / "frontend" / "src" / "components" / "ThreadCard.jsx"
tc_text = tc_path.read_text(encoding="utf-8")

# 引数 props の定義を確認・正規化
# ThreadCard({ statement, thread, ... }) どちらで渡されても動くように防御的に取得
target_check = """  // statement または thread のいずれかが渡されても受け取れるように防御的処理
  const item = thread || statement || {};
  const isOsakaThread = cityCode === 'osaka' || 
                        item?.council === '大阪市会' || 
                        item?.source_url?.includes('city.osaka.lg.jp');
  const councilOriginalLabel = isOsakaThread ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認';"""

# 先ほど追加した壊れた判定ブロックを差し替え
tc_text = re.sub(
    r"// 都市の判定.*?const councilOriginalLabel = .*?;",
    target_check,
    tc_text,
    flags=re.DOTALL
)

# もし props 引数に statement または thread が入っていない場合の対応
# export default function ThreadCard({ ... })
if "cityCode" not in tc_text.split("export default function ThreadCard")[1].split("{")[0]:
    tc_text = re.sub(
        r"export default function ThreadCard\(\{([^}]+)\}\)",
        r"export default function ThreadCard({\1, cityCode})",
        tc_text
    )

tc_path.write_text(tc_text, encoding="utf-8")
print("✅ ThreadCard.jsx の ReferenceError を修正しました。")
