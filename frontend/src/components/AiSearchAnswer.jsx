import React, { useState, useEffect } from 'react';
import { 
  Sparkles, Landmark, ExternalLink, Milestone, 
  MapPin, ArrowRight, UserCheck, CheckCircle2 
} from 'lucide-react';
import { openOfficialMinute, getOfficialLinkTooltip } from '../utils/officialLink';
import { getCityDataUrl } from '../config/cities';

export default function AiSearchAnswer({ query, filteredThreads, cityCode = 'kyoto', onOpenTopicDetail, onSelectSpeaker }) {
  const [topicMatch, setTopicMatch] = useState(null);
  const [matchingPledges, setMatchingPledges] = useState([]);
  const [dynamicSummary, setDynamicSummary] = useState(null);

  useEffect(() => {
    const cleanQuery = (query || '').trim().toLowerCase();
    if (!cleanQuery) {
      setTopicMatch(null);
      setMatchingPledges([]);
      setDynamicSummary(null);
      return;
    }

    const topicUrl = getCityDataUrl 
      ? getCityDataUrl(cityCode, 'topic_summaries') 
      : `/data/${cityCode === 'kyoto' ? '' : cityCode + '_'}topic_summaries.json`;
    
    const pledgeUrl = getCityDataUrl 
      ? getCityDataUrl(cityCode, 'pledge_tracker') 
      : `/data/pledge_tracker_${cityCode}.json`;

    // 1. 論点サマリーと公約トラッカーを並行フェッチ
    Promise.all([
      fetch(topicUrl).then(r => r.ok ? r.json() : []).catch(() => []),
      fetch(pledgeUrl).then(r => r.ok ? r.json() : {}).catch(() => ({}))
    ]).then(([topics, pledgeData]) => {
      
      // ① 論点マッチング（加重スコアリング・手書きif文を完全撤廃）
      let bestTopic = null;
      let highestScore = 0;

      topics.forEach(t => {
        let score = 0;
        const title = (t.title || '').toLowerCase();
        const cat = (t.category || '').toLowerCase();
        const lead = (t.lead_summary || '').toLowerCase();
        const keywords = (t.keywords || []).map(k => k.toLowerCase());

        if (title.includes(cleanQuery)) score += 10;
        if (cleanQuery.includes(title)) score += 8;
        if (keywords.some(k => k.includes(cleanQuery) || cleanQuery.includes(k))) score += 7;
        if (cat.includes(cleanQuery)) score += 3;
        if (lead.includes(cleanQuery)) score += 2;

        if (score > highestScore && score >= 5) {
          highestScore = score;
          bestTopic = t;
        }
      });
      setTopicMatch(bestTopic);

      // ② 公約トラッカーから「この政策を掲げる議員」を逆引き
      const matchedCouncilors = [];
      Object.entries(pledgeData).forEach(([speaker, data]) => {
        (data.tracked_items || []).forEach(item => {
          const headline = (item.headline || '').toLowerCase();
          const target = (item.target_issue || '').toLowerCase();
          const category = (item.category || '').toLowerCase();

          if (headline.includes(cleanQuery) || target.includes(cleanQuery) || category.includes(cleanQuery)) {
            matchedCouncilors.push({
              speaker,
              district: data.district,
              party: data.party,
              headline: item.headline,
              hasStatements: (item.council_statements || []).length > 0,
              statementCount: (item.council_statements || []).length
            });
          }
        });
      });
      // 質疑実績がある議員を優先して最大4名抽出
      matchedCouncilors.sort((a, b) => (b.hasStatements ? 1 : 0) - (a.hasStatements ? 1 : 0));
      setMatchingPledges(matchedCouncilors.slice(0, 4));

      // ③ 論点にも公約にも該当しない一般語彙の場合の動的要約
      if (!bestTopic && filteredThreads && filteredThreads.length > 0) {
        const topThreads = filteredThreads.slice(0, 3);
        setDynamicSummary({
          lead: `本議会において「${query}」に関連する質疑が計${filteredThreads.length}件記録されています。直近では主に以下の委員会・会議体で議論が行われています。`,
          points: topThreads.map(t => ({
            text: t.summary || (t.statement_text || '').slice(0, 100) + '...',
            speaker: t.speaker,
            date: t.meeting_date,
            title: t.meeting_title,
            official_url: t.official_url || t.source_url
          }))
        });
      } else {
        setDynamicSummary(null);
      }
    });
  }, [query, filteredThreads, cityCode]);

  if (!topicMatch && matchingPledges.length === 0 && !dynamicSummary) return null;

  return (
    <section className="bg-white rounded-2xl border border-indigo-200 p-5 md:p-6 shadow-sm space-y-5 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-amber-500" />

      {/* ヘッダー */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3.5">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600">
            <Sparkles className="w-4 h-4 fill-indigo-100" />
          </div>
          <div>
            <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
              Policy & Pledge Overview
            </span>
            <h2 className="text-base font-extrabold text-slate-900 leading-tight">
              論点と公約の現在地
            </h2>
          </div>
        </div>

        {topicMatch && onOpenTopicDetail && (
          <button
            onClick={() => onOpenTopicDetail(topicMatch.topic_id)}
            className="inline-flex items-center text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100/70 border border-indigo-200/80 px-3 py-1.5 rounded-lg transition-colors cursor-pointer group"
          >
            <span>政策タイムラインを見る</span>
            <ArrowRight className="w-3.5 h-3.5 ml-1 group-hover:translate-x-0.5 transition-transform" />
          </button>
        )}
      </div>

      {/* ① 論点マスターヒット時の要旨 */}
      {topicMatch && (
        <div className="space-y-4">
          <div className="p-3.5 rounded-xl bg-indigo-50/60 border border-indigo-100 text-xs space-y-1">
            <span className="text-[10px] font-black text-indigo-900 uppercase tracking-wider flex items-center gap-1">
              <Milestone className="w-3 h-3 text-indigo-600" /> 政策の現在地・到達点
            </span>
            <p className="text-slate-800 font-bold leading-relaxed">
              {topicMatch.current_status}
            </p>
          </div>

          <div>
            <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-wider mb-1">
              論点の背景と全体像
            </h3>
            <p className="text-xs md:text-sm text-slate-700 leading-relaxed font-medium">
              {topicMatch.lead_summary}
            </p>
          </div>
        </div>
      )}

      {/* ② 【NEW】公約連動：この政策を公約に掲げる議員 */}
      {matchingPledges.length > 0 && (
        <div className="pt-2 border-t border-slate-100 space-y-2.5">
          <div className="flex items-center gap-1.5 text-[11px] font-black text-slate-700">
            <UserCheck className="w-3.5 h-3.5 text-indigo-600" />
            <span>このテーマを重点公約に掲げる議員 ({matchingPledges.length}名)</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {matchingPledges.map((p, idx) => (
              <div 
                key={idx}
                onClick={() => onSelectSpeaker && onSelectSpeaker(p.speaker)}
                className={`p-2.5 rounded-xl border text-xs transition-all ${
                  onSelectSpeaker ? 'cursor-pointer hover:border-indigo-300 hover:shadow-2xs bg-slate-50/80' : 'bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between gap-1 mb-1">
                  <div className="flex items-center gap-1.5 font-bold text-slate-800">
                    <span>{p.speaker}</span>
                    <span className="text-[10px] text-slate-400 font-normal">({p.party})</span>
                  </div>
                  {p.hasStatements ? (
                    <span className="inline-flex items-center text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                      <CheckCircle2 className="w-2.5 h-2.5 mr-0.5" /> 質疑実績あり
                    </span>
                  ) : (
                    <span className="text-[10px] text-slate-400">継続監視中</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-600 line-clamp-1">
                  📌 {p.headline}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ③ 一時情報（原本）リンク */}
      {topicMatch && topicMatch.timeline_phases?.length > 0 && (
        <div className="pt-2 border-t border-slate-100 space-y-2">
          <div className="flex items-center gap-1.5 text-[11px] font-black text-slate-600">
            <MapPin className="w-3.5 h-3.5 text-rose-500" />
            <span>一次情報（公式原本）の所在</span>
          </div>
          <div className="space-y-1.5">
            {topicMatch.timeline_phases.slice(-2).map((phase, pIdx) => {
              const ex = phase.exchanges?.[0];
              if (!ex) return null;
              return (
                <div key={pIdx} className="flex flex-col sm:flex-row sm:items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-200 gap-2">
                  <div className="text-xs">
                    <span className="font-bold text-slate-800 mr-2">【{phase.period}】</span>
                    <span className="text-slate-600">{ex.meeting_title} ({ex.meeting_date})</span>
                  </div>
                  <button
                    onClick={() => openOfficialMinute(ex)}
                    title={getOfficialLinkTooltip(ex)}
                    className="inline-flex items-center text-[11px] font-bold text-slate-700 hover:text-indigo-600 bg-white hover:bg-slate-100 border border-slate-200 px-2.5 py-1 rounded-lg transition-colors cursor-pointer shrink-0 shadow-2xs"
                  >
                    <Landmark className="w-3 h-3 mr-1 text-indigo-600" />
                    <span>本議会 原本で確認</span>
                    <ExternalLink className="w-2.5 h-2.5 ml-1 text-slate-400" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ④ 一般キーワード検索時のフォールバック要約 */}
      {!topicMatch && dynamicSummary && (
        <div className="space-y-4">
          <p className="text-xs md:text-sm text-slate-700 leading-relaxed font-medium">
            {dynamicSummary.lead}
          </p>
          <div className="space-y-2">
            <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-rose-500" />
              主要な議論の所在（一次情報）
            </h3>
            <div className="space-y-2">
              {dynamicSummary.points.map((pt, idx) => (
                <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-slate-200/60 pb-1.5">
                    <span className="font-bold text-slate-800">
                      🏛️ {pt.title} ({pt.date})
                    </span>
                    <button
                      onClick={() => openOfficialMinute(pt)}
                      className="inline-flex items-center text-[10px] font-bold text-slate-700 hover:text-indigo-600 bg-white border border-slate-200 px-2 py-0.5 rounded transition-colors cursor-pointer shrink-0"
                    >
                      <Landmark className="w-3 h-3 mr-1 text-indigo-600" />
                      原本を開く
                      <ExternalLink className="w-2.5 h-2.5 ml-1 text-slate-400" />
                    </button>
                  </div>
                  <p className="text-slate-600 leading-relaxed">{pt.text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}