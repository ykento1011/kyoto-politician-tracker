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

  // PC版のみ枠外クリックを監視（画面幅640px以上）
  useEffect(() => {
    function handleClickOutside(event) {
      if (window.innerWidth >= 640 && desktopDropdownRef.current && !desktopDropdownRef.current.contains(event.target)) {
        setIsCityDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

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
      {/* メインヘッダー: select-noneとbackdrop-blurを排除して確実にタップを感知 */}
      <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-xs">
        <div className="max-w-6xl mx-auto px-3 sm:px-6 h-14 sm:h-16 flex items-center justify-between gap-2">
          
          {/* ロゴ */}
          <button
            type="button"
            onClick={() => {
              closeAll();
              onLogoClick();
            }}
            className="flex items-center gap-2 text-left cursor-pointer focus:outline-none shrink-0"
          >
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-sm shrink-0">
              <Landmark className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="shrink-0">
              <div className="text-sm sm:text-base font-black text-slate-900 tracking-tight leading-none whitespace-nowrap">
                議会のミカタ
              </div>
              <div className="hidden sm:block text-[10px] font-bold text-slate-400 tracking-wider mt-0.5 whitespace-nowrap">
                {CITIES[cityCode]?.label || '自治体'}会・政策プロセス可視化ポータル
              </div>
            </div>
          </button>

          {/* PC用ナビゲーション (640px 以上) */}
          <nav className="hidden sm:flex items-center gap-1.5 sm:gap-2 shrink-0">
            {/* PC 都市選択 */}
            <div className="relative mr-1" ref={desktopDropdownRef}>
              <button
                type="button"
                onClick={() => setIsCityDropdownOpen(!isCityDropdownOpen)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border transition-colors cursor-pointer ${
                  isCityDropdownOpen 
                    ? 'bg-indigo-50 border-indigo-200 text-indigo-700' 
                    : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <span>{CITIES[cityCode]?.label || '都市選択'}</span>
                <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isCityDropdownOpen ? 'rotate-180 text-indigo-600' : ''}`} />
              </button>

              {isCityDropdownOpen && (
                <div className="absolute top-full right-0 mt-1.5 w-44 bg-white rounded-xl shadow-xl border border-slate-200 py-1.5 z-50 overflow-hidden">
                  <button
                    type="button"
                    onClick={() => handleCityChange('portal')}
                    className="w-full flex items-center justify-between px-3 py-2 text-xs font-black text-slate-500 hover:text-indigo-700 hover:bg-indigo-50 border-b border-slate-100 text-left cursor-pointer"
                  >
                    <span>← 総合ポータルへ戻る</span>
                  </button>
                  {Object.entries(CITIES).map(([code, { label }]) => (
                    <button
                      type="button"
                      key={code}
                      onClick={() => handleCityChange(code)}
                      className="w-full flex items-center justify-between px-3 py-2 text-xs font-bold hover:bg-slate-50 text-left cursor-pointer"
                    >
                      <span className={code === cityCode ? 'text-indigo-600 font-black' : 'text-slate-600'}>
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
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-black text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors cursor-pointer"
            >
              <Landmark className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
              <span>市長政策進捗</span>
              <span className="bg-indigo-600 text-white text-[9px] px-1.5 py-0.2 rounded-full font-bold shrink-0">New</span>
            </button>

            {/* 議員比較 */}
            <button
              type="button"
              onClick={onOpenCompare}
              className={`hidden md:flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
                isCompareMode ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <GitCompare className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span>議員比較</span>
            </button>

            {/* ガイド */}
            <button
              type="button"
              onClick={onOpenGuide}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <Compass className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span>できること</span>
            </button>

            {/* 分析方法 */}
            <button
              type="button"
              onClick={onOpenMethodology}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <BookOpen className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span>分析方法</span>
            </button>

            {/* サイトについて */}
            <button
              type="button"
              onClick={onOpenAbout}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <HelpCircle className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span>サイトについて</span>
            </button>
          </nav>

          {/* モバイル用ナビゲーション (640px 未満) */}
          <div className="flex sm:hidden items-center gap-2 shrink-0">
            {/* モバイル都市選択ボタン */}
            <button
              type="button"
              onClick={() => {
                setIsMobileMenuOpen(false);
                setIsCityDropdownOpen(!isCityDropdownOpen);
              }}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold bg-slate-100 text-slate-800 active:bg-slate-200 cursor-pointer"
            >
              <span>{CITIES[cityCode]?.label || '都市'}</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
            </button>

            {/* モバイル政策進捗ボタン */}
            <button
              type="button"
              onClick={() => {
                closeAll();
                onOpenMayor();
              }}
              className="flex items-center gap-1 min-h-[44px] px-3 py-2 rounded-lg text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 active:bg-indigo-100 cursor-pointer shrink-0"
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
              className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg text-slate-700 active:bg-slate-100 cursor-pointer shrink-0"
              aria-label="メニュー"
            >
              {isMobileMenuOpen ? <X className="w-6 h-6 text-indigo-600" /> : <Menu className="w-6 h-6 text-slate-800" />}
            </button>
          </div>

        </div>
        
      </header>

      {/* ========================================================= */}
      {/* モバイル専用: 独立した全画面オーバーレイ型メニュー (z-[100]) */}
      {/* ========================================================= */}

      {/* 1. モバイル都市切り替えシート */}
      {isCityDropdownOpen && (
        <div className="fixed inset-0 z-[100] sm:hidden flex flex-col justify-end bg-slate-900/40 animate-in fade-in duration-150">
          <div className="bg-white rounded-t-3xl p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <span className="text-sm font-black text-slate-900">自治体を切り替え</span>
              <button 
                type="button" 
                onClick={() => setIsCityDropdownOpen(false)}
                className="p-1 rounded-full text-slate-400 hover:bg-slate-100 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <button
              type="button"
              onClick={() => handleCityChange('portal')}
              className="w-full text-left px-4 py-3 rounded-xl text-xs font-black text-indigo-600 bg-indigo-50 border border-indigo-100 active:bg-indigo-100 cursor-pointer"
            >
              ← 総合ポータルへ戻る
            </button>

            <div className="grid grid-cols-2 gap-2">
              {Object.entries(CITIES).map(([code, { label }]) => (
                <button
                  type="button"
                  key={code}
                  onClick={() => handleCityChange(code)}
                  className={`flex items-center justify-between px-4 py-3 rounded-xl text-xs font-bold border cursor-pointer ${
                    code === cityCode 
                      ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm' 
                      : 'bg-white border-slate-200 text-slate-700 active:bg-slate-50'
                  }`}
                >
                  <span>{label}</span>
                  {code === cityCode && <Check className="w-4 h-4 text-white" />}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 2. モバイルメインメニューシート */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-[100] sm:hidden flex flex-col justify-end bg-slate-900/40 animate-in fade-in duration-150">
          <div className="bg-white rounded-t-3xl p-5 shadow-2xl space-y-2">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-2">
              <span className="text-sm font-black text-slate-900">メニュー</span>
              <button 
                type="button" 
                onClick={() => setIsMobileMenuOpen(false)}
                className="p-1 rounded-full text-slate-400 hover:bg-slate-100 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <button
              type="button"
              onClick={() => handleMenuAction(onOpenMayor)}
              className="w-full flex items-center justify-between px-4 py-3.5 rounded-xl text-xs font-black text-indigo-700 bg-indigo-50 border border-indigo-100 text-left active:bg-indigo-100 cursor-pointer"
            >
              <div className="flex items-center gap-3">
                <Landmark className="w-4 h-4 text-indigo-600 shrink-0" />
                <span>市長政策進捗トラッカー</span>
              </div>
              <span className="bg-indigo-600 text-white text-[9px] px-2 py-0.5 rounded-full font-bold">New</span>
            </button>

            <button
              type="button"
              onClick={() => handleMenuAction(onOpenCompare)}
              className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-xs font-bold text-left cursor-pointer ${
                isCompareMode ? 'bg-indigo-600 text-white' : 'text-slate-700 bg-slate-50 active:bg-slate-100'
              }`}
            >
              <GitCompare className="w-4 h-4 text-slate-500 shrink-0" />
              <span>議員比較モード</span>
            </button>

            <button
              type="button"
              onClick={() => handleMenuAction(onOpenGuide)}
              className="w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-xs font-bold text-slate-700 bg-slate-50 active:bg-slate-100 text-left cursor-pointer"
            >
              <Compass className="w-4 h-4 text-slate-500 shrink-0" />
              <span>できること（ご利用ガイド）</span>
            </button>

            <button
              type="button"
              onClick={() => handleMenuAction(onOpenMethodology)}
              className="w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-xs font-bold text-slate-700 bg-slate-50 active:bg-slate-100 text-left cursor-pointer"
            >
              <BookOpen className="w-4 h-4 text-slate-500 shrink-0" />
              <span>データ分析方法</span>
            </button>

            <button
              type="button"
              onClick={() => handleMenuAction(onOpenAbout)}
              className="w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-xs font-bold text-slate-700 bg-slate-50 active:bg-slate-100 text-left cursor-pointer"
            >
              <HelpCircle className="w-4 h-4 text-slate-500 shrink-0" />
              <span>当サイトについて（運営理念）</span>
            </button>
          </div>
        </div>
      )}
    </>
  );
}
