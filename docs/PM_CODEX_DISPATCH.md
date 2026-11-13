# PM → Codex自動着手（安全限定版）

## 役割と使い方

- 統括PMが**公開可能な**GitHub Issueを確認し、作業内容・許可変更範囲・受入条件・禁止事項を整えます。
- 統括PMは対象Issueに、単独行で **`/codex-run`** とコメントします。Issue作成だけでは開始されません。
- GitHub Actions が公式`openai/codex-action`でCodexを起動し、許可範囲内の変更だけを差分として収集します。
- 別の権限分離されたジョブで差分を適用し、**Draft PR**を作成します。既存CIと独立PM審査は別工程です。自動マージ・自動公開はありません。
- 初回は本番用Issueではなく、公開可能な小さなPythonテスト修正Issueで動作確認します。

## 有効化に必要な1回限りの管理操作

1. OpenAI API（ChatGPT月額契約とは別請求）のAPIキーを用意し、リポジトリ **Settings → Secrets and variables → Actions → New repository secret** で **`OPENAI_API_KEY`** として登録。値はIssueやチャットに投稿しない。
2. GitHub **Settings → Actions → General → Workflow permissions** の **Allow GitHub Actions to create and approve pull requests** を有効にする。各ジョブのGITHUB_TOKEN権限はworkflowで限定しています。
3. このDraft PRのCIと差分を確認してから、既存のmain保護ルールに従ってマージします。Workflowが既定ブランチに入るまではIssueコメントで自動起動できません。

## セキュリティ境界

- 実行するIssueは`ykento1011`本人が作成したOPEN Issueのみ。起動コメントも同じ本人の**完全一致** `/codex-run` に限定。オーナーのみ手動`workflow_dispatch`も可能です。
- GitHub-hosted Linux runnerで公開GitHubの`main`だけをcheckoutします。ローカルWindows作業領域・非公開Google Driveにはアクセスできません。
- CodexのジョブはGitHub読み取り権限、APIキーは公式actionの代理プロキシ経由。PRを開く別の書込みジョブにはOpenAI APIキーを渡しません。
- 自動変更は`data-pipeline/`または`tests/`配下のPythonと`docs/`配下Markdownに限定。追加・変更のみ、最大8ファイル・200KB。構文チェック・差分チェックを実施します。
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