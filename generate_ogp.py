import os
from PIL import Image, ImageDraw, ImageFont

# 出力先ディレクトリ
output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend", "public"))
os.makedirs(output_dir, exist_ok=True)

# フォントの設定 (Windows標準フォント「メイリオ ボールド」)
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
    badge_text="京都・大阪・名古屋 市会公開データ × 一次資料検証基盤",
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
    badge_text="京都市会 公式会議録 × 松井市長政策トラッカー",
    title_text="議会のミカタ 京都",
    sub_text="対話がわかる。政策が見える。",
    desc_lines=[
        "京都市会12万件超の発言記録と会派賛否ログを構造化。",
        "「新京都戦略」に基づく主要14施策の予算・条例・マイルストーンを可視化。"
    ],
    filename="ogp-kyoto.png",
    accent_color="#4f46e5"
)

# 3. 大阪専用 OGP (ogp-osaka.png)
create_ogp(
    badge_text="大阪市会 公式会議録 × 横山市長政策トラッカー",
    title_text="議会のミカタ 大阪",
    sub_text="対話がわかる。政策が見える。",
    desc_lines=[
        "大阪市会会議録発言記録と議案採決ログを客観的に構造化。",
        "マニフェスト24重点公約の予算措置・関連条例・成立執行進捗を完全追跡。"
    ],
    filename="ogp-osaka.png",
    accent_color="#0284c7"
)

# 4. 名古屋専用 OGP (ogp-nagoya.png)
create_ogp(
    badge_text="名古屋市会 公式会議録 × 広沢市長政策トラッカー",
    title_text="議会のミカタ 名古屋",
    sub_text="対話がわかる。政策が見える。",
    desc_lines=[
        "名古屋市会公式会議録と電子採決ログを客観的に構造化。",
        "現職68議員の質疑スレッド分析と広沢市長政策トラッカーを完全追跡。"
    ],
    filename="ogp-nagoya.png",
    accent_color="#d97706"  # 名古屋城・金鯱アンバー
)

    # 4. 横浜市版 OGP

if __name__ == "__main__":
    # 1. 京都市版 OGP
    create_ogp(
        badge_text="地方議会オープンデータ基盤",
        title_text="議会のミカタ 京都",
        sub_text="京都市会 公式会議録12万発言 × 松井市長政策トラッカー",
        desc_lines=[
            "AIは入口。判断するのは市民です。",
            "12万件の生発言データと議案採決を客観的に構造化",
            "看板公約と議会質疑・賛否行動の完全照合"
        ],
        filename="ogp-kyoto.png",
        accent_color="#4f46e5"
    )

    # 2. 大阪市版 OGP
    create_ogp(
        badge_text="地方議会オープンデータ基盤",
        title_text="議会のミカタ 大阪",
        sub_text="大阪市会 公式会議録 × 横山市長政策トラッカー",
        desc_lines=[
            "AIは入口。判断するのは市民です。",
            "大阪市会の公式質疑・議案採決ログを客観的に構造化",
            "市長公約の予算化・条例化を一次資料から追跡"
        ],
        filename="ogp-osaka.png",
        accent_color="#0284c7"
    )

    # 3. 名古屋市版 OGP
    create_ogp(
        badge_text="地方議会オープンデータ基盤",
        title_text="議会のミカタ 名古屋",
        sub_text="名古屋市会 公式会議録 × 広沢市長政策トラッカー",
        desc_lines=[
            "AIは入口。判断するのは市民です。",
            "名古屋市会の公式質疑・議案採決ログを客観的に構造化",
            "市長公約の予算化・条例化を一次資料から追跡"
        ],
        filename="ogp-nagoya.png",
        accent_color="#0d9488"
    )

    # 4. 横浜市版 OGP
    create_ogp(
        badge_text="地方議会オープンデータ基盤",
        title_text="議会のミカタ 横浜",
        sub_text="横浜市会 公式会議録 × 原澤新市長政策トラッカー",
        desc_lines=[
            "2026年10月就任・原澤敦美市長の看板公約を一次資料から追跡",
            "横浜市会の公式会議録・賛否分裂議案データを客観的AI分析",
            "AIは入口。判断するのは市民です。"
        ],
        filename="ogp-yokohama.png",
        accent_color="#0ea5e9"
    )
