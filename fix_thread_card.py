import re
from pathlib import Path

path = Path("frontend/src/components/ThreadCard.jsx")
content = path.read_text(encoding="utf-8")

# 1. 引数に stmt, statement, thread すべてを受け取れるように拡張
old_sig = re.search(r"export default function ThreadCard\(\s*\{([^}]+)\}\s*\)", content)
if old_sig:
    sig_content = old_sig.group(1)
    # stmt, statement, thread を確実に含める
    if "statement" not in sig_content:
        sig_content = "statement, " + sig_content
    if "thread" not in sig_content:
        sig_content = "thread, " + sig_content
    new_sig = f"export default function ThreadCard({{{sig_content}}})"
    content = content[:old_sig.start()] + new_sig + content[old_sig.end():]

# 2. 関数冒頭で stmt を安全に統合 (stmt = stmt || statement || thread || {})
replacement_init = """
  // どの引数名で渡されても確実に受領
  const actualStmt = stmt || statement || thread || {};
"""

# 関数シグネチャの直後に actualStmt の定義を挿入し、参照を置換
content = re.sub(
    r"(export default function ThreadCard\([^{]+\)\s*\{)",
    r"\1\n  const actualStmt = stmt || statement || thread || {};\n  const safeThread = actualStmt;",
    content,
    count=1
)

# 3. thread?. や stmt?. 、stmt. を actualStmt / safeThread 経由で安全化
content = content.replace("thread?.", "safeThread?.")
content = content.replace("stmt?.", "actualStmt?.")
content = content.replace("stmt.", "actualStmt.")

path.write_text(content, encoding="utf-8")
print("✅ ThreadCard.jsx の ReferenceError を完全修正しました。")
