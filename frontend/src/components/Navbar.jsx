import React from 'react';
import { Landmark, Compass, HelpCircle, GitCompare, BookOpen } from 'lucide-react';

export default function Navbar({
  onLogoClick,
  onOpenGuide,
  onOpenAbout,
  onOpenMethodology,
  onOpenCompare,
  onOpenMayor,
  isCompareMode = false
}) {
  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-2xs">
      <div className="max-w-6xl mx-auto px-3 sm:px-6 h-14 sm:h-16 flex items-center justify-between gap-2 sm:gap-4">
        {/* ロゴエリア */}
        <button
          onClick={onLogoClick}
          className="flex items-center gap-2 sm:gap-2.5 text-left group cursor-pointer focus:outline-none shrink-0"
        >
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-sm group-hover:bg-indigo-700 transition-colors shrink-0">
            <Landmark className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
          <div>
            <div className="text-sm sm:text-base font-black text-slate-900 tracking-tight leading-none group-hover:text-indigo-600 transition-colors">
              議会のミカタ
            </div>
            {/* 💡 スマホ時は非表示にし、PC以上で表示 */}
            <div className="hidden sm:block text-[10px] font-bold text-slate-400 tracking-wider mt-0.5">
              京都市議会・政策プロセス可視化ポータル
            </div>
          </div>
        </button>

        {/* ナビゲーションメニュー */}
        <nav className="flex items-center gap-1 sm:gap-2 shrink-0">
          {/* 松井市長 政策進捗ボタン（スマホでは短縮表示） */}
          <button
            onClick={onOpenMayor}
            className="flex items-center gap-1 sm:gap-1.5 px-2 py-1.5 sm:px-3 sm:py-1.5 rounded-lg text-xs font-black text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-all cursor-pointer shadow-2xs"
            title="松井市長 政策進捗"
          >
            <Landmark className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
            <span>
              <span className="hidden sm:inline">松井市長 </span>政策進捗
            </span>
            <span className="bg-indigo-600 text-white text-[9px] px-1.5 py-0.2 rounded-full font-bold shrink-0">New</span>
          </button>

          {/* 議員比較（中画面以上） */}
          <button
            onClick={onOpenCompare}
            className={`hidden md:flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              isCompareMode
                ? 'bg-indigo-600 text-white shadow-2xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <GitCompare className="w-3.5 h-3.5 text-slate-500" />
            <span>議員比較</span>
          </button>

          {/* ガイド（スマホではアイコンのみ） */}
          <button
            onClick={onOpenGuide}
            className="flex items-center gap-1 p-2 sm:px-2.5 sm:py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all cursor-pointer"
            title="できること（活用ガイド）"
          >
            <Compass className="w-4 h-4 sm:w-3.5 sm:h-3.5 text-slate-500 shrink-0" />
            <span className="hidden sm:inline">できること</span>
          </button>

          {/* 評価基準（スマホでは非表示） */}
          <button
            onClick={onOpenMethodology}
            className="hidden sm:flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all cursor-pointer"
          >
            <BookOpen className="w-3.5 h-3.5 text-slate-500 shrink-0" />
            <span>評価基準</span>
          </button>

          {/* 当サイトについて（スマホではアイコンのみ） */}
          <button
            onClick={onOpenAbout}
            className="flex items-center gap-1 p-2 sm:px-2.5 sm:py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all cursor-pointer"
            title="当サイトについて"
          >
            <HelpCircle className="w-4 h-4 sm:w-3.5 sm:h-3.5 text-slate-500 shrink-0" />
            <span className="hidden sm:inline">サイトについて</span>
          </button>
        </nav>
      </div>
    </header>
  );
}