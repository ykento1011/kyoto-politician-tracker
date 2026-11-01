import json
import os

queue_path = "data-pipeline/data/evidence_health_queue.json"
if not os.path.exists(queue_path):
    exit(0)

with open(queue_path, "r", encoding="utf-8") as f:
    queue = json.load(f)

updated_files = set()
for item in queue:
    status = item.get("agent_status")
    if not status: continue
    
    city = item["city"].lower()
    pid = item["pledge_id"]
    field_path = item["field"]
    
    # MANUAL_REVIEW_REQUIRED(AI修復失敗)ならTrue、SUCCESS(修復成功)ならFalse
    is_broken_flag = (status == "MANUAL_REVIEW_REQUIRED")
    
    file_path = f"frontend/public/data/{city}_mayor_tracker.json"
    if not os.path.exists(file_path): continue
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    modified = False
    for p in data.get("pledges", []):
        if str(p.get("id") or p.get("pledge_id")) == str(pid):
            obj = None
            if "official_plan" in field_path and "official_plan" in p:
                obj = p["official_plan"]
            elif "budget_records" in field_path:
                idx = int(field_path.split("[")[1].split("]")[0])
                if len(p.get("budget_records", [])) > idx:
                    obj = p["budget_records"][idx]
            elif "milestone" in field_path and "milestone" in p:
                obj = p["milestone"]
                
            if obj is not None:
                if is_broken_flag:
                    if not obj.get("is_broken"):
                        obj["is_broken"] = True
                        modified = True
                else:
                    if "is_broken" in obj:
                        del obj["is_broken"]
                        modified = True
    
    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        updated_files.add(file_path)

if updated_files:
    print(f"⚙️ {len(updated_files)}件のデータファイルに対し、is_brokenフラグの自動着脱（同期）を完了しました。")
