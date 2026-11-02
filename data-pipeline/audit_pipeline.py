import os
import re
import glob

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 80)
print("【静的監査実行】data-pipeline 取得アーキテクチャ調査（クエリ発行: 0件）")
print("=" * 80)

# 対象Pythonスクリプト一覧（監査・適用ツール自身は除外）
py_files = [
    f for f in glob.glob(os.path.join(PIPELINE_DIR, "**", "*.py"), recursive=True) 
    if "audit_" not in os.path.basename(f) and "apply_" not in os.path.basename(f)
]

# -------------------------------------------------------------
# 1. BigQuery クライアント・クエリ呼び出し監査
# -------------------------------------------------------------
print("\n### 1. BigQuery (google.cloud.bigquery) 呼び出し監査結果")

for py_path in py_files:
    rel_path = os.path.relpath(py_path, os.path.dirname(PIPELINE_DIR))
    with open(py_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        lines = content.splitlines()

    has_bq_import = "google.cloud" in content and "bigquery" in content
    has_client_call = "bigquery.Client" in content

    if has_bq_import or has_client_call:
        print(f"\n📂 対象ファイル: {rel_path}")
        
        # ファイル全体で安全弁（maximum_bytes_billed）が定義されているか
        file_has_safe_config = "maximum_bytes_billed" in content

        for i, line in enumerate(lines, 1):
            if ".query(" in line:
                # 前後10行のローカルコンテキスト
                context = "\n".join(lines[max(0, i-10):min(len(lines), i+10)])
                
                # 安全弁の判定: 直近コンテキスト内にあるか、または job_config / SAFE_JOB_CONFIG が渡されているか
                has_safety_guard = (
                    "maximum_bytes_billed" in context or 
                    "dry_run" in context or 
                    ("job_config" in line and file_has_safe_config)
                )
                
                in_loop = any(re.match(r"^\s*(for|while)\s+", lines[j]) for j in range(max(0, i-15), i))
                
                print(f"  - L{i}: クエリ発行検出: `{line.strip()}`")
                print(f"    - 安全弁 (maximum_bytes_billed / dry_run): {'✅ あり' if has_safety_guard else '❌ なし（危険）'}")
                print(f"    - ループ内発行の疑い (N+1): {'⚠️ 検出あり' if in_loop else 'なし'}")

        # スキャン対象テーブルの推定
        tables = set(re.findall(r"FROM\s+[`'\"]?([\w\.\-]+)[`'\"]?", content, re.IGNORECASE))
        if tables:
            print(f"  - 参照テーブル: {', '.join(tables)}")

print("\n" + "=" * 80)
print("【監査スキャン完了】")
