import os
import sys
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
SCRAPE_VOTES_SCRIPT = os.path.join(BASE_DIR, "scrape_kyoto_votes.py") # 💡 追加
GENERATE_ISSUES_SCRIPT = os.path.join(BASE_DIR, "generate_bill_issues.py") # 💡 追加

# 出力・監視対象のファイル
CRAWLED_FILE = os.path.join(BASE_DIR, "sagebase_crawled_data.json")
VOTES_FILE = os.path.join(PROJECT_ROOT, "frontend", "public", "data", "votes_summary.json")
ISSUES_FILE = os.path.join(PROJECT_ROOT, "frontend", "public", "data", "bill_issues.json")

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emoji = "🚀" if level == "INFO" else "⚠️" if level == "WARN" else "❌"
    print(f"[{ts}] {emoji} {msg}", flush=True)

def run_script(script_path, description):
    log(f"{description} を開始...")
    try:
        # 仮想環境の python で実行する
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

def get_file_timestamp(filepath):
    """ファイルの最終更新日時（タイムスタンプ）を取得"""
    if os.path.exists(filepath):
        return os.path.getmtime(filepath)
    return 0

def check_for_changes():
    """Git の status を確認し、コミットすべき変更があるか判定"""
    try:
        os.chdir(PROJECT_ROOT)
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        changes = result.stdout.strip()
        # pycache など関係ない変更を省くため、frontend/public/data と data-pipeline/ 配下の .json を監視
        has_data_change = any(line.endswith(".json") for line in changes.split('\n') if line)
        return has_data_change
    except subprocess.CalledProcessError as e:
        log("Git の状態確認に失敗しました", "ERROR")
        return False

def push_to_github():
    """変更をステージング、コミット、プッシュする"""
    log("GitHub への自動デプロイを開始...")
    try:
        os.chdir(PROJECT_ROOT)
        
        # 💡 ワイルドカードを使わずディレクトリ単位で追加（本番に必要なデータのみ安全にステージング）
        subprocess.run(["git", "add", "frontend/public/data"], check=True)
        
        # コミット
        commit_msg = f"Auto-update: 議事録または議決データの最新化 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        
        # プッシュ (Cloudflare Pagesのビルドが走る)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        log("✅ GitHub へのプッシュが完了。本番環境に数分で反映されます。")
    except subprocess.CalledProcessError as e:
        log(f"Git プッシュ処理中にエラーが発生しました: {e}", "ERROR")

def main():
    print("\n" + "="*60)
    log("Sagebase 定期監視・全自動データ更新パイプラインを開始")
    print("="*60)

    # 1. 議事録ファイル更新前のタイムスタンプを取得
    before_ts = get_file_timestamp(CRAWLED_FILE)

    # 2. 議事録データの取得 (fetch_sagebase)
    success, output = run_script(FETCH_SCRIPT, "Sagebaseからの新着議事録取得")
    if not success:
        log("データ取得で致命的エラー。パイプラインを中断します。", "ERROR")
        return

    # 3. 議決・賛否データの更新 (scrape & generate issues)
    # ※スクレイピングやAPI制限等でエラーになっても、議事録側のパイプラインは止めない
    log("--- [議決・賛否データの更新チェック] ---")
    
    votes_before_ts = get_file_timestamp(VOTES_FILE)
    scrape_ok, _ = run_script(SCRAPE_VOTES_SCRIPT, "京都市会HPからの議案・賛否スクレイピング")
    
    if scrape_ok:
        votes_after_ts = get_file_timestamp(VOTES_FILE)
        # votes_summary.json が更新された（または前回完了している）場合、対立議案分析を実行
        issues_ok, _ = run_script(GENERATE_ISSUES_SCRIPT, "Geminiによる新規対立議案の争点分析")
        if not issues_ok:
            log("対立議案分析でエラーが発生しましたが、パイプラインは続行します", "WARN")
    else:
        log("議案スクレイピングでエラーが発生しましたが、パイプラインは続行します", "WARN")
    
    log("--- [議決・賛否データの更新チェック完了] ---")

    # 4. 議事録の差分確認
    after_ts = get_file_timestamp(CRAWLED_FILE)

    # 議事録が更新されたか、あるいは議決データ側で更新（未解析議案の処理含む）があったか
    minutes_updated = after_ts > before_ts
    
    if minutes_updated:
        log("🆕 新しい議事録が追加・更新されました。Gemini解析パイプラインを実行します。")
        
        # 5. Gemini 評価バッチの実行
        ok, _ = run_script(ANALYZE_SCRIPT, "Gemini 評価バッチ")
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
            
    else:
        log("✅ 新しい議事録はありませんでした。")

    # 8. 全体のGit差分チェックとデプロイ
    # （議事録が更新されていなくても、議案データ・AI争点解説が更新されていればプッシュする）
    if check_for_changes():
        log("データファイルに変更があります。デプロイ処理へ進みます。")
        push_to_github()
    else:
        log("✅ 変更されたデータはありませんでした（手元のデータは最新です）。")

    print("="*60)
    log("🎉 パイプラインが安全に終了しました。")
    print("="*60)

if __name__ == "__main__":
    main()