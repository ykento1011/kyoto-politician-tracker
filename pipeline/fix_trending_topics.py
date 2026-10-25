from pathlib import Path

modified_files = []

# フロントエンドの全JSXファイルをスキャンして、0件になるサジェストキーワードを議会用語に置き換える
for p in Path("frontend/src").rglob("*.jsx"):
    txt = p.read_text(encoding="utf-8")
    original = txt
    
    # 略称から、実際にヒットする「正式用語の空白（AND）検索」へ置換
    txt = txt.replace("国保料府内統一", "国民健康保険 統一")
    txt = txt.replace("学校熱中症対策", "学校 熱中症")
    
    if txt != original:
        p.write_text(txt, encoding="utf-8")
        modified_files.append(p.name)

if modified_files:
    print(f"✅ 以下のファイルのサジェストキーワードを確実にヒットする言葉へ修正しました: {', '.join(modified_files)}")
else:
    print("⚠️ 該当するキーワードが見つかりませんでした。")
