@echo off
chcp 65001 > nul
echo ============================================================
echo [ %date% %time% ] 議会のミカタ 定期自動更新パイプライン開始
echo ============================================================

cd /d "%~dp0.."

:: 仮想環境の有効化
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: 1. 通常データ更新 & 第1層: 死活監視
echo.
echo >>> [STEP 1/3] run_update.py（通常バッチ & 一次資料死活監視）実行中...
python data-pipeline/run_update.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] run_update.py で致命的エラーが発生しました。
    exit /b %ERRORLEVEL%
)

:: 2. 第2層: トリガー駆動型 一次資料探索エージェント
echo.
echo >>> [STEP 2/3] update_evidence_url.py（キュー内失効URLの自律探索）実行中...
python data-pipeline/update_evidence_url.py --from-queue data-pipeline/data/evidence_health_queue.json

:: 3. 第3層: GitHub PR 自動起票 & Discord 通知
echo.
echo >>> [STEP 3/3] orchestrate_evidence_pr.py（PR自動起票 & Discord通知）実行中...
python data-pipeline/orchestrate_evidence_pr.py

echo.
echo ============================================================
echo [ %date% %time% ] 全自動更新および自浄パイプライン完走
echo ============================================================
