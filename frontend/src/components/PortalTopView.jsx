import React from 'react';
import { 
  Building2, 
  MapPin, 
  ArrowRight, 
  Sparkles, 
  Landmark, 
  Search, 
  CheckCircle2, 
  FileText, 
  HelpCircle, 
  BookOpen, 
  ChevronRight,
  ExternalLink,
  ShieldCheck,
  Award,
  Vote,
  Scale,
  Activity,
  BookmarkCheck,
  Coins,
  Flag
} from 'lucide-react';

export default function PortalTopView({ onSelectCity, onOpenAbout, onOpenGuide, onOpenMethodology }) {
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans selection:bg-indigo-500 selection:text-white flex flex-col justify-between">
      
      {/* グローバルヘッダー */}
      <header className="bg-white border-b border-slate-200/80 sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-black text-lg shadow-sm">
              M
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-black text-slate-900 text-base tracking-tight">議会のミカタ</span>
                <span className="text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-100 px-2 py-0.5 rounded-full">
                  ポータル
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-bold hidden sm:block">二元代表制の政策プロセスを可視化するシビックテック基盤</p>
            </div>
          </div>

          <nav className="flex items-center gap-2 sm:gap-3 text-xs font-bold text-slate-600">
            <button onClick={onOpenGuide} className="hover:text-indigo-600 px-2.5 py-1.5 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer">
              ご利用ガイド
            </button>
            <button onClick={onOpenAbout} className="hover:text-indigo-600 px-2.5 py-1.5 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer">
              About
            </button>
            <button onClick={onOpenMethodology} className="hover:text-indigo-600 px-2.5 py-1.5 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer">
              評価仕様書
            </button>
          </nav>
        </div>
      </header>

      {/* メインコンテンツ */}
      <main className="max-w-6xl mx-auto px-6 py-12 md:py-16 space-y-16 flex-grow w-full">
        
        {/* ヒーローセクション */}
        <section className="text-center space-y-5 max-w-3xl mx-auto pt-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-black shadow-2xs">
            <Sparkles className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
            <span>政令指定都市 議会・首長政策トレーサビリティ基盤</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-black text-slate-900 tracking-tight leading-tight">
            AIは入口。<br className="sm:hidden" />判断するのは市民です。
          </h1>

          <p className="text-sm sm:text-base text-slate-600 font-medium leading-relaxed">
            首長公約の予算化進捗・議会での採決態度・議員の質疑ログを、主観的な格付けを排して客観的に構造化。原本（PDF・公式議事録）への直結により、有権者自らが一次情報で確かめられるオープンデータ基盤です。
          </p>

          <p className="text-xs sm:text-sm font-black text-indigo-950">
            京都・大阪・名古屋・横浜の議会データを公開中
          </p>
        </section>

        {/* 自治体選択グリッド（4都市） */}
        <section className="space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-200 pb-3">
            <div>
              <h2 className="text-lg font-black text-slate-900 flex items-center gap-2">
                <Landmark className="w-5 h-5 text-indigo-600" />
                対象自治体を選択
              </h2>
              <p className="text-xs text-slate-500 font-medium">現在運用中の議会ダッシュボードへ直接アクセスできます</p>
            </div>
            <span className="text-[11px] font-mono text-slate-400 font-bold">4 CITIES ONLINE</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
            
            {/* ① 京都市会カード (京都・紫藍: indigo) */}
            <div 
              onClick={() => onSelectCity('kyoto')}
              className="bg-white rounded-3xl border-2 border-slate-200 hover:border-indigo-500 p-6 shadow-xs hover:shadow-md transition-all cursor-pointer group flex flex-col justify-between space-y-5 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-50/50 rounded-bl-full pointer-events-none -mr-6 -mt-6 group-hover:scale-110 transition-transform" />
              
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-black">
                    運用中
                  </span>
                  <span className="text-xs font-mono font-bold text-slate-400">/kyoto/</span>
                </div>

                <div>
                  <h3 className="text-2xl font-black text-slate-900 group-hover:text-indigo-600 transition-colors">
                    京都市会
                  </h3>
                  <p className="text-xs text-slate-500 font-bold mt-1">Kyoto City Council</p>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed font-medium">
                  本会議・全委員会の12万発言・5,100超の質疑スレッドを網羅。全67議員の看板公約と議決の照合、松井市長政策トラッカーを完備。
                </p>

                <div className="grid grid-cols-3 gap-1.5 pt-1 text-center">
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 block">現職議員</span>
                    <span className="text-sm font-black text-slate-900">67名</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 block">質疑スレッド</span>
                    <span className="text-sm font-black text-slate-900">5,100+</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 block">議案賛否</span>
                    <span className="text-sm font-black text-slate-900">300件</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-slate-100">
                <span className="text-xs font-bold text-indigo-600 group-hover:underline">京都市会ダッシュボードを開く</span>
                <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            </div>

            {/* ② 大阪市会カード (水都大阪・鮮青: blue) */}
            <div 
              onClick={() => onSelectCity('osaka')}
              className="bg-white rounded-3xl border-2 border-slate-200 hover:border-blue-500 p-6 shadow-xs hover:shadow-md transition-all cursor-pointer group flex flex-col justify-between space-y-5 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-50/50 rounded-bl-full pointer-events-none -mr-6 -mt-6 group-hover:scale-110 transition-transform" />

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-700 text-xs font-black">
                    運用中
                  </span>
                  <span className="text-xs font-mono font-bold text-slate-400">/osaka/</span>
                </div>

                <div>
                  <h3 className="text-2xl font-black text-slate-900 group-hover:text-blue-600 transition-colors">
                    大阪市会
                  </h3>
                  <p className="text-xs text-slate-500 font-bold mt-1">Osaka City Council</p>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed font-medium">
                  本会議および全委員会の1,260超の最新質疑スレッドを構造化。現職81議員の論戦スタイル、万博・副首都ビジョン等の重要政策、横山市長政策トラッカーを収録。
                </p>

                <div className="grid grid-cols-3 gap-1.5 pt-1 text-center">
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 block">現職議員</span>
                    <span className="text-sm font-black text-slate-900">81名</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 block">質疑スレッド</span>
                    <span className="text-sm font-black text-slate-900">1,260+</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 block">対立議案分析</span>
                    <span className="text-sm font-black text-slate-900">網羅</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-slate-100">
                <span className="text-xs font-bold text-blue-600 group-hover:underline">大阪市会ダッシュボードを開く</span>
                <div className="w-8 h-8 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors">
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            </div>

            {/* ③ 名古屋市会カード (金鯱・黄金: amber) */}
            <div 
              onClick={() => onSelectCity('nagoya')}
              className="bg-white rounded-3xl border-2 border-slate-200 hover:border-amber-500 p-6 shadow-xs hover:shadow-md transition-all cursor-pointer group flex flex-col justify-between space-y-5 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-amber-50/50 rounded-bl-full pointer-events-none -mr-6 -mt-6 group-hover:scale-110 transition-transform" />

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="px-3 py-1 rounded-full bg-amber-50 border border-amber-100 text-amber-700 text-xs font-black">
                    運用中
                  </span>
                  <span className="text-xs font-mono font-bold text-slate-400">/nagoya/</span>
                </div>

                <div>
                  <h3 className="text-2xl font-black text-slate-900 group-hover:text-amber-600 transition-colors">
                    名古屋市会
                  </h3>
                  <p className="text-xs text-slate-500 font-bold mt-1">Nagoya City Council</p>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed font-medium">
                  電子採決ログ・広沢市長「名古屋城木造復元」等の進捗トラッカー。現職68議員の賛否と質疑をオープンデータとして可視化します。
                </p>

                <div className="grid grid-cols-3 gap-1.5 pt-1 text-center">
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 block">現職議員</span>
                    <span className="text-sm font-black text-slate-900">68名</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 block">質疑スレッド</span>
                    <span className="text-sm font-black text-slate-900">準備中</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 block">対立議案分析</span>
                    <span className="text-sm font-black text-slate-900">網羅</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-slate-100">
                <span className="text-xs font-bold text-amber-600 group-hover:underline">名古屋市会ダッシュボードを開く</span>
                <div className="w-8 h-8 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center group-hover:bg-amber-600 group-hover:text-white transition-colors">
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            </div>

            {/* ④ 横浜市会カード (港湾ベイ・シアン: cyan) */}
            <div 
              onClick={() => onSelectCity('yokohama')}
              className="bg-white rounded-3xl border-2 border-slate-200 hover:border-cyan-500 p-6 shadow-xs hover:shadow-md transition-all cursor-pointer group flex flex-col justify-between space-y-5 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-50/50 rounded-bl-full pointer-events-none -mr-6 -mt-6 group-hover:scale-110 transition-transform" />

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="px-3 py-1 rounded-full bg-cyan-50 border border-cyan-100 text-cyan-700 text-xs font-black flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse" />
                    新市政先行公開
                  </span>
                  <span className="text-xs font-mono font-bold text-slate-400">/yokohama/</span>
                </div>

                <div>
                  <h3 className="text-2xl font-black text-slate-900 group-hover:text-cyan-600 transition-colors">
                    横浜市会
                  </h3>
                  <p className="text-xs text-slate-500 font-bold mt-1">Yokohama City Council</p>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed font-medium">
                  2026年10月就任の原澤敦美市長・重点12公約トラッカーと18区現職86議員名簿を先行公開。公約原本（選挙公報PDF等）完全バインド。
                </p>

                <div className="grid grid-cols-3 gap-1.5 pt-1 text-center">
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 block">現職議員</span>
                    <span className="text-sm font-black text-slate-900">86名</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 block">重点公約</span>
                    <span className="text-sm font-black text-slate-900">12件</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 block">議会論戦</span>
                    <span className="text-sm font-black text-slate-900">移行期</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-slate-100">
                <span className="text-xs font-bold text-cyan-600 group-hover:underline">横浜市会ダッシュボードを開く</span>
                <div className="w-8 h-8 rounded-full bg-cyan-50 text-cyan-600 flex items-center justify-center group-hover:bg-cyan-600 group-hover:text-white transition-colors">
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            </div>

          </div>

          {/* 順次展開案内 */}
          <div className="p-4 rounded-2xl bg-slate-100/80 border border-slate-200 text-xs text-slate-600 flex items-center justify-between flex-wrap gap-2">
            <span className="font-bold flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              対象自治体は順次拡大予定（政令指定都市・中核市等の政策・議事録パイプラインを開発中）
            </span>
            <span className="text-slate-400 font-mono text-[11px]">Expanding to more cities</span>
          </div>
        </section>

        {/* 3つの基盤機能 */}
        <section className="space-y-6">
          <div className="text-center space-y-2">
            <h2 className="text-xl sm:text-2xl font-black text-slate-900">
              政策トレーサビリティを支える3つの柱
            </h2>
            <p className="text-xs text-slate-500">主観的な合否判定を排し、公開された公文書ファクトのみを突き合わせます</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center">
                <BookmarkCheck className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-black text-slate-900">議員の言行一致トラッカー</h3>
              <p className="text-xs text-slate-600 leading-relaxed font-normal">
                選挙公報原本から抽出した看板公約と、議会での実際の採決態度（賛成/反対）および関連質疑ログを直接照合。言行一致のファクトを可視化します。
              </p>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-3">
              <div className="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center">
                <Coins className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-black text-slate-900">首長政策×予算定量検証</h3>
              <p className="text-xs text-slate-600 leading-relaxed font-normal">
                首長の主要公約が総合計画に位置づけられ、主要事業説明書でいくら予算化（千円単位）されたかを追跡。条例提出から議決結果まで網羅します。
              </p>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-3">
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
      <footer className="bg-white border-t border-slate-200 py-10 px-6 mt-12">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-xs text-slate-500">
          <div className="space-y-1 text-center md:text-left">
            <div className="font-black text-slate-800 text-sm">議会のミカタ（Gikai no Mikata）</div>
            <p>非営利・独立シビックテックプロジェクト（運営：株式会社KICKs 代表 山本健人）</p>
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
