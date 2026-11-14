# PM → Codex自動着手（安全限定版）

> **2026-11-14 初回パイロット限定**：本PRのworkflowは **Issue #19のみ**起動可能です。許可する変更は新規 `docs/CODEX_DISPATCH_SMOKE.md` 1ファイル、指定された2行＋末尾改行の完全一致のみ。Pythonコードや既存ファイルの変更は一切許可しません。試験完了後に汎用タスクへ拡張する場合は別PR・レビュー・代表承認が必要です。夜間の自動スケジュール起動や既存PMチャットの自動起動は実装対象外です。


## 役割と使い方

- 統括PMが**公開可能な**GitHub Issueを確認し、作業内容・許可変更範囲・受入条件・禁止事項を整えます。
- 統括PMは対象Issueに、単独行で **`/codex-run`** とコメントします。Issue作成だけでは開始されません。
- GitHub Actions が公式`openai/codex-action`でCodexを起動し、許可範囲内の変更だけを差分として収集します。
- 別の権限分離されたジョブで差分を適用し、**Draft PR**を作成します。既存CIと独立PM審査は別工程です。自動マージ・自動公開はありません。
- 初回は **Issue #19** の公開可能なMarkdown新規1ファイルのみで動作確認します。

## 有効化に必要な1回限りの管理操作

1. OpenAI API（ChatGPT月額契約とは別請求）の**専用プロジェクト**を作り、まず月額上限を設定して **Enforce a hard limit** を有効にする（API公式ヘルプに沿う）。専用APIキーを用意し、リポジトリ **Settings → Secrets and variables → Actions → New repository secret** で **`OPENAI_API_KEY`** として登録。値はIssueやチャットに投稿しない。
2. GitHub **Settings → Actions → General → Workflow permissions** の **Allow GitHub Actions to create and approve pull requests** を有効にする。各ジョブのGITHUB_TOKEN権限はworkflowで限定しています。
3. このDraft PRのCIと差分を確認し、**本番の自動デプロイ条件に影響がないことを別確認してから**、代表がmainへのマージを明示承認します。Workflowが既定ブランチに入るまではIssueコメントで自動起動できません。
4. その後Issue #19にオーナー自身が `/codex-run` と単独コメントして**1回のみ**実証。API課金とActions結果を確認し、Draft PRはレビュー後も自動マージしません。

## セキュリティ境界

- 実行するIssueは`ykento1011`本人が作成したOPEN Issueのみ。起動コメントも同じ本人の**完全一致** `/codex-run` に限定。オーナーのみ手動`workflow_dispatch`も可能です。
- GitHub-hosted Linux runnerで公開GitHubの`main`だけをcheckoutします。ローカルWindows作業領域・非公開Google Driveにはアクセスできません。
- CodexのジョブはGitHub読み取り権限、APIキーは公式actionの代理プロキシ経由。PRを開く別の書込みジョブにはOpenAI APIキーを渡しません。
- **初回パイロットはdocs/CODEX_DISPATCH_SMOKE.mdの新規作成のみ**。1ファイル・内容完全一致を二つの権限分離ジョブで検証し、変更予定外の差分は拒否します。パイロット後の拡張は別審査です。
- 公開リポジトリは**GitHub上のコミット自体が公開**されます。未公開原典・SHADOW・秘密情報・内部PMレビューをIssueやPRに含めないでください。
- **P1-INT2Bのローカル私有worktree、Issue #15の保存済みHTMLを使う修正はこのworkflowの対象外**です。安全な非公開環境に接続した別のランナーが必要です。
- `GITHUB_TOKEN`で開いたPRのCIはGitHubの仕様や設定によってWorkflow承認を追加で求める場合があります。CI合格まではマージしないでください。

## 障害切り分け

- 起動しない：Workflowが既定ブランチにあるか、Issue・コメントの本人条件を満たすか、コメントが完全一致か確認。
- `OPENAI_API_KEY`なし・API課金未設定：公式actionを実行できません。秘密値はGitHub Secretで設定します。
- Draft PR作成失敗：Actions GeneralのPR作成許可、権限、allowlist、runnerログを確認。
- 非公開・ローカル作業：GitHub-hosted runnerにはアクセスできません。公開リポジトリへ非公開資料をpushしてはいけません。

## 「完了」の定義

workflowのコードがPRに入っただけでは、運用完成とはしません。初回の安全な公開テストIssueで、**PMによる起動コメント → Actions上のCodex実行 → Draft PR → CI/PMによる受入** の一連の動作を確認して初めて本番運用開始とします。
## 評価指標と停止条件

- **実際の成功**：Issue #19のオーナーコメント1回 → Actions起動 → 定義した1ファイルだけのDraft PR自動作成 → CI/PM検証を追跡できること。
- **評価するのは往復削減**：代表の手動転記・Codex起動・ログ貼付の回数と、承認可能な成果が届くまでの時間。1ファイルの作成自体を事業成果とは扱いません。
- APIキー未設定、課金上限未設定、Actions権限不足、main自動公開の影響未確認なら **STOP**。秘密値をIssue・チャット・ログへ貼らない。既存公開データと非公開Driveのデータは操作しません。
- GitHub Actionsの`GITHUB_TOKEN`から生成したPRにはCI承認が追加で必要なことがあります。自動PR生成をCI合格・自動マージと混同しません。
