#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
議員カルテ画像 自動生成システム（Playwright版）
SpeakerDetailViewのDOMを高精細キャプチャし、16:9 OGP画像を一括生成する
"""

import os
import sys
import json
import time
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
PUBLIC_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"
STATEMENTS_SUMMARY_FILE = PUBLIC_DATA_DIR / "statements_summary.json"
OUTPUT_DIR = BASE_DIR / "output_cards"

# 16:9 出力解像度
TARGET_WIDTH = 1200
TARGET_HEIGHT = 675
CANVAS_SCALE = 2  # 内部作業解像度: 2400x1350 (Retina品質)
BG_COLOR = (15, 23, 42)  # Slate 900 (#0F172A)

# 異体字・通称名マッピング
NAME_CANONICAL_MAP = {
    "江村理紗": "江村りさ",
    "江村りさ": "江村理紗",
    "井﨑敦子": "井崎敦子",
    "井崎敦子": "井﨑敦子",
    "繁隆夫": "繁隆夫",
    "繁隆夫": "繁隆夫",
}


def load_target_councilors() -> list:
    """statements_summary.json から現任期議員リストを抽出"""
    if not STATEMENTS_SUMMARY_FILE.exists():
        print(f"[警告] {STATEMENTS_SUMMARY_FILE} が見つかりません。デフォルトリストを使用します。")
        return [
            {"slug": "江村理紗", "name": "江村理紗"},
            {"slug": "片桐直哉", "name": "片桐直哉"},
        ]

    with open(STATEMENTS_SUMMARY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    seen = set()
    councilors = []
    for item in data:
        raw_name = item.get("speaker", "").strip().replace(" ", "").replace(" ", "")
        if raw_name and raw_name not in seen:
            seen.add(raw_name)
            councilors.append({
                "slug": raw_name,
                "name": raw_name,
                "district": item.get("district", ""),
                "party": item.get("partyGroup", "")
            })

    return councilors


def fit_to_16_9(src_path: Path, dest_path: Path):
    """キャプチャ画像を16:9（1200x675）の中央に配置し、Slate 900背景でパディング"""
    img = Image.open(src_path)

    canvas_w = TARGET_WIDTH * CANVAS_SCALE   # 2400
    canvas_h = TARGET_HEIGHT * CANVAS_SCALE  # 1350
    canvas = Image.new("RGB", (canvas_w, canvas_h), BG_COLOR)

    # 左右・上下に余白を設けてスケール調整
    max_w = 2160
    max_h = 1200
    scale = min(max_w / img.width, max_h / img.height, 1.0)

    if scale < 1.0:
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # 中央配置
    offset_x = (canvas_w - img.width) // 2
    offset_y = (canvas_h - img.height) // 2
    canvas.paste(img, (offset_x, offset_y))

    # 1200x675へリサイズして保存
    final_img = canvas.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(dest_path, "PNG", optimize=True)


def capture_councilor(page, base_url: str, councilor: dict, output_dir: Path):
    """1名分の議員詳細画面へ遷移し、フッターを注入してヘッダーカードをキャプチャ"""
    name = councilor["name"]
    slug = councilor["slug"]

    target_url = f"{base_url}/?speaker={quote(name)}"
    print(f"▶ 撮影開始: {name} ({target_url})")

    try:
        page.goto(target_url, wait_until="networkidle", timeout=15000)
    except Exception as e:
        alt_name = NAME_CANONICAL_MAP.get(name)
        if alt_name:
            target_url = f"{base_url}/?speaker={quote(alt_name)}"
            page.goto(target_url, wait_until="networkidle", timeout=15000)
        else:
            print(f"  ❌ ページ読み込み失敗: {name} ({e})")
            return False

    # アニメーション待機（Recharts描画やTailwind遷移の完了）
    page.wait_for_timeout(1000)

    # 1. 不要な上部ボタンの非表示化 & main headerへのブランドフッター動的注入
    injected = page.evaluate("""() => {
        // 「ポータルに戻る」などのボタン群を非表示化
        const topNavButtons = document.querySelectorAll('button');
        topNavButtons.forEach(btn => {
            if (btn.innerText && (btn.innerText.includes('ポータルに戻る') || btn.innerText.includes('議員比較に追加'))) {
                const parentNav = btn.closest('div');
                if (parentNav && parentNav.classList.contains('flex')) {
                    parentNav.style.display = 'none';
                }
            }
        });

        // 💡 ナビバー（header）を除外し、main内のheaderカードのみを取得
        const headerCard = document.querySelector('main header') || document.querySelector('header.rounded-2xl');
        if (!headerCard) return false;

        // ブランドフッターの注入（重複防止）
        if (!document.getElementById('injected-brand-footer')) {
            const footer = document.createElement('div');
            footer.id = 'injected-brand-footer';
            footer.style.cssText = `
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding-top: 16px;
                margin-top: 20px;
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
                    ※京都市会公式会議録より機械抽出（序列評価・採点はありません）
                </div>
            `;
            headerCard.appendChild(footer);
        }
        return true;
    }""")

    if not injected:
        print(f"  ⚠️ main内のヘッダー要素が見つかりませんでした: {name}")
        return False

    # 2. 💡 main内のheaderカードを特定して高精度キャプチャ
    header_element = page.locator("main header").first
    temp_path = output_dir / f"temp_{slug}.png"
    header_element.screenshot(path=str(temp_path))

    # 3. Pillowで16:9（1200x675）に整形
    final_path = output_dir / f"{slug}_card.png"
    fit_to_16_9(temp_path, final_path)

    # 一時ファイルの削除
    if temp_path.exists():
        temp_path.unlink()

    print(f"  ✅ 出力完了: {final_path.name}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Playwrightによる議員カルテOGP画像自動生成")
    parser.add_argument("--base-url", type=str, default="http://localhost:5173", help="接続先URL (デフォルト: http://localhost:5173)")
    parser.add_argument("--speaker", type=str, default="", help="特定の議員のみ生成する場合に指定 (例: 江村理紗)")
    parser.add_argument("--limit", type=int, default=0, help="生成件数上限 (0なら全件)")
    args = parser.parse_args()

    councilors = load_target_councilors()

    if args.speaker:
        target_name = args.speaker.strip().replace(" ", "")
        councilors = [c for c in councilors if target_name in c["name"] or c["name"] in target_name]
        if not councilors:
            alt = NAME_CANONICAL_MAP.get(target_name)
            if alt:
                councilors = [c for c in load_target_councilors() if alt in c["name"]]

        if not councilors:
            print(f"❌ 対象議員が見つかりませんでした: {args.speaker}")
            return

    if args.limit > 0:
        councilors = councilors[:args.limit]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"=== 議員カルテOGP Playwrightキャプチャ開始 ({len(councilors)}件) ===")
    print(f"接続先: {args.base_url}")
    print(f"出力先: {OUTPUT_DIR.resolve()}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=2  # Retina解像度で鮮明に撮影
        )
        page = context.new_page()

        success_count = 0
        for c in councilors:
            if capture_councilor(page, args.base_url, c, OUTPUT_DIR):
                success_count += 1

        browser.close()

    print(f"=== 全工程完了: {success_count}/{len(councilors)} 件生成成功 ===")


if __name__ == "__main__":
    main()