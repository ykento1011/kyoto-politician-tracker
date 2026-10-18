import React, { useState, useEffect, useMemo } from 'react';
import {
  Search, Hash, PieChart, BarChart3, Landmark, Loader2, 
  MapPin, FileText, User, MessageCircle, Scale, BookOpen, ArrowRight, GitCompare, Shuffle
} from 'lucide-react';

import { useStatements } from './hooks/useStatements';
import { TRENDING_TAGS, cleanName } from './utils/styleHelpers';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import MacroTopicMap from './components/MacroTopicMap';
import BillsSection from './components/BillsSection';
import SpeakerDetailView from './components/SpeakerDetailView';
import ThreadCard from './components/ThreadCard';
import HighlightedThreads from './components/HighlightedThreads';
import TimelineModal from './components/TimelineModal';
import CompareDashboard from './components/CompareDashboard';
import BillDetailModal from './components/BillDetailModal';
import Methodology from './components/Methodology';
import SearchResultsView from './components/SearchResultsView'; // 💡 追加
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';

export default function App() {
  const {
    statements, isLoading,
    searchQuery, setSearchQuery, 
    submittedQuery, setSubmittedQuery, // 💡 追加
    selectedCategory, setSelectedCategory,
    selectedCommittee, setSelectedCommittee, selectedDistrict, setSelectedDistrict,
    sortPerspective, setSortPerspective, viewMode, setViewMode,
    selectedSpeaker, speakerCategory, setSpeakerCategory, speakerSort, setSpeakerSort, speakerFilteredThreads,
    compareList, setCompareList, isCompareMode,
    clearSpeakerAndCompare, 
    handleSpeakerClick, handleViewContext,
    selectedContext, isPanelOpen, setIsPanelOpen, isLoadingContext,
    topicStats, speakerStats, filteredSpeakers, filteredThreads
  } = useStatements();

  const [votesData, setVotesData] = useState([]);
  const [billIssues, setBillIssues] = useState([]);
  const [onlyContestedBills, setOnlyContestedBills] = useState(true);
  const [billResultFilter, setBillResultFilter] = useState('');
  const [selectedBillForModal, setSelectedBillForModal] = useState(null);
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);

  const [compareActive, setCompareActive] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch('/data/votes_summary.json'),
      fetch('/data/bill_issues.json')
    ])
      .then(async ([resVotes, resIssues]) => {
        if (resVotes.ok) setVotesData(await resVotes.json());
        if (resIssues.ok) setBillIssues(await resIssues.json());
      })
      .catch((err) => console.error("Failed to load bill/vote data", err));
  }, []);

  const issuesMap = useMemo(() => {
    const map = {};
    billIssues.forEach(item => {
      map[`${item.session_name}_${item.bill_number}`] = item;
    });
    return map;
  }, [billIssues]);

  const matchesCategory = (b, catName) => {
    const text = `${b.title} ${b.key_conflict || ''} ${b.background || ''}`;
    if (catName === '都市再生・交通インフラ' || catName === '都市計画') {
      return text.includes('都市計画') || text.includes('建築') || text.includes('開発') || text.includes('住宅') || text.includes('新幹線') || text.includes('道路');
    }
    if (catName === '産業・観光・地域経済') {
      return text.includes('観光') || text.includes('宿泊税') || text.includes('産業') || text.includes('万博') || text.includes('芸術大学') || text.includes('市場') || text.includes('コメ');
    }
    if (catName === '福祉・医療・健康') {
      return text.includes('医療') || text.includes('健康保険') || text.includes('国保') || text.includes('介護') || text.includes('保護') || text.includes('衛生') || text.includes('薬');
    }
    if (catName === '子育て・教育') {
      return text.includes('子ども') || text.includes('給食') || text.includes('学校') || text.includes('保育') || text.includes('児童') || text.includes('こども');
    }
    if (catName === '財政・行革') {
      return text.includes('予算') || text.includes('決算') || text.includes('報酬') || text.includes('給与') || text.includes('定数') || text.includes('手続') || text.includes('献金') || text.includes('裏金') || text.includes('監査');
    }
    if (catName === 'くらし・環境・エネルギー') {
      return text.includes('原発') || text.includes('温暖化') || text.includes('環境') || text.includes('下水') || text.includes('水道') || text.includes('処理水') || text.includes('太陽光');
    }
    if (catName === '防災・減災・治安') {
      return text.includes('防災') || text.includes('消防') || text.includes('災害') || text.includes('耐震');
    }
    if (catName === '文化・景観・歴史') {
      return text.includes('文化') || text.includes('景観') || text.includes('世界遺産') || text.includes('歴史') || text.includes('二条城');
    }
    return text.includes(catName);
  };

  const getIssueCountForCategory = (catName) => {
    if (!billIssues || billIssues.length === 0) return 0;
    return billIssues.filter(b => matchesCategory(b, catName)).length;
  };

  const filteredBills = useMemo(() => {
    return votesData.filter(bill => {
      const vValues = Object.values(bill.votes || {});
      const isContested = vValues.includes('賛成') && vValues.includes('反対');

      if (onlyContestedBills && !isContested) return false;
      if (selectedCategory && !matchesCategory(bill, selectedCategory)) return false;
      if (billResultFilter && !(bill.result || '').includes(billResultFilter)) return false;

      if (submittedQuery.trim()) { // 💡 searchQueryから変更
        const q = submittedQuery.toLowerCase();
        const issue = issuesMap[`${bill.session_name}_${bill.bill_number}`];
        const target = `${bill.title} ${bill.bill_number} ${bill.session_name} ${issue?.key_conflict || ''} ${issue?.background || ''}`.toLowerCase();
        if (!target.includes(q)) return false;
      }
      return true;
    });
  }, [votesData, onlyContestedBills, selectedCategory, billResultFilter, submittedQuery, issuesMap]);

  const handleOpenMethodology = () => {
    clearSpeakerAndCompare();
    setCompareActive(false);
    setIsMethodologyOpen(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCloseMethodology = () => {
    setIsMethodologyOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const startCompareWithSpeaker = (speaker) => {
    const targetObj = (typeof speaker === 'object' && speaker !== null)
      ? speaker
      : speakerStats.find(s => s.speaker === speaker) || selectedSpeaker;

    if (targetObj) {
      setCompareList([targetObj]);
      setCompareActive(true);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
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
    setCompareList(prev => [...prev, speaker]);
  };

  const handleRemoveCompareSpeaker = (speaker) => {
    setCompareList(prev => prev.filter(s => s.speaker !== speaker.speaker));
  };

  // 💡 検索実行（Enterキー または ボタンクリック）
  const handleSearchSubmit = () => {
    if (searchQuery.trim() !== '') {
      setSubmittedQuery(searchQuery);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // 💡 検索クリア（トップページへ戻る）
  const handleClearSearch = () => {
    setSearchQuery('');
    setSubmittedQuery('');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const formatSummaryRadar = (speaker) => [
    { subject: '根拠・データ', A: speaker.avg_evidence || 0, fullMark: 5 },
    { subject: '対案・是正', A: speaker.avg_solution || 0, fullMark: 5 },
    { subject: '地域解像度', A: speaker.avg_local_focus || 0, fullMark: 5 },
    { subject: '議論の進展', A: speaker.avg_constructive || 0, fullMark: 5 },
  ];

  if (isMethodologyOpen) {
    return <Methodology onBack={handleCloseMethodology} />;
  }

if (compareActive || (isCompareMode && compareList.length >= 2)) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        <Navbar onLogoClick={handleCloseCompare} isCompareMode={true} />
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
          onSelectBill={setSelectedBillForModal} // 💡 これを追加
        />
        {/* 💡 比較画面内でも議案詳細モーダルが開くように追加 */}
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
        <TimelineModal isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
      </div>
    );
  }

  // 💡 検索結果画面（submittedQueryが存在する場合）
  if (submittedQuery) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between selection:bg-indigo-500 selection:text-white">
        <Navbar
          onLogoClick={handleClearSearch}
          onOpenMethodology={handleOpenMethodology}
          onOpenCompare={() => {
            setCompareActive(true);
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
          isCompareMode={false}
        />
        
        {/* トップの検索バー（検索結果画面用・控えめなデザイン） */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 sticky top-16 z-20">
          <div className="max-w-4xl mx-auto flex items-center gap-3">
            <div className="relative flex-grow shadow-sm">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleSearchSubmit(); }}
                className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none text-sm font-bold text-slate-800"
              />
            </div>
            <button onClick={handleSearchSubmit} className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2.5 rounded-lg transition-colors cursor-pointer shrink-0">
              再検索
            </button>
          </div>
        </div>

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
          onOpenCompare={startCompareWithSpeaker}
          onSelectBill={setSelectedBillForModal}
          onOpenMethodology={handleOpenMethodology}
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

        <TimelineModal isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
        <Footer onOpenMethodology={handleOpenMethodology} />
      </div>
    );
  }

  // 💡 通常のトップページ・議員詳細画面
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between selection:bg-indigo-500 selection:text-white">
      <Navbar
        onLogoClick={() => { clearSpeakerAndCompare(); setCompareActive(false); }}
        onOpenMethodology={handleOpenMethodology}
        onOpenCompare={() => {
          setCompareActive(true);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
        isCompareMode={false}
      />

      {!selectedSpeaker ? (
        <>
          <header className="bg-white border-b border-slate-200/60 pt-14 pb-12 px-6 text-center relative overflow-hidden">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full max-w-4xl bg-gradient-to-b from-indigo-50/50 to-transparent -z-10 rounded-full blur-3xl opacity-50"></div>
            <div className="max-w-3xl mx-auto">
              <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight mb-5">
                対話がわかる。<span className="text-indigo-600">政策が見える。</span>
              </h1>
              <p className="text-slate-500 text-sm md:text-base leading-relaxed max-w-2xl mx-auto mb-6">
                文字数や発言回数では測れない、政策論戦の「密度」と「個性」をAIで可視化。<br className="hidden md:block"/>
                京都市の重要課題に、誰がどのような対案や視点で挑み、どの議案にどう投票したかを探るオープンデータ基盤です。
              </p>

              <div className="mb-8">
                <button
                  onClick={handleOpenMethodology}
                  className="text-xs font-bold text-indigo-600 hover:text-indigo-800 hover:underline inline-flex items-center gap-1.5 bg-indigo-50/80 px-3 py-1.5 rounded-full border border-indigo-100 cursor-pointer"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>AI監査ロジック・採点基準の解説（ホワイトペーパー）はこちら</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              {/* 💡 検索バー */}
              <div className="relative max-w-2xl mx-auto shadow-sm group">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-indigo-400 group-focus-within:text-indigo-600 w-5 h-5 transition-colors" />
                <input
                  type="text"
                  placeholder="気になる政策キーワードを入力 (例: オーバーツーリズム、給食、新幹線)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleSearchSubmit(); }}
                  className="w-full pl-12 pr-24 py-3.5 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all text-base text-slate-800 placeholder-slate-400 font-medium"
                />
                <button 
                  onClick={handleSearchSubmit}
                  className="absolute right-2 top-1/2 -translate-y-1/2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2 rounded-lg transition-colors cursor-pointer"
                >
                  検索
                </button>
              </div>
              
              <div className="max-w-2xl mx-auto mt-4 flex flex-wrap gap-2 justify-center">
                <span className="text-[11px] font-bold text-slate-400 mt-1 mr-1">注目の論点:</span>
                {TRENDING_TAGS.map(tag => (
                  <button 
                    key={tag} 
                    onClick={() => { 
                      setSearchQuery(tag); 
                      setSubmittedQuery(tag); 
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }} 
                    className="inline-flex items-center px-2.5 py-1 bg-slate-100 hover:bg-indigo-50 text-slate-600 hover:text-indigo-700 text-[11px] font-bold rounded-md transition-colors border border-slate-200 hover:border-indigo-200 cursor-pointer"
                  >
                    <Hash className="w-3 h-3 mr-0.5 opacity-50" />{tag}
                  </button>
                ))}
              </div>
            </div>
          </header>

          <main className="max-w-6xl mx-auto py-8 px-6 space-y-10">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-24 text-slate-400 space-y-3">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                <p className="text-sm font-medium">議会質疑データを読み込み中...</p>
              </div>
            ) : (
              <>
                <HighlightedThreads statements={statements} onSpeakerClick={handleSpeakerClick} onViewContext={handleViewContext} onOpenMethodology={handleOpenMethodology} />

                <MacroTopicMap
                  topicStats={topicStats}
                  selectedCategory={selectedCategory}
                  onSelectCategory={(cat) => setSelectedCategory(cat === selectedCategory ? '' : cat)}
                  getIssueCountForCategory={getIssueCountForCategory}
                />

                <section className="sticky top-16 z-20 bg-[#F8FAFC]/95 backdrop-blur-md py-3 -mx-6 px-6 md:mx-0 md:px-0 border-b md:border-b-0 md:rounded-b-lg border-slate-200 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 transition-all">
                  <div className="flex bg-slate-100 p-1 rounded-xl w-full sm:w-fit border border-slate-200 shrink-0">
                    <button onClick={() => setViewMode('speakers')} className={`flex-1 sm:flex-none flex items-center justify-center px-4 py-2 rounded-lg text-xs md:text-sm font-bold transition-all cursor-pointer ${viewMode === 'speakers' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}><User className="w-4 h-4 mr-1.5" />議員から探す</button>
                    <button onClick={() => setViewMode('threads')} className={`flex-1 sm:flex-none flex items-center justify-center px-4 py-2 rounded-lg text-xs md:text-sm font-bold transition-all cursor-pointer ${viewMode === 'threads' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}><MessageCircle className="w-4 h-4 mr-1.5" />質疑から探す</button>
                    <button onClick={() => setViewMode('bills')} className={`flex-1 sm:flex-none flex items-center justify-center px-4 py-2 rounded-lg text-xs md:text-sm font-bold transition-all cursor-pointer ${viewMode === 'bills' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}><Scale className="w-4 h-4 mr-1.5" />議案・賛否から探す</button>
                  </div>

                  <div className="flex flex-wrap gap-2 w-full lg:w-auto">
                    {viewMode !== 'bills' && (
                      <div className="flex items-center bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 flex-grow sm:flex-grow-0">
                        <MapPin className="w-3.5 h-3.5 text-indigo-500 mr-1.5 shrink-0" />
                        <select value={selectedDistrict} onChange={(e) => setSelectedDistrict(e.target.value)} className="bg-transparent text-slate-700 text-xs font-bold outline-none cursor-pointer w-full">
                          <option value="">全行政区</option>
                          {["北区", "上京区", "左京区", "中京区", "東山区", "下京区", "南区", "右京区", "伏見区", "山科区", "西京区"].map(d => <option key={d} value={d}>{d}</option>)}
                        </select>
                      </div>
                    )}
                    <div className="flex items-center bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 flex-grow sm:flex-grow-0">
                      <PieChart className="w-3.5 h-3.5 text-indigo-500 mr-1.5 shrink-0" />
                      <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} className="bg-transparent text-slate-700 text-xs font-bold outline-none cursor-pointer w-full">
                        <option value="">全分野（すべて）</option>
                        {topicStats.map(t => <option key={t.name} value={t.name}>{t.name}</option>)}
                      </select>
                    </div>
                    {viewMode === 'threads' && (
                      <div className="flex items-center bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 flex-grow sm:flex-grow-0">
                        <Landmark className="w-3.5 h-3.5 text-indigo-500 mr-1.5 shrink-0" />
                        <select value={selectedCommittee} onChange={(e) => setSelectedCommittee(e.target.value)} className="bg-transparent text-slate-700 text-xs font-bold outline-none cursor-pointer w-full">
                          <option value="">全会議体</option>
                          <option value="本会議">本会議</option>
                          <option value="予算・決算特別委員会">予算・決算特別委員会</option>
                          <option value="産業交通水道委員会">産業交通水道委員会</option>
                          <option value="まちづくり委員会">まちづくり委員会</option>
                          <option value="教育福祉委員会">教育福祉委員会</option>
                          <option value="くらし環境委員会">くらし環境委員会</option>
                          <option value="総務消防委員会">総務消防委員会</option>
                        </select>
                      </div>
                    )}
                    {viewMode === 'bills' && (
                      <div className="flex items-center bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 flex-grow sm:flex-grow-0">
                        <FileText className="w-3.5 h-3.5 text-indigo-500 mr-1.5 shrink-0" />
                        <select value={billResultFilter} onChange={(e) => setBillResultFilter(e.target.value)} className="bg-transparent text-slate-700 text-xs font-bold outline-none cursor-pointer w-full">
                          <option value="">全議決結果</option>
                          <option value="可決">可決</option>
                          <option value="否決">否決</option>
                          <option value="認定">認定</option>
                          <option value="同意">同意</option>
                        </select>
                      </div>
                    )}
                    {viewMode !== 'bills' && (
                      <div className="flex items-center bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 flex-grow sm:flex-grow-0">
                        <BarChart3 className="w-3.5 h-3.5 text-indigo-500 mr-1.5 shrink-0" />
                        <select value={sortPerspective} onChange={(e) => setSortPerspective(e.target.value)} className="bg-transparent text-slate-700 text-xs font-bold outline-none cursor-pointer w-full">
                          <option value="random">日替わりシャッフル（公平表示）</option>
                          <option value="name">五十音順（名前順）</option>
                          <option value="recent">新着順</option>
                          <option value="solution">具体的対案を重視</option>
                          <option value="local_focus">現場解像度を重視</option>
                          <option value="constructive">議論の進展を重視</option>
                          <option value="evidence">客観データを重視</option>
                        </select>
                      </div>
                    )}
                  </div>
                </section>

                {viewMode === 'speakers' && (
                  <div className="space-y-4">
                    {sortPerspective === 'random' && (
                      <div className="flex items-center justify-between px-1 text-[11px] font-bold text-slate-400">
                        <span className="flex items-center gap-1">
                          <Shuffle className="w-3 h-3 text-indigo-500" />
                          掲載順の公平性を期すため、全議員を日替わりでランダムに表示しています
                        </span>
                        <span>{filteredSpeakers.length} 名表示中</span>
                      </div>
                    )}

                    <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in duration-300">
                      {filteredSpeakers.map((speaker) => (
                        <article key={speaker.speaker} onClick={() => handleSpeakerClick(speaker.speaker)} className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-lg hover:border-indigo-300 transition-all duration-300 cursor-pointer flex flex-col group relative">
                          <div className="p-5 border-b border-slate-100 flex justify-between items-start bg-slate-50/50">
                            <div>
                              <h2 className="text-lg font-black text-slate-900 tracking-tight group-hover:text-indigo-700 transition-colors">{speaker.speaker}</h2>
                              <div className="flex items-center gap-1.5 mt-0.5 text-[11px] font-bold text-slate-500">
                                <span className="bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded border border-slate-300">{speaker.district}</span>
                                <span className="truncate max-w-[150px]" title={speaker.partyGroup}>{speaker.partyGroup}</span>
                              </div>
                              <div className="flex flex-wrap gap-1 mt-2">
                                {speaker.topCategories.map(cat => <span key={cat} className="px-1.5 py-0.5 bg-white text-slate-500 text-[10px] font-bold rounded border border-slate-200">{cat}</span>)}
                              </div>
                            </div>
                            <div className="flex flex-col items-end">
                              <span className={`px-2 py-0.5 text-[10px] font-extrabold rounded border shadow-2xs ${speaker.style.badgeClass}`}>{speaker.style.label}</span>
                            </div>
                          </div>

                          <div className="p-5 flex-grow flex flex-col items-center justify-center relative">
                            <div className="absolute top-3 left-4">
                              <div className="text-[9px] font-bold text-slate-400 uppercase">質疑スレッド</div>
                              <div className="text-lg font-black text-slate-700">{speaker.count}<span className="text-[10px] font-medium text-slate-400 ml-0.5">件</span></div>
                            </div>
                            <div className="w-full h-36">
                              <ResponsiveContainer width="100%" height="100%">
                                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={formatSummaryRadar(speaker)}>
                                  <PolarGrid stroke="#e2e8f0" />
                                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 9, fontWeight: 600 }} />
                                  <PolarRadiusAxis domain={[0, 5]} tick={false} axisLine={false} />
                                  <Radar dataKey="A" stroke="#6366f1" strokeWidth={2} fill="#818cf8" fillOpacity={0.4} />
                                </RadarChart>
                              </ResponsiveContainer>
                            </div>
                          </div>
                          
                          <div className="p-3 bg-slate-50/50 border-t border-slate-100 flex items-center justify-between gap-2">
                            <button 
                              onClick={(e) => { 
                                e.stopPropagation(); 
                                startCompareWithSpeaker(speaker); 
                              }}
                              className="px-3 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-indigo-600 bg-white hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 transition-all flex items-center gap-1 cursor-pointer"
                            >
                              <GitCompare className="w-3.5 h-3.5 text-indigo-500" />比較する
                            </button>
                            <span className="text-xs font-bold text-indigo-600 group-hover:translate-x-0.5 transition-transform">詳細を見る →</span>
                          </div>
                        </article>
                      ))}
                      {filteredSpeakers.length === 0 && <div className="col-span-full text-center py-20 text-slate-500">条件に一致する議員が見つかりませんでした。</div>}
                    </section>
                  </div>
                )}

                {viewMode === 'threads' && (
                  <section className="space-y-6 animate-in fade-in duration-300">
                    <div className="text-xs font-bold text-slate-500 mb-2">検索結果: トップ {filteredThreads.length} 件</div>
                    {filteredThreads.map((stmt) => (
                      <ThreadCard 
                        key={stmt.id} 
                        stmt={stmt} 
                        speakerInfo={speakerStats.find(s => s.speaker === cleanName(stmt.speaker))} 
                        onSpeakerClick={handleSpeakerClick} 
                        onViewContext={handleViewContext} 
                        showSpeakerHeader={true} 
                        onOpenMethodology={handleOpenMethodology}
                      />
                    ))}
                    {filteredThreads.length === 0 && <div className="text-center py-20 text-slate-500">条件に一致する質疑が見つかりませんでした。</div>}
                  </section>
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
              </>
            )}
          </main>
        </>
      ) : (
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
          onOpenCompare={startCompareWithSpeaker}
          onBack={clearSpeakerAndCompare}
          onSpeakerClick={handleSpeakerClick}
          onViewContext={handleViewContext}
          onOpenMethodology={handleOpenMethodology}
          onSelectBill={setSelectedBillForModal}
        />
      )}

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

      <TimelineModal isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
      <Footer onOpenMethodology={handleOpenMethodology} />
    </div>
  );
}