import json
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = PROJECT_ROOT / "frontend" / "public" / "councilors"
COUNCILORS_FILE = PROJECT_ROOT / "frontend" / "public" / "data" / "osaka_councilors.json"

INDEX_URL = "https://www.city.osaka.lg.jp/shikai/page/0000310422.html"
BASE_SHIKAI = "https://www.city.osaka.lg.jp/shikai/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def download_image(url, save_path):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            if len(data) > 500:
                with open(save_path, "wb") as f:
                    f.write(data)
                return True
    except Exception as e:
        print(f"  ❌ 取得エラー: {url} -> {e}")
    return False

def main():
    print("=" * 60)
    print("🔧 大阪市会 議員写真ファイル名の名寄せ・完全補完")
    print("=" * 60)

    # 1. osaka_councilors.json の議員一覧読み込み
    with open(COUNCILORS_FILE, "r", encoding="utf-8") as f:
        c_data = json.load(f)

    # リスト形式または辞書形式に対応
    if isinstance(c_data, list):
        target_names = [item["name"].replace(" ", "").replace(" ", "") for item in c_data if "name" in item]
    elif isinstance(c_data, dict):
        target_names = [name.replace(" ", "").replace(" ", "") for name in c_data.keys()]
    else:
        print("❌ 不明なJSON形式です")
        return

    print(f"📋 システム登録議員数: {len(target_names)} 名")

    # 2. 会派名が含まれているファイルの修正（中田光一郎など）
    bad_file = IMAGE_DIR / "公明党大阪市会議員団中田光一郎.jpg"
    if bad_file.exists():
        correct_file = IMAGE_DIR / "中田光一郎.jpg"
        bad_file.rename(correct_file)
        print("✅ リネーム完了: 公明党大阪市会議員団中田光一郎.jpg -> 中田光一郎.jpg")

    # 3. 24区ページを再スキャンして、未取得議員を正確に特定してダウンロード
    # 「りゆき」のように alt の切り出しで欠落したケースを、登録議員名が含まれるかで直接マッチング
    existing_files = {p.stem for p in IMAGE_DIR.glob("*.jpg")}
    missing = [name for name in target_names if name not in existing_files]
    print(f"🔍 未取得または不一致の議員: {len(missing)} 名")
    if missing:
        print("  未取得リスト:", ", ".join(missing))

    if missing:
        req = urllib.request.Request(INDEX_URL, headers=HEADERS)
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode("utf-8")
        soup = BeautifulSoup(html, "html.parser")
        ward_links = [urllib.parse.urljoin(INDEX_URL, a["href"]) for a in soup.find_all("a", href=True) if a.text.strip().endswith("区") and "/shikai/page/" in a["href"]]

        for w_url in ward_links:
            try:
                req_sub = urllib.request.Request(w_url, headers=HEADERS)
                with urllib.request.urlopen(req_sub) as r:
                    s_html = r.read().decode("utf-8")
            except Exception:
                continue

            s_soup = BeautifulSoup(s_html, "html.parser")
            for img in s_soup.find_all("img"):
                alt = img.get("alt", "").replace(" ", "").replace(" ", "")
                src = img.get("src", "").strip()
                if not src:
                    continue

                for m_name in list(missing):
                    # alt属性の中に議員名がまるごと含まれているか照合
                    if m_name in alt:
                        clean_src = src.lstrip("./")
                        img_url = urllib.parse.urljoin(BASE_SHIKAI, clean_src) if clean_src.startswith("cmsfiles/") else urllib.parse.urljoin(w_url, src)
                        save_p = IMAGE_DIR / f"{m_name}.jpg"
                        if download_image(img_url, save_p):
                            print(f"  🎯 補完成功: {m_name} ({img_url})")
                            missing.remove(m_name)
                        break

    # 4. 最終突合確認
    final_existing = {p.stem for p in IMAGE_DIR.glob("*.jpg")}
    matched = [name for name in target_names if name in final_existing]
    print("\n" + "=" * 60)
    print(f"🎉 最終照合結果: {len(matched)} / {len(target_names)} 名の画像が完全に揃いました！")
    if len(matched) < len(target_names):
        still_missing = [name for name in target_names if name not in final_existing]
        print(f"⚠️ 残りの未取得議員 ({len(still_missing)}名):", ", ".join(still_missing))
    print("=" * 60)

if __name__ == "__main__":
    main()
