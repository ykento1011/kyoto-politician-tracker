import json
import urllib.request
import urllib.parse
import re
from bs4 import BeautifulSoup
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = PROJECT_ROOT / "frontend" / "public" / "councilors"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

COUNCILORS_JSON = PROJECT_ROOT / "frontend" / "public" / "data" / "osaka_councilors.json"
INDEX_URL = "https://www.city.osaka.lg.jp/shikai/page/0000310422.html"
BASE_SHIKAI = "https://www.city.osaka.lg.jp/shikai/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def download_image(url, save_path):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            if len(data) > 500:  # 正常な画像サイズか判定
                with open(save_path, "wb") as f:
                    f.write(data)
                return True
        return False
    except Exception as e:
        print(f"  ❌ 取得エラー: {url} -> {e}")
        return False

def main():
    print("=" * 60)
    print("📸 大阪市会 全議員プロフィール画像 一括ダウンロード")
    print("=" * 60)

    # 1. 登録済み議員名簿の読み込み
    known_councilors = []
    if COUNCILORS_JSON.exists():
        with open(COUNCILORS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                known_councilors = [item["name"].replace(" ", "").replace(" ", "") for item in data if "name" in item]
            elif isinstance(data, dict):
                known_councilors = [name.replace(" ", "").replace(" ", "") for name in data.keys()]
    print(f"📋 追跡対象議員数: {len(known_councilors)} 名")

    # 2. 選挙区名簿トップから全区のURLを取得
    req = urllib.request.Request(INDEX_URL, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode("utf-8")
    except Exception as e:
        print(f"❌ インデックス取得失敗: {e}")
        return

    soup = BeautifulSoup(html, "html.parser")
    ward_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.text.strip()
        if text.endswith("区") and "/shikai/page/" in href:
            full_url = urllib.parse.urljoin(INDEX_URL, href)
            ward_links.append((text, full_url))

    print(f"🗺️ 選挙区ページ: {len(ward_links)} 区")

    # 3. 各区ページから画像と議員名を紐付けて保存
    saved_count = 0
    matched_names = set()

    for ward_name, ward_url in ward_links:
        try:
            req_sub = urllib.request.Request(ward_url, headers=HEADERS)
            with urllib.request.urlopen(req_sub) as r:
                sub_html = r.read().decode("utf-8")
        except Exception as e:
            print(f"❌ {ward_name} 取得失敗: {e}")
            continue

        sub_soup = BeautifulSoup(sub_html, "html.parser")
        for img in sub_soup.find_all("img"):
            alt = img.get("alt", "").replace(" ", "").replace(" ", "")
            src = img.get("src", "").strip()

            if not src or "議員の写真" not in alt:
                continue

            # 既知の議員名とマッチング
            target_name = None
            for name in known_councilors:
                if name in alt:
                    target_name = name
                    break

            # 名簿から特定できない場合は alt から「〜議員の写真」の前方を安全に抽出
            if not target_name:
                m = re.search(r'(?:団の|会派.*?の|の)?([^の]+?)議員の写真', alt)
                if m:
                    target_name = m.group(1).replace(" ", "").replace(" ", "")

            if not target_name:
                continue

            # URLを https://www.city.osaka.lg.jp/shikai/cmsfiles/... に解決
            clean_src = re.sub(r'^\./', '', src)
            if clean_src.startswith("cmsfiles/"):
                img_url = urllib.parse.urljoin(BASE_SHIKAI, clean_src)
            else:
                img_url = urllib.parse.urljoin(ward_url, src)

            save_file = IMAGE_DIR / f"{target_name}.jpg"

            # 取得と保存
            if save_file.exists() and save_file.stat().st_size > 1000:
                matched_names.add(target_name)
                saved_count += 1
                continue

            if download_image(img_url, save_file):
                matched_names.add(target_name)
                saved_count += 1
                print(f"  ✅ 取得成功: {target_name} ({ward_name})")

    print("\n" + "=" * 60)
    print(f"🎉 ダウンロード完了: {len(matched_names)} / {len(known_councilors)} 名の議員画像を保存しました。")
    print(f"📁 保存先: {IMAGE_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
