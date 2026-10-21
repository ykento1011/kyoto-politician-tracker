import os
from PIL import Image, ImageDraw, ImageFont

# キャンバスサイズ (800 x 800 px : 高解像度・X推奨)
size = 800

# フォント設定 (Windows標準のメイリオ ボールド)
font_path = "C:\\Windows\\Fonts\\meiryob.ttc"
if not os.path.exists(font_path):
    font_path = "C:\\Windows\\Fonts\\msgothic.ttc"

try:
    # タイムラインの極小表示でも潰れない極太・特大フォント
    font_main = ImageFont.truetype(font_path, 150)
    font_sub = ImageFont.truetype(font_path, 70)
except Exception:
    font_main = font_sub = ImageFont.load_default()

output_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "public")
)
os.makedirs(output_dir, exist_ok=True)

# ========================================================
# パターンA: インディゴ・公式ブランド版 (視認性最強)
# ========================================================
img_a = Image.new("RGB", (size, size), "#4338ca")  # Indigo-700
draw_a = ImageDraw.Draw(img_a)

# テキスト定義
text_line1 = "議会の"
text_line2 = "ミカタ"

# 中央揃えで描画 (丸型トリミングの内側に配置)
bbox1 = draw_a.textbbox((0, 0), text_line1, font=font_main)
bbox2 = draw_a.textbbox((0, 0), text_line2, font=font_main)

w1, h1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]
w2, h2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]

# 2行の合計高さと間隔
spacing = 20
total_h = h1 + h2 + spacing
start_y = (size - total_h) // 2 - 20

# 描画
x1 = (size - w1) // 2
y1 = start_y
draw_a.text((x1, y1), text_line1, fill="#ffffff", font=font_main)

x2 = (size - w2) // 2
y2 = y1 + h1 + spacing
draw_a.text((x2, y2), text_line2, fill="#ffffff", font=font_main)

path_a = os.path.join(output_dir, "x_profile_icon_indigo.png")
img_a.save(path_a, "PNG")
print(f"パターンA生成完了: {path_a}")


# ========================================================
# パターンB: ダークテーマ・サイト統一版 (OGP同系色)
# ========================================================
img_b = Image.new("RGB", (size, size), "#0f172a")  # Slate-900
draw_b = ImageDraw.Draw(img_b)

# 中央にfavicon風の角丸スクエア枠
box_padding = 90
draw_b.rounded_rectangle(
    [box_padding, box_padding, size - box_padding, size - box_padding],
    radius=140,
    fill="#1e1b4b",  # 深いIndigo
    outline="#6366f1",  # 鮮やかなIndigo境界線
    width=6,
)

# 描画
draw_b.text((x1, y1), text_line1, fill="#ffffff", font=font_main)
draw_b.text((x2, y2), text_line2, fill="#818cf8", font=font_main)

path_b = os.path.join(output_dir, "x_profile_icon_dark.png")
img_b.save(path_b, "PNG")
print(f"パターンB生成完了: {path_b}")