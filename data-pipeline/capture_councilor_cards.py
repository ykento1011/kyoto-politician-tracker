#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
議員カルテ画像 自動生成システム（Playwright版）
京都市会公式名簿順（No.01〜67）を厳格に保持し、16:9 OGP画像を一括生成する。
"""

import os
import sys
import json
import argparse
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from PIL import Image

# ==========================================
# パス・定数設定
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
OUTPUT_DIR = BASE_DIR / "output_cards"

# 16:9 出力解像度仕様
TARGET_WIDTH = 1200
TARGET_HEIGHT = 675
CANVAS_SCALE = 2  # Retina 2x内部解像度 (2400x1350)
BG_COLOR = (15, 23, 42)  # Slate 900 (#0F172A)

# ==========================================
# 💡 京都市会 公式名簿順マスターリスト（全67名・五十音順固定）
# 動的ソートを排し、この配列順および no を絶対値として使用する
# ==========================================
COUNCILORS_ORDERED = [
    {"no": 1, "name": "青野 仁志", "district": "中京区", "party": "公明党"},
    {"no": 2, "name": "赤阪 仁", "district": "伏見区", "party": "日本共産党"},
    {"no": 3, "name": "天方 ひろゆき", "district": "西京区", "party": "無所属"},
    {"no": 4, "name": "井﨑 敦子", "district": "左京区", "party": "無所属"},
    {"no": 5, "name": "井上 よしひろ", "district": "右京区", "party": "自由民主党"},
    {"no": 6, "name": "宇佐美 賢一", "district": "左京区", "party": "維新・京都・国民"},
    {"no": 7, "name": "江村 理紗", "district": "右京区", "party": "維新・京都・国民"},
    {"no": 8, "name": "えもと かよこ", "district": "右京区", "party": "日本共産党"},
    {"no": 9, "name": "大津 裕太", "district": "中京区", "party": "維新・京都・国民"},
    {"no": 10, "name": "おんづか 功", "district": "左京区", "party": "維新・京都・国民"},
    {"no": 11, "name": "片桐 直哉", "district": "北区", "party": "維新・京都・国民"},
    {"no": 12, "name": "加藤 あい", "district": "山科区", "party": "日本共産党"},
    {"no": 13, "name": "加藤 昌洋", "district": "左京区", "party": "自由民主党"},
    {"no": 14, "name": "神谷 修平", "district": "右京区", "party": "維新・京都・国民"},
    {"no": 15, "name": "河合 ようこ", "district": "西京区", "party": "日本共産党"},
    {"no": 16, "name": "かわしま 優子", "district": "伏見区", "party": "維新・京都・国民"},
    {"no": 17, "name": "河村 諒", "district": "伏見区", "party": "自由民主党"},
    {"no": 18, "name": "きくち 一秀", "district": "下京区", "party": "日本共産党"},
    {"no": 19, "name": "北尾 ゆか", "district": "南区", "party": "日本共産党"},
    {"no": 20, "name": "北川 みき", "district": "伏見区", "party": "自由民主党"},
    {"no": 21, "name": "北山 ただお", "district": "右京区", "party": "自由民主党"},
    {"no": 22, "name": "久保田 正紀", "district": "上京区", "party": "自由民主党"},
    {"no": 23, "name": "くまざわ 真昭", "district": "南区", "party": "維新・京都・国民"},
    {"no": 24, "name": "くらた 共子", "district": "上京区", "party": "日本共産党"},
    {"no": 25, "name": "こうち 大輔", "district": "西京区", "party": "自由民主党"},
    {"no": 26, "name": "小島 信太郎", "district": "山科区", "party": "自由民主党"},
    {"no": 27, "name": "さくらい 泰広", "district": "左京区", "party": "自由民主党"},
    {"no": 28, "name": "繁 隆夫", "district": "伏見区", "party": "自由民主党"},
    {"no": 29, "name": "しまもと 京司", "district": "下京区", "party": "自由民主党"},
    {"no": 30, "name": "下村 あきら", "district": "下京区", "party": "公明党"},
    {"no": 31, "name": "菅谷 浩平", "district": "北区", "party": "維新・京都・国民"},
    {"no": 32, "name": "田中 明秀", "district": "西京区", "party": "自由民主党"},
    {"no": 33, "name": "田中 たかのり", "district": "山科区", "party": "維新・京都・国民"},
    {"no": 34, "name": "谷口 みゆき", "district": "山科区", "party": "公明党"},
    {"no": 35, "name": "玉本 なるみ", "district": "北区", "party": "日本共産党"},
    {"no": 36, "name": "津田 大三", "district": "中京区", "party": "自由民主党"},
    {"no": 37, "name": "寺田 一博", "district": "中京区", "party": "自由民主党"},
    {"no": 38, "name": "とがし 豊", "district": "左京区", "party": "日本共産党"},
    {"no": 39, "name": "富 きくお", "district": "左京区", "party": "公明党"},
    {"no": 40, "name": "中高 しゅうじ", "district": "東山区", "party": "自由民主党"},
    {"no": 41, "name": "中野 洋一", "district": "東山区", "party": "公明党"},
    {"no": 42, "name": "中村 まり", "district": "上京区", "party": "維新・京都・国民"},
    {"no": 43, "name": "西野 さち子", "district": "伏見区", "party": "日本共産党"},
    {"no": 44, "name": "西村 義直", "district": "伏見区", "party": "公明党"},
    {"no": 45, "name": "西山 信昌", "district": "伏見区", "party": "公明党"},
    {"no": 46, "name": "橋村 芳和", "district": "伏見区", "party": "自由民主党"},
    {"no": 47, "name": "土方 莉紗", "district": "南区", "party": "自由民主党"},
    {"no": 48, "name": "兵藤 しんいち", "district": "公明党", "party": "公明党"},
    {"no": 49, "name": "平井 良人", "district": "中京区", "party": "日本共産党"},
    {"no": 50, "name": "平田 圭", "district": "中京区", "party": "公明党"},
    {"no": 51, "name": "平山 たかお", "district": "中京区", "party": "自由民主党"},
    {"no": 52, "name": "平山 よしかず", "district": "南区", "party": "自由民主党"},
    {"no": 53, "name": "増成 竜治", "district": "伏見区", "party": "維新・京都・国民"},
    {"no": 54, "name": "松田 けい子", "district": "山科区", "party": "自由民主党"},
    {"no": 55, "name": "みちはた 弘之", "district": "東山区", "party": "日本共産党"},
    {"no": 56, "name": "椋田 隆知", "district": "北区", "party": "自由民主党"},
    {"no": 57, "name": "森 かれん", "district": "南区", "party": "維新・京都・国民"},
    {"no": 58, "name": "森田 守", "district": "南区", "party": "自由民主党"},
    {"no": 59, "name": "森田 ゆみ子", "district": "南区", "party": "日本共産党"},
    {"no": 60, "name": "もりもと 英靖", "district": "西京区", "party": "日本共産党"},
    {"no": 61, "name": "山田 こうじ", "district": "右京区", "party": "日本共産党"},
    {"no": 62, "name": "やまね 智史", "district": "伏見区", "party": "日本共産党"},
    {"no": 63, "name": "山本 恵一", "district": "北区", "party": "自由民主党"},
    {"no": 64, "name": "山本 しゅうじ", "district": "山科区", "party": "日本共産党"},
    {"no": 65, "name": "山本 陽子", "district": "西京区", "party": "日本共産党"},
    {"no": 66, "name": "湯浅 光彦", "district": "右京区", "party": "公明党"},
    {"no": 67, "name": "吉田 孝雄", "district": "公明党", "party": "公明党"},
]

# 異体字マッピング
NAME_CANONICAL_MAP = {
    "江村りさ": "江村理紗",
    "井崎敦子": "井﨑敦子",
    "繁隆夫": "繁隆夫",
}


def fit_to_16_9(src_path: Path, dest_path: Path):
    """キャプチャ画像を16:9中央配置し、Slate 900背景でパディング保存"""
    img = Image.open(src_path)

    canvas_w = TARGET_WIDTH * CANVAS_SCALE   # 2400
    canvas_h = TARGET_HEIGHT * CANVAS_SCALE  # 1350
    canvas = Image.new("RGB", (canvas_w, canvas_h), BG_COLOR)

    max_w = 2160
    max_h = 1200
    scale = min(max_w / img.width, max_h / img.height, 1.0)

    if scale < 1.0:
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    offset_x = (canvas_w - img.width) // 2
    offset_y = (canvas_h - img.height) // 2
    canvas.paste(img, (offset_x, offset_y))

    final_img = canvas.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(dest_path, "PNG", optimize=True)


def capture_councilor(page, base_url: str, c: dict, output_dir: Path) -> bool:
    """各議員のページへ遷移し、公式通し番号（c['no']）を適用して保存"""
    clean_name = c["name"].replace(" ", "").replace(" ", "")
    encoded_name = quote(clean_name)
    target_url = f"{base_url}/?speaker={encoded_name}"
    
    print(f"[{c['no']:02d}/67] 処理中: {c['name']} ({target_url})")

    try:
        page.goto(target_url, wait_until="networkidle", timeout=20000)
    except Exception as e:
        print(f"  ❌ ページ遷移エラー: {c['name']} ({e})")
        return False

    page.wait_for_timeout(1200)

    # 1. DOM操作（不要UIの非表示化 ＆ ブランドフッターの注入）
    injected = page.evaluate("""() => {
        const buttons = document.querySelectorAll('button');
        buttons.forEach(btn => {
            if (btn.innerText && (btn.innerText.includes('ポータルに戻る') || btn.innerText.includes('議員比較に追加'))) {
                const parent = btn.closest('div.flex');
                if (parent) parent.style.display = 'none';
            }
        });

        const headerCard = document.querySelector('main header') || document.querySelector('header.rounded-2xl');
        if (!headerCard) return false;

        if (!document.getElementById('injected-brand-footer')) {
            const footer = document.createElement('div');
            footer.id = 'injected-brand-footer';
            footer.style.cssText = `
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding-top: 16px;
                margin-top: 18px;
                border-top: 1px solid #E2E8F0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            `;
            footer.innerHTML = `
                <div style="font-size: 13px; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 6px;">
                    <span style="color: #4F46E5;">🏛️</span>
                    <span>議会のミカタ 京都</span>
                    <span style="font-weight: 500; color: #6366F1;">｜ gikai-mikata.jp</span>
                </div>
                <div style="font-size: 11px; color: #64748B; font-weight: 500;">
                    ※データは京都市会公式会議録より機械抽出（序列評価・採点はありません）
                </div>
            `;
            headerCard.appendChild(footer);
        }
        return true;
    }""")

    if not injected:
        print(f"  ⚠️ 対象カード要素の検出に失敗: {c['name']}")
        return False

    # 2. main header カードのキャプチャ
    header_element = page.locator("main header").first
    temp_path = output_dir / f"temp_{c['no']:02d}.png"
    header_element.screenshot(path=str(temp_path))

    # 3. 💡 要件定義に基づく公式通し番号でのファイル名採番
    out_filename = f"{c['no']:02d}_{encoded_name}.png"
    dest_path = output_dir / out_filename
    fit_to_16_9(temp_path, dest_path)

    if temp_path.exists():
        temp_path.unlink()

    print(f"  -> 保存完了: {dest_path.name}")
    return True


def main():
    parser = argparse.ArgumentParser(description="京都市会公式名簿順 OGP画像一括生成")
    parser.add_argument("--base-url", type=str, default="http://localhost:5173", help="接続先ベースURL")
    parser.add_argument("--speaker", type=str, default="", help="特定の議員のみテスト生成する場合に指定 (例: 江村理紗)")
    parser.add_argument("--limit", type=int, default=0, help="生成件数上限")
    args = parser.parse_args()

    # 💡 動的ソートを完全撤廃し、COUNCILORS_ORDERED をそのまま採用
    councilors = list(COUNCILORS_ORDERED)

    if args.speaker:
        target = args.speaker.strip().replace(" ", "").replace(" ", "")
        # 異体字変換
        target = NAME_CANONICAL_MAP.get(target, target)
        councilors = [c for c in councilors if target in c["name"].replace(" ", "")]
        if not councilors:
            print(f"❌ 指定された議員が見つかりませんでした: {args.speaker}")
            return

    if args.limit > 0:
        councilors = councilors[:args.limit]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print(f"🚀 京都市会公式名簿順（1〜67）カルテ画像生成開始 (対象: {len(councilors)} 件)")
    print(f"🌐 接続先: {args.base_url}")
    print(f"📁 出力先: {OUTPUT_DIR.resolve()}")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=2
        )
        page = context.new_page()

        success_count = 0
        for c in councilors:
            if capture_councilor(page, args.base_url, c, OUTPUT_DIR):
                success_count += 1

        browser.close()

    print("=" * 60)
    print(f"🎉 全処理完了: {success_count}/{len(councilors)} 件を名簿順通し番号で出力しました。")
    print("=" * 60)


if __name__ == "__main__":
    main()