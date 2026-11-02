import React from 'react';
import { 
  Building2, 
  MapPin, 
  ArrowRight, 
  Sparkles, 
  Landmark, 
  Compass,
  HelpCircle, 
  BookOpen, 
  ExternalLink,
  BookmarkCheck,
  Coins,
  Flag
} from 'lucide-react';

export default function PortalTopView({ onSelectCity, onOpenAbout, onOpenGuide, onOpenMethodology }) {
  
  // 路線図マップの都市データ定義
  const mapNodes = [
    { code: 'kobe', name: '神戸', label: '運用中', bg: 'bg-teal-500', ring: 'ring-teal-200', text: 'text-teal-700', badge: 'bg-teal-50 text-teal-700 border-teal-200' },
    { code: 'osaka', name: '大阪', label: '運用中', bg: 'bg-blue-500', ring: 'ring-blue-200', text: 'text-blue-700', badge: 'bg-blue-50 text-blue-700 border-blue-200' },
    { code: 'kyoto', name: '京都', label: '運用中', bg: 'bg-indigo-500', ring: 'ring-indigo-200', text: 'text-indigo-700', badge: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
    { code: 'nagoya', name: '名古屋', label: '運用中', bg: 'bg-amber-500', ring: 'ring-amber-200', text: 'text-amber-700', badge: 'bg-amber-50 text-amber-700 border-amber-200' },
    { code: 'yokohama', name: '横浜', label: '先行公開', bg: 'bg-cyan-500', ring: 'ring-cyan-200', text: 'text-cyan-700', badge: 'bg-cyan-50 text-cyan-700 border-cyan-200' },
    { code: 'future', name: '他エリア', label: 'Next', bg: 'bg-slate-300', ring: '', text: 'text-slate-400', badge: 'bg-slate-50 text-slate-400 border-slate-200' },
  ];

  // ミニマップからのスムーズスクロール＆ハイライト連動処理
  const scrollToCard = (code) => {
    if (code === 'future') return;
    const el = document.getElementById(`city-card-${code}`);
    if (el) {
      const y = el.getBoundingClientRect().top + window.scrollY - 80; // ヘッダー分オフセット
      window.scrollTo({ top: y, behavior: 'smooth' });
      
      // ハイライト用のクラスを一時的に付与
      el.classList.add('ring-4', 'ring-indigo-500', 'scale-[1.02]', 'shadow-2xl');
      setTimeout(() => {
        el.classList.remove('ring-4', 'ring-indigo-500', 'scale-[1.02]', 'shadow-2xl');
      }, 1200);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans selection:bg-indigo-500 selection:text-white flex flex-col justify-between">
      
      {/* グローバルヘッダー (スマホでの崩れを防止したレスポンシブ設計) */}
      <header className="bg-white/95 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-50 shadow-2xs">
        <div className="max-w-6xl mx-auto px-3 sm:px-6 h-14 sm:h-16 flex items-center justify-between">
          
          {/* ロゴ */}
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-black text-sm sm:text-lg shadow-sm shrink-0">
              M
            </div>
            <div className="shrink-0">
              <div className="flex items-center gap-2">
                <span className="font-black text-slate-900 text-sm sm:text-base tracking-tight whitespace-nowrap">議会のミカタ</span>
                <span className="hidden sm:inline-block text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-100 px-2 py-0.5 rounded-full whitespace-nowrap">
                  ポータル
                </span>
              </div>
              <p className="text-[9px] sm:text-[10px] text-slate-400 font-bold whitespace-nowrap mt-0.5">
                二元代表制 政策プロセス可視化基盤
              </p>
            </div>
          </div>

          {/* ナビゲーション (スマホ時はアイコンのみに自動圧縮) */}
          <nav className="flex items-center gap-1 sm:gap-2 text-xs font-bold text-slate-600 shrink-0">
            <button 
              onClick={onOpenGuide} 
              className="flex items-center gap-1.5 hover:text-indigo-600 p-2 sm:px-3 sm:py-2 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer shrink-0"
              title="ご利用ガイド"
            >
              <Compass className="w-5 h-5 sm:w-4 sm:h-4 shrink-0" />
              <span className="hidden sm:inline whitespace-nowrap">ガイド</span>
            </button>
            
            <button 
              onClick={onOpenAbout} 
              className="flex items-center gap-1.5 hover:text-indigo-600 p-2 sm:px-3 sm:py-2 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer shrink-0"
              title="サイトについて"
            >
              <HelpCircle className="w-5 h-5 sm:w-4 sm:h-4 shrink-0" />
              <span className="hidden sm:inline whitespace-nowrap">About</span>
            </button>
            
            <button 
              onClick={onOpenMethodology} 
              className="hidden sm:flex items-center gap-1.5 hover:text-indigo-600 px-3 py-2 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer shrink-0"
            >
              <BookOpen className="w-4 h-4 shrink-0" />
              <span className="whitespace-nowrap">仕様書</span>
            </button>
          </nav>
        </div>
      </header>

      {/* メインコンテンツ */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12 space-y-12 sm:space-y-16 flex-grow w-full">
        
        {/* ヒーローセクション */}
        <section className="text-center space-y-5 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-[10px] sm:text-xs font-black shadow-2xs">
            <Sparkles className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
            <span>政令指定都市 議会・首長政策トレーサビリティ基盤</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-black text-slate-900 tracking-tight leading-tight">
            AIは入口。<br className="sm:hidden" />判断するのは市民です。
          </h1>

          <p className="text-xs sm:text-base text-slate-600 font-medium leading-relaxed px-2">
            首長公約の予算化進捗・議会での採決態度・議員の質疑ログを、主観的な格付けを排して客観的に構造化。原本（公式会議録等）への直結により、有権者自らが一次情報で確かめられるオープンデータ基盤です。
          </p>
        </section>

        {/* 路線図風ネットワークマップ (新規追加) */}
        <section className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-sm sm:text-base font-black text-slate-900 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-indigo-500" />
              5 CITIES NETWORK
            </h2>
            <span className="hidden sm:inline-block text-xs font-bold text-slate-400 bg-slate-50 border border-slate-100 px-2.5 py-1 rounded-md">
              タップでダッシュボード詳細へスキップ
            </span>
            <span className="sm:hidden text-[10px] font-bold text-slate-400">横スクロール対応 →</span>
          </div>

          <div className="relative w-full overflow-x-auto pb-4 -mx-2 px-2 sm:mx-0 sm:px-0" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
            <div className="min-w-[550px] sm:w-full flex items-center justify-between relative px-6">
              
              {/* ベースの接続ライン */}
              <div className="absolute left-10 right-10 top-5 h-1 bg-slate-200 rounded-full" />
              
              {/* 各都市のノード (ピン) */}
              {mapNodes.map((node) => {
                const isFuture = node.code === 'future';
                return (
                  <div 
                    key={node.code} 
                    onClick={() => scrollToCard(node.code)}
                    className={`relative flex flex-col items-center gap-3 z-10 ${isFuture ? 'cursor-default opacity-60' : 'cursor-pointer group'}`}
                  >
                    {/* 丸ピン */}
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center border-4 border-white shadow-sm transition-all duration-300
                      ${node.bg} 
                      ${!isFuture && 'group-hover:scale-110 group-hover:ring-4 ' + node.ring}
                    `}>
                      <Building2 className="w-4 h-4 text-white" />
                    </div>

                    {/* テキスト情報 */}
                    <div className="text-center space-y-1.5">
                      <div className={`text-sm font-black ${node.text} ${!isFuture && 'group-hover:text-indigo-600'} transition-colors`}>
                        {node.name}
                      </div>
                      <div className={`text-[9px] sm:text-[10px] font-bold px-2 py-0.5 rounded-full border ${node.badge} whitespace-nowrap`}>
                        {node.label}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* 自治体選択グリッド（5都市） */}
        <section className="space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-200 pb-3">
            <div>
              <h2 className="text-lg font-black text-slate-900 flex items-center gap-2">
                <Landmark className="w-5 h-5 text-indigo-600" />
                運用中ダッシュボード
              </h2>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            
            {/* ① 京都市会カード */}
            <div 
              id="city-card-kyoto"
              onClick={() => onSelectCity('kyoto')}
              className="bg-white rounded-3xl border-2 border-slate-200 hover:border-indigo-500 p-6 shadow-xs hover:shadow-lg transition-all duration-500 cursor-pointer group flex flex-col justify-between space-y-5 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-50/50 rounded-bl-full pointer-events-none -mr-6 -mt-6 group-hover:scale-110 transition-transform" />
              
              <div className="space-y-4 relative z-10">
                <div className="flex items-center justify-between">
                  <span className="px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-[10px] sm:text-xs font-black">
                    運用中
                  </span>
                  <span className="text-xs font-mono font-bold text-slate-400">/kyoto/</span>
                </div>

                <div>
                  <h3 className="text-2xl font-black text-slate-900 group-hover:text-indigo-600 transition-colors">
                    京都市会
                  </h3>
                  <p className="text-[10px] sm:text-xs text-slate-500 font-bold mt-1">Kyoto City Council</p>
                </div>

                <p className="text-[11px] sm:text-xs text-slate-600 leading-relaxed font-medium">
                  本会議・全委員会の12万発言・5,100超の質疑スレッドを網羅。全67議員の看板公約と議決照合、市長政策トラッカーを完備。
                </p>

                <div className="grid grid-cols-3 gap-1.5 pt-1 text-center">
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">現職議員</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">67名</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">質疑スレッド</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">5,100+</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">議案賛否</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">300件</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-slate-100 relative z-10">
                <span className="text-[11px] sm:text-xs font-bold text-indigo-600 group-hover:underline">ダッシュボードを開く</span>
                <div className="w-7 h-7 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            </div>

            {/* ② 大阪市会カード */}
            <div 
              id="city-card-osaka"
              onClick={() => onSelectCity('osaka')}
              className="bg-white rounded-3xl border-2 border-slate-200 hover:border-blue-500 p-6 shadow-xs hover:shadow-lg transition-all duration-500 cursor-pointer group flex flex-col justify-between space-y-5 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-50/50 rounded-bl-full pointer-events-none -mr-6 -mt-6 group-hover:scale-110 transition-transform" />

              <div className="space-y-4 relative z-10">
                <div className="flex items-center justify-between">
                  <span className="px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-700 text-[10px] sm:text-xs font-black">
                    運用中
                  </span>
                  <span className="text-xs font-mono font-bold text-slate-400">/osaka/</span>
                </div>

                <div>
                  <h3 className="text-2xl font-black text-slate-900 group-hover:text-blue-600 transition-colors">
                    大阪市会
                  </h3>
                  <p className="text-[10px] sm:text-xs text-slate-500 font-bold mt-1">Osaka City Council</p>
                </div>

                <p className="text-[11px] sm:text-xs text-slate-600 leading-relaxed font-medium">
                  本会議および全委員会の1,260超の最新質疑スレッドを構造化。現職81議員の論戦スタイル、万博・副首都ビジョン等を収録。
                </p>

                <div className="grid grid-cols-3 gap-1.5 pt-1 text-center">
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">現職議員</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">81名</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">質疑スレッド</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">1,260+</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">対立議案分析</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">網羅</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-slate-100 relative z-10">
                <span className="text-[11px] sm:text-xs font-bold text-blue-600 group-hover:underline">ダッシュボードを開く</span>
                <div className="w-7 h-7 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors">
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            </div>

            {/* ③ 名古屋市会カード */}
            <div 
              id="city-card-nagoya"
              onClick={() => onSelectCity('nagoya')}
              className="bg-white rounded-3xl border-2 border-slate-200 hover:border-amber-500 p-6 shadow-xs hover:shadow-lg transition-all duration-500 cursor-pointer group flex flex-col justify-between space-y-5 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-amber-50/50 rounded-bl-full pointer-events-none -mr-6 -mt-6 group-hover:scale-110 transition-transform" />

              <div className="space-y-4 relative z-10">
                <div className="flex items-center justify-between">
                  <span className="px-3 py-1 rounded-full bg-amber-50 border border-amber-100 text-amber-700 text-[10px] sm:text-xs font-black">
                    運用中
                  </span>
                  <span className="text-xs font-mono font-bold text-slate-400">/nagoya/</span>
                </div>

                <div>
                  <h3 className="text-2xl font-black text-slate-900 group-hover:text-amber-600 transition-colors">
                    名古屋市会
                  </h3>
                  <p className="text-[10px] sm:text-xs text-slate-500 font-bold mt-1">Nagoya City Council</p>
                </div>

                <p className="text-[11px] sm:text-xs text-slate-600 leading-relaxed font-medium">
                  電子採決ログ・「名古屋城木造復元」等の進捗トラッカー。現職68議員の賛否と質疑をオープンデータとして可視化します。
                </p>

                <div className="grid grid-cols-3 gap-1.5 pt-1 text-center">
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">現職議員</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">68名</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">質疑スレッド</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">準備中</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">対立議案分析</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">網羅</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-slate-100 relative z-10">
                <span className="text-[11px] sm:text-xs font-bold text-amber-600 group-hover:underline">ダッシュボードを開く</span>
                <div className="w-7 h-7 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center group-hover:bg-amber-600 group-hover:text-white transition-colors">
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            </div>

            {/* ④ 横浜市会カード */}
            <div 
              id="city-card-yokohama"
              onClick={() => onSelectCity('yokohama')}
              className="bg-white rounded-3xl border-2 border-slate-200 hover:border-cyan-500 p-6 shadow-xs hover:shadow-lg transition-all duration-500 cursor-pointer group flex flex-col justify-between space-y-5 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-50/50 rounded-bl-full pointer-events-none -mr-6 -mt-6 group-hover:scale-110 transition-transform" />

              <div className="space-y-4 relative z-10">
                <div className="flex items-center justify-between">
                  <span className="px-3 py-1 rounded-full bg-cyan-50 border border-cyan-100 text-cyan-700 text-[10px] sm:text-xs font-black flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse" />
                    先行公開
                  </span>
                  <span className="text-xs font-mono font-bold text-slate-400">/yokohama/</span>
                </div>

                <div>
                  <h3 className="text-2xl font-black text-slate-900 group-hover:text-cyan-600 transition-colors">
                    横浜市会
                  </h3>
                  <p className="text-[10px] sm:text-xs text-slate-500 font-bold mt-1">Yokohama City Council</p>
                </div>

                <p className="text-[11px] sm:text-xs text-slate-600 leading-relaxed font-medium">
                  重点12公約トラッカーと18区現職86議員名簿を先行公開。公約原本（選挙公報PDF等）と議会ログを完全バインド。
                </p>

                <div className="grid grid-cols-3 gap-1.5 pt-1 text-center">
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">現職議員</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">86名</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">重点公約</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">12件</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">議会論戦</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">移行期</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-slate-100 relative z-10">
                <span className="text-[11px] sm:text-xs font-bold text-cyan-600 group-hover:underline">ダッシュボードを開く</span>
                <div className="w-7 h-7 rounded-full bg-cyan-50 text-cyan-600 flex items-center justify-center group-hover:bg-cyan-600 group-hover:text-white transition-colors">
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            </div>

            {/* ⑤ 神戸市会カード */}
            <div 
              id="city-card-kobe"
              onClick={() => onSelectCity('kobe')}
              className="bg-white rounded-3xl border-2 border-slate-200 hover:border-teal-500 p-6 shadow-xs hover:shadow-lg transition-all duration-500 cursor-pointer group flex flex-col justify-between space-y-5 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-teal-50/50 rounded-bl-full pointer-events-none -mr-6 -mt-6 group-hover:scale-110 transition-transform" />

              <div className="space-y-4 relative z-10">
                <div className="flex items-center justify-between">
                  <span className="px-3 py-1 rounded-full bg-teal-50 border border-teal-100 text-teal-700 text-[10px] sm:text-xs font-black">
                    運用中
                  </span>
                  <span className="text-xs font-mono font-bold text-slate-400">/kobe/</span>
                </div>

                <div>
                  <h3 className="text-2xl font-black text-slate-900 group-hover:text-teal-600 transition-colors">
                    神戸市会
                  </h3>
                  <p className="text-[10px] sm:text-xs text-slate-500 font-bold mt-1">Kobe City Council</p>
                </div>

                <p className="text-[11px] sm:text-xs text-slate-600 leading-relaxed font-medium">
                  「神戸2025ビジョン」主要公約の予算原本トラッカー。全63議員の公式顔写真、選挙公報看板公約と議決ログを完全配備。
                </p>

                <div className="grid grid-cols-3 gap-1.5 pt-1 text-center">
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">現職議員</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">63名</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">重点政策</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">5分野</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 block">公報原本</span>
                    <span className="text-xs sm:text-sm font-black text-slate-900">100%</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-slate-100 relative z-10">
                <span className="text-[11px] sm:text-xs font-bold text-teal-600 group-hover:underline">ダッシュボードを開く</span>
                <div className="w-7 h-7 rounded-full bg-teal-50 text-teal-600 flex items-center justify-center group-hover:bg-teal-600 group-hover:text-white transition-colors">
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            </div>

          </div>
        </section>

        {/* 3つの基盤機能 */}
        <section className="space-y-6 pt-4">
          <div className="text-center space-y-2">
            <h2 className="text-xl sm:text-2xl font-black text-slate-900">
              政策トレーサビリティを支える3つの柱
            </h2>
            <p className="text-[11px] sm:text-xs text-slate-500">主観的な合否判定を排し、公開された公文書ファクトのみを突き合わせます</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 space-y-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center">
                <BookmarkCheck className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-black text-slate-900">議員の言行一致トラッカー</h3>
              <p className="text-xs text-slate-600 leading-relaxed font-normal">
                選挙公報原本から抽出した看板公約と、議会での実際の採決態度（賛成/反対）および関連質疑ログを直接照合。言行一致のファクトを可視化します。
              </p>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 space-y-3">
              <div className="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center">
                <Coins className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-black text-slate-900">首長政策×予算定量検証</h3>
              <p className="text-xs text-slate-600 leading-relaxed font-normal">
                首長の主要公約が総合計画に位置づけられ、主要事業説明書でいくら予算化（千円単位）されたかを追跡。条例提出から議決結果まで網羅します。
              </p>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 space-y-3">
              <div className="w-9 h-9 rounded-xl bg-amber-50 border border-amber-100 text-amber-600 flex items-center justify-center">
                <Flag className="w-5 h-5 text-rose-500" />
              </div>
              <h3 className="text-sm font-black text-slate-900">原本直結とオープン監査</h3>
              <p className="text-xs text-slate-600 leading-relaxed font-normal">
                全質疑に会議録原本直リンクを完備。リンク切れや誤記は、資料横の旗マーク（⚑）から1タップで運営へ通知・自動是正できる基盤を実装しています。
              </p>
            </div>

          </div>
        </section>
      </main>

      {/* フッター */}
      <footer className="bg-white border-t border-slate-200 py-8 sm:py-10 px-4 sm:px-6 mt-12">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-[10px] sm:text-xs text-slate-500">
          <div className="space-y-1 text-center md:text-left">
            <div className="font-black text-slate-800 text-xs sm:text-sm">議会のミカタ（Gikai no Mikata）</div>
            <p>独立シビックテックプロジェクト（運営：株式会社KICKs 代表 山本健人）</p>
          </div>

          <div className="flex items-center gap-4 flex-wrap justify-center font-bold">
            <button onClick={onOpenAbout} className="hover:text-indigo-600 transition-colors cursor-pointer">About</button>
            <button onClick={onOpenMethodology} className="hover:text-indigo-600 transition-colors cursor-pointer">評価仕様書</button>
            <button onClick={onOpenGuide} className="hover:text-indigo-600 transition-colors cursor-pointer">ご利用ガイド</button>
            <a 
              href="https://github.com/ykento1011/kyoto-politician-tracker" 
              target="_blank" 
              rel="noopener noreferrer" 
              className="hover:text-indigo-600 transition-colors inline-flex items-center gap-1"
            >
              GitHub <ExternalLink className="w-3 h-3 opacity-60" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

