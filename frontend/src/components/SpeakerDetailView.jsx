import React, { useState, useMemo } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import {
  ArrowLeft, GitCompare, User, Landmark, ExternalLink, Globe,
  Sparkles, TrendingUp, Users, ChevronDown, ArrowRight,
  MessageCircle, Scale, PieChart, BarChart3, Flame, CheckCircle2, XCircle,
  Trophy, Award, Layers
} from 'lucide-react';
import ThreadCard from './ThreadCard';

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

  const formatSummaryRadar = (speaker) => [
    { subject: '根拠・データ', A: speaker.avg_evidence || 0, fullMark: 5 },
    { subject: '対案・是正', A: speaker.avg_solution || 0, fullMark: 5 },
    { subject: '地域解像度', A: speaker.avg_local_focus || 0, fullMark: 5 },
    { subject: '議論の進展', A: speaker.avg_constructive || 0, fullMark: 5 },
  ];

  // 冒頭コンポーネント内に以下を追加
  const cleanName = selectedSpeaker?.speaker ? selectedSpeaker.speaker.replace(/\s+/g, '') : '';
  const [detailPhotoSrc, setDetailPhotoSrc] = useState(`/councilors/${cleanName}.jpg`);
  const [detailFallbackTried, setDetailFallbackTried] = useState(false);

  const handleDetailPhotoError = () => {
    const aliasMap = {
      '井崎敦子': '井﨑敦子',
      '井﨑敦子': '井崎敦子',
      '繁隆夫': '繁隆夫',
      '繁隆夫': '繁隆夫'
    };
    if (!detailFallbackTried && aliasMap[cleanName]) {
      setDetailFallbackTried(true);
      setDetailPhotoSrc(`/councilors/${aliasMap[cleanName]}.jpg`);
    }
  };
  // 政策トピック構成比（上位3〜4分野）の計算
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

  // この議員の「象徴的な代表質疑（総合最高評価）」を抽出
  const featuredThread = useMemo(() => {
    const stmts = selectedSpeaker?.statements || speakerFilteredThreads;
    if (!stmts || stmts.length === 0) return null;

    // 4軸スコア合計（特に具体的対案と客観データ）が最も高いスレッドを算出
    return [...stmts].sort((a, b) => {
      const scoreA = (a.solution_score || 0) + (a.evidence_score || 0) + (a.local_focus_score || 0) + (a.constructive_score || 0);
      const scoreB = (b.solution_score || 0) + (b.evidence_score || 0) + (b.local_focus_score || 0) + (b.constructive_score || 0);
      if (scoreB !== scoreA) return scoreB - scoreA;
      return new Date(b.meeting_date) - new Date(a.meeting_date);
    })[0];
  }, [selectedSpeaker, speakerFilteredThreads]);

  const generateCouncilorProfileSummary = (speaker) => {
    if (!speaker) return "";
    const categoriesStr = speaker.topCategories && speaker.topCategories.length > 0 ? speaker.topCategories.join("・") : "市政全般";
    const metrics = [
      { key: 'solution', label: '具体的対案や是正策の提示', val: speaker.avg_solution },
      { key: 'local_focus', label: '生活現場や地域課題への解像度', val: speaker.avg_local_focus },
      { key: 'evidence', label: '客観的な根拠・データ活用', val: speaker.avg_evidence },
      { key: 'constructive', label: '鋭い行政監視と議論の進展力', val: speaker.avg_constructive },
    ].sort((a, b) => b.val - a.val);

    let narrative = "";
    if (metrics[0].key === 'solution') narrative = `単なる課題指摘にとどまらず「${metrics[0].label}」に際立った強みがあり、実現可能性を見据えた制度改善・対案提起をリードする政策志向`;
    else if (metrics[0].key === 'local_focus') narrative = `市民生活の実態や地域現場に根ざした「${metrics[0].label}」が際立っており、当事者の切実な声を的確に議場へ届ける現場主義`;
    else if (metrics[0].key === 'evidence') narrative = `公的統計や実証事例など「${metrics[0].label}」を手堅く組み立て、客観的ファクトに基づき論理的整合性の高い質疑を展開するデータ重視`;
    else narrative = `行政答弁の不備や論理破綻を的確に突く「${metrics[0].label}」に長けており、市側から明確な見解や方針転換を果敢に引き出す監視志向`;

    return `主に【${categoriesStr}】の分野で精力的に登壇。全${speaker.count}件の実質政策質疑ログからは、${narrative}が顕著に読み取れます。`;
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
    const speakerName = selectedSpeaker.speaker;

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
          if (key.includes(speakerName)) {
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

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-7 space-y-4">
            {/* AI活動分析サマリー */}
            <div className="bg-gradient-to-br from-indigo-50/50 to-slate-50 p-4 rounded-xl border border-indigo-100/70">
              <div className="flex items-center gap-1.5 text-xs font-extrabold text-indigo-900 mb-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                AI活動分析：政策アプローチと特徴
              </div>
              <p className="text-xs text-slate-700 leading-relaxed font-medium">{generateCouncilorProfileSummary(selectedSpeaker)}</p>
              <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-indigo-100/60 leading-normal">{selectedSpeaker.style.desc}</p>
            </div>

            {/* 💡 政策トピック構成比（プログレスバー表示） */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-2.5 shadow-2xs">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                <span className="flex items-center gap-1.5 text-indigo-900 font-extrabold">
                  <Layers className="w-3.5 h-3.5 text-indigo-600" />
                  注力政策分野TOP3（質疑構成比）
                </span>
                <span className="text-[10px] text-slate-400 font-medium">全 {selectedSpeaker.count} 質疑</span>
              </div>

              <div className="space-y-2 pt-1">
                {topicBreakdown.map((t, idx) => {
                  const barColors = [
                    'bg-indigo-600',
                    'bg-sky-500',
                    'bg-amber-500'
                  ];
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

          {/* 4軸レーダーチャート */}
          <div className="lg:col-span-5 bg-slate-50/80 p-4 rounded-xl border border-slate-100 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-extrabold text-slate-700 flex items-center">
                <TrendingUp className="w-3.5 h-3.5 mr-1 text-indigo-600" />
                4軸ポリシーパラメータ
              </span>
              <span className="text-[10px] font-black text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-100">
                AI客観評価
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
        </div>
      </header>

      {/* 関連する議員を探すアコーディオン */}
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
                  <span className={`px-1.5 py-0.2 text-[9px] font-bold rounded border inline-block ${rel.style.badgeClass}`}>{rel.style.label}</span>
                </div>
              </button>
            ))}
            {(relatedTab === 'district' ? sameDistrictSpeakers : samePartySpeakers).length === 0 && <div className="col-span-full py-6 text-center text-xs text-slate-400 bg-white rounded-xl">他に該当する議員が登録されていません。</div>}
          </div>
        </div>
      </details>

      {/* タブ切り替えバー */}
      <div className="flex items-center justify-between mb-4 border-b border-slate-200 pb-2">
        <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200">
          <button
            onClick={() => setSpeakerDetailTab('threads')}
            className={`flex items-center px-4 py-2 rounded-lg text-xs md:text-sm font-bold transition-all cursor-pointer ${speakerDetailTab === 'threads' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
          >
            <MessageCircle className="w-4 h-4 mr-1.5" />
            質疑ログ ({speakerFilteredThreads.length}件)
          </button>
          <button
            onClick={() => setSpeakerDetailTab('votes')}
            className={`flex items-center px-4 py-2 rounded-lg text-xs md:text-sm font-bold transition-all cursor-pointer ${speakerDetailTab === 'votes' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
          >
            <Scale className="w-4 h-4 mr-1.5" />
            議決・賛否の記録 ({selectedSpeakerBills.length}件)
          </button>
        </div>
      </div>

      {/* 質疑ログタブ */}
      {speakerDetailTab === 'threads' && (
        <div className="space-y-6 animate-in fade-in">
          {/* 💡 象徴的な代表質疑（Featured Thread）のピックアップ枠 */}
          {featuredThread && !speakerCategory && speakerSort === 'recent' && (
            <div className="relative rounded-2xl bg-gradient-to-r from-amber-500/10 via-indigo-500/5 to-transparent p-0.5 border border-amber-200/80 shadow-xs">
              <div className="bg-white rounded-[14px] p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-[11px] font-black">
                    <Trophy className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
                    象徴的な代表質疑（総合最高評価）
                  </div>
                  <span className="text-[11px] font-bold text-slate-400">
                    具体的対案 × データ活用
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

          {/* フィルター・ソートバー */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-slate-50/80 p-3 rounded-xl border border-slate-200">
            <div className="text-xs font-bold text-slate-500">{selectedSpeaker.speaker} 議員の質疑一覧 ({speakerFilteredThreads.length}件)</div>
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
                  <option value="solution">具体的対案を重視</option>
                  <option value="local_focus">現場解像度を重視</option>
                  <option value="constructive">議論の進展を重視</option>
                  <option value="evidence">客観データを重視</option>
                </select>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {speakerFilteredThreads.length > 0 ? speakerFilteredThreads.map((stmt) => (
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

      {/* 議案・賛否タブ */}
      {speakerDetailTab === 'votes' && (
        <div className="space-y-6 animate-in fade-in">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold text-slate-500">絞り込み:</span>
              {[
                { key: 'contested', label: '激論議案のみ' },
                { key: 'all', label: '全議案' },
                { key: 'agree', label: '賛成した議案' },
                { key: 'disagree', label: '反対した議案' }
              ].map(btn => (
                <button
                  key={btn.key}
                  onClick={() => setSpeakerVoteFilter(btn.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all cursor-pointer ${speakerVoteFilter === btn.key
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
                            <Flame className="w-2.5 h-2.5 fill-rose-500 text-rose-500" />激論議案
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
                        <span className={`text-xs font-black inline-flex items-center gap-1 ${isAgree ? 'text-emerald-600' : 'text-rose-600'
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
                          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                          対立の核心: {issue.key_conflict}
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed">
                          {issue.background}
                        </p>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
                        <div className={`p-3 rounded-lg border leading-relaxed text-xs ${isAgree
                            ? 'bg-emerald-50/90 border-emerald-300 ring-2 ring-emerald-500/20'
                            : 'bg-emerald-50/50 border-emerald-100 opacity-80'
                          }`}>
                          <span className="text-[11px] font-black text-emerald-800 flex items-center justify-between mb-1">
                            <span>賛成派の論理</span>
                            {isAgree && <span className="text-[9px] bg-emerald-600 text-white px-1.5 py-0.2 rounded font-bold">当該議員の立場</span>}
                          </span>
                          <p className="text-slate-700">{issue.agree_logic}</p>
                        </div>

                        <div className={`p-3 rounded-lg border leading-relaxed text-xs ${!isAgree
                            ? 'bg-rose-50/90 border-rose-300 ring-2 ring-rose-500/20'
                            : 'bg-rose-50/50 border-rose-100 opacity-80'
                          }`}>
                          <span className="text-[11px] font-black text-rose-800 flex items-center justify-between mb-1">
                            <span>反対派の論理</span>
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
    </main>
  );
}