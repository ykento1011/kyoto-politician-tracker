from pathlib import Path

for p in Path("frontend/src/components").glob("*.jsx"):
    txt = p.read_text(encoding="utf-8")
    if "（Contested Bills）" in txt:
        # カッコ書きを削除
        txt = txt.replace("（Contested Bills）", "")
        p.write_text(txt, encoding="utf-8")
        
print("✅ 「（Contested Bills）」のカッコ書きを削除しました。")
