import React from 'react';
import { 
  ArrowLeft, ShieldCheck, Database, Sliders, Scale, 
  AlertCircle, ExternalLink, Sparkles, CheckCircle2, FileText, Calendar, Landmark, Layers, BookmarkCheck, Coins, BookCheck, Flame
} from 'lucide-react';

export default function Methodology({ onBack }) {
  return (
    <div className="min-h-screen bg-[#FDFDFD] text-slate-800 font-sans selection:bg-indigo-500 selection:text-white">
      {/* 画面トップバー */}
      <div className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-6 h-14 flex items-center justify-between">
          <button
            onClick={onBack}
            className="inline-flex items-center text-xs font-bold text-slate-600 hover:text-indigo-600 transition-colors py-1.5 px-3 rounded-lg border border-slate-200 bg-white shadow-2xs hover:bg-slate-50 cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />
            トップページに戻る
          </button>
          <span className="text-[11px] font-mono text-slate-400 font-semibold tracking-wider uppercase">
            Platform Methodology v2.0
          </span>
        </div>
      </div>

      <main className="max-w-4xl mx-auto py-12 px-6 md:px-8 space-y-16">
        
        {/* ① ページヘッダー */}
        <header className="border-b border-slate-200 pb-10 space-y-3">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-black tracking-wide">
            <FileText className="w-3.5 h-3.5" /> 公開技術白書・政策監査仕様書
          </div>
          <h1 className="text-3xl md:text-4xl font-serif font-bold text-slate-900 tracking-tight leading-tight">
            政策監査ロジック・公約照合データ仕様書
          </h1>
          <p className="text-slate-500 text-sm md:text-base leading-relaxed pt-2">
            本プラットフォームが採用するデータ収集・前処理アルゴリズム、選挙公報原本および主要事業説明書との照合パイプライン、評価ルーブリック、およびAI採点における中立性・再現性の技術仕様を完全公開します。
          </p>
        </header>

        {/* ② セクション1：プラットフォームの設計思想 */}
        <section className="space-y-4">
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2 border-l-4 border-indigo-600 pl-3">
            <span>1. なぜ「格付け（通信簿）」をしないのか</span>
          </h2>
          <div className="text-sm leading-relaxed text-slate-700 space-y-3 pl-4">
            <p>
              本プラットフォームの目的は、議員や首長に序列や合否をつける「通信簿」を作ることではありません。従来型の議会評価で頻繁に用いられてきた「発言回数」「登壇文字数」「提出議案件数」といった形式的な数値は、実際の政策論戦の質を反映せず、時としてパフォーマンス的な発言を助長する懸念がありました。
            </p>
            <p>
              私たちは、発言の「量」ではなく政策対話の<strong>「密度」と「個性」</strong>に着目しています。ある議員はデータに基づく手堅い論証を得意とし、別の議員は現場当事者の切実な声を直接議場へ届けることに長けています。市民が自身の関心や価値観に合う議員を見つけ出すための「マッチング情報」を提供することこそが本ツールの設計思想です。
            </p>
          </div>
        </section>

        {/* ③ セクション2：分析対象データと公約・予算トレーサビリティ仕様 */}
        <section className="space-y-4">
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2 border-l-4 border-indigo-600 pl-3">
            <span>2. 分析対象データと「公約・予算・議決」の照合仕様</span>
          </h2>
          <div className="text-sm leading-relaxed text-slate-700 space-y-4 pl-4">
            <p>
              本プラットフォームは、議事録のテキスト分析にとどまらず、選挙管理委員会の選挙公報、自治体の総合計画、および行財政担当部局の予算公文書を統合した多層構造で構築されています。
            </p>

            {/* 採用データソース＆ライセンス一覧 */}
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 space-y-2 text-xs">
              <div className="font-bold text-slate-800 flex items-center gap-1.5">
                <Database className="w-4 h-4 text-indigo-600" />
                採用データソースとクレジット一覧
              </div>
              <ul className="list-disc list-inside space-y-1.5 text-slate-600 pl-1 leading-normal">
                <li>
                  <strong className="text-slate-700">市会議決・会議録:</strong> 対象議会の公式会議録および議決結果一覧（本会議・常任委員会・特別委員会）
                </li>
                <li>
                  <strong className="text-slate-700">市議選公約原本:</strong> 各自治体選挙管理委員会発行の「議員選挙 選挙公報原本（PDF）」
                </li>
                <li>
                  <strong className="text-slate-700">市長選公約原本:</strong> 各自治体選挙管理委員会発行の「首長選挙 選挙公報原本（PDF）」
                </li>
                <li>
                  <strong className="text-slate-700">市公式総合計画:</strong> 対象自治体策定の最上位計画（総合基本計画・政策集などの公式原本）
                </li>
                <li>
                  <strong className="text-slate-700">予算・事業公文書:</strong> 各自治体の行財政担当部局が発行する『主要事業説明書』『予算案概要』等の公式公文書各年度資料
                </li>
                <li>
                  <strong className="text-slate-700">政治議論データ基盤:</strong>{' '}
                  <a 
                    href="https://sage-base.com/" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="text-indigo-600 font-bold hover:underline inline-flex items-center gap-0.5"
                  >
                    Sagebase <ExternalLink className="w-3 h-3 opacity-60" />
                  </a>
                  （発言の構造化・人物同定データを利用 / ライセンス:{' '}
                  <a 
                    href="https://creativecommons.org/licenses/by/4.0/deed.ja" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="text-indigo-600 hover:underline"
                  >
                    CC BY 4.0
                  </a>
                  ）
                </li>
              </ul>
            </div>

            {/* 議員看板公約トラッカーのデータ仕様 */}
            <div className="bg-indigo-50/50 p-4.5 rounded-2xl border border-indigo-100 space-y-2.5">
              <h3 className="font-bold text-indigo-950 text-xs flex items-center gap-1.5">
                <BookmarkCheck className="w-4 h-4 text-indigo-600" /> 議員看板公約トラッカーのデータ仕様と照合ロジック
              </h3>
              <p className="text-xs text-indigo-950/80 leading-relaxed">
                全選挙区の現任期議員を対象に、選挙公報原本からスローガン的記述を除いた具体的看板公約（1人あたり3件）を抽出。公報紙面の原文をそのまま引用・保存しています。
              </p>
              <p className="text-xs text-indigo-950/80 leading-relaxed">
                公約の対象政策キーワードと、議会公式の議案採決ログ（<code>votes_summary.json</code>）および質疑発言ログを機械突合。包括予算で執行される政策については無関係な単独条例案の誤爆を排除し、議場で市側に何を迫ったかの質疑スレッドと会議録原本を1対1で直結させています。「公約違反」等の判定はシステム側で行わず、公報原本と会議録の並列提示に徹しています。
              </p>
            </div>

            {/* 市長政策ライフサイクル×予算定量のデータ仕様 */}
            <div className="bg-emerald-50/50 p-4.5 rounded-2xl border border-emerald-200/80 space-y-2.5">
              <h3 className="font-bold text-emerald-950 text-xs flex items-center gap-1.5">
                <Coins className="w-4 h-4 text-emerald-700" /> 市長政策トラッカーのデータ仕様と定量の完全性
              </h3>
              <p className="text-xs text-emerald-950/90 leading-relaxed">
                現職首長の主要な看板公約を対象に、「①公約表明 ➔ ②市公式確定計画（自治体の公式確定計画） ➔ ③予算措置 ➔ ④条例提出・可決 ➔ ⑤成立・執行」の5段階を追跡しています。
              </p>
              <p className="text-xs text-emerald-950/90 leading-relaxed">
                予算データに関しては、AIの推論を経由せず、自治体発行の『主要事業説明書』等のPDF原本から直接抽出した「千円単位の計上額」および「特定財源内訳（宿泊税充当額、国費、市債、一般財源）」を紐付けています。各公約カードから主要事業説明書PDF原本への直接リンクを完備し、原資料を確認できる状態で掲載し検証可能性を担保しています。
              </p>
            </div>

            {/* 原本トレーサビリティ仕様 */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
              <h3 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                <Landmark className="w-4 h-4 text-slate-700" /> 公的原本へのトレーサビリティ（監査可能性の技術仕様）
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                全5,100件以上の質疑スレッドに対して、各議会公式サーバー上の原本ページ（MinuteView）へ直接遷移する固有URL（council_id / schedule_id / view_years）を結合。利用者はボタン1つで公的機関の一次情報に直接アクセスし、文脈の確認を行えます。
              </p>
              <div className="mt-3 p-3 bg-white rounded-lg border border-slate-200">
                <p className="text-[11px] font-bold text-slate-700 mb-1 flex items-center gap-1.5"><AlertCircle className="w-3.5 h-3.5 text-rose-500" /> データ健全性を担保するユーザー参加型監査システム</p>
                <p className="text-[11px] text-slate-600 leading-normal">
                  データ・リンクの不備報告パイプラインとして、Cloudflare Pages Functions および Discord Webhooks を統合したフィードバックシステムを実装しています。利用者が資料横の旗アイコン（⚑）をクリックすると、対象の「自治体・発言ID・現在URL」等のメタデータがバックエンドで自動収集され、運営側へ即時通知・修正される自律的なデータクレンジング基盤を構築しています。
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <h3 className="font-bold text-slate-900 text-xs flex items-center gap-1.5 mb-1.5">
                  <Database className="w-4 h-4 text-slate-600" /> ノイズ発言の機械的排除
                </h3>
                <p className="text-xs text-slate-600 leading-normal">
                  議長による議事進行、開会挨拶、定型辞、点呼、単なる賛否の宣告など、政策的な議論を含まない発言ブロックは、前処理パイプラインのルールベース・アルゴリズムにより機械的に除外しています。
                </p>
              </div>

              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <h3 className="font-bold text-slate-900 text-xs flex items-center gap-1.5 mb-1.5">
                  <Sliders className="w-4 h-4 text-slate-600" /> 対話単位のスレッド構造化
                </h3>
                <p className="text-xs text-slate-600 leading-normal">
                  議員の発言単体のみを切り取って評価することはしません。「議員の質問 ➔ 行政側の答弁 ➔ 議員の再質問」という一連の往復を1つの「質疑スレッド」として結合し、文脈全体の整合性と進展度を評価します。
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ④ セクション3：4軸の統一ルーブリック（評価基準表） */}
        <section className="space-y-5">
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2 border-l-4 border-indigo-600 pl-3">
            <span>3. 政策対話の「密度」を測る4軸の統一ルーブリック</span>
          </h2>
          {/* 💡 先行研究を参照して設計した点と、評価の機械的実施を明記 */}
          <p className="text-sm text-slate-600 pl-4 leading-relaxed">
            各質疑スレッドは、党派性や政策の賛否・イデオロギーから独立し、政治・議会研究の先行研究を参照して設計された以下の4つの統一評価指標（各0〜5点）によって機械的に評価されます。
          </p>

          <div className="overflow-x-auto border border-slate-200 rounded-xl shadow-2xs">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-slate-100 text-slate-800 font-bold border-b border-slate-200">
                  <th className="p-3.5 w-36">評価軸</th>
                  <th className="p-3.5 w-44">0点（基礎水準）</th>
                  <th className="p-3.5 w-52">3点（標準水準）</th>
                  <th className="p-3.5">5点（高度水準）</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white text-slate-700">
                <tr>
                  <td className="p-3.5 font-bold text-slate-900 bg-slate-50/50">
                    根拠・データ<br/>
                    <span className="text-[10px] text-slate-400 font-mono">Evidence</span>
                  </td>
                  <td className="p-3.5">主観的な感想、感情的な主張、伝聞情報のみで構成されている。</td>
                  <td className="p-3.5">予算額や決算実績、過去の経緯、他都市の類似事例などのファクトを引用している。</td>
                  <td className="p-3.5 font-medium">条例条文、公的統計データ、公式答弁ログ、監査結果等の一次資料を明確に提示している。</td>
                </tr>
                <tr>
                  <td className="p-3.5 font-bold text-slate-900 bg-slate-50/50">
                    対案・是正策<br/>
                    <span className="text-[10px] text-slate-400 font-mono">Solution</span>
                  </td>
                  <td className="p-3.5">単なる現状批判や、実現可能性を欠く抽象的な要望にとどまっている。</td>
                  <td className="p-3.5">具体的かつ実務上検討可能な改善策や、制度運用の代替選択肢を提示している。</td>
                  <td className="p-3.5 font-medium">
                    財源措置や制度設計を含む対案の提示。<br/>
                    <span className="text-indigo-700 font-bold">※または行政の重大な不備・瑕疵を論理的に突き、是正や見直しを公式に約束させた追及型質疑も最高評価とする。</span>
                  </td>
                </tr>
                <tr>
                  <td className="p-3.5 font-bold text-slate-900 bg-slate-50/50">
                    地域解像度<br/>
                    <span className="text-[10px] text-slate-400 font-mono">Local Focus</span>
                  </td>
                  <td className="p-3.5">当該自治体の市政に直接関係のない国政レベルの抽象論や一般論に終始している。</td>
                  <td className="p-3.5">特定の行政区、担当部局・事業名、当該自治体独自の制度運用上の課題に言及している。</td>
                  <td className="p-3.5 font-medium">町名、学区、商店街、公共施設、交差点、路線名など、生活現場の固有名詞や当事者の実情に深く踏み込んでいる。</td>
                </tr>
                <tr>
                  <td className="p-3.5 font-bold text-slate-900 bg-slate-50/50">
                    議論の進展<br/>
                    <span className="text-[10px] text-slate-400 font-mono">Constructive</span>
                  </td>
                  <td className="p-3.5">用意された原稿の棒読みに終始し、行政側の答弁内容を無視して持論を展開している。</td>
                  <td className="p-3.5">行政側の答弁を踏まえ、論点を絞り込んで再質問・確認を行っている。</td>
                  <td className="p-3.5 font-medium">答弁の論理破綻や曖昧な回答を突き、実態調査や再検討、方針転換の言質を引き出すなど、議論を一段前進させている。</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* 💡 学術的裏付けの一次資料（参考文献）リンク */}
          <div className="pt-4 border-t border-slate-200 space-y-2">
            <div className="flex items-center gap-1.5 font-bold text-indigo-950 text-[11px]">
              <Landmark className="w-3.5 h-3.5 text-indigo-600" />
              <span>主要な依拠論文・学術リファレンス（一次資料検証）</span>
            </div>
            <p className="text-[10px] text-slate-500">
              本ルーブリックの理論的基盤となった主要な先行研究です。リンク先から実際の学術論文や事典の一次情報をご確認いただけます。
            </p>
            <ul className="space-y-1.5 text-[10px] text-slate-600 pl-1">
              <li>
                <a 
                  href="https://doi.org/10.1057/palgrave.cep.6110002" 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="hover:text-indigo-600 hover:underline inline-flex items-center gap-1 transition-colors"
                >
                  Steenbergen, M. R., et al. (2003). "Measuring Political Deliberation: A Discourse Quality Index" (DQIの提唱論文) <ExternalLink className="w-2.5 h-2.5 opacity-60 shrink-0" />
                </a>
              </li>
              <li>
                <a 
                  href="https://plato.stanford.edu/entries/political-representation/" 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="hover:text-indigo-600 hover:underline inline-flex items-center gap-1 transition-colors"
                >
                  Stanford Encyclopedia of Philosophy: "Political Representation" (H.F. Pitkin「実質的代表」理論の解説) <ExternalLink className="w-2.5 h-2.5 opacity-60 shrink-0" />
                </a>
              </li>
              <li>
                <a 
                  href="https://ndlsearch.ndl.go.jp/search?cs=bib&display=panel&from=0&size=20&keyword=%E8%87%AA%E6%B2%BB%E4%BD%93%E8%AD%B0%E5%93%A1%E3%81%8C%E7%9F%A5%E3%81%A3%E3%81%A6%E3%81%8A%E3%81%8F%E3%81%B9%E3%81%8D%E6%94%BF%E7%AD%96%E8%B2%A1%E5%8B%99%E3%81%AE%E5%9F%BA%E7%A4%8E%E7%9F%A5%E8%AD%98&f-ht=ndl&f-ht=library" 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="hover:text-indigo-600 hover:underline inline-flex items-center gap-1 transition-colors"
                >
                  国立国会図書館サーチ: 江藤俊昭 編著 (2019). 『自治体議員が知っておくべき政策財務の基礎知識』（二元代表制・議会の政策立案機能 / 第一法規） <ExternalLink className="w-2.5 h-2.5 opacity-60 shrink-0" />
                </a>
              </li>
            </ul>
          </div>
        </section>

        {/* ⑤ セクション4：政策カテゴリーの統一分類アルゴリズム */}
        <section className="space-y-4">
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2 border-l-4 border-indigo-600 pl-3">
            <span>4. 8大政策分野への統一マッピングアルゴリズム</span>
          </h2>
          <div className="text-sm leading-relaxed text-slate-700 space-y-3 pl-4">
            <p>
              市議会の所管構造に適合した<strong>「統一8大政策分野」</strong>への再マッピングパイプラインを採用しています。
            </p>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2 text-xs">
              <div className="font-bold text-slate-800 flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-indigo-600" />
                採用する8大政策分野と分類ルール
              </div>
              <p className="text-slate-600 leading-relaxed">
                常任委員会（産業交通水道、総務消防等）の所管構造および専門キーワード辞書（地域特有の産業・税制・交通インフラ・財政行革・景観保護等）を組み合わせた階層的ルールベース・アルゴリズムにより、再現性の高い分類を行っています。
              </p>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {['子育て・教育', '都市再生・交通インフラ', '産業・観光・地域経済', '福祉・医療・健康', '財政・行革', 'くらし・環境・エネルギー', '防災・減災・治安', '文化・景観・歴史'].map(cat => (
                  <span key={cat} className="px-2 py-0.5 bg-white border border-slate-200 rounded font-bold text-slate-700">
                    {cat}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ⑥ セクション5：AIの再現性と公平性の担保 */}
        <section className="space-y-4">
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2 border-l-4 border-indigo-600 pl-3">
            <span>5. アルゴリズムの中立性と技術仕様</span>
          </h2>
          <div className="text-sm leading-relaxed text-slate-700 space-y-3 pl-4">
            <p>
              「AIの採点が恣意的ではないか」という懸念を払拭するため、以下の厳格なシステム制約を設けています。
            </p>
            <ul className="list-disc list-inside space-y-2 text-xs md:text-sm pl-1">
              <li>
                <strong>決定論的出力の固定:</strong> 評価モデル（Google Gemini）の生成パラメータ <code>temperature</code> を <strong>0.0</strong> に設定し、同一の質疑スレッドを入力した際には常に同一の採点結果が出力される決定論的挙動（再現性）を担保しています。
              </li>
              <li>
                <strong>完全単一プロンプトの適用:</strong> 議員の所属会派、当選回数、年齢、性別などの属性情報は評価用プロンプトの評価要素から除外され、全議員・全スレッドに対して単一の同一プロンプトのみが機械的に適用されています。
              </li>
              <li>
                <strong>パイプラインの自動化と公開:</strong> データスクレイピングから評価、原本URL結合に至る全ソースコードおよびプロンプト文面はオープンソースとして公開しています。
              </li>
            </ul>

            <div className="pt-2">
              <a
                href="https://github.com/ykento1011/kyoto-politician-tracker"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 px-3.5 py-2 rounded-lg border border-slate-300 transition-colors"
              >
                GitHubリポジトリでプロンプト・ソースコードを確認 <ExternalLink className="w-3.5 h-3.5 ml-1.5 opacity-60" />
              </a>
            </div>
          </div>
        </section>

        {/* ⑦ セクション6：政策マップ・議案一覧における「激論（賛否対立議案）」の定義 */}
        <section className="space-y-4">
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2 border-l-4 border-indigo-600 pl-3">
            <span>6. 政策マップにおける「激論（賛否対立議案）」の定義</span>
          </h2>
          <div className="text-sm leading-relaxed text-slate-700 space-y-3 pl-4">
            <p>
              マクロ論戦マップ等で表示される「激論議案 ○件」という数値は、議論の感情的な激しさや主観的な紛糾度を表すものではありません。
            </p>
            <p>
              本議会に提出された全議案のうち、全会一致で可決されたものを除き、<strong>会派・議員間で「賛成」と「反対」に投票態度が分かれた議案の総数</strong>を機械的に集計した客観的ファクトです。対立の背景にある政策的争点や双方の論理を比較・検証するための重要指標として抽出しています。
            </p>
          </div>
        </section>

        {/* ⑧ セクション7：評価の限界と免責事項 */}
        <section className="space-y-4 pb-8 border-b border-slate-200">
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2 border-l-4 border-indigo-600 pl-3">
            <span>7. 本データが示さないもの（免責事項）</span>
          </h2>
          <div className="bg-amber-50/70 border border-amber-200/90 rounded-2xl p-5 text-xs md:text-sm leading-relaxed text-amber-950 space-y-2.5">
            <div className="flex items-center gap-2 font-bold text-amber-900">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
              議場外の政治活動・議員実績に関する測定範囲
            </div>
            <p>
              本プラットフォームが可視化しているのは、あくまで「対象議会の議場および委員会室内で記録された公式な対話ログ」に限定されています。
            </p>
            <p className="text-amber-900/90">
              市民からの日常的な相談解決、地域の道路補修や街灯設置等の陳情対応、各種政策勉強会の主催、他自治体や省庁との調整交渉など、<strong>議場外における重要な議員活動や実績は本ツールの測定範囲外</strong>です。したがって、本ツールのスコア単体をもって議員の総合的な能力や資質を決定づけるものではありません。
            </p>
          </div>
        </section>

        {/* フッター戻るボタン */}
        <div className="text-center pt-4">
          <button
            onClick={onBack}
            className="inline-flex items-center px-6 py-3 rounded-xl bg-slate-900 text-white font-bold text-xs hover:bg-slate-800 transition-all shadow-md cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            トップページに戻って分析を見る
          </button>
        </div>

      </main>
    </div>
  );
}