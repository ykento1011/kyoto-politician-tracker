import React from 'react';
import { X, Scale, ShieldCheck, BookOpen, CheckCircle2, AlertCircle } from 'lucide-react';

export default function MethodologyModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-3xl bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden my-8 flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ヘッダー */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-black text-slate-900">AI評価基準・プロンプト仕様書</h2>
              <p className="text-[11px] font-bold text-slate-500">Methodology & Rubric Specifications</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-white hover:bg-slate-100 text-slate-400 hover:text-slate-700 flex items-center justify-center border border-slate-200 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 本文エリア */}
        <div className="p-6 md:p-8 overflow-y-auto space-y-8 text-slate-700 text-xs md:text-sm leading-relaxed">
          {/* 中立性・運用の基本原則 */}
          <section className="bg-indigo-50/60 border border-indigo-100 rounded-2xl p-5 space-y-3">
            <div className="flex items-center gap-2 text-indigo-900 font-black text-xs uppercase tracking-wider">
              <ShieldCheck className="w-4 h-4 text-indigo-600" />
              中立性の宣誓と機械的適用の原則
            </div>
            <p className="text-slate-700">
              本プラットフォームは特定の政党・会派・政治信条を支持または批判するものではありません。
              評価はLLM（Gemini）を用い、<strong>所属会派や議員名を完全に同一の条件下に置いた統一プロンプト</strong>によって機械的に算出されています。
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 text-[11px] text-slate-600 font-bold">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                政治信条（右派・左派等）の良し悪しは一切採点しない
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                全12万発言に対して同一のルーブリック基準を厳格適用
              </div>
            </div>
          </section>

          {/* 4軸評価ルーブリックの詳細 */}
          <section className="space-y-4">
            <h3 className="text-sm font-black text-slate-900 flex items-center gap-2">
              <Scale className="w-4 h-4 text-indigo-600" />
              4つの評価軸と採点ルーブリック（1.0 〜 5.0点）
            </h3>

            <div className="grid grid-cols-1 gap-3.5">
              <div className="p-4 rounded-xl border border-slate-200 bg-white">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-black text-slate-900 text-xs">1. 根拠・データ（Evidence Score）</span>
                  <span className="text-[10px] font-black text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">客観性の測定</span>
                </div>
                <p className="text-slate-600 text-xs leading-normal">
                  単なる主観的感想や伝聞にとどまらず、統計データ、公的調査結果、関係法令、他都市の先行事例、条例条文などの客観的事実・エビデンスをどの程度具体的に提示して論戦を組み立てているかを評価します。
                </p>
              </div>

              <div className="p-4 rounded-xl border border-slate-200 bg-white">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-black text-slate-900 text-xs">2. 対案・是正（Solution Score）</span>
                  <span className="text-[10px] font-black text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">政策提言性の測定</span>
                </div>
                <p className="text-slate-600 text-xs leading-normal">
                  市政の課題や行政の対応に対する批判・問題提起にとどまらず、「どのような制度改定や予算措置を行うべきか」「代替案としてどのような選択肢があるか」という具体的・建設的な解決策を提示できているかを評価します。
                </p>
              </div>

              <div className="p-4 rounded-xl border border-slate-200 bg-white">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-black text-slate-900 text-xs">3. 地域解像度（Local Focus Score）</span>
                  <span className="text-[10px] font-black text-amber-600 bg-amber-50 px-2 py-0.5 rounded">生活現場の実態反映</span>
                </div>
                <p className="text-slate-600 text-xs leading-normal">
                  抽象的な一般論ではなく、京都固有の地域事情、各行政区・学区の生活環境、中小企業や伝統産業の現場、市民・当事者が直面している切実な困りごとが、どれだけ生々しく具体的な解像度で議場に持ち込まれているかを測定します。
                </p>
              </div>

              <div className="p-4 rounded-xl border border-slate-200 bg-white">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-black text-slate-900 text-xs">4. 議論の進展（Constructive Score）</span>
                  <span className="text-[10px] font-black text-rose-600 bg-rose-50 px-2 py-0.5 rounded">論点整理・行政監視</span>
                </div>
                <p className="text-slate-600 text-xs leading-normal">
                  市長や局長等の答弁の矛盾、論点のすり替え、答弁漏れを的確に把握し、再質問によって議論を一歩前へ進め、市側の明確な方針転換や検討約束を引き出せているかを評価します。
                </p>
              </div>
            </div>
          </section>

          {/* 免責事項・留意点 */}
          <section className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-[11px] text-slate-500 space-y-2">
            <div className="flex items-center gap-1.5 font-bold text-slate-700">
              <AlertCircle className="w-3.5 h-3.5 text-slate-500" />
              データの取り扱いと利用上の留意事項
            </div>
            <ul className="list-disc pl-4 space-y-1 leading-relaxed">
              <li>本スコアは議事録テキストに基づくAI自然言語処理の結果であり、各議員の人格・品位を決定付けるものではありません。</li>
              <li>議長・副議長・委員長など、議事進行に特化した役職を務める登壇回については、評価の歪みを防ぐため一律で採点対象外としてフィルタリングを行っています。</li>
              <li>議事録表記の誤字脱字やデータの訂正要請につきましては、フッターのお問い合わせ窓口より承っております。</li>
            </ul>
          </section>
        </div>

        {/* フッター */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end shrink-0">
          <button
            onClick={onClose}
            className="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            閉じる
          </button>
        </div>
      </div>
    </div>
  );
}