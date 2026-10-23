import React, { useState, useMemo, useEffect } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import {
  ArrowLeft, GitCompare, User, Landmark, ExternalLink, Globe,
  Sparkles, TrendingUp, Users, ChevronDown, ArrowRight,
  MessageCircle, Scale, PieChart, BarChart3, CheckCircle2, XCircle,
  Layers, BookmarkCheck, FileText, Check, AlertCircle, ShieldCheck, BookOpen
} from 'lucide-react';
import ThreadCard from './ThreadCard';
import { openOfficialMinute, getOfficialLinkTooltip } from '../utils/officialLink';
import { cleanStyleLabel, cleanStyleDesc } from '../utils/styleHelpers';

// 異体字・旧字体・選挙公報通称名（ひらがな）エイリアス辞書
const ALIAS_MAP = {
  // 異体字・旧字体
  '井崎敦子': '井﨑敦子',
  '井﨑敦子': '井崎敦子',
  '繁隆夫': '繁隆夫',
  '繁隆夫': '繁隆夫',

  // 💡 選挙公報原本（ひらがな・通称名）との完全マッピング
  '西山信昌': '西山のぶまさ',
  '西山のぶまさ': '西山信昌',
  '青野仁志': '青野ひとし',
  '青野ひとし': '青野仁志',
  '宇佐美賢一': '宇佐美けんいち',
  '宇佐美けんいち': '宇佐美賢一',
  '江村理紗': '江村りさ',
  '江村りさ': '江村理紗',
  '大津裕太': '大津ゆうた',
  '大津ゆうた': '大津裕太',
  '河村諒': '河村りょう',
  '河村りょう': '河村諒',
  'きくち一秀': 'きくちかずひで',
  'きくちかずひで': 'きくち一秀',
  '小島信太郎': 'こじま信太郎',
  'こじま信太郎': '小島信太郎',
  '繁隆夫': 'しげ隆夫',
  'しげ隆夫': '繁隆夫',
  'しまもと京司': '島本きょうじ',
  '島本きょうじ': 'しまもと京司',
  '田中明秀': '田中あきひで',
  '田中あきひで': '田中明秀',
  '寺田一博': '寺田かずひろ',
  '寺田かずひろ': '寺田一博',
  '土方莉紗': '土方りさ',
  '土方りさ': '土方莉紗',
  '橋村芳和': 'はしむら芳和',
  'はしむら芳和': '橋村芳和',
  '平田圭': '平田けい',
  '平田けい': '平田圭',
  '増成竜治': 'ますなり竜治',
  'ますなり竜治': '増成竜治',
  '椋田隆知': 'ムクダ隆知',
  'ムクダ隆知': '椋田隆知',
  '湯浅光彦': 'ゆあさ光彦',
  'ゆあさ光彦': '湯浅光彦',
  '吉田孝雄': '吉田たかお',
  '吉田たかお': '吉田孝雄',
};

export default function SpeakerDetailView({
  selectedSpeaker,
  speakerStats,
  speakerFilteredThreads,
  topicStats,
  speakerCategory,
  setSpeakerCategory,
  speakerSort,
  setSpeakerSort,
  votesData,
  issuesMap,
  onOpenCompare,
  onBack,
  onSpeakerClick,
  onViewContext,
  onOpenMethodology,
  onSelectBill
}) {
  const [relatedTab, setRelatedTab] = useState('district');
  const [speakerDetailTab, setSpeakerDetailTab] = useState('threads');
  const [speakerVoteFilter, setSpeakerVoteFilter] = useState('contested');
  const [pledgeTrackerMap, setPledgeTrackerMap] = useState({});

  useEffect(() => {
    fetch('/data/pledge_tracker.json')
      .then(res => res.ok ? res.json() : {})
      .then(data => setPledgeTrackerMap(data))
      .catch(err => console.error("Failed to load pledge tracker data:", err));
  }, []);

const currentSpeakerTracker = useMemo(() => {
    if (!selectedSpeaker || !selectedSpeaker.speaker) return null;
    const name = selectedSpeaker.speaker.replace(/[\s ]+/g, '');
    const alias = ALIAS_MAP[name];
    return pledgeTrackerMap[name] || (alias ? pledgeTrackerMap[alias] : null) || null;
  }, [selectedSpeaker, pledgeTrackerMap]);

  const handleViewStatementContext = (stmtRecord) => {
    if (!stmtRecord || !onViewContext) return;
    const allStmts = selectedSpeaker?.statements || actualThreads || [];
    const targetId = stmtRecord.speech_id || stmtRecord.id;
    
    let target = allStmts.find(s => s.id === targetId);
    if (!target) {
      target = allStmts.find(s => s.meeting_date === stmtRecord.date && (s.summary === stmtRecord.summary || s.summary?.includes(stmtRecord.summary?.slice(0, 15))));
    }
    if (!target) {
      target = {
        ...stmtRecord,
        id: targetId || `pledge_stmt_${stmtRecord.date}`,
        speaker: selectedSpeaker?.speaker,
        meeting_date: stmtRecord.date,
        meeting_title: stmtRecord.committee,
        committee_name: stmtRecord.committee,
        category: selectedSpeaker?.topCategories?.[0] || '市政全般'
      };
    }
    onViewContext(target);
  };

  const cleanName = selectedSpeaker?.speaker ? selectedSpeaker.speaker.replace(/\s+/g, '') : '';
  const [detailPhotoSrc, setDetailPhotoSrc] = useState(`/councilors/${cleanName}.jpg`);
  const [detailFallbackTried, setDetailFallbackTried] = useState(false);

  const handleDetailPhotoError = () => {
    if (!detailFallbackTried && ALIAS_MAP[cleanName]) {
      setDetailFallbackTried(true);
      setDetailPhotoSrc(`/councilors/${ALIAS_MAP[cleanName]}.jpg`);
    }
  };

  const formatSummaryRadar = (speaker) => [
    { subject: '根拠・データ', A: speaker.avg_evidence || 0, fullMark: 5 },
    { subject: '対案・是正', A: speaker.avg_solution || 0, fullMark: 5 },
    { subject: '地域解像度', A: speaker.avg_local_focus || 0, fullMark: 5 },
    { subject: '議論の進展', A: speaker.avg_constructive || 0, fullMark: 5 },
  ];

  const topicBreakdown = useMemo(() => {
    if (!selectedSpeaker || !selectedSpeaker.catCounts) return [];
    const total = selectedSpeaker.count || 1;
    return Object.entries(selectedSpeaker.catCounts)
      .map(([cat, cnt]) => ({
        category: cat,
        count: cnt,
        percentage: Math.round((cnt / total) * 100)
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 3);
  }, [selectedSpeaker]);

  const actualThreads = useMemo(() => {
    if (speakerFilteredThreads && speakerFilteredThreads.length > 0) {
      return speakerFilteredThreads;
    }
    let list = selectedSpeaker?.statements ? [...selectedSpeaker.statements] : [];
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
  }, [speakerFilteredThreads, selectedSpeaker, speakerCategory, speakerSort]);

  const featuredThread = useMemo(() => {
    const stmts = selectedSpeaker?.statements || actualThreads;
    if (!stmts || stmts.length === 0) return null;

    return [...stmts].sort((a, b) => {
      const scoreA = (a.solution_score || 0) + (a.evidence_score || 0) + (a.local_focus_score || 0) + (a.constructive_score || 0);
      const scoreB = (b.solution_score || 0) + (b.evidence_score || 0) + (b.local_focus_score || 0) + (b.constructive_score || 0);
      if (scoreB !== scoreA) return scoreB - scoreA;
      return new Date(b.meeting_date) - new Date(a.meeting_date);
    })[0];
  }, [selectedSpeaker, actualThreads]);

  // 💡 人物評価を排除し、質疑データの事実記述のみに統一
  const generateCouncilorProfileSummary = (speaker) => {
    if (!speaker) return "";
    const categoriesStr = speaker.topCategories && speaker.topCategories.length > 0 ? speaker.topCategories.join("・") : "市政全般";
    const metrics = [
      { key: 'solution', val: speaker.avg_solution },
      { key: 'local_focus', val: speaker.avg_local_focus },
      { key: 'evidence', val: speaker.avg_evidence },
      { key: 'constructive', val: speaker.avg_constructive },
    ].sort((a, b) => b.val - a.val);

    let narrative = "";
    if (metrics[0].key === 'solution') {
      narrative = "具体的な対案や是正策に関する質疑が多く確認されています";
    } else if (metrics[0].key === 'local_focus') {
      narrative = "地域住民・当事者に関する質疑も確認されています";
    } else if (metrics[0].key === 'evidence') {
      narrative = "統計・数値・資料などの根拠を用いた質疑が多く確認されています";
    } else {
      narrative = "行政答弁や制度運用に関する確認・追及を含む質疑が多く確認されています";
    }

    return `主に【${categoriesStr}】の分野で登壇。全${speaker.count}件の実質政策質疑ログからは、${narrative}。`;
  };

  const sameDistrictSpeakers = useMemo(() => {
    if (!selectedSpeaker) return [];
    return speakerStats.filter(s => s.district === selectedSpeaker.district && s.speaker !== selectedSpeaker.speaker);
  }, [selectedSpeaker, speakerStats]);

  const samePartySpeakers = useMemo(() => {
    if (!selectedSpeaker) return [];
    return speakerStats.filter(s => s.partyGroup === selectedSpeaker.partyGroup && s.speaker !== selectedSpeaker.speaker);
  }, [selectedSpeaker, speakerStats]);

  const selectedSpeakerBills = useMemo(() => {
    if (!selectedSpeaker || !votesData.length) return [];
    const isIndependent = !selectedSpeaker.partyGroup || selectedSpeaker.partyGroup === '無所属';
    const party = selectedSpeaker.partyGroup || '';
    
    const baseName = selectedSpeaker.speaker;
    const aliasName = ALIAS_MAP[baseName];

    return votesData.map(bill => {
      const votes = bill.votes || {};
      let myVote = null;

      if (!isIndependent) {
        for (const [groupName, voteVal] of Object.entries(votes)) {
          if (groupName.includes(party) || party.includes(groupName)) {
            myVote = voteVal;
            break;
          }
        }
      }
      
      if (!myVote) {
        for (const [key, voteVal] of Object.entries(votes)) {
          if (key.includes(baseName) || (aliasName && key.includes(aliasName))) {
            myVote = voteVal;
            break;
          }
        }
      }

      const vValues = Object.values(votes);
      const isContested = vValues.includes('賛成') && vValues.includes('反対');

      return { ...bill, myVote, isContested };
    }).filter(b => b.myVote);
  }, [selectedSpeaker, votesData]);

  const filteredSpeakerBills = useMemo(() => {
    return selectedSpeakerBills.filter(bill => {
      if (speakerVoteFilter === 'contested' && !bill.isContested) return false;
      if (speakerVoteFilter === 'agree' && bill.myVote !== '賛成') return false;
      if (speakerVoteFilter === 'disagree' && bill.myVote !== '反対') return false;
      return true;
    });
  }, [selectedSpeakerBills, speakerVoteFilter]);

  return (
    <main className="max-w-5xl mx-auto py-8 px-6 animate-in fade-in slide-in-from-bottom-4 duration-300 w-full">
      <div className="flex items-center justify-between mb-6">
        <button onClick={onBack} className="inline-flex items-center text-xs font-bold text-slate-500 hover:text-indigo-600 transition-colors bg-white px-3 py-2 rounded-lg border border-slate-200 shadow-sm cursor-pointer">
          <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />一覧に戻る
        </button>
        <button
          onClick={() => onOpenCompare(selectedSpeaker)}
          className="px-3.5 py-2 rounded-lg text-xs font-black transition-all flex items-center gap-1.5 border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 shadow-sm cursor-pointer"
        >
          <GitCompare className="w-3.5 h-3.5" />この議員を比較する
        </button>
      </div>

      <header className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 mb-6 space-y-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-6 border-b border-slate-100">
          <div className="flex items-start gap-4">
            <div className="w-16 h-20 rounded-xl overflow-hidden bg-slate-100 border border-slate-200 shrink-0 flex items-center justify-center shadow-xs">
              <img
                src={detailPhotoSrc}
                alt={selectedSpeaker.speaker}
                className="w-full h-full object-cover"
                onError={handleDetailPhotoError}
              />
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap mb-1">
                <h2 className="text-2xl font-black text-slate-900 tracking-tight">{selectedSpeaker.speaker}</h2>
                {/* 💡 要件1：「現場代弁型」➔「主な質疑傾向：現場・生活課題」 */}
                <span className={`px-2.5 py-0.5 text-xs font-extrabold rounded border ${selectedSpeaker.style?.badgeClass || 'bg-slate-100'}`}>
                  {cleanStyleLabel(selectedSpeaker.style?.label)}
                </span>
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

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-gradient-to-br from-indigo-50/50 to-slate-50 p-4 rounded-xl border border-indigo-100/70">
              <div className="flex items-center gap-1.5 text-xs font-extrabold text-indigo-900 mb-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                質疑データ分析：政策分野と特徴
              </div>
              <p className="text-xs text-slate-700 leading-relaxed font-medium">{generateCouncilorProfileSummary(selectedSpeaker)}</p>
              {/* 💡 要件2：「切実な声を届ける」等の情緒表現をサニタイズ */}
              <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-indigo-100/60 leading-normal">
                {cleanStyleDesc(selectedSpeaker.style?.desc)}
              </p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-2.5 shadow-2xs">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                <span className="flex items-center gap-1.5 text-indigo-900 font-extrabold">
                  <Layers className="w-3.5 h-3.5 text-indigo-600" />
                  質疑の多い政策分野TOP3
                </span>
                <span className="text-[10px] text-slate-400 font-medium">全 {selectedSpeaker.count} 質疑</span>
              </div>

              <div className="space-y-2 pt-1">
                {topicBreakdown.map((t, idx) => {
                  const barColors = ['bg-indigo-600', 'bg-sky-500', 'bg-amber-500'];
                  return (
                    <div key={t.category} className="space-y-1">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-bold text-slate-700 truncate max-w-[200px]">{t.category}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-slate-400 text-[11px] font-medium">{t.count}件</span>
                          <span className="font-black text-slate-900 w-8 text-right font-mono">{t.percentage}%</span>
                        </div>
                      </div>
                      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${barColors[idx] || 'bg-slate-400'}`}
                          style={{ width: `${t.percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* 💡 要件5：「4軸による質疑分析」の重複を解消し、タイトル1回のみ表示 */}
          <div className="lg:col-span-5 bg-slate-50/80 p-4 rounded-xl border border-slate-100 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-extrabold text-slate-800 flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5 text-indigo-600" />
                  4軸による質疑分析
                </span>
              </div>
              <div className="w-full h-44">
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

            <div className="pt-2 border-t border-slate-200/60 mt-1 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1 text-[10px] text-slate-400 leading-normal">
              <span>※質疑データを4つの分析軸から整理した分析値です。議員の優劣や公式評価を示すものではありません。</span>
              {onOpenMethodology && (
                <button
                  onClick={onOpenMethodology}
                  className="text-indigo-600 hover:text-indigo-800 font-bold hover:underline cursor-pointer inline-flex items-center gap-0.5 shrink-0"
                >
                  <BookOpen className="w-2.5 h-2.5" />
                  <span>分析方法を見る</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* 関連する議員を探す */}
      <details className="bg-white rounded-2xl shadow-sm border border-slate-200 mb-8 group overflow-hidden">
        <summary className="p-5 flex items-center justify-between cursor-pointer list-none [&::-webkit-details-marker]:hidden hover:bg-slate-50 transition-colors">
          <div className="flex items-center gap-2 font-extrabold text-slate-800 text-sm">
            <Users className="w-5 h-5 text-indigo-500" />
            <span>関連する議員を探す（同じ選挙区・会派）</span>
          </div>
          <ChevronDown className="w-5 h-5 text-slate-400 group-open:rotate-180 transition-transform" />
        </summary>
        <div className="p-5 border-t border-slate-100 bg-slate-50/30">
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-bold w-fit mb-4">
            <button onClick={() => setRelatedTab('district')} className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${relatedTab === 'district' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-slate-500 hover:text-slate-700'}`}>同じ選挙区（{selectedSpeaker.district}・{sameDistrictSpeakers.length}名）</button>
            <button onClick={() => setRelatedTab('party')} className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${relatedTab === 'party' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-slate-500 hover:text-slate-700'}`}>同じ会派（{samePartySpeakers.length}名）</button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
            {(relatedTab === 'district' ? sameDistrictSpeakers : samePartySpeakers).map((rel) => (
              <button
                key={rel.speaker}
                onClick={() => onSpeakerClick(rel.speaker)}
                className="p-3 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all text-left flex flex-col justify-between group shadow-2xs bg-white cursor-pointer"
              >
                <div>
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="text-xs font-black text-slate-800 group-hover:text-indigo-600 transition-colors">{rel.speaker}</span>
                    <ArrowRight className="w-3 h-3 text-slate-300 group-hover:text-indigo-500 group-hover:translate-x-0.5 transition-all shrink-0" />
                  </div>
                  <span className={`px-1.5 py-0.2 text-[9px] font-bold rounded border inline-block ${rel.style?.badgeClass || 'bg-slate-100'}`}>
                    {cleanStyleLabel(rel.style?.label)}
                  </span>
                </div>
              </button>
            ))}
            {(relatedTab === 'district' ? sameDistrictSpeakers : samePartySpeakers).length === 0 && <div className="col-span-full py-6 text-center text-xs text-slate-400 bg-white rounded-xl">他に該当する議員が登録されていません。</div>}
          </div>
        </div>
      </details>

      {/* 3つのタブナビゲーション */}
      <div className="flex items-center justify-between mb-4 border-b border-slate-200 pb-2">
        <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200 flex-wrap gap-1">
          <button
            onClick={() => setSpeakerDetailTab('threads')}
            className={`flex items-center px-4 py-2 rounded-lg text-xs md:text-sm font-bold transition-all cursor-pointer ${
              speakerDetailTab === 'threads' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <MessageCircle className="w-4 h-4 mr-1.5" />
            質疑ログ ({actualThreads.length}件)
          </button>
          <button
            onClick={() => setSpeakerDetailTab('votes')}
            className={`flex items-center px-4 py-2 rounded-lg text-xs md:text-sm font-bold transition-all cursor-pointer ${
              speakerDetailTab === 'votes' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Scale className="w-4 h-4 mr-1.5" />
            議決・賛否の記録 ({selectedSpeakerBills.length}件)
          </button>
          <button
            onClick={() => setSpeakerDetailTab('pledges')}
            className={`flex items-center px-4 py-2 rounded-lg text-xs md:text-sm font-bold transition-all cursor-pointer ${
              speakerDetailTab === 'pledges' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <BookmarkCheck className="w-4 h-4 mr-1.5 text-indigo-600" />
            公約と議会活動の照合 ({currentSpeakerTracker?.tracked_items?.length || 0}件)
          </button>
        </div>
      </div>

      {/* ① 質疑ログタブ */}
      {speakerDetailTab === 'threads' && (
        <div className="space-y-6 animate-in fade-in">
          {featuredThread && !speakerCategory && speakerSort === 'recent' && (
            <div className="relative rounded-2xl bg-gradient-to-r from-indigo-500/10 via-slate-500/5 to-transparent p-0.5 border border-indigo-200/80 shadow-xs">
              <div className="bg-white rounded-[14px] p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-900 text-[11px] font-black">
                    <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                    代表的な質疑
                  </div>
                  <span className="text-[11px] font-bold text-slate-400">
                    4軸分析における特徴的な質疑
                  </span>
                </div>

                <ThreadCard
                  stmt={featuredThread}
                  onViewContext={onViewContext}
                  showSpeakerHeader={false}
                  onOpenMethodology={onOpenMethodology}
                />
              </div>
            </div>
          )}

          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-slate-50/80 p-3 rounded-xl border border-slate-200">
            <div className="text-xs font-bold text-slate-500">{selectedSpeaker.speaker} 議員の質疑一覧 ({actualThreads.length}件)</div>
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
                  <option value="recent">新着順</option>
                  <option value="solution">対案・是正順</option>
                  <option value="local_focus">地域解像度順</option>
                  <option value="constructive">議論の進展順</option>
                  <option value="evidence">根拠・データ順</option>
                </select>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {actualThreads.length > 0 ? actualThreads.map((stmt) => (
              <ThreadCard
                key={stmt.id}
                stmt={stmt}
                onViewContext={onViewContext}
                showSpeakerHeader={false}
                onOpenMethodology={onOpenMethodology}
              />
            )) : (
              <div className="text-center py-12 bg-white rounded-xl border border-slate-200">
                <p className="text-slate-500 text-sm font-medium">条件に一致する質疑スレッドがありません。</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ② 議決・賛否の記録タブ */}
      {speakerDetailTab === 'votes' && (
        <div className="space-y-6 animate-in fade-in">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold text-slate-500">絞り込み:</span>
              {[
                { key: 'contested', label: '賛否が分かれた議案のみ' },
                { key: 'all', label: '全議案' },
                { key: 'agree', label: '賛成した議案' },
                { key: 'disagree', label: '反対した議案' }
              ].map(btn => (
                <button
                  key={btn.key}
                  onClick={() => setSpeakerVoteFilter(btn.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all cursor-pointer ${
                    speakerVoteFilter === btn.key
                      ? 'bg-indigo-50 text-indigo-700 border-indigo-300 shadow-2xs'
                      : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {btn.label}
                </button>
              ))}
            </div>
            <div className="text-[11px] text-slate-400">
              該当: {filteredSpeakerBills.length} 件
            </div>
          </div>

          <div className="space-y-4">
            {filteredSpeakerBills.map((bill, idx) => {
              const issue = issuesMap[`${bill.session_name}_${bill.bill_number}`];
              const isAgree = bill.myVote === '賛成';

              return (
                <article key={idx} className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pb-3 border-b border-slate-100">
                    <div className="space-y-1.5 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] font-black text-slate-500 bg-slate-100 px-2 py-0.5 rounded font-mono">
                          {bill.session_name} ({bill.bill_number})
                        </span>
                        {bill.isContested ? (
                          <span className="text-[10px] font-black px-2 py-0.5 rounded bg-rose-50 text-rose-600 border border-rose-200 flex items-center gap-1">
                            <Scale className="w-2.5 h-2.5 text-rose-500" />賛否が分かれた議案
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-50 text-slate-400 border border-slate-200">
                            全会一致
                          </span>
                        )}
                        {bill.result && (
                          <span className="text-[10px] font-bold text-slate-500 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded">
                            結果: {bill.result}
                          </span>
                        )}
                      </div>
                      <h2 className="text-base font-black text-slate-900 leading-snug">
                        {bill.title}
                      </h2>
                    </div>

                    <div className="shrink-0 self-start sm:self-auto flex items-center gap-2">
                      <div className="flex items-center gap-1.5 bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-200">
                        <span className="text-xs font-bold text-slate-500">投票態度:</span>
                        <span className={`text-xs font-black inline-flex items-center gap-1 ${
                          isAgree ? 'text-emerald-600' : 'text-rose-600'
                        }`}>
                          {isAgree ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                          {bill.myVote}
                        </span>
                      </div>

                      <button
                        onClick={() => onSelectBill(bill)}
                        className="px-3 py-1.5 text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 rounded-xl border border-indigo-200 transition-all flex items-center gap-1 cursor-pointer"
                      >
                        <span>全議員の賛否・詳細</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>

                  {issue && (
                    <div className="bg-indigo-50/40 p-4 rounded-xl border border-indigo-100 space-y-3">
                      <div>
                        <div className="flex items-center gap-1.5 text-xs font-black text-indigo-900 mb-1">
                          <Scale className="w-3.5 h-3.5 text-indigo-600" />
                          対立の論点: {issue.key_conflict}
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed">
                          {issue.background}
                        </p>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
                        <div className={`p-3 rounded-lg border leading-relaxed text-xs ${
                          isAgree
                            ? 'bg-emerald-50/90 border-emerald-300 ring-2 ring-emerald-500/20'
                            : 'bg-emerald-50/50 border-emerald-100 opacity-80'
                        }`}>
                          <span className="text-[11px] font-black text-emerald-800 flex items-center justify-between mb-1">
                            <span>賛成側の主な論理</span>
                            {isAgree && <span className="text-[9px] bg-emerald-600 text-white px-1.5 py-0.2 rounded font-bold">当該議員の立場</span>}
                          </span>
                          <p className="text-slate-700">{issue.agree_logic}</p>
                        </div>

                        <div className={`p-3 rounded-lg border leading-relaxed text-xs ${
                          !isAgree
                            ? 'bg-rose-50/90 border-rose-300 ring-2 ring-rose-500/20'
                            : 'bg-rose-50/50 border-rose-100 opacity-80'
                        }`}>
                          <span className="text-[11px] font-black text-rose-800 flex items-center justify-between mb-1">
                            <span>反対側の主な論理</span>
                            {!isAgree && <span className="text-[9px] bg-rose-600 text-white px-1.5 py-0.2 rounded font-bold">当該議員の立場</span>}
                          </span>
                          <p className="text-slate-700">{issue.disagree_logic}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </article>
              );
            })}

            {filteredSpeakerBills.length === 0 && (
              <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-slate-200">
                <p className="text-slate-400 font-bold text-xs">該当する投票記録がありません。</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ③ 公約と議会活動の照合タブ */}
      {speakerDetailTab === 'pledges' && (
        <div className="space-y-6 animate-in fade-in">
          <div className="bg-slate-100/90 rounded-2xl p-5 border border-slate-200 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs leading-relaxed">
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 font-black text-slate-800 text-xs">
                <ShieldCheck className="w-4 h-4 text-indigo-600 shrink-0" />
                <span>選挙公報原本に基づく看板政策のファクト対比</span>
              </div>
              <p className="text-slate-600 text-[11px]">
                選挙公報原本に掲載された本人の看板公約（原文引用）と、任期中の実際の議決（賛成/反対）および議場での関連質疑を客観的に並列提示しています。
              </p>
            </div>
            {currentSpeakerTracker?.bulletin_url && (
              <a
                href={currentSpeakerTracker.bulletin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-indigo-600 hover:text-indigo-800 font-bold text-xs shrink-0 transition-colors shadow-2xs cursor-pointer"
              >
                <Landmark className="w-3.5 h-3.5 text-indigo-500" />
                <span>選管公式公報PDF原本</span>
                <ExternalLink className="w-3 h-3 ml-0.5 opacity-60" />
              </a>
            )}
          </div>

          {currentSpeakerTracker && currentSpeakerTracker.tracked_items && currentSpeakerTracker.tracked_items.length > 0 ? (
            <div className="space-y-6">
              {currentSpeakerTracker.tracked_items.map((item, idx) => (
                <div key={idx} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden space-y-0">
                  <div className="bg-slate-50/80 px-6 py-3.5 border-b border-slate-100 flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-black bg-indigo-50 text-indigo-700 border border-indigo-200">
                        {item.category || '市政政策'}
                      </span>
                      <h3 className="text-base font-black text-slate-900 leading-snug">
                        {item.headline}
                      </h3>
                    </div>
                    {item.stance && (
                      <span className="text-[11px] font-bold text-slate-500">
                        スタンス: <strong className="text-slate-800">{item.stance}</strong>
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">
                    <div className="p-6 space-y-4 bg-indigo-50/15 flex flex-col justify-between">
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-black text-indigo-900 flex items-center gap-1.5 uppercase tracking-wider">
                            <BookmarkCheck className="w-4 h-4 text-indigo-600" />
                            2023年 選挙公報での訴え
                          </span>
                          <span className="text-[10px] font-bold text-slate-400">
                            公式選挙公報 原本
                          </span>
                        </div>

                        <div className="bg-white p-4 rounded-xl border border-indigo-100 shadow-2xs space-y-2">
                          <span className="text-[10px] font-black text-slate-400 block">公報紙面からの原文引用:</span>
                          <blockquote className="text-xs text-slate-800 font-bold leading-relaxed border-l-2 border-indigo-500 pl-3 italic">
                            “{item.election_promise?.quote || item.headline}”
                          </blockquote>
                        </div>
                      </div>

                      {item.election_promise?.bulletin_url && (
                        <div className="pt-2">
                          <a
                            href={item.election_promise.bulletin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[11px] font-bold text-indigo-600 hover:text-indigo-800 hover:underline"
                          >
                            <span>京都市選管 公式公報原本（PDF）で紙面を確認</span>
                            <ExternalLink className="w-3 h-3 opacity-60" />
                          </a>
                        </div>
                      )}
                    </div>

                    <div className="p-6 space-y-4 bg-white flex flex-col justify-between">
                      <div className="space-y-3.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-black text-indigo-950 flex items-center gap-1.5 uppercase tracking-wider">
                            <MessageCircle className="w-4 h-4 text-indigo-600" />
                            議場・委員会での発言・追及ログ
                          </span>
                          <span className="text-[10px] font-bold text-slate-400">
                            公式議事録ログ
                          </span>
                        </div>

                        {(item.council_statements && item.council_statements.length > 0) || item.council_statement ? (
                          <div className="space-y-3">
                            {(item.council_statements || [item.council_statement]).map((stmt, sIdx) => (
                              <div key={sIdx} className="p-4 rounded-xl bg-indigo-50/40 border border-indigo-100 space-y-2.5">
                                <div className="flex items-center justify-between text-[10px] font-bold text-slate-500">
                                  <span className="font-mono bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">
                                    {stmt.date} / {stmt.committee}
                                  </span>
                                  <span className="text-indigo-600 font-black px-1.5 py-0.2 bg-indigo-50 rounded border border-indigo-200">
                                    関連質疑
                                  </span>
                                </div>

                                <p className="text-xs text-slate-800 leading-relaxed font-medium">
                                  {stmt.summary}
                                </p>

                                <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 border-t border-indigo-100/70 mt-2">
                                  <button
                                    onClick={() => handleViewStatementContext(stmt)}
                                    className="flex-1 py-1.5 px-3 flex items-center justify-center text-xs font-bold text-indigo-700 bg-white hover:bg-indigo-50 border border-indigo-200 rounded-lg transition-colors shadow-2xs cursor-pointer group"
                                  >
                                    <MessageCircle className="w-3.5 h-3.5 mr-1.5 text-indigo-600 group-hover:scale-110 transition-transform" />
                                    <span>市側答弁を含むタイムライン・詳細を表示</span>
                                  </button>

                                  {stmt.official_url ? (
                                    <a
                                      href={stmt.official_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="px-3 py-1.5 flex items-center justify-center text-[11px] font-bold text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors cursor-pointer shrink-0"
                                    >
                                      <Landmark className="w-3.5 h-3.5 mr-1 text-slate-500" />
                                      <span>会議録原本</span>
                                      <ExternalLink className="w-2.5 h-2.5 ml-1 opacity-60" />
                                    </a>
                                  ) : (
                                    <button
                                      onClick={() => {
                                        const full = selectedSpeaker?.statements?.find(s => s.id === (stmt.speech_id || stmt.id));
                                        if (full) openOfficialMinute(full);
                                      }}
                                      className="px-3 py-1.5 flex items-center justify-center text-[11px] font-bold text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors cursor-pointer shrink-0"
                                    >
                                      <Landmark className="w-3.5 h-3.5 mr-1 text-slate-500" />
                                      <span>会議録原本</span>
                                      <ExternalLink className="w-2.5 h-2.5 ml-1 opacity-60" />
                                    </button>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 text-xs text-slate-400 leading-relaxed">
                            任期中にこの公約テーマに直接言及した代表的な質疑スレッドは確認されていません。
                          </div>
                        )}
                      </div>

                      <div className="pt-3 border-t border-slate-100">
                        {item.council_vote ? (
                          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/80 space-y-1.5">
                            <div className="flex items-center justify-between flex-wrap gap-1">
                              <span className="text-[10px] font-black text-slate-500 font-mono">
                                関連議案: {item.council_vote.session_name} ({item.council_vote.bill_number})
                              </span>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-black inline-flex items-center gap-1 ${
                                item.council_vote.my_vote === '賛成'
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : 'bg-rose-50 text-rose-700 border border-rose-200'
                              }`}>
                                {item.council_vote.my_vote === '賛成' ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                                投票態度: {item.council_vote.my_vote}
                              </span>
                            </div>
                            <div className="text-xs font-bold text-slate-800 truncate" title={item.council_vote.bill_title}>
                              {item.council_vote.bill_title}
                            </div>
                            {item.council_vote.context_note && (
                              <p className="text-[10px] text-slate-500 leading-normal mt-1">
                                💡 {item.council_vote.context_note}
                              </p>
                            )}
                          </div>
                        ) : (
                          <div className="text-[10px] text-slate-400 mt-2">
                            ※単独の採決議案（条例案等）はありません（一般会計包括予算等に組み込まれて審議・執行される政策です）。
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-slate-200 space-y-2">
              <AlertCircle className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-slate-600 font-bold text-sm">現在、この議員の選挙公報看板公約データを照合中です。</p>
            </div>
          )}
        </div>
      )}
    </main>
  );
}