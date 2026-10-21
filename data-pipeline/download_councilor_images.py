import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

# 出力先ディレクトリ (frontend/public/councilors)
OUTPUT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "councilors")
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 京都市内 11行政区のスラッグ
DISTRICTS = [
    "kitaku",
    "kamigyoku",
    "sakyoku",
    "nakagyoku",
    "higashiyamaku",
    "shimogyoku",
    "minamiku",
    "ukyoku",
    "fushimiku",
    "yamashinaku",
    "nishikyoku",
]

BASE_URL = "https://www2.city.kyoto.lg.jp/shikai/meibo/senkyoku/{}.html"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like"
        " Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

print("京都市会HPから議員顔写真のダウンロードを開始します...")
saved_count = 0

for dist in DISTRICTS:
    target_url = BASE_URL.format(dist)
    try:
        res = requests.get(target_url, headers=headers, timeout=10)
        # 京都市会HPのShift_JIS / CP932エンコードに対応
        res.encoding = res.apparent_encoding or "shift_jis"
        soup = BeautifulSoup(res.text, "html.parser")

        boxes = soup.find_all("div", class_="profbox")
        for box in boxes:
            # 議員名の取得
            name_tag = box.find(["h3", "h4"])
            if not name_tag:
                continue

            # ルビ等のspanを削除して名前テキストのみ抽出
            for span in name_tag.find_all("span"):
                span.decompose()
            raw_name = name_tag.get_text().strip()
            # 空白（全角・半角）をすべて除去して名前に統一
            clean_name = re.sub(r"\s+", "", raw_name)

            # 画像URLの取得
            img_container = box.find("p", class_="profimg")
            if not img_container or not img_container.find("img"):
                continue

            img_src = img_container.find("img")["src"]
            full_img_url = urllib.parse.urljoin(target_url, img_src)

            # 画像のダウンロードと保存
            img_res = requests.get(full_img_url, headers=headers, timeout=10)
            if img_res.status_code == 200:
                out_path = os.path.join(OUTPUT_DIR, f"{clean_name}.jpg")
                with open(out_path, "wb") as f:
                    f.write(img_res.content)
                print(f"[{dist}] 保存成功: {clean_name}.jpg")
                saved_count += 1
            else:
                print(f"[{dist}] 画像取得失敗: {clean_name} ({img_res.status_code})")

    except Exception as e:
        print(f"[{dist}] スクレイピングエラー: {e}")

print(f"\nダウンロード完了: 合計 {saved_count} 名の顔写真を保存しました。")
print(f"保存先: {OUTPUT_DIR}")