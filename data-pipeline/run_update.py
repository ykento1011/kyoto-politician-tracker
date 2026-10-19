import os
import sys
import json
import subprocess
import time
from datetime import datetime

# パス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# スクリプトのパス
FETCH_SCRIPT = os.path.join(BASE_DIR, "fetch_sagebase.py")
ANALYZE_SCRIPT = os.path.join(BASE_DIR, "batch_analyze_council.py")
TIMELINE_SCRIPT = os.path.join(BASE_DIR, "build_timeline_contexts.py")
STATIC_DATA_SCRIPT = os.path.join(BASE_DIR, "generate_static_data.py")
REMAP_SCRIPT = os.path.join(BASE_DIR, "remap_categories.py")
SCRAPE_VOTES_SCRIPT = os.path.join(BASE_DIR, "scrape_kyoto_votes.py")
GENERATE_ISSUES_SCRIPT = os.path.join(BASE_DIR, "generate_bill_issues.py")

# 出力・監視対象のファイル
CRAWLED_FILE = os.path.join(BASE_DIR, "sagebase_crawled_data.json")
VOTES_FILE = os.path.join(PROJECT_ROOT, "frontend", "public", "data", "votes_summary.json")

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emoji = "🚀" if level == "INFO" else "⚠️" if level == "WARN" else "❌"
    print(f"[{ts}] {emoji} {msg}", flush=True)

def run_script(script_path, description):
    log(f"{description} を開始...")
    try:
        python_exe = sys.executable
        result = subprocess.run([python_exe, script_path], capture_output=True, text=True, check=True)
        log(f"{description} 完了")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        log(f"{description} でエラー発生！", "ERROR")
        print("--- Error Output ---")
        print(e.stderr)
        print("--------------------")
        return False, e.stderr

def load_crawled_ids():
    """既存の議事録IDセットを取得"""
    if os.path.exists(CRAWLED_FILE):
        try:
            with open(CRAWLED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {f"{d.get('meeting_id')}_{d.get('sequence_number')}" for d in data}
        except Exception:
            return set()
    return set()

def summarize_new_minutes(before_ids):
    """新しく追加された議事録のサマリー（件数、日付、会議名）を生成"""
    if not os.path.exists(CRAWLED_FILE):
        return ""
    try:
        with open(CRAWLED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        new_items = [d for d in data if f"{d.get('meeting_id')}_{d.get('sequence_number')}" not in before_ids]
        if not new_items:
            return ""
        
        count = len(new_items)
        sample = new_items[-1]
        sample_date = sample.get("meeting_date", "")
        sample_title = sample.get("meeting_title", "").replace("京都市会", "").strip()[:18]
        
        return f"【{sample_date} {sample_title} など新着{count}件】"
    except Exception:
        return "【新着議事録を追加】"

def check_for_changes():
    """Git の status を確認し、frontend/public/data 配下にコミットすべき変更があるか判定"""
    try:
        os.chdir(PROJECT_ROOT)
        result = subprocess.run(["git", "status", "--porcelain", "frontend/public/data"], capture_output=True, text=True, check=True)
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        log("Git の状態確認に失敗しました", "ERROR")
        return False

def push_to_github(custom_detail=""):
    """変更をステージング、コミット、プッシュする"""
    log("GitHub への自動デプロイを開始...")
    try:
        os.chdir(PROJECT_ROOT)
        
        # 公開データディレクトリを安全にステージング
        subprocess.run(["git", "add", "frontend/public/data"], check=True)
        
        # 詳細なコミットメッセージの構築
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        if custom_detail:
            commit_msg = f"Auto-update: {custom_detail} を追加・反映 ({now_str})"
        else:
            commit_msg = f"Auto-update: 議決・賛否データの最新化 ({now_str})"
            
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        log(f"✅ GitHub へのプッシュが完了（{commit_msg}）。")
    except subprocess.CalledProcessError as e:
        log(f"Git プッシュ処理中にエラーが発生しました: {e}", "ERROR")

def main():
    print("\n" + "="*60)
    log("Sagebase 定期監視・全自動データ更新パイプラインを開始")
    print("="*60)

    # 1. 取得前の議事録 ID を控える
    before_ids = load_crawled_ids()
    before_count = len(before_ids)

    # 2. 議事録データの取得 (fetch_sagebase)
    success, output = run_script(FETCH_SCRIPT, "Sagebaseからの新着議事録取得")
    if not success:
        log("データ取得で致命的エラー。パイプラインを中断します。", "ERROR")
        return

    # 3. 議決・賛否データの更新 (動的スクレイピング & 争点分析)
    log("--- [議決・賛否データの更新チェック] ---")
    scrape_ok, _ = run_script(SCRAPE_VOTES_SCRIPT, "京都市会HPからの議案・賛否スクレイピング")
    if scrape_ok:
        issues_ok, _ = run_script(GENERATE_ISSUES_SCRIPT, "Geminiによる新規対立議案の争点分析")
        if not issues_ok:
            log("対立議案分析で警告が発生しましたが、パイプラインは続行します", "WARN")
    else:
        log("議案スクレイピングで警告が発生しましたが、パイプラインは続行します", "WARN")
    log("--- [議決・賛否データの更新チェック完了] ---")

    # 4. 議事録の差分確認
    after_ids = load_crawled_ids()
    minutes_updated = len(after_ids) > before_count
    new_detail_str = ""

    if minutes_updated:
        new_detail_str = summarize_new_minutes(before_ids)
        log(f"🆕 新しい議事録が追加されました: {new_detail_str}")
        
        # 5. Gemini 評価バッチの実行（※未評価スレッドのみ処理）
        ok, _ = run_script(ANALYZE_SCRIPT, "Gemini 評価バッチ（未評価差分のみ）")
        if not ok:
            return

        # 6. JSON 分割・タイムライン生成
        ok, _ = run_script(TIMELINE_SCRIPT, "タイムライン・コンテキストJSON分割")
        if not ok:
            return

        # 7. フロントエンド用 サマリー生成
        ok, _ = run_script(STATIC_DATA_SCRIPT, "フロントエンド用 サマリーJSON生成")
        if not ok:
            return

        # 7.5 カテゴリーの統一再マッピング（先祖返り防止）
        ok, _ = run_script(REMAP_SCRIPT, "最新カテゴリーへの統一再マッピング")
        if not ok:
            log("カテゴリー再マッピングで警告が出ましたが続行します", "WARN")
    else:
        log("✅ 新しい議事録はありませんでした。")

    # 8. 全体のGit差分チェックとデプロイ
    if check_for_changes():
        log("データファイルに変更があります。デプロイ処理へ進みます。")
        push_to_github(new_detail_str)
    else:
        log("✅ 変更されたデータはありませんでした（手元のデータは最新です）。")

    print("="*60)
    log("🎉 パイプラインが安全に終了しました。")
    print("="*60)

if __name__ == "__main__":
    main()