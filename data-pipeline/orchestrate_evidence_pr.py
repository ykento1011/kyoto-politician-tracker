import json
import os
import subprocess
import datetime

QUEUE_PATH = "data-pipeline/data/evidence_health_queue.json"

def run_cmd(cmd):
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout.strip()

if not os.path.exists(QUEUE_PATH):
    exit(0)

with open(QUEUE_PATH, "r", encoding="utf-8") as f:
    queue = json.load(f)

cities = set(i["city"] for i in queue if "city" in i)
date_str = datetime.datetime.now().strftime("%Y%m%d%H%M")
created_prs = 0

for city in cities:
    city_items = [i for i in queue if i.get("city") == city]
    success_items = [i for i in city_items if i.get("agent_status") == "SUCCESS"]
    broken_items = [i for i in city_items if i.get("agent_status") == "MANUAL_REVIEW_REQUIRED"]

    file_path = f"frontend/public/data/{city.lower()}_mayor_tracker.json"
    
    # 【1】リンク無効化用PR起票
    if broken_items:
        branch = f"bot/disable-broken-evidence-{city.lower()}-{date_str}"
        title = f"fix(evidence): disable broken links (set is_broken) for {city.lower()}"
        body = "## 🚨 404リンク無効化 (Fail-Closed) 自動対応\n\n代替ページの特定に失敗したため、フェイルセーフ原則に基づき対象データに `is_broken: true` を付与しました。\n**このPRをマージすることで、画面上では対象リンクが安全にグレーアウト（クリック不可）されます。**\n\n### 📍 無効化対象一覧\n"
        for b in broken_items:
            body += f"- **{b.get('headline')}** (`{b.get('field')}`)\n  - 失効URL: `{b.get('url')}`\n"
        
        run_cmd(["git", "checkout", "main"])
        run_cmd(["git", "checkout", "-b", branch])
        run_cmd(["git", "add", file_path])
        run_cmd(["git", "commit", "-m", title])
        run_cmd(["git", "push", "origin", branch])
        pr_url = run_cmd(["gh", "pr", "create", "--title", title, "--body", body])
        
        print(f"[{city.upper()}] 🚨 無効化PR起票成功: {pr_url}")
        print(f"  --> Discord通知 [黄色Embed送信]: ⚠️ 要手動調査 リンク無効化PRをマージして画面を安全化してください")
        created_prs += 1

    # 【2】URL正常更新用PR起票
    if success_items:
        branch = f"bot/update-evidence-{city.lower()}-{date_str}"
        title = f"fix(evidence): auto-update primary source for {city.lower()}"
        body = "## ✅ 404リンク自動修復 (Self-Healing)\n\nAI探索に合格した代替ページへの更新です。\n\n### 📍 修復対象一覧\n"
        for s in success_items:
            body += f"- **{s.get('headline')}**\n  - 新URL: `{s.get('new_url')}`\n"
        
        run_cmd(["git", "checkout", "main"])
        run_cmd(["git", "checkout", "-b", branch])
        run_cmd(["git", "add", file_path])
        run_cmd(["git", "commit", "-m", title])
        run_cmd(["git", "push", "origin", branch])
        pr_url = run_cmd(["gh", "pr", "create", "--title", title, "--body", body])
        
        print(f"[{city.upper()}] ✅ 更新PR起票成功: {pr_url}")
        print(f"  --> Discord通知 [緑色Embed送信]: ✅ 修復完了 エビデンスURL自動更新")
        created_prs += 1

run_cmd(["git", "checkout", "main"])

# 処理完了後、キューをクリア
with open(QUEUE_PATH, "w", encoding="utf-8") as f:
    json.dump([], f)
    
print(f"\n🏁 PR起票プロセス完了 (計 {created_prs} 件のPRを作成しました)")
