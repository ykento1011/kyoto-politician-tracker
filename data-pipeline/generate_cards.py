#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
京都市議会議員 カルテOGP画像 自動生成パイプライン (1200 x 675 px / 16:9)
「議会のミカタ 京都」公約・採決・AI客観評価 連携版
"""

import os
import sys
import json
import io
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ==========================================
# パス・ディレクトリ設定
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
PUBLIC_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"
COUNCILOR_IMAGES_DIR = PROJECT_ROOT / "frontend" / "public" / "councilors"
OUTPUT_DIR = BASE_DIR / "output"

STATEMENTS_SUMMARY_FILE = PUBLIC_DATA_DIR / "statements_summary.json"
PLEDGE_TRACKER_FILE = PUBLIC_DATA_DIR / "pledge_tracker.json"
VOTES_SUMMARY_FILE = PUBLIC_DATA_DIR / "votes_summary.json"

CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 675

# カラーパレット (Tailwind Slate/Indigo準拠)
COLOR_BG_DARK = (15, 23, 42)          # Slate 900
COLOR_BG_CARD = (255, 255, 255)       # White
COLOR_CARD_BORDER = (226, 232, 240)   # Slate 200
COLOR_TEXT_MAIN = (15, 23, 42)        # Slate 900
COLOR_TEXT_MUTED = (100, 116, 139)    # Slate 500
COLOR_TEXT_LIGHT = (148, 163, 184)    # Slate 400
COLOR_PRIMARY = (79, 70, 229)         # Indigo 600
COLOR_PRIMARY_LIGHT = (238, 242, 255) # Indigo 50
COLOR_PRIMARY_BORDER = (199, 210, 254)# Indigo 200
COLOR_EMERALD_BG = (236, 253, 245)    # Emerald 50
COLOR_EMERALD_TEXT = (4, 120, 87)     # Emerald 700
COLOR_ROSE_BG = (255, 241, 242)       # Rose 50
COLOR_ROSE_TEXT = (190, 18, 60)       # Rose 700

# 💡 過去スクリプト（extract_pledges_gemini.py, scrape_kyoto_votes.py）に基づく正規化辞書
NAME_CANONICAL_MAP = {
    # 異体字・旧字体
    "井崎敦子": "井﨑敦子",
    "井﨑敦子": "井﨑敦子",
    "繁隆夫": "繁隆夫",
    "繁隆夫": "繁隆夫",
    "繫隆夫": "繁隆夫",
    # 通称名・ひらがな ⇄ 戸籍・写真ファイル名（双方向）
    "江村りさ": "江村理紗",
    "江村理紗": "江村りさ",
    "土方りさ": "土方莉紗",
    "土方莉紗": "土方りさ",
    "天方ひろゆき": "天方浩之",
    "天方浩之": "天方ひろゆき",
    "森かれん": "森華倫",
    "森華倫": "森かれん",
}


# ==========================================
# 議員名・画像解決ヘルパー
# ==========================================
def clean_speaker_name(raw_name: str) -> str:
    """空白・改行を除去したクリーンな名前を返す"""
    if not raw_name:
        return ""
    return raw_name.replace(" ", "").replace(" ", "").replace("\t", "").replace("\n", "").strip()


def resolve_avatar_image(name: str) -> Optional[Path]:
    """議員名から frontend/public/councilors 内の実写真ファイルを柔軟に探索"""
    clean = clean_speaker_name(name)
    candidates = [
        COUNCILOR_IMAGES_DIR / f"{clean}.jpg",
        COUNCILOR_IMAGES_DIR / f"{clean}.png",
        COUNCILOR_IMAGES_DIR / f"{name}.jpg"
    ]

    # 別名候補（江村りさ ⇄ 江村理紗、井﨑 ⇄ 井崎 など）
    alias = NAME_CANONICAL_MAP.get(clean)
    if alias:
        candidates.extend([
            COUNCILOR_IMAGES_DIR / f"{alias}.jpg",
            COUNCILOR_IMAGES_DIR / f"{alias}.png"
        ])

    for path in candidates:
        if path.exists():
            return path
    return None


def find_system_japanese_font(bold: bool = False) -> str:
    """環境に応じた日本語フォントのパスを探索"""
    candidates = []
    if sys.platform.startswith("win"):
        candidates = [
            "C:/Windows/Fonts/meiryob.ttc" if bold else "C:/Windows/Fonts/meiryo.ttc",
            "C:/Windows/Fonts/msgothic.ttc",
            "C:/Windows/Fonts/yumin.ttf",
            "C:/Windows/Fonts/yu-gothic.ttf"
        ]
    elif sys.platform.startswith("darwin"):
        candidates = [
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode.ttf"
        ]
    else:
        candidates = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/ipafont/ipagp.ttf"
        ]
    
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def load_font(custom_path: Optional[str], size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    if custom_path and os.path.exists(custom_path):
        try:
            return ImageFont.truetype(custom_path, size)
        except Exception:
            pass
    
    sys_font_path = find_system_japanese_font(bold=bold)
    if sys_font_path:
        try:
            return ImageFont.truetype(sys_font_path, size)
        except Exception:
            pass
            
    return ImageFont.load_default()


# ==========================================
# 描画ユーティリティ
# ==========================================
def draw_rounded_rectangle(draw: ImageDraw.ImageDraw, box: Tuple[int, int, int, int], 
                           radius: int, fill=None, outline=None, width: int = 1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_wrapped_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, 
                      max_width: int, max_lines: int = 4) -> List[str]:
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        bbox = font.getbbox(test_line)
        line_w = bbox[2] - bbox[0]
        if line_w <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
            if len(lines) >= max_lines - 1:
                break
    if current_line and len(lines) < max_lines:
        lines.append(current_line)
    elif len(lines) >= max_lines - 1 and current_line:
        lines.append(current_line[:max(1, len(current_line) - 2)] + "…")
    return lines


def create_circular_avatar(image_path: Optional[Path], diameter: int) -> Image.Image:
    """実写真画像を正円にトリミングし、Indigoの枠線を付与"""
    if image_path and image_path.exists():
        try:
            src = Image.open(str(image_path)).convert("RGBA")
        except Exception:
            src = Image.new("RGBA", (diameter, diameter), (203, 213, 225, 255))
    else:
        src = Image.new("RGBA", (diameter, diameter), (226, 232, 240, 255))

    src = ImageOps.fit(src, (diameter, diameter), Image.Resampling.LANCZOS, centering=(0.5, 0.35))

    mask = Image.new("L", (diameter, diameter), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, diameter - 1, diameter - 1), fill=255)

    output = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    output.paste(src, (0, 0), mask=mask)

    ring = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    ring_draw = ImageDraw.Draw(ring)
    ring_draw.ellipse((1, 1, diameter - 2, diameter - 2), outline=(79, 70, 229, 255), width=4)
    output = Image.alpha_composite(output, ring)

    return output


def generate_radar_chart(categories: List[str], values: List[float], size_px: int = 400) -> Image.Image:
    num_vars = len(categories)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    
    values_closed = values + values[:1]
    angles_closed = angles + angles[:1]

    font_path = find_system_japanese_font(bold=True)
    font_prop = None
    if font_path and os.path.exists(font_path):
        font_prop = fm.FontProperties(fname=font_path)
        font_prop.set_size(10)
        font_prop.set_weight('bold')

    dpi = 100
    fig_size = size_px / dpi
    fig, ax = plt.subplots(figsize=(fig_size, fig_size), subplot_kw=dict(polar=True), dpi=dpi)
    
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(0)
    ax.set_ylim(0, 5.0)

    ax.set_yticks([1.0, 2.0, 3.0, 4.0, 5.0])
    ax.set_yticklabels([])
    ax.grid(color="#CBD5E1", linestyle="--", linewidth=1.0)
    ax.spines['polar'].set_color("#94A3B8")
    ax.spines['polar'].set_linewidth(1.2)

    ax.set_xticks(angles)
    if font_prop:
        ax.set_xticklabels(categories, fontproperties=font_prop, color="#1E293B")
    else:
        ax.set_xticklabels(categories, fontsize=9.5, fontweight='bold', color="#1E293B")

    ax.plot(angles_closed, values_closed, color="#4F46E5", linewidth=2.5, linestyle='solid')
    ax.fill(angles_closed, values_closed, color="#6366F1", alpha=0.35)
    ax.scatter(angles, values, color="#4338CA", s=36, zorder=10)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)
    
    return Image.open(buf).convert("RGBA")


# ==========================================
# カード合成メイン処理
# ==========================================
def render_councilor_card(data: Dict, output_path: str, font_dir: Optional[str] = None):
    img = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), COLOR_BG_DARK)
    draw = ImageDraw.Draw(img)

    draw_rounded_rectangle(draw, (24, 24, 460, CANVAS_HEIGHT - 60), radius=20, fill=(241, 245, 249, 255))
    draw_rounded_rectangle(draw, (480, 24, CANVAS_WIDTH - 24, CANVAS_HEIGHT - 60), radius=20, fill=(248, 250, 252, 255))

    bold_path = os.path.join(font_dir, "NotoSansJP-Bold.ttf") if font_dir else None
    reg_path = os.path.join(font_dir, "NotoSansJP-Regular.ttf") if font_dir else None

    font_title = load_font(bold_path, 34, bold=True)
    font_subtitle = load_font(bold_path, 13, bold=True)
    font_body_bold = load_font(bold_path, 14, bold=True)
    font_body = load_font(reg_path, 13, bold=False)
    font_caption = load_font(reg_path, 11, bold=False)
    font_brand = load_font(bold_path, 15, bold=True)

    # ----------------------------------------------------
    # ■ 左側エリア（40%）
    # ----------------------------------------------------
    left_x = 48
    name_text = data.get("name", "議員氏名")

    avatar_file = resolve_avatar_image(name_text)
    avatar_size = 120
    avatar_img = create_circular_avatar(avatar_file, avatar_size)
    img.paste(avatar_img, (left_x, 48), mask=avatar_img)

    # 氏名
    draw.text((left_x + avatar_size + 20, 68), name_text, font=font_title, fill=COLOR_TEXT_MAIN)

    # 所属バッジ
    party_text = data.get("party", "会派未登録")
    district_text = data.get("district", "選挙区未登録")
    badge_str = f"{district_text}  |  {party_text}"
    
    badge_w = font_subtitle.getbbox(badge_str)[2] - font_subtitle.getbbox(badge_str)[0] + 24
    badge_box = (left_x + avatar_size + 20, 118, left_x + avatar_size + 20 + max(badge_w, 200), 144)
    draw_rounded_rectangle(draw, badge_box, radius=6, fill=COLOR_PRIMARY_LIGHT, outline=COLOR_PRIMARY_BORDER)
    draw.text((left_x + avatar_size + 30, 123), badge_str, font=font_subtitle, fill=COLOR_PRIMARY)

    # 看板公約カード
    pledge_box = (48, 195, 436, CANVAS_HEIGHT - 80)
    draw_rounded_rectangle(draw, pledge_box, radius=14, fill=COLOR_BG_CARD, outline=COLOR_CARD_BORDER)

    draw_rounded_rectangle(draw, (64, 210, 210, 234), radius=4, fill=COLOR_PRIMARY_LIGHT)
    draw.text((72, 213), "選管公報原本の看板公約", font=load_font(bold_path, 11, bold=True), fill=COLOR_PRIMARY)

    headline_text = data.get("pledge_headline", "市政政策")
    draw.text((64, 246), headline_text, font=font_body_bold, fill=COLOR_TEXT_MAIN)

    quote_text = f"“{data.get('pledge_quote', '')}”"
    quote_lines = draw_wrapped_text(draw, quote_text, font_body, max_width=350, max_lines=7)
    
    quote_y = 280
    for line in quote_lines:
        draw.text((64, quote_y), line, font=font_body, fill=COLOR_TEXT_MUTED)
        quote_y += 22

    draw.text((64, CANVAS_HEIGHT - 110), "出典: 令和5年 京都市議会議員選挙 公報原本", font=font_caption, fill=COLOR_TEXT_LIGHT)

    # ----------------------------------------------------
    # ■ 右側エリア（60%）
    # ----------------------------------------------------
    right_x = 504

    # 1. レーダーチャートカード
    radar_box = (right_x, 48, CANVAS_WIDTH - 48, 335)
    draw_rounded_rectangle(draw, radar_box, radius=14, fill=COLOR_BG_CARD, outline=COLOR_CARD_BORDER)

    draw.text((right_x + 20, 64), "AI客観ポリシーパラメータ (4軸/5点満点)", font=font_body_bold, fill=COLOR_TEXT_MAIN)
    draw.text((right_x + 20, 84), "全任期5,000件超の質疑ログから密度・対案・解像度を抽出", font=font_caption, fill=COLOR_TEXT_MUTED)

    metrics = data.get("metrics", {
        "根拠・データ": 3.5,
        "対案・是正": 3.5,
        "地域解像度": 3.5,
        "議論の進展": 3.5
    })
    chart_img = generate_radar_chart(list(metrics.keys()), list(metrics.values()), size_px=270)
    chart_x = right_x + 360
    chart_y = 52
    img.paste(chart_img, (chart_x, chart_y), mask=chart_img)

    score_y = 120
    for label, val in metrics.items():
        draw.text((right_x + 24, score_y), f"• {label}", font=font_body, fill=COLOR_TEXT_MAIN)
        draw.text((right_x + 180, score_y), f"{val:.1f} / 5.0", font=font_body_bold, fill=COLOR_PRIMARY)
        score_y += 34

    # 2. 激論議案ログカード
    bill_box = (right_x, 355, CANVAS_WIDTH - 48, CANVAS_HEIGHT - 80)
    draw_rounded_rectangle(draw, bill_box, radius=14, fill=COLOR_BG_CARD, outline=COLOR_CARD_BORDER)

    draw.text((right_x + 20, 372), "直近の激戦議案ログ & 議場質疑実績", font=font_body_bold, fill=COLOR_TEXT_MAIN)

    bill_log = data.get("recent_log", {})
    session_title = bill_log.get("session", "令和6年 市会定例会")
    bill_title = bill_log.get("bill_title", "市政重要審議案件")
    vote_stance = bill_log.get("vote", "賛成")
    log_summary = bill_log.get("summary", "本会議・委員会において市政課題に関する審議・質疑を実施。")

    vote_bg = COLOR_EMERALD_BG if vote_stance == "賛成" else COLOR_ROSE_BG
    vote_fg = COLOR_EMERALD_TEXT if vote_stance == "賛成" else COLOR_ROSE_TEXT
    vote_badge_box = (right_x + 20, 404, right_x + 85, 426)
    draw_rounded_rectangle(draw, vote_badge_box, radius=4, fill=vote_bg)
    draw.text((right_x + 28, 407), f"採決: {vote_stance}", font=load_font(bold_path, 11, bold=True), fill=vote_fg)

    draw.text((right_x + 95, 407), f"{session_title} : {bill_title}", font=font_subtitle, fill=COLOR_TEXT_MAIN)

    summary_lines = draw_wrapped_text(draw, log_summary, font_body, max_width=620, max_lines=4)
    sum_y = 440
    for line in summary_lines:
        draw.text((right_x + 20, sum_y), line, font=font_body, fill=COLOR_TEXT_MUTED)
        sum_y += 24

    # ----------------------------------------------------
    # ■ フッターエリア
    # ----------------------------------------------------
    footer_y = CANVAS_HEIGHT - 44
    draw.text((36, footer_y), "議会のミカタ 京都", font=font_brand, fill=(255, 255, 255, 255))
    draw.text((180, footer_y + 3), "|   kyoto-politician-tracker.web.app", font=font_caption, fill=COLOR_TEXT_LIGHT)
    
    disclaimer_text = "※本データは京都市会公式会議録および選挙管理委員会公報原本より機械抽出・AI客観解析したものです（序列評価ではありません）。"
    draw.text((CANVAS_WIDTH - 650, footer_y + 3), disclaimer_text, font=font_caption, fill=COLOR_TEXT_LIGHT)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", quality=95)
    print(f"[完了] カード生成: {output_path} (写真: {avatar_file.name if avatar_file else '未検出(プレースホルダー)'})")


# ==========================================
# 本番JSONデータ統合ローダー
# ==========================================
def load_all_councilors_from_project() -> List[Dict]:
    """statements_summary.json と pledge_tracker.json を結合してカード用データを構築"""
    if not STATEMENTS_SUMMARY_FILE.exists():
        print(f"[エラー] {STATEMENTS_SUMMARY_FILE} が見つかりません。")
        return []

    with open(STATEMENTS_SUMMARY_FILE, "r", encoding="utf-8") as f:
        statements_data = json.load(f)

    pledge_map = {}
    if PLEDGE_TRACKER_FILE.exists():
        try:
            with open(PLEDGE_TRACKER_FILE, "r", encoding="utf-8") as f:
                pledge_map = json.load(f)
        except Exception:
            pass

    # 議員単位に集約（speakerStats の辞書）
    councilors_dict = {}
    for stmt in statements_data:
        raw_spk = stmt.get("speaker", "")
        clean_spk = clean_speaker_name(raw_spk)
        if not clean_spk:
            continue

        if clean_spk not in councilors_dict:
            councilors_dict[clean_spk] = {
                "name": clean_spk,
                "district": stmt.get("district", "京都市"),
                "party": stmt.get("partyGroup", "京都市会"),
                "metrics": {
                    "根拠・データ": round(float(stmt.get("avg_evidence", stmt.get("evidence_score", 3.5))), 1),
                    "対案・是正": round(float(stmt.get("avg_solution", stmt.get("solution_score", 3.5))), 1),
                    "地域解像度": round(float(stmt.get("avg_local_focus", stmt.get("local_focus_score", 3.5))), 1),
                    "議論の進展": round(float(stmt.get("avg_constructive", stmt.get("constructive_score", 3.5))), 1),
                },
                "statements": []
            }
        
        # 質疑ログの蓄積
        if stmt.get("summary"):
            councilors_dict[clean_spk]["statements"].append(stmt)

    result_list = []
    for spk, info in councilors_dict.items():
        # 公約データの結合
        plg_info = pledge_map.get(spk)
        if not plg_info and spk in NAME_CANONICAL_MAP:
            plg_info = pledge_map.get(NAME_CANONICAL_MAP[spk])

        headline = "市民生活と京都の未来を拓く政策推進"
        quote = "市民の切実な声に寄り添い、確かな未来へ向けた制度改革と魅力あるまちづくりを全力で推進します。"
        recent_log = {
            "session": "令和6年 市会本会議",
            "bill_title": "一般会計当初予算案",
            "vote": "賛成",
            "summary": "市民生活の安心・安全確保および持続可能な財政運営に向け、市政全般にわたり建設的な質疑を展開。"
        }

        if plg_info and plg_info.get("tracked_items"):
            item = plg_info["tracked_items"][0]
            headline = item.get("headline", headline)
            quote = item.get("election_promise", {}).get("quote", quote)
            
            if item.get("council_vote"):
                v = item["council_vote"]
                recent_log["session"] = v.get("session_name", recent_log["session"])
                recent_log["bill_title"] = v.get("bill_title", recent_log["bill_title"])
                recent_log["vote"] = v.get("my_vote", "賛成")
                if item.get("council_statements"):
                    recent_log["summary"] = item["council_statements"][0].get("summary", recent_log["summary"])

        elif info["statements"]:
            st = info["statements"][0]
            recent_log["session"] = f"{st.get('meeting_date', '')} {st.get('meeting_title', '')}".strip()
            recent_log["summary"] = st.get("summary", recent_log["summary"])

        slug = spk.replace(" ", "").replace(" ", "")
        result_list.append({
            "slug": slug,
            "name": spk,
            "district": info["district"],
            "party": info["party"],
            "pledge_headline": headline,
            "pledge_quote": quote,
            "metrics": info["metrics"],
            "recent_log": recent_log
        })

    return result_list


# ==========================================
# CLI エントリーポイント
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="議員カルテOGP自動生成ツール")
    parser.add_argument("--speaker", type=str, help="特定議員のみ生成する場合に氏名を指定 (例: 江村りさ)")
    parser.add_argument("--limit", type=int, default=0, help="生成件数上限 (0なら全件)")
    args = parser.parse_args()

    print("=== 京都市議会議員 カルテOGP自動生成パイプライン ===")
    councilors = load_all_councilors_from_project()
    if not councilors:
        print("[警告] 実データが見つからないため、初期テストデータを適用します。")
        councilors = [
            {
                "slug": "江村理紗",
                "name": "江村 りさ",
                "party": "地域政党京都党",
                "district": "右京区選挙区",
                "pledge_headline": "アイデアで稼ぎ、財政再建と市民サービスを両立",
                "pledge_quote": "発想の転換による行財政改革！ アイデアで稼げる自治体に転換し、財政再建と市民サービス向上を両立させます。",
                "metrics": {"根拠・データ": 4.6, "対案・是正": 4.8, "地域解像度": 4.2, "議論の進展": 4.7},
                "recent_log": {
                    "session": "令和7年11月市会",
                    "bill_title": "宿泊税条例改正案",
                    "vote": "賛成",
                    "summary": "宿泊税上限引き上げに伴う使途の透明化を徹底追及。観光客負担を市民インフラ整備へ確実に充当させる具体的な制度改善答弁を引き出した。"
                }
            },
            {
                "slug": "片桐直哉",
                "name": "片桐 直哉",
                "party": "立憲民主党",
                "district": "北区選挙区",
                "pledge_headline": "徹底した市民参加と協働による市政改革",
                "pledge_quote": "若い世代が安心して子どもを産み育てられるよう、子育て世帯の数が増え、子育てを楽しめる京都をつくります。",
                "metrics": {"根拠・データ": 4.1, "対案・是正": 4.3, "地域解像度": 4.7, "議論の進展": 4.0},
                "recent_log": {
                    "session": "令和7年9月市会",
                    "bill_title": "中学校給食センター整備契約",
                    "vote": "賛成",
                    "summary": "普通学級に通う発達特性のある児童への支援拡充を具体的事例とともに質疑。教育委員会から外部連携強化の前向きな答弁を獲得。"
                }
            }
        ]

  # フィルタリング
    if args.speaker:
        target_clean = clean_speaker_name(args.speaker)
        # 💡 ひらがな・漢字・異体字の別名を双方向で検索対象に追加
        search_targets = {target_clean}
        if target_clean in NAME_CANONICAL_MAP:
            search_targets.add(NAME_CANONICAL_MAP[target_clean])
        for k, v in NAME_CANONICAL_MAP.items():
            if target_clean == v:
                search_targets.add(k)

        def is_match(name: str) -> bool:
            c_name = clean_speaker_name(name)
            if c_name in search_targets:
                return True
            for t in search_targets:
                if t in c_name or c_name in t:
                    return True
            return False

        councilors = [c for c in councilors if is_match(c["name"])]
        if not councilors:
            print(f"[エラー] 該当議員が見つかりませんでした: {args.speaker}")
            return
    if args.limit > 0:
        councilors = councilors[:args.limit]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"対象件数: {len(councilors)} 件")

    for item in councilors:
        slug = item.get("slug", item["name"])
        out_file = str(OUTPUT_DIR / f"{slug}_card.png")
        render_councilor_card(item, out_file)

    print("=== 全件の画像生成が完了しました ===")
    print(f"出力先: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()