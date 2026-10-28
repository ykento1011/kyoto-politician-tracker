import React, { useState, useEffect, useMemo } from 'react';
import { 
  Users, MessageSquare, Scale, SlidersHorizontal, 
  ArrowUpDown, ChevronDown 
} from 'lucide-react';
import SpeakerCard from './SpeakerCard';
import ThreadCard from './ThreadCard';
import BillsSection from './BillsSection';

const INITIAL_SPEAKERS_LIMIT = 12;
const INITIAL_THREADS_LIMIT = 10;
const KYOTO_DISTRICTS = ['北区', '上京区', '左京区', '中京区', '東山区', '下京区', '南区', '右京区', '西京区', '伏見区', '山科区'];
const NAGOYA_DISTRICTS = [
  '千種区', '東区', '北区', '西区', '中村区', '中区', '昭和区', '瑞穂区',
  '熱田区', '中川区', '港区', '南区', '守山区', '緑区', '名東区', '天白区'
];

const YOKOHAMA_DISTRICTS = [
  '鶴見区', '神奈川区', '西区', '中区', '南区', '港南区', '保土ケ谷区', '旭区',
  '磯子区', '金沢区', '港北区', '緑区', '青葉区', '都筑区', '戸塚区', '栄区',
  '泉区', '瀬谷区'
];
const OSAKA_DISTRICTS = [
  '北区', '都島区', '福島区', '此花区', '中央区', '西区', '港区', '大正区', 
  '天王寺区', '浪速区', '西淀川区', '淀川区', '東淀川区', '東成区', '生野区', 
  '旭区', '城東区', '鶴見区', '阿倍野区', '住之江区', '住吉区', '東住吉区', '平野区', '西成区'
];

export default function MainTabView({
  cityCode = 'kyoto',
viewMode,
  setViewMode,
  filteredSpeakers = [],
  filteredThreads = [],
  filteredBills = [],
  topicStats = [],
  speakerStats = [],
  selectedDistrict,
  setSelectedDistrict,
  selectedCategory,
  setSelectedCategory,
  sortPerspective,
  setSortPerspective,
  selectedSession,
  setSelectedSession,
  selectedResult,
  setSelectedResult,
  uniqueSessions = [],
  uniqueResults = [],
  onlyContestedBills,
  setOnlyContestedBills,
  issuesMap = {},
  onSpeakerClick,
  onOpenCompare,
  onViewContext,
  onSelectBill,
  onOpenMethodology
}) {
  const activeDistricts = React.useMemo(() => {
    // 議員データから実在する行政区を動的に優先抽出
    if (speakerStats && speakerStats.length > 0) {
      const statsDistricts = Array.from(new Set(speakerStats.map(s => s.district).filter(Boolean)));
      if (statsDistricts.length > 0) return statsDistricts;
    }
    if (cityCode === 'yokohama') return YOKOHAMA_DISTRICTS;
    if (cityCode === 'nagoya') return NAGOYA_DISTRICTS;
    if (cityCode === 'osaka') return OSAKA_DISTRICTS;
    return KYOTO_DISTRICTS;
  }, [cityCode, speakerStats]);
  const [visibleSpeakersCount, setVisibleSpeakersCount] = useState(INITIAL_SPEAKERS_LIMIT);
  const [visibleThreadsCount, setVisibleThreadsCount] = useState(INITIAL_THREADS_LIMIT);

  useEffect(() => {
    setVisibleSpeakersCount(INITIAL_SPEAKERS_LIMIT);
    setVisibleThreadsCount(INITIAL_THREADS_LIMIT);
  }, [selectedCategory, selectedDistrict, sortPerspective, viewMode]);

  const displayedSpeakers = useMemo(() => {
    return filteredSpeakers.slice(0, visibleSpeakersCount);
  }, [filteredSpeakers, visibleSpeakersCount]);

  const displayedThreads = useMemo(() => {
    return filteredThreads.slice(0, visibleThreadsCount);
  }, [filteredThreads, visibleThreadsCount]);

  return (
    <section className="space-y-6">
      {/* 3大タブヘッダー */}
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
            議員一覧 ({filteredSpeakers.length.toLocaleString()})
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
            質疑スレッド ({filteredThreads.length.toLocaleString()})
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
            議案・賛否の記録 ({filteredBills.length.toLocaleString()})
          </button>
        </div>
      </div>

      {/* 議員・スレッド用フィルターバー */}
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
              {activeDistricts.map(d => (
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
                <option key={t.name} value={t.name}>{t.name} ({t.count.toLocaleString()}件)</option>
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

      {/* 議案専用フィルターバー */}
      {viewMode === 'bills' && (
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 flex-wrap">
            <SlidersHorizontal className="w-4 h-4 text-slate-400 mr-1" />
            
            <select
              value={selectedSession}
              onChange={(e) => setSelectedSession(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-bold text-slate-700 outline-none cursor-pointer max-w-[200px] truncate"
            >
              <option value="">すべての会期</option>
              {uniqueSessions.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>

            <select
              value={selectedResult}
              onChange={(e) => setSelectedResult(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-bold text-slate-700 outline-none cursor-pointer"
            >
              <option value="">すべての議決結果</option>
              {uniqueResults.map(r => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>

            {(selectedSession || selectedResult) && (
              <button
                onClick={() => { setSelectedSession(''); setSelectedResult(''); }}
                className="text-slate-400 hover:text-rose-600 font-bold ml-1 transition-colors cursor-pointer"
              >
                リセット
              </button>
            )}
          </div>
          <div className="text-[11px] font-bold text-slate-400">
            該当: <span className="text-indigo-600">{filteredBills.length.toLocaleString()}</span> 件
          </div>
        </div>
      )}

      {/* ① 議員一覧ビュー */}
      {viewMode === 'speakers' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {displayedSpeakers.map((speaker) => (
              <SpeakerCard cityCode={cityCode} 
                key={speaker.speaker}
                speaker={speaker}
                onSpeakerClick={onSpeakerClick}
                onOpenCompare={onOpenCompare}
              />
            ))}
          </div>

          {visibleSpeakersCount < filteredSpeakers.length && (
            <div className="text-center pt-2">
              <button
                onClick={() => setVisibleSpeakersCount(prev => prev + 12)}
                className="inline-flex items-center gap-1.5 px-6 py-3 rounded-xl bg-white hover:bg-slate-50 border border-slate-300 text-xs font-bold text-slate-700 shadow-2xs hover:shadow-xs transition-all cursor-pointer"
              >
                <span>さらに議員を表示する（残り {(filteredSpeakers.length - visibleSpeakersCount).toLocaleString()} 名）</span>
                <ChevronDown className="w-4 h-4 text-slate-400" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* ② 質疑スレッド一覧ビュー */}
      {viewMode === 'threads' && (
        <div className="space-y-6">
          <div className="space-y-6">
            {displayedThreads.map((stmt) => (
              <ThreadCard cityCode={cityCode} 
                key={stmt.id}
                stmt={stmt}
                speakerInfo={speakerStats.find(s => s.speaker === stmt.speaker)}
                onSpeakerClick={onSpeakerClick}
                onViewContext={onViewContext}
                showSpeakerHeader={true}
                onOpenMethodology={onOpenMethodology}
              />
            ))}
          </div>

          {visibleThreadsCount < filteredThreads.length && (
            <div className="text-center pt-2">
              <button
                onClick={() => setVisibleThreadsCount(prev => prev + 10)}
                className="inline-flex items-center gap-1.5 px-6 py-3 rounded-xl bg-white hover:bg-slate-50 border border-slate-300 text-xs font-bold text-slate-700 shadow-2xs hover:shadow-xs transition-all cursor-pointer"
              >
                <span>さらに質疑スレッドを表示する（残り {(filteredThreads.length - visibleThreadsCount).toLocaleString()} 件）</span>
                <ChevronDown className="w-4 h-4 text-slate-400" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* ③ 議案一覧ビュー */}
      {viewMode === 'bills' && (
        <BillsSection
          filteredBills={filteredBills}
          onlyContestedBills={onlyContestedBills}
          setOnlyContestedBills={setOnlyContestedBills}
          issuesMap={issuesMap}
          onSelectBill={onSelectBill}
        />
      )}
    </section>
  );
}