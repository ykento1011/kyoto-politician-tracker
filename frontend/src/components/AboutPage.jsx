import React from 'react';
import { 
  ArrowLeft, Compass, Search, Lightbulb, User, 
  ExternalLink, Mail, Award, Shield, Milestone, Sparkles 
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
            膨大な議事録のデータを、もう少し身近に、わかりやすく読み解くための個人的な実験プロジェクトです。
          </p>
        </header>

        {/* 2. はじまりと動機（BACKGROUND） */}
        <section className="bg-white rounded-3xl border border-slate-200 p-8 md:p-10 shadow-sm space-y-5">
          <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
            <Search className="w-4 h-4" />
            BACKGROUND / はじまりと動機
          </div>
          <h2 className="text-xl md:text-2xl font-black text-slate-900 leading-snug">
            「議会で実際に何が話されているのか」を知りたかった。
          </h2>
          <div className="space-y-4 text-sm md:text-base text-slate-600 leading-relaxed font-normal">
            <p>
              京都市のまちづくりや地域の動きを見ていると、日々さまざまな政策や条例が議論されています。しかし、実際に議会の公式サイトを見てみると、そこにあるのは数万字におよぶ膨大な議事録の文字の羅列でした。
            </p>
            <p>
              「誰がどんなテーマに関心を持ち、どういうスタンスで質疑を行っているのか」を知りたいと思っても、忙しい日常の中でこれらを一つひとつ読み通すのはかなり骨が折れます。
            </p>
            <div className="p-4 rounded-2xl bg-indigo-50/60 border border-indigo-100 text-indigo-950 text-sm font-medium leading-relaxed">
              「自然言語処理やAIの力を借りてデータを整理すれば、もっと直感的に議論の論点や流れを追えるのではないか？」
            </div>
            <p>
              そんな個人的な知的好奇心と関心から、このサイトの開発をスタートしました。
            </p>
          </div>
        </section>

        {/* 3. このツールのスタンス（OUR APPROACH） */}
        <section className="bg-white rounded-3xl border border-slate-200 p-8 md:p-10 shadow-sm space-y-5">
          <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
            <Lightbulb className="w-4 h-4" />
            OUR APPROACH / このツールのスタンス
          </div>
          <h2 className="text-xl md:text-2xl font-black text-slate-900 leading-snug">
            正解を決めるためではなく、論点を立体的に眺めるために。
          </h2>
          <div className="space-y-4 text-sm md:text-base text-slate-600 leading-relaxed font-normal">
            <p>
              本サイトは、特定の政治的主張を支持・批判したり、議員の優劣をランキング付けしたりするものではありません。
            </p>
            <p>
              議事録という公開データをAIで分析し、「どのようなテーマに注力しているのか」「どのような視点から提案を行っているのか」を構造化して表示しています。AIによる要約やスコアリングはあくまでひとつの補助線（補助的な見方）に過ぎません。
            </p>
            <p className="bg-slate-50 p-4 rounded-2xl border border-slate-200 text-slate-700 text-sm">
              「この議員はこういう分野を熱心に質問しているんだ」「会派によって着眼点がこれだけ違うんだ」といった発見のきっかけとして、気軽にデータを眺めてもらうためのツールを目指しています。
            </p>
          </div>
          {onOpenMethodology && (
            <div className="pt-2">
              <button
                onClick={onOpenMethodology}
                className="text-xs font-bold text-indigo-600 hover:text-indigo-800 underline underline-offset-4 inline-flex items-center cursor-pointer transition-colors"
              >
                AIの客観的評価基準（プロンプト・仕様書）を見る →
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
            <span>本プロジェクトは、特定の政党・団体等とは一切関係のない、個人の関心に基づく独立した取り組みです。</span>
          </div>

          <div className="space-y-4 pt-1">
            <div>
              <h3 className="text-xl font-black text-slate-900">山本 健人（Kento Yamamoto）</h3>
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
              現在は地域ビジネスの支援を行いながら、データ分析やWeb技術を活用した情報可視化の試みに取り組んでいます。（保有資格：行政書士、元米国公認会計士）
            </p>

            {/* TOIMAPリンク */}
            <div className="pt-2">
              <a
                href="https://toimap.jp/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-indigo-50 text-slate-700 hover:text-indigo-600 border border-slate-200 text-xs font-bold transition-all shadow-2xs"
              >
                <Award className="w-3.5 h-3.5 text-amber-500" />
                <span>シビックテックの取り組み：TOIMAP（トイマップ）公式サイト</span>
                <ExternalLink className="w-3 h-3 ml-0.5 opacity-60" />
              </a>
            </div>
          </div>
        </section>

        {/* 5. 今後の予定（FUTURE STEPS） */}
        <section className="bg-white rounded-3xl border border-slate-200 p-8 md:p-10 shadow-sm space-y-6">
          <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
            <Milestone className="w-4 h-4" />
            FUTURE STEPS / 今後の予定
          </div>
          <div>
            <h2 className="text-xl md:text-2xl font-black text-slate-900 leading-snug">
              本サービスは現在、個人開発による実験的なベータ版として公開しています。
            </h2>
          </div>

          <div className="space-y-3 pt-1">
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
              <div className="text-xs font-black text-slate-800">1. データの拡充</div>
              <p className="text-xs text-slate-600 leading-relaxed">
                京都市会の直近の質疑データの順次反映・分析精度の向上
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
              <div className="text-xs font-black text-slate-800">2. 機能のブラッシュアップ</div>
              <p className="text-xs text-slate-600 leading-relaxed">
                実際に使ってくださった方々からのご意見をもとにした検索や比較UIの改善
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
              <div className="text-xs font-black text-slate-800">3. 他地域への展開の検討</div>
              <p className="text-xs text-slate-600 leading-relaxed">
                需要やフィードバックを見ながら、周辺自治体や他都市への対応も緩やかに模索していきます
              </p>
            </div>
          </div>

          {/* ご意見・フィードバック導線 */}
          <div className="mt-8 pt-8 border-t border-slate-100 text-center space-y-4">
            <p className="text-xs text-slate-500 max-w-lg mx-auto leading-relaxed">
              データの誤記やシステムの改善点、感想などがございましたら、お気軽にフィードバックフォームよりお寄せください。
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