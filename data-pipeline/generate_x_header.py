import os
from PIL import Image, ImageDraw, ImageFont

# 1. キャンバス作成 (X公式推奨: 1500 x 500 px)
width, height = 1500, 500
image = Image.new("RGB", (width, height), "#0f172a")  # Slate-900
draw = ImageDraw.Draw(image)

# 2. 外枠装飾
draw.rectangle([15, 15, width - 15, height - 15], outline="#334155", width=2)

# 3. フォント設定 (Windows標準フォント)
font_path = "C:\\Windows\\Fonts\\meiryob.ttc"  # メイリオ ボールド
if not os.path.exists(font_path):
    font_path = "C:\\Windows\\Fonts\\msgothic.ttc"

try:
    font_badge = ImageFont.truetype(font_path, 20)
    font_title = ImageFont.truetype(font_path, 54)
    font_sub = ImageFont.truetype(font_path, 26)
    font_features = ImageFont.truetype(font_path, 20)
    font_url = ImageFont.truetype(font_path, 22)
except Exception:
    font_badge = font_title = font_sub = font_features = font_url = ImageFont.load_default()

# 4. アイコン重複回避設計
# 左下(横0〜360px、縦250〜500px)は丸アイコンが被るため、主要テキストの開始X座標を 380px に設定
start_x = 380

# --- バッジ ---
badge_text = "京都市会 公開データ × 生成AI ｜ 独立系シビックテック基盤"
badge_y = 65
bbox = draw.textbbox((start_x, badge_y), badge_text, font=font_badge)
draw.rectangle(
    [bbox[0] - 12, bbox[1] - 6, bbox[2] + 12, bbox[3] + 6],
    fill="#1e1b4b",
    outline="#4338ca",
    width=1,
)
draw.text((start_x, badge_y), badge_text, fill="#a5b4fc", font=font_badge)

# --- メインタイトル ---
title_text = "議会のミカタ 京都"
draw.text((start_x, 125), title_text, fill="#ffffff", font=font_title)

# --- キャッチコピー ---
sub_text = "「対話がわかる。政策が見える。」"
draw.text((start_x, 205), sub_text, fill="#818cf8", font=font_sub)

# --- 2大トラッカー特徴 ---
f1_text = "● 全67議員 言行一致トラッカー（選挙公報原本 ⇄ 議決・質疑ログ）"
f2_text = "● 松井市長 政策進捗トラッカー（新京都戦略 ⇄ 予算書定量データ）"

draw.text((start_x, 265), f1_text, fill="#cbd5e1", font=font_features)
draw.text((start_x, 305), f2_text, fill="#cbd5e1", font=font_features)

# --- 境界線 ＆ 正式URL ---
draw.line([(start_x, 360), (width - 60, 360)], fill="#1e293b", width=1)

url_text = "https://gikai-mikata.jp"
draw.text((start_x, 385), url_text, fill="#94a3b8", font=font_url)

sub_note = "※特定の政党・団体とは無関係の独立した客観データプロジェクトです"
draw.text((start_x, 420), sub_note, fill="#64748b", font=font_badge)

# 5. 保存処理
output_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "public")
)
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "x_header_official.png")
image.save(output_path, "PNG")
print(f"X用ヘッダー画像を再生成しました: {output_path}")