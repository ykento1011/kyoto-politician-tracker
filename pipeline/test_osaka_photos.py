import urllib.request
import re
from bs4 import BeautifulSoup

INDEX_URL = "https://www.city.osaka.lg.jp/shikai/page/0000310422.html"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

req = urllib.request.Request(INDEX_URL, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    
    soup = BeautifulSoup(html, "html.parser")
    # 各区へのリンクを抽出
    ward_links = []
    for a in soup.find_all("a", href=True):
        if "選挙区別名簿（" in a.text and "/shikai/page/" in a["href"]:
            full_url = urllib.parse.urljoin(INDEX_URL, a["href"])
            ward_links.append((a.text.strip(), full_url))
            
    print(f"✅ 見つかった選挙区ページ: {len(ward_links)} 件")
    for name, link in ward_links[:3]:
        print(f"  - {name}: {link}")

    # 1ページ目（北区など）をテスト取得して議員画像構造を確認
    if ward_links:
        test_name, test_url = ward_links[0]
        req_sub = urllib.request.Request(test_url, headers=headers)
        with urllib.request.urlopen(req_sub) as r:
            sub_html = r.read().decode("utf-8")
        sub_soup = BeautifulSoup(sub_html, "html.parser")
        
        print(f"\n【{test_name} の画像タグ調査】")
        for img in sub_soup.find_all("img"):
            alt = img.get("alt", "")
            src = img.get("src", "")
            if "写真" in alt or "議員" in alt:
                print(f"  議員写真候補: alt='{alt}' | src='{src}'")

except Exception as e:
    print("❌ エラー発生:", e)
