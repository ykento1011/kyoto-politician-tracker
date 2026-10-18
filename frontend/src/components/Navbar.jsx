import React from 'react';
import { Scale, BookOpen, GitCompare } from 'lucide-react';
import GithubIcon from './GithubIcon';

export default function Navbar({ onLogoClick, onOpenMethodology, onOpenCompare, isCompareMode }) {
  return (
    <nav className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200/80 transition-all h-16">
      <div className="max-w-6xl mx-auto px-6 h-full flex items-center justify-between">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={onLogoClick}>
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold tracking-tight text-slate-900 text-base">議会のミカタ <span className="text-sm">京都</span></span>
              <span className="text-[9px] font-black px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">BETA</span>
            </div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider hidden sm:block mt-0.5">京都市議会 AI政策対話ログ</p>
          </div>
        </div>

        {isCompareMode ? (
          <div className="flex items-center space-x-3">
            <span className="text-xs font-bold text-slate-500 hidden sm:inline">徹底比較モード</span>
            <a
              href="https://github.com/ykento1011/kyoto-politician-tracker"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center text-xs font-bold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg transition-colors shadow-2xs"
            >
              <GithubIcon className="w-3.5 h-3.5 mr-1.5 text-slate-700" />
              GitHub
            </a>
            <button 
              onClick={onLogoClick}
              className="text-xs font-bold text-slate-600 hover:text-indigo-600 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
            >
              トップへ戻る
            </button>
          </div>
        ) : (
          <div className="flex items-center space-x-2.5">
            <button
              onClick={onOpenMethodology}
              className="inline-flex items-center text-xs font-bold text-slate-600 hover:text-indigo-600 bg-white hover:bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl transition-colors shadow-2xs"
            >
              <BookOpen className="w-3.5 h-3.5 mr-1.5 text-indigo-500" />
              AI評価ロジックと基準
            </button>

            <a
              href="https://github.com/ykento1011/kyoto-politician-tracker"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center text-xs font-bold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl transition-colors shadow-2xs"
            >
              <GithubIcon className="w-3.5 h-3.5 mr-1.5 text-slate-700" />
              <span>GitHub</span>
            </a>

            <button
              onClick={() => onOpenCompare()}
              className="inline-flex items-center text-xs font-black text-indigo-600 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 px-3.5 py-2 rounded-xl transition-all shadow-2xs"
            >
              <GitCompare className="w-3.5 h-3.5 mr-1.5" />
              議員を比較する
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}