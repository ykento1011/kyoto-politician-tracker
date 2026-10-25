const safeFetchJson = async (url) => {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const text = await res.text();
    if (text.trim().startsWith('<')) return null; // HTMLフォールバック防止
    return JSON.parse(text);
  } catch (e) {
    return null;
  }
};
import React, { useState, useEffect, useMemo, useCallback } from 'react';
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
import MayorTrackerView from './components/MayorTrackerView';
import TimelineModal from './components/TimelineModal';
import BillDetailModal from './components/BillDetailModal';
import AboutPage from './components/AboutPage';
import Methodology from './components/Methodology';
import GuidePage from './components/GuidePage';
import { useStatements } from './hooks/useStatements';
import FeedbackButton from './components/FeedbackButton';

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

function parseCurrentRoute() {
  const params = new URLSearchParams(window.location.search);
  const hash = window.location.hash || '';
  const pathname = window.location.pathname;

  if (hash.startsWith('#topic=')) {
    return { type: 'topic', topicId: hash.replace('#topic=', '') };
  }
  if (hash.startsWith('#category=')) {
    return { type: 'category', categoryName: decodeURIComponent(hash.replace('#category=', '')) };
  }

  const view = params.get('view');
  if (view === 'mayor' || pathname === '/mayor') return { type: 'mayor' };
  if (view === 'guide' || pathname === '/guide') return { type: 'guide' };
  if (view === 'about' || pathname === '/about') return { type: 'about' };
  if (view === 'methodology' || pathname === '/methodology') return { type: 'methodology' };
  if (view === 'contested' || pathname === '/contested') return { type: 'contested', category: params.get('cat') || '' };

  const compareParam = params.get('compare');
  if (compareParam !== null) {
    const names = compareParam === 'open' ? [] : compareParam.split(',').map(s => decodeURIComponent(s.trim())).filter(Boolean);
    return { type: 'compare', names };
  }

  const speakerParam = params.get('speaker');
  if (speakerParam) {
    return { type: 'speaker', speakerName: decodeURIComponent(speakerParam.trim()) };
  }

  const qParam = params.get('q');
  if (qParam) {
    return { type: 'search', query: decodeURIComponent(qParam.trim()) };
  }

  return { type: 'portal' };
}

export default function App() {
  // 💡 URLのパスから初期都市を判定（デフォルトはkyoto）
  const [cityCode] = useState(() => {
    if (typeof window !== 'undefined') {
      const path = window.location.pathname;
      const params = new URLSearchParams(window.location.search);
      if (path.startsWith('/osaka') || params.get('city') === 'osaka') {
        return 'osaka';
      }
      return 'kyoto';
    }
    return 'kyoto';
  });

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
    speakerCategory,
    setSpeakerCategory,
    speakerSort,
    setSpeakerSort,
    compareList,
    handleViewContext,
    selectedContext,
    isPanelOpen,
    setIsPanelOpen,
    isLoadingContext,
    topicStats,
    speakerStats,
    filteredSpeakers,
    filteredThreads
  } = useStatements(cityCode); // 💡 cityCode をフックに渡す

  const [votesData, setVotesData] = useState([]);
  const [billIssuesList, setBillIssuesList] = useState([]);
  const [issuesMap, setIssuesMap] = useState({});
  const [mayorTrackerData, setMayorTrackerData] = useState(null);
  const [selectedBillForModal, setSelectedBillForModal] = useState(null);
  const [onlyContestedBills, setOnlyContestedBills] = useState(true);

  const [selectedSession, setSelectedSession] = useState('');
  const [selectedResult, setSelectedResult] = useState('');

  const [currentRoute, setCurrentRoute] = useState(() => parseCurrentRoute());

  useEffect(() => {
    // 💡 都市に応じたデータをフェッチするように修正（将来的にosaka_votes_summary.json等に対応できるよう）
    const prefix = cityCode === 'kyoto' ? '' : `${cityCode}_`;

    fetch(`/data/${prefix}votes_summary.json`)
      .then(res => (res.ok ? res.json() : []))
      .then(data => setVotesData(data))
      .catch(err => console.error('Failed to load votes:', err));

    fetch(`/data/${prefix}bill_issues.json`)
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

    fetch(`/data/${prefix}mayor_tracker.json`)
      .then(res => (res.ok ? res.json() : null))
      .then(data => setMayorTrackerData(data))
      .catch(err => console.error('Failed to load mayor tracker:', err));
  }, [cityCode]);

  useEffect(() => {
    const onLocationChange = () => {
      const nextRoute = parseCurrentRoute();
      setCurrentRoute(nextRoute);

      if (nextRoute.type === 'search') {
        setSearchQuery(nextRoute.query);
        setSubmittedQuery(nextRoute.query);
      } else {
        setSubmittedQuery('');
      }
    };

    window.addEventListener('popstate', onLocationChange);
    window.addEventListener('hashchange', onLocationChange);
    window.addEventListener('app-navigate', onLocationChange);
    return () => {
      window.removeEventListener('popstate', onLocationChange);
      window.removeEventListener('hashchange', onLocationChange);
      window.removeEventListener('app-navigate', onLocationChange);
    };
  }, [setSearchQuery, setSubmittedQuery]);

  // 💡 都市に応じたSEOメタタグの動的書き換え
  useEffect(() => {
    const isOsaka = cityCode === 'osaka';

    const title = isOsaka
      ? "議会のミカタ 大阪 ｜ AIは入口。判断するのは市民です。"
      : "議会のミカタ 京都 ｜ AIは入口。判断するのは市民です。";

    const description = isOsaka
      ? "大阪市会公式会議録と議決データを客観的に構造化。現職81議員・1,260超の質疑スレッド分析、賛否が分かれた議案の記録、横山市長政策進捗トラッカー（一次資料・予算照合）により、市民が自ら確認・判断できるオープンデータ基盤。"
      : "京都市会公式会議録12万発言と議決データを客観的に構造化。4軸による質疑分析、賛否が分かれた議案の記録、選挙公報原本に基づく看板公約の照合により、市民が自ら一次情報で確認・判断できるオープンデータ・プラットフォーム。";

    const canonicalUrl = isOsaka
      ? "https://gikai-mikata.jp/osaka"
      : "https://gikai-mikata.jp/";

    // document.title
    document.title = title;

    // メタタグ更新ヘルパー
    const setMeta = (selector, attr, value) => {
      let el = document.querySelector(selector);
      if (!el) {
        el = document.createElement('meta');
        const [attrName, attrVal] = selector.replace(/[\[\]'"]/g, '').split('=');
        el.setAttribute(attrName, attrVal);
        document.head.appendChild(el);
      }
      el.setAttribute(attr, value);
    };

    setMeta("meta[name='description']", "content", description);
    setMeta("meta[property='og:title']", "content", title);
    setMeta("meta[property='og:description']", "content", description);
    setMeta("meta[property='og:url']", "content", canonicalUrl);
    setMeta("meta[name='twitter:title']", "content", title);
    setMeta("meta[name='twitter:description']", "content", description);

    // Canonical
    let linkCanonical = document.querySelector("link[rel='canonical']");
    if (linkCanonical) {
      linkCanonical.setAttribute("href", canonicalUrl);
    }
  }, [cityCode]);

  const navigate = useCallback((url, replace = false) => {
    const basePath = cityCode === 'kyoto' ? '' : `/${cityCode}`; // basePathを考慮
    const finalUrl = url.startsWith('/') ? `${basePath}${url}` : `${basePath}/${url}`;

    if (replace) {
      window.history.replaceState({}, '', finalUrl);
    } else {
      window.history.pushState({}, '', finalUrl);
    }
    window.dispatchEvent(new Event('app-navigate'));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [cityCode]);

  const resolveSpeaker = useCallback((spk) => {
    if (!spk) return null;
    const name = typeof spk === 'string' ? spk.replace(/\s+/g, '') : spk.speaker?.replace(/\s+/g, '');
    return (speakerStats || []).find(s => s.speaker.replace(/\s+/g, '') === name) || null;
  }, [speakerStats]);

  const handleGoHome = useCallback(() => {
    setSearchQuery('');
    setSubmittedQuery('');
    navigate('/');
  }, [navigate, setSearchQuery, setSubmittedQuery]);

  const handleSpeakerClick = useCallback((speakerInput) => {
    const speakerName = typeof speakerInput === 'string' ? speakerInput : speakerInput?.speaker;
    if (!speakerName) return;
    navigate(`/?speaker=${encodeURIComponent(speakerName)}`);
  }, [navigate]);

  const handleOpenCompare = useCallback((initialSpeaker) => {
    let names = [];
    if (initialSpeaker) {
      const name = typeof initialSpeaker === 'string' ? initialSpeaker : initialSpeaker.speaker;
      if (name) names = [name];
    } else if (compareList.length > 0) {
      names = compareList.map(s => s.speaker);
    }
    const param = names.length > 0 ? names.join(',') : 'open';
    navigate(`/?compare=${encodeURIComponent(param)}`);
  }, [compareList, navigate]);

  const handleAddSpeakerToCompare = useCallback((spkOrList) => {
    const rawAdd = Array.isArray(spkOrList) ? spkOrList : [spkOrList];
    const newNames = rawAdd.map(s => (typeof s === 'string' ? s : s?.speaker)).filter(Boolean);

    const currentNames = (currentRoute.type === 'compare' ? currentRoute.names : compareList.map(s => s.speaker)) || [];
    const combined = [...currentNames];
    newNames.forEach(n => {
      if (!combined.includes(n)) combined.push(n);
    });
    const finalNames = combined.slice(0, 12);

    navigate(`/?compare=${encodeURIComponent(finalNames.join(','))}`, true);
  }, [currentRoute, compareList, navigate]);

  const handleRemoveSpeakerFromCompare = useCallback((spk) => {
    const targetName = typeof spk === 'string' ? spk : spk?.speaker;
    const currentNames = (currentRoute.type === 'compare' ? currentRoute.names : compareList.map(s => s.speaker)) || [];
    const nextNames = currentNames.filter(n => n !== targetName);
    const param = nextNames.length > 0 ? nextNames.join(',') : 'open';

    navigate(`/?compare=${encodeURIComponent(param)}`, true);
  }, [currentRoute, compareList, navigate]);

  const navigateToView = useCallback((viewName) => {
    navigate(`/?view=${viewName}`);
  }, [navigate]);

  const handleOpenCategoryDetail = useCallback((catName) => {
    navigate(`/#category=${encodeURIComponent(catName)}`);
  }, [navigate]);

  const handleOpenTopicDetail = useCallback((topicId) => {
    navigate(`/#topic=${topicId}`);
  }, [navigate]);

  const handleSearchSubmit = useCallback((e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    navigate(`/?q=${encodeURIComponent(searchQuery.trim())}`);
  }, [searchQuery, navigate]);

  const handleKeywordClick = useCallback((keyword) => {
    setSearchQuery(keyword);
    navigate(`/?q=${encodeURIComponent(keyword.trim())}`);
  }, [setSearchQuery, navigate]);

  const activeCompareList = useMemo(() => {
    if (currentRoute.type !== 'compare') return compareList;
    if (!currentRoute.names || currentRoute.names.length === 0) return [];
    return currentRoute.names.map(name => resolveSpeaker(name)).filter(Boolean);
  }, [currentRoute, compareList, resolveSpeaker]);

  const activeSpeaker = useMemo(() => {
    if (currentRoute.type !== 'speaker' || !currentRoute.speakerName) return null;
    return resolveSpeaker(currentRoute.speakerName);
  }, [currentRoute, resolveSpeaker]);

  const threadsForSpeaker = useMemo(() => {
    if (!activeSpeaker) return [];
    let list = activeSpeaker.statements ? [...activeSpeaker.statements] : [];
    if (speakerCategory) {
      list = list.filter(s => s.category === speakerCategory || (s.category && s.category.includes(speakerCategory)));
    }
    if (speakerSort === 'recent') {
      list.sort((a, b) => new Date(b.meeting_date || 0) - new Date(a.meeting_date || 0));
    } else if (speakerSort === 'solution') {
      list.sort((a, b) => (b.solution_score || 0) - (a.solution_score || 0));
    } else if (speakerSort === 'local_focus') {
      list.sort((a, b) => (b.local_focus_score || 0) - (a.local_focus_score || 0));
    } else if (speakerSort === 'constructive') {
      list.sort((a, b) => (b.constructive_score || 0) - (a.constructive_score || 0));
    } else if (speakerSort === 'evidence') {
      list.sort((a, b) => (b.evidence_score || 0) - (a.evidence_score || 0));
    }
    return list;
  }, [activeSpeaker, speakerCategory, speakerSort]);

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
        <p className="text-sm font-black text-slate-500 tracking-wider">議会データを読み込み中...</p>
      </div>
    );
  }

  const renderNavbar = (isCompare = false) => (
    <Navbar
      onLogoClick={handleGoHome}
      onOpenGuide={() => navigateToView('guide')}
      onOpenAbout={() => navigateToView('about')}
      onOpenMethodology={() => navigateToView('methodology')}
      onOpenCompare={() => handleOpenCompare()}
      onOpenMayor={() => navigateToView('mayor')}
      isCompareMode={isCompare}
      cityCode={cityCode} // 💡 NavbarにcityCodeを渡す
    />
  );

  // --- 排他的画面ルーティング ---

  if (currentRoute.type === 'mayor') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <MayorTrackerView
            data={mayorTrackerData}
            onBack={handleGoHome}
            onSelectBill={setSelectedBillForModal}
            onOpenMethodology={() => navigateToView('methodology')}
          />
        </div>
        <BillDetailModal
          cityCode={cityCode}
          isOpen={Boolean(selectedBillForModal)}
          onClose={() => setSelectedBillForModal(null)}
          bill={selectedBillForModal}
          issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null}
          speakerStats={speakerStats}
          onSpeakerClick={handleSpeakerClick}
        />
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'guide') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <GuidePage onBack={handleGoHome} onOpenMethodology={() => navigateToView('methodology')} onOpenAbout={() => navigateToView('about')} />
        </div>
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'about') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <AboutPage onBack={handleGoHome} onOpenMethodology={() => navigateToView('methodology')} />
        </div>
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'methodology') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <Methodology onBack={handleGoHome} />
        </div>
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'topic') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <TopicDetailPage topicId={currentRoute.topicId} cityCode={cityCode} onBack={handleGoHome} />
        </div>
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'category') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <CategoryDetailPage
            categoryName={currentRoute.categoryName}
            onBack={handleGoHome}
            topicStats={topicStats}
            filteredThreads={statements.filter(s => s.category === currentRoute.categoryName)}
            filteredBills={votesData.filter(b => getCategoryForBill(b) === currentRoute.categoryName)}
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
        </div>
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'contested') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <ContestedBillsView initialCategory={currentRoute.category} billIssues={billIssuesList} votesData={votesData} onClose={handleGoHome} onSpeakerClick={handleSpeakerClick} />
        </div>
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'compare') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(true)}
        <div className="flex-grow">
          <CompareDashboard
            compareList={activeCompareList}
            allSpeakers={speakerStats}
            onAddSpeaker={handleAddSpeakerToCompare}
            onRemoveSpeaker={handleRemoveSpeakerFromCompare}
            onClose={handleGoHome}
            onViewContext={handleViewContext}
            onSpeakerClick={handleSpeakerClick}
            votesData={votesData}
            issuesMap={issuesMap}
            onSelectBill={setSelectedBillForModal}
            onOpenMethodology={() => navigateToView('methodology')}
          />
        </div>
        <BillDetailModal
          cityCode={cityCode} isOpen={Boolean(selectedBillForModal)} onClose={() => setSelectedBillForModal(null)} bill={selectedBillForModal} issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null} speakerStats={speakerStats} onSpeakerClick={(spk) => { setSelectedBillForModal(null); handleSpeakerClick(spk); }} />
        <TimelineModal
          cityCode={cityCode}
          isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'speaker' && activeSpeaker) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <SpeakerDetailView
            cityCode={cityCode}
            selectedSpeaker={activeSpeaker}
            speakerStats={speakerStats}
            speakerFilteredThreads={threadsForSpeaker}
            topicStats={topicStats}
            speakerCategory={speakerCategory}
            setSpeakerCategory={setSpeakerCategory}
            speakerSort={speakerSort}
            setSpeakerSort={setSpeakerSort}
            votesData={votesData}
            issuesMap={issuesMap}
            onOpenCompare={(spk) => handleOpenCompare(spk)}
            onBack={handleGoHome}
            onSpeakerClick={handleSpeakerClick}
            onViewContext={handleViewContext}
            onOpenMethodology={() => navigateToView('methodology')}
            onSelectBill={setSelectedBillForModal}
          />
        </div>
        <TimelineModal
          cityCode={cityCode}
          isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
        <BillDetailModal
          cityCode={cityCode} isOpen={Boolean(selectedBillForModal)} onClose={() => setSelectedBillForModal(null)} bill={selectedBillForModal} issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null} speakerStats={speakerStats} onSpeakerClick={handleSpeakerClick} />
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'search') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <SearchResultsView cityCode={cityCode}
            submittedQuery={currentRoute.query}
            onClearSearch={handleGoHome}
            filteredThreads={filteredThreads}
            filteredBills={filteredBills}
            filteredSpeakers={filteredSpeakers}
            speakerStats={speakerStats}
            issuesMap={issuesMap}
            onlyContestedBills={onlyContestedBills}
            setOnlyContestedBills={setOnlyContestedBills}
            onSpeakerClick={handleSpeakerClick}
            onViewContext={handleViewContext}
            onOpenCompare={(spk) => handleOpenCompare(spk)}
            onSelectBill={setSelectedBillForModal}
            onOpenMethodology={() => navigateToView('methodology')}
            onOpenTopicDetail={handleOpenTopicDetail}
          />
        </div>
        <BillDetailModal
          cityCode={cityCode} isOpen={Boolean(selectedBillForModal)} onClose={() => setSelectedBillForModal(null)} bill={selectedBillForModal} issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null} speakerStats={speakerStats} onSpeakerClick={handleSpeakerClick} />
        <TimelineModal
          cityCode={cityCode}
          isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between selection:bg-indigo-500 selection:text-white">
      {renderNavbar(false)}

      <main className="max-w-6xl mx-auto py-8 px-6 w-full flex-grow space-y-10">
        <HeroSection
          cityCode={cityCode}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onSearchSubmit={handleSearchSubmit}
          onKeywordClick={handleKeywordClick}
          onOpenGuide={() => navigateToView('guide')}
        />

        <MacroTopicMap
          cityCode={cityCode}
          topicStats={topicStats}
          selectedCategory={selectedCategory}
          onOpenCategoryDetail={handleOpenCategoryDetail}
          getIssueCountForCategory={getIssueCountForCategory}
          onOpenTopicDetail={handleOpenTopicDetail}
        />

        <HighlightedThreads
          statements={statements}
          onViewContext={handleViewContext}
          onSpeakerClick={handleSpeakerClick}
          onOpenMethodology={() => navigateToView('methodology')}
        />

        <MainTabView
          cityCode={cityCode}
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
          onOpenCompare={(spk) => handleOpenCompare(spk)}
          onViewContext={handleViewContext}
          onSelectBill={setSelectedBillForModal}
          onOpenMethodology={() => navigateToView('methodology')}
        />
      </main>

      <BillDetailModal
        cityCode={cityCode}
        isOpen={Boolean(selectedBillForModal)}
        onClose={() => setSelectedBillForModal(null)}
        bill={selectedBillForModal}
        issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null}
        speakerStats={speakerStats}
        onSpeakerClick={handleSpeakerClick}
      />

      <TimelineModal
        cityCode={cityCode}
        isOpen={isPanelOpen}
        onClose={() => setIsPanelOpen(false)}
        selectedContext={selectedContext}
        isLoading={isLoadingContext}
      />
      <FeedbackButton />
      <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
    </div>
  );
}