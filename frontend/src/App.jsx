import React, { useState, useEffect, useMemo } from 'react';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import HeroSection from './components/HeroSection';
import MainTabView from './components/MainTabView';
import SpeakerDetailView from './components/SpeakerDetailView';
import SearchResultsView from './components/SearchResultsView';
import CompareDashboard from './components/CompareDashboard';
import HighlightedThreads from './components/HighlightedThreads';
import MacroTopicMap from './components/MacroTopicMap';
import ContestedBillsView from './components/ContestedBillsView';
import TopicDetailPage from './components/TopicDetailPage';
import CategoryDetailPage from './components/CategoryDetailPage';
import TimelineModal from './components/TimelineModal';
import BillDetailModal from './components/BillDetailModal';
import AboutPage from './components/AboutPage';
import Methodology from './components/Methodology';
import GuidePage from './components/GuidePage';
import { useStatements } from './hooks/useStatements';

function getCategoryForBill(b) {
  const text = `${b.title || ''} ${b.key_conflict || ''} ${b.background || ''}`;
  if (text.includes('都市計画') || text.includes('建築') || text.includes('開発') || text.includes('住宅') || text.includes('新幹線')) return '都市再生・交通インフラ';
  if (text.includes('観光') || text.includes('宿泊税') || text.includes('産業') || text.includes('万博') || text.includes('芸術大学') || text.includes('市場')) return '産業・観光・地域経済';
  if (text.includes('医療') || text.includes('健康保険') || text.includes('国保') || text.includes('介護') || text.includes('保護') || text.includes('衛生')) return '福祉・医療・健康';
  if (text.includes('子ども') || text.includes('給食') || text.includes('学校') || text.includes('保育') || text.includes('児童')) return '子育て・教育';
  if (text.includes('予算') || text.includes('決算') || text.includes('報酬') || text.includes('給与') || text.includes('定数') || text.includes('手続')) return '財政・行革';
  if (text.includes('原発') || text.includes('温暖化') || text.includes('環境') || text.includes('下水') || text.includes('水道')) return 'くらし・環境・エネルギー';
  if (text.includes('防災') || text.includes('消防') || text.includes('災害') || text.includes('耐震')) return '防災・減災・治安';
  if (text.includes('文化') || text.includes('景観') || text.includes('世界遺産') || text.includes('歴史')) return '文化・景観・歴史';
  return '市政全般';
}

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
  const [billIssuesList, setBillIssuesList] = useState([]);
  const [issuesMap, setIssuesMap] = useState({});
  const [selectedBillForModal, setSelectedBillForModal] = useState(null);
  const [onlyContestedBills, setOnlyContestedBills] = useState(true);

  const [selectedSession, setSelectedSession] = useState('');
  const [selectedResult, setSelectedResult] = useState('');

  const [compareActive, setCompareActive] = useState(false);
  const [isGuideOpen, setIsGuideOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);
  const [isContestedViewOpen, setIsContestedViewOpen] = useState(false);
  const [contestedInitialCategory, setContestedInitialCategory] = useState('');
  const [selectedTopicId, setSelectedTopicId] = useState(null);
  const [selectedCategoryPage, setSelectedCategoryPage] = useState(null);

  useEffect(() => {
    fetch('/data/votes_summary.json')
      .then(res => (res.ok ? res.json() : []))
      .then(data => setVotesData(data))
      .catch(err => console.error('Failed to load votes:', err));

    fetch('/data/bill_issues.json')
      .then(res => (res.ok ? res.json() : []))
      .then(data => {
        setBillIssuesList(data);
        const map = {};
        data.forEach(item => {
          map[`${item.session_name}_${item.bill_number}`] = item;
        });
        setIssuesMap(map);
      })
      .catch(err => console.error('Failed to load bill issues:', err));
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const view = params.get('view');
      const pathname = window.location.pathname;

      if (pathname === '/guide' || view === 'guide') {
        setIsGuideOpen(true);
        setIsAboutOpen(false);
        setIsMethodologyOpen(false);
        setIsContestedViewOpen(false);
      } else if (pathname === '/about' || view === 'about') {
        setIsAboutOpen(true);
        setIsGuideOpen(false);
        setIsMethodologyOpen(false);
        setIsContestedViewOpen(false);
      } else if (pathname === '/methodology' || view === 'methodology') {
        setIsMethodologyOpen(true);
        setIsGuideOpen(false);
        setIsAboutOpen(false);
        setIsContestedViewOpen(false);
      } else {
        setIsGuideOpen(false);
        setIsAboutOpen(false);
        setIsMethodologyOpen(false);
        setIsContestedViewOpen(false);
      }
    };

    const handleHashChange = () => {
      const hash = window.location.hash;
      if (hash.startsWith('#topic=')) {
        setSelectedTopicId(hash.replace('#topic=', ''));
        setSelectedCategoryPage(null);
      } else if (hash.startsWith('#category=')) {
        setSelectedCategoryPage(decodeURIComponent(hash.replace('#category=', '')));
        setSelectedTopicId(null);
      } else {
        setSelectedTopicId(null);
        setSelectedCategoryPage(null);
      }
    };

    handlePopState();
    handleHashChange();

    window.addEventListener('popstate', handlePopState);
    window.addEventListener('hashchange', handleHashChange);
    return () => {
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('hashchange', handleHashChange);
    };
  }, []);

  const resetAllSubViews = () => {
    clearSpeakerAndCompare();
    setCompareActive(false);
    setIsGuideOpen(false);
    setIsAboutOpen(false);
    setIsMethodologyOpen(false);
    setIsContestedViewOpen(false);
    setSelectedTopicId(null);
    setSelectedCategoryPage(null);
  };

  const handleOpenCategoryDetail = (catName) => {
    resetAllSubViews();
    setSelectedCategoryPage(catName);
    window.location.hash = `category=${encodeURIComponent(catName)}`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenTopicDetail = (topicId) => {
    resetAllSubViews();
    setSelectedTopicId(topicId);
    window.location.hash = `topic=${topicId}`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const navigateToView = (viewName) => {
    resetAllSubViews();
    window.location.hash = '';
    const url = new URL(window.location);
    url.searchParams.set('view', viewName);
    window.history.pushState({}, '', url);

    if (viewName === 'guide') setIsGuideOpen(true);
    if (viewName === 'about') setIsAboutOpen(true);
    if (viewName === 'methodology') setIsMethodologyOpen(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const closeViewAndResetUrl = () => {
    setIsGuideOpen(false);
    setIsAboutOpen(false);
    setIsMethodologyOpen(false);
    const url = new URL(window.location);
    url.searchParams.delete('view');
    window.history.pushState({}, '', url);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setSelectedTopicId(null);
    setSelectedCategoryPage(null);
    window.location.hash = '';
    setSubmittedQuery(searchQuery);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleKeywordClick = (keyword) => {
    setSelectedTopicId(null);
    setSelectedCategoryPage(null);
    window.location.hash = '';
    setSearchQuery(keyword);
    setSubmittedQuery(keyword);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const getIssueCountForCategory = useMemo(() => {
    const counts = {};
    billIssuesList.forEach(b => {
      const cat = getCategoryForBill(b);
      counts[cat] = (counts[cat] || 0) + 1;
    });
    return (catName) => counts[catName] || 0;
  }, [billIssuesList]);

  const uniqueSessions = useMemo(() => [...new Set((votesData || []).map(b => b.session_name).filter(Boolean))], [votesData]);
  const uniqueResults = useMemo(() => [...new Set((votesData || []).map(b => b.result).filter(Boolean))], [votesData]);

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
    if (selectedSession) list = list.filter(b => b.session_name === selectedSession);
    if (selectedResult) list = list.filter(b => b.result === selectedResult);
    if (onlyContestedBills) {
      list = list.filter(bill => {
        const votes = Object.values(bill.votes || {});
        return votes.includes('賛成') && votes.includes('反対');
      });
    }
    return list;
  }, [votesData, submittedQuery, selectedSession, selectedResult, onlyContestedBills]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        <p className="text-sm font-black text-slate-500 tracking-wider">京都市議会データを読み込み中...</p>
      </div>
    );
  }

  // --- サブページ条件分岐 ---
  if (isGuideOpen) return <GuidePage onBack={closeViewAndResetUrl} onOpenMethodology={() => navigateToView('methodology')} onOpenAbout={() => navigateToView('about')} />;
  if (selectedTopicId) return <TopicDetailPage topicId={selectedTopicId} onBack={() => { setSelectedTopicId(null); window.location.hash = ''; }} />;
  if (selectedCategoryPage) {
    return (
      <CategoryDetailPage
        categoryName={selectedCategoryPage}
        onBack={() => { setSelectedCategoryPage(null); window.location.hash = ''; }}
        topicStats={topicStats}
        filteredThreads={statements.filter(s => s.category === selectedCategoryPage)}
        filteredBills={votesData.filter(b => getCategoryForBill(b) === selectedCategoryPage)}
        speakerStats={speakerStats}
        issuesMap={issuesMap}
        onlyContestedBills={onlyContestedBills}
        setOnlyContestedBills={setOnlyContestedBills}
        onSpeakerClick={handleSpeakerClick}
        onViewContext={handleViewContext}
        onSelectBill={setSelectedBillForModal}
        onOpenMethodology={() => navigateToView('methodology')}
        onOpenTopicDetail={handleOpenTopicDetail}
      />
    );
  }
  if (isAboutOpen) return <AboutPage onBack={closeViewAndResetUrl} onOpenMethodology={() => navigateToView('methodology')} />;
  if (isMethodologyOpen) return <Methodology onBack={closeViewAndResetUrl} />;

  // 激戦議案ビュー
  if (isContestedViewOpen) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        <Navbar onLogoClick={() => setIsContestedViewOpen(false)} onOpenGuide={() => navigateToView('guide')} onOpenAbout={() => navigateToView('about')} onOpenMethodology={() => navigateToView('methodology')} onOpenCompare={() => { setIsContestedViewOpen(false); setCompareActive(true); }} isCompareMode={false} />
        <ContestedBillsView initialCategory={contestedInitialCategory} billIssues={billIssuesList} votesData={votesData} onClose={() => setIsContestedViewOpen(false)} onSpeakerClick={handleSpeakerClick} />
        <Footer onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  // 議員比較ダッシュボード
  if (compareActive || compareList.length >= 2) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        <Navbar onLogoClick={() => setCompareActive(false)} onOpenGuide={() => navigateToView('guide')} onOpenAbout={() => navigateToView('about')} onOpenMethodology={() => navigateToView('methodology')} onOpenCompare={() => {}} isCompareMode={true} />
        <CompareDashboard compareList={compareList} allSpeakers={speakerStats} onAddSpeaker={(spk) => { if (compareList.length < 3) setCompareList([...compareList, spk]); }} onRemoveSpeaker={(spk) => setCompareList(compareList.filter(s => s.speaker !== spk.speaker))} onClose={() => setCompareActive(false)} onViewContext={handleViewContext} onSpeakerClick={handleSpeakerClick} votesData={votesData} issuesMap={issuesMap} onSelectBill={setSelectedBillForModal} />
        <BillDetailModal isOpen={Boolean(selectedBillForModal)} onClose={() => setSelectedBillForModal(null)} bill={selectedBillForModal} issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null} speakerStats={speakerStats} onSpeakerClick={(spk) => { setSelectedBillForModal(null); handleSpeakerClick(spk); }} />
        <TimelineModal isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
        <Footer onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  // 議員個別詳細ビュー
  if (selectedSpeaker) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        <Navbar onLogoClick={clearSpeakerAndCompare} onOpenGuide={() => navigateToView('guide')} onOpenAbout={() => navigateToView('about')} onOpenMethodology={() => navigateToView('methodology')} onOpenCompare={() => { clearSpeakerAndCompare(); setCompareActive(true); }} isCompareMode={false} />
        <SpeakerDetailView selectedSpeaker={selectedSpeaker} speakerStats={speakerStats} speakerFilteredThreads={speakerFilteredThreads} topicStats={topicStats} speakerCategory={speakerCategory} setSpeakerCategory={setSpeakerCategory} speakerSort={speakerSort} setSpeakerSort={setSpeakerSort} votesData={votesData} issuesMap={issuesMap} onOpenCompare={(spk) => { setCompareList([spk]); setCompareActive(true); window.scrollTo({ top: 0, behavior: 'smooth' }); }} onBack={clearSpeakerAndCompare} onSpeakerClick={handleSpeakerClick} onViewContext={handleViewContext} onOpenMethodology={() => navigateToView('methodology')} onSelectBill={setSelectedBillForModal} />
        <TimelineModal isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
        <BillDetailModal isOpen={Boolean(selectedBillForModal)} onClose={() => setSelectedBillForModal(null)} bill={selectedBillForModal} issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null} speakerStats={speakerStats} onSpeakerClick={handleSpeakerClick} />
        <Footer onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  // キーワード検索結果画面
  if (submittedQuery.trim() !== '') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        <Navbar onLogoClick={() => { setSearchQuery(''); setSubmittedQuery(''); }} onOpenGuide={() => navigateToView('guide')} onOpenAbout={() => navigateToView('about')} onOpenMethodology={() => navigateToView('methodology')} onOpenCompare={() => { clearSpeakerAndCompare(); setCompareActive(true); }} isCompareMode={false} />
        <SearchResultsView submittedQuery={submittedQuery} onClearSearch={() => { setSearchQuery(''); setSubmittedQuery(''); }} filteredThreads={filteredThreads} filteredBills={filteredBills} filteredSpeakers={filteredSpeakers} speakerStats={speakerStats} issuesMap={issuesMap} onlyContestedBills={onlyContestedBills} setOnlyContestedBills={setOnlyContestedBills} onSpeakerClick={handleSpeakerClick} onViewContext={handleViewContext} onOpenCompare={(spk) => { setCompareList([spk]); setCompareActive(true); }} onSelectBill={setSelectedBillForModal} onOpenMethodology={() => navigateToView('methodology')} onOpenTopicDetail={handleOpenTopicDetail} />
        <BillDetailModal isOpen={Boolean(selectedBillForModal)} onClose={() => setSelectedBillForModal(null)} bill={selectedBillForModal} issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null} speakerStats={speakerStats} onSpeakerClick={handleSpeakerClick} />
        <TimelineModal isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
        <Footer onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  // --- トップ画面（メインポータル） ---
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between selection:bg-indigo-500 selection:text-white">
      <Navbar
        onLogoClick={() => { resetAllSubViews(); setSearchQuery(''); setSubmittedQuery(''); }}
        onOpenGuide={() => navigateToView('guide')}
        onOpenAbout={() => navigateToView('about')}
        onOpenMethodology={() => navigateToView('methodology')}
        onOpenCompare={() => { resetAllSubViews(); setCompareActive(true); }}
        isCompareMode={false}
      />

      <main className="max-w-6xl mx-auto py-8 px-6 w-full flex-grow space-y-10">
        {/* ① ヒーローセクション（検索・タグ・バナー） */}
        <HeroSection
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onSearchSubmit={handleSearchSubmit}
          onKeywordClick={handleKeywordClick}
          onOpenGuide={() => navigateToView('guide')}
        />

        {/* ② 市議会マクロ論戦マップ */}
        <MacroTopicMap
          topicStats={topicStats}
          selectedCategory={selectedCategory}
          onOpenCategoryDetail={handleOpenCategoryDetail}
          getIssueCountForCategory={getIssueCountForCategory}
          onOpenTopicDetail={handleOpenTopicDetail}
        />

        {/* ③ 注目の政策論戦ピックアップ */}
        <HighlightedThreads
          statements={statements}
          onViewContext={handleViewContext}
          onSpeakerClick={handleSpeakerClick}
          onOpenMethodology={() => navigateToView('methodology')}
        />

        {/* ④ メインタブビュー（議員一覧 / 質疑スレッド / 議案・賛否） */}
        <MainTabView
          viewMode={viewMode}
          setViewMode={setViewMode}
          filteredSpeakers={filteredSpeakers}
          filteredThreads={filteredThreads}
          filteredBills={filteredBills}
          topicStats={topicStats}
          speakerStats={speakerStats}
          selectedDistrict={selectedDistrict}
          setSelectedDistrict={setSelectedDistrict}
          selectedCategory={selectedCategory}
          setSelectedCategory={setSelectedCategory}
          sortPerspective={sortPerspective}
          setSortPerspective={setSortPerspective}
          selectedSession={selectedSession}
          setSelectedSession={setSelectedSession}
          selectedResult={selectedResult}
          setSelectedResult={setSelectedResult}
          uniqueSessions={uniqueSessions}
          uniqueResults={uniqueResults}
          onlyContestedBills={onlyContestedBills}
          setOnlyContestedBills={setOnlyContestedBills}
          issuesMap={issuesMap}
          onSpeakerClick={handleSpeakerClick}
          onOpenCompare={(spk) => { setCompareList([spk]); setCompareActive(true); }}
          onViewContext={handleViewContext}
          onSelectBill={setSelectedBillForModal}
          onOpenMethodology={() => navigateToView('methodology')}
        />
      </main>

      {/* グローバルモーダル */}
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

      <Footer onOpenMethodology={() => navigateToView('methodology')} />
    </div>
  );
}