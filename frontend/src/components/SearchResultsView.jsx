import React, { useState, useMemo } from 'react';
import { 
  ArrowLeft, Sparkles, MessageCircle, User, Scale, Search, Flame, 
  Target, GitCompare, ArrowRight // 💡 Target を追加
} from 'lucide-react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import ThreadCard from './ThreadCard';
import BillsSection from './BillsSection';
import { cleanName } from '../utils/styleHelpers';

export default function SearchResultsView({
  submittedQuery,
  onClearSearch,
  filteredThreads = [],
  filteredBills = [],
  filteredSpeakers = [],
  speakerStats = [],
  issuesMap = {},
  onlyContestedBills,
  setOnlyContestedBills,
  onSpeakerClick,
  onViewContext,
  onOpenCompare,
  onSelectBill,
  onOpenMethodology
}) {
  const [activeTab, setActiveTab] = useState('threads'); // 'threads' | 'bills' | 'speakers'

  // 💡 検索ヒットした「激論議案」のAI解説データを抽出
  const aiIssueDigest = useMemo(() => {
    for (const bill of filteredBills) {
      const issue = issuesMap[`${bill.session_name}_${bill.bill_number}`];
      if (issue && issue.key_conflict) return issue;
    }
    return null;
  }, [filteredBills, issuesMap]);

  // 💡 検索ヒットした「質疑」の中で、総合評価スコアが最も高いものをピックアップ
  const topThreadDigest = useMemo(() => {
    if (filteredThreads.length === 0) return null;
    return [...filteredThreads].sort((a, b) => {
      const scoreA = (a.solution_score || 0) + (a.evidence_score || 0) + (a.local_focus_score || 0) + (a.constructive_score || 0);
      const scoreB = (b.solution_score || 0) + (b.evidence_score || 0) + (b.local_focus_score || 0) + (b.constructive_score || 0);
      return scoreB - scoreA;
    })[0];
  }, [filteredThreads]);

  const formatSummaryRadar = (speaker) => [
    { subject: '根拠・データ', A: speaker.avg_evidence || 0, fullMark: 5 },
    { subject: '対案・是正', A: speaker.avg_solution || 0, fullMark: 5 },
    { subject: '地域解像度', A: speaker.avg_local_focus || 0, fullMark: 5 },
    { subject: '議論の進展', A: speaker.avg_constructive || 0, fullMark: 5 },
  ];

  return (
    <main className="max-w-6xl mx-auto py-8 px-6 animate-in fade-in slide-in-from-bottom-4 duration-300 w-full">
      <div className="mb-6 flex items-center justify-between">
        <button 
          onClick={onClearSearch}
          className="inline-flex items-center text-xs font-bold text-slate-500 hover:text-indigo-600 bg-white hover:bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl shadow-sm transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />検索をクリアしてトップへ
        </button>
      </div>

      <header className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <Search className="w-5 h-5 text-indigo-500" />
          <h2 className="text-2xl font-black text-slate-900">
            「{submittedQuery}」<span className="text-slate-500 text-lg">の検索結果</span>
          </h2>
        </div>
        <p className="text-sm font-bold text-slate-500 ml-7">
          関連質疑 {filteredThreads.length}件 / 関連議案 {filteredBills.length}件 / 言及した議員 {filteredSpeakers.length}名
        </p>
      </header>

      {/* 💡 AIダイジェスト領域 */}
      {(aiIssueDigest || topThreadDigest) && (
        <section className="bg-gradient-to-br from-indigo-50/80 to-slate-50 border border-indigo-100 p-6 rounded-2xl mb-8 shadow-sm">
          <div className="flex items-center gap-1.5 text-xs font-black text-indigo-700 bg-white border border-indigo-100 px-2.5 py-1 rounded-lg shadow-2xs w-fit mb-4">
            <Sparkles className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
            AI自動分析：このテーマを巡る議会の対立構造と論点
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {aiIssueDigest && (
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
                <div className="flex items-center gap-1.5 text-[11px] font-black text-rose-600 bg-rose-50 px-2 py-0.5 rounded border border-rose-100 w-fit">
                  <Flame className="w-3 h-3 fill-rose-500" />
                  最も激論になった関連議案の争点
                </div>
                <div>
                  <h4 className="text-sm font-black text-slate-800 mb-1.5 leading-snug">
                    {aiIssueDigest.key_conflict}
                  </h4>
                  <p className="text-xs text-slate-600 leading-relaxed font-medium">
                    {aiIssueDigest.background}
                  </p>
                </div>
              </div>
            )}

            {topThreadDigest && (
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
                <div className="flex items-center gap-1.5 text-[11px] font-black text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100 w-fit">
                  <Target className="w-3 h-3" />
                  AI最高評価の代表質疑サマリー
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-black text-slate-800">{topThreadDigest.speaker} 議員</span>
                    <span className="text-[10px] text-slate-400 font-bold">{topThreadDigest.meeting_date}</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed font-medium">
                    {topThreadDigest.summary}
                  </p>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* タブ切り替え */}
      <div className="flex items-center overflow-x-auto border-b border-slate-200 mb-6 pb-px hide-scrollbar">
        <button
          onClick={() => setActiveTab('threads')}
          className={`flex items-center px-5 py-3 text-sm font-black whitespace-nowrap transition-colors border-b-2 cursor-pointer ${
            activeTab === 'threads' ? 'border-indigo-600 text-indigo-700 bg-indigo-50/50' : 'border-transparent text-slate-500 hover:bg-slate-50'
          }`}
        >
          <MessageCircle className="w-4 h-4 mr-2" />
          質疑スレッド ({filteredThreads.length})
        </button>
        <button
          onClick={() => setActiveTab('bills')}
          className={`flex items-center px-5 py-3 text-sm font-black whitespace-nowrap transition-colors border-b-2 cursor-pointer ${
            activeTab === 'bills' ? 'border-indigo-600 text-indigo-700 bg-indigo-50/50' : 'border-transparent text-slate-500 hover:bg-slate-50'
          }`}
        >
          <Scale className="w-4 h-4 mr-2" />
          議案・賛否の記録 ({filteredBills.length})
        </button>
        <button
          onClick={() => setActiveTab('speakers')}
          className={`flex items-center px-5 py-3 text-sm font-black whitespace-nowrap transition-colors border-b-2 cursor-pointer ${
            activeTab === 'speakers' ? 'border-indigo-600 text-indigo-700 bg-indigo-50/50' : 'border-transparent text-slate-500 hover:bg-slate-50'
          }`}
        >
          <User className="w-4 h-4 mr-2" />
          関連する議員 ({filteredSpeakers.length})
        </button>
      </div>

      {/* コンテンツ表示エリア */}
      <div className="animate-in fade-in duration-300 min-h-[400px]">
        {activeTab === 'threads' && (
          <div className="space-y-6">
            {filteredThreads.length > 0 ? (
              filteredThreads.map((stmt) => (
                <ThreadCard 
                  key={stmt.id} 
                  stmt={stmt} 
                  speakerInfo={speakerStats.find(s => s.speaker === cleanName(stmt.speaker))} 
                  onSpeakerClick={onSpeakerClick} 
                  onViewContext={onViewContext} 
                  showSpeakerHeader={true} 
                  onOpenMethodology={onOpenMethodology}
                />
              ))
            ) : (
              <div className="text-center py-20 text-slate-500 bg-white rounded-2xl border border-slate-200">
                このキーワードに一致する質疑は見つかりませんでした。
              </div>
            )}
          </div>
        )}

        {activeTab === 'bills' && (
          <BillsSection
            filteredBills={filteredBills}
            onlyContestedBills={onlyContestedBills}
            setOnlyContestedBills={setOnlyContestedBills}
            issuesMap={issuesMap}
            onSelectBill={onSelectBill}
          />
        )}

        {activeTab === 'speakers' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredSpeakers.length > 0 ? (
              filteredSpeakers.map((speaker) => (
                <article key={speaker.speaker} onClick={() => onSpeakerClick(speaker.speaker)} className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-lg hover:border-indigo-300 transition-all duration-300 cursor-pointer flex flex-col group relative">
                  <div className="p-5 border-b border-slate-100 flex justify-between items-start bg-slate-50/50">
                    <div>
                      <h2 className="text-lg font-black text-slate-900 tracking-tight group-hover:text-indigo-700 transition-colors">{speaker.speaker}</h2>
                      <div className="flex items-center gap-1.5 mt-0.5 text-[11px] font-bold text-slate-500">
                        <span className="bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded border border-slate-300">{speaker.district}</span>
                        <span className="truncate max-w-[150px]">{speaker.partyGroup}</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end">
                      <span className={`px-2 py-0.5 text-[10px] font-extrabold rounded border shadow-2xs ${speaker.style?.badgeClass || 'bg-slate-100 text-slate-600'}`}>
                        {speaker.style?.label || '標準'}
                      </span>
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
                      onClick={(e) => { e.stopPropagation(); onOpenCompare(speaker); }}
                      className="px-3 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-indigo-600 bg-white hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 transition-all flex items-center gap-1 cursor-pointer"
                    >
                      <GitCompare className="w-3.5 h-3.5 text-indigo-500" />比較する
                    </button>
                    <span className="text-xs font-bold text-indigo-600 group-hover:translate-x-0.5 transition-transform">詳細を見る →</span>
                  </div>
                </article>
              ))
            ) : (
              <div className="col-span-full text-center py-20 text-slate-500 bg-white rounded-2xl border border-slate-200">
                このキーワードに言及している議員は見つかりませんでした。
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}