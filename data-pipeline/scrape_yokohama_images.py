import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATS_FILE = BASE_DIR / "frontend/public/data/yokohama_speaker_stats.json"
IMG_DIR = BASE_DIR / "frontend/public/councilors/yokohama"

IMG_DIR.mkdir(parents=True, exist_ok=True)

MEIBO_URLS = [
    f"https://www.city.yokohama.lg.jp/shikai/giin/kubetsu/meibo{i}.html" for i in range(11, 17)
]
HEADERS = {"User-Agent": "Mozilla/5.0"}

def clean_name(name):
    return re.sub(r'[\s ]+', '', str(name))

def main():
    if not STATS_FILE.exists():
        print(f"❌ 議員マスタが見つかりません: {STATS_FILE}")
        return

    stats = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    
    # "speaker" キーを優先して取得するように修正
    target_names = {}
    for s in stats:
        name = s.get("speaker") or s.get("name")
        if name:
            target_names[clean_name(name)] = name
            
    print(f"🎯 抽出対象: {len(target_names)} 名の現職議員")

    downloaded = 0

    for url in MEIBO_URLS:
        print(f"\n🌐 ページ取得中: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content.decode("utf-8", errors="replace"), "html.parser")
            
            for img in soup.find_all("img"):
                src = img.get("src", "")
                alt = clean_name(img.get("alt", ""))
                
                if not src:
                    continue
                
                parent_text = clean_name(img.find_parent().get_text()) if img.find_parent() else ""
                
                matched_name = None
                for c_name in target_names.keys():
                    if c_name in alt or c_name in parent_text:
                        matched_name = c_name
                        break
                
                if matched_name:
                    img_url = urljoin(url, src)
                    file_path = IMG_DIR / f"{matched_name}.jpg"
                    
                    if file_path.exists():
                        continue
                    
                    img_resp = requests.get(img_url, headers=HEADERS, timeout=10)
                    if img_resp.status_code == 200:
                        file_path.write_bytes(img_resp.content)
                        print(f"✅ 保存成功: {matched_name}.jpg")
                        downloaded += 1
                        time.sleep(0.5)
                        
        except Exception as e:
            print(f"⚠️ {url} の取得中にエラーが発生しました: {e}")

    print("\n" + "=" * 60)
    print(f"🎉 処理完了: 新たに {downloaded} 件の画像をダウンロードしました。")
    print(f"📁 保存先: {IMG_DIR.relative_to(BASE_DIR)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
