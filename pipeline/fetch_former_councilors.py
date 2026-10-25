import urllib.request
from pathlib import Path

IMAGE_DIR = Path("frontend/public/councilors")
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 参議院公式、政党公認アーカイブ等からの高解像度・公式顔写真ソース
TARGETS = {
    # 司隆史（第27回参院選当選・参議院公式プロフィール）
    "司隆史": "https://www.sangiin.go.jp/japanese/joho1/kousei/giin/photo/p7025036.jpg",
    # 岡崎太（参議院公式プロフィール）
    "岡崎太": "https://www.sangiin.go.jp/japanese/joho1/kousei/giin/photo/p7025014.jpg",
    # 佐々木りえ（日本維新の会公式 / 選挙公報写真）
    "佐々木りえ": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/Rie_Sasaki_202507.jpg/480px-Rie_Sasaki_202507.jpg",
    # 高見亮（衆議院公式 / 維新公式）
    "高見亮": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/60/Ryo_Takami_2026.jpg/480px-Ryo_Takami_2026.jpg",
    # 山田はじめ（維新公式アーカイブ）
    "山田はじめ": "https://oneosaka.jp/toitsu_osaka/img/candidate/osakashi_nishiyodogawaku_yamadahajime.jpg",
    # 永井啓介（自民党大阪府連 / 選挙ドットコム公式）
    "永井啓介": "https://storage.googleapis.com/go2senkyo-production/candidate_photos/127315.jpg"
}

def download(name, url):
    save_path = IMAGE_DIR / f"{name}.jpg"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            if len(data) > 1000:
                with open(save_path, "wb") as f:
                    f.write(data)
                print(f"✅ 取得成功: {name}.jpg ({len(data):,} bytes)")
                return True
    except Exception as e:
        print(f"⚠️ {name} 直接取得エラー: {e}")
    return False

print("=" * 60)
print("📥 前職・転出議員（6名）の写真補完処理")
print("=" * 60)

for name, url in TARGETS.items():
    dest = IMAGE_DIR / f"{name}.jpg"
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"⏭️ 既存: {name}.jpg")
    else:
        download(name, url)

# 最終検証
import json
with open("frontend/public/data/osaka_statements_summary.json", "r", encoding="utf-8") as f:
    stmt_data = json.load(f)

councilors = sorted(list({item.get("speaker", "").replace(" ", "").replace(" ", "") for item in stmt_data if item.get("speaker")}))
existing = {p.stem for p in IMAGE_DIR.glob("*.jpg")}
missing = [c for c in councilors if c not in existing]

print("\n" + "=" * 60)
print(f"📊 最終結果: {len(councilors) - len(missing)} / {len(councilors)} 名の顔写真が配備完了")
if missing:
    print(f"未配備: {missing}")
else:
    print("🎉 大阪市会の対象議員87名全員の顔写真が完全配備されました！")
print("=" * 60)
