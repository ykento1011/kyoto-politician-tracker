import React, { useState, useRef, useEffect } from 'react';
import { 
  Landmark, 
  Compass, 
  HelpCircle, 
  GitCompare, 
  BookOpen, 
  ChevronDown, 
  Check, 
  Menu, 
  X 
} from 'lucide-react';

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
  const [isCityDropdownOpen, setIsCityDropdownOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const desktopDropdownRef = useRef(null);

  const CITIES = {
    kyoto: { label: '京都市', path: '/kyoto/' },
    osaka: { label: '大阪市', path: '/osaka/' },
    nagoya: { label: '名古屋市', path: '/nagoya/' },
    yokohama: { label: '横浜市', path: '/yokohama/' },
    kobe: { label: '神戸市', path: '/kobe/' }
  };

  // PC版ドロップダウンの枠外クリック検知
  useEffect(() => {
    function handleClickOutside(event) {
      if (desktopDropdownRef.current && !desktopDropdownRef.current.contains(event.target)) {
        setIsCityDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // メニューが開いているときは背景スクロールを抑制
  useEffect(() => {
    if (isMobileMenuOpen || isCityDropdownOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobileMenuOpen, isCityDropdownOpen]);

  const closeAll = () => {
    setIsCityDropdownOpen(false);
    setIsMobileMenuOpen(false);
  };

  const handleCityChange = (newCity) => {
    closeAll();
    if (newCity === 'portal') {
      window.location.href = '/';
      return;
    }
    if (newCity === cityCode) return;
    window.location.href = CITIES[newCity]?.path || `/${newCity}/`;
  };

  const handleMenuAction = (action) => {
    closeAll();
    if (action) action();
  };

  return (
    <>
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-2xs select-none">
        <div className="max-w-6xl mx-auto px-3 sm:px-6 h-14 sm:h-16 flex items-center justify-between gap-2">
          
          {/* ロゴエリア */}
          <button
            type="button"
            onClick={() => {
              closeAll();
              onLogoClick();
            }}
            className="flex items-center gap-2 text-left group cursor-pointer focus:outline-none shrink-0 touch-manipulation"
          >
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-sm group-hover:bg-indigo-700 transition-colors shrink-0">
              <Landmark className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="shrink-0">
              <div className="text-sm sm:text-base font-black text-slate-900 tracking-tight leading-none group-hover:text-indigo-600 transition-colors whitespace-nowrap">
                議会のミカタ
              </div>
              <div className="hidden sm:block text-[10px] font-bold text-slate-400 tracking-wider mt-0.5 whitespace-nowrap">
                {CITIES[cityCode]?.label || '自治体'}会・政策プロセス可視化ポータル
              </div>
            </div>
          </button>

          {/* ========================================================= */}
          {/* PC用ナビゲーション (640px 以上) */}
          {/* ========================================================= */}
          <nav className="hidden sm:flex items-center gap-1.5 sm:gap-2 shrink-0">
            
            {/* PC 都市選択 */}
            <div className="relative mr-1" ref={desktopDropdownRef}>
              <button
                type="button"
                onClick={() => setIsCityDropdownOpen(!isCityDropdownOpen)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer shadow-2xs border whitespace-nowrap ${
                  isCityDropdownOpen 
                    ? 'bg-indigo-50 border-indigo-200 text-indigo-700' 
                    : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300'
                }`}
              >
                <span>{CITIES[cityCode]?.label || '都市選択'}</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isCityDropdownOpen ? 'rotate-180 text-indigo-600' : 'text-slate-400'}`} />
              </button>

              {isCityDropdownOpen && (
                <div className="absolute top-full right-0 mt-1.5 w-44 bg-white rounded-xl shadow-xl border border-slate-200 py-1.5 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
                  <button
                    type="button"
                    onClick={() => handleCityChange('portal')}
                    className="w-full flex items-center justify-between px-3 py-2 text-xs font-black text-slate-500 hover:text-indigo-700 hover:bg-indigo-50 border-b border-slate-100 transition-colors text-left cursor-pointer"
                  >
                    <span>← 総合ポータルへ戻る</span>
                  </button>
                  
                  {Object.entries(CITIES).map(([code, { label }]) => (
                    <button
                      type="button"
                      key={code}
                      onClick={() => handleCityChange(code)}
                      className="w-full flex items-center justify-between px-3 py-2 text-xs font-bold hover:bg-slate-50 transition-colors text-left cursor-pointer group"
                    >
                      <span className={code === cityCode ? 'text-indigo-600 font-black' : 'text-slate-600 group-hover:text-slate-900'}>
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
              type="button"
              onClick={onOpenMayor}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-black text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-all cursor-pointer shadow-2xs whitespace-nowrap"
            >
              <Landmark className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
              <span>市長政策進捗</span>
              <span className="bg-indigo-600 text-white text-[9px] px-1.5 py-0.2 rounded-full font-bold shrink-0">New</span>
            </button>

            {/* 議員比較 */}
            <button
              type="button"
              onClick={onOpenCompare}
              className={`hidden md:flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                isCompareMode
                  ? 'bg-indigo-600 text-white shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <GitCompare className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span>議員比較</span>
            </button>

            {/* ガイド */}
            <button
              type="button"
              onClick={onOpenGuide}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all cursor-pointer whitespace-nowrap"
            >
              <Compass className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span>できること</span>
            </button>

            {/* 分析方法 */}
            <button
              type="button"
              onClick={onOpenMethodology}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all cursor-pointer whitespace-nowrap"
            >
              <BookOpen className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span>分析方法</span>
            </button>

            {/* サイトについて */}
            <button
              type="button"
              onClick={onOpenAbout}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all cursor-pointer whitespace-nowrap"
            >
              <HelpCircle className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span>サイトについて</span>
            </button>
          </nav>

          {/* ========================================================= */}
          {/* モバイル用ナビゲーション (640px 未満) */}
          {/* ========================================================= */}
          <div className="flex sm:hidden items-center gap-1.5 shrink-0">
            
            {/* モバイル都市選択ボタン */}
            <button
              type="button"
              onClick={() => {
                setIsMobileMenuOpen(false);
                setIsCityDropdownOpen(!isCityDropdownOpen);
              }}
              className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-bold bg-slate-100 text-slate-700 active:bg-slate-200 touch-manipulation whitespace-nowrap"
            >
              <span>{CITIES[cityCode]?.label || '都市'}</span>
              <ChevronDown className={`w-3.5 h-3.5 text-slate-500 transition-transform ${isCityDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* モバイル政策進捗ボタン */}
            <button
              type="button"
              onClick={() => {
                closeAll();
                onOpenMayor();
              }}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 active:bg-indigo-100 touch-manipulation whitespace-nowrap shrink-0"
            >
              <Landmark className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
              <span>政策進捗</span>
            </button>

            {/* モバイルハンバーガーボタン */}
            <button
              type="button"
              onClick={() => {
                setIsCityDropdownOpen(false);
                setIsMobileMenuOpen(!isMobileMenuOpen);
              }}
              className="p-1.5 rounded-lg text-slate-700 active:bg-slate-100 touch-manipulation shrink-0"
              aria-label="メニュー"
            >
              {isMobileMenuOpen ? (
                <X className="w-5 h-5 text-indigo-600" />
              ) : (
                <Menu className="w-5 h-5 text-slate-700" />
              )}
            </button>
          </div>

        </div>

        {/* ========================================================= */}
        {/* モバイル展開エリア (Z軸 50 / 最前面) */}
        {/* ========================================================= */}

        {/* 1. モバイル都市切り替えドロワー */}
        {isCityDropdownOpen && (
          <div className="sm:hidden border-t border-slate-200 bg-white px-4 py-3 shadow-2xl relative z-50 animate-in slide-in-from-top-1 duration-150">
            <div className="text-[11px] font-bold text-slate-400 mb-2">表示する自治体を選択</div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleCityChange('portal')}
                className="col-span-2 text-left px-3 py-2.5 rounded-xl text-xs font-black text-indigo-600 bg-indigo-50 border border-indigo-100 active:bg-indigo-100 touch-manipulation"
              >
                ← 総合ポータルへ戻る
              </button>
              {Object.entries(CITIES).map(([code, { label }]) => (
                <button
                  type="button"
                  key={code}
                  onClick={() => handleCityChange(code)}
                  className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-bold border touch-manipulation ${
                    code === cityCode 
                      ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm' 
                      : 'bg-white border-slate-200 text-slate-700 active:bg-slate-50'
                  }`}
                >
                  <span>{label}</span>
                  {code === cityCode && <Check className="w-3.5 h-3.5 text-white" />}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 2. モバイルメインメニュードロワー */}
        {isMobileMenuOpen && (
          <div className="sm:hidden border-t border-slate-200 bg-white px-3 py-3 shadow-2xl relative z-50 animate-in slide-in-from-top-1 duration-150 space-y-1.5">
            <button
              type="button"
              onClick={() => handleMenuAction(onOpenMayor)}
              className="w-full flex items-center gap-3 px-3.5 py-3 rounded-xl text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-100 text-left active:bg-indigo-100 touch-manipulation"
            >
              <Landmark className="w-4 h-4 text-indigo-600 shrink-0" />
              <div className="flex-1 flex items-center justify-between">
                <span>市長政策進捗トラッカー</span>
                <span className="bg-indigo-600 text-white text-[9px] px-1.5 py-0.2 rounded-full font-bold">New</span>
              </div>
            </button>

            <button
              type="button"
              onClick={() => handleMenuAction(onOpenCompare)}
              className={`w-full flex items-center gap-3 px-3.5 py-3 rounded-xl text-xs font-bold text-left transition-colors touch-manipulation ${
                isCompareMode ? 'bg-indigo-600 text-white' : 'text-slate-700 active:bg-slate-100'
              }`}
            >
              <GitCompare className="w-4 h-4 text-slate-500 shrink-0" />
              <span>議員比較モード</span>
            </button>

            <button
              type="button"
              onClick={() => handleMenuAction(onOpenGuide)}
              className="w-full flex items-center gap-3 px-3.5 py-3 rounded-xl text-xs font-bold text-slate-700 active:bg-slate-100 text-left touch-manipulation"
            >
              <Compass className="w-4 h-4 text-slate-500 shrink-0" />
              <span>できること（活用ガイド）</span>
            </button>

            <button
              type="button"
              onClick={() => handleMenuAction(onOpenMethodology)}
              className="w-full flex items-center gap-3 px-3.5 py-3 rounded-xl text-xs font-bold text-slate-700 active:bg-slate-100 text-left touch-manipulation"
            >
              <BookOpen className="w-4 h-4 text-slate-500 shrink-0" />
              <span>データ分析方法</span>
            </button>

            <button
              type="button"
              onClick={() => handleMenuAction(onOpenAbout)}
              className="w-full flex items-center gap-3 px-3.5 py-3 rounded-xl text-xs font-bold text-slate-700 active:bg-slate-100 text-left touch-manipulation"
            >
              <HelpCircle className="w-4 h-4 text-slate-500 shrink-0" />
              <span>当サイトについて（運営理念）</span>
            </button>
          </div>
        )}
      </header>

      {/* モバイル展開時の半透明バックドロップ (Z軸 40 / 外側タップで確実に閉じる) */}
      {(isCityDropdownOpen || isMobileMenuOpen) && (
        <div 
          onClick={closeAll}
          className="fixed inset-0 bg-slate-900/30 backdrop-blur-[2px] z-40 sm:hidden animate-in fade-in duration-150"
          aria-hidden="true"
        />
      )}
    </>
  );
}
