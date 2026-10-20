import os
from PIL import Image, ImageDraw, ImageFont

# 1. キャンバスの作成 (1200 x 630 px : note見出し推奨比率)
width, height = 1200, 630
image = Image.new("RGB", (width, height), "#0f172a")  # Slate-900 (洗練された濃紺)
draw = ImageDraw.Draw(image)

# 2. 装飾枠・アクセントバー
# 外枠
draw.rectangle([20, 20, width - 20, height - 20], outline="#334155", width=2)
# 左端のアクセントカラー帯 (Indigo)
draw.rectangle([40, 40, 56, height - 40], fill="#6366f1")

# 3. フォント設定 (Windows標準フォント)
font_path = "C:\\Windows\\Fonts\\meiryob.ttc"  # メイリオ ボールド
if not os.path.exists(font_path):
    font_path = "C:\\Windows\\Fonts\\msgothic.ttc"

try:
    font_badge = ImageFont.truetype(font_path, 24)
    font_title = ImageFont.truetype(font_path, 66)
    font_sub = ImageFont.truetype(font_path, 34)
    font_desc = ImageFont.truetype(font_path, 26)
    font_url = ImageFont.truetype(font_path, 24)
except Exception:
    font_badge = font_title = font_sub = font_desc = font_url = (
        ImageFont.load_default()
    )

# 4. テキスト定義
badge_text = "新機能 ｜ 32大政策タイムライン ＆ 原本直リンク"
title_text = "議会のミカタ 京都"
sub_text = "「あの政策、今どうなってる？」を5秒で可視化。"
desc_text = (
    "市バス混雑・空き家税・全員制給食など32大政策の議論変遷をAIでタイムライン化。\n"
    "要約から京都市会公式サーバーの原本へワンクリックで直結、一次情報で追跡可能に。"
)
url_text = "https://gikai-mikata.jp"

# 5. テキスト描画
# バッジ（文字幅に合わせて枠を自動計算）
badge_x, badge_y = 90, 85
bbox = draw.textbbox((badge_x, badge_y), badge_text, font=font_badge)
draw.rectangle(
    [bbox[0] - 14, bbox[1] - 8, bbox[2] + 14, bbox[3] + 8],
    fill="#1e1b4b",
    outline="#4338ca",
    width=1,
)
draw.text((badge_x, badge_y), badge_text, fill="#a5b4fc", font=font_badge)

# メインタイトル
draw.text((90, 160), title_text, fill="#ffffff", font=font_title)

# サブタイトル / キャッチコピー
draw.text((90, 260), sub_text, fill="#818cf8", font=font_sub)

# 説明文
draw.multiline_text((90, 335), desc_text, fill="#cbd5e1", font=font_desc, spacing=14)

# サイトURL
draw.text((90, 520), url_text, fill="#64748b", font=font_url)

# 6. 保存処理（note見出し画像としてのみ書き出し、ogp.png は変更しない）
output_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "public")
)
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "note_header_timeline.png")
image.save(output_path, "PNG")
print(f"note用の見出し画像を生成しました（サイトのOGPには影響しません）: {output_path}")