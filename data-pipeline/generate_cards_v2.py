#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
議員カルテ画像自動生成システム v2.0
要件定義書に準拠した16:9（1200x675）OGP画像の生成
"""

import os
import sys
import json
import io
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ==========================================
# 寸法・カラー定数定義
# ==========================================
CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 675
CANVAS_PADDING = 24
COL_GAP = 20

# カラーパレット（Tailwind Slate/Indigo 準拠）
COLOR_BG_DARK = (15, 23, 42)          # Slate 900 (#0F172A) - ベース背景
COLOR_CARD_BG = (255, 255, 255)       # White (#FFFFFF) - カード背景
COLOR_CARD_BORDER = (226, 232, 240)   # Slate 200 (#E2E8F0)
COLOR_TEXT_MAIN = (15, 23, 42)        # Slate 900
COLOR_TEXT_MUTED = (71, 85, 105)      # Slate 600 (#475569)
COLOR_TEXT_LIGHT = (148, 163, 184)    # Slate 400 (#94A3B8)

COLOR_PRIMARY = (79, 70, 229)         # Indigo 600 (#4F46E5)
COLOR_PRIMARY_LIGHT = (238, 242, 255) # Indigo 50 (#EEF2FF)
COLOR_PRIMARY_BORDER = (199, 210, 254)# Indigo 200 (#C7D2FE)

COLOR_VOTE_YES_BG = (220, 252, 231)   # Green 50 (#DCFCE7)
COLOR_VOTE_YES_FG = (21, 128, 61)     # Green 700 (#15803D)
COLOR_VOTE_NO_BG = (254, 226, 226)    # Red 50 (#FEE2E2)
COLOR_VOTE_NO_FG = (185, 28, 28)      # Red 700 (#B91C1C)


# ==========================================
# フォント解決処理
# ==========================================
def find_system_japanese_font(bold: bool = False) -> str:
    candidates = []
    if sys.platform.startswith("win"):
        candidates = [
            "C:/Windows/Fonts/meiryob.ttc" if bold else "C:/Windows/Fonts/meiryo.ttc",
            "C:/Windows/Fonts/msgothic.ttc",
            "C:/Windows/Fonts/yu-gothic.ttf",
            "C:/Windows/Fonts/yumin.ttf"
        ]
    elif sys.platform.startswith("darwin"):
        candidates = [
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/PingFang.ttc"
        ]
    else:
        candidates = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"
        ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return ""

def load_font(size: int, bold: bool = False, custom_font_path: Optional[str] = None) -> ImageFont.FreeTypeFont:
    if custom_font_path and os.path.exists(custom_font_path):
        try:
            return ImageFont.truetype(custom_font_path, size)
        except Exception:
            pass
    sys_font = find_system_japanese_font(bold=bold)
    if sys_font:
        try:
            return ImageFont.truetype(sys_font, size)
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

def create_circular_avatar(image_path: Optional[str], diameter: int = 90) -> Image.Image:
    """90pxの円形アバターを作成し、Indigoの枠線を付与"""
    if image_path and os.path.exists(image_path):
        try:
            src = Image.open(image_path).convert("RGBA")
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

    # 枠線
    ring = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    ring_draw = ImageDraw.Draw(ring)
    ring_draw.ellipse((1, 1, diameter - 2, diameter - 2), outline=(79, 70, 229, 255), width=3)
    output = Image.alpha_composite(output, ring)
    return output


# ==========================================
# 0%〜50% ポリシー構成比レーダーチャート生成
# ==========================================
def generate_percentage_radar_chart(portfolio: List[Dict], size_px: int = 280) -> Image.Image:
    """【新要件】スコアを廃止し、0〜50%の構成比率を表すレーダーチャートを生成"""
    categories = [item["domain"] for item in portfolio]
    values = [float(item["percentage"]) for item in portfolio]

    num_vars = len(categories)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()

    values_closed = values + values[:1]
    angles_closed = angles + angles[:1]

    font_path = find_system_japanese_font(bold=True)
    font_prop = fm.FontProperties(fname=font_path) if font_path else None
    if font_prop:
        font_prop.set_size(8.5)
        font_prop.set_weight('bold')

    dpi = 100
    fig_size = size_px / dpi
    fig, ax = plt.subplots(figsize=(fig_size, fig_size), subplot_kw=dict(polar=True), dpi=dpi)

    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(0)
    ax.set_ylim(0, 50.0)  # 最大値を50%に固定

    # 刻み線とグリッド
    ax.set_yticks([10.0, 20.0, 30.0, 40.0, 50.0])
    ax.set_yticklabels([])  # 内部の数値テキストは非表示
    ax.grid(color="#E2E8F0", linestyle="--", linewidth=1.0)
    ax.spines['polar'].set_color("#CBD5E1")
    ax.spines['polar'].set_linewidth(1.0)

    # 外周ラベル
    ax.set_xticks(angles)
    if font_prop:
        ax.set_xticklabels(categories, fontproperties=font_prop, color="#334155")
    else:
        ax.set_xticklabels(categories, fontsize=8.5, color="#334155")

    # ポリゴン描画
    ax.plot(angles_closed, values_closed, color="#4F46E5", linewidth=2.0)
    ax.fill(angles_closed, values_closed, color="#6366F1", alpha=0.35)
    ax.scatter(angles, values, color="#4338CA", s=28, zorder=5)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


# ==========================================
# カードUI メイン合成処理
# ==========================================
def render_councilor_card_v2(data: Dict, output_path: str):
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), COLOR_BG_DARK)
    draw = ImageDraw.Draw(canvas)

    # 該当フォント読み込み
    f_title = load_font(28, bold=True)
    f_sub = load_font(18, bold=True)
    f_head = load_font(15, bold=True)
    f_badge = load_font(11, bold=True)
    f_body_bold = load_font(13, bold=True)
    f_body = load_font(12, bold=False)
    f_caption = load_font(10, bold=False)

    # グリッド配置座標
    left_x = CANVAS_PADDING
    left_y = CANVAS_PADDING
    left_w = 380
    left_h = 575

    right_x = left_x + left_w + COL_GAP
    right_w = 730
    right_upper_y = CANVAS_PADDING
    right_upper_h = 295
    right_lower_y = right_upper_y + right_upper_h + 15
    right_lower_h = 265

    # ----------------------------------------------------
    # ■ 1. 左カラム：議員属性・公約カード (380x575)
    # ----------------------------------------------------
    draw_rounded_rectangle(draw, (left_x, left_y, left_x + left_w, left_y + left_h),
                           radius=16, fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER)

    # 属性上部: アイコン (90px)
    avatar_size = 90
    avatar_img = create_circular_avatar(data.get("avatar_path"), diameter=avatar_size)
    canvas.paste(avatar_img, (left_x + 18, left_y + 18), mask=avatar_img)

    # 属性上部: 氏名・ふりがな
    name_str = data.get("name", "")
    draw.text((left_x + 120, left_y + 20), name_str, font=f_title, fill=COLOR_TEXT_MAIN)
    if data.get("name_furigana"):
        draw.text((left_x + 122, left_y + 58), data.get("name_furigana"), font=f_caption, fill=COLOR_TEXT_MUTED)

    # 属性上部: 所属バッジ群 (横並びピル型)
    badge_cur_x = left_x + 120
    badge_y = left_y + 78
    badges = [
        data.get("party", ""),
        data.get("constituency", ""),
        f"{data.get('terms', 1)}期" if data.get("terms") else ""
    ]
    for badge_text in badges:
        if not badge_text:
            continue
        bbox = f_badge.getbbox(badge_text)
        bw = (bbox[2] - bbox[0]) + 14
        bh = 22
        draw_rounded_rectangle(draw, (badge_cur_x, badge_y, badge_cur_x + bw, badge_y + bh),
                               radius=6, fill=COLOR_PRIMARY_LIGHT, outline=COLOR_PRIMARY_BORDER)
        draw.text((badge_cur_x + 7, badge_y + 3), badge_text, font=f_badge, fill=COLOR_PRIMARY)
        badge_cur_x += bw + 6

    # 区切り線
    draw.line((left_x + 18, left_y + 120, left_x + left_w - 18, left_y + 120), fill=COLOR_CARD_BORDER, width=1)

    # 中部公約エリア
    pledge_data = data.get("election_pledge", {})
    draw_rounded_rectangle(draw, (left_x + 18, left_y + 132, left_x + 155, left_y + 154),
                           radius=4, fill=(243, 232, 255), outline=(216, 180, 254))
    draw.text((left_x + 24, left_y + 135), "選管公報原本の看板公約", font=f_caption, fill=(126, 34, 206))

    # 公約タイトル (18pt Bold)
    p_title = pledge_data.get("title", "")
    draw.text((left_x + 18, left_y + 162), p_title, font=f_sub, fill=COLOR_TEXT_MAIN)

    # 公約本文引用
    lead_quote = f"“{pledge_data.get('lead_quote', '')}”"
    quote_lines = draw_wrapped_text(draw, lead_quote, f_body, max_width=340, max_lines=5)
    qy = left_y + 195
    for ql in quote_lines:
        draw.text((left_x + 18, qy), ql, font=f_body, fill=COLOR_TEXT_MUTED)
        qy += 20

    # 空白解消: タグ群 (#)
    tag_y = left_y + 315
    tag_x = left_x + 18
    for tag in pledge_data.get("tags", []):
        tag_str = f"#{tag}"
        t_box = f_badge.getbbox(tag_str)
        t_w = (t_box[2] - t_box[0]) + 12
        draw_rounded_rectangle(draw, (tag_x, tag_y, tag_x + t_w, tag_y + 22),
                               radius=4, fill=(241, 245, 249), outline=COLOR_CARD_BORDER)
        draw.text((tag_x + 6, tag_y + 3), tag_str, font=f_badge, fill=COLOR_TEXT_MUTED)
        tag_x += t_w + 6

    # 空白解消: 公報原本スニペット枠
    snip_box = (left_x + 18, left_y + 355, left_x + left_w - 18, left_y + 535)
    draw_rounded_rectangle(draw, snip_box, radius=8, fill=(248, 250, 252), outline=COLOR_CARD_BORDER)
    draw.text((left_x + 30, left_y + 368), "【京都市選挙管理委員会 法定公報証明】", font=f_badge, fill=COLOR_PRIMARY)
    snip_text = "※ 本欄記載の内容は正式に発行された選挙公報原文から抽出しており、主観的修飾や採点を含みません。有権者は直接公式公報と照合可能です。"
    for idx, sl in enumerate(draw_wrapped_text(draw, snip_text, f_caption, max_width=320, max_lines=6)):
        draw.text((left_x + 30, left_y + 395 + (idx * 18)), sl, font=f_caption, fill=COLOR_TEXT_LIGHT)

    # 左欄フッター（出典）
    draw.text((left_x + 18, left_y + 548), f"出典: {pledge_data.get('source', '令和5年 京都市議会議員選挙 公報原本')}",
              font=f_caption, fill=COLOR_TEXT_LIGHT)

    # ----------------------------------------------------
    # ■ 2. 右カラム上段：政策ポートフォリオ (730x295)
    # ----------------------------------------------------
    draw_rounded_rectangle(draw, (right_x, right_upper_y, right_x + right_w, right_upper_y + right_upper_h),
                           radius=16, fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER)

    draw.text((right_x + 24, right_upper_y + 18), "AI政策ポートフォリオ（質疑分野の構成比率）", font=f_head, fill=COLOR_TEXT_MAIN)
    draw.text((right_x + 24, right_upper_y + 40), "全任期の市会質疑ログより発言テーマの配分比率を客観抽出（序列評価ではありません）",
              font=f_caption, fill=COLOR_TEXT_MUTED)

    # リスト描画（左側）
    portfolio = data.get("policy_portfolio", [])
    py = right_upper_y + 70
    for p_item in portfolio:
        domain = p_item.get("domain", "")
        pct = p_item.get("percentage", 0)
        draw.text((right_x + 24, py), f"•  {domain}", font=f_body_bold, fill=COLOR_TEXT_MAIN)
        draw.text((right_x + 220, py), f"{pct}%", font=f_head, fill=COLOR_PRIMARY)

        # プログレスバー描画
        draw_rounded_rectangle(draw, (right_x + 270, py + 4, right_x + 400, py + 12),
                               radius=3, fill=(241, 245, 249))
        bar_w = int(130 * (min(pct, 50) / 50.0))
        if bar_w > 0:
            draw_rounded_rectangle(draw, (right_x + 270, py + 4, right_x + 270 + bar_w, py + 12),
                                   radius=3, fill=COLOR_PRIMARY)
        py += 38

    # レーダーチャート合成（右側）
    radar_img = generate_percentage_radar_chart(portfolio, size_px=270)
    canvas.paste(radar_img, (right_x + 430, right_upper_y + 15), mask=radar_img)

    # ----------------------------------------------------
    # ■ 3. 右カラム下段：激戦議案ログ＆質疑実績 (730x260)
    # ----------------------------------------------------
    draw_rounded_rectangle(draw, (right_x, right_lower_y, right_x + right_w, right_lower_y + right_lower_h),
                           radius=16, fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER)

    draw.text((right_x + 24, right_lower_y + 18), "直近の激戦議案ログ ＆ 議場質疑実績", font=f_head, fill=COLOR_TEXT_MAIN)

    leg_records = data.get("legislative_records", [])
    vote_rec = next((r for r in leg_records if r.get("type") == "採決"), {})
    speech_rec = next((r for r in leg_records if r.get("type") == "質疑"), {})

    # 1段目: 採決態度
    is_yes = vote_rec.get("status") == "賛成"
    v_bg = COLOR_VOTE_YES_BG if is_yes else COLOR_VOTE_NO_BG
    v_fg = COLOR_VOTE_YES_FG if is_yes else COLOR_VOTE_NO_FG

    draw_rounded_rectangle(draw, (right_x + 24, right_lower_y + 48, right_x + 94, right_lower_y + 70),
                           radius=4, fill=v_bg)
    draw.text((right_x + 30, right_lower_y + 51), f"採決:{vote_rec.get('status', '賛成')}", font=f_badge, fill=v_fg)

    v_detail = f"{vote_rec.get('council_session', '')} ： {vote_rec.get('bill_name', '')}"
    draw.text((right_x + 104, right_lower_y + 51), v_detail, font=f_body_bold, fill=COLOR_TEXT_MAIN)

    # 2段目: 議場質疑 (Blockquote風)
    draw_rounded_rectangle(draw, (right_x + 24, right_lower_y + 86, right_x + 64, right_lower_y + 108),
                           radius=4, fill=COLOR_PRIMARY_LIGHT)
    draw.text((right_x + 30, right_lower_y + 89), "質疑", font=f_badge, fill=COLOR_PRIMARY)

    speech_meta = f"{speech_rec.get('council_session', '')} ｜ 論点：{speech_rec.get('topic', '')}"
    draw.text((right_x + 74, right_lower_y + 89), speech_meta, font=f_body_bold, fill=COLOR_TEXT_MAIN)

    sp_box = (right_x + 24, right_lower_y + 118, right_x + right_w - 24, right_lower_y + 225)
    draw_rounded_rectangle(draw, sp_box, radius=8, fill=(248, 250, 252), outline=COLOR_CARD_BORDER)
    draw.rectangle((right_x + 24, right_lower_y + 118, right_x + 28, right_lower_y + 225), fill=COLOR_PRIMARY)

    raw_quote = f"「{speech_rec.get('quote', '')}」"
    quote_lines = draw_wrapped_text(draw, raw_quote, f_body, max_width=640, max_lines=4)
    spy = right_lower_y + 128
    for line in quote_lines:
        draw.text((right_x + 40, spy), line, font=f_body, fill=COLOR_TEXT_MUTED)
        spy += 22

    draw.text((right_x + 40, right_lower_y + 234), "※ 市会会議録原本より引用",
              font=f_caption, fill=COLOR_TEXT_LIGHT)

    # ----------------------------------------------------
    # ■ 4. 外枠フッター領域
    # ----------------------------------------------------
    footer_y = CANVAS_HEIGHT - 38
    # ドメイン統一
    draw.text((CANVAS_PADDING + 10, footer_y), "議会のミカタ 京都 ｜ gikai-mikata.jp",
              font=f_body_bold, fill=(255, 255, 255))

    # 免責ポリシー
    disclaimer = "※本データは京都市会公式会議録および選挙管理委員会公報原本より機械抽出した客観データです（序列評価・採点はありません）。"
    draw.text((CANVAS_WIDTH - 680, footer_y + 2), disclaimer, font=f_caption, fill=COLOR_TEXT_LIGHT)

    # 書き出し
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG", quality=95)
    print(f"[完了] カード生成: {output_path}")


# ==========================================
# デモ実行
# ==========================================
if __name__ == "__main__":
    sample_data = {
        "id": "emura-risa",
        "name": "江村理紗",
        "name_furigana": "えむら りさ",
        "party": "京都党",
        "constituency": "右京区",
        "terms": 3,
        "avatar_path": "../frontend/public/councilors/江村理紗.jpg",
        "election_pledge": {
            "title": "発想の転換による行財政改革",
            "lead_quote": "発想の転換による行財政改革！アイデアで稼げる自治体に転換し、財政再建と市民サービス向上を両立。",
            "tags": ["財政健全化", "稼げる自治体", "身を切る改革"],
            "source": "令和5年 京都市議会議員選挙 公報原本"
        },
        "policy_portfolio": [
            {"domain": "行財政改革", "percentage": 34},
            {"domain": "都市計画・観光", "percentage": 22},
            {"domain": "福祉・医療", "percentage": 18},
            {"domain": "教育・子育て", "percentage": 14},
            {"domain": "環境・景観", "percentage": 12}
        ],
        "legislative_records": [
            {
                "type": "採決",
                "status": "賛成",
                "council_session": "令和6年 市会本会議",
                "bill_name": "京都市一般会計当初予算案"
            },
            {
                "type": "質疑",
                "council_session": "2025年3月 予算特別委員会",
                "topic": "宿泊税増収分の使途・財源置換検証",
                "quote": "宿泊税の増収分について歳出側の見通しが不明瞭。一般財源の置き換えではないか。"
            }
        ]
    }

    out_file = str(Path("output") / f"{sample_data['id']}_card.png")
    render_councilor_card_v2(sample_data, out_file)