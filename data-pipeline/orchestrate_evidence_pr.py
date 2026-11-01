import os
import sys
import json
import re
import argparse
import subprocess
from datetime import datetime
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
FRONTEND_DATA_DIR = os.path.join(PROJECT_ROOT, "frontend", "public", "data")
QUEUE_FILE = os.path.join(BASE_DIR, "data", "evidence_health_queue.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")

def load_webhook_url():
    if not os.path.exists(ENV_FILE):
        return None
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DISCORD_WEBHOOK_URL="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return val if val else None
    except Exception:
        pass
    return None

def notify_discord_pr(city, headline, field, old_url, new_url, pr_url, dry_run=False):
    webhook_url = load_webhook_url()
    if not webhook_url and not dry_run:
        print("⚠️ DISCORD_WEBHOOK_URLが設定されていないため、通知をスキップします。")
        return

    desc_lines = [
        f"**施策名:** {headline}",
        f"**対象フィールド:** `{field}`",
        f"**旧URL (404失効):** [リンク]({old_url})",
        f"**新URL (自律特定):** [公式単体ページ確認]({new_url})"
    ]
    desc = "\n".join(desc_lines)

    payload = {
        "username": "議会のミカタ 自動更新Bot",
        "avatar_url": "https://gikai-mikata.jp/favicon-96x96.png",
        "embeds": [{
            "title": f"🎉 【自動検知・PR起票完了】 {city.upper()} 一次公文書エビデンス更新",
            "description": desc,
            "color": 0x2ecc71,
            "fields": [
                {"name": "GitHub PR", "value": f"[🔍 マージ確認画面へ]({pr_url})", "inline": False}
            ],
            "footer": {"text": "Self-Healing Evidence Pipeline"}
        }]
    }

    if dry_run:
        print("\n=== [DRY-RUN] Discord Webhook (PR Created) Payload ===")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("=====================================================\n")
        return

    try:
        res = requests.post(webhook_url, json=payload, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"⚠️ Discord 通知の送信に失敗しました: {e}")

def notify_discord_manual(city, headline, field, old_url, reason, dry_run=False):
    webhook_url = load_webhook_url()
    if not webhook_url and not dry_run:
        return

    desc_lines = [
        f"**施策名:** {headline}",
        f"**対象フィールド:** `{field}`",
        f"**失効URL:** [リンク]({old_url})",
        "",
        f"**破棄理由:** {reason}"
    ]
    desc = "\n".join(desc_lines)

    payload = {
        "username": "議会のミカタ 自動更新Bot",
        "avatar_url": "https://gikai-mikata.jp/favicon-96x96.png",
        "embeds": [{
            "title": f"⚠️ 【要手動調査】 {city.upper()} 一次公文書エビデンス更新",
            "description": desc,
            "color": 0xf1c40f,
            "footer": {"text": "Fail-Closed Validator"}
        }]
    }

    if dry_run:
        print("\n=== [DRY-RUN] Discord Webhook (Manual Review) Payload ===")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("=========================================================\n")
        return

    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Discord 通知の送信に失敗しました: {e}")

def update_json_data(city, pledge_id, field_path, new_url):
    file_path = os.path.join(FRONTEND_DATA_DIR, f"{city}_mayor_tracker.json")
    if not os.path.exists(file_path):
        return False, "Tracker JSON not found"
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if pledge_id == "mayor_info":
            parts = field_path.split(".")
            if len(parts) == 2 and parts[0] == "mayor_info":
                data["mayor_info"][parts[1]] = new_url
        else:
            found = False
            for p in data.get("pledges", []):
                if str(p.get("pledge_id")) == str(pledge_id):
                    found = True
                    if field_path.startswith("election_promise.bulletin_url"):
                        if "election_promise" not in p: p["election_promise"] = {}
                        p["election_promise"]["bulletin_url"] = new_url
                    elif field_path.startswith("official_plan.doc_url"):
                        if "official_plan" not in p: p["official_plan"] = {}
                        p["official_plan"]["doc_url"] = new_url
                    elif field_path.startswith("milestone.evidence_url"):
                        if "milestone" not in p: p["milestone"] = {}
                        p["milestone"]["evidence_url"] = new_url
                    elif field_path.startswith("budget_records[") or field_path.startswith("ordinance_records["):
                        m = re.match(r"(.*?)\[(\d+)\]\.(.*)", field_path)
                        if m:
                            arr_name, idx_str, key_name = m.groups()
                            idx = int(idx_str)
                            if arr_name in p and len(p[arr_name]) > idx:
                                p[arr_name][idx][key_name] = new_url
                    break
            if not found:
                return False, f"Pledge ID {pledge_id} not found"
                
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return True, "Success"
    except Exception as e:
        return False, str(e)

def run_cmd(cmd, cwd, dry_run=False):
    if dry_run:
        print(f" [DRY-RUN EXEC] {' '.join(cmd)}")
        return True, "dry-run success"
    try:
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return True, res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()

def create_pull_request(item, dry_run=False):
    city = item["city"]
    pid = item["pledge_id"]
    hl = item["headline"]
    field = item["field"]
    old_url = item["url"]
    new_url = item["new_url"]
    new_title = item.get("new_title", "公式単体ページ")
    
    date_str = datetime.now().strftime("%Y%m%d")
    branch_name = f"bot/update-evidence-{city}-{pid}-{date_str}"
    
    print(f"\n🚀 [PR起票開始] {city.upper()} - {hl[:20]}...")
    
    ok, out = run_cmd(["git", "checkout", "main"], cwd=PROJECT_ROOT, dry_run=dry_run)
    if not ok: return False, f"git checkout main failed: {out}"
    
    run_cmd(["git", "branch", "-D", branch_name], cwd=PROJECT_ROOT, dry_run=True)
    if not dry_run:
        subprocess.run(["git", "branch", "-D", branch_name], cwd=PROJECT_ROOT, capture_output=True)

    ok, out = run_cmd(["git", "checkout", "-b", branch_name], cwd=PROJECT_ROOT, dry_run=dry_run)
    if not ok: return False, f"git checkout -b failed: {out}"

    if not dry_run:
        ok, msg = update_json_data(city, pid, field, new_url)
        if not ok:
            run_cmd(["git", "checkout", "main"], cwd=PROJECT_ROOT, dry_run=False)
            return False, f"JSON update failed: {msg}"
    else:
        print(f" [DRY-RUN] Update JSON: {city}_mayor_tracker.json (Field: {field} -> {new_url})")

    run_cmd(["git", "add", f"frontend/public/data/{city}_mayor_tracker.json"], cwd=PROJECT_ROOT, dry_run=dry_run)
    
    commit_msg = f"fix(evidence): auto-update primary source for {city} - {hl[:20]}"
    ok, out = run_cmd(["git", "commit", "-m", commit_msg], cwd=PROJECT_ROOT, dry_run=dry_run)
    if not ok:
        run_cmd(["git", "checkout", "main"], cwd=PROJECT_ROOT, dry_run=False)
        return False, f"git commit failed (no changes?): {out}"

    ok, out = run_cmd(["git", "push", "-u", "origin", branch_name], cwd=PROJECT_ROOT, dry_run=dry_run)
    if not ok:
        run_cmd(["git", "checkout", "main"], cwd=PROJECT_ROOT, dry_run=False)
        return False, f"git push failed: {out}"

    pr_body_lines = [
        "## 📄 一次公文書エビデンス 自律更新（Self-Healing）",
        "",
        f"**対象施策**: `{city.upper()}` | ID: {pid} | {hl}",
        f"**更新フィールド**: `{field}`",
        "",
        "### 🔗 URL差分",
        f"- ❌ **旧URL (失効/404)**: {old_url}",
        f"- ✅ **新URL (自律特定)**: {new_url}",
        "",
        f"**特定根拠・タイトル**: `{new_title}`",
        "",
        "---",
        "*※ Fail-Closed 4重バリデーション（公式ドメイン検証、トップページ遮断、白書PDF除外、本文エンティティ照合）を完全合格しています。*",
        "*レビュアーは上記リンクを目視確認し、問題なければマージしてください。*"
    ]
    pr_body = "\n".join(pr_body_lines)

    gh_cmd = [
        "gh", "pr", "create",
        "--title", commit_msg,
        "--body", pr_body,
        "--base", "main",
        "--head", branch_name
    ]
    
    if dry_run:
        print(f" [DRY-RUN EXEC] {' '.join(gh_cmd[:4])} ...")
        print(" [DRY-RUN] --- PR BODY PREVIEW ---")
        print(pr_body)
        print(" [DRY-RUN] -----------------------")
        pr_url = "https://github.com/org/repo/pull/999 (DRY-RUN)"
    else:
        try:
            res = subprocess.run(gh_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=True)
            pr_url = res.stdout.strip()
        except subprocess.CalledProcessError as e:
            run_cmd(["git", "checkout", "main"], cwd=PROJECT_ROOT, dry_run=False)
            return False, f"gh pr create failed. Error: {e.stderr.strip()}"

    run_cmd(["git", "checkout", "main"], cwd=PROJECT_ROOT, dry_run=dry_run)
    return True, pr_url

def main():
    parser = argparse.ArgumentParser(description="一次公文書エビデンス自動PR起票オーケストレーター")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（Git操作やPR起票をモック実行）")
    args = parser.parse_args()

    if not os.path.exists(QUEUE_FILE):
        print("キューファイルが存在しません。終了します。")
        sys.exit(0)

    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            queue_items = json.load(f)
    except Exception as e:
        print(f"キュー読み込みエラー: {e}")
        sys.exit(1)

    updated_count = 0
    pr_count = 0
    notified_manual_count = 0

    for item in queue_items:
        status = item.get("agent_status")
        
        if status == "AUTO_FIX_CANDIDATE":
            ok, pr_url_or_err = create_pull_request(item, dry_run=args.dry_run)
            if ok:
                print(f"✅ PR起票成功: {pr_url_or_err}")
                item["agent_status"] = "PR_CREATED"
                item["pr_url"] = pr_url_or_err
                notify_discord_pr(item["city"], item["headline"], item["field"], item["url"], item["new_url"], pr_url_or_err, dry_run=args.dry_run)
                pr_count += 1
                updated_count += 1
            else:
                print(f"❌ PR起票失敗: {pr_url_or_err}")
                item["agent_status"] = "PR_FAILED"
                item["agent_note"] = pr_url_or_err
                updated_count += 1

        elif status == "MANUAL_REVIEW_REQUIRED" and not item.get("notified_discord"):
            notify_discord_manual(item["city"], item["headline"], item["field"], item["url"], item.get("agent_note", "特定不能"), dry_run=args.dry_run)
            item["notified_discord"] = True
            notified_manual_count += 1
            updated_count += 1

    if updated_count > 0 and not args.dry_run:
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(queue_items, f, ensure_ascii=False, indent=2)
        print(f"\n📝 キューの状態を更新・保存しました (PR起票 {pr_count}件 / 通知済処理 {notified_manual_count}件)。")
    elif args.dry_run:
        print(f"\n🧪 [DRY-RUN] 完了: PR起票対象 {pr_count}件 / 要手動通知対象 {notified_manual_count}件")
    else:
        print("\n✅ 処理すべき新しいキューアイテムはありませんでした。")

if __name__ == "__main__":
    main()
