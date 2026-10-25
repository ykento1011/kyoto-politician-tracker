import json, re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "frontend" / "public" / "data" / "osaka_statements_summary.json"

# 明らかな行政側・役職落ち・非議員の除外リスト
EXCLUDE_SPEAKERS = {
    "高橋大阪", "中小路大阪", "尾花大阪", "彌園万博", "森代表監査委員",
    "山田", "山向", "尾植"
}

def clean_speaker_name(name):
    # 末尾の「委員」「議員」「君」を除去
    cleaned = re.sub(r'(委員|議員|君)$', '', name).strip()
    return cleaned

def main():
    if not INPUT_FILE.exists():
        print(f"File not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📊 処理前スレッド総数: {len(data):,} 件")

    cleaned_data = []
    removed_count = 0
    speaker_stats = {}

    for item in data:
        raw_spk = item.get("speaker", "").strip()
        
        # 1. 行政側ノイズの除外
        if raw_spk in EXCLUDE_SPEAKERS or any(x in raw_spk for x in ["局長", "部長", "課長", "次長", "参事", "理事", "技監", "監査委員"]):
            removed_count += 1
            continue
            
        # 2. 名字一文字や短すぎるノイズの除外
        if len(raw_spk) <= 2 and not raw_spk in ["東", "武"]: # 実在する単漢字姓議員への配慮
            if len(raw_spk) <= 1:
                removed_count += 1
                continue

        # 3. 名前の正規化（サフィックス除去）
        spk = clean_speaker_name(raw_spk)
        item["speaker"] = spk

        cleaned_data.append(item)
        speaker_stats[spk] = speaker_stats.get(spk, 0) + 1

    # 保存
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    print(f"🗑️ 除外した行政・ノイズスレッド: {removed_count:,} 件")
    print(f"✨ クリーンアップ後スレッド数: {len(cleaned_data):,} 件")
    print(f"👥 有効な質問者（議員）ユニーク数: {len(speaker_stats)} 名")
    
    print("\n【質問スレッド数の多い議員 Top 15】")
    sorted_spk = sorted(speaker_stats.items(), key=lambda x: x[1], reverse=True)
    for spk, cnt in sorted_spk[:15]:
        print(f"  {spk:<12}: {cnt:3d} 件")

if __name__ == "__main__":
    main()
