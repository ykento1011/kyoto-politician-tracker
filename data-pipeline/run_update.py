import os
import sys
import json
import subprocess
from datetime import datetime
from google.cloud import bigquery
from dotenv import load_dotenv

# .env の読み込み
load_dotenv()

# === パス・環境設定 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_PATH = os.path.join(BASE_DIR, "sagebase_crawled_data.json")

# Sagebase (BigQuery) 接続情報
PROJECT_ID = "gen-lang-client-0253904061"
DATASET_ID = "sagebase_data"
KYOTO_INTERNAL_ID = 88  # 京都市

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 {msg}")

def run_step(script_name):
    """データパイプラインスクリプトを順次実行"""
    script_path = os.path.join(BASE_DIR, script_name)
    log(f"実行中: {script_name}...")
    res = subprocess.run([sys.executable, script_path], cwd=BASE_DIR)
    if res.returncode != 0:
        log(f"❌ {script_name} の実行中にエラーが発生しました。パイプラインを中断します。")
        sys.exit(1)

def get_local_latest_info():
    """手元データから最新会議日と取得済み発言キー（meeting_id + sequence_number）を取得"""
    if not os.path.exists(RAW_DATA_PATH):
        return "2023-05-01", set()

    with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    latest_date = "2023-05-01"
    existing_ids = set()

    for item in data:
        mid = item.get("meeting_id") or ""
        seq = str(item.get("sequence_number") or "")
        existing_ids.add(f"{mid}_{seq}")

        mdate = item.get("meeting_date")
        if mdate and str(mdate) > latest_date:
            latest_date = str(mdate)

    return latest_date, existing_ids

def check_and_fetch_new_statements(latest_date, existing_ids):
    """BigQuery を監視し、手元にない新規発言レコードのみを抽出"""
    log(f"Sagebase (BigQuery) を監視中... (手元の最新会議日: {latest_date})")
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT 
            m.sagebase_id AS meeting_id,
            c.sequence_number,
            c.speaker_name AS speaker,
            c.comment AS statement_text,
            m.name AS meeting_title,
            m.date AS meeting_date
        FROM `{PROJECT_ID}.{DATASET_ID}.conversations` c
        JOIN `{PROJECT_ID}.{DATASET_ID}.minutes` min
          ON c.minutes_id = min.id
        JOIN `{PROJECT_ID}.{DATASET_ID}.meetings` m
          ON min.meeting_id = m.id
        JOIN `{PROJECT_ID}.{DATASET_ID}.conferences` conf
          ON m.conference_id = conf.id
        WHERE conf.governing_body_id = {KYOTO_INTERNAL_ID}
          AND m.date >= '{latest_date}'
        ORDER BY m.date ASC, c.sequence_number ASC
    """

    try:
        query_job = client.query(query)
        rows = list(query_job.result())
    except Exception as e:
        log(f"❌ BigQueryクエリエラー: {e}")
        sys.exit(1)

    new_records = []
    for r in rows:
        unique_key = f"{r.meeting_id}_{r.sequence_number}"
        if unique_key not in existing_ids:
            new_records.append({
                "meeting_id": r.meeting_id,
                "sequence_number": r.sequence_number,
                "speaker": r.speaker,
                "statement_text": r.statement_text,
                "meeting_title": r.meeting_title,
                "meeting_date": str(r.meeting_date)
            })

    return new_records

def git_commit_and_push():
    """更新された差分データを GitHub へ自動プッシュ"""
    log("GitHub への自動コミット＆プッシュを実行中...")
    try:
        project_root = os.path.dirname(BASE_DIR)
        
        # Git ステージング
        subprocess.run(["git", "add", "frontend/public/data/"], cwd=project_root, check=True)
        subprocess.run(["git", "add", "data-pipeline/sagebase_crawled_data.json"], cwd=project_root, check=True)
        subprocess.run(["git", "add", "data-pipeline/analyzed_kyoto_politicians_term.json"], cwd=project_root, check=True)
        subprocess.run(["git", "add", "data-pipeline/eval_checkpoint.json"], cwd=project_root, check=True)
        
        status = subprocess.run(["git", "status", "--porcelain"], cwd=project_root, capture_output=True, text=True)
        if not status.stdout.strip():
            log("コミット対象の差分はありませんでした。")
            return

        commit_msg = f"chore: 議事録データ自動定期更新 ({datetime.now().strftime('%Y-%m-%d')})"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=project_root, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=project_root, check=True)
        log("✅ GitHub へのプッシュが完了しました！Cloudflare Pages が自動更新されます。")
    except Exception as e:
        log(f"⚠️ Git操作中にエラーが発生しました: {e}")

def main():
    print("=" * 60)
    log("Sagebase 定期監視・全自動データ更新パイプラインを開始")
    print("=" * 60)

    # 1. 手元の状態確認
    latest_date, existing_ids = get_local_latest_info()

    # 2. BigQuery から新規発言ログを取得
    new_statements = check_and_fetch_new_statements(latest_date, existing_ids)

    if not new_statements:
        log("✅ 新しい議事録はありませんでした（手元のデータは最新です）。")
        print("=" * 60)
        return

    log(f"🎉 新着の発言データを検知しました！ (新規: {len(new_statements):,} 件)")

    # 3. 生データ (sagebase_crawled_data.json) へマージ保存
    with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
        current_raw = json.load(f)
    
    current_raw.extend(new_statements)
    with open(RAW_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(current_raw, f, ensure_ascii=False)
    log(f"生データファイルを更新しました (総計: {len(current_raw):,} 件)")

    # 4. 新規スレッドの Gemini 自動評価（未評価のみ処理）
    run_step("batch_analyze_council.py")

    # 5. カテゴリ判定の最適化
    run_step("remap_categories.py")

    # 6. 一覧用サマリー (statements_summary.json) の再生成
    run_step("generate_static_data.py")

    # 7. 会議別タイムラインJSONの分割・生成
    run_step("build_timeline_contexts.py")

    # 8. GitHub へ自動 Push して公開反映
    git_commit_and_push()

    print("=" * 60)
    log("🎉 パイプラインが完了しました！")
    print("=" * 60)

if __name__ == "__main__":
    main()