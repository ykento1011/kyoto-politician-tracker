# 保存原本1系列のオフライン再実行

既存の `operations` によるアドホック処理。取得、定期実行、公開とは別工程です。

1. 承認済みP1コードと、対象都市の保存済みCASを使用します。実証には原本を既存 `SnapshotStore` で複製した隔離CASを使います。
2. CASと別の所有者限定ディレクトリを新規に用意し、状態保存先にします。稼働中の週次状態を流用しません。
3. 下記の実値を記載した私有JSONを用意します。リポジトリに原本・状態・実行設定を置きません。
4. 承認済みPython、コード、Windowsでは固定PowerShellを使用して実行します。

```text
MAYOR_PWSH_EXE=<固定済みpwsh.exeのパス>
PYTHONPATH=<実行コードのdata-pipeline>
python -B -m mayor_updates.operations --replay-spec <所有者限定の私有JSON>
```

私有JSONの必須項目：

| 項目 | 内容 |
| --- | --- |
| `city`, `series_id`, `policy_ids` | 登録都市コード、単一系列ID、既存政策ID |
| `source` | `id`, `url`, `media_type` (`html`/`pdf`), `role` (`index`/`progress`), `fiscal_year`, `policy_ids` |
| `source.policy_id` | `progress` の対象政策ID |
| `source.selector`, `source.resolution_base` | 保存HTMLの位置と、確認済みの公式URL解決基準 |
| `source.review_pages` | PDFの明示的な位置。例：`[{"physical_page": 1}]`。印刷ページが確認済みなら `printed_page` も記録 |
| `sha256`, `document_id` | 保存済み最新版のSHAと都市別文書ID |
| `snapshot_root`, `state_root` | 都市専用CASと別の隔離状態ディレクトリ |
| `baseline` | 公開基準JSONの私有コピーの `path` と `sha256` |
| `p1_code_root`, `city_capable` | SHA検証対象の既存P1コード。都市対応版は `true` |
| `base_revision` | 基準コード版 |
| `network_enabled` | 省略または `false`。`true` は拒否 |

`source` の年度は保存レコードと一致させます。制度案内の管理年度を、予算の対象年度や成立の根拠に流用しません。

初回に都市・系列・政策・原典URL・CAS・基準JSONを状態へ固定します。別系列への転用、都市混入、非公式ホスト、原本SHA不一致、取得失敗を拒否します。京都の旧形式JSONは、都市名・公式選挙公報URL・政策IDが一致する場合に限り受け入れ、JSON自体は変更しません。

実行ごとの `replay_result.json` にSHA、文書ID、読み戻し結果、差分、レビュー件数、通信0件、公開書込み0件を記録します。変更がある場合のみ `new_reviews.html` を作成し、正常終了後に状態とレビュー識別子を一括保存します。同一版の再実行ではレビュー0件になります。停止時は終了コード2とし、前回の正常状態を保持します。ロック取得・私有領域確認に失敗した場合も処理を開始しません。

新しい保存版を処理する場合は、別途承認された取得工程で保全後、私有設定の `sha256` を明示的に更新します。この入口は添付PDFの取得、予算・進捗の自動認定、公開JSON更新を行いません。初回索引登録はリンク一覧の基準化であり、政策変更提案ではありません。

模擬改版は別CAS・別状態で行い、実際の過去版比較と区別します。稼働P1・固定SHA・定期タスクへの適用は別途判断します。
