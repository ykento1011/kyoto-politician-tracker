import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE = ROOT / "data-pipeline"
FRONTEND = ROOT / "frontend"
FRONTEND_DATA = FRONTEND / "public" / "data"

def check_progress(city_code):
    city = city_code.lower()
    print("=" * 75)
    print(f"📊 【議会のミカタ】新都市展開・全体進捗照合レポート: {city.upper()}")
    print("=" * 75)

    phases = [
        {"phase": 1, "name": "一次情報・テナント適合性診断", "status": "⏳ 未着手", "details": []},
        {"phase": 2, "name": "SSoTマスター先行配備＆サーキットブレーカー", "status": "⏳ 未着手", "details": []},
        {"phase": 3, "name": "議事録抽出・タイムライン分割", "status": "⏳ 未着手", "details": []},
        {"phase": 4, "name": "議決・対立議案AI論点解説", "status": "⏳ 未着手", "details": []},
        {"phase": 5, "name": "公報原本物理抽出＆セマンティック公約結合", "status": "⏳ 未着手", "details": []},
        {"phase": 6, "name": "政策論戦マップ＆首長トラッカー", "status": "⏳ 未着手", "details": []},
        {"phase": 7, "name": "フロントエンド統合＆設定・アセット配備", "status": "⏳ 未着手", "details": []},
        {"phase": 8, "name": "3段階多層監査＆Playwright全画面検証", "status": "⏳ 未着手", "details": []},
        {"phase": 9, "name": "run_update.py 自走化＆自動デプロイ", "status": "⏳ 未着手", "details": []},
    ]

    # --- Phase 1 チェック ---
    mayors_file = PIPELINE / "master" / "mayors.json"
    p1_ok = False
    if mayors_file.exists():
        try:
            m_data = json.loads(mayors_file.read_text(encoding="utf-8"))
            if city in m_data:
                phases[0]["details"].append(f"首長マスター登録済み: {m_data[city].get('name')}")
                p1_ok = True
        except Exception:
            pass
    phases[0]["status"] = "✅ 完了" if p1_ok else "🔄 進行中 / 未着手"

    # --- Phase 2 チェック ---
    master_c = PIPELINE / "master" / f"councilors_{city}.json"
    override_c = PIPELINE / "master" / f"manual_overrides_{city}.json"
    stats_c = FRONTEND_DATA / f"{city}_speaker_stats.json"
    p2_score = 0
    if master_c.exists():
        p2_score += 1
        phases[1]["details"].append(f"正本マスター: {master_c.name}")
    if override_c.exists():
        p2_score += 1
        phases[1]["details"].append(f"手動オーバーライド層: {override_c.name}")
    if stats_c.exists():
        p2_score += 1
        phases[1]["details"].append(f"公開マスター同期: {stats_c.name}")
    phases[1]["status"] = "✅ 完了" if p2_score == 3 else ("🔄 進行中" if p2_score > 0 else "⏳ 未着手")

    # --- Phase 3 チェック ---
    stmt_file = FRONTEND_DATA / f"{city}_statements_summary.json"
    if stmt_file.exists():
        phases[2]["status"] = "✅ 完了"
        try:
            cnt = len(json.loads(stmt_file.read_text(encoding="utf-8")))
            phases[2]["details"].append(f"質疑スレッドデータ: {cnt} 件")
        except Exception:
            pass
    else:
        phases[2]["status"] = "⏳ 未着手"

    # --- Phase 4 チェック ---
    votes_file = FRONTEND_DATA / f"{city}_votes_summary.json"
    bills_file = FRONTEND_DATA / f"{city}_bill_issues.json"
    p4_score = 0
    if votes_file.exists():
        p4_score += 1
        phases[3]["details"].append(f"議決データ: {votes_file.name}")
    if bills_file.exists():
        p4_score += 1
        phases[3]["details"].append(f"対立議案AI解説: {bills_file.name}")
    phases[3]["status"] = "✅ 完了" if p4_score == 2 else ("🔄 進行中" if p4_score > 0 else "⏳ 未着手")

    # --- Phase 5 チェック ---
    pledge_candidates = [
        FRONTEND_DATA / city / "pledge_tracker.json",
        FRONTEND_DATA / f"{city}/pledge_tracker.json",
        FRONTEND_DATA / f"pledge_tracker_{city}.json"
    ]
    pledge_file = next((p for p in pledge_candidates if p.exists()), None)
    if pledge_file:
        phases[4]["status"] = "✅ 完了"
        phases[4]["details"].append(f"公約トラッカー: {pledge_file.relative_to(ROOT)}")
    else:
        phases[4]["status"] = "⏳ 未着手"

    # --- Phase 6 チェック ---
    topic_file = FRONTEND_DATA / f"{city}_topic_summaries.json"
    mayor_script = PIPELINE / f"build_mayor_tracker_{city}.py"
    mayor_json = FRONTEND_DATA / f"{city}_mayor_tracker.json"
    p6_score = 0
    if topic_file.exists():
        p6_score += 1
        phases[5]["details"].append(f"政策論戦マップ: {topic_file.name}")
    if mayor_script.exists():
        p6_score += 1
        phases[5]["details"].append(f"首長スクリプト: {mayor_script.name}")
    if mayor_json.exists():
        p6_score += 1
        phases[5]["details"].append(f"首長トラッカーJSON: {mayor_json.name}")
    phases[5]["status"] = "✅ 完了" if p6_score == 3 else ("🔄 進行中" if p6_score > 0 else "⏳ 未着手")

    # --- Phase 7 チェック ---
    cities_js = FRONTEND / "src" / "config" / "cities.js"
    photo_dir = FRONTEND / "public" / "councilors" / city
    p7_score = 0
    if cities_js.exists() and f"'{city}'" in cities_js.read_text(encoding="utf-8").lower():
        p7_score += 1
        phases[6]["details"].append("cities.js 設定登録済み")
    if photo_dir.exists() and len(list(photo_dir.glob("*.jpg"))) > 0:
        p7_score += 1
        phases[6]["details"].append(f"議員顔写真: {len(list(photo_dir.glob('*.jpg')))} 枚")
    phases[6]["status"] = "✅ 完了" if p7_score == 2 else ("🔄 進行中" if p7_score > 0 else "⏳ 未着手")

    # --- Phase 8 チェック ---
    # Phase 2〜7が揃っているか
    all_ready = all(phases[i]["status"] == "✅ 完了" for i in range(7))
    phases[7]["status"] = "🔄 監査可能（実行待ち）" if all_ready else "⏳ 前段階未達"

    # --- Phase 9 チェック ---
    run_file = PIPELINE / "run_update.py"
    if run_file.exists() and f'"{city}"' in run_file.read_text(encoding="utf-8"):
        phases[8]["details"].append("run_update.py CITIES 登録済み")
        phases[8]["status"] = "🔄 自走検証待ち" if all_ready else "⏳ 前段階未達"
    else:
        phases[8]["status"] = "⏳ 未配備"

    completed_count = sum(1 for p in phases if "✅" in p["status"])
    pct = (completed_count / 9.0) * 100

    for p in phases:
        print(f"[{p['status']}] Phase {p['phase']}: {p['name']}")
        for d in p["details"]:
            print(f"      └ {d}")

    print("-" * 75)
    print(f"🏁 全体進捗スコア: {completed_count}/9 フェーズ完了 ({pct:.1f}%)")
    print("=" * 75)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="新都市追加の全体進捗照合ツール")
    parser.add_argument("--city", required=True, help="対象都市コード (例: kobe, kyoto)")
    args = parser.parse_args()
    check_progress(args.city)
