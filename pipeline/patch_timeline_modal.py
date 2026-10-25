from pathlib import Path
import re

modal_file = Path("frontend/src/components/TimelineModal.jsx")
text = modal_file.read_text(encoding="utf-8")

# cityCode を props で受け取れるように変更
if "cityCode = 'kyoto'" not in text:
    text = text.replace(
        "export default function TimelineModal({\n  isOpen,\n  onClose,\n  selectedContext,\n  isLoading\n}) {",
        "export default function TimelineModal({\n  isOpen,\n  onClose,\n  selectedContext,\n  isLoading,\n  cityCode = 'kyoto'\n}) {"
    )

# ラベルの動的切り替え
old_label = "<span>京都市会 公式原本で確認</span>"
new_label = "<span>{cityCode === 'osaka' ? '大阪市会' : '京都市会'} 公式原本で確認</span>"
if old_label in text:
    text = text.replace(old_label, new_label)

modal_file.write_text(text, encoding="utf-8")

# App.jsx 側の呼び出し元で cityCode を渡す
app_file = Path("frontend/src/App.jsx")
app_text = app_file.read_text(encoding="utf-8")

app_text = re.sub(
    r'<TimelineModal\s+isOpen=\{isPanelOpen\}',
    '<TimelineModal\n        cityCode={cityCode}\n        isOpen={isPanelOpen}',
    app_text
)

app_file.write_text(app_text, encoding="utf-8")
print("✅ TimelineModal の都市別ラベル対応を完了しました。")
