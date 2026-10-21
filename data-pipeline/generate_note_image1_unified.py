import os
from PIL import Image, ImageDraw, ImageFont

# 1. キャンバスの作成 (1200 x 630 px : note推奨比率)
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
    # 文字を削った分、サイズを大きくして視認性を高める
    font_title = ImageFont.truetype(font_path, 60)
    font_sub = ImageFont.truetype(font_path, 34)
    font_desc = ImageFont.truetype(font_path, 28)
    font_url = ImageFont.truetype(font_path, 24)
except Exception:
    font_badge = font_title = font_sub = font_desc = font_url = ImageFont.load_default()

# 4. 徹底的に短く洗練されたテキスト定義
badge_text = "機能紹介 01 ｜ 言行一致トラッカー"
title_text = "「選挙公報」 × 「議会の議決ログ」"
sub_text = "全67議員の公約実行度を、客観的に可視化。"
desc_text = (
    "抽象的なスローガンではなく、具体的公約を抽出。\n"
    "「口約束」で終わっていないか、一次情報で裏取り可能。"
)
url_text = "https://gikai-no-mikata.jp"

# 5. テキスト描画
# 余白を広くとるため、全体の開始位置(Y座標)を下げる
start_y = 100

# バッジ
badge_x, badge_y = 90, start_y
bbox = draw.textbbox((badge_x, badge_y), badge_text, font=font_badge)
draw.rectangle(
    [bbox[0] - 14, bbox[1] - 8, bbox[2] + 14, bbox[3] + 8],
    fill="#1e1b4b",
    outline="#4338ca",
    width=1,
)
draw.text((badge_x, badge_y), badge_text, fill="#a5b4fc", font=font_badge)

# メインタイトル (1行で短く力強く)
draw.text((90, start_y + 80), title_text, fill="#ffffff", font=font_title)

# サブタイトル / キャッチコピー
draw.text((90, start_y + 200), sub_text, fill="#818cf8", font=font_sub)

# 説明文 (行間を広げる)
draw.multiline_text((90, start_y + 270), desc_text, fill="#cbd5e1", font=font_desc, spacing=16)

# サイトURL
draw.text((90, 520), url_text, fill="#64748b", font=font_url)

# 6. 保存処理
output_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "public")
)
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "note_image1_simplified.png")
image.save(output_path, "PNG")
print(f"画像生成が完了しました: {output_path}")