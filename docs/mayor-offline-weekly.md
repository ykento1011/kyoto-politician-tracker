# 3都市の保存原本による共通週次レビュー

## 境界と既存機構の再利用

main `2cf3af922d33a024e9c205532368c5e58384d7a9` から分離。
UI #96/#97、未マージの #87/#89/#93/#94 に依存しない。
`offline_weekly` → `continuous.cycle` → `operations.run_trial` → P1Bridge/CAS読取り → 私有レビューという既存経路を使う。
新しいHTTP取得器、Windowsタスク、通知送信、公開処理はない。

`config/mayor_offline_weekly.json` は保存資料の再処理用であり、source登録承認ではない。
全sourceはpending、取得無効。大阪の2026は追跡年であり、本文で確認した予算年度ではない。
都市・policy ID・資料用途・年度の根拠は別項目。政策との対応はHOLDのまま。

起動例は `python -B -m mayor_updates.offline_weekly --runtime <owner-only-runtime>`。
runtimeはnetwork_enabled=false、city、隔離state_root、snapshot_root、固定P1ルート、config/baseline/profileのSHA、code_filesのPINを必要とする。
実パス・receipt実体はリポジトリへ登録しない。CLIのPIN/ACL検査は合成試験の代替ではなく実環境接続時の別ゲート。

月曜09:00 JST以降の当週キーだけを消費し、過去週を取り戻さない。
同週の再試行は拒否。これは新設の隔離オフライン周期記録であり、既存の取得予約には触れない。
CASは読み取り、stateは都市・全profile・CAS絶対実体へ束縛する。
未知の構造、訂正・撤回・差替え・取消・追補は安全側のHOLD。キーワードは意味判定の証明ではなく例外抽出にのみ使う。
正常な文書改版も政策変更とは認定せず、原文位置を保持した非公開候補にする。
`city_report.json` はlast-good SHA、保存時刻、保存観測の経過日数、HOLD理由を出力する。
保存時刻の鮮度は新しいHTTP観測の鮮度ではない。

保存横浜HTMLの全角「令和８年度」で既存年度ガードが停止することを再現したため、年度文字の照合時だけNFKCで表記を揃える。原文・引用・原本SHAは変更せず、令和7年度への差替えはHOLDする。

## 今回の検証結果

- targeted: 新規10 PASS、既存continuous 6 PASS、periodic 21 PASS、operations 16 PASS／私有依存12 SKIP。合計53 PASS／12 SKIP。SKIPは実結合成功に数えない。
- 保存済み3都市HTMLの実バイトを隔離fixture bridgeへ読み取り、各都市の初回状態登録と次週のunchanged／追加レビュー0を確認。P1本体・receipt検証器を通す私有CLI結合試験ではない。
- 合成改版は3都市それぞれ非公開レビュー1件、同一版は追加0、同週重複は拒否。失敗・訂正・撤回・追補・未知構造・異年度・都市混入・CAS変更は停止しlast-goodを保持。
- private原本・既存CAS/state/予約への書込み0。試験用state/周期記録は一時隔離領域内だけ。公式GET、公開JSON、main、本番、既存監視変更0。
- 私有P1 CLI接続、正式source登録、実HTTPの再観測／実改版、Windows定期起動、外部通知、公開は未実施・別GO。
- 初回CodexレビューのP2・2件を修正。保存原本検査は周期予約後に実施し、SHA/MIME異常で停止しても失敗記録と予約を保持。修復後の同週再処理も拒否。selectorだけの空本文・見出しやレビュー可能原文位置の欠落もHOLDする。

## 保存原本の限定照合（通信0）

| 都市 | 既存資料 | 原本SHA256 |
|---|---|---|
| 大阪 | 保育料制度案内HTML | e9151f0f53408da7df3157540b41f3e46f374d457dd43406314f698167de8842 |
| 横浜 | R8予算索引HTML | 872f5c8da45129bd6a3296269942880e20eeac8de6a163bb556e2bde294ae98b |
| 神戸 | R8予算特別委員会HTML | ec68e69dfa5a720aa1eb08abe5b6b9714c24c4663945e29a84cea800e75b42ae |

今回の実バイト読戻しと上記SHAは一致。保存HTMLからselectorを確認。
合成fixtureの変更を公式原典の実改版とは扱わない。既存実取得成功を今回の新しい取得実績として数えない。

## 横浜主要事業PDFの最終プレフライト

固定URL: https://www.city.yokohama.lg.jp/city-info/zaisei/jokyo/yosan/r8/r8yosan.files/R8yosan-shuyou.pdf

| 項目 | 結果 |
|---|---|
| 保存索引 | 上記横浜SHAの実バイト一致。`#tmp_contents` 内のanchor ordinal 17 |
| 正確なhref・文書名 | `r8yosan.files/R8yosan-shuyou.pdf`／資料編（主要事業一覧）（PDF：1,014KB） |
| 年度・掲載区分 | 令和8年度予算、令和8年1月26日 |
| 文書ID案 | `yokohama-doc-a19d0abfd5a6d4ca51da9599`。URL規則からの案であり登録完了ではない |
| 保存PDF・receipt・予約 | 調査した既存私有領域のJSON参照では当該PDFは索引候補2ファイルのみ。取得済み原本・receipt・予約は確認できず。不存在の全環境保証ではない |
| 既存取得候補PIN | 保存済み承認manifestの18ファイルすべて一致。旧索引取得コードmanifestも一致 |
| 既存ACL | 候補コード、横浜CAS、取得state、receiptsで現行owner-only検査PASS |
| 既存binding | 保存binding SHA読戻し一致。ただし索引HTML用なのでPDFへ転用しない |
| 正式source承認／個別通信GO | PDFについて未成立。以前の1GETは索引HTML限定であり流用不可 |
| 専用scope/binding・実行予約 | 未作成。承認後に別途検証。現在実行可能とは判定しない |

既存validate_scopeは総量2MiBの案をHTML1件＋PDF1件／4MiB契約との不一致で拒否する。
既存4MiB契約での診断用メモリ案も、保存索引をindex_urlに持ちながらHTMLを取得対象に含めないため拒否することを通信0で確認した。
上限を拡大して実行せず、索引も再GETしない。保存索引の読取り照合を持つPDF専用契約は別の最小設計・Coding GOが必要。

判定HOLD／現在の実GETはNO-GO。次の個別承認は上記1URL、1GET、2MiB、親の壁時計10秒、TLS検証、redirect/retry/追加リンク0。
保存済み同URLを再確認してから排他的に予約し、失敗・不明・中断は予約を保持して停止、再取得しない。
専用固定scope/binding、実行時PIN/ACL、登録承認・個別GOが揃ってから実施。今回作成しない。
目的はM01との関連候補の探索のみ。予算認定・公約達成認定・旧404出典の置換はしない。

## 大阪・名古屋のHOLD

大阪のCDN公約PDFは登録URLとして存在するが、保存済み保育料HTMLにはCDNへの掲載リンクがない。
制度案内は公約PDFの出所も登録予算も証明しない。
既存生成器の公式候補 `https://www.city.osaka.lg.jp/senkyo/` は広い選挙索引であり、該当公約への直接掲載元とは未確認。
次の取得を提案する場合はこの索引1GET/2MiB/10秒、リンク追跡0から。保存済み同URLの原本有無と専用ガード、PM個別GOが前提。CDN自体を公式として取得しない。

名古屋の保存制度案内は令和7年度減税額見込み102億円と既存5%減税の説明を含む。
登録額は「平年約120〜130億円減収織込」、資料ラベルは「財政局主要事業説明書（一般財源）」だが、当該会計・算定範囲を今回確認できていない。
年度見込み／平年値、対象税目と控除範囲、会計、減収と事業費、5%継続と10%公約を区別する。
原典候補は既登録URL `https://www.city.nagoya.jp/shikai/shingi/1030858/1030859/1030860.html`。
1GET/2MiB/10秒・追加リンク0の候補に留め、資料名・年度・税目を確認する用途。一般財源という登録ラベルだけで会計を認証しない。保存有無・専用ガード・個別GOは未成立。
既存102億円HTMLは再取得不要。金額差の推測補完、10%実現・予算成立・執行認定はしない。

## 5都市の準備状況と次ゲート

| 都市 | 現在 | 残条件 |
|---|---|---|
| 京都 | 既存6資料運用を変更せず維持 | 11/23 09:00予定・12:00管理期限の実イベント／receipt照合。今回の試験と別 |
| 大阪 | 保存制度HTMLを共通オフライン経路へ接続 | source正式登録、CDN出所、実改版・運用承認 |
| 名古屋 | 既存同一SHA再観測の受入を継承 | 今回の3都市profileへ未接続。同じ設定方式で追加可能。120〜130/102の対応保留 |
| 横浜 | 保存R8索引を共通経路へ接続 | 主要事業PDFのsource承認・専用scope/binding・個別GET GO、M01対応審査 |
| 神戸 | 保存R8索引を共通経路へ接続 | source正式登録、未確認予算・政策対応の審査、実改版・運用承認 |

自動HTTP・外部通知・公開、既存タスク変更は別GO。Cloudflare Preview branch None／Access制限あり／HooksなしはPM確認を継承し、管理画面再調査はしない。
これは過去Preview全数や本番Access制御の検証ではない。
