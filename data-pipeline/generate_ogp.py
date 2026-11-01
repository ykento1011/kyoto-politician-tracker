import os
from PIL import Image, ImageDraw, ImageFont

# 出力先ディレクトリ (data-pipeline から親ディレクトリを経由して frontend/public を解決)
base_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(base_dir) == "data-pipeline":
    output_dir = os.path.abspath(os.path.join(base_dir, "..", "frontend", "public"))
else:
    output_dir = os.path.abspath(os.path.join(base_dir, "frontend", "public"))

os.makedirs(output_dir, exist_ok=True)

# フォントの設定 (Windows標準フォント)
font_path = "C:\\Windows\\Fonts\\meiryob.ttc"
if not os.path.exists(font_path):
    font_path = "C:\\Windows\\Fonts\\msgothic.ttc"

try:
    font_badge = ImageFont.truetype(font_path, 24)
    font_title = ImageFont.truetype(font_path, 66)
    font_sub = ImageFont.truetype(font_path, 32)
    font_desc = ImageFont.truetype(font_path, 26)
    font_url = ImageFont.truetype(font_path, 22)
except Exception:
    font_badge = font_title = font_sub = font_desc = font_url = ImageFont.load_default()

def create_ogp(badge_text, title_text, sub_text, desc_lines, filename, accent_color="#6366f1"):
    width, height = 1200, 630
    image = Image.new("RGB", (width, height), "#0f172a") # Slate-900
    draw = ImageDraw.Draw(image)

    # 外枠
    draw.rectangle([20, 20, width - 20, height - 20], outline="#334155", width=2)
    # 左端のアクセントカラー帯
    draw.rectangle([40, 40, 56, height - 40], fill=accent_color)

    # バッジ
    badge_x, badge_y = 105, 95
    bbox = draw.textbbox((badge_x, badge_y), badge_text, font=font_badge)
    draw.rectangle(
        [bbox[0] - 14, bbox[1] - 8, bbox[2] + 14, bbox[3] + 8],
        fill="#1e1b4b",
        outline="#4338ca",
        width=1
    )
    draw.text((badge_x, badge_y), badge_text, fill="#a5b4fc", font=font_badge)

    # メインタイトル
    draw.text((90, 170), title_text, fill="#ffffff", font=font_title)

    # サブタイトル / キャッチコピー
    draw.text((90, 270), sub_text, fill="#818cf8", font=font_sub)

    # 概要説明文
    draw.multiline_text((90, 350), "\n".join(desc_lines), fill="#cbd5e1", font=font_desc, spacing=14)

    # 右下ドメイン表示
    draw.text((90, 525), "https://gikai-mikata.jp", fill="#64748b", font=font_url)

    # 保存
    target_path = os.path.join(output_dir, filename)
    image.save(target_path, "PNG")
    print(f"✅ 生成完了: {target_path}")

# 1. メイン総合 OGP (ogp.png)
create_ogp(
    badge_text="5大政令市（京都・大阪・名古屋・横浜・神戸）公開データ × 一次資料検証基盤",
    title_text="議会のミカタ",
    sub_text="AIは入口。判断するのは市民です。",
    desc_lines=[
        "市会公式会議録の発言ログと全議員の採決スタンスを客観的に構造化。",
        "市長公約の公式計画化・予算計上・条例制定・施行進捗を、",
        "自治体公文書原本リンクとともに市民自ら検証できるオープンデータ基盤。"
    ],
    filename="ogp.png",
    accent_color="#6366f1"
)

# 2. 京都専用 OGP (ogp-kyoto.png)
create_ogp(
    badge_text="京都市会 公式会議録 × 市長政策トラッカー",
    title_text="議会のミカタ 京都",
    sub_text="対話がわかる。政策が見える。",
    desc_lines=[
        "京都市会12万件超の発言記録と会派賛否ログを構造化。",
        "基本計画に基づく主要施策の予算・条例・マイルストーン進捗を可視化。"
    ],
    filename="ogp-kyoto.png",
    accent_color="#4f46e5"
)

# 3. 大阪専用 OGP (ogp-osaka.png)
create_ogp(
    badge_text="大阪市会 公式会議録 × 市長政策トラッカー",
    title_text="議会のミカタ 大阪",
    sub_text="対話がわかる。政策が見える。",
    desc_lines=[
        "大阪市会会議録発言記録と議案採決ログを客観的に構造化。",
        "マニフェスト重点公約の予算措置・関連条例・成立執行進捗を完全追跡。"
    ],
    filename="ogp-osaka.png",
    accent_color="#0284c7"
)

# 4. 名古屋専用 OGP (ogp-nagoya.png)
create_ogp(
    badge_text="名古屋市会 公式会議録 × 市長政策トラッカー",
    title_text="議会のミカタ 名古屋",
    sub_text="対話がわかる。政策が見える。",
    desc_lines=[
        "名古屋市会公式会議録と電子採決ログを客観的に構造化。",
        "現職議員の質疑スレッド分析と市長政策トラッカーを完全追跡。"
    ],
    filename="ogp-nagoya.png",
    accent_color="#d97706"
)

# 5. 横浜専用 OGP (ogp-yokohama.png)
create_ogp(
    badge_text="横浜市会 公式会議録 × 市長政策トラッカー",
    title_text="議会のミカタ 横浜",
    sub_text="対話がわかる。政策が見える。",
    desc_lines=[
        "横浜市会会議録発言記録と常任委員会・本会議採決ログを客観的に構造化。",
        "市政重点計画・重要政策の予算・条例・執行状況を完全追跡。"
    ],
    filename="ogp-yokohama.png",
    accent_color="#2563eb"
)

# 6. 神戸専用 OGP (ogp-kobe.png)
create_ogp(
    badge_text="神戸市会 公式会議録 × 市長政策トラッカー",
    title_text="議会のミカタ 神戸",
    sub_text="対話がわかる。政策が見える。",
    desc_lines=[
        "神戸市会本会議・予算決算委員会会議録と採決ログを客観的に構造化。",
        "基本計画に基づく重点施策の予算計上・マイルストーンを可視化。"
    ],
    filename="ogp-kobe.png",
    accent_color="#0d9488"
)
