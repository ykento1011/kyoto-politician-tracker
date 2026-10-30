import React from "react";
import { Search, Sparkles, Compass, ArrowRight, ExternalLink, Flag } from "lucide-react";
import { getCityConfig } from "../config/cities";

export default function HeroSection({
  searchQuery,
  setSearchQuery,
  onSearchSubmit,
  onKeywordClick,
  onOpenGuide,
  cityCode = "kyoto"
}) {
  const config = getCityConfig(cityCode) || {
    councilName: "市会",
    hotTopics: [],
    scopeText: "公式会議録・議決データ"
  };

  const cityName = config.councilName;
  const hotTopics = config.hotTopics || [];
  const scopeText = config.scopeText;

  return (
    <section className="text-center py-6 md:py-10 space-y-4">
      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-black shadow-2xs">
        <Sparkles className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
        {cityName} 公開データ × 生成AI分析
      </div>

      <h1 className="text-3xl md:text-5xl font-black text-slate-900 tracking-tight leading-tight">
        対話がわかる。政策が見える。
      </h1>
      <div className="space-y-2 max-w-xl mx-auto">
        <p className="text-xs md:text-sm text-slate-600 leading-relaxed font-medium">
          公式の会議録データを客観的に構造化し、膨大な質疑スレッドの横断検索を実現。文字数や登壇回数だけでは見えない議員それぞれの政策対話の特徴を、統一ルーブリックによるデータ分析で可視化します。
        </p>
        <p className="text-xs md:text-sm font-black text-indigo-950">
          AIは入口。判断するのは市民です。
        </p>
      </div>

      <div className="inline-flex flex-wrap items-center justify-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-100/80 border border-slate-200 text-[11px] text-slate-600 font-bold">
        <span className="flex items-center gap-1 text-indigo-700">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-pulse" />
          分析対象
        </span>
        <span>現任期（2023年5月〜最新公開分）</span>
        <span className="text-slate-300">|</span>
        <span>{scopeText}</span>
      </div>

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

      <div className="max-w-xl mx-auto pt-2 text-left">
        <div className="bg-amber-50/90 border border-amber-200/80 rounded-2xl p-3.5 sm:p-4 shadow-2xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <div className="w-7 h-7 rounded-xl bg-amber-100/90 border border-amber-200 flex items-center justify-center shrink-0 mt-0.5">
              <Flag className="w-3.5 h-3.5 text-rose-500 fill-rose-500/20" />
            </div>
            <div className="space-y-0.5">
              <div className="text-xs font-black text-amber-950 flex items-center gap-1.5 flex-wrap">
                <span>一次資料のリンク切れ・誤記は「旗マーク（⚑）」から</span>
                <span className="text-[10px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.2 rounded">自動取得</span>
              </div>
              <p className="text-[11px] text-amber-900/80 leading-relaxed font-medium">
                各カードの公式原本リンク横にある <strong className="text-rose-600 font-bold">⚑</strong> を押すと、発言IDやURLが自動添付され1タップで報告できます。
              </p>
            </div>
          </div>
          <a
            href="https://docs.google.com/forms/d/e/1FAIpQLSf-GwUeTmRg05kBYyf0LJRoGwexG7Jn_G0-C0q3GynYayxFBQ/viewform?usp=send_form"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full sm:w-auto shrink-0 inline-flex items-center justify-center gap-1 px-3 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition-colors shadow-2xs cursor-pointer text-center"
            title="一般的なご意見や改善要望フォームを開く"
          >
            <span>その他のご意見</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      <div className="max-w-xl mx-auto pt-2">
        <form onSubmit={onSearchSubmit} className="relative flex items-center">
          <Search className="w-5 h-5 text-slate-400 absolute left-4 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={`${cityName}の論点、キーワード、議員名で議会全体を横断検索...`}
            className="w-full pl-12 pr-24 py-3.5 bg-white border border-slate-300 rounded-2xl shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm font-bold text-slate-800 placeholder:text-slate-400 transition-all"
          />
          <button
            type="submit"
            className="absolute right-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-black rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            検索
          </button>
        </form>

        <div className="flex items-center gap-1.5 flex-wrap justify-center mt-3 text-xs">
          <span className="text-[11px] font-bold text-slate-400">注目の論点:</span>
          {hotTopics.map((topic) => (
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
