import os
import time
import requests
from pathlib import Path
from tqdm import tqdm

BASE_URL = "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000313/313230/"
SAVE_DIR = Path(__file__).resolve().parent / "bulletins"

# 2023年4月9日執行 京都市議会議員一般選挙 公報ファイル一覧
BULLETIN_FILES = [
    {"district": "北区", "filename": "01kita.pdf"},
    {"district": "上京区", "filename": "02kamigyo.pdf"},
    {"district": "左京区", "filename": "03sakyo1.pdf"},
    {"district": "左京区", "filename": "03sakyo2.pdf"},
    {"district": "中京区", "filename": "04nakagyo.pdf"},
    {"district": "東山区", "filename": "05higashiyama.pdf"},
    {"district": "山科区", "filename": "06yamashina.pdf"},
    {"district": "下京区", "filename": "07shimogyo.pdf"},
    {"district": "南区", "filename": "08minami.pdf"},
    {"district": "右京区", "filename": "09ukyo1.pdf"},
    {"district": "右京区", "filename": "09ukyo2.pdf"},
    {"district": "西京区", "filename": "10nishikyo1.pdf"},
    {"district": "西京区", "filename": "10nishikyo2.pdf"},
    {"district": "伏見区", "filename": "11fushimi1.pdf"},
    {"district": "伏見区", "filename": "11fushimi2.pdf"},
    {"district": "伏見区", "filename": "11fushimi3.pdf"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.city.kyoto.lg.jp/senkyo/page/0000313230.html"
}

def download_file(url: str, dest_path: Path, max_retries: int = 3):
    if dest_path.exists() and dest_path.stat().st_size > 10000:
        print(f"[スキップ] 既に存在します: {dest_path.name}")
        return True

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, stream=True, timeout=30)
            if response.status_code == 200:
                total_size = int(response.headers.get("content-length", 0))
                with open(dest_path, "wb") as f, tqdm(
                    desc=dest_path.name,
                    total=total_size,
                    unit="iB",
                    unit_scale=True,
                    unit_divisor=1024,
                    leave=False
                ) as bar:
                    for chunk in response.iter_content(chunk_size=8192):
                        size = f.write(chunk)
                        bar.update(size)
                print(f"[完了] ダウンロード成功: {dest_path.name}")
                return True
            else:
                print(f"[警告] ステータスコード {response.status_code} ({attempt}/{max_retries}): {url}")
        except Exception as e:
            print(f"[エラー] 接続エラー ({attempt}/{max_retries}): {e}")
        time.sleep(2)
    return False

def main():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"=== 選挙公報PDFダウンロード開始 (全{len(BULLETIN_FILES)}ファイル) ===")
    
    success_count = 0
    for item in BULLETIN_FILES:
        url = BASE_URL + item["filename"]
        dest = SAVE_DIR / item["filename"]
        if download_file(url, dest):
            success_count += 1
        time.sleep(1)

    print(f"\nダウンロード完了: {success_count}/{len(BULLETIN_FILES)} 件が正常に保存されました。")

if __name__ == "__main__":
    main()