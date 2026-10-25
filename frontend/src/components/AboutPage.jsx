import React from 'react';
import {
  ArrowLeft, Compass, Search, Lightbulb, User,
  ExternalLink, Mail, Award, Shield, Milestone, Landmark, Layers, FileCheck, Scale, Coins, BookmarkCheck
} from 'lucide-react';

export default function AboutPage({ onBack, onOpenMethodology }) {
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans pb-20 selection:bg-indigo-500 selection:text-white">
      {/* 画面トップ戻るバー */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-30 px-6 py-3.5">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <button
            onClick={onBack}
            className="inline-flex items-center text-xs font-bold text-slate-600 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50 border border-slate-200 px-3.5 py-2 rounded-xl transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4 mr-1.5" />
            トップページへ戻る
          </button>
          <span className="text-xs font-black text-slate-400">About & Project Overview</span>
        </div>
      </div>

      <main className="max-w-4xl mx-auto px-6 pt-12 space-y-12">
        {/* 1. イントロダクション */}
        <header className="text-center space-y-4 pt-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-bold">
            <Compass className="w-3.5 h-3.5" />
            プロジェクトについて
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight leading-tight">
            「議会のミカタ」について
          </h1>
          <p className="text-sm md:text-base text-slate-600 font-medium max-w-2xl mx-auto leading-relaxed">
            選挙公報原本から議事録、予算書まで。地方自治の「公約・議決・予算・執行」を横断して追跡し、二元代表制の政策プロセスを可視化する独立系シビックテックプロジェクトです。
          </p>
        </header>

        {/* 2. はじまりと動機（BACKGROUND） */}
        <section className="bg-white rounded-3xl border border-slate-200 p-8 md:p-10 shadow-sm space-y-5">
          <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
            <Search className="w-4 h-4" />
            BACKGROUND / はじまりと動機
          </div>
          <h2 className="text-xl md:text-2xl font-black text-slate-900 leading-snug">
            「選挙時の公約は、議会と市政で本当に実行されているのか？」を知りたかった。
          </h2>
          <div className="space-y-4 text-sm md:text-base text-slate-600 leading-relaxed font-normal">
            <p>
              選挙のたびに各候補者や首長は魅力的な公約を掲げます。しかし、当選後にそれらが市議会でどのように質疑され、どの議案に賛否が投じられ、実際にいくらの予算として執行されたのかを一連の流れとして追跡することは極めて困難でした。
            </p>
            <p>
              公開されているのは、数万ページに及ぶ議事録PDF、膨大で難解な主要事業説明書、公報画像データの断片です。これらがバラバラに存在しているため、市民が「言行一致」や「公約の現在地」を確かめるには莫大な時間と専門知識が必要でした。
            </p>
            <div className="p-4 rounded-2xl bg-indigo-50/60 border border-indigo-100 text-indigo-950 text-sm font-medium leading-relaxed">
              「選挙公報の原本から議決、予算執行までを1本のデータパイプラインで結べば、市民誰もが市政を同一基準で検証できるのではないか？」
            </div>
            <p>
              この問題意識から、単なる議事録検索ツールを超え、公約を起点とした政策トレーサビリティ基盤の開発をスタートしました。
            </p>
          </div>
        </section>

        {/* 3. このツールのスタンス（OUR APPROACH & PRIMARY SOURCE） */}
        <section className="bg-white rounded-3xl border border-slate-200 p-8 md:p-10 shadow-sm space-y-6">
          <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
            <Lightbulb className="w-4 h-4" />
            OUR APPROACH / このツールのスタンス
          </div>
          <h2 className="text-xl md:text-2xl font-black text-slate-900 leading-snug">
            正解を決めるためではなく、論点と事実関係を立体的に眺めるために。
          </h2>
          <div className="space-y-4 text-sm md:text-base text-slate-600 leading-relaxed font-normal">
            <p>
              本サイトは、特定の政治的主張を支持・批判したり、「公約違反」といった主観的なラベリングを行うものではありません。
            </p>
            <p>
              首長と議会がそれぞれ持つ権能（予算編成権と議決権）に即し、公式選挙公報、新京都戦略、主要事業説明書、会議録原本という公文書のファクトのみを並列提示しています。事実の解釈と判断は、常に主権者である市民自身に委ねられています。
            </p>
          </div>

          {/* 一次情報への徹底した接続性 */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
            <div className="flex items-center gap-2 text-xs font-black text-slate-900">
              <Landmark className="w-4 h-4 text-indigo-600 shrink-0" />
              <span>一次公文書への接続性とトレーサビリティ</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              AIによる要約やスコアリングは入口を広げるための補助線です。私たちはAIによる要約や評価に誤りが生じる可能性を考慮し、すべての質疑スレッド、公約引用カード、予算定量データに、<strong>選挙管理委員会・京都市会・京都市行財政担当部局の公式原本（PDF／Web）への直リンク</strong>を完備しています。
            </p>
            <p className="text-xs text-slate-600 leading-relaxed">
              疑わしい点があればいつでも原本を開き、直接数字や前後の発言を確認できるよう設計しています。また、万が一資料のリンク切れや不備を発見した場合、資料リンク横の「旗マーク（⚑）」から1タップで運営へ通知できる自動フィードバック機能を備えており、継続的なデータ品質の向上に努めています。
            </p>
          </div>

          {onOpenMethodology && (
            <div className="pt-2">
              <button
                onClick={onOpenMethodology}
                className="text-xs font-bold text-indigo-600 hover:text-indigo-800 underline underline-offset-4 inline-flex items-center cursor-pointer transition-colors"
              >
                公開された統一ルーブリック評価基準および公約・予算データ仕様書を見る →
              </button>
            </div>
          )}
        </section>

        {/* 4. 運営者プロフィール（PROFILE） */}
        <section className="bg-white rounded-3xl border border-slate-200 p-8 md:p-10 shadow-sm space-y-6">
          <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
            <User className="w-4 h-4" />
            PROFILE / 運営者プロフィール
          </div>

          <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 text-xs font-bold text-slate-600 flex items-center gap-2">
            <Shield className="w-4 h-4 text-indigo-500 shrink-0" />
            <span>本プロジェクトは、特定の政党・会派等から独立して運営するシビックテックプロジェクトです。</span>
          </div>

          <div className="space-y-4 pt-1">
            <div>
              <h3 className="text-xl font-black text-slate-900">山本 健人（Yamamoto Kento）</h3>
              <p className="text-xs text-slate-500 font-bold mt-1">
                株式会社KICKs 代表 / 京都大学MBA
              </p>
            </div>

            <p className="text-xs md:text-sm text-slate-600 leading-relaxed">
              一橋大学社会学部を卒業後、アマゾンジャパン合同会社にてオペレーション管理やAI導入などの業務プロセスの改善に従事。
            </p>
            <p className="text-xs md:text-sm text-slate-600 leading-relaxed">
              その後、京都大学経営管理大学院（MBA）にて観光・地域課題を研究。在学中の研究をもとに、観光地のトイレ利用と情報の非対称性を可視化するWebサービス「TOIMAP」を開発・運営（SDGsリーダーシップアワード2025 最優秀賞などを受賞）。
            </p>
            <p className="text-xs md:text-sm text-slate-600 leading-relaxed">
              現在は宿泊施設運営も手掛けながら、データ分析やWeb技術を活用した行政・地域情報可視化の試みに取り組んでいます。（保有資格：行政書士、元米国公認会計士）
            </p>

            <div className="pt-2 flex flex-wrap items-center gap-2">
              <a
                href="https://kanko-innovation.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-indigo-50 text-slate-700 hover:text-indigo-600 border border-slate-200 text-xs font-bold transition-all shadow-2xs"
              >
                <Landmark className="w-3.5 h-3.5 text-indigo-600" />
                <span>運営元：株式会社KICKs コーポレートサイト</span>
                <ExternalLink className="w-3 h-3 ml-0.5 opacity-60" />
              </a>

              <a
                href="https://toimap.jp/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-indigo-50 text-slate-700 hover:text-indigo-600 border border-slate-200 text-xs font-bold transition-all shadow-2xs"
              >
                <Award className="w-3.5 h-3.5 text-amber-500" />
                <span>シビックテック：TOIMAP（トイマップ）公式サイト</span>
                <ExternalLink className="w-3 h-3 ml-0.5 opacity-60" />
              </a>
            </div>
          </div>
        </section>

        {/* 5. 到達点と今後の展開（CURRENT MILESTONE & FUTURE HORIZON） */}
        <section className="bg-white rounded-3xl border border-slate-200 p-8 md:p-10 shadow-sm space-y-6">
          <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
            <Milestone className="w-4 h-4" />
            CURRENT MILESTONE & FUTURE HORIZON / 現在地と今後の展望
          </div>
          <div>
            <h2 className="text-xl md:text-2xl font-black text-slate-900 leading-snug">
              公約・議決・予算執行を一体で洗う「二元代表制の政策プロセスを追う可視化基盤」へ到達。
            </h2>
            <p className="text-xs md:text-sm text-slate-600 mt-2 leading-relaxed font-normal">
              本サービスは単なる議事録の要約からスタートしましたが、今回のアップデートにより、地方自治の二大主役である「議会」と「首長」の言行一致および行政執行プロセスを一体的に追跡する基盤へと進化しました。
            </p>
          </div>

          {/* 二元代表制の両輪ブロック */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            <div className="p-5 rounded-2xl bg-indigo-50/40 border border-indigo-100 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-black text-indigo-950">
                <BookmarkCheck className="w-4 h-4 text-indigo-600" />
                <span>議会（ブレーキ・ハンドル）の言行一致追跡</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                全現職議員を対象に、選挙公報原本に掲載された看板公約と、任期中の実際の議決態度（賛成/反対）および委員会質疑ログを直接照合。議会が持つ監視・政策提言機能のファクトを明らかにします。
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-emerald-50/40 border border-emerald-100 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-black text-emerald-950">
                <Coins className="w-4 h-4 text-emerald-600" />
                <span>首長（アクセル）の予算・条例ライフサイクル検証</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                首長の主要公約を対象に、自治体の総合計画『自治体総合計画（確定版）』への公式位置づけ、主要事業説明書の予算計上額（千円単位）と財源内訳、提出条例の会派別賛否までを定量的に追跡します。
              </p>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-black text-slate-900">
              <FileCheck className="w-4 h-4 text-indigo-600" />
              <span>宿泊税・法定外目的税の使途透明性と他自治体比較</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              年132億円規模へと拡大する「宿泊税」に着目し、集められた目的税が具体的にどの公約やインフラ対策に充当されているのかを主要事業説明書ベースで透明化。他自治体との制度比較データ分析パイプラインの構築も進めています。
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-indigo-50/50 border border-indigo-100 text-xs text-slate-700 leading-relaxed">
            <span className="font-bold text-indigo-950">シビックテックとしてのデータ開放：</span>
            蓄積された政策論点データ、公約マッピング、予算定量スキーマは、研究者や地域報道、市民のオープンデータ活動に貢献できるよう、APIや構造化データとしての外部公開・活用も視野に入れて運用しています。
          </div>

          {/* ご意見・フィードバック導線 */}
          <div className="mt-8 pt-8 border-t border-slate-100 text-center space-y-4">
            <p className="text-xs text-slate-500 max-w-lg mx-auto leading-relaxed">
              データの誤記やシステムの改善点、取り上げてほしい政策テーマなどがございましたら、お気軽にフィードバックフォームよりお寄せください。
            </p>
            <div>
              <a
                href="https://forms.gle/36F9b6xeC8NqzNsU9"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-sm hover:shadow transition-all cursor-pointer"
              >
                <Mail className="w-4 h-4" />
                ご意見・フィードバックはこちら（Googleフォーム）
              </a>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}