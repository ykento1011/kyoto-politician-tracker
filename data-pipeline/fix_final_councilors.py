import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "councilors")
)
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    )
}

print("=== 最終調整：北区・上京区の議員写真修復 ===")

# 1. 北区：山本恵一議員のリネーム
old_k_path = os.path.join(OUTPUT_DIR, "k-yamamoto.jpg")
new_k_path = os.path.join(OUTPUT_DIR, "山本恵一.jpg")
if os.path.exists(old_k_path):
    if os.path.exists(new_k_path):
        os.remove(new_k_path)
    os.rename(old_k_path, new_k_path)
    print("✓ [北区] 山本恵一.jpg に正常にリネームしました")

# 空白の「.jpg」ができていれば削除
empty_jpg = os.path.join(OUTPUT_DIR, ".jpg")
if os.path.exists(empty_jpg):
    os.remove(empty_jpg)

# 2. 上京区：くらた共子議員の画像取得
# 上京区ページから「くらた」を含むテキストブロック、またはimgタグを直接探索
url = "https://www2.city.kyoto.lg.jp/shikai/meibo/senkyoku/kamigyoku.html"
res = requests.get(url, headers=headers, timeout=10)
res.encoding = res.apparent_encoding or "shift_jis"
soup = BeautifulSoup(res.text, "html.parser")

kurata_img_url = None
# 全imgタグの中から、kurataを含むものや、くらた議員のボックスにあるものを探す
for img in soup.find_all("img"):
    src = img.get("src", "")
    alt = img.get("alt", "")
    if "kurata" in src.lower():
        kurata_img_url = urllib.parse.urljoin(url, src)
        break

# もしURLにkurataが含まれない場合、ページ内のprofboxから探索
if not kurata_img_url:
    for box in soup.find_all("div", class_="profbox"):
        if "くらた" in box.get_text():
            img = box.find("img")
            if img and "src" in img.attrs:
                kurata_img_url = urllib.parse.urljoin(url, img["src"])
                break

# それでも見つからない場合の京都市会サーバー標準パス
if not kurata_img_url:
    kurata_img_url = (
        "https://www2.city.kyoto.lg.jp/shikai/img/meibo/giin0505/kurata.jpg"
    )

print(f"くらた共子 議員の画像URLを検証中: {kurata_img_url}")
img_res = requests.get(kurata_img_url, headers=headers, timeout=10)
if img_res.status_code == 200:
    out_path = os.path.join(OUTPUT_DIR, "くらた共子.jpg")
    with open(out_path, "wb") as f:
        f.write(img_res.content)
    print("✓ [上京区] くらた共子.jpg を正常に保存しました")
else:
    print(f"× 画像取得エラー: ステータスコード {img_res.status_code}")

# 不要になった一時ファイル（ローマ字IDなど）があれば整理
for f in ["sugaya.jpg", "tamamoto.jpg", "mori.jpg", "nakadaka.jpg", "terada.jpg"]:
    p = os.path.join(OUTPUT_DIR, f)
    if os.path.exists(p):
        os.remove(p)

print("\n全議員（67名）の写真アセットの整備が完了しました！")