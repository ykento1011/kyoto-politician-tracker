import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from pathlib import Path

OUTPUT_DIR = Path("data-pipeline/raw_pdfs/nagoya")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def main():
    print("=" * 60)
    print("名古屋市 選挙公報PDF 一括ダウンローダー")
    print("=" * 60)
    
    url = input("🔗 選挙公報のPDFリンクがまとまっているページ（名古屋市公式など）のURLを入力してください:\n> ").strip()
    if not url:
        print("URLが入力されなかったため終了します。")
        return

    try:
        print(f"\n🌐 ページを取得中... {url}")
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        
        # .pdf で終わるリンクをすべて抽出
        pdf_links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.lower().endswith(".pdf"):
                full_url = urljoin(url, href)
                if full_url not in [link[1] for link in pdf_links]:
                    pdf_links.append((a_tag.get_text(strip=True) or "無名リンク", full_url))
        
        if not pdf_links:
            print("⚠️ ページ内にPDFリンクが見つかりませんでした。")
            return
            
        print(f"🎯 {len(pdf_links)} 件のPDFリンクを発見しました。ダウンロードを開始します...")
        
        downloaded = 0
        for name, pdf_url in pdf_links:
            # URLからファイル名を取得
            filename = pdf_url.split("/")[-1]
            save_path = OUTPUT_DIR / filename
            
            if save_path.exists():
                print(f"⏭️ スキップ (保存済): {filename}")
                continue
                
            print(f"⬇️ ダウンロード中: {filename} ({name})")
            pdf_resp = requests.get(pdf_url, headers=HEADERS, timeout=30)
            if pdf_resp.status_code == 200:
                save_path.write_bytes(pdf_resp.content)
                downloaded += 1
            else:
                print(f"❌ 失敗 (ステータス {pdf_resp.status_code}): {filename}")
            
            time.sleep(1) # サーバー負荷軽減
            
        print("\n🎉 処理完了！")
        print(f"✅ {downloaded} 件のPDFを {OUTPUT_DIR} に保存しました。")

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
