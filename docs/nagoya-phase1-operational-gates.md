# 名古屋SSP Phase 1：独立した準備工程

main起点。PR #101/#98/#71を変更・importしない。実通信・保存先作成・ACL変更・
実予約・source承認・Ready/main統合は今回の成果に含まれない。

## A. source登録審査票

対象は名古屋tenant207のセッションHTML GETと会期索引POST。
既存コードのURLと保存済み市公式HTMLのフッターは参照先の根拠であり、取得許諾ではない。

|用途|保存資料による根拠|判定・必要な審査|
|---|---|---|
|公式閲覧|SSP名古屋入口のコード上の参照|SSP利用条件の適用本文は未確認|
|機械取得|固定2リクエストのコード上の契約|公式な機械取得条件は未確認、PM審査待ち|
|非公開保存|既存原本保管の運用実績|SSP原本の保存条件・期間・利用主体は未確認|
|転載|保存済み市公式ページの著作権案内リンク|条件本文未確認。Phase1取得許可と別審査|
|外部AI送信|根拠なし|NO-GO。取得許可に含めない|

不足文書の別取得申請候補：
`https://www.city.nagoya.jp/about/1017985.html`（著作権・リンク・免責事項）。
保存済み公式ページの相対hrefを解決したURL。最大1GET・2MiB・10秒・TLS必須・
転送/再試行0、別の非公開証跡領域への保存を提案する。今回取得しない。
当該ページだけでSSP配信先への適用を断定しない。SSP固有の条件文書URLは未確定であり、
推測URLを追加しない。保存済み資料で確定できなければ公式担当への照会を代表へ提案する。

source登録票には発行主体（名古屋市会、適用確認待ち）、配信ホスト、固定URL/payload、
用途（索引の非公開照合のみ）、保存期間、根拠本文/位置/SHA、条件適用範囲、審査者、
承認者、承認日時/期限を記録する。PMが技術/用途を審査し、代表が管理責任・利用判断を承認。
未確認欄を空のまま承認済みへ昇格させない。

## B. owner-only配置・権限案（未作成）

読み取り確認した既存親領域は継承有効。所有者のほか、サンドボックスグループに読取・実行、
SYSTEMとAdministratorsに全権限がある。そのまま子を作ってもowner-onlyとは認定できない。

- 既存領域を変更せず、Git/同期/公開領域外の名古屋SSP専用rootを別承認で作成する。
- `cas/`：新規ハッシュ原本と読み戻し。`receipts/`：確定証跡。`state/`：last-good参照。
  `attempts/`：一回限りの予約・結果不明記録。正常版と失敗runを分離する。
- 実行専用の非管理者主体と、承認を管理する主体を分離する。同じ所有者が全権限を持つ
  ディレクトリ間の移動だけでは自己改変防止にならない。
- 継承を遮断した専用DACLでサンドボックス/Users/共有グループの権限を除く。
  OSのSYSTEMと復旧管理者の例外をPMが明記する。この場合のowner-onlyは
  「指定実行主体と承認済みOS管理例外のみ」であり、管理者からの不可視を意味しない。
- 実行主体にChangePermissions/TakeOwnershipを与えない。原本・receipt・予約の確定後の
  改変/削除を防ぐには、管理者所有の書込サービス等で確定操作を分離する。
  同じ実行主体がroot所有者で自由に削除できる構成を不可逆予約とは認定しない。
- source承認・PIN・公開検証鍵は承認管理境界で管理し実行主体はread-only。
  署名秘密鍵は実行主体の読取も不可の署名境界へ。今回は生成・配置しない。

実作成GOではroot絶対パス、主体SID、管理者例外、所有者、継承遮断、ディレクトリ毎の
実効アクセス、署名管理者、復旧担当を指定する。DACL表示だけでなくグループ所属・
共有/バックアップ/同期経路・reparse・実行トークンからの拒否も確認後に受け入れる。

## C. 通信無効transport

`nagoya_phase1_transport.py`の`StreamTransport`は固定request生成、TLS context、
ストリームread/write上限、HTTP異常、Cookie制限を実装する。
実HTTPS接続生成コードは未成立authority gateの後にあり到達不能。
`acquire_live()`は常にHOLD。`enabled=false`・`network_enabled=false`は維持する。
単なるフラグ変更で有効化できない。正規署名/ACL/P1検証は未実装であり、合成値を信用しない。

|契約|実装・検証範囲|
|---|---|
|通信|GET `/tenant/nagoya/SpTop.html` → POST `/dnp/search/councils/index`|
|body|`tenant_id=207&power_user=false`固定|
|header|名古屋SpMinuteBrowse.html Referer、XMLHttpRequest、identity encoding固定|
|容量|各2MiB、合計4MiB。readは残量+1まで、超過分をsinkへ書かない|
|期限|fake応答子25秒、stage全体を外部子60秒で監督。間隔1.2秒以上|
|Cookie|空開始、同一Phase内メモリのみ。属性未知・別domainはHOLD。Phase2引継ぎなし|
|状態|子起動前の合成予約、再実行拒否、正常HEADのatomic更新、旧CAS読戻し|

一時受信bodyは各2MiB以下のメモリsink。応答子出力は起動前入力制限と固定出力構造で
上限を拘束しメモリPIPEで受け取る。Cookieをdisk spoolへ書かない。
Cookieを含まないphase結果のみ上限付きspoolを使う。
失敗runにも完成済み原本が残ることはあるが正常HEADは旧版を保持する。
準備receiptはcommit成功を主張しない。成功認定はHEADのrunとCAS一致が必要。
強制終了時に残るLOCK/runは不明として保留し、同runを再実行しない。
60秒監督の終了後に残り得る応答子にはstateパスを渡さず、現行fake分岐にはstate書込・
実通信のコード経路がない。OSによるネットワーク/書込能力の分離は未実装。
OS停止/プロセス生成遅延/管理者操作への保証ではない。

試験はfake connectionと隔離temporary rootのみ。実原本/人物データを使用しない。
実TLSハンドシェイク、名古屋Cookie仕様、権利、実P1署名、実ACL、実予約の受入は未実証。
live transportを有効化する前に、A/B受入・正規認可検証・プロセスツリー停止・
改変不能監査と実予約サービスの接続を別途審査する。
Phase2、676/2認証、Gemini、公開、定期登録はこのPRの範囲外。
