import os
from PIL import Image, ImageDraw, ImageFont

# 1. キャンバスの作成 (1200 x 630 px)
width, height = 1200, 630
image = Image.new("RGB", (width, height), "#0f172a") # Slate-900 (洗練された濃紺)
draw = ImageDraw.Draw(image)

# 2. 背景にアクセントのグラデーション/装飾枠を描画
# 外枠
draw.rectangle([20, 20, width - 20, height - 20], outline="#334155", width=2)
# 左端のアクセントカラー帯 (Emerald - 大阪用)
draw.rectangle([40, 40, 56, height - 40], fill="#10b981") 

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
# バッジ（カテゴリ）の背景枠を文字幅に合わせて自動調整
badge_text = "大阪市会 公開データ × 生成AI"
badge_x, badge_y = 105, 98

# textbboxで実際の文字幅を取得し、左右に15px、上下に10pxの余白を足して枠を描画
bbox = draw.textbbox((badge_x, badge_y), badge_text, font=font_badge)
draw.rectangle(
    [bbox[0] - 15, bbox[1] - 10, bbox[2] + 15, bbox[3] + 10], 
    fill="#064e3b", # Emerald系ダーク
    outline="#059669", # Emerald系
    width=1
)
draw.text((badge_x, badge_y), badge_text, fill="#6ee7b7", font=font_badge) # Emerald系ライト

# タイトル
draw.text((90, 175), "議会のミカタ 大阪", fill="#ffffff", font=font_title)

# サブタイトル / キャッチコピー
draw.text((90, 275), "対話がわかる。政策が見える。", fill="#34d399", font=font_sub) # Emerald系

# サービス説明文
desc_text = (
    "大阪市会・全1,260超の質疑スレッドと市長政策トラッカーを客観的に構造化。\n"
    "議員の政策対話と公約の進捗を、市民が自ら一次情報で検証できます。"
)
draw.multiline_text((90, 360), desc_text, fill="#cbd5e1", font=font_desc, spacing=14)

# 右下ドメイン表示
draw.text((90, 520), "https://gikai-mikata.jp/osaka", fill="#64748b", font=font_url)

# 5. frontend/public/osaka/ogp.png として保存
# スクリプトの実行場所を基準に保存先のパスを構築
output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "osaka"))
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "ogp.png")

image.save(output_path, "PNG")
print(f"OGP画像を正常に生成・配置しました: {output_path}")