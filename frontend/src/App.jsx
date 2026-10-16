import React, { useState, useEffect, useMemo } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { 
  Search, Filter, Lightbulb, FileText, X, MessageCircle, 
  Loader2, ChevronUp, ChevronDown, Sparkles, Scale, Activity, CheckCircle2, ArrowLeft, User
} from 'lucide-react';
import { supabase } from './supabaseClient';

export default function App() {
  const [statements, setStatements] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  
  // 画面遷移用の状態（null: 議員一覧ビュー、object: その議員の詳細ビュー）
  const [selectedSpeaker, setSelectedSpeaker] = useState(null);

  // スライドパネル（文脈表示）用の状態管理
  const [selectedContext, setSelectedContext] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [isLoadingContext, setIsLoadingContext] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  // 1. Supabaseから評価対象となった実質的質疑（スコア > 0）を全件取得
  useEffect(() => {
    fetchStatements();
  }, []);

  const fetchStatements = async () => {
    setIsLoading(true);
    try {
      const { data, error } = await supabase
        .from('statements')
        .select('*')
        .gt('total_quality_score', 0)
        .order('meeting_date', { ascending: false });

      if (error) throw error;
      setStatements(data || []);
    } catch (err) {
      console.error('Supabase fetch error:', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // 2. 取得した発言データを「議員単位」でグループ化・集計する
  const speakerStats = useMemo(() => {
    const stats = {};
    statements.forEach(stmt => {
      if (!stats[stmt.speaker]) {
        stats[stmt.speaker] = {
          speaker: stmt.speaker,
          count: 0,
          total_quality_score: 0,
          evidence_score: 0,
          solution_score: 0,
          local_focus_score: 0,
          constructive_score: 0,
          statements: [],
          categories: new Set(),
        };
      }
      const s = stats[stmt.speaker];
      s.count += 1;
      s.total_quality_score += stmt.total_quality_score;
      s.evidence_score += stmt.evidence_score;
      s.solution_score += stmt.solution_score;
      s.local_focus_score += stmt.local_focus_score;
      s.constructive_score += stmt.constructive_score;
      s.statements.push(stmt);
      
      // カンマ区切りの複数カテゴリ（"財政, 福祉"など）を分割してセットに保存
      if (stmt.category) {
          stmt.category.split(',').forEach(c => s.categories.add(c.trim()));
      }
    });

    // 平均値を算出し、スコアが高い順に並び替え
    return Object.values(stats).map(s => ({
      ...s,
      avg_total: Math.round(s.total_quality_score / s.count),
      avg_evidence: Number((s.evidence_score / s.count).toFixed(1)),
      avg_solution: Number((s.solution_score / s.count).toFixed(1)),
      avg_local_focus: Number((s.local_focus_score / s.count).toFixed(1)),
      avg_constructive: Number((s.constructive_score / s.count).toFixed(1)),
      categories: Array.from(s.categories),
      // 個別の発言は新しい順にソートしておく
      statements: s.statements.sort((a, b) => new Date(b.meeting_date) - new Date(a.meeting_date))
    })).sort((a, b) => b.avg_total - a.avg_total); 
  }, [statements]);

  // 3. 検索と絞り込み（議員一覧に対するフィルター）
  const filteredSpeakers = speakerStats.filter((speaker) => {
    const query = searchQuery.toLowerCase();
    const speakerMatch = speaker.speaker?.toLowerCase().includes(query);
    const categoryMatch = selectedCategory ? speaker.categories.includes(selectedCategory) : true;
    return speakerMatch && categoryMatch;
  });

  // 4. 文脈（タイムライン）取得用ロジック
  const handleViewContext = async (stmt) => {
    setIsPanelOpen(true);
    setIsLoadingContext(true);
    setSelectedContext({ statement: stmt, context: [] });

    const startSeq = Math.max(1, stmt.sequence_number - 15);
    const endSeq = stmt.sequence_number + 15;

    try {
      const { data, error } = await supabase
        .from('statements')
        .select('*')
        .eq('meeting_id', stmt.meeting_id)
        .gte('sequence_number', startSeq)
        .lte('sequence_number', endSeq)
        .order('sequence_number', { ascending: true });

      if (error) throw error;
      const formatted = formatContextMessages(data || [], stmt.sequence_number);
      setSelectedContext({ statement: stmt, context: formatted });
    } catch (err) {
      console.error('Context fetch error:', err.message);
    } finally {
      setIsLoadingContext(false);
    }
  };

  const handleLoadMoreContext = async (direction) => {
    if (!selectedContext?.context?.length || isLoadingMore) return;
    setIsLoadingMore(true);

    const currentSeqs = selectedContext.context.map(c => c.sequence_number);
    const minSeq = Math.min(...currentSeqs);
    const maxSeq = Math.max(...currentSeqs);
    const meetingId = selectedContext.statement.meeting_id;

    try {
      let query = supabase.from('statements').select('*').eq('meeting_id', meetingId);

      if (direction === 'prev') {
        const fetchStart = Math.max(1, minSeq - 15);
        query = query.gte('sequence_number', fetchStart).lt('sequence_number', minSeq).order('sequence_number', { ascending: true });
      } else {
        query = query.gt('sequence_number', maxSeq).lte('sequence_number', maxSeq + 15).order('sequence_number', { ascending: true });
      }

      const { data, error } = await query;
      if (error) throw error;

      if (data && data.length > 0) {
        const formattedNew = formatContextMessages(data, selectedContext.statement.sequence_number);
        const merged = direction === 'prev' 
          ? [...formattedNew, ...selectedContext.context]
          : [...selectedContext.context, ...formattedNew];

        setSelectedContext(prev => ({ ...prev, context: merged }));
      }
    } catch (err) {
      console.error('Load more context error:', err.message);
    } finally {
      setIsLoadingMore(false);
    }
  };

  const formatContextMessages = (rawList, targetSeq) => {
    return rawList.map((item) => {
      const text = (item.statement_text || '').trim();
      const isShortProcedural = text.length < 35 && (
        text.endsWith('委員。') || text.endsWith('議員。') || text.endsWith('部長。') || 
        text.endsWith('局長。') || text.includes('異議なし') || text.includes('開会いたします') || text.includes('散会いたします')
      );
      return {
        ...item,
        is_target: item.sequence_number === targetSeq,
        is_admin: item.total_quality_score === 0 && !item.speaker?.includes('委員') && !item.speaker?.includes('議員'),
        is_short_procedural: isShortProcedural
      };
    });
  };

  // サマリーカード用（短縮ラベル）
  const formatSummaryRadar = (speaker) => [
    { subject: '根拠', A: speaker.avg_evidence || 0, fullMark: 5 },
    { subject: '対案', A: speaker.avg_solution || 0, fullMark: 5 },
    { subject: '地域', A: speaker.avg_local_focus || 0, fullMark: 5 },
    { subject: '進展', A: speaker.avg_constructive || 0, fullMark: 5 },
  ];

  // 個別発言カード用
  const formatDetailRadar = (statement) => [
    { subject: '根拠・データ', A: statement.evidence_score || 0, fullMark: 5 },
    { subject: '対案・解決策', A: statement.solution_score || 0, fullMark: 5 },
    { subject: '地域解像度', A: statement.local_focus_score || 0, fullMark: 5 },
    { subject: '議論の進展', A: statement.constructive_score || 0, fullMark: 5 },
  ];

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans relative antialiased selection:bg-indigo-500 selection:text-white">
      
      {/* 1. Global Navigation Bar */}
      <nav className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200/80 transition-all">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setSelectedSpeaker(null)}>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold tracking-tight text-slate-900 text-base">KYOTO CIVIC PULSE</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">BETA</span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium hidden sm:block">京都市議会 AI政策監査プラットフォーム</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 text-slate-600 text-xs font-medium">
              <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
              <span>Gemini 2.5 Flash</span>
            </div>
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200/60 text-emerald-700 text-xs font-semibold">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span>LIVE AUDIT</span>
            </div>
          </div>
        </div>
      </nav>

      {/* 2. Hero Section (一覧表示時のみ表示) */}
      {!selectedSpeaker && (
        <header className="relative bg-gradient-to-b from-white via-slate-50 to-[#F8FAFC] border-b border-slate-200/60 pt-12 pb-10 px-6">
          <div className="max-w-6xl mx-auto">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
              <div>
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-700 text-xs font-bold tracking-wide uppercase mb-3 border border-indigo-100">
                  <Activity className="w-3.5 h-3.5" />
                  Council Speech Quality Index
                </div>
                <h1 className="text-3xl md:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
                  議会質疑の「密度」を可視化する。
                </h1>
                <p className="mt-2.5 text-slate-500 text-sm md:text-base max-w-2xl leading-relaxed">
                  定型的な進行や行政の答弁をAIで自動除外。<br className="hidden sm:inline" />
                  「事実根拠・対案・地域課題」に基づいた実質的な政策質疑のみを議員ごとに集約して評価します。
                </p>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm min-w-[120px]">
                  <span className="text-[11px] font-bold text-slate-400 block uppercase tracking-wider">評価対象議員</span>
                  <span className="text-2xl font-black text-slate-900">{speakerStats.length}<span className="text-sm font-semibold text-slate-500 ml-1">名</span></span>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm min-w-[130px]">
                  <span className="text-[11px] font-bold text-slate-400 block uppercase tracking-wider">実質質疑 総数</span>
                  <span className="text-2xl font-black text-indigo-600">{statements.length}<span className="text-sm font-semibold text-slate-500 ml-1">件</span></span>
                </div>
              </div>
            </div>
          </div>
        </header>
      )}

      {/* 3. Main Content Area */}
      <main className="max-w-6xl mx-auto py-8 px-6">
        
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-24 text-slate-400 space-y-3">
            <Loader2 className="w-7 h-7 animate-spin text-indigo-600" />
            <p className="text-sm font-medium">Supabaseから監査データを同期中...</p>
          </div>
        ) : !selectedSpeaker ? (
          /* =========================================
             ビュー A: 議員一覧（サマリーカード）
          ========================================== */
          <>
            {/* フィルタバー */}
            <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4 bg-white p-3.5 rounded-2xl shadow-sm border border-slate-200/80">
              <div className="relative w-full md:w-96">
                <Search className="absolute left-3.5 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder="議員名で検索..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all text-sm text-slate-800 placeholder-slate-400"
                />
              </div>
              <div className="flex gap-3 w-full md:w-auto">
                <select 
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-700 text-sm font-medium outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all flex-grow md:flex-grow-0"
                >
                  <option value="">全政策分野</option>
                  <option value="都市計画">都市計画</option>
                  <option value="防災・減災">防災・減災</option>
                  <option value="福祉・医療">福祉・医療</option>
                  <option value="子育て・教育">子育て・教育</option>
                  <option value="財政・行革">財政・行革</option>
                  <option value="環境・エネルギー">環境・エネルギー</option>
                </select>
              </div>
            </div>

            {/* 議員グリッド */}
            {filteredSpeakers.length === 0 ? (
              <div className="text-center py-20 bg-white rounded-2xl border border-slate-200 p-8 shadow-sm">
                <div className="w-12 h-12 rounded-full bg-slate-50 text-slate-400 flex items-center justify-center mx-auto mb-3">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <p className="text-slate-700 font-bold">該当する議員データがありません</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredSpeakers.map((speaker) => (
                  <article 
                    key={speaker.speaker} 
                    onClick={() => setSelectedSpeaker(speaker)}
                    className="bg-white rounded-2xl shadow-sm border border-slate-200/80 overflow-hidden hover:shadow-lg hover:border-indigo-300 transition-all duration-300 cursor-pointer flex flex-col group relative"
                  >
                    <div className="p-6 border-b border-slate-100 flex justify-between items-start bg-gradient-to-br from-white to-slate-50">
                      <div>
                        <h2 className="text-xl font-extrabold text-slate-900 tracking-tight mb-2 group-hover:text-indigo-700 transition-colors">
                          {speaker.speaker} <span className="text-xs font-medium text-slate-500 ml-1">議員</span>
                        </h2>
                        <div className="flex flex-wrap gap-1.5">
                          {speaker.categories.slice(0, 3).map(cat => (
                             <span key={cat} className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] font-bold rounded-md border border-slate-200">
                               {cat}
                             </span>
                          ))}
                          {speaker.categories.length > 3 && (
                             <span className="px-2 py-0.5 bg-slate-100 text-slate-500 text-[10px] font-bold rounded-md">+{speaker.categories.length - 3}</span>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex flex-col items-center justify-center bg-indigo-50 border border-indigo-100 rounded-xl p-3 w-16 h-16 shrink-0 group-hover:bg-indigo-600 group-hover:border-indigo-600 transition-colors">
                        <span className="text-[8px] text-indigo-500 font-bold uppercase tracking-wider mb-0.5 group-hover:text-indigo-200">Avg</span>
                        <span className="text-xl font-black text-indigo-700 leading-none group-hover:text-white">{speaker.avg_total}</span>
                      </div>
                    </div>

                    <div className="p-5 flex-grow flex flex-col items-center justify-center relative">
                      <div className="absolute top-4 left-5">
                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">抽出質疑数</div>
                        <div className="text-lg font-black text-slate-700">{speaker.count}<span className="text-xs font-medium text-slate-400 ml-0.5">件</span></div>
                      </div>
                      
                      <div className="w-full h-36 mt-2">
                        <ResponsiveContainer width="100%" height="100%">
                          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={formatSummaryRadar(speaker)}>
                            <PolarGrid stroke="#f1f5f9" />
                            <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 10, fontWeight: 600 }} />
                            <PolarRadiusAxis angle={30} domain={[0, 5]} tick={false} axisLine={false} />
                            <Radar name="Avg Score" dataKey="A" stroke="#6366f1" strokeWidth={2} fill="#818cf8" fillOpacity={0.4} />
                          </RadarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                    
                    <div className="bg-slate-50 p-3 border-t border-slate-100 text-center text-xs font-bold text-indigo-600 group-hover:bg-indigo-50 transition-colors">
                      この議員の質疑一覧を見る →
                    </div>
                  </article>
                ))}
              </div>
            )}
          </>
        ) : (
          /* =========================================
             ビュー B: 議員詳細（個別発言ドリルダウン）
          ========================================== */
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
            {/* 戻るボタン */}
            <button 
              onClick={() => setSelectedSpeaker(null)}
              className="mb-6 inline-flex items-center text-sm font-semibold text-slate-500 hover:text-indigo-600 transition-colors bg-white px-4 py-2 rounded-xl border border-slate-200 shadow-sm hover:shadow"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              議員一覧に戻る
            </button>

            {/* プロフィールヘッダー */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 mb-8 flex flex-col md:flex-row justify-between items-center gap-6">
              <div className="flex items-center gap-5">
                <div className="w-16 h-16 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600 border border-indigo-100">
                  <User className="w-8 h-8" />
                </div>
                <div>
                  <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">{selectedSpeaker.speaker} <span className="text-lg font-medium text-slate-500">議員</span></h2>
                  <p className="text-sm text-slate-500 mt-1 font-medium">評価対象の実質質疑: <span className="text-indigo-600 font-bold">{selectedSpeaker.count}件</span></p>
                </div>
              </div>
              <div className="flex gap-4">
                 <div className="text-center px-6 py-3 bg-slate-50 rounded-xl border border-slate-100">
                    <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Average Score</span>
                    <span className="text-3xl font-black text-indigo-600">{selectedSpeaker.avg_total}</span>
                 </div>
              </div>
            </div>

            {/* 個別発言グリッド */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-7">
              {selectedSpeaker.statements.map((stmt) => (
                <article key={stmt.id} className="bg-white rounded-2xl shadow-sm border border-slate-200/80 overflow-hidden hover:shadow-md hover:border-slate-300 transition-all duration-200 flex flex-col group">
                  <div className="p-6 border-b border-slate-100 flex justify-between items-start">
                    <div>
                      <div className="flex items-center space-x-2 mb-2.5">
                        <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 text-[11px] font-bold rounded-md tracking-wide">
                          {stmt.category}
                        </span>
                        <span className="text-slate-400 text-xs font-medium">{stmt.meeting_date}</span>
                      </div>
                      <h2 className="text-lg font-extrabold text-slate-900 tracking-tight leading-tight line-clamp-2">
                        {stmt.meeting_title}
                      </h2>
                    </div>
                    
                    <div className="flex flex-col items-center justify-center bg-slate-50 border border-slate-200/80 rounded-xl p-3 w-20 h-20 shrink-0">
                      <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider mb-0.5">SCORE</span>
                      <span className="text-2xl font-black text-indigo-600 leading-none">{stmt.total_quality_score}</span>
                    </div>
                  </div>

                  <div className="p-6 flex-grow flex flex-col sm:flex-row gap-6">
                    <div className="sm:w-3/5 flex flex-col">
                      <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center">
                        <FileText className="w-3.5 h-3.5 mr-1" />
                        発言要旨
                      </h3>
                      <p className="text-slate-600 text-sm leading-relaxed mb-4 font-normal">
                        {stmt.summary}
                      </p>
                    </div>
                    
                    <div className="sm:w-2/5 h-40 relative -mt-2">
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={formatDetailRadar(stmt)}>
                          <PolarGrid stroke="#f1f5f9" />
                          <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 10, fontWeight: 600 }} />
                          <PolarRadiusAxis angle={30} domain={[0, 5]} tick={false} axisLine={false} />
                          <Radar name="Score" dataKey="A" stroke="#6366f1" strokeWidth={2} fill="#818cf8" fillOpacity={0.3} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="bg-slate-50/60 p-5 mt-auto border-t border-slate-100 flex flex-col gap-3">
                    <div className="flex items-start bg-white p-3.5 rounded-xl border border-slate-200/70 shadow-2xs">
                      <Lightbulb className="w-4 h-4 text-amber-500 mt-0.5 mr-2.5 shrink-0" />
                      <div>
                        <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">AI Auditor Note</h4>
                        <p className="text-xs text-slate-500 leading-relaxed font-normal">
                          {stmt.scoring_reasoning}
                        </p>
                      </div>
                    </div>
                    
                    <button 
                      onClick={() => handleViewContext(stmt)}
                      className="w-full py-2.5 flex items-center justify-center text-xs font-bold text-indigo-600 bg-white hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 rounded-xl transition-all shadow-2xs"
                    >
                      <MessageCircle className="w-3.5 h-3.5 mr-1.5 text-indigo-500" />
                      質疑前後の議事録タイムラインを表示
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* --- Context Slide-Over Modal --- */}
      <div 
        className={`fixed inset-0 bg-slate-900/30 backdrop-blur-xs z-40 transition-opacity duration-300 ${isPanelOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
        onClick={() => setIsPanelOpen(false)}
      />

      <div className={`fixed inset-y-0 right-0 w-full max-w-3xl bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col ${isPanelOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-white shadow-2xs z-10">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center">
              <MessageCircle className="w-4 h-4 mr-2 text-indigo-600" />
              会議録タイムライン
            </h2>
            <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">
              {selectedContext?.statement?.meeting_title} ({selectedContext?.statement?.meeting_date})
            </p>
          </div>
          <button 
            onClick={() => setIsPanelOpen(false)}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 bg-slate-50 space-y-4">
          {isLoadingContext ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 space-y-3">
              <Loader2 className="w-7 h-7 animate-spin text-indigo-600" />
              <p className="text-xs font-medium">発言タイムラインを取得中...</p>
            </div>
          ) : selectedContext?.context?.length > 0 ? (
            <>
              <div className="text-center pb-2">
                <button
                  onClick={() => handleLoadMoreContext('prev')}
                  disabled={isLoadingMore}
                  className="inline-flex items-center text-xs font-medium text-slate-500 hover:text-indigo-600 bg-white border border-slate-200 px-3.5 py-1 rounded-full shadow-2xs transition-all disabled:opacity-50"
                >
                  <ChevronUp className="w-3 h-3 mr-1" />
                  これより前の発言を読み込む
                </button>
              </div>

              {selectedContext.context.map((msg, idx) => {
                if (msg.is_short_procedural && !msg.is_target) {
                  return (
                    <div key={idx} className="flex items-center justify-center my-1 text-slate-400 text-xs">
                      <div className="h-px bg-slate-200 flex-grow max-w-[50px]" />
                      <span className="mx-2.5 font-medium bg-slate-100 text-slate-500 px-2.5 py-0.5 rounded-full text-[10px] border border-slate-200/50">
                        #{msg.sequence_number} {msg.speaker}: {msg.statement_text.trim()}
                      </span>
                      <div className="h-px bg-slate-200 flex-grow max-w-[50px]" />
                    </div>
                  );
                }

                return (
                  <div 
                    key={idx} 
                    className={`flex flex-col ${msg.is_target ? 'items-end' : 'items-start'}`}
                  >
                    <div className={`flex items-center space-x-1.5 mb-1 ${msg.is_target ? 'flex-row-reverse space-x-reverse mr-1' : 'ml-1'}`}>
                      <span className="text-[10px] font-mono text-slate-400">
                        #{msg.sequence_number}
                      </span>
                      <span className={`text-xs font-bold ${msg.is_target ? 'text-indigo-600' : 'text-slate-600'}`}>
                        {msg.speaker} {msg.is_admin ? '(市理事者/職員)' : ''}
                      </span>
                      {msg.is_target && (
                        <span className="bg-indigo-600 text-white text-[9px] font-bold px-1.5 py-0.2 rounded">
                          評価対象
                        </span>
                      )}
                    </div>
                    
                    <div 
                      className={`
                        max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap shadow-2xs
                        ${msg.is_target 
                          ? 'bg-indigo-600 text-white rounded-tr-none' 
                          : msg.is_admin 
                            ? 'bg-white border border-slate-200 text-slate-700 rounded-tl-none font-normal' 
                            : 'bg-slate-200/70 text-slate-600 rounded-tl-none'
                        }
                      `}
                    >
                      {msg.statement_text}
                    </div>

                    {msg.is_target && selectedContext.statement && (
                      <div className="mt-2.5 max-w-[88%] bg-indigo-50 border border-indigo-100 rounded-xl p-3.5 mr-1 shadow-2xs">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="bg-indigo-600 text-white text-[10px] font-bold px-2 py-0.5 rounded shadow-2xs">
                            Score: {selectedContext.statement.total_quality_score}
                          </span>
                          <span className="text-[11px] font-bold text-indigo-900 uppercase tracking-wide">AI Auditor Note</span>
                        </div>
                        <p className="text-xs text-indigo-950 leading-relaxed font-normal">
                          {selectedContext.statement.scoring_reasoning}
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}

              <div className="text-center pt-2">
                <button
                  onClick={() => handleLoadMoreContext('next')}
                  disabled={isLoadingMore}
                  className="inline-flex items-center text-xs font-medium text-slate-500 hover:text-indigo-600 bg-white border border-slate-200 px-3.5 py-1 rounded-full shadow-2xs transition-all disabled:opacity-50"
                >
                  <ChevronDown className="w-3 h-3 mr-1" />
                  これより後の発言を読み込む
                </button>
              </div>
            </>
          ) : (
            <div className="text-center text-slate-400 mt-10">
              <p className="text-xs">文脈データが見つかりませんでした。</p>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}