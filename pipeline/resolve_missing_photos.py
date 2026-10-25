import json
import urllib.request
import urllib.parse
import re
from bs4 import BeautifulSoup
from pathlib import Path

IMAGE_DIR = Path("frontend/public/councilors")
INDEX_URL = "https://www.city.osaka.lg.jp/shikai/page/0000310422.html"
BASE_SHIKAI = "https://www.city.osaka.lg.jp/shikai/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 1. 判明しているリネーム処理
rename_map = {
    "公明党大阪市会議員団中田光一郎.jpg": "中田光一郎.jpg",
    "りゆき.jpg": "馬場のりゆき.jpg"
}

for old_name, new_name in rename_map.items():
    old_p = IMAGE_DIR / old_name
    new_p = IMAGE_DIR / new_name
    if old_p.exists():
        if new_p.exists():
            new_p.unlink()
        old_p.rename(new_p)
        print(f"✅ リネーム完了: {old_name} -> {new_name}")

# 残りの未取得議員
missing = ["佐々木りえ", "司隆史", "山田はじめ", "岡崎太", "永井啓介", "高見亮"]
print(f"\n🔍 残り {len(missing)} 名の調査を開始: {missing}")

# 2. 24区のページを巡回して各議員の掲載箇所・imgタグを詳細探索
req = urllib.request.Request(INDEX_URL, headers=HEADERS)
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode("utf-8")
soup = BeautifulSoup(html, "html.parser")
ward_links = [(a.text.strip(), urllib.parse.urljoin(INDEX_URL, a["href"])) 
              for a in soup.find_all("a", href=True) 
              if a.text.strip().endswith("区") and "/shikai/page/" in a["href"]]

found_images = {}

for w_name, w_url in ward_links:
    try:
        req_sub = urllib.request.Request(w_url, headers=HEADERS)
        with urllib.request.urlopen(req_sub) as r:
            s_html = r.read().decode("utf-8")
    except Exception as e:
        continue

    s_soup = BeautifulSoup(s_html, "html.parser")

    # ページ内の全imgタグを表示
    for m in list(missing):
        # 議員名がHTML内に含まれているか
        if m in s_html:
            print(f"  📌 {m} が {w_name} に見つかりました")
            # 周辺の画像を探す
            for img in s_soup.find_all("img"):
                alt = img.get("alt", "")
                src = img.get("src", "")
                if m in alt or m[:2] in alt:
                    clean_src = src.lstrip("./")
                    img_url = urllib.parse.urljoin(BASE_SHIKAI, clean_src) if clean_src.startswith("cmsfiles/") else urllib.parse.urljoin(w_url, src)
                    save_path = IMAGE_DIR / f"{m}.jpg"
                    try:
                        req_img = urllib.request.Request(img_url, headers=HEADERS)
                        with urllib.request.urlopen(req_img) as ir:
                            data = ir.read()
                            if len(data) > 500:
                                with open(save_path, "wb") as f:
                                    f.write(data)
                                print(f"    🎯 画像取得成功: {m} ({img_url})")
                                missing.remove(m)
                                break
                    except Exception as err:
                        print(f"    ❌ 画像取得エラー: {err}")

if missing:
    print(f"\n⚠️ 依然として見つからない議員: {missing}")
    # 苗字のみでの検索や正字一覧ページの確認
    for m in missing:
        surname = m[:2]
        print(f"--- 検索: {m} (苗字: {surname}) ---")
        for w_name, w_url in ward_links:
            req_sub = urllib.request.Request(w_url, headers=HEADERS)
            with urllib.request.urlopen(req_sub) as r:
                s_html = r.read().decode("utf-8")
            if surname in s_html:
                s_soup = BeautifulSoup(s_html, "html.parser")
                for img in s_soup.find_all("img"):
                    alt = img.get("alt", "")
                    if "議員の写真" in alt and (surname in alt or m in alt):
                        print(f"    候補発見 [{w_name}]: alt='{alt}', src='{img.get('src')}'")
