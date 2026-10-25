import React, { useState, useRef, useEffect } from 'react';
import { Landmark, Compass, HelpCircle, GitCompare, BookOpen, ChevronDown, Check } from 'lucide-react';

export default function Navbar({
  onLogoClick,
  onOpenGuide,
  onOpenAbout,
  onOpenMethodology,
  onOpenCompare,
  onOpenMayor,
  isCompareMode = false,
  cityCode = 'kyoto'
}) {
  // カスタムドロップダウンの開閉状態管理
  const [isCityDropdownOpen, setIsCityDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const CITIES = {
    kyoto: { label: '京都市', prefix: '' },
    osaka: { label: '大阪市', prefix: '/osaka' }
  };

  // 枠外クリックでドロップダウンを閉じる処理
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsCityDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleCityChange = (newCity) => {
    setIsCityDropdownOpen(false);
    if (newCity === cityCode) return;
    
    // 都市切り替えのルーティング処理
    if (newCity === 'kyoto') {
      window.location.href = '/';
    } else {
      window.location.href = CITIES[newCity].prefix;
    }
  };

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
            <div className="hidden sm:block text-[10px] font-bold text-slate-400 tracking-wider mt-0.5">
              {CITIES[cityCode]?.label}会・政策プロセス可視化ポータル
            </div>
          </div>
        </button>

        {/* ナビゲーションメニュー */}
        <nav className="flex items-center gap-1 sm:gap-2 shrink-0">
          
          {/* モダンなカスタム都市選択ドロップダウン */}
          <div className="relative mr-1" ref={dropdownRef}>
            <button
              onClick={() => setIsCityDropdownOpen(!isCityDropdownOpen)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer shadow-2xs border ${
                isCityDropdownOpen 
                  ? 'bg-indigo-50 border-indigo-200 text-indigo-700' 
                  : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300'
              }`}
            >
              <span>{CITIES[cityCode]?.label}</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isCityDropdownOpen ? 'rotate-180 text-indigo-600' : 'text-slate-400'}`} />
            </button>

            {/* ドロップダウンメニュー本体 */}
            {isCityDropdownOpen && (
              <div className="absolute top-full right-0 mt-1.5 w-32 bg-white rounded-xl shadow-lg border border-slate-200 py-1.5 z-50 overflow-hidden transform origin-top animate-in fade-in slide-in-from-top-2 duration-200">
                {Object.entries(CITIES).map(([code, { label }]) => (
                  <button
                    key={code}
                    onClick={() => handleCityChange(code)}
                    className="w-full flex items-center justify-between px-3 py-2 text-xs font-bold hover:bg-slate-50 transition-colors text-left cursor-pointer group"
                  >
                    <span className={code === cityCode ? 'text-indigo-600' : 'text-slate-600 group-hover:text-slate-900'}>
                      {label}
                    </span>
                    {code === cityCode && <Check className="w-3.5 h-3.5 text-indigo-600" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 市長政策進捗 */}
          <button
            onClick={onOpenMayor}
            className="flex items-center gap-1 sm:gap-1.5 px-2 py-1.5 sm:px-3 sm:py-1.5 rounded-lg text-xs font-black text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-all cursor-pointer shadow-2xs"
            title={`${CITIES[cityCode]?.label.replace('市', '市長')} 政策進捗`}
          >
            <Landmark className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
            <span>
              <span className="hidden sm:inline">{cityCode === 'osaka' ? '横山市長 ' : '松井市長 '}</span>政策進捗
            </span>
            <span className="bg-indigo-600 text-white text-[9px] px-1.5 py-0.2 rounded-full font-bold shrink-0">New</span>
          </button>

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

          <button
            onClick={onOpenGuide}
            className="flex items-center gap-1 p-2 sm:px-2.5 sm:py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all cursor-pointer"
            title="できること（活用ガイド）"
          >
            <Compass className="w-4 h-4 sm:w-3.5 sm:h-3.5 text-slate-500 shrink-0" />
            <span className="hidden sm:inline">できること</span>
          </button>

          <button
            onClick={onOpenMethodology}
            className="hidden sm:flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all cursor-pointer"
          >
            <BookOpen className="w-3.5 h-3.5 text-slate-500 shrink-0" />
            <span>分析方法</span>
          </button>

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