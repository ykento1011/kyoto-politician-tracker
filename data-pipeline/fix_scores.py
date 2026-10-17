import json

# upload_to_supabase.py が読み込んでいるファイル名に合わせてください
filename = "analyzed_kyoto_politicians.json"

def main():
    print("データを読み込んでいます...")
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    fixed_count = 0

    for item in data:
        if "analysis" in item and "scores" in item["analysis"]:
            scores = item["analysis"]["scores"]
            for key in ["evidence", "solution", "local_focus", "constructive", "total_quality"]:
                if key in scores:
                    val = scores[key]
                    if isinstance(val, float) or (isinstance(val, str) and "." in val):
                        try:
                            # 小数を四捨五入して整数（int）に変換
                            scores[key] = int(round(float(val)))
                            fixed_count += 1
                        except (ValueError, TypeError):
                            scores[key] = 0

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 修正完了！ {fixed_count} 個の小数を整数に変換しました。")

if __name__ == "__main__":
    main()