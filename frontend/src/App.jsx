import React, { useState } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import {
  Search, Scale, Activity, ArrowLeft, User, MessageCircle,
  Hash, PieChart, BarChart3, CheckCircle2, Info, Landmark, Loader2, 
  ChevronDown, MapPin, ExternalLink, Globe, Sparkles, TrendingUp, Users, ArrowRight, GitCompare, X, Check
} from 'lucide-react';

import { useStatements } from './hooks/useStatements';
import { TRENDING_TAGS, cleanName } from './utils/styleHelpers';
import ThreadCard from './components/ThreadCard';
import HighlightedThreads from './components/HighlightedThreads';
import TimelineModal from './components/TimelineModal';
import CompareDashboard from './components/CompareDashboard';

export default function App() {
  const {
    statements, isLoading,
    searchQuery, setSearchQuery, selectedCategory, setSelectedCategory,
    selectedCommittee, setSelectedCommittee, selectedDistrict, setSelectedDistrict,
    sortPerspective, setSortPerspective, viewMode, setViewMode,
    selectedSpeaker, speakerCategory, setSpeakerCategory, speakerSort, setSpeakerSort, speakerFilteredThreads,
    compareList, setCompareList, isCompareMode,
    toggleCompare, executeCompare, clearSpeakerAndCompare, handleSpeakerClick, handleViewContext,
    selectedContext, isPanelOpen, setIsPanelOpen, isLoadingContext,
    topicStats, speakerStats, filteredSpeakers, filteredThreads
  } = useStatements();

  const [relatedTab, setRelatedTab] = useState('district');

  const handleCategorySelect = (category) => { setSelectedCategory(category); setViewMode('threads'); };
  const handleTagSelect = (tag) => { setSearchQuery(tag); setViewMode('threads'); };

  const formatSummaryRadar = (speaker) => [
    { subject: '根拠・データ', A: speaker.avg_evidence || 0, fullMark: 5 },
    { subject: '対案・是正', A: speaker.avg_solution || 0, fullMark: 5 },
    { subject: '地域解像度', A: speaker.avg_local_focus || 0, fullMark: 5 },
    { subject: '議論の進展', A: speaker.avg_constructive || 0, fullMark: 5 },
  ];

  const generateCouncilorProfileSummary = (speaker) => {
    if (!speaker) return "";
    const categoriesStr = speaker.topCategories && speaker.topCategories.length > 0 ? speaker.topCategories.join("・") : "市政全般";
    const metrics = [
      { key: 'evidence', label: '客観的な根拠・データ活用', val: speaker.avg_evidence },
      { key: 'solution', label: '具体的対案や是正策の提示', val: speaker.avg_solution },
      { key: 'local_focus', label: '生活現場や地域課題への解像度', val: speaker.avg_local_focus },
      { key: 'constructive', label: '鋭い行政監視と議論の進展力', val: speaker.avg_constructive },
    ].sort((a, b) => b.val - a.val);
    
    let narrative = "";
    if (metrics[0].key === 'solution') narrative = `課題指摘にとどまらず「${metrics[0].label}」に強い特徴があり、実現可能性を見据えた制度改善をリードする傾向`;
    else if (metrics[0].key === 'local_focus') narrative = `生活現場の実態に根ざした「${metrics[0].label}」が際立っており、市民や当事者の切実な声を的確に議場へ持ち込む傾向`;
    else if (metrics[0].key === 'evidence') narrative = `数字や実証事例など「${metrics[0].label}」を手堅く組み立て、論理的整合性の高い質疑を展開する傾向`;
    else narrative = `行政答弁の不備や論理破綻を突く「${metrics[0].label}」に長けており、市側から明確な見解や方針転換を引き出す傾向`;

    return `主に【${categoriesStr}】の分野で活発に登壇。全${speaker.count}件の政策質疑ログからは、${narrative}が見て取れます。`;
  };

  const sameDistrictSpeakers = React.useMemo(() => {
    if (!selectedSpeaker) return [];
    return speakerStats.filter(s => s.district === selectedSpeaker.district && s.speaker !== selectedSpeaker.speaker);
  }, [selectedSpeaker, speakerStats]);

  const samePartySpeakers = React.useMemo(() => {
    if (!selectedSpeaker) return [];
    return speakerStats.filter(s => s.partyGroup === selectedSpeaker.partyGroup && s.speaker !== selectedSpeaker.speaker);
  }, [selectedSpeaker, speakerStats]);

  // 💡 ルーティング分岐：比較モードなら全画面で CompareDashboard を表示
  if (isCompareMode && compareList.length >= 2) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans relative antialiased flex flex-col justify-between">
        <nav className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200/80 transition-all h-16">
          <div className="max-w-6xl mx-auto px-6 h-full flex items-center justify-between">
            <div className="flex items-center space-x-3 cursor-pointer" onClick={clearSpeakerAndCompare}>
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
                <Scale className="w-5 h-5" />
              </div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold tracking-tight text-slate-900 text-base">議会のミカタ <span className="text-sm">京都</span></span>
                <span className="text-[9px] font-black px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">BETA</span>
              </div>
            </div>
            <div className="hidden md:flex items-center space-x-4 text-xs font-bold text-slate-500">
              <div className="flex items-center"><Activity className="w-3.5 h-3.5 mr-1 text-slate-400"/>徹底比較モード</div>
            </div>
          </div>
        </nav>

        <CompareDashboard
          compareList={compareList}
          onClose={clearSpeakerAndCompare}
          onViewContext={handleViewContext}
          onSpeakerClick={handleSpeakerClick}
        />

        <TimelineModal isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
      </div>
    );
  }

  // ＝＝＝ 以降、既存のトップページ＆詳細ページのレンダリング ＝＝＝
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans relative antialiased selection:bg-indigo-500 selection:text-white flex flex-col justify-between">
      <nav className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200/80 transition-all h-16">
        <div className="max-w-6xl mx-auto px-6 h-full flex items-center justify-between">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={clearSpeakerAndCompare}>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold tracking-tight text-slate-900 text-base">議会のミカタ <span className="text-sm">京都</span></span>
                <span className="text-[9px] font-black px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">BETA</span>
              </div>
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider hidden sm:block mt-0.5">京都市議会 AI政策対話ログ</p>
            </div>
          </div>
          <div className="hidden md:flex items-center space-x-4 text-xs font-bold text-slate-500">
            <div className="flex items-center"><Activity className="w-3.5 h-3.5 mr-1 text-slate-400"/>分析対象: 120,532 発言</div>
            <div className="flex items-center"><CheckCircle2 className="w-3.5 h-3.5 mr-1 text-indigo-500"/>抽出質疑: 5,128 スレッド</div>
          </div>
        </div>
      </nav>

      {!selectedSpeaker && (
        <>
          <header className="bg-white border-b border-slate-200/60 pt-14 pb-12 px-6 text-center relative overflow-hidden">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full max-w-4xl bg-gradient-to-b from-indigo-50/50 to-transparent -z-10 rounded-full blur-3xl opacity-50"></div>
            <div className="max-w-3xl mx-auto">
              <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight mb-5">
                対話がわかる。<span className="text-indigo-600">政策が見える。</span>
              </h1>
              <p className="text-slate-500 text-sm md:text-base leading-relaxed max-w-2xl mx-auto mb-8">
                文字数や発言回数では測れない、政策論戦の「密度」と「個性」をAIで可視化。<br className="hidden md:block"/>
                京都市の重要課題に、誰がどのような対案や視点で挑んでいるかを探るオープンデータ・プラットフォームです。
              </p>

              <div className="relative max-w-2xl mx-auto shadow-sm group">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-indigo-400 group-focus-within:text-indigo-600 w-5 h-5 transition-colors" />
                <input
                  type="text"
                  placeholder="気になる政策キーワードを入力 (例: オーバーツーリズム、学童保育)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-3.5 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all text-base text-slate-800 placeholder-slate-400 font-medium"
                />
              </div>
              <div className="max-w-2xl mx-auto mt-4 flex flex-wrap gap-2 justify-center">
                <span className="text-[11px] font-bold text-slate-400 mt-1 mr-1">注目の論点:</span>
                {TRENDING_TAGS.map(tag => (
                  <button key={tag} onClick={() => handleTagSelect(tag)} className="inline-flex items-center px-2.5 py-1 bg-slate-100 hover:bg-indigo-50 text-slate-600 hover:text-indigo-700 text-[11px] font-bold rounded-md transition-colors border border-slate-200 hover:border-indigo-200">
                    <Hash className="w-3 h-3 mr-0.5 opacity-50" />{tag}
                  </button>
                ))}
                {searchQuery && <button onClick={() => setSearchQuery('')} className="text-[11px] text-rose-500 font-bold hover:underline ml-2 mt-1">クリア</button>}
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
                <HighlightedThreads statements={statements} onSpeakerClick={handleSpeakerClick} onViewContext={handleViewContext} />

                <section>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-extrabold text-slate-800 flex items-center">
                      <PieChart className="w-4 h-4 mr-1.5 text-indigo-500" />市議会マクロ論戦マップ
                    </h3>
                    <span className="text-[10px] text-slate-400 font-bold bg-slate-100 px-2 py-0.5 rounded-full">全 5,128 スレッド集計</span>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {topicStats.map(topic => (
                      <button key={topic.name} onClick={() => handleCategorySelect(topic.name)} className={`flex flex-col p-3 rounded-xl border text-left transition-all ${selectedCategory === topic.name ? 'bg-indigo-50 border-indigo-300 shadow-sm' : 'bg-white border-slate-200 hover:border-indigo-300 hover:shadow-sm'}`}>
                        <span className={`text-xs font-bold ${selectedCategory === topic.name ? 'text-indigo-800' : 'text-slate-700'}`}>{topic.name}</span>
                        <div className="flex items-end justify-between mt-2">
                          <span className="text-lg font-black text-slate-900">{topic.percentage}<span className="text-[10px] text-slate-400 font-medium ml-0.5">%</span></span>
                          <span className="text-[10px] text-slate-400 font-medium">{topic.count}件</span>
                        </div>
                        <div className="w-full bg-slate-100 h-1 mt-2 rounded-full overflow-hidden">
                          <div className="bg-indigo-400 h-full rounded-full" style={{ width: `${topic.percentage}%` }}></div>
                        </div>
                      </button>
                    ))}
                  </div>

                  <details className="mt-3 group text-xs text-slate-500 bg-slate-50 rounded-lg border border-slate-200/80 p-2.5">
                    <summary className="flex items-center gap-1.5 font-bold text-slate-700 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                      <Info className="w-4 h-4 text-indigo-500 shrink-0" /><span>対象データとAI分類の特性について</span>
                      <ChevronDown className="w-3.5 h-3.5 ml-auto text-slate-400 group-open:rotate-180 transition-transform" />
                    </summary>
                    <div className="mt-2.5 pl-1 pt-2 border-t border-slate-200">
                      <ul className="list-disc list-inside space-y-1.5 leading-relaxed">
                        <li><strong className="text-slate-600">対象データ:</strong> 京都市会 現任期（2023年5月〜2026年時点）の本会議・各常任委員会・特別委員会の会議録から抽出された実質政策質疑</li>
                        <li><strong className="text-slate-600">分類の特性:</strong> 政策分野はAIによる主たる論点の自動分類です。複合的なテーマは分散して集計される場合があります。</li>
                      </ul>
                    </div>
                  </details>
                </section>

                <section className="sticky top-16 z-20 bg-[#F8FAFC]/95 backdrop-blur-md py-3 -mx-6 px-6 md:mx-0 md:px-0 border-b md:border-b-0 md:rounded-b-lg border-slate-200 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 transition-all">
                  <div className="flex bg-slate-100 p-1 rounded-xl w-full sm:w-fit border border-slate-200 shrink-0">
                    <button onClick={() => setViewMode('speakers')} className={`flex-1 sm:flex-none flex items-center justify-center px-4 py-2 rounded-lg text-sm font-bold transition-all ${viewMode === 'speakers' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'}`}>
                      <User className="w-4 h-4 mr-2" />議員から探す
                    </button>
                    <button onClick={() => setViewMode('threads')} className={`flex-1 sm:flex-none flex items-center justify-center px-4 py-2 rounded-lg text-sm font-bold transition-all ${viewMode === 'threads' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'}`}>
                      <MessageCircle className="w-4 h-4 mr-2" />論戦から探す
                    </button>
                  </div>

                  <div className="flex flex-wrap gap-2.5 w-full lg:w-auto">
                    <div className="flex items-center bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 flex-grow sm:flex-grow-0">
                      <MapPin className="w-3.5 h-3.5 text-indigo-500 mr-1.5 shrink-0" />
                      <select value={selectedDistrict} onChange={(e) => setSelectedDistrict(e.target.value)} className="bg-transparent text-slate-700 text-xs font-bold outline-none cursor-pointer w-full">
                        <option value="">全行政区</option>
                        {["北区", "上京区", "左京区", "中京区", "東山区", "下京区", "南区", "右京区", "伏見区", "山科区", "西京区"].map(d => <option key={d} value={d}>{d}</option>)}
                      </select>
                    </div>

                    <div className="flex items-center bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 flex-grow sm:flex-grow-0">
                      <PieChart className="w-3.5 h-3.5 text-indigo-500 mr-1.5 shrink-0" />
                      <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} className="bg-transparent text-slate-700 text-xs font-bold outline-none cursor-pointer w-full">
                        <option value="">全分野</option>
                        {topicStats.map(t => <option key={t.name} value={t.name}>{t.name}</option>)}
                      </select>
                    </div>

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

                    <div className="flex items-center bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 flex-grow sm:flex-grow-0">
                      <BarChart3 className="w-3.5 h-3.5 text-indigo-500 mr-1.5 shrink-0" />
                      <select value={sortPerspective} onChange={(e) => setSortPerspective(e.target.value)} className="bg-transparent text-slate-700 text-xs font-bold outline-none cursor-pointer w-full">
                        <option value="recent">新着順</option>
                        <option value="solution">具体的対案を重視</option>
                        <option value="local_focus">現場解像度を重視</option>
                        <option value="constructive">議論の進展を重視</option>
                        <option value="evidence">客観データを重視</option>
                      </select>
                    </div>
                  </div>
                </section>

                {viewMode === 'speakers' ? (
                  <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in duration-300">
                    {filteredSpeakers.map((speaker) => {
                      const isCompared = compareList.some(s => s.speaker === speaker.speaker);
                      return (
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
                            <button onClick={(e) => toggleCompare(speaker, e)} className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1 border ${isCompared ? 'bg-indigo-600 text-white border-indigo-600 shadow-2xs' : 'bg-white text-slate-600 hover:text-indigo-600 border-slate-200 hover:border-indigo-200'}`}>
                              {isCompared ? <Check className="w-3.5 h-3.5" /> : <GitCompare className="w-3.5 h-3.5" />}
                              {isCompared ? '比較中' : '比較に追加'}
                            </button>
                            <span className="text-xs font-bold text-indigo-600 group-hover:translate-x-0.5 transition-transform">詳細を見る →</span>
                          </div>
                        </article>
                      );
                    })}
                    {filteredSpeakers.length === 0 && <div className="col-span-full text-center py-20 text-slate-500">条件に一致する議員が見つかりませんでした。</div>}
                  </section>
                ) : (
                  <section className="space-y-6 animate-in fade-in duration-300">
                    <div className="text-xs font-bold text-slate-500 mb-2">検索結果: トップ {filteredThreads.length} 件</div>
                    {filteredThreads.map((stmt) => <ThreadCard key={stmt.id} stmt={stmt} speakerInfo={speakerStats.find(s => s.speaker === cleanName(stmt.speaker))} onSpeakerClick={handleSpeakerClick} onViewContext={handleViewContext} showSpeakerHeader={true} />)}
                    {filteredThreads.length === 0 && <div className="text-center py-20 text-slate-500">条件に一致する質疑が見つかりませんでした。</div>}
                  </section>
                )}
              </>
            )}
          </main>
        </>
      )}

      {/* ＝＝＝ 単一議員詳細画面 ＝＝＝ */}
      {selectedSpeaker && (
        <main className="max-w-5xl mx-auto py-8 px-6 animate-in fade-in slide-in-from-bottom-4 duration-300 w-full">
          <div className="flex items-center justify-between mb-6">
            <button onClick={clearSpeakerAndCompare} className="inline-flex items-center text-xs font-bold text-slate-500 hover:text-indigo-600 transition-colors bg-white px-3 py-2 rounded-lg border border-slate-200 shadow-sm">
              <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />一覧に戻る
            </button>
            <button onClick={() => toggleCompare(selectedSpeaker)} className={`px-3 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 border shadow-sm ${compareList.some(s => s.speaker === selectedSpeaker.speaker) ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-700 hover:bg-indigo-50 border-slate-200'}`}>
              <GitCompare className="w-3.5 h-3.5" />{compareList.some(s => s.speaker === selectedSpeaker.speaker) ? '比較から外す' : '他の議員と比較する'}
            </button>
          </div>

          <header className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 mb-6 space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-6 border-b border-slate-100">
              <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600 border border-indigo-100 shrink-0">
                  <User className="w-7 h-7" />
                </div>
                <div>
                  <div className="flex items-center gap-3 flex-wrap mb-1">
                    <h2 className="text-2xl font-black text-slate-900 tracking-tight">{selectedSpeaker.speaker}</h2>
                    <span className={`px-2.5 py-0.5 text-xs font-extrabold rounded border ${selectedSpeaker.style.badgeClass}`}>{selectedSpeaker.style.label}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-bold text-slate-600 mt-1">
                    <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">{selectedSpeaker.district}</span>
                    <span>{selectedSpeaker.partyGroup}</span>
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2 self-start md:self-auto">
                {selectedSpeaker.officialUrl && <a href={selectedSpeaker.officialUrl} target="_blank" rel="noopener noreferrer" className="bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold inline-flex items-center gap-1 transition-colors shadow-2xs"><Landmark className="w-3.5 h-3.5" />京都市会 公式紹介 <ExternalLink className="w-3 h-3 ml-0.5 opacity-50" /></a>}
                {selectedSpeaker.websiteUrl && <a href={selectedSpeaker.websiteUrl} target="_blank" rel="noopener noreferrer" className="bg-white hover:bg-indigo-50 text-indigo-600 border border-indigo-200 px-3 py-1.5 rounded-lg text-xs font-bold inline-flex items-center gap-1 transition-colors shadow-2xs"><Globe className="w-3.5 h-3.5" />公式Webサイト <ExternalLink className="w-3 h-3 ml-0.5 opacity-50" /></a>}
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
              <div className="lg:col-span-7 space-y-4">
                <div className="bg-gradient-to-br from-indigo-50/50 to-slate-50 p-4 rounded-xl border border-indigo-100/70">
                  <div className="flex items-center gap-1.5 text-xs font-extrabold text-indigo-900 mb-1.5"><Sparkles className="w-3.5 h-3.5 text-amber-500" />AI活動分析：政策アプローチと特徴</div>
                  <p className="text-xs text-slate-700 leading-relaxed font-medium">{generateCouncilorProfileSummary(selectedSpeaker)}</p>
                  <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-indigo-100/60 leading-normal">{selectedSpeaker.style.desc}</p>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">議場での主な質疑分野</span>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedSpeaker.topCategories.map(cat => <span key={cat} className="px-2 py-1 bg-white text-slate-700 text-xs font-bold rounded-md border border-slate-200 shadow-2xs">#{cat}</span>)}
                  </div>
                </div>
              </div>
              <div className="lg:col-span-5 bg-slate-50/80 p-4 rounded-xl border border-slate-100 flex flex-col justify-between">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-extrabold text-slate-700 flex items-center"><TrendingUp className="w-3.5 h-3.5 mr-1 text-indigo-600" />4軸ポリシーパラメータ</span>
                  <span className="text-[10px] font-black text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-100">全 {selectedSpeaker.count} 質疑</span>
                </div>
                <div className="w-full h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="68%" data={formatSummaryRadar(selectedSpeaker)}>
                      <PolarGrid stroke="#e2e8f0" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: '#475569', fontSize: 10, fontWeight: 700 }} />
                      <PolarRadiusAxis domain={[0, 5]} tick={false} axisLine={false} />
                      <Radar dataKey="A" stroke="#6366f1" strokeWidth={2} fill="#818cf8" fillOpacity={0.4} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </header>

          <details className="bg-white rounded-2xl shadow-sm border border-slate-200 mb-8 group overflow-hidden">
            <summary className="p-5 flex items-center justify-between cursor-pointer list-none [&::-webkit-details-marker]:hidden hover:bg-slate-50 transition-colors">
              <div className="flex items-center gap-2 font-extrabold text-slate-800 text-sm"><Users className="w-5 h-5 text-indigo-500" /><span>関連する議員を探す（同じ選挙区・会派）</span></div>
              <ChevronDown className="w-5 h-5 text-slate-400 group-open:rotate-180 transition-transform" />
            </summary>
            <div className="p-5 border-t border-slate-100 bg-slate-50/30">
              <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-bold w-fit mb-4">
                <button onClick={() => setRelatedTab('district')} className={`px-3 py-1.5 rounded-md transition-all ${relatedTab === 'district' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-slate-500 hover:text-slate-700'}`}>同じ選挙区（{selectedSpeaker.district}・{sameDistrictSpeakers.length}名）</button>
                <button onClick={() => setRelatedTab('party')} className={`px-3 py-1.5 rounded-md transition-all ${relatedTab === 'party' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-slate-500 hover:text-slate-700'}`}>同じ会派（{samePartySpeakers.length}名）</button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
                {(relatedTab === 'district' ? sameDistrictSpeakers : samePartySpeakers).map((rel) => (
                  <button key={rel.speaker} onClick={() => handleSpeakerClick(rel.speaker)} className="p-3 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all text-left flex flex-col justify-between group shadow-2xs bg-white">
                    <div>
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <span className="text-xs font-black text-slate-800 group-hover:text-indigo-600 transition-colors">{rel.speaker}</span>
                        <ArrowRight className="w-3 h-3 text-slate-300 group-hover:text-indigo-500 group-hover:translate-x-0.5 transition-all shrink-0" />
                      </div>
                      <span className={`px-1.5 py-0.2 text-[9px] font-bold rounded border inline-block ${rel.style.badgeClass}`}>{rel.style.label}</span>
                    </div>
                  </button>
                ))}
                {(relatedTab === 'district' ? sameDistrictSpeakers : samePartySpeakers).length === 0 && <div className="col-span-full py-6 text-center text-xs text-slate-400 bg-white rounded-xl">他に該当する議員が登録されていません。</div>}
              </div>
            </div>
          </details>

          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-6 bg-slate-50/80 p-3 rounded-xl border border-slate-200">
            <div className="text-xs font-bold text-slate-500">{selectedSpeaker.speaker} 議員の質疑ログ ({speakerFilteredThreads.length}件)</div>
            <div className="flex flex-wrap gap-2 w-full sm:w-auto">
              <div className="flex items-center bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 flex-grow sm:flex-grow-0">
                <PieChart className="w-3.5 h-3.5 text-indigo-500 mr-1.5 shrink-0" />
                <select value={speakerCategory} onChange={(e) => setSpeakerCategory(e.target.value)} className="bg-transparent text-slate-700 text-xs font-bold outline-none cursor-pointer w-full">
                  <option value="">全分野</option>
                  {topicStats.map(t => <option key={t.name} value={t.name}>{t.name}</option>)}
                </select>
              </div>
              <div className="flex items-center bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 flex-grow sm:flex-grow-0">
                <BarChart3 className="w-3.5 h-3.5 text-indigo-500 mr-1.5 shrink-0" />
                <select value={speakerSort} onChange={(e) => setSpeakerSort(e.target.value)} className="bg-transparent text-slate-700 text-xs font-bold outline-none cursor-pointer w-full">
                  <option value="recent">新着順</option><option value="solution">具体的対案を重視</option><option value="local_focus">現場解像度を重視</option><option value="constructive">議論の進展を重視</option><option value="evidence">客観データを重視</option>
                </select>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {speakerFilteredThreads.length > 0 ? speakerFilteredThreads.map((stmt) => <ThreadCard key={stmt.id} stmt={stmt} onViewContext={handleViewContext} showSpeakerHeader={false} />) : <div className="text-center py-12 bg-white rounded-xl border border-slate-200"><p className="text-slate-500 text-sm font-medium">条件に一致する質疑スレッドがありません。</p></div>}
          </div>
        </main>
      )}

      {/* 💡 画面下部 固定比較バー (1名以上選択されている場合に表示) */}
      {compareList.length > 0 && !isCompareMode && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 w-[92%] max-w-2xl bg-slate-900/95 backdrop-blur-md text-white p-3.5 rounded-2xl shadow-2xl border border-slate-700 flex items-center justify-between gap-3 animate-in slide-in-from-bottom-5">
          <div className="flex items-center gap-2 overflow-x-auto hide-scrollbar">
            <span className="text-xs font-bold text-slate-400 shrink-0 ml-1">
              比較中 ({compareList.length}/3):
            </span>
            {compareList.map(spk => (
              <span key={spk.speaker} className="inline-flex items-center gap-1.5 bg-slate-800 text-white text-xs font-bold px-2.5 py-1.5 rounded-lg border border-slate-700 shrink-0">
                {spk.speaker}
                <button onClick={(e) => toggleCompare(spk, e)} className="hover:text-rose-400"><X className="w-3 h-3" /></button>
              </span>
            ))}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <button onClick={() => setCompareList([])} className="text-[11px] text-slate-400 hover:text-white font-medium">クリア</button>
            <button
              onClick={executeCompare}
              disabled={compareList.length < 2}
              className={`px-4 py-2 rounded-xl text-xs font-black transition-all flex items-center gap-1.5 ${compareList.length >= 2 ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-500/30' : 'bg-slate-800 text-slate-500 cursor-not-allowed'}`}
            >
              <GitCompare className="w-4 h-4" />比較を実行
            </button>
          </div>
        </div>
      )}

      <TimelineModal isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />

      <footer className="bg-slate-900 text-slate-400 py-12 px-6 mt-10">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-10">
          <div className="space-y-4">
            <h3 className="text-white font-extrabold text-sm flex items-center"><Scale className="w-4 h-4 mr-2" />運営ポリシー・中立性の宣誓</h3>
            <p className="text-xs leading-relaxed">本プラットフォームは特定の政党・政治団体を支持または批判するものではありません。AI（Gemini）による客観的ルーブリック評価は、全議員に対して完全に同一のプロンプトと基準で機械的に適用されています。</p>
          </div>
          <div className="space-y-4 md:text-right">
            <h3 className="text-white font-extrabold text-sm">開発・運営</h3>
            <div className="text-xs space-y-1"><p>株式会社KICKs</p><p>代表 山本健人</p></div>
          </div>
        </div>
      </footer>
    </div>
  );
}