import os
import sys
import json
import shutil
import subprocess
import time
from datetime import datetime
import requests

# パス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
ENV_FILE = os.path.join(BASE_DIR, ".env")
# サービスアカウント認証の自動設定（完全無人実行用）
SA_KEY_FILE = os.path.join(BASE_DIR, "service_account.json")
if os.path.exists(SA_KEY_FILE):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SA_KEY_FILE

FRONTEND_DATA_DIR = os.path.join(PROJECT_ROOT, "frontend", "public", "data")

# スクリプトのパス（京都）
FETCH_SCRIPT = os.path.join(BASE_DIR, "fetch_sagebase.py")
ANALYZE_SCRIPT = os.path.join(BASE_DIR, "batch_analyze_council.py")
TIMELINE_SCRIPT = os.path.join(BASE_DIR, "build_timeline_contexts.py")
STATIC_DATA_SCRIPT = os.path.join(BASE_DIR, "generate_static_data.py")
SCRAPE_VOTES_SCRIPT = os.path.join(BASE_DIR, "scrape_kyoto_votes.py")
GENERATE_ISSUES_SCRIPT = os.path.join(BASE_DIR, "generate_bill_issues.py")
GENERATE_ISSUES_OSAKA_SCRIPT = os.path.join(BASE_DIR, "generate_osaka_bill_issues.py")
BUILD_PLEDGE_TRACKER_SCRIPT = os.path.join(BASE_DIR, "build_pledge_tracker.py")
BUILD_MAYOR_TRACKER_SCRIPT = os.path.join(BASE_DIR, "build_mayor_tracker.py")

# スクリプトのパス（大阪）
BUILD_PLEDGE_TRACKER_OSAKA_SCRIPT = os.path.join(BASE_DIR, "build_pledge_tracker_with_extracted_osaka.py")
BUILD_MAYOR_TRACKER_OSAKA_SCRIPT = os.path.join(BASE_DIR, "build_mayor_tracker_osaka.py")

# スクリプトのパス（名古屋）
BUILD_MAYOR_TRACKER_NAGOYA_SCRIPT = os.path.join(BASE_DIR, "build_mayor_tracker_nagoya.py")

# 3都市共通 統合トピック要約ジェネレーター
UNIFIED_TOPIC_SCRIPT = os.path.join(BASE_DIR, "generate_unified_topic_summaries.py")

# 自動テストスクリプト（ルート直下）
COMPREHENSIVE_TEST_SCRIPT = os.path.join(PROJECT_ROOT, "run_comprehensive_test.py")

# 出力・監視対象のファイル
CRAWLED_FILE = os.path.join(BASE_DIR, "sagebase_crawled_data.json")

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

    colors = {
        "success": 0x2ecc71,  # 緑
        "info": 0x3498db,     # 青
        "warn": 0xf39c12,     # 黄
        "error": 0xe74c3c     # 赤
    }
    color = colors.get(status, 0x3498db)

    fields = [
        {"name": "実行環境", "value": "タスクスケジューラ / 手動実行", "inline": True},
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
            "footer": {"text": "議会のミカタ パイプライン監視"}
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

def run_script(script_path, description, args=None):
    log(f"{description} を開始...")
    if not os.path.exists(script_path):
        log(f"スクリプトが見つかりません（スキップ）: {os.path.basename(script_path)}", "WARN")
        return False, "File not found"
    try:
        python_exe = sys.executable
        cmd = [python_exe, script_path]
        if args:
            cmd.extend(args)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        log(f"{description} 完了")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        log(f"{description} でエラー発生！", "ERROR")
        print("--- Error Output ---")
        print(e.stderr)
        print("--------------------")
        return False, e.stderr

def sync_osaka_mayor_files():
    """大阪市長トラッカーの出力ファイル名をフロントエンド参照名と同期"""
    src_a = os.path.join(FRONTEND_DATA_DIR, "mayor_tracker_osaka.json")
    dst_a = os.path.join(FRONTEND_DATA_DIR, "osaka_mayor_tracker.json")
    if os.path.exists(src_a):
        try:
            shutil.copy2(src_a, dst_a)
            log("大阪市長トラッカーファイル名同期完了 (osaka_mayor_tracker.json)")
        except Exception as e:
            log(f"ファイル同期中に警告: {e}", "WARN")

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
        raw_title = sample.get("meeting_title", "").strip()
        sample_title = raw_title[:20]
        
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

def run_pre_deploy_test():
    """デプロイ直前の自動ヘルスチェック（Playwright自動巡回）"""
    if not os.path.exists(COMPREHENSIVE_TEST_SCRIPT):
        log("自動巡回テストスクリプトが見つかりません。テストをスキップします。", "WARN")
        return True, ""
    log("🛡️ デプロイ前の自動健全性テスト（Playwright全画面巡回）を実行中...")
    try:
        python_exe = sys.executable
        res = subprocess.run([python_exe, COMPREHENSIVE_TEST_SCRIPT], capture_output=True, text=True, check=True)
        if "全画面・全モーダル・全タブ正常" in res.stdout or "全ページ正常" in res.stdout:
            log("✅ 自動健全性テスト合格（UIクラッシュ・404・コンソールエラーなし）")
            return True, ""
        else:
            log("❌ 自動テストでUIエラーが検知されました", "ERROR")
            return False, res.stdout
    except subprocess.CalledProcessError as e:
        log("❌ 自動健全性テスト実行中にエラーが発生しました", "ERROR")
        return False, e.stderr

def push_to_github(custom_detail=""):
    log("GitHub への自動デプロイを開始...")
    try:
        os.chdir(PROJECT_ROOT)
        subprocess.run(["git", "add", "frontend/public/data"], check=True)
        
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        if custom_detail:
            commit_msg = f"Auto-update: {custom_detail} を追加・反映 ({now_str})"
        else:
            commit_msg = f"Auto-update: 京都・大阪・名古屋 議決・公約・政策タイムライン最新化 ({now_str})"
            
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        log(f"✅ GitHub へのプッシュが完了（{commit_msg}）。")
        return True, commit_msg
    except subprocess.CalledProcessError as e:
        log(f"Git プッシュ処理中にエラーが発生しました: {e}", "ERROR")
        return False, str(e)

def main():
    is_dry_run = "--dry-run" in sys.argv or "--no-push" in sys.argv

    print("\n" + "="*60)
    log("定期監視・全自動データ更新パイプライン（京都・大阪・名古屋 統合版）を開始")
    if is_dry_run:
        log("🧪 ドライランモード: GitHub へのデプロイ（commit/push）は行われません")
    print("="*60)

    # 1. 取得前の議事録 ID を控える
    before_ids = load_crawled_ids()
    before_count = len(before_ids)

    # 2. 議事録データの取得 (fetch_sagebase)
    success, output = run_script(FETCH_SCRIPT, "新着議事録データの取得")
    if not success:
        log("データ取得で致命的エラー。パイプラインを中断します。", "ERROR")
        notify_discord("❌ 定期更新エラー: 議事録取得失敗", "データ取得スクリプトの実行中にエラーが発生しました。", status="error", error_detail=output)
        return

    # 3. 議決・賛否データの更新（3都市共通エンジン）
    log("--- [議決・賛否データの更新チェック] ---")
    scrape_ok, _ = run_script(SCRAPE_VOTES_SCRIPT, "議会公式HPからの議案・賛否スクレイピング（京都）")
    if os.path.exists(GENERATE_ISSUES_SCRIPT):
        for c in ["kyoto", "osaka", "nagoya"]:
            run_script(GENERATE_ISSUES_SCRIPT, f"Geminiによる対立議案の争点分析（{c.upper()}）", args=["--city", c])
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

        # 7. フロントエンド用 サマリー生成
        ok, err = run_script(STATIC_DATA_SCRIPT, "フロントエンド用 サマリーJSON生成")
        if not ok:
            notify_discord("❌ 定期更新エラー: サマリー生成失敗", "statements_summary.json の生成中にエラーが発生しました。", status="error", error_detail=err)
            return

    else:
        log("✅ 新しい議事録はありませんでした。")

    # 7.6 政策タイムライン（マクロ論戦マップ）の最新化（3都市統合）
    log("--- [政策タイムラインの最新化（3都市）] ---")
    if os.path.exists(UNIFIED_TOPIC_SCRIPT):
        for city in ["osaka", "nagoya"]:
            run_script(UNIFIED_TOPIC_SCRIPT, f"政策タイムラインの差分更新（{city.upper()}）", args=["--city", city])
    log("--- [政策タイムラインの最新化完了] ---")

    # 7.7 議員看板公約トラッカーの最新化（京都・大阪）
    log("--- [議員公約トラッカーの最新化] ---")
    p_ok, _ = run_script(BUILD_PLEDGE_TRACKER_SCRIPT, "京都市議 看板公約トラッカーの再結合")
    if not p_ok:
        log("京都市議公約トラッカー更新で警告が出ましたが続行します", "WARN")

    p_osaka_ok, _ = run_script(BUILD_PLEDGE_TRACKER_OSAKA_SCRIPT, "大阪市議 看板公約トラッカーの再結合")
    if not p_osaka_ok:
        log("大阪市議公約トラッカー更新で警告が出ましたが続行します", "WARN")

    # 7.8 首長 政策ライフサイクル×予算トラッカーの最新化（京都・大阪・名古屋）
    log("--- [首長政策トラッカーの最新化] ---")
    m_ok, _ = run_script(BUILD_MAYOR_TRACKER_SCRIPT, "京都市長（松井市長）政策・予算トラッカーの更新")
    if not m_ok:
        log("京都市長政策トラッカー更新で警告が出ましたが続行します", "WARN")

    m_osaka_ok, _ = run_script(BUILD_MAYOR_TRACKER_OSAKA_SCRIPT, "大阪市長（横山市長）政策・予算トラッカーの更新")
    if not m_osaka_ok:
        log("大阪市長政策トラッカー更新で警告が出ましたが続行します", "WARN")

    if os.path.exists(BUILD_MAYOR_TRACKER_NAGOYA_SCRIPT):
        run_script(BUILD_MAYOR_TRACKER_NAGOYA_SCRIPT, "名古屋市長（広沢市長）政策・予算トラッカーの更新")
    
    # 大阪首長トラッカーのファイル名同期
    sync_osaka_mayor_files()
    log("--- [公約・政策トラッカーの最新化完了] ---")

    # 8. Git差分チェックと安全なデプロイ
    has_changes = check_for_changes()
    if has_changes:
        log("データファイルに変更があります。")

        # 🛡️ プッシュ前の自動健全性検証
        test_passed, test_err = run_pre_deploy_test()
        if not test_passed:
            log("❌ 自動健全性テストに失敗したため、安全のため GitHub デプロイを中止しました。", "ERROR")
            notify_discord("❌ 定期更新中断: 画面健全性チェック不合格", "データ生成後に実施した全画面巡回テストで異常が検知されたため、本番サイトの破壊を防ぐためデプロイを中断しました。", status="error", error_detail=test_err)
            return

        if is_dry_run:
            log("🧪 ドライランのため、GitHub へのコミット・プッシュはスキップしました。", "WARN")
            notify_discord("🧪 テスト実行完了: 新着データあり（未デプロイ）", "ドライランモードで実行されたため、GitHub へのプッシュは保留されました。", status="info")
        else:
            push_ok, push_msg = push_to_github(new_detail_str)
            if push_ok:
                detail_desc = f"**更新内容:** {new_detail_str}\n京都・大阪・名古屋の最新データを自動検証の上、GitHub (`main`) へ安全にデプロイしました。" if new_detail_str else "京都・大阪・名古屋の議決・公約・首長トラッカーを自動検証の上、GitHub へデプロイしました。"
                notify_discord("🎉 定期更新完了: 京都・大阪・名古屋の最新データを反映", detail_desc, status="success")
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