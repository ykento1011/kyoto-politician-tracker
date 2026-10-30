import json
import os
from pathlib import Path

def normalize_value(val):
    if not isinstance(val, str): return val
    v = val.lower().strip()
    if v == 'for': return '賛成'
    if v == 'against': return '反対'
    if v == 'split': return '対応割れ'
    if v == 'abstain': return '棄権'
    if v == 'absent': return '欠席'
    return val

def main():
    # run_update.py から呼ばれる想定 (カレントは data-pipeline 又は プロジェクトルート)
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "frontend" / "public" / "data"
    
    if not data_dir.exists():
        print(f"Directory not found: {data_dir}")
        return

    count = 0
    for p in data_dir.glob("*.json"):
        if "vote" not in p.name.lower() and "bill" not in p.name.lower():
            continue
            
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            continue
            
        changed = False
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "votes" in item and isinstance(item["votes"], dict):
                    for k, v in item["votes"].items():
                        new_v = normalize_value(v)
                        if new_v != v:
                            item["votes"][k] = new_v
                            changed = True
                            
        if changed:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[正規化完了] {p.name} の賛否データを日本語に変換しました。")
            count += 1
            
    if count == 0:
        print("[正規化] 変換が必要なデータはありませんでした。")

if __name__ == "__main__":
    main()
