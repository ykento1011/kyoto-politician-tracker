# 京都会議録の同一性確認と保存済み運用検証

この変更は既存取得器・話者／議案境界・品質保留・追記検査の共通入口を整える。
定期ジョブへの導入、実通信、Gemini、公開は別工程。既存ジョブを差し替えない。

## 会議単位の取得／確認契約

`kyoto_one_meeting_guard.py --approval <private-approval.json>` は実通信入口。
このPRの検証では実行しない。承認のSHAを新コードに合わせ直しただけで実行してはならない。

| scope | 履歴の条件 | 完了状態 |
|---|---|---|
| `kyoto_verified_new_meeting` | 固定750会議と指定した保存履歴の両方に未登録 | 原本取得済み・オフライン照合待ち |
| `kyoto_meeting_identity_only` | いずれかに登録済み | `identity_confirmed_private_only` |

後者は通常の継続更新器が受け付ける取得receiptと区別し、履歴登録・解析・公開を行わない。
前者も原本保存だけで履歴追加や解析を自動実行しない。
従来scopeと呼出し形式を維持し、新規経路の重複拒否を緩めない。

両scopeは、`identity_review` に都市、資料区分、公式開催日、正式名称、委員会名、
回次、会期ID、日程IDを要求する。2023-05-01以降の現任期に限定する。
承認ファイルは次を拘束する。

- `identity_sources.catalog` と `identity_sources.activity`：非公開原本のpath／SHA、
  活動一覧のliteral／source_position／review_reference。資料区分は会議であること。
- `registered_history`：非公開保存履歴のpath／SHA。固定750会議のSHAも従来どおり固定。
- guard／transport／identity／path guardのコードSHA、PM承認参照、使い捨てrun_id。
- `requests`：セッションGET、日程POST、条件付き本文POSTの固定URL・完全一致パラメータ。
- 最大3通信、応答ごと2MiB・合計4MiB、25秒、1.2秒以上の間隔、
  TLS検証、転送・再試行なし。前段失敗・容量不明・日程不一致なら次通信を行わない。

日程の開催日・回次・IDと、本文冒頭の正式会議名・回次・日付が一致して初めて
同一性を確認する。原本とreceiptを非公開CASへ保存し読み戻す。収録完全性はunknown。
現在は京都委員会の「令和…（第…回）」形式に対応し、別形式を推測して受け入れない。

## 索引差分による候補管理

`kyoto_candidate_changes.reevaluate(previous_evidence, current_evidence,
candidates, records, mappings=None)` は読み取り専用の関数。
各evidenceは保存索引・取得receiptのpath／SHAを持つ。成功した公式POSTの応答との一致も検査する。
既存台帳のcandidate_key、checked_index_sha256、checked_reference_sha256を再利用する。
開催日の確認状態は既存の公式証拠から `official_date_confirmed` に渡す。

同一SHAは再照会を省き、索引変更時も会期IDまたは年・月・委員会・回次が関係する候補だけを
オフライン再評価する。公式の識別子参照には原本SHA・位置・原文を要求する。
録画や開催日の存在だけでは昇格しない。昇格先は照合待ちであり、通信許可でも同一性認証でもない。
開催日／日程不明は保留、資料と任期外は分析対象外。候補キー重複や破損は停止する。
返り値を現在の稼働台帳へ自動適用する処理は含めない。

## 保存済み経路のオフライン検証

`kyoto_saved_workflow.py inspect --config <private-config.json>` は書込みなし。
`stage` は指定した非公開領域だけに、既存追記アダプターを使った再現候補を作る。
`KYOTO_PRIVATE_ROOT` を既存非公開領域へ設定し、configの `files` に各入力の
path／SHA、`target` に上記identity_review形式、`output_root` に独立した保存先を指定する。

必須入力はhistory、acquisition、schedules、minutes、rows、master、legacy。
質疑がある場合はprepared_manifest、plan、analysis、api_policy、content_review、
quality_approval、candidate_summary、candidate_timeline、baselineも必要。
秘密情報・APIキーは不要。保存済みモデル結果だけを使用する。

1. 公式日程・本文原本・receiptを照合する。
2. 既存 `kyoto_thread_contract` の話者／議案境界で質疑を再構成する。
3. 解析入力・実プロンプト・話者・発言ID・モデル設定のfingerprintを保存planと照合する。
4. 既存 `kyoto_thread_repair` の解析receipt・部分公開審査を再利用する。
   全選択質疑の採用にも明示的な `approved_selected_results` 審査を必要とする。
5. 採用結果は要旨と評価理由の両方を原文照合した保存審査記録、結果SHA、原文位置を要求する。
   意味の正しさを自動認定する仕組みではない。保留質疑の混入は停止する。
6. 既存レコード不変・ID・原文・タイムライン対応を従来の追記検査で確認する。

stageは履歴上のbaselineを再現する検証用で、
`offline_replay_not_for_publication`／`publication_enabled=false` を明記する。
公開済み会議をもう一度公開する候補には使わない。失敗時に既存の正常ステージを上書きしない。

## 回帰と受入境界

```sh
python -B -m unittest discover -s tests -p "test_kyoto_meeting_guard.py"
python -B -m unittest discover -s tests -p "test_kyoto_operations_contract.py"
python -B -m unittest discover -s tests -p "test_kyoto_continuation.py"
python -B -m unittest discover -s tests -p "test_kyoto_thread_repair.py"
```

新規試験は合成原本を使い、socketと外部プロセスを禁止する。
保存済み6352は12採用・1保留、6353は14採用・2保留を非公開で再現した。
6346は同一性確認後に実質的質疑0件で停止する。非公開資料はリポジトリへ含めない。

5都市への展開には、都市ごとの任期・公式索引／日程／本文の契約、
議員名簿と話者・議案境界、公開JSONへの対応を保存原本で別途受け入れる必要がある。
京都のIDや固定750会議の条件を他都市へ流用しない。
