import sys
from pathlib import Path
import subprocess

pipeline_dir = Path("../data-pipeline")

if not pipeline_dir.exists():
    print(f"⚠️ {pipeline_dir.resolve()} が見つかりません。ディレクトリ階層を確認してください。")
    sys.exit(1)

# PDF抽出に関連しそうなスクリプトを検索
candidates = list(pipeline_dir.glob("*bulletin*.py")) + \
             list(pipeline_dir.glob("*pdf*.py")) + \
             list(pipeline_dir.glob("*extract*.py"))

candidates = list(set(candidates))

if not candidates:
    print("⚠️ 該当するPDF読み取りスクリプトが見つかりませんでした。")
    print("data-pipeline 内の既存Pythonスクリプト一覧:")
    for f in pipeline_dir.glob("*.py"):
        print(f"  - {f.name}")
else:
    print("✅ 以下のPDF読み取り/抽出スクリプトが見つかりました:")
    for script in candidates:
        print(f"\n▶ {script.name}")
        print("-" * 40)
        # 使い方（ヘルプ）を出力して引数を確認
        try:
            result = subprocess.run(["python", str(script), "--help"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            out = result.stdout.strip()
            err = result.stderr.strip()
            if out:
                print(out)
            elif err:
                print(err)
            else:
                print("(ヘルプ出力なし)")
        except Exception as e:
            print(f"実行エラー: {e}")
