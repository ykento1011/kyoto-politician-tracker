from pathlib import Path

components = ["Methodology.jsx", "GuidePage.jsx", "AboutPage.jsx"]

replacements = [
    # Methodology.jsx の漏れ
    ("市会議決・会議録: 京都市会 公式会議録および議決結果一覧", "議会議決・会議録: 対象議会の公式会議録および議決結果一覧"),
    
    # GuidePage.jsx の漏れ
    ("市長公約が市の最上位計画である『新京都戦略』に正式に位置づけられているか", "首長公約が自治体の最上位計画に正式に位置づけられているか"),
    ("京都市会の会議録原本、行財政局の主要事業説明書PDF", "対象議会の会議録原本、行財政担当部局の主要事業説明書PDF"),
    
    # その他、念のための表記揺れカバー
    ("京都市会の会議録原本", "対象議会の会議録原本"),
    ("京都市会 公式会議録", "対象議会の公式会議録"),
    ("行財政局の", "行財政担当部局の")
]

for comp in components:
    p = Path(f"frontend/src/components/{comp}")
    if p.exists():
        txt = p.read_text(encoding="utf-8")
        for old, new in replacements:
            txt = txt.replace(old, new)
        p.write_text(txt, encoding="utf-8")

print("✅ 残存していた「京都市会」「新京都戦略」「行財政局」などの固有表現を汎用化しました。")
