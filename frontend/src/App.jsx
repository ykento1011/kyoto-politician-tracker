import React, { useState } from 'react';
import { 
  Users, MessageSquare, FileText, Search, Sparkles, Filter, 
  HelpCircle, Scale, ChevronRight, RefreshCw, Calendar, Database 
} from 'lucide-react';
import { useStatements } from './hooks/useStatements';
import SpeakerCard from './components/SpeakerCard';
import TimelineModal from './components/TimelineModal';
import Methodology from './components/Methodology';
import Footer from './components/Footer';

export default function App() {
  const {
    statements,
    isLoading,
    searchQuery,
    setSearchQuery,
    submittedQuery,
    setSubmittedQuery,
    selectedCategory,
    setSelectedCategory,
    selectedCommittee,
    setSelectedCommittee,
    selectedDistrict,
    setSelectedDistrict,
    sortPerspective,
    setSortPerspective,
    viewMode,
    setViewMode,
    selectedSpeaker,
    speakerCategory,
    setSpeakerCategory,
    speakerSort,
    setSpeakerSort,
    speakerFilteredThreads,
    compareList,
    isCompareMode,
    toggleCompare,
    executeCompare,
    clearSpeakerAndCompare,
    handleSpeakerClick,
    handleViewContext,
    selectedContext,
    isPanelOpen,
    setIsPanelOpen,
    isLoadingContext,
    topicStats,
    speakerStats,
    filteredSpeakers,
    filteredThreads
  } = useStatements();

  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('speakers'); // 'speakers' | 'threads' | 'bills'

  // 検索実行ハンドラー
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setSubmittedQuery(searchQuery);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* グローバルヘッダー */}
      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div 
            onClick={clearSpeakerAndCompare} 
            className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-black text-sm shadow-sm">
              京
            </div>
            <div>
              <span className="font-extrabold text-base tracking-tight text-slate-900 block leading-tight">
                京都市会議員トラッカー
              </span>
              <span className="text-[10px] text-slate-500 font-medium">現任期 公開データ分析</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsMethodologyOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg border border-slate-200 transition-colors"
            >
              <HelpCircle className="w-3.5 h-3.5 text-indigo-500" />
              <span>評価手法・データ範囲</span>
            </button>
          </div>
        </div>
      </header>

      {/* メインコンテンツ */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8 space-y-8">
        {/* ヒーローセクション */}
        <section className="text-center py-6 md:py-10 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-black shadow-2xs">
            <Sparkles className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
            京都市会 公開会議録 × 生成AI客観評価
          </div>

          <h1 className="text-3xl md:text-5xl font-black text-slate-900 tracking-tight leading-tight">
            対話がわかる。政策が見える。
          </h1>

          <p className="text-xs md:text-sm text-slate-500 max-w-xl mx-auto leading-relaxed">
            文字数や登壇回数では見えない「政策提言の具体性と議論の深さ」を中立なAIルーブリック評価で可視化します。
          </p>

          {/* 💡 データ対象期間・範囲の常時明記バッジ */}
          <div className="inline-flex flex-wrap items-center justify-center gap-2 px-4 py-2 rounded-2xl bg-white border border-slate-200 shadow-xs text-xs text-slate-600 font-bold">
            <span className="flex items-center gap-1.5 text-indigo-600">
              <Calendar className="w-3.5 h-3.5" />
              対象任期：2023年5月〜最新公開分
            </span>
            <span className="text-slate-300">|</span>
            <span className="flex items-center gap-1.5 text-slate-600">
              <Database className="w-3.5 h-3.5 text-slate-400" />
              本会議・全常任委員会・決算予算特別委員会（全12万発言・5,100超の質疑スレッド）
            </span>
          </div>
        </section>

        {/* 検索・フィルターエリア */}
        <section className="bg-white rounded-2xl p-4 md:p-6 border border-slate-200 shadow-sm space-y-4">
          <form onSubmit={handleSearchSubmit} className="relative flex items-center">
            <Search className="absolute left-4 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="政策テーマ、議員名、キーワードで検索（例: 子育て、空き家、交通局、財政健全化）..."
              className="w-full pl-11 pr-24 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-slate-400"
            />
            <button
              type="submit"
              className="absolute right-2 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg shadow-sm transition-colors"
            >
              検索
            </button>
          </form>

          {/* タブ切り替え */}
          <div className="flex border-b border-slate-200">
            <button
              onClick={() => setActiveTab('speakers')}
              className={`flex items-center gap-2 px-5 py-3 text-xs md:text-sm font-extrabold border-b-2 transition-all ${
                activeTab === 'speakers'
                  ? 'border-indigo-600 text-indigo-600 bg-indigo-50/30'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              <Users className="w-4 h-4" />
              議員から探す ({filteredSpeakers.length}名)
            </button>
            <button
              onClick={() => setActiveTab('threads')}
              className={`flex items-center gap-2 px-5 py-3 text-xs md:text-sm font-extrabold border-b-2 transition-all ${
                activeTab === 'threads'
                  ? 'border-indigo-600 text-indigo-600 bg-indigo-50/30'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              政策質疑スレッドから探す ({filteredThreads.length}件)
            </button>
          </div>
        </section>

        {/* 議員一覧表示 */}
        {activeTab === 'speakers' && (
          <section className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-sm font-black text-slate-900 tracking-tight">
                京都市会議員一覧（現任期）
              </h2>
              <div className="text-xs text-slate-400 font-medium">
                初期表示：公平性を保つ日替わりランダム順
              </div>
            </div>

            {isLoading ? (
              <div className="py-20 text-center space-y-3">
                <RefreshCw className="w-6 h-6 animate-spin text-indigo-600 mx-auto" />
                <p className="text-xs text-slate-400 font-medium">議事録・評価データを読み込み中...</p>
              </div>
            ) : filteredSpeakers.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredSpeakers.map((speaker) => (
                  <SpeakerCard
                    key={speaker.speaker}
                    speaker={speaker}
                    onSelect={() => handleSpeakerClick(speaker.speaker)}
                    onViewTimeline={handleViewContext}
                  />
                ))}
              </div>
            ) : (
              <div className="bg-white rounded-2xl p-12 text-center border border-slate-200">
                <p className="text-sm text-slate-500 font-bold">条件に一致する議員が見つかりませんでした。</p>
              </div>
            )}
          </section>
        )}

        {/* スレッド一覧表示 */}
        {activeTab === 'threads' && (
          <section className="space-y-4">
            <h2 className="text-sm font-black text-slate-900 tracking-tight">
              政策質疑スレッド一覧（現任期）
            </h2>
            <div className="space-y-3">
              {filteredThreads.map((thread) => (
                <div 
                  key={thread.id} 
                  className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-3 hover:border-indigo-200 transition-colors"
                >
                  <div className="flex items-center justify-between text-xs text-slate-400 font-bold">
                    <span>{thread.speaker} 議員</span>
                    <span>{thread.meeting_date}</span>
                  </div>
                  <h3 className="text-sm font-extrabold text-slate-800 leading-snug">
                    {thread.meeting_title}
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-100">
                    {thread.summary || thread.statement_text}
                  </p>
                  <div className="flex justify-end pt-1">
                    <button
                      onClick={() => handleViewContext(thread)}
                      className="px-3 py-1.5 text-xs font-bold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors flex items-center gap-1"
                    >
                      <span>会議録タイムラインを見る</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>

      {/* タイムラインモーダル */}
      <TimelineModal
        isOpen={isPanelOpen}
        onClose={() => setIsPanelOpen(false)}
        selectedContext={selectedContext}
        isLoading={isLoadingContext}
      />

      {/* 評価手法モーダル */}
      <Methodology
        isOpen={isMethodologyOpen}
        onClose={() => setIsMethodologyOpen(false)}
      />

      {/* フッター */}
      <Footer />
    </div>
  );
}