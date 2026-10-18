import React, { useState, useEffect, useMemo } from 'react';
import { 
  Search, Sparkles, Users, MessageSquare, Scale, 
  SlidersHorizontal, X, GitCompare, ArrowUpDown 
} from 'lucide-react';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import SpeakerCard from './components/SpeakerCard';
import SpeakerDetailView from './components/SpeakerDetailView';
import SearchResultsView from './components/SearchResultsView';
import CompareDashboard from './components/CompareDashboard';
import BillsSection from './components/BillsSection';
import ThreadCard from './components/ThreadCard';
import HighlightedThreads from './components/HighlightedThreads';
import MethodologyModal from './components/MethodologyModal';
import TimelineModal from './components/TimelineModal';
import BillDetailModal from './components/BillDetailModal';
import AboutPage from './components/AboutPage';
import { useStatements } from './hooks/useStatements';

const HOT_TOPICS = [
  'オーバーツーリズム',
  '市バス',
  '中小企業支援',
  '空き家対策',
  '伝統産業',
  '子育て支援',
  '財政再建'
];

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
    setCompareList,
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

  const [votesData, setVotesData] = useState([]);
  const [issuesMap, setIssuesMap] = useState({});
  const [selectedBillForModal, setSelectedBillForModal] = useState(null);
  const [onlyContestedBills, setOnlyContestedBills] = useState(true);

  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);
  const [compareActive, setCompareActive] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);

  useEffect(() => {
    fetch('/data/votes_summary.json')
      .then(res => (res.ok ? res.json() : []))
      .then(data => setVotesData(data))
      .catch(err => console.error('Failed to load votes:', err));

    fetch('/data/bill_issues.json')
      .then(res => (res.ok ? res.json() : []))
      .then(data => {
        const map = {};
        data.forEach(item => {
          map[`${item.session_name}_${item.bill_number}`] = item;
        });
        setIssuesMap(map);
      })
      .catch(err => console.error('Failed to load bill issues:', err));
  }, []);

  useEffect(() => {
    const checkAboutRoute = () => {
      const params = new URLSearchParams(window.location.search);
      if (window.location.pathname === '/about' || params.get('view') === 'about') {
        setIsAboutOpen(true);
      } else {
        setIsAboutOpen(false);
      }
    };
    checkAboutRoute();
    window.addEventListener('popstate', checkAboutRoute);
    return () => window.removeEventListener('popstate', checkAboutRoute);
  }, []);

  const handleOpenAbout = () => {
    clearSpeakerAndCompare();
    setCompareActive(false);
    setIsMethodologyOpen(false);
    setIsAboutOpen(true);
    const url = new URL(window.location);
    url.searchParams.set('view', 'about');
    window.history.pushState({}, '', url);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCloseAbout = () => {
    setIsAboutOpen(false);
    const url = new URL(window.location);
    url.searchParams.delete('view');
    if (url.pathname === '/about') url.pathname = '/';
    window.history.pushState({}, '', url);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenMethodology = () => {
    setIsMethodologyOpen(true);
  };

  const handleCloseCompare = () => {
    setCompareActive(false);
    clearSpeakerAndCompare();
  };

  const handleAddCompareSpeaker = (speaker) => {
    if (compareList.length >= 3) {
      alert('比較できる議員は最大3名までです。');
      return;
    }
    if (!compareList.some(s => s.speaker === speaker.speaker)) {
      setCompareList([...compareList, speaker]);
    }
  };

  const handleRemoveCompareSpeaker = (speaker) => {
    setCompareList(compareList.filter(s => s.speaker !== speaker.speaker));
  };

  const handleDirectCompare = (speaker) => {
    if (!compareList.some(s => s.speaker === speaker.speaker)) {
      if (compareList.length >= 3) {
        alert('比較できる議員は最大3名までです。');
        return;
      }
      setCompareList(prev => [...prev, speaker]);
    }
    setCompareActive(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setSubmittedQuery(searchQuery);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleKeywordClick = (keyword) => {
    setSearchQuery(keyword);
    setSubmittedQuery(keyword);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setSubmittedQuery('');
  };

  const filteredBills = useMemo(() => {
    let list = votesData || [];
    if (submittedQuery.trim() !== '') {
      const q = submittedQuery.toLowerCase();
      list = list.filter(b => 
        (b.title && b.title.toLowerCase().includes(q)) ||
        (b.bill_number && b.bill_number.toLowerCase().includes(q)) ||
        (b.session_name && b.session_name.toLowerCase().includes(q))
      );
    }
    if (onlyContestedBills) {
      list = list.filter(bill => {
        const votes = Object.values(bill.votes || {});
        return votes.includes('賛成') && votes.includes('反対');
      });
    }
    return list;
  }, [votesData, submittedQuery, onlyContestedBills]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        <p className="text-sm font-black text-slate-500 tracking-wider">京都市議会データを読み込み中...</p>
      </div>
    );
  }

  // 1. Aboutページ
  if (isAboutOpen) {
    return (
      <AboutPage
        onBack={handleCloseAbout}
        onOpenMethodology={() => {
          setIsAboutOpen(false);
          handleOpenMethodology();
        }}
      />
    );
  }

  // 2. 比較画面
  if (compareActive || (isCompareMode && compareList.length >= 2)) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        <Navbar
          onLogoClick={handleCloseCompare}
          isCompareMode={true}
          onOpenAbout={handleOpenAbout}
          onOpenMethodology={handleOpenMethodology}
          onOpenCompare={() => {}}
        />
        <CompareDashboard
          compareList={compareList}
          allSpeakers={speakerStats}
          onAddSpeaker={handleAddCompareSpeaker}
          onRemoveSpeaker={handleRemoveCompareSpeaker}
          onClose={handleCloseCompare}
          onViewContext={handleViewContext}
          onSpeakerClick={handleSpeakerClick}
          votesData={votesData}
          issuesMap={issuesMap}
          onSelectBill={setSelectedBillForModal}
        />
        <BillDetailModal
          isOpen={Boolean(selectedBillForModal)}
          onClose={() => setSelectedBillForModal(null)}
          bill={selectedBillForModal}
          issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null}
          speakerStats={speakerStats}
          onSpeakerClick={(spkName) => {
            setSelectedBillForModal(null);
            handleSpeakerClick(spkName);
          }}
        />
        <TimelineModal
          isOpen={isPanelOpen}
          onClose={() => setIsPanelOpen(false)}
          selectedContext={selectedContext}
          isLoading={isLoadingContext}
        />
        <Footer onOpenMethodology={handleOpenMethodology} />
      </div>
    );
  }

  // 3. 議員詳細画面（Propsの欠落を完全復元）
  if (selectedSpeaker) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        <Navbar
          onLogoClick={() => { clearSpeakerAndCompare(); handleCloseAbout(); }}
          onOpenAbout={handleOpenAbout}
          onOpenMethodology={handleOpenMethodology}
          onOpenCompare={() => {
            clearSpeakerAndCompare();
            setCompareActive(true);
          }}
          isCompareMode={false}
        />
        <SpeakerDetailView
          selectedSpeaker={selectedSpeaker}
          speakerStats={speakerStats}
          speakerFilteredThreads={speakerFilteredThreads}
          topicStats={topicStats}
          speakerCategory={speakerCategory}
          setSpeakerCategory={setSpeakerCategory}
          speakerSort={speakerSort}
          setSpeakerSort={setSpeakerSort}
          votesData={votesData}
          issuesMap={issuesMap}
          onOpenCompare={handleDirectCompare}
          onBack={clearSpeakerAndCompare}
          onSpeakerClick={handleSpeakerClick}
          onViewContext={handleViewContext}
          onOpenMethodology={handleOpenMethodology}
          onSelectBill={setSelectedBillForModal}
        />
        <TimelineModal
          isOpen={isPanelOpen}
          onClose={() => setIsPanelOpen(false)}
          selectedContext={selectedContext}
          isLoading={isLoadingContext}
        />
        <BillDetailModal
          isOpen={Boolean(selectedBillForModal)}
          onClose={() => setSelectedBillForModal(null)}
          bill={selectedBillForModal}
          issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null}
          speakerStats={speakerStats}
          onSpeakerClick={handleSpeakerClick}
        />
        <MethodologyModal
          isOpen={isMethodologyOpen}
          onClose={() => setIsMethodologyOpen(false)}
        />
        <Footer onOpenMethodology={handleOpenMethodology} />
      </div>
    );
  }

  // 4. 検索結果画面
  if (submittedQuery.trim() !== '') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        <Navbar
          onLogoClick={() => {
            handleClearSearch();
            clearSpeakerAndCompare();
          }}
          onOpenAbout={handleOpenAbout}
          onOpenMethodology={handleOpenMethodology}
          onOpenCompare={() => {
            clearSpeakerAndCompare();
            setCompareActive(true);
          }}
          isCompareMode={false}
        />
        <SearchResultsView
          submittedQuery={submittedQuery}
          onClearSearch={handleClearSearch}
          filteredThreads={filteredThreads}
          filteredBills={filteredBills}
          filteredSpeakers={filteredSpeakers}
          speakerStats={speakerStats}
          issuesMap={issuesMap}
          onlyContestedBills={onlyContestedBills}
          setOnlyContestedBills={setOnlyContestedBills}
          onSpeakerClick={handleSpeakerClick}
          onViewContext={handleViewContext}
          onOpenCompare={handleDirectCompare}
          onSelectBill={setSelectedBillForModal}
          onOpenMethodology={handleOpenMethodology}
        />
        <BillDetailModal
          isOpen={Boolean(selectedBillForModal)}
          onClose={() => setSelectedBillForModal(null)}
          bill={selectedBillForModal}
          issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null}
          speakerStats={speakerStats}
          onSpeakerClick={handleSpeakerClick}
        />
        <TimelineModal
          isOpen={isPanelOpen}
          onClose={() => setIsPanelOpen(false)}
          selectedContext={selectedContext}
          isLoading={isLoadingContext}
        />
        <MethodologyModal
          isOpen={isMethodologyOpen}
          onClose={() => setIsMethodologyOpen(false)}
        />
        <Footer onOpenMethodology={handleOpenMethodology} />
      </div>
    );
  }

  // 5. トップ画面
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between selection:bg-indigo-500 selection:text-white">
      <Navbar
        onLogoClick={() => {
          clearSpeakerAndCompare();
          handleClearSearch();
          setCompareActive(false);
        }}
        onOpenAbout={handleOpenAbout}
        onOpenMethodology={handleOpenMethodology}
        onOpenCompare={() => {
          clearSpeakerAndCompare();
          setCompareActive(true);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
        isCompareMode={false}
      />

      <main className="max-w-6xl mx-auto py-8 px-6 w-full flex-grow space-y-10">
        <section className="text-center py-6 md:py-10 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-black shadow-2xs">
            <Sparkles className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
            京都市議会 公開データ × 生成AI客観分析
          </div>
          <h1 className="text-3xl md:text-5xl font-black text-slate-900 tracking-tight leading-tight">
            対話がわかる。政策が見える。
          </h1>
          <p className="text-xs md:text-sm text-slate-500 max-w-xl mx-auto leading-relaxed">
            12万件超の発言記録を構造化。文字数や登壇回数では見えない「政策提言の密度と個性」を中立なAIルーブリック評価で可視化します。
          </p>

          <div className="max-w-xl mx-auto pt-2">
            <form onSubmit={handleSearchSubmit} className="relative flex items-center">
              <Search className="w-5 h-5 text-slate-400 absolute left-4 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="論点、キーワード、議員名で議会全体を横断検索..."
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
              {HOT_TOPICS.map((topic) => (
                <button
                  key={topic}
                  onClick={() => handleKeywordClick(topic)}
                  className="px-2.5 py-1 rounded-lg bg-white hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 text-slate-600 hover:text-indigo-600 text-[11px] font-bold transition-all cursor-pointer shadow-2xs"
                >
                  {topic}
                </button>
              ))}
            </div>
          </div>
        </section>

        <HighlightedThreads
          statements={statements}
          onViewContext={handleViewContext}
          onSpeakerClick={handleSpeakerClick}
        />

        <section className="space-y-6">
          <div className="flex items-center justify-between border-b border-slate-200 pb-px overflow-x-auto hide-scrollbar">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setViewMode('speakers')}
                className={`flex items-center px-5 py-3 text-sm font-black whitespace-nowrap transition-colors border-b-2 cursor-pointer ${
                  viewMode === 'speakers'
                    ? 'border-indigo-600 text-indigo-700 bg-indigo-50/50'
                    : 'border-transparent text-slate-500 hover:bg-slate-50'
                }`}
              >
                <Users className="w-4 h-4 mr-2" />
                議員一覧 ({filteredSpeakers.length})
              </button>
              <button
                onClick={() => setViewMode('threads')}
                className={`flex items-center px-5 py-3 text-sm font-black whitespace-nowrap transition-colors border-b-2 cursor-pointer ${
                  viewMode === 'threads'
                    ? 'border-indigo-600 text-indigo-700 bg-indigo-50/50'
                    : 'border-transparent text-slate-500 hover:bg-slate-50'
                }`}
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                質疑スレッド ({filteredThreads.length})
              </button>
              <button
                onClick={() => setViewMode('bills')}
                className={`flex items-center px-5 py-3 text-sm font-black whitespace-nowrap transition-colors border-b-2 cursor-pointer ${
                  viewMode === 'bills'
                    ? 'border-indigo-600 text-indigo-700 bg-indigo-50/50'
                    : 'border-transparent text-slate-500 hover:bg-slate-50'
                }`}
              >
                <Scale className="w-4 h-4 mr-2" />
                議案・賛否の記録 ({filteredBills.length})
              </button>
            </div>
          </div>

          {viewMode !== 'bills' && (
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 flex-wrap">
                <SlidersHorizontal className="w-4 h-4 text-slate-400 mr-1" />
                <select
                  value={selectedDistrict}
                  onChange={(e) => setSelectedDistrict(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-bold text-slate-700 outline-none cursor-pointer"
                >
                  <option value="">すべての選挙区（行政区）</option>
                  {['北区', '上京区', '左京区', '中京区', '東山区', '下京区', '南区', '右京区', '西京区', '伏見区', '山科区'].map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>

                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-bold text-slate-700 outline-none cursor-pointer"
                >
                  <option value="">すべての政策分野</option>
                  {topicStats.map(t => (
                    <option key={t.name} value={t.name}>{t.name} ({t.count}件)</option>
                  ))}
                </select>

                {(selectedDistrict || selectedCategory) && (
                  <button
                    onClick={() => { setSelectedDistrict(''); setSelectedCategory(''); }}
                    className="text-slate-400 hover:text-rose-600 font-bold ml-1 transition-colors cursor-pointer"
                  >
                    リセット
                  </button>
                )}
              </div>

              <div className="flex items-center gap-2">
                <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                <select
                  value={sortPerspective}
                  onChange={(e) => setSortPerspective(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-bold text-slate-700 outline-none cursor-pointer"
                >
                  <option value="random">日替わりランダム（中立順）</option>
                  <option value="recent">登壇日が新しい順</option>
                  <option value="solution">具体的対案スコア順</option>
                  <option value="local_focus">地域解像度スコア順</option>
                  <option value="evidence">データ活用スコア順</option>
                  <option value="constructive">議論の進展スコア順</option>
                  {viewMode === 'speakers' && <option value="name">議員名（五十音順）</option>}
                </select>
              </div>
            </div>
          )}

          {viewMode === 'speakers' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredSpeakers.map((speaker) => (
                <SpeakerCard
                  key={speaker.speaker}
                  speaker={speaker}
                  onSpeakerClick={handleSpeakerClick}
                  onToggleCompare={toggleCompare}
                  isCompared={compareList.some(s => s.speaker === speaker.speaker)}
                  onOpenCompare={handleDirectCompare}
                />
              ))}
            </div>
          )}

          {viewMode === 'threads' && (
            <div className="space-y-6">
              {filteredThreads.map((stmt) => (
                <ThreadCard
                  key={stmt.id}
                  stmt={stmt}
                  speakerInfo={speakerStats.find(s => s.speaker === stmt.speaker)}
                  onSpeakerClick={handleSpeakerClick}
                  onViewContext={handleViewContext}
                  showSpeakerHeader={true}
                  onOpenMethodology={handleOpenMethodology}
                />
              ))}
            </div>
          )}

          {viewMode === 'bills' && (
            <BillsSection
              filteredBills={filteredBills}
              onlyContestedBills={onlyContestedBills}
              setOnlyContestedBills={setOnlyContestedBills}
              issuesMap={issuesMap}
              onSelectBill={setSelectedBillForModal}
            />
          )}
        </section>
      </main>

      {compareList.length > 0 && !isCompareMode && !compareActive && (
        <aside aria-label="選択中の議員の比較" className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-slate-900/95 backdrop-blur text-white px-5 py-3.5 rounded-2xl shadow-2xl border border-slate-700 flex items-center gap-4 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-300">比較候補:</span>
            <div className="flex items-center gap-1.5">
              {compareList.map((spk) => (
                <span
                  key={spk.speaker}
                  className="inline-flex items-center gap-1 bg-slate-800 text-white text-xs font-bold px-2.5 py-1 rounded-lg border border-slate-700"
                >
                  {spk.speaker}
                  <button
                    onClick={(e) => toggleCompare(spk, e)}
                    className="text-slate-400 hover:text-white cursor-pointer ml-1"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>
          <button
            onClick={() => {
              if (compareList.length < 2) {
                alert('2名以上の議員を選択してください。');
                return;
              }
              executeCompare();
            }}
            className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-black px-4 py-2 rounded-xl shadow-md transition-all cursor-pointer"
          >
            <GitCompare className="w-3.5 h-3.5" />
            ポリシー比較を開始 ({compareList.length}/3)
          </button>
        </aside>
      )}

      <BillDetailModal
        isOpen={Boolean(selectedBillForModal)}
        onClose={() => setSelectedBillForModal(null)}
        bill={selectedBillForModal}
        issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null}
        speakerStats={speakerStats}
        onSpeakerClick={handleSpeakerClick}
      />

      <TimelineModal
        isOpen={isPanelOpen}
        onClose={() => setIsPanelOpen(false)}
        selectedContext={selectedContext}
        isLoading={isLoadingContext}
      />

      <MethodologyModal
        isOpen={isMethodologyOpen}
        onClose={() => setIsMethodologyOpen(false)}
      />

      <Footer onOpenMethodology={handleOpenMethodology} />
    </div>
  );
}