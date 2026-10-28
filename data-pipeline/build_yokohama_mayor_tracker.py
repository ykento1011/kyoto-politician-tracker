import json
import uuid
from pathlib import Path

# パス設定
BASE_DIR = Path(__file__).resolve().parent
INPUT_JSON = BASE_DIR / "data" / "yokohama_mayor_pledges.json"
OUTPUT_DIR = BASE_DIR.parent / "frontend" / "public" / "data"
OUTPUT_JSON = OUTPUT_DIR / "yokohama_mayor_tracker.json"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def build_tracker():
    if not INPUT_JSON.exists():
        print(f"❌ 入力データが見つかりません: {INPUT_JSON}")
        return

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # ターゲット候補者（「原沢あつみ」または「原澤あつみ」）のデータを取得
    target_candidate = None
    for cand in raw_data:
        # 表記ゆれ対応: 「原沢」と「原澤」両方をカバー
        if "原沢あつみ" in cand.get("speaker", "") or "原澤あつみ" in cand.get("speaker", ""):
            target_candidate = cand
            break
            
    if not target_candidate:
        print("❌ 抽出データの中にターゲット候補者（原沢/原澤あつみ）が見つかりません。")
        return

    # フロントエンドのスキーマに合わせたトラッカー構造を構築
    tracker_data = {
        "speaker": target_candidate["speaker"],
        "pledges": []
    }

    # 公約ごとにIDを振り、スキーマを整形
    for i, pledge in enumerate(target_candidate.get("pledges", [])):
        pledge_id = f"YH-P-{str(i+1).zfill(2)}"
        
        # 画面表示用の構造を作成
        tracker_item = {
            "id": pledge_id,
            "pledge_id": pledge_id,
            "category": pledge.get("category", "その他"),
            "headline": pledge.get("headline", ""),
            "title": pledge.get("headline", ""), # 互換性のため
            "election_promise": {
                "document_type": "横浜市選挙公報",
                "source_name": "横浜市選管発行 令和8年市長選挙公報",
                "bulletin_url": "https://www.city.yokohama.lg.jp/city-info/senkyo/data/mayor/20261018kohosya_koho.files/R08_kouhou.pdf",
                "quote": pledge.get("exact_quote", ""), # Geminiが抽出した正確な本文
                "note": "※選挙公報原本（PDF）から抽出した文言です。"
            }
        }
        tracker_data["pledges"].append(tracker_item)

    # JSON出力
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(tracker_data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ トラッカーデータを更新しました: {OUTPUT_JSON}")
    print(f"   登録された公約数: {len(tracker_data['pledges'])}")

if __name__ == "__main__":
    build_tracker()
