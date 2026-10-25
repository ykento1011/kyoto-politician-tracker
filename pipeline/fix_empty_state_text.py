from pathlib import Path
import glob

components_dir = Path("frontend/src/components")
modified_files = []

for p in components_dir.glob("*.jsx"):
    txt = p.read_text(encoding="utf-8")
    original_txt = txt
    
    # 1. 議会名の汎用化
    txt = txt.replace("京都市議会の現任期", "本議会の現任期")
    txt = txt.replace("京都市会の現任期", "本議会の現任期")
    
    # 2. 京都御所などの固有例え話の汎用化
    old_example = "例えば「京都御所」や「京都御苑」は環境省など国の管轄であり、京都市の予算や権限が直接及ばないテーマは"
    new_example = "例えば、国や都道府県の管轄であり、本市の予算や権限が直接及ばないテーマは"
    txt = txt.replace(old_example, new_example)

    # 万が一改行などで一致しなかった場合の保険置換
    if "京都御所" in txt or "京都御苑" in txt:
        import re
        txt = re.sub(
            r"例えば「京都御所」や「京都御苑」は.*?京都市の予算や権限が直接及ばないテーマは",
            "例えば、国や都道府県の管轄であり、本市の予算や権限が直接及ばないテーマは",
            txt,
            flags=re.DOTALL
        )

    if txt != original_txt:
        p.write_text(txt, encoding="utf-8")
        modified_files.append(p.name)

if modified_files:
    print(f"✅ 以下のファイルの京都固有テキストを汎用化しました: {', '.join(modified_files)}")
else:
    print("⚠️ 該当するテキストが見つかりませんでした。すでに修正されているか、別のコンポーネントにある可能性があります。")
