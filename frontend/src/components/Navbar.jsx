import React from 'react';
import { BookOpen, GitCompare, Landmark, Info } from 'lucide-react';

export default function Navbar({
  onLogoClick,
  onOpenMethodology,
  onOpenAbout, // 💡 追加
  onOpenCompare,
  isCompareMode = false
}) {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-2xs">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* ロゴ */}
        <button
          onClick={onLogoClick}
          className="flex items-center gap-2.5 text-left cursor-pointer group"
        >
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-sm group-hover:bg-indigo-700 transition-colors">
            <Landmark className="w-5 h-5" />
          </div>
          <div>
            <div className="font-black text-base text-slate-900 tracking-tight leading-none group-hover:text-indigo-600 transition-colors">
              議会のミカタ <span className="text-indigo-600 text-xs font-extrabold bg-indigo-50 px-1.5 py-0.5 rounded ml-1 border border-indigo-100">京都</span>
            </div>
            <div className="text-[10px] text-slate-400 font-bold tracking-wider mt-0.5">
              KYOTO CITY COUNCIL TRACKER
            </div>
          </div>
        </button>

        {/* ナビゲーションメニュー */}
        <nav className="flex items-center gap-2">
          {/* 当サイトについて（About） */}
          <button
            onClick={onOpenAbout}
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold text-slate-600 hover:text-indigo-600 hover:bg-slate-50 transition-colors cursor-pointer"
          >
            <Info className="w-3.5 h-3.5 text-indigo-500" />
            <span>当サイトについて</span>
          </button>

          {/* AI採点基準（Methodology） */}
          <button
            onClick={onOpenMethodology}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold text-slate-600 hover:text-indigo-600 hover:bg-slate-50 transition-colors cursor-pointer"
          >
            <BookOpen className="w-3.5 h-3.5 text-slate-400" />
            <span className="hidden md:inline">AI採点基準</span>
          </button>

          {/* 議員比較 */}
          <button
            onClick={onOpenCompare}
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              isCompareMode
                ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                : 'bg-white border border-slate-200 hover:border-indigo-300 text-slate-700 hover:text-indigo-600 shadow-2xs'
            }`}
          >
            <GitCompare className="w-3.5 h-3.5 text-indigo-500" />
            <span>議員比較</span>
          </button>
        </nav>
      </div>
    </header>
  );
}