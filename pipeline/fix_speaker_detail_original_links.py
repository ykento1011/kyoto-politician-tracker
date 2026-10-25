from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==========================================
# 1. SpeakerDetailView.jsx の原本リンク動的化
# ==========================================
sdv_path = PROJECT_ROOT / "frontend" / "src" / "components" / "SpeakerDetailView.jsx"
sdv_text = sdv_path.read_text(encoding="utf-8")

# 引数 props に cityCode を受け取れるようにする
if "cityCode" not in sdv_text.split("export default function SpeakerDetailView")[1].split("{")[0]:
    sdv_text = re.sub(
        r"export default function SpeakerDetailView\(\{([^}]+)\}\)",
        r"export default function SpeakerDetailView({\1, cityCode = 'kyoto'})",
        sdv_text
    )

# 京都市会 公式原本で確認 のテキスト置換
old_text = "京都市会 公式原本で確認"
new_text = "{cityCode === 'osaka' ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認'}"

sdv_text = sdv_text.replace(old_text, new_text)

# 選挙公報原本のタイトルやリンクも大阪対応（「京都市選挙管理委員会」等がある場合）
sdv_text = sdv_text.replace("京都市選挙管理委員会", "{cityCode === 'osaka' ? '大阪市選挙管理委員会' : '京都市選挙管理委員会'}")

sdv_path.write_text(sdv_text, encoding="utf-8")
print("✅ SpeakerDetailView.jsx の原本表記を修正しました。")

# ==========================================
# 2. App.jsx: SpeakerDetailView 呼び出しに cityCode を渡す
# ==========================================
app_path = PROJECT_ROOT / "frontend" / "src" / "App.jsx"
app_text = app_path.read_text(encoding="utf-8")

if "<SpeakerDetailView" in app_text and "cityCode={cityCode}" not in app_text.split("<SpeakerDetailView")[1].split("/>")[0]:
    app_text = app_text.replace(
        "<SpeakerDetailView",
        "<SpeakerDetailView\n            cityCode={cityCode}"
    )
    app_path.write_text(app_text, encoding="utf-8")
    print("✅ App.jsx の SpeakerDetailView 呼び出しに cityCode を追加しました。")

# ==========================================
# 3. AiSearchAnswer.jsx の原本表記も修正
# ==========================================
ai_path = PROJECT_ROOT / "frontend" / "src" / "components" / "AiSearchAnswer.jsx"
if ai_path.exists():
    ai_text = ai_path.read_text(encoding="utf-8")
    if "cityCode" not in ai_text.split("export default function AiSearchAnswer")[1].split("{")[0]:
        ai_text = re.sub(
            r"export default function AiSearchAnswer\(\{([^}]+)\}\)",
            r"export default function AiSearchAnswer({\1, cityCode = 'kyoto'})",
            ai_text
        )
    ai_text = ai_text.replace("京都市会 公式原本で確認", "{cityCode === 'osaka' ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認'}")
    ai_text = ai_text.replace("京都市会 公式原本", "{cityCode === 'osaka' ? '大阪市会 公式原本' : '京都市会 公式原本'}")
    ai_path.write_text(ai_text, encoding="utf-8")
    print("✅ AiSearchAnswer.jsx の原本表記を修正しました。")

print("\n全原本リンク表記の動的修正が完了しました。")
