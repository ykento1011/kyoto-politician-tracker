import os
import sys
import json
import subprocess
import time
from datetime import datetime
import requests

# パス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
ENV_FILE = os.path.join(BASE_DIR, ".env")

# スクリプトのパス
FETCH_SCRIPT = os.path.join(BASE_DIR, "fetch_sagebase.py")
ANALYZE_SCRIPT = os.path.join(BASE_DIR, "batch_analyze_council.py")
TIMELINE_SCRIPT = os.path.join(BASE_DIR, "build_timeline_contexts.py")
STATIC_DATA_SCRIPT = os.path.join(BASE_DIR, "generate_static_data.py")
REMAP_SCRIPT = os.path.join(BASE_DIR, "remap_categories.py")
SCRAPE_VOTES_SCRIPT = os.path.join(BASE_DIR, "scrape_kyoto_votes.py")
GENERATE_ISSUES_SCRIPT = os.path.join(BASE_DIR, "generate_bill_issues.py")
TOPIC_TIMELINES_SCRIPT = os.path.join(BASE_DIR, "generate_topic_timelines.py")
BUILD_PLEDGE_TRACKER_SCRIPT = os.path.join(BASE_DIR, "build_pledge_tracker.py")
BUILD_MAYOR_TRACKER_SCRIPT = os.path.join(BASE_DIR, "build_mayor_tracker.py")

# 出力・監視対象のファイル
CRAWLED_FILE = os.path.join(BASE_DIR, "sagebase_crawled_data.json")
VOTES_FILE = os.path.join(PROJECT_ROOT, "frontend", "public", "data", "votes_summary.json")

def load_webhook_url():
    """data-pipeline/.env から DISCORD_WEBHOOK_URL を安全に読み込む"""
    if not os.path.exists(ENV_FILE):
        return None
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DISCORD_WEBHOOK_URL="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return val if val else None
    except Exception:
        pass
    return None

def notify_discord(title, description="", status="info", error_detail=""):
    """Discord Webhook へ Embed 形式で通知を送信"""
    webhook_url = load_webhook_url()
    if not webhook_url:
        return

    # ステータス別カラー (16進数RGB)
    colors = {
        "success": 0x2ecc71,  # 緑
        "info": 0x3498db,     # 青
        "warn": 0xf39c12,     # 黄
        "error": 0xe74c3c     # 赤
    }
    color = colors.get(status, 0x3498db)

    fields = [
        {"name": "実行環境", "value": "Windows タスクスケジューラ (ローカル)", "inline": True},
        {"name": "実行時刻", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True}
    ]

    if error_detail:
        snippet = error_detail[-800:] if len(error_detail) > 800 else error_detail
        fields.append({"name": "エラー抜粋", "value": f"```text\n{snippet}\n```", "inline": False})

    payload = {
        "username": "議会のミカタ 自動更新Bot",
        "avatar_url": "https://gikai-mikata.jp/favicon-96x96.png",
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "fields": fields,
            "footer": {"text": "議会のミカタ 京都 パイプライン監視"}
        }]
    }

    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Discord 通知の送信に失敗しました: {e}")

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emoji = "🚀" if level == "INFO" else "⚠️" if level == "WARN" else "❌"
    print(f"[{ts}] {emoji} {msg}", flush=True)

def run_script(script_path, description):
    log(f"{description} を開始...")
    if not os.path.exists(script_path):
        log(f"スクリプトが見つかりません: {script_path}", "WARN")
        return False, "File not found"
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
    if os.path.exists(CRAWLED_FILE):
        try:
            with open(CRAWLED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {f"{d.get('meeting_id')}_{d.get('sequence_number')}" for d in data}
        except Exception:
            return set()
    return set()

def summarize_new_minutes(before_ids):
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
    try:
        os.chdir(PROJECT_ROOT)
        result = subprocess.run(["git", "status", "--porcelain", "frontend/public/data"], capture_output=True, text=True, check=True)
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        log("Git の状態確認に失敗しました", "ERROR")
        return False

def push_to_github(custom_detail=""):
    log("GitHub への自動デプロイを開始...")
    try:
        os.chdir(PROJECT_ROOT)
        subprocess.run(["git", "add", "frontend/public/data"], check=True)
        
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        if custom_detail:
            commit_msg = f"Auto-update: {custom_detail} を追加・反映 ({now_str})"
        else:
            commit_msg = f"Auto-update: 議決・公約・政策タイムラインデータの最新化 ({now_str})"
            
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        log(f"✅ GitHub へのプッシュが完了（{commit_msg}）。")
        return True, commit_msg
    except subprocess.CalledProcessError as e:
        log(f"Git プッシュ処理中にエラーが発生しました: {e}", "ERROR")
        return False, str(e)

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
        notify_discord("❌ 定期更新エラー: 議事録取得失敗", "Sagebaseからのデータ取得中にエラーが発生しました。", status="error", error_detail=output)
        return

    # 3. 議決・賛否データの更新
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
        
        # 5. Gemini 評価バッチ
        ok, err = run_script(ANALYZE_SCRIPT, "Gemini 評価バッチ（未評価差分のみ）")
        if not ok:
            notify_discord("❌ 定期更新エラー: Gemini評価失敗", "Gemini 4軸分析バッチの実行中にエラーが発生しました。", status="error", error_detail=err)
            return

        # 6. JSON 分割・タイムライン生成
        ok, err = run_script(TIMELINE_SCRIPT, "タイムライン・コンテキストJSON分割")
        if not ok:
            notify_discord("❌ 定期更新エラー: タイムライン生成失敗", "タイムラインJSONの分割処理中にエラーが発生しました。", status="error", error_detail=err)
            return

        # 7. フロントエンド用 サマリー生成（カテゴリー精査・原本URL統合版）
        ok, err = run_script(STATIC_DATA_SCRIPT, "フロントエンド用 サマリーJSON生成")
        if not ok:
            notify_discord("❌ 定期更新エラー: サマリー生成失敗", "statements_summary.json の生成中にエラーが発生しました。", status="error", error_detail=err)
            return

        # 7.6 政策タイムライン（topic_summaries.json）の最新化
        ok, _ = run_script(TOPIC_TIMELINES_SCRIPT, "32大政策論点タイムラインの差分更新")
        if not ok:
            log("政策タイムライン更新で警告が出ましたがパイプラインは続行します", "WARN")

    else:
        log("✅ 新しい議事録はありませんでした。")

    # 7.7 看板公約トラッカー（pledge_tracker.json）の最新化
    log("--- [公約・政策トラッカーの最新化] ---")
    p_ok, _ = run_script(BUILD_PLEDGE_TRACKER_SCRIPT, "議員看板公約トラッカーの再結合（質疑・採決リンク更新）")
    if not p_ok:
        log("議員公約トラッカー更新で警告が出ましたが続行します", "WARN")

    # 7.8 松井市長 政策ライフサイクル×予算トラッカー（mayor_tracker.json）の最新化
    m_ok, _ = run_script(BUILD_MAYOR_TRACKER_SCRIPT, "松井市長 政策ライフサイクル・予算トラッカーの更新")
    if not m_ok:
        log("市長政策トラッカー更新で警告が出ましたが続行します", "WARN")
    log("--- [公約・政策トラッカーの最新化完了] ---")

    # 8. Git差分チェックとデプロイ
    has_changes = check_for_changes()
    if has_changes:
        log("データファイルに変更があります。デプロイ処理へ進みます。")
        push_ok, push_msg = push_to_github(new_detail_str)
        if push_ok:
            detail_desc = f"**更新内容:** {new_detail_str}\nGitHub (`main`) への自動デプロイが完了しました。" if new_detail_str else "議決・公約・政策トラッカーの更新を反映し、GitHub へデプロイしました。"
            notify_discord("🎉 定期更新完了: 新着データを反映しました", detail_desc, status="success")
        else:
            notify_discord("⚠️ 定期更新警告: Gitプッシュ失敗", f"データ生成は成功しましたが、GitHub へのプッシュに失敗しました。\n`{push_msg}`", status="warn")
    else:
        log("✅ 変更されたデータはありませんでした（手元のデータは最新です）。")
        notify_discord("✅ 定期チェック完了: 新着データなし", "議事録・議決データの定期巡回を実施しました。更新対象の差分はありませんでした。", status="info")

    print("="*60)
    log("🎉 パイプラインが安全に終了しました。")
    print("="*60)

if __name__ == "__main__":
    main()
