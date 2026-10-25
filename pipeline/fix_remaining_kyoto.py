from pathlib import Path

components = ["Methodology.jsx", "GuidePage.jsx", "AboutPage.jsx"]

for comp in components:
    p = Path(f"frontend/src/components/{comp}")
    if not p.exists():
        continue
        
    txt = p.read_text(encoding="utf-8")
    
    # 漏れていた箇所をピンポイントで汎用化
    txt = txt.replace("京都市総合計画", "自治体の総合計画")
    txt = txt.replace("京都市政に", "対象自治体の市政に")
    
    p.write_text(txt, encoding="utf-8")

print("✅ 残っていた「京都市総合計画」などの表記を汎用化しました。")
