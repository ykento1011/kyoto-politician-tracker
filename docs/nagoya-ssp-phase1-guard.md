# 名古屋SSP Phase 1 — 通信無効の専用ガード

この変更は実通信を許可しない。`acquire_live()` は引数にかかわらず予約前に拒否する。
旧名古屋取得器・共通scraper・京都ガードをimport/起動しない。
PR #98・#71の未統合コードに依存しない。

## 固定契約

|順序|method / URL|body|
|---|---|---|
|1|GET `https://ssp.kaigiroku.net/tenant/nagoya/SpTop.html`|なし|
|2|POST `https://ssp.kaigiroku.net/dnp/search/councils/index`|`tenant_id=207&power_user=false`|

Refererは `https://ssp.kaigiroku.net/tenant/nagoya/SpMinuteBrowse.html`、
`X-Requested-With: XMLHttpRequest`。POSTはフォーム形式。
Cookieは空から開始し、同一合成実行内だけで同一ホストのsecure Cookieを引き継ぐ。
Cookie値はCAS・receiptへ保存しない。Phase間のCookie保存・引継ぎは実装しない。

2 attempts、各2MiB・総量4MiB、TLS必須、redirect/retry各0。
一回限りの子プロセスは`subprocess.run(timeout<=25)`で終了待ち、期限時はkill/waitされる。
親は単調時計で60秒の期限を管理し、各子に残時間以下を渡す。通信間隔は1.2秒。
この子は**合成応答の検査・返却だけ**で、HTTPクライアントは持たない。
合成HTTP属性の成功を実際のTLS・サーバー・Cookie互換性の証明とは扱わない。
さらに外部の60秒監督プロセスが、全ファイル検査・解析・保存を含むphase子全体を監督する。
強制終了時の残存ロック/試行は不明状態として保留する。HTTP応答子には状態書込み機能がない。
入力envelopeを起動前に制限し、出力は一時ファイルから上限付きで読む。
OS停止・プロセス生成自体の遅延まで保証するものではなく、実通信実装の受入は別に必要。

## 隔離状態と失敗

`run_synthetic`は`OFFLINE-TEST-ONLY.json`で明示されたリポジトリ外の一時領域のみ使用。
入力に実行主体、scope、原典source登録、承認参照、実行コード/実PythonバイナリSHA、
承認ハッシュに結び付くbinding、合成owner-only ACL、receipt名前空間を要求する。
**これらは試験fixtureであり、正規承認の署名や実ACL検査ではない。**
不備・不一致は子の起動/予約前に拒否。既存CASの読み戻し検証後にrunを一回限りで予約し、
各子起動前にattemptを排他的に記録する。成功時のみHEADをatomic replaceする。
処理失敗・不明時はrunを消費し、直前のHEADと既存CASを保持する。
失敗runに途中CASが残ることはあるが、正常HEADからは参照しない。
receiptの`synthetic_prepared`は合成原本の準備を示し、commit成功を主張しない。
正常状態へのcommit成立はHEADのrun_id一致で別に確認する。
ロックが残った異常終了は人手審査待ち。削除して同じrunを再試行しない。

## 試験

`python -B -m unittest discover -s tests -p test_nagoya_ssp_phase1_guard.py`

合成順序・ヘッダー・Cookie、URL/tenant/body/ACL/PIN/承認不一致、容量、
子・親期限、HTTP異常、未知JSONP、重複run、CAS/last-good保全を検査する。
実際の一回の合成子プロセス試験を含む。合成ACL変更は実ACL変更ではない。

## 実運用GOまで未成立

- 実取得・利用条件と名古屋tenant207のsource登録承認、実行主体・所有者限定ACL。
- 署名/管理された正規承認、実P1コード/依存PINと都市専用binding・receipt・保存先。
- ネットワーク境界で容量・TLS・転送/再試行禁止を強制する別審査のlive transport、
  外部watchdogの実運用審査、正規予約・監査の接続。

以上が不足する限り実通信0を維持する。Phase 2、加工キャッシュ候補676/2の認証、
Gemini、定期登録、公開JSON、Ready化、main統合はこの変更の対象外。
既存CAS・receipt・active binding・実予約・監視ジョブは変更しない。
