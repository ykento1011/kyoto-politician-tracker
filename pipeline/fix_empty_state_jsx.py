from pathlib import Path
import re

p = Path("frontend/src/components/SearchResultsView.jsx")
if p.exists():
    txt = p.read_text(encoding="utf-8")
    
    # 消えてしまった <strong> タグを正しい位置（「本市の予算〜」の前）に復元
    txt = re.sub(
        r"例えば、国や都道府県の管轄であり、本市の予算や権限が直接及ばないテーマは([^<]*)</strong>",
        r"例えば、国や都道府県の管轄であり、<strong>本市の予算や権限が直接及ばないテーマは\1</strong>",
        txt
    )
    
    p.write_text(txt, encoding="utf-8")
    print("✅ SearchResultsView.jsx の欠落した <strong> タグを復元しました。")
