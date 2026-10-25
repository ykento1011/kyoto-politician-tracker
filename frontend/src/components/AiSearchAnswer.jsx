import React, { useState, useEffect } from 'react';
import { 
  Sparkles, Landmark, ExternalLink, Milestone, 
  MapPin, Calendar, ArrowRight, ShieldCheck 
} from 'lucide-react';
import { openOfficialMinute, getOfficialLinkTooltip } from '../utils/officialLink';

export default function AiSearchAnswer({ query, filteredThreads, onOpenTopicDetail }) {
  const [topicMatch, setTopicMatch] = useState(null);
  const [dynamicSummary, setDynamicSummary] = useState(null);

  useEffect(() => {
    const cleanQuery = (query || '').trim().toLowerCase();
    if (!cleanQuery) return;

    // 1. まず 20大論点マスター（topic_summaries.json）から完全/部分一致を探索（高速・確実）
    fetch('/data/topic_summaries.json')
      .then(res => res.ok ? res.json() : [])
      .then(topics => {
        const matched = topics.find(t => 
          t.title.toLowerCase().includes(cleanQuery) ||
          cleanQuery.includes(t.title.toLowerCase()) ||
          t.category.toLowerCase().includes(cleanQuery) ||
          (cleanQuery.includes('空き家') && t.topic_id === 'vacant_house_tax') ||
          (cleanQuery.includes('バス') && t.topic_id === 'bus_fare_priority') ||
          (cleanQuery.includes('宿泊税') && t.topic_id === 'accommodation_tax_revision') ||
          (cleanQuery.includes('給食') && t.topic_id === 'school_lunch_free') ||
          (cleanQuery.includes('医療費') && t.topic_id === 'children_medical_subsidy')
        );

        if (matched) {
          setTopicMatch(matched);
          setDynamicSummary(null);
        } else {
          setTopicMatch(null);
          // 2. マスターにない独自ワードの場合、ヒットしたスレッドから要点を抽出
          if (filteredThreads && filteredThreads.length > 0) {
            const topThreads = filteredThreads.slice(0, 3);
            setDynamicSummary({
              lead: `本議会において「${query}」に関連する質疑が計${filteredThreads.length}件記録されています。直近では主に以下の委員会・会議体で議論が行われています。`,
              points: topThreads.map(t => ({
                text: t.summary || (t.statement_text || '').slice(0, 100) + '...',
                speaker: t.speaker,
                date: t.meeting_date,
                title: t.meeting_title,
                source_url: t.source_url
              }))
            });
          }
        }
      })
      .catch(() => {
        setTopicMatch(null);
      });
  }, [query, filteredThreads]);

  if (!topicMatch && !dynamicSummary) return null;

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
              Policy Issue Overview
            </span>
            <h2 className="text-base font-extrabold text-slate-900 leading-tight">
              論点の要旨と現在地
            </h2>
          </div>
        </div>

        {topicMatch && onOpenTopicDetail && (
          <button
            onClick={() => onOpenTopicDetail(topicMatch.topic_id)}
            className="inline-flex items-center text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100/70 border border-indigo-200/80 px-3 py-1.5 rounded-lg transition-colors cursor-pointer group"
          >
            <span>年度別の政策タイムラインを見る</span>
            <ArrowRight className="w-3.5 h-3.5 ml-1 group-hover:translate-x-0.5 transition-transform" />
          </button>
        )}
      </div>

      {/* ① コア論点マスターにヒットした場合の高品質解説 */}
      {topicMatch ? (
        <div className="space-y-4">
          {/* 現在地のハイライト */}
          <div className="p-3.5 rounded-xl bg-indigo-50/60 border border-indigo-100 text-xs space-y-1">
            <span className="text-[10px] font-black text-indigo-900 uppercase tracking-wider flex items-center gap-1">
              <Milestone className="w-3 h-3 text-indigo-600" /> 政策の現在地・到達点
            </span>
            <p className="text-slate-800 font-bold leading-relaxed">
              {topicMatch.current_status}
            </p>
          </div>

          {/* 論点の全体像 */}
          <div>
            <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-wider mb-1">
              論点の背景と全体像
            </h3>
            <p className="text-xs md:text-sm text-slate-700 leading-relaxed font-medium">
              {topicMatch.lead_summary}
            </p>
          </div>

          {/* 主な対立軸・ポイント */}
          {topicMatch.conflict_axes?.length > 0 && (
            <div className="space-y-1.5">
              <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-wider">
                主な争点・対立軸
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {topicMatch.conflict_axes.map((axis, i) => (
                  <div key={i} className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 font-medium flex items-start gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                    <span>{axis}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 💡 一次情報の位置情報（出典の所在） */}
          <div className="pt-2 border-t border-slate-100 space-y-2">
            <div className="flex items-center gap-1.5 text-[11px] font-black text-slate-600">
              <MapPin className="w-3.5 h-3.5 text-rose-500" />
              <span>一次情報（公式原本）の所在</span>
            </div>

            <div className="space-y-1.5">
              {topicMatch.timeline_phases?.slice(-2).map((phase, pIdx) => {
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
        </div>
      ) : (
        /* ② 一般キーワードの場合の要点整理と位置情報 */
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
                  <p className="text-slate-600 leading-relaxed">
                    {pt.text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}