@echo off
echo ============================================================
echo Kyoto Politician Tracker - Scheduled Pipeline
echo ============================================================

cd /d "%~dp0.."

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo.
echo [STEP 1/3] Running run_update.py...
python data-pipeline\run_update.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] run_update.py failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

echo.
echo [STEP 2/3] Running update_evidence_url.py...
python data-pipeline\update_evidence_url.py --from-queue data-pipeline\data\evidence_health_queue.json

echo.
echo [STEP 3/3] Running orchestrate_evidence_pr.py...
python data-pipeline\orchestrate_evidence_pr.py

echo.
echo ============================================================
echo Pipeline Completed Successfully.
echo ============================================================
