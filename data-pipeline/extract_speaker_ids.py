import json

def extract_speakers():
    with open("sagebase_crawled_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 重複を排除して ID: 名前 の辞書を作成
    speakers = {}
    for row in data:
        s_id = row.get("speaker_id")
        name = row.get("speaker")
        if s_id and name:
            # 「委員長」「主査」などの肩書が混ざっている場合は除去
            clean_name = name.replace("委員長", "").replace("副委員長", "").replace("主査", "").strip()
            speakers[s_id] = clean_name

    # ID順にソートして出力
    sorted_speakers = dict(sorted(speakers.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0))

    with open("kyoto_councilors_list.json", "w", encoding="utf-8") as f:
        json.dump(sorted_speakers, f, indent=2, ensure_ascii=False)

    print(f"✅ 全 {len(sorted_speakers)} 名の発言者リストを kyoto_councilors_list.json に出力しました！")
    print("※このファイルから市の職員（理事者）の行を削除すれば、完璧な議員IDフィルターになります。")

if __name__ == "__main__":
    extract_speakers()