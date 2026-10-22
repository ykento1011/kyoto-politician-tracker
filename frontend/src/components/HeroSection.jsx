import React from 'react';
import { Search, Sparkles, Compass, ArrowRight } from 'lucide-react';

const HOT_TOPICS = [
  'オーバーツーリズム',
  '市バス',
  '中小企業支援',
  '空き家対策',
  '伝統産業',
  '子育て支援',
];

export default function HeroSection({
  searchQuery,
  setSearchQuery,
  onSearchSubmit,
  onKeywordClick,
  onOpenGuide
}) {
  return (
    <section className="text-center py-6 md:py-10 space-y-4">
      {/* サービスバッジ */}
      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-black shadow-2xs">
        <Sparkles className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
        京都市議会 公開データ × 生成AI分析
      </div>

      <h1 className="text-3xl md:text-5xl font-black text-slate-900 tracking-tight leading-tight">
        対話がわかる。政策が見える。
      </h1>
      <div className="space-y-2 max-w-xl mx-auto">
        <p className="text-xs md:text-sm text-slate-600 leading-relaxed font-medium">
          12万件超の発言記録を構造化し、5,100超の質疑スレッドを横断検索。文字数や登壇回数だけでは見えない議員それぞれの政策対話の特徴を、統一ルーブリックによるAI評価で可視化します。
        </p>
        <p className="text-xs md:text-sm font-black text-indigo-950">
          AIは入口。判断するのは市民です。
        </p>
      </div>

      {/* 分析対象バッジ */}
      <div className="inline-flex flex-wrap items-center justify-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-100/80 border border-slate-200 text-[11px] text-slate-600 font-bold">
        <span className="flex items-center gap-1 text-indigo-700">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-pulse" />
          分析対象
        </span>
        <span>現任期（2023年5月〜最新公開分）</span>
        <span className="text-slate-300">|</span>
        <span>本会議・全常任委員会・特別委員会（12万件超の発言・5,100超の質疑・全67議員・300件の議案賛否）</span>
      </div>

      {/* できることページへの直通バナー */}
      <div className="pt-1">
        <button
          onClick={onOpenGuide}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-white hover:bg-indigo-50 text-indigo-700 border border-indigo-200 text-xs font-bold transition-all shadow-2xs group cursor-pointer"
        >
          <Compass className="w-3.5 h-3.5 text-indigo-600" />
          <span>初めての方へ：当サイトでできること・活用ガイドを見る</span>
          <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform text-indigo-500" />
        </button>
      </div>

      {/* 検索入力窓 */}
      <div className="max-w-xl mx-auto pt-2">
        <form onSubmit={onSearchSubmit} className="relative flex items-center">
          <Search className="w-5 h-5 text-slate-400 absolute left-4 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="論点、キーワード、議員名で議会全体を横断検索..."
            className="w-full pl-12 pr-24 py-3.5 bg-white border border-slate-300 rounded-2xl shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm font-bold text-slate-800 placeholder:text-slate-400 transition-all"
          />
          <button
            type="submit"
            className="absolute right-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-black rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            検索
          </button>
        </form>

        {/* 注目の論点タグ */}
        <div className="flex items-center gap-1.5 flex-wrap justify-center mt-3 text-xs">
          <span className="text-[11px] font-bold text-slate-400">注目の論点:</span>
          {HOT_TOPICS.map((topic) => (
            <button
              key={topic}
              onClick={() => onKeywordClick(topic)}
              className="px-2.5 py-1 rounded-lg bg-white hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 text-slate-600 hover:text-indigo-600 text-[11px] font-bold transition-all cursor-pointer shadow-2xs"
            >
              {topic}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}