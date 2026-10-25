import os
import time
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SAVE_DIR = BASE_DIR / "bulletins_osaka"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# 大阪市24行政区の一覧（公式番号 01〜24 に対応）
DISTRICTS = [
    (1, "北区"), (2, "都島区"), (3, "福島区"), (4, "此花区"),
    (5, "中央区"), (6, "西区"), (7, "港区"), (8, "大正区"),
    (9, "天王寺区"), (10, "浪速区"), (11, "西淀川区"), (12, "淀川区"),
    (13, "東淀川区"), (14, "東成区"), (15, "生野区"), (16, "旭区"),
    (17, "城東区"), (18, "鶴見区"), (19, "阿倍野区"), (20, "住之江区"),
    (21, "住吉区"), (22, "東住吉区"), (23, "平野区"), (24, "西成区")
]

BASE_URL = "https://www.city.osaka.lg.jp/contents/wdu240/shikai/kouhosha/{num:02d}.pdf"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print(f"📥 大阪市議選（2023年4月9日執行）選挙公報PDFの一括ダウンロードを開始します...")
print(f"保存先: {SAVE_DIR.resolve()}\n")

success_count = 0
for num, name in DISTRICTS:
    url = BASE_URL.format(num=num)
    filename = f"{num:02d}_{name}.pdf"
    filepath = SAVE_DIR / filename
    
    if filepath.exists() and filepath.stat().st_size > 1000:
        print(f"⏩ [{num:02d}/24] {name}: 既に存在するためスキップ ({filepath.name})")
        success_count += 1
        continue

    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200 and len(res.content) > 1000:
            with open(filepath, "wb") as f:
                f.write(res.content)
            print(f"✅ [{num:02d}/24] {name}: 取得完了 ({len(res.content):,} bytes) -> {filename}")
            success_count += 1
        else:
            print(f"⚠️ [{num:02d}/24] {name}: HTTPステータス {res.status_code} (URL: {url})")
    except Exception as e:
        print(f"❌ [{num:02d}/24] {name}: エラー発生 ({e})")
    
    time.sleep(1) # サーバー負荷防止

print(f"\n🎉 完了: 全24区中 {success_count} 区の公報PDFを保存しました。")
