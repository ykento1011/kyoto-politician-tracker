from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==========================================
# 1. BillDetailModal.jsx の修正
# ==========================================
bdm_path = PROJECT_ROOT / "frontend" / "src" / "components" / "BillDetailModal.jsx"
bdm_text = bdm_path.read_text(encoding="utf-8")

# 引数 props に cityCode を追加
if "cityCode" not in bdm_text.split("export default function BillDetailModal")[1].split("{")[0]:
    bdm_text = re.sub(
        r"export default function BillDetailModal\(\{([^}]+)\}\)",
        r"export default function BillDetailModal({\1, cityCode = 'kyoto'})",
        bdm_text
    )

# 268行目の公式審議結果ページリンクの文言を動的化
old_label = "京都市会 公式審議結果ページを開く"
new_label = "{cityCode === 'osaka' ? '大阪市会 公式審議結果ページを開く' : '京都市会 公式審議結果ページを開く'}"

if old_label in bdm_text:
    bdm_text = bdm_text.replace(old_label, new_label)

bdm_path.write_text(bdm_text, encoding="utf-8")
print("✅ BillDetailModal.jsx の公式リンク表記を修正しました。")

# ==========================================
# 2. App.jsx 内の全 BillDetailModal 呼び出しに cityCode を渡す
# ==========================================
app_path = PROJECT_ROOT / "frontend" / "src" / "App.jsx"
app_text = app_path.read_text(encoding="utf-8")

# cityCode={cityCode} が含まれていない <BillDetailModal をすべて置換
def add_city_code(match):
    tag = match.group(0)
    if "cityCode=" in tag:
        return tag
    return tag.replace("<BillDetailModal", "<BillDetailModal\n          cityCode={cityCode}")

app_text = re.sub(r"<BillDetailModal\b[^>]*", add_city_code, app_text)
app_path.write_text(app_text, encoding="utf-8")
print("✅ App.jsx のすべての BillDetailModal 呼び出しに cityCode を追加しました。")
