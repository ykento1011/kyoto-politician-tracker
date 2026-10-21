import React from 'react';
import { 
  ArrowLeft, Compass, Search, Milestone, Users, 
  Scale, Landmark, CheckCircle2, ArrowRight, ShieldCheck,
  Layers, Table, BarChart3, BookOpen
} from 'lucide-react';

export default function GuidePage({ onBack, onOpenMethodology, onOpenAbout }) {
  return (
    <div className="w-full pb-20 selection:bg-indigo-500 selection:text-white">
      {/* ページ内サブバー */}
      <div className="bg-slate-50/80 border-b border-slate-200/80 px-6 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <button
            onClick={onBack}
            className="inline-flex items-center text-xs font-bold text-slate-600 hover:text-indigo-600 bg-white hover:bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-lg transition-colors cursor-pointer shadow-2xs"
          >
            <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />
            一覧に戻る
          </button>
          <span className="text-[11px] font-black text-slate-400 uppercase tracking-wider">User Guide / できること</span>
        </div>
      </div>

      <main className="max-w-4xl mx-auto px-6 pt-10 space-y-12">
        {/* ヘッダー */}
        <header className="text-center space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-black shadow-2xs">
            <Compass className="w-3.5 h-3.5" />
            議会のミカタ ご利用ガイド
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight leading-tight">
            当サイトでできること
          </h1>
          <p className="text-sm md:text-base text-slate-600 font-medium max-w-2xl mx-auto leading-relaxed">
            12万件超の公式議事録と全議決データを完全構造化。難解な市議会の動きを、市民の視点から直感的に読み解くための5つの機能を紹介します。
          </p>
        </header>

        {/* 理念宣言バナー */}
        <div className="bg-indigo-50/60 rounded-2xl p-5 border border-indigo-100 flex items-start gap-3.5 text-xs text-indigo-950 leading-relaxed">
          <ShieldCheck className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-black text-indigo-900 text-sm">
              本プラットフォームの基本理念：序列（通信簿）ではなく「政策マッチング」
            </div>
            <p className="text-slate-600 text-xs">
              議員に点数をつけて合否を決めることが目的ではありません。ある議員はデータに基づく制度改善を得意とし、別の議員は生活現場の声を代弁することに長けています。市民が自身の関心や価値観に合う議員を見つけ出すための客観的情報基盤を提供しています。
            </p>
          </div>
        </div>

        {/* 5大機能のカード一覧 */}
        <div className="space-y-8">

          {/* ① 政策タイムライン */}
          <section className="bg-white rounded-3xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-4 hover:border-indigo-200 transition-colors">
            <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
              <Milestone className="w-4 h-4" />
              機能 01 / 政策の変遷と現在地を追う
            </div>
            <h2 className="text-xl md:text-2xl font-black text-slate-900 leading-snug">
              重要政策の「これまでの経緯と現在の着地点」がわかる
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed font-normal">
              「市バスの混雑対策」「空き家税」「北陸新幹線延伸」「全員制中学校給食」など、京都市の重要政策32論点を厳選。複数年度にまたがる議場の議論をAIがフェーズごとに整理し、<strong>「行政のスタンスがどう変わり、今どこまで進んでいるか」</strong>を最新順で把握できます。
            </p>
            <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 text-xs text-slate-700 space-y-1.5">
              <div className="font-black text-slate-900 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600" />
                こんな時に便利：
              </div>
              <ul className="list-disc list-inside space-y-1 pl-1 text-slate-600">
                <li>ニュースになっているあの政策が、議会でどう合意されたのか流れを知りたい時</li>
                <li>会期ごとの行政側の公式答弁方針の変化を時系列で確認したい時</li>
              </ul>
            </div>
          </section>

          {/* ② 議員カルテと比較ダッシュボード */}
          <section className="bg-white rounded-3xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-4 hover:border-indigo-200 transition-colors">
            <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
              <Users className="w-4 h-4" />
              機能 02 / 議員の個性と政策注力分野を見る（同区内全員比較対応）
            </div>
            <h2 className="text-xl md:text-2xl font-black text-slate-900 leading-snug">
              発言回数ではなく「提言の密度」と「得意分野」がわかる
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed font-normal">
              単なる文字数や登壇数では測れない議員の活動を、客観的なAIルーブリック評価（具体的対案・データ活用・地域解像度・議論の進展）で分析。個別の詳細カルテに加え、<strong>伏見区（12名）をはじめとする同じ行政区の議員全員など、最大12名までワンクリックで並べて政策スタンスや注力ポートフォリオを横断比較</strong>できます。
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <div className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
                  <Table className="w-3.5 h-3.5 text-indigo-600" />
                  4軸アプローチ比較マトリクス
                </div>
                <p className="text-[11px] text-slate-500 leading-normal">
                  対案提示やデータ活用など、各議員の得意な論戦スタイルを一覧表で比較。関心のあるアプローチ順に並び替えできます。
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <div className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-indigo-600" />
                  8大政策分野ポートフォリオ表
                </div>
                <p className="text-[11px] text-slate-500 leading-normal">
                  「子育て」「環境」「交通」など、統一8大政策分野の中でどのテーマに最も多くの発言機会を割いているかを可視化します。
                </p>
              </div>
            </div>

            <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 text-xs text-slate-700 space-y-1.5">
              <div className="font-black text-slate-900 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600" />
                こんな時に便利：
              </div>
              <ul className="list-disc list-inside space-y-1 pl-1 text-slate-600">
                <li>自分の選挙区の議員たちが、それぞれどのような強みや注力テーマを持っているか俯瞰したい時</li>
                <li>特定の政策分野（教育や財政など）で最も熱心に質疑を行っている議員を探したい時</li>
              </ul>
            </div>
          </section>

          {/* ③ 議案・賛否の記録 */}
          <section className="bg-white rounded-3xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-4 hover:border-indigo-200 transition-colors">
            <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
              <Scale className="w-4 h-4" />
              機能 03 / 議決と会派の態度を検証する
            </div>
            <h2 className="text-xl md:text-2xl font-black text-slate-900 leading-snug">
              どの議案で「誰が賛成し、誰が反対したのか」がわかる
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed font-normal">
              市議会に提出された全議案の賛否結果を網羅。全会一致で可決された議案だけでなく、<strong>「賛否が分かれた激論議案（Contested Bills）」</strong>に絞り込み、なぜ反対意見が出たのか、対立の背景にある争点をAI解説とともに確認できます。各議案をクリックすると、無所属議員を含む全議員の個別の投票態度も一目で確認できます。
            </p>
            <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 text-xs text-slate-700 space-y-1.5">
              <div className="font-black text-slate-900 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600" />
                こんな時に便利：
              </div>
              <ul className="list-disc list-inside space-y-1 pl-1 text-slate-600">
                <li>条例や予算案に対する各政党・会派・無所属議員の実際の投票行動をチェックしたい時</li>
                <li>議場が紛糾した重要案件の対立構図と双方の論理を短時間で把握したい時</li>
              </ul>
            </div>
          </section>

          {/* ④ 全5,100件の横断検索 */}
          <section className="bg-white rounded-3xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-4 hover:border-indigo-200 transition-colors">
            <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
              <Search className="w-4 h-4" />
              機能 04 / 議事録の網羅的な検索と絞り込み
            </div>
            <h2 className="text-xl md:text-2xl font-black text-slate-900 leading-snug">
              5,100件超の質疑から「関心のある話題」を瞬時に探せる
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed font-normal">
              本会議から常任委員会・特別委員会まで、全任期の実質質疑スレッド（5,100件以上）を軽量インデックス化。キーワード検索はもちろん、<strong>政策カテゴリー・行政区・年次・会議体</strong>を掛け合わせて瞬時に絞り込めます。
            </p>
            <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 text-xs text-slate-700 space-y-1.5">
              <div className="font-black text-slate-900 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600" />
                こんな時に便利：
              </div>
              <ul className="list-disc list-inside space-y-1 pl-1 text-slate-600">
                <li>「保育園」「無電柱化」「空き家対策」など、特定の政策ワードがいつどの委員会で討議されたか調べたい時</li>
                <li>自分の住む区に関する議論だけをピックアップしたい時</li>
              </ul>
            </div>
          </section>

          {/* ⑤ 公式原本直リンク */}
          <section className="bg-white rounded-3xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-4 hover:border-indigo-200 transition-colors">
            <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
              <Landmark className="w-4 h-4" />
              機能 05 / 一次情報への徹底した接続性
            </div>
            <h2 className="text-xl md:text-2xl font-black text-slate-900 leading-snug">
              AI要約からワンクリックで「京都市会の公式原本」を検証できる
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed font-normal">
              AIの要約やスコアはあくまで議論を広く見渡すための補助線です。当サイトでは、すべての質疑スレッドやタイムラインに<strong>京都市会公式サイト（公的サーバー）の会議録原本への直リンク</strong>を完備。気になる点があればいつでも前後の生の発言を直接確認（一次情報の裏取り）できます。
            </p>
            <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 text-xs text-slate-700 space-y-1.5">
              <div className="font-black text-slate-900 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                信頼性の担保：
              </div>
              <p className="text-slate-600">
                AIによる解釈のブレ（ハルシネーション）を疑う余地を残さないため、すべてのデータが公的な一次情報に直接紐づいています。
              </p>
            </div>
          </section>

        </div>

        {/* 関連リンク案内 */}
        <section className="pt-6 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <button
            onClick={onOpenAbout}
            className="p-5 bg-white rounded-2xl border border-slate-200 hover:border-indigo-200 text-left space-y-1.5 transition-all cursor-pointer group shadow-2xs"
          >
            <span className="text-[11px] font-black text-slate-400 uppercase tracking-wider">PROJECT BACKGROUND</span>
            <div className="text-sm font-black text-slate-900 group-hover:text-indigo-600 transition-colors flex items-center justify-between">
              <span>開発の背景・運営者について</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </div>
            <p className="text-xs text-slate-500">なぜこのプロジェクトを立ち上げたのか、理念と動機を紹介します。</p>
          </button>

          <button
            onClick={onOpenMethodology}
            className="p-5 bg-white rounded-2xl border border-slate-200 hover:border-indigo-200 text-left space-y-1.5 transition-all cursor-pointer group shadow-2xs"
          >
            <span className="text-[11px] font-black text-slate-400 uppercase tracking-wider">EVALUATION RUBRIC</span>
            <div className="text-sm font-black text-slate-900 group-hover:text-indigo-600 transition-colors flex items-center justify-between">
              <span>AI採点基準・プロンプト仕様書</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </div>
            <p className="text-xs text-slate-500">中立なAIルーブリック評価のプロンプトと採点基準を完全公開しています。</p>
          </button>
        </section>

        {/* トップへ戻る */}
        <div className="pt-4 text-center">
          <button
            onClick={onBack}
            className="inline-flex items-center px-6 py-3 rounded-xl bg-slate-900 text-white font-bold text-xs hover:bg-slate-800 transition-all shadow-md cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            トップページへ戻って使ってみる
          </button>
        </div>
      </main>
    </div>
  );
}