import os
from PIL import Image, ImageDraw, ImageFont

# 1. キャンバスの作成 (1200 x 630 px)
width, height = 1200, 630
image = Image.new("RGB", (width, height), "#0f172a") # Slate-900 (洗練された濃紺)
draw = ImageDraw.Draw(image)

# 2. 背景にアクセントのグラデーション/装飾枠を描画
# 外枠
draw.rectangle([20, 20, width - 20, height - 20], outline="#334155", width=2)
# 左端のアクセントカラー帯 (Indigo)
draw.rectangle([40, 40, 56, height - 40], fill="#6366f1")

# 3. フォントの設定 (Windows標準フォント「メイリオ」を使用)
font_path = "C:\\Windows\\Fonts\\meiryob.ttc"  # メイリオ ボールド
if not os.path.exists(font_path):
    font_path = "C:\\Windows\\Fonts\\msgothic.ttc" # 代替: MSゴシック

try:
    font_badge = ImageFont.truetype(font_path, 26)
    font_title = ImageFont.truetype(font_path, 68)
    font_sub = ImageFont.truetype(font_path, 34)
    font_desc = ImageFont.truetype(font_path, 28)
    font_url = ImageFont.truetype(font_path, 24)
except Exception:
    font_badge = font_title = font_sub = font_desc = font_url = ImageFont.load_default()

# 4. テキストの描画
# バッジ（カテゴリ）
draw.rectangle([90, 90, 430, 140], fill="#1e1b4b", outline="#4338ca", width=1)
draw.text((105, 98), "京都市会 公開データ × 生成AI", fill="#a5b4fc", font=font_badge)

# タイトル
draw.text((90, 175), "議会のミカタ 京都", fill="#ffffff", font=font_title)

# サブタイトル / キャッチコピー
draw.text((90, 275), "対話がわかる。政策が見える。", fill="#818cf8", font=font_sub)

# サービス説明文
desc_text = (
    "京都市議会12万件超の発言記録をAIで構造化。\n"
    "議員の質疑アプローチ・注力政策・議案賛否スタンスを客観的に可視化します。"
)
draw.multiline_text((90, 360), desc_text, fill="#cbd5e1", font=font_desc, spacing=14)

# 右下ドメイン表示
draw.text((90, 520), "https://gikai-mikata.jp", fill="#64748b", font=font_url)

# 5. frontend/public/ogp.png として保存
output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "public"))
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "ogp.png")

image.save(output_path, "PNG")
print(f"OGP画像を正常に生成・配置しました: {output_path}")