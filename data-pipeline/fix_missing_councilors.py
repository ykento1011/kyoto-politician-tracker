import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "councilors")
)
BASE_URL = "https://www2.city.kyoto.lg.jp/shikai/meibo/senkyoku/{}.html"
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    )
}

print("=== 北区・上京区の構造チェックと再取得 ===")

for dist in ["kitaku", "kamigyoku"]:
    url = BASE_URL.format(dist)
    res = requests.get(url, headers=headers, timeout=10)
    res.encoding = res.apparent_encoding or "shift_jis"
    soup = BeautifulSoup(res.text, "html.parser")

    boxes = soup.find_all("div", class_="profbox")
    print(f"\n【{dist}】 検出ボックス数: {len(boxes)}")

    for idx, box in enumerate(boxes):
        box_id = box.get("id", "no-id")
        # h3, h4 だけでなくテキスト全体から名前を抽出
        raw_text = box.get_text()

        # 画像タグ
        img_tag = box.find("img")
        img_src = img_tag["src"] if img_tag else "画像なし"

        # 見出しタグの確認
        heading = box.find(["h3", "h4", "p"])
        heading_text = (
            re.sub(r"\s+", "", heading.get_text()) if heading else "見出しなし"
        )

        print(
            f"  [{idx+1}] ID: {box_id:<12} | 見出し: {heading_text:<15} |"
            f" 画像: {img_src}"
        )

        # 画像のダウンロード
        if img_tag and "src" in img_tag.attrs:
            full_img_url = urllib.parse.urljoin(url, img_tag["src"])
            img_res = requests.get(full_img_url, headers=headers, timeout=10)
            if img_res.status_code == 200:
                # box_id をフォールバック用ファイル名としても保持
                clean_name = (
                    re.sub(r"\（.*?\）", "", heading_text) if heading else box_id
                )
                if not clean_name or clean_name == "画像なし":
                    clean_name = box_id

                file_path = os.path.join(OUTPUT_DIR, f"{clean_name}.jpg")
                with open(file_path, "wb") as f:
                    f.write(img_res.content)
                print(f"      -> 保存: {clean_name}.jpg (ID: {box_id})")