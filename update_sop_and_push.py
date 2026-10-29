import json
import re
import subprocess
from pathlib import Path

ROOT = Path(".")
SOP_FILE = ROOT / "議会のミカタSOP.txt"

if not SOP_FILE.exists():
    print(f"❌ {SOP_FILE} が見つかりません。")
    exit(1)

content = SOP_FILE.read_text(encoding="utf-8")

# 1. トラブルシューティング表に追記する項目
new_troubles = """| 他都市で選挙区に「京都」、政党に議会名が表示される | `SpeakerCard.jsx` 内の三項演算子フォールバックに他都市名が直書きされていた | 他都市名・議会名へのフォールバック定数を完全撤廃し、データが存在する場合のみ表示、未設定時は「無所属」とする |
| 議員マスタJSONがあるのに会派や行政区が反映されない | `useStatements.js` が配列（`[`）形式のみを想定し、辞書（`{`）形式のマスタ読み込みをスキップしていた | `starts_with('[')` 単体判定を撤廃し、dict / array の両構造を自動判定して正規化・マージするロジックにする |
| 自治体公式名簿から顔写真が取得できない（特定議員のみ欠落） | 公式HTMLの `img[alt]` が氏名ではなく会派名になっていた、または画像と氏名が別テーブル・別DIVに分離している | `alt` 単体依存を排し、`<h3>` 議員名ブロックと直後の紹介枠（`.shokai_wp` 等）をペア走査して画像URLを抽出する |
| 名古屋市会議員が全員「無所属」と表示される | `speaker_stats.json` が「無所属」で初期化され、マスタのキー名が `party` ではなく `faction` になっていた | マスタの正規会派データをJSONに同期し、アダプター層で `faction` を `party` / `partyGroup` にマッピングして返却する |
"""

# トラブルシューティング表の末尾に追記
table_marker = "| `AttributeError: 'SourceFileLoader' object has no attribute 'load_module'`"
if table_marker in content and "他都市で選挙区に「京都」" not in content:
    idx = content.find(table_marker)
    line_end = content.find("\n", idx)
    content = content[:line_end + 1] + new_troubles + content[line_end + 1:]
    print("✅ トラブルシューティング・チェックリストに4件の実戦教訓を追記しました。")
elif "他都市で選挙区に「京都」" in content:
    print("ℹ️ トラブルシューティング項目は既に追記済みです。")

# 2. Phase 4 のマスタ取得原則に注意書きを追加
master_rule = """
   - 【厳格化】`speaker_stats.json` のデータ構造（辞書型 / リスト型）の完全吸収:
     都市によって `{ "議員名": { ... } }` または `[ { "speaker": ... } ]` で出力形式が異なる場合がある。`useStatements.js` は必ず両方の型を判定・展開し、姓名の空白除去キーおよび `aliases` 配列も含めた二重照合マップを構築すること。安易な `startsWith('[')` チェックでフェッチを破棄してはならない。
   - 【厳格化】不適切な他都市名フォールバックの禁止:
     UIコンポーネントにおいて、選挙区や会派が未取得の場合に `'京都'` や `'名古屋市会'` など推測や別都市の定数をフォールバック表示させる実装を完全禁止する（存在しない場合は非表示、または「無所属」と明記）。"""

if "【厳格化】`speaker_stats.json` のデータ構造" not in content:
    phase4_marker = "4. 姓名の表記揺れ・スペース耐性:"
    if phase4_marker in content:
        idx = content.find(phase4_marker)
        line_end = content.find("\n", idx)
        content = content[:line_end + 1] + master_rule + content[line_end + 1:]
        print("✅ Phase 4 にマスタ読み込み・フォールバック禁止の厳格原則を追記しました。")

# 3. 追記セクション（本日の作業サマリー）の付与
summary_entry = """
5. 【2026-10 実務記録】都市間UI標準化・データ連携および議員マスタ同期
- 横浜市会: 公式名簿の構造差分（alt=会派名）を解消し、現職86名全員の顔写真（86/86）を `frontend/public/councilors/yokohama` に完全配備。
- 都市フォールバック撤廃: `useStatements.js` の dict/array 両対応化と `SpeakerCard.jsx` のフォールバック除去により、横浜市トップにおける「京都」タグ漏洩および議会名による会派偽装を根本根絶。
- 名古屋市会: `nagoyaCouncilorMaster.js` の正式会派情報を `nagoya_speaker_stats.json` および `councilors_nagoya.json` に同期し、フロントエンド共通の `party` / `partyGroup` にマッピング統一。
"""

if "5. 【2026-10 実務記録】" not in content:
    content = content.rstrip() + "\n" + summary_entry
    print("✅ 運用基準末尾に本日の実務記録を追記しました。")

SOP_FILE.write_text(content, encoding="utf-8")
print(f"📄 {SOP_FILE.name} を正常に更新・保存しました。")

# 余分な仮ファイルがあれば掃除
temp_sop = ROOT / "docs" / "SOP.md"
if temp_sop.exists():
    temp_sop.unlink()
    print("🧹 docs/SOP.md（一時ファイル）を削除しました。")

# 4. Git コミット & プッシュ
print("\n" + "=" * 65)
print("🚀 Git Commit & Push 実行")
print("=" * 65)

def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr and res.returncode != 0:
        print(res.stderr.strip())
    return res.returncode

run_cmd("git add .")
commit_msg = "docs: update SOP with city fallback elimination, master sync and complete yokohama images"
run_cmd(f'git commit -m "{commit_msg}"')
push_res = run_cmd("git push")

if push_res == 0:
    print("\n🎉 GitHub への Push が正常に完了しました。")
else:
    print("\n⚠️ Push の実行ステータスを確認してください。")
