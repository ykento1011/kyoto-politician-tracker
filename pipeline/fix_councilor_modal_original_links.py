from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==========================================
# 1. CouncilorDetailModal.jsx の原本リンク動的化
# ==========================================
modal_path = PROJECT_ROOT / "frontend" / "src" / "components" / "CouncilorDetailModal.jsx"
modal_text = modal_path.read_text(encoding="utf-8")

# props に cityCode を受け取れるようにする
if "cityCode" not in modal_text.split("export default function CouncilorDetailModal")[1].split("{")[0]:
    modal_text = re.sub(
        r"export default function CouncilorDetailModal\(\{([^}]+)\}\)",
        r"export default function CouncilorDetailModal({\1, cityCode = 'kyoto'})",
        modal_text
    )

# 京都市会 公式原本で確認 を動的ラベルに置換
old_label = "京都市会 公式原本で確認"
new_label = "{cityCode === 'osaka' ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認'}"

modal_text = modal_text.replace(f"<span>{old_label}</span>", f"<span>{new_label}</span>")
modal_text = modal_text.replace(old_label, new_label)

modal_path.write_text(modal_text, encoding="utf-8")
print("✅ CouncilorDetailModal.jsx の原本表記を修正しました。")

# ==========================================
# 2. App.jsx から CouncilorDetailModal に cityCode を渡す
# ==========================================
app_path = PROJECT_ROOT / "frontend" / "src" / "App.jsx"
app_text = app_path.read_text(encoding="utf-8")

if "<CouncilorDetailModal" in app_text and "cityCode={cityCode}" not in app_text.split("<CouncilorDetailModal")[1].split("/>")[0]:
    app_text = app_text.replace(
        "<CouncilorDetailModal",
        "<CouncilorDetailModal\n            cityCode={cityCode}"
    )
    app_path.write_text(app_text, encoding="utf-8")
    print("✅ App.jsx の CouncilorDetailModal 呼び出しに cityCode を渡しました。")

# ==========================================
# 3. 他のモーダル・コンポーネント（ContextViewModal等）も一括検査・修正
# ==========================================
for p in (PROJECT_ROOT / "frontend" / "src" / "components").glob("*.jsx"):
    txt = p.read_text(encoding="utf-8")
    if "京都市会 公式原本" in txt:
        print(f"ℹ️ {p.name} にも原本テキストを検知。動的置換します。")
        txt = re.sub(
            r"京都市会\s*公式原本で確認",
            "{cityCode === 'osaka' ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認'}",
            txt
        )
        p.write_text(txt, encoding="utf-8")
