# 横浜R8主要事業PDF専用ガード（通信無効）

固定PDFは `https://www.city.yokohama.lg.jp/city-info/zaisei/jokyo/yosan/r8/r8yosan.files/R8yosan-shuyou.pdf` のみ。
profile `yokohama_r8_major_pdf` だけに HTML 0 / PDF 1 / 1GET / 2MiB / 親worker壁時計10秒を許容する。
HTTPS/TLS、redirect/retry/リンク追跡0。設定のenabled/network_enabledはともにfalse。
一般のHTML1+PDF1/4MiB、京都P-04/P-14、PR #99、既存P1・運用設定は変更しない。

## 保存索引の必須照合

- URL: `https://www.city.yokohama.lg.jp/city-info/zaisei/jokyo/yosan/r8/r8yosan.html`
- SHA256: `872f5c8da45129bd6a3296269942880e20eeac8de6a163bb556e2bde294ae98b`
- `#tmp_contents` は一意。hrefありanchorの1始まり17番目。
- href: `r8yosan.files/R8yosan-shuyou.pdf`
- 資料名: `資料編（主要事業一覧）（PDF：1,014KB）`
- 直前の見出し: `令和８年度予算（令和８年１月26日）`
- 対象href重複、base/refresh、構造不明、原本欠落・SHA破損、CAS上の別都市/年度/文書ID/MIME不一致、異版・複数版はHOLD。

索引は読み取り専用であり取得元リストに入れない。新しい索引への自動追随や承認継承をしない。
固定PDFの文書IDは `yokohama-doc-a19d0abfd5a6d4ca51da9599`。年度2026、other_official/application/pdf。
YOKOHAMA-M01の探索候補であり、政策対応・予算額・公約達成は未確認。

## 専用bindingとPIN

`validate_storage(..., code_root=actual_p1_root)` を親とworkerの両方から呼ぶ。
無効scopeは `yokohama_r8_major_pdf_binding.json` のみ読む。
将来の有効scopeは `yokohama_r8_major_pdf_active_binding.json` のみ読む。
片方だけ有効、不正型、欠落、既存city_binding.jsonや京都bindingへのfallbackはHOLD。
今回、実私有領域にはどちらも作成しない。

bindingはscope SHA、都市、解決済みCAS/state/P1ルート、CAS/stateのdevice/inode、索引SHA、P1 manifest SHA、実行city_scope.py/acquire.pyの実バイトSHAへ束縛する。
storageはbinding実バイトSHA、同じP1ルート、p1_filesの18ファイルmanifestを持つ。
承認済み候補P1 manifest SHAは `df02598305964e5d3bea333301ecccb93e26702db6f0a43a5fe6f8c180dd57d2`。
同値の別P1を推測で受理せず、実ファイル全PINと同一実体を照合する。
private_root/CAS/state/output/binding/P1ルートのowner-only ACLと実行主体を既存検査で確認。symlink等での実体切替、CAS/state/code重なり、都市混入はHOLD。
新しいACL付与・緩和は行わない。

scope設定は固定契約と厳密比較し、余分な値やTrue/1の型差も拒否する。
`--refresh-existing` は専用profileで拒否。保存済み原本は再利用し、PDFヘッダー・文書ID・都市・URL・年度・媒体を読戻しで確認する。
取得失敗・応答不明は既存の永続URL予約を保持して停止。予約の削除・自動再GETはしない。

## 合成試験と未実施事項

新規14試験と既存京都15、一般都市10を通信0で確認。
正常な専用bindingの読取りで全ファイル不変、fallback拒否、改変・欠落・URL偽装・位置変更・異年度・PIN/ACL/CAS不一致を検証。
親入口は合成子プロセスだけを使用し、1PDF・10秒の引渡し、読戻し、失敗/タイムアウト/異都市versionの停止、予約重複拒否を確認。
テストのindex/P1 SHAは合成データ用に限定置換し、本番定数も別の試験で固定値一致を検査する。
テスト中のbinding・予約・原本はTemporaryDirectory内の合成物のみ。ソケット接続は拒否している。

未実施: 実原本へ新ガードを適用する私有結合、実workerのPIN/ACL検査時間、実PDF取得、正式source登録、active binding作成、取得予約、政策対応審査。
実P1/保存索引/owner-only環境への接続は別ゲート。PIN/ACL検査もworkerの10秒内であり、実環境で完了できなければHOLD（時間制限は緩めない）。
scope/bindingは人間のsource登録承認や実GETの承認receiptを代替しない。
Ready化・マージ・本番・公式GETはPM/代表の別GOが必要。
