import json
from pathlib import Path

topic_file = Path("frontend/public/data/yokohama_topic_summaries.json")
if not topic_file.exists():
    print("❌ yokohama_topic_summaries.json が見つかりません。")
    exit()

with open(topic_file, "r", encoding="utf-8") as f:
    topics = json.load(f)

print("=" * 70)
print(f"📊 横浜市会 政策論戦マップ 整合性レポート")
print(f"・トピック総数: {len(topics)} 件")
print("=" * 70)

total_exchanges = 0
raw_text_count = 0
missing_urls = 0
missing_seq = 0

for t in topics:
    title = t.get("title")
    cat = t.get("category")
    phases = t.get("timeline_phases", [])
    
    t_exchanges = 0
    for p in phases:
        for ex in p.get("exchanges", []):
            total_exchanges += 1
            t_exchanges += 1
            # 原本テキストか三人称要約か判定
            txt = ex.get("statement_text") or ex.get("speech_text") or ""
            if len(txt) > 30 and not txt.endswith("説明した。") and not txt.endswith("答弁した。"):
                raw_text_count += 1
            if not ex.get("official_url"):
                missing_urls += 1
            if not ex.get("sequence_number") and "th_" not in str(ex.get("id", "")):
                missing_seq += 1

    print(f"・[{cat}] {title[:30]}... -> 関連質疑: {t_exchanges} 件")

print("\n【SOP品質ゲート判定】")
raw_rate = (raw_text_count / total_exchanges * 100) if total_exchanges > 0 else 0
print(f"・総発言カード数: {total_exchanges:,} 件")
print(f"・生発言（肉声）適用率: {raw_rate:.1f}% （SOP基準: 90%以上）")
print(f"・公式原本URL欠損: {missing_urls} 件")
print(f"・発言番号（sequence_number）欠損: {missing_seq} 件")

if raw_rate >= 90.0 and missing_urls == 0 and missing_seq == 0:
    print("🎉 SOP品質ゲート合格: 生発言優先・ディープリンク完全性が満たされています。")
else:
    print("⚠️ 要確認項目があります。")
print("=" * 70)
