import re
from pathlib import Path

app_path = Path("frontend/src/App.jsx")
if app_path.exists():
    text = app_path.read_text(encoding="utf-8")
    
    print("=== 1. ハッシュルート・クエリパラメータの処理箇所 ===")
    for line in text.splitlines():
        if any(k in line for k in ["location.hash", "location.search", "category=", "topic=", "speaker=", "viewMode", "modal"]):
            print(f"  {line.strip()[:100]}")

    print("\n=== 2. モーダル・ビューの条件分岐 ===")
    for line in text.splitlines():
        if any(k in line for k in ["<TimelineModal", "<BillDetailModal", "<CompareDashboard", "<MayorTrackerView", "<TopicDetailPage", "<CategoryDetailPage"]):
            print(f"  {line.strip()[:100]}")
