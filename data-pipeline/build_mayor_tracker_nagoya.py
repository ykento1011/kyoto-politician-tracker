import json
from pathlib import Path
from datetime import datetime

# パス設定
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
SEED_FILE = BASE_DIR / "data" / "nagoya_mayor_tracker_seed.json"
OUTPUT_JSON = PROJECT_ROOT / "frontend" / "public" / "data" / "nagoya_mayor_tracker.json"

def build_nagoya_mayor_tracker():
    if not SEED_FILE.exists():
        print(f"❌ シードファイルが見つかりません: {SEED_FILE}")
        return False
        
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    if "metadata" in data and isinstance(data["metadata"], dict):
        data["metadata"]["last_updated"] = today_str
    if "summary_stats" in data and isinstance(data["summary_stats"], dict):
        data["summary_stats"]["last_updated"] = today_str
        
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    pledges_count = len(data.get("pledges", []))
    print(f"✅ 名古屋市長 政策・予算トラッカーを更新保存しました: {OUTPUT_JSON.name} (政策件数: {pledges_count} 件)")
    return True

if __name__ == "__main__":
    build_nagoya_mayor_tracker()
