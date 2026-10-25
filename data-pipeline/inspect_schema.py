import json
from pathlib import Path

cwd = Path('.').resolve()
root = cwd.parent if cwd.name == 'data-pipeline' else cwd

# 1. 京都版 tracked_items[0] の中身を表示
pt_path = root / 'frontend' / 'public' / 'data' / 'pledge_tracker.json'
if pt_path.exists():
    with open(pt_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        first_key = list(data.keys())[0]
        sample = data[first_key]
        print(f"=== 京都版サンプル ({first_key}) の tracked_items ===")
        if sample.get('tracked_items'):
            print(json.dumps(sample['tracked_items'][0], ensure_ascii=False, indent=2))
        else:
            print("tracked_items is empty")

# 2. 大阪の質疑データから議員名・会派・区の抽出テスト
os_path = root / 'frontend' / 'public' / 'data' / 'osaka_statements_summary.json'
if os_path.exists():
    with open(os_path, 'r', encoding='utf-8') as f:
        os_data = json.load(f)
        stmts = os_data if isinstance(os_data, list) else os_data.get('statements', [])
        
        councilor_map = {}
        for s in stmts:
            spk = s.get('speaker') or s.get('speaker_name')
            if not spk:
                continue
            party = s.get('party') or s.get('speaker_party') or '所属未登録'
            district = s.get('district') or s.get('ward') or ''
            if spk not in councilor_map:
                councilor_map[spk] = {'party': party, 'district': district, 'count': 0}
            councilor_map[spk]['count'] += 1

        print(f"\n=== 大阪の議員抽出結果 (上位10名サンプル) ===")
        sorted_c = sorted(councilor_map.items(), key=lambda x: x[1]['count'], reverse=True)
        for name, info in sorted_c[:10]:
            p = info['party']
            d = info['district']
            c = info['count']
            print(f"{name} | 会派: {p} | 区: {d} | 発言数: {c}件")
