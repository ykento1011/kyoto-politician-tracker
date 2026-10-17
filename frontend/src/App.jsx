import React, { useState, useEffect, useMemo } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { 
  Search, Filter, Lightbulb, FileText, X, MessageCircle, 
  Loader2, ChevronUp, ChevronDown, Sparkles, Scale, Activity, ArrowLeft, User, Compass, Calendar
} from 'lucide-react';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
const supabase = createClient(supabaseUrl, supabaseKey);

const VALID_COUNCILORS = [
  "青野仁志", "赤阪仁", "天方ひろゆき", "井﨑敦子", "井崎敦子", "井上よしひろ", "宇佐美賢一",
  "江村理紗", "えもとかよこ", "大津裕太", "おんづか功", "片桐直哉", "加藤あい",
  "加藤昌洋", "神谷修平", "河合ようこ", "かわしま優子", "河村諒", "きくち一秀",
  "北尾ゆか", "北川みき", "北山ただお", "久保田正紀", "くまざわ真昭", "くらた共子",
  "こうち大輔", "小島信太郎", "さくらい泰広", "繁隆夫", "しまもと京司", "下村あきら",
  "菅谷浩平", "田中明秀", "田中たかのり", "谷口みゆき", "玉本なるみ", "津田大三",
  "寺田一博", "とがし豊", "富きくお", "中高しゅうじ", "中野洋一", "中村まり",
  "西野さち子", "西村義直", "西山信昌", "橋村芳和", "土方莉紗", "兵藤しんいち",
  "平井良人", "平田圭", "平山たかお", "平山よしかず", "増成竜治", "松田けい子",
  "みちはた弘之", "椋田隆知", "森かれん", "森田守", "森田ゆみ子", "もりもと英靖",
  "山田こうじ", "やまね智史", "山本恵一", "山本しゅうじ", "山本陽子", "湯浅光彦",
  "吉田孝雄"
];

const cleanName = (name) => name ? String(name).replace(/[\s ]+/g, '') : '';

const determineCouncilorStyle = (evidence, solution, localFocus, constructive) => {
  if (solution >= 3.5 && evidence >= 3.0) {
    return {
      label: "政策ビルダー型",
      desc: "具体的対案と客観データで制度設計・改善をリード",
      badgeClass: "bg-blue-50 text-blue-700 border-blue-200"
    };
  }
  if (constructive >= 3.5 && evidence >= 3.0) {
    return {
      label: "行政チェッカー型",
      desc: "行政答弁の論理破綻や制度不備を的確に追及・是正",
      badgeClass: "bg-rose-50 text-rose-700 border-rose-200"
    };
  }
  if (localFocus >= 4.0 && constructive >= 3.0) {
    return {
      label: "地域フロントライン型",
      desc: "生活現場・特定地域の課題を議場に持ち込み動かす",
      badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200"
    };
  }
  if (localFocus >= 3.5) {
    return {
      label: "現場代弁型",
      desc: "地域住民や当事者の切実な声を届ける",
      badgeClass: "bg-amber-50 text-amber-700 border-amber-200"
    };
  }
  return {
    label: "論点提起型",
    desc: "多角的な視点から市政の新たな論点を掘り起こす",
    badgeClass: "bg-purple-50 text-purple-700 border-purple-200"
  };
};

const cleanAuditorNote = (text) => {
  if (!text) return '';
  return text
    .replace(/\bevidence\s*:\s*/gi, '根拠・データ: ')
    .replace(/\bsolution\s*:\s*/gi, '対案・是正策: ')
    .replace(/\blocal_focus\s*:\s*/gi, '地域解像度: ')
    .replace(/\bconstructive\s*:\s*/gi, '議論の進展: ')
    .replace(/\bevidence\b/gi, '根拠・データ')
    .replace(/\bsolution\b/gi, '対案・是正策')
    .replace(/\blocal_focus\b/gi, '地域解像度')
    .replace(/\bconstructive\b/gi, '議論の進展');
};

export default function App() {
  const [statements, setStatements] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [sortPerspective, setSortPerspective] = useState('recent');
  const [selectedSpeaker, setSelectedSpeaker] = useState(null);

  const [selectedContext, setSelectedContext] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [isLoadingContext, setIsLoadingContext] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  useEffect(() => {
    fetchStatements();
  }, []);

  // 💡 静的JSONから超高速・ゼロAPIコストで取得
  const fetchStatements = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/data/statements_summary.json');
      if (!res.ok) throw new Error('静的データの取得に失敗しました');
      const allRecords = await res.json();

      const validData = [];
      allRecords.forEach(stmt => {
        const speakerName = cleanName(stmt.speaker);
        if (!VALID_COUNCILORS.includes(speakerName)) return;

        const ev = Number(stmt.evidence_score || 0);
        const sol = Number(stmt.solution_score || 0);
        const lf = Number(stmt.local_focus_score || 0);
        const cons = Number(stmt.constructive_score || 0);

        if (ev > 0 || sol > 0 || lf > 0 || cons > 0) {
          validData.push({
            ...stmt,
            evidence_score: ev,
            solution_score: sol,
            local_focus_score: lf,
            constructive_score: cons
          });
        }
      });

      setStatements(validData);
    } catch (err) {
      console.error('Fetch error:', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const speakerStats = useMemo(() => {
    const stats = {};
    statements.forEach(stmt => {
      const spk = stmt.speaker;
      if (!stats[spk]) {
        stats[spk] = {
          speaker: spk,
          count: 0,
          evidence_score: 0,
          solution_score: 0,
          local_focus_score: 0,
          constructive_score: 0,
          statements: [],
          categories: new Set(),
          latest_date: stmt.meeting_date || ""
        };
      }
      const s = stats[spk];
      s.count += 1;
      s.evidence_score += stmt.evidence_score;
      s.solution_score += stmt.solution_score;
      s.local_focus_score += stmt.local_focus_score;
      s.constructive_score += stmt.constructive_score;
      s.statements.push(stmt);

      if (stmt.meeting_date && stmt.meeting_date > s.latest_date) {
        s.latest_date = stmt.meeting_date;
      }

      if (stmt.category) {
        String(stmt.category).replace(/[\[\]'"]/g, '').split(',').forEach(c => {
          if (c.trim()) s.categories.add(c.trim());
        });
      }
    });

    return Object.values(stats).map(s => {
      const avgEv = Number((s.evidence_score / s.count).toFixed(1));
      const avgSol = Number((s.solution_score / s.count).toFixed(1));
      const avgLoc = Number((s.local_focus_score / s.count).toFixed(1));
      const avgCon = Number((s.constructive_score / s.count).toFixed(1));
      const style = determineCouncilorStyle(avgEv, avgSol, avgLoc, avgCon);

      return {
        ...s,
        avg_evidence: avgEv,
        avg_solution: avgSol,
        avg_local_focus: avgLoc,
        avg_constructive: avgCon,
        style: style,
        categories: Array.from(s.categories),
        statements: s.statements.sort((a, b) => new Date(b.meeting_date) - new Date(a.meeting_date))
      };
    }).sort((a, b) => b.count - a.count);
  }, [statements]);

  const filteredSpeakers = useMemo(() => {
    let list = speakerStats.filter((speaker) => {
      const query = searchQuery.toLowerCase();
      const speakerMatch = speaker.speaker?.toLowerCase().includes(query);
      const categoryMatch = selectedCategory ? speaker.categories.includes(selectedCategory) : true;
      return speakerMatch && categoryMatch;
    });

    if (sortPerspective === 'solution') {
      list.sort((a, b) => b.avg_solution - a.avg_solution);
    } else if (sortPerspective === 'local_focus') {
      list.sort((a, b) => b.avg_local_focus - a.avg_local_focus);
    } else if (sortPerspective === 'constructive') {
      list.sort((a, b) => b.avg_constructive - a.avg_constructive);
    } else if (sortPerspective === 'evidence') {
      list.sort((a, b) => b.avg_evidence - a.avg_evidence);
    }

    return list;
  }, [speakerStats, searchQuery, selectedCategory, sortPerspective]);

  // 💡 タイムライン表示時のみ Supabase から必要部分だけを取得
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
      const isOfficial = !VALID_COUNCILORS.includes(cleanName(item.speaker));
      return {
        ...item,
        is_target: item.sequence_number === targetSeq,
        is_admin: isOfficial,
        is_short_procedural: isShortProcedural
      };
    });
  };

  const formatSummaryRadar = (speaker) => [
    { subject: '根拠・データ', A: speaker.avg_evidence || 0, fullMark: 5 },
    { subject: '対案・是正', A: speaker.avg_solution || 0, fullMark: 5 },
    { subject: '地域解像度', A: speaker.avg_local_focus || 0, fullMark: 5 },
    { subject: '議論の進展', A: speaker.avg_constructive || 0, fullMark: 5 },
  ];

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans relative antialiased selection:bg-indigo-500 selection:text-white flex flex-col justify-between">
      <div>
        <nav className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200/80 transition-all">
          <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
            <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setSelectedSpeaker(null)}>
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
                <Scale className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-extrabold tracking-tight text-slate-900 text-base">議会のミカタ 京都</span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">CIVIC TECH</span>
                </div>
                <p className="text-[11px] text-slate-400 font-medium hidden sm:block">京都市議会 政策質疑の多角的可視化プラットフォーム</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 text-slate-600 text-xs font-medium">
                <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
                <span>AI客観ルーブリック監査</span>
              </div>
            </div>
          </div>
        </nav>

        {!selectedSpeaker && (
          <header className="relative bg-gradient-to-b from-white via-slate-50 to-[#F8FAFC] border-b border-slate-200/60 pt-12 pb-10 px-6">
            <div className="max-w-6xl mx-auto">
              <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div>
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-700 text-xs font-bold tracking-wide uppercase mb-3 border border-indigo-100">
                    <Activity className="w-3.5 h-3.5" />
                    Speech Quality Matrix
                  </div>
                  <h1 className="text-3xl md:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
                    文字数では見えない、議会論戦の「密度」と「個性」をAIで可視化。
                  </h1>
                  <p className="mt-2.5 text-slate-500 text-sm md:text-base max-w-2xl leading-relaxed">
                    定型的な議事進行や会派討論を自動除外。<br className="hidden sm:inline" />
                    「根拠・対案・地域性・進展」の4つの客観軸から、議員それぞれの質疑スタイルを紐解きます。
                  </p>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm min-w-[120px]">
                    <span className="text-[11px] font-bold text-slate-400 block uppercase tracking-wider">登録議員</span>
                    <span className="text-2xl font-black text-slate-900">{speakerStats.length}<span className="text-sm font-semibold text-slate-500 ml-1">名</span></span>
                  </div>
                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm min-w-[130px]">
                    <span className="text-[11px] font-bold text-slate-400 block uppercase tracking-wider">実質質疑スレッド</span>
                    <span className="text-2xl font-black text-indigo-600">{statements.length.toLocaleString()}<span className="text-sm font-semibold text-slate-500 ml-1">件</span></span>
                  </div>
                </div>
              </div>
            </div>
          </header>
        )}

        <main className="max-w-6xl mx-auto py-8 px-6">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-24 text-slate-400 space-y-3">
              <Loader2 className="w-7 h-7 animate-spin text-indigo-600" />
              <p className="text-sm font-medium">議会質疑データを読み込み中...</p>
            </div>
          ) : !selectedSpeaker ? (
            <>
              <div className="flex flex-col lg:flex-row justify-between items-center mb-8 gap-4 bg-white p-3.5 rounded-2xl shadow-sm border border-slate-200/80">
                <div className="relative w-full lg:w-72">
                  <Search className="absolute left-3.5 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
                  <input
                    type="text"
                    placeholder="議員名で検索..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all text-sm text-slate-800 placeholder-slate-400"
                  />
                </div>
                
                <div className="flex flex-wrap sm:flex-nowrap gap-3 w-full lg:w-auto">
                  <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 flex-grow sm:flex-grow-0">
                    <Compass className="w-4 h-4 text-indigo-600 shrink-0" />
                    <span className="text-xs font-bold text-slate-500 shrink-0 hidden sm:inline">重視する視点:</span>
                    <select 
                      value={sortPerspective}
                      onChange={(e) => setSortPerspective(e.target.value)}
                      className="bg-transparent text-slate-700 text-sm font-semibold outline-none cursor-pointer w-full"
                    >
                      <option value="recent">デフォルト（質疑数順）</option>
                      <option value="solution">具体的な対案・是正策を重視</option>
                      <option value="local_focus">生活現場・地域解像度を重視</option>
                      <option value="constructive">鋭い行政監視・進展を重視</option>
                      <option value="evidence">客観データ・根拠提示を重視</option>
                    </select>
                  </div>

                  <select 
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-700 text-sm font-medium outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all flex-grow sm:flex-grow-0"
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
                        </div>
                      </div>
                      
                      <div className="flex flex-col items-end">
                        <span className={`px-2.5 py-1 text-xs font-extrabold rounded-lg border shadow-2xs ${speaker.style.badgeClass}`}>
                          {speaker.style.label}
                        </span>
                        <span className="text-[10px] text-slate-400 mt-1.5 font-medium flex items-center">
                          <Calendar className="w-3 h-3 mr-0.5 inline" /> {speaker.latest_date}
                        </span>
                      </div>
                    </div>

                    <div className="p-5 flex-grow flex flex-col items-center justify-center relative">
                      <div className="absolute top-4 left-5">
                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">分析対象質疑</div>
                        <div className="text-base font-black text-slate-700">{speaker.count}<span className="text-xs font-medium text-slate-400 ml-0.5">スレッド</span></div>
                      </div>
                      
                      <div className="w-full h-40 mt-2">
                        <ResponsiveContainer width="100%" height="100%">
                          <RadarChart cx="50%" cy="50%" outerRadius="68%" data={formatSummaryRadar(speaker)}>
                            <PolarGrid stroke="#f1f5f9" />
                            <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 10, fontWeight: 600 }} />
                            <PolarRadiusAxis domain={[0, 5]} tick={false} axisLine={false} />
                            <Radar name="質疑特性" dataKey="A" stroke="#6366f1" strokeWidth={2} fill="#818cf8" fillOpacity={0.35} />
                          </RadarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                    
                    <div className="bg-slate-50 p-3 border-t border-slate-100 text-center text-xs font-bold text-indigo-600 group-hover:bg-indigo-50 transition-colors">
                      質疑スレッドと詳細特性を見る →
                    </div>
                  </article>
                ))}
              </div>
            </>
          ) : (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
              <button 
                onClick={() => setSelectedSpeaker(null)}
                className="mb-6 inline-flex items-center text-sm font-semibold text-slate-500 hover:text-indigo-600 transition-colors bg-white px-4 py-2 rounded-xl border border-slate-200 shadow-sm hover:shadow"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                議員一覧に戻る
              </button>

              <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div className="flex items-center gap-5">
                  <div className="w-16 h-16 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600 border border-indigo-100 shrink-0">
                    <User className="w-8 h-8" />
                  </div>
                  <div>
                    <div className="flex items-center gap-3 flex-wrap">
                      <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">{selectedSpeaker.speaker} <span className="text-lg font-medium text-slate-500">議員</span></h2>
                      <span className={`px-3 py-1 text-xs font-extrabold rounded-lg border ${selectedSpeaker.style.badgeClass}`}>
                        {selectedSpeaker.style.label}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1.5 font-medium">
                      {selectedSpeaker.style.desc}
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 shrink-0">
                   <div className="px-5 py-3 bg-slate-50 rounded-xl border border-slate-100 text-center">
                      <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">抽出スレッド数</span>
                      <span className="text-2xl font-black text-slate-800">{selectedSpeaker.count}<span className="text-xs font-medium text-slate-400 ml-1">件</span></span>
                   </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-7">
                {selectedSpeaker.statements.map((stmt) => {
                  const activeMetrics = [
                    { label: '根拠・データ', val: stmt.evidence_score, color: 'bg-indigo-500' },
                    { label: '対案・是正策', val: stmt.solution_score, color: 'bg-emerald-500' },
                    { label: '地域解像度', val: stmt.local_focus_score, color: 'bg-amber-500' },
                    { label: '議論の進展', val: stmt.constructive_score, color: 'bg-purple-500' },
                  ].filter(m => m.val > 0);

                  return (
                    <article key={stmt.id || `${stmt.meeting_id}_${stmt.sequence_number}`} className="bg-white rounded-2xl shadow-sm border border-slate-200/80 overflow-hidden hover:shadow-md hover:border-slate-300 transition-all duration-200 flex flex-col group">
                      <div className="p-6 border-b border-slate-100 flex justify-between items-start">
                        <div>
                          <div className="flex items-center space-x-2 mb-2.5">
                            <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 text-[11px] font-bold rounded-md tracking-wide">
                              {stmt.category ? String(stmt.category).replace(/[\[\]'"]/g, '') : "政策質疑"}
                            </span>
                            <span className="text-slate-400 text-xs font-medium">{stmt.meeting_date}</span>
                          </div>
                          <h2 className="text-lg font-extrabold text-slate-900 tracking-tight leading-tight line-clamp-2">
                            {stmt.meeting_title}
                          </h2>
                        </div>
                      </div>

                      <div className="p-6 flex-grow flex flex-col md:flex-row gap-6">
                        <div className="md:w-3/5 flex flex-col">
                          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center">
                            <FileText className="w-3.5 h-3.5 mr-1" />
                            質疑スレッド要旨
                          </h3>
                          <p className="text-slate-600 text-sm leading-relaxed mb-4 font-normal">
                            {stmt.summary}
                          </p>
                          
                          <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 mt-auto">
                            <div className="text-[10px] font-bold text-slate-400 mb-1 flex items-center">
                              <MessageCircle className="w-3 h-3 mr-1" />
                              スレッド起点発言 (#{stmt.sequence_number})
                            </div>
                            <p className="text-xs text-slate-500 line-clamp-2 italic">
                              「{stmt.statement_snippet || stmt.statement_text}」
                            </p>
                          </div>
                        </div>
                        
                        <div className="md:w-2/5 flex flex-col justify-center bg-slate-50/70 p-4 rounded-xl border border-slate-100/80">
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2.5 block">
                            本質疑の着目ポイント
                          </span>
                          {activeMetrics.length > 0 ? (
                            <div className="space-y-2">
                              {activeMetrics.map((metric) => (
                                <div key={metric.label}>
                                  <div className="flex justify-between text-xs font-bold text-slate-600 mb-0.5">
                                    <span className="text-[11px]">{metric.label}</span>
                                    <span className="font-mono text-[11px] text-slate-700">{metric.val} <span className="text-[9px] text-slate-400 font-normal">/ 5</span></span>
                                  </div>
                                  <div className="w-full bg-slate-200/80 h-1.5 rounded-full overflow-hidden">
                                    <div 
                                      className={`h-full ${metric.color} rounded-full transition-all duration-500`} 
                                      style={{ width: `${(metric.val / 5) * 100}%` }}
                                    />
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-center py-4 text-slate-400 text-xs font-medium">
                              論点整理・初期確認の質疑
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="bg-slate-50/60 p-5 mt-auto border-t border-slate-100 flex flex-col gap-3">
                        <div className="flex items-start bg-white p-3.5 rounded-xl border border-slate-200/70 shadow-2xs">
                          <Lightbulb className="w-4 h-4 text-amber-500 mt-0.5 mr-2.5 shrink-0" />
                          <div className="flex-1">
                            <h4 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">AI Auditor Note</h4>
                            <p className="text-xs text-slate-600 leading-relaxed font-normal whitespace-pre-line">
                              {cleanAuditorNote(stmt.scoring_reasoning)}
                            </p>
                          </div>
                        </div>
                        
                        <button 
                          onClick={() => handleViewContext(stmt)}
                          className="w-full py-2.5 flex items-center justify-center text-xs font-bold text-indigo-600 bg-white hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 rounded-xl transition-all shadow-2xs"
                        >
                          <MessageCircle className="w-3.5 h-3.5 mr-1.5 text-indigo-500" />
                          市側答弁を含む一連のタイムラインを表示
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          )}
        </main>
      </div>

      <footer className="bg-white border-t border-slate-200 mt-20 py-10 px-6">
        <div className="max-w-6xl mx-auto text-center space-y-3">
          <div className="flex items-center justify-center space-x-2 text-slate-800 font-extrabold text-sm">
            <Scale className="w-4 h-4 text-indigo-600" />
            <span>議会のミカタ 京都</span>
          </div>
          <p className="text-xs text-slate-500 max-w-2xl mx-auto leading-relaxed">
            本ツールは特定の政党・団体・会派を支持または批判するものではありません。AIによる客観的ルーブリック分析は全議員に同一基準で適用されています。なお、本分析は議場内での質疑スレッドのみを対象としており、議場外での政策活動や地域活動等は評価対象外です。
          </p>
          <p className="text-[11px] text-slate-400">
            開発・運営：株式会社KICKs 代表 山本健人（元米国公認会計士・行政書士・京大MBA）
          </p>
        </div>
      </footer>

      {isPanelOpen && (
        <>
          <div 
            className="fixed inset-0 bg-slate-900/30 backdrop-blur-xs z-40 transition-opacity"
            onClick={() => setIsPanelOpen(false)}
          />

          <div className="fixed inset-y-0 right-0 w-full max-w-3xl bg-white shadow-2xl z-50 flex flex-col">
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
                            {msg.speaker} {msg.is_admin ? '(市側/進行)' : ''}
                          </span>
                          {msg.is_target && (
                            <span className="bg-indigo-600 text-white text-[9px] font-bold px-1.5 py-0.2 rounded">
                              評価対象起点
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
                              <span className="text-[11px] font-bold text-indigo-900 uppercase tracking-wide">AI Auditor Note</span>
                            </div>
                            <p className="text-xs text-indigo-950 leading-relaxed font-normal whitespace-pre-line">
                              {cleanAuditorNote(selectedContext.statement.scoring_reasoning)}
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
        </>
      )}
    </div>
  );
}