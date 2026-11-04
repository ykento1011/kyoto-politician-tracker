import React, { useState, useEffect } from 'react';
import { 
  Sparkles, Landmark, ExternalLink, Milestone, 
  MapPin, ArrowRight, UserCheck, CheckCircle2,
  FileText, MessageSquareQuote
} from 'lucide-react';
import { openOfficialMinute, getOfficialLinkTooltip } from '../utils/officialLink';
import { getCityDataUrl } from '../config/cities';

// 質疑データから動的タイムラインとメタデータを構築する関数
const buildDynamicTimeline = (query, threads) => {
  if (!threads || threads.length === 0) return null;

  // 1. 日付順（昇順）にソート
  const sorted = [...threads].sort((a, b) => 
    (a.meeting_date || '').localeCompare(b.meeting_date || '')
  );

  const first = sorted[0];
  const latest = sorted[sorted.length - 1];
  const mid = sorted.length > 2 ? sorted[Math.floor(sorted.length / 2)] : null;

  // 2. 頻出の委員会および議員・会派を集計
  const committeeCounts = {};
  const speakerCounts = {};

  sorted.forEach(t => {
    if (t.meeting_title) {
      committeeCounts[t.meeting_title] = (committeeCounts[t.meeting_title] || 0) + 1;
    }
    if (t.speaker) {
      const label = `${t.speaker}${t.party ? `（${t.party}）` : ''}`;
      speakerCounts[label] = (speakerCounts[label] || 0) + 1;
    }
  });

  const topCommittees = Object.keys(committeeCounts)
    .sort((a, b) => committeeCounts[b] - committeeCounts[a])
    .slice(0, 3);

  const topSpeakers = Object.keys(speakerCounts)
    .sort((a, b) => speakerCounts[b] - speakerCounts[a])
    .slice(0, 4);

  // 3. フェーズの構成（発端・進展・直近）
  const phases = [
    {
      label: '発端・初期の質疑',
      badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
      data: first
    }
  ];

  if (mid && mid !== first && mid !== latest) {
    phases.push({
      label: '議論の展開・継続審議',
      badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
      data: mid
    });
  }

  if (latest && latest !== first) {
    phases.push({
      label: '直近の動向・到達点',
      badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
      data: latest
    });
  }

  return {
    totalCount: sorted.length,
    startDate: first.meeting_date,
    latestDate: latest.meeting_date,
    topCommittees,
    topSpeakers,
    phases
  };
};

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

    const topicUrl = (getCityDataUrl && getCityDataUrl(cityCode, 'topicSummaries')) || `/data/${cityCode}_topic_summaries.json`;
    const fallbackTopicUrl = `/data/${cityCode === 'kyoto' ? 'topic_summaries.json' : cityCode + '_topic_summaries.json'}`;
    const pledgeUrl = (getCityDataUrl && getCityDataUrl(cityCode, 'pledgeTracker')) || `/data/${cityCode === 'kyoto' ? '' : cityCode + '_'}pledge_tracker.json`;

    // 1. 論点サマリーと公約トラッカーを並行フェッチ
    Promise.all([
      fetch(topicUrl)
        .then(r => r.ok ? r.json() : fetch(fallbackTopicUrl).then(r2 => r2.ok ? r2.json() : []))
        .catch(() => []),
      fetch(pledgeUrl)
        .then(r => r.ok ? r.json() : {})
        .catch(() => ({}))
    ]).then(([topics, pledgeData]) => {
      
      // ① 論点マッチング（加重スコアリング・型ガード付き）
      let bestTopic = null;
      let highestScore = 0;

      if (Array.isArray(topics)) {
        topics.forEach(t => {
          let score = 0;
          const title = (t.title || '').toLowerCase();
          const cat = (t.category || '').toLowerCase();
          
          // 型ガード: lead_summary が文字列でもオブジェクトでも安全にテキスト取得
          const rawLead = t.lead_summary;
          const lead = (typeof rawLead === 'object' && rawLead !== null ? (rawLead.summary || '') : (rawLead || '')).toLowerCase();
          const keywords = (t.keywords || []).map(k => String(k).toLowerCase());

          // 部分一致・相互含有判定
            // タイトルまたはキーワードへの明確な合致を必須とし、本文の単語言及のみでの誤選定を排除
            const titleMatch = title.includes(cleanQuery) || cleanQuery.includes(title);
            const keywordMatch = keywords.some(k => k.includes(cleanQuery) || cleanQuery.includes(k));

            if (titleMatch) score += 10;
            if (keywordMatch) score += 7;
            if (lead.includes(cleanQuery)) score += 2; // 本文言及はボーナス加点に留める
            if (cat.includes(cleanQuery)) score += 1;

            // 採用条件: タイトルまたはキーワードに明確に合致し、スコア7以上
            if ((titleMatch || keywordMatch) && score > highestScore && score >= 7) {
              highestScore = score;
              bestTopic = t;
            }
        });
      }
      setTopicMatch(bestTopic);

      // ② 公約トラッカーから「この政策を掲げる議員」を逆引き
      const matchedCouncilors = [];
      if (pledgeData && typeof pledgeData === 'object') {
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
      }
      // 質疑実績がある議員を優先して最大4名抽出
      matchedCouncilors.sort((a, b) => (b.hasStatements ? 1 : 0) - (a.hasStatements ? 1 : 0));
      setMatchingPledges(matchedCouncilors.slice(0, 4));

        // ③ 論点未ヒット時のフォールバック要約（動的タイムライン生成）
        if (!bestTopic && filteredThreads && filteredThreads.length > 0) {
          const timelineData = buildDynamicTimeline(cleanQuery, filteredThreads);
          setDynamicSummary(timelineData);
        } else {
          setDynamicSummary(null);
        }
    });
  }, [query, filteredThreads, cityCode]);

  if (!topicMatch && matchingPledges.length === 0 && !dynamicSummary) return null;

  // lead_summary の表示用文字列と計画名を取得
  const leadSummaryText = topicMatch 
    ? (typeof topicMatch.lead_summary === 'object' && topicMatch.lead_summary !== null 
        ? topicMatch.lead_summary.summary 
        : topicMatch.lead_summary)
    : '';
  const leadPlanName = topicMatch && typeof topicMatch.lead_summary === 'object' && topicMatch.lead_summary !== null
    ? topicMatch.lead_summary.plan_name
    : null;

  return (
    <section data-testid="ai-search-answer" className="bg-white rounded-2xl border border-indigo-200 p-5 md:p-6 shadow-sm space-y-5 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-amber-500" />

      {/* ヘッダー */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3.5">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600">
            <Sparkles className="w-4 h-4 fill-indigo-100" />
          </div>
          <div>
            <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
              {topicMatch ? 'Policy & Pledge Overview' : 'Council Discussion Summary'}
            </span>
            <h2 className="text-base font-extrabold text-slate-900 leading-tight">
              {topicMatch ? '政策の現在地・論点の背景と全体像' : `「${query}」に関する議会の議論傾向`}
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
          {topicMatch.current_status && (
            <div className="p-3.5 rounded-xl bg-indigo-50/60 border border-indigo-100 text-xs space-y-1">
              <span className="text-[10px] font-black text-indigo-900 uppercase tracking-wider flex items-center gap-1">
                <Milestone className="w-3 h-3 text-indigo-600" /> 政策の現在地・到達点
              </span>
              <p className="text-slate-800 font-bold leading-relaxed">
                {topicMatch.current_status}
              </p>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between gap-2 mb-1">
              <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-wider">
                論点の背景と全体像
              </h3>
              {leadPlanName && (
                <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50/80 px-2 py-0.5 rounded border border-indigo-100 truncate max-w-[280px]">
                  📌 {leadPlanName}
                </span>
              )}
            </div>
            <p className="text-xs md:text-sm text-slate-700 leading-relaxed font-medium">
              {leadSummaryText}
            </p>
          </div>
        </div>
      )}

      {/* ② 公約連動：この政策を公約に掲げる議員 */}
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

      {/* ③ 一次情報（原本）リンク（論点マスターヒット時） */}
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
                    <span>議事録原本を確認</span>
                    <ExternalLink className="w-2.5 h-2.5 ml-1 text-slate-400" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

        {/* ④ 一般キーワード検索時の動的タイムライン＆サマリー */}
        {!topicMatch && dynamicSummary && (
          <div className="space-y-4">
            {/* 概要ヘッダーカード */}
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-extrabold text-slate-800 text-sm">
                  「{query}」に関する議会での議論タイムライン
                </span>
                <span className="text-[11px] font-bold text-slate-500">
                  計 {dynamicSummary.totalCount} 件の関連質疑 ({dynamicSummary.startDate} 〜 {dynamicSummary.latestDate})
                </span>
              </div>

              {/* 主な審議場所・頻出議員 */}
              <div className="pt-2 border-t border-slate-200/60 flex flex-wrap gap-y-1.5 gap-x-4 text-[11px] text-slate-600">
                {dynamicSummary.topCommittees.length > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-slate-400">主な審議:</span>
                    <span>{dynamicSummary.topCommittees.join(' / ')}</span>
                  </div>
                )}
                {dynamicSummary.topSpeakers.length > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-slate-400">主な質問者:</span>
                    <span>{dynamicSummary.topSpeakers.join(', ')}</span>
                  </div>
                )}
              </div>
            </div>

            {/* 垂直タイムライン */}
            <div className="relative pl-4 space-y-4 before:content-[''] before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-indigo-100">
              {dynamicSummary.phases.map((phase, idx) => {
                const item = phase.data;
                const text = item.summary || (item.statement_text || '').slice(0, 140) + '...';
                return (
                  <div key={idx} className="relative space-y-1.5">
                    {/* タイムラインのポイント丸ポチ */}
                    <div className="absolute -left-[19px] top-1.5 w-2.5 h-2.5 rounded-full bg-indigo-500 ring-4 ring-white" />

                    <div className="flex flex-wrap items-center justify-between gap-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-extrabold px-1.5 py-0.5 rounded border ${phase.badgeColor}`}>
                          {phase.label}
                        </span>
                        <span className="text-xs font-bold text-slate-800">
                          {item.meeting_date}
                        </span>
                        <span className="text-xs text-slate-500">
                          {item.meeting_title}
                        </span>
                      </div>

                      {/* 一次情報原本リンク */}
                      <button
                        type="button"
                        onClick={() => openOfficialMinute(item)}
                        title={getOfficialLinkTooltip(item)}
                        className="inline-flex items-center text-[10px] font-bold text-slate-700 hover:text-indigo-600 bg-white border border-slate-200 px-2 py-0.5 rounded transition-colors cursor-pointer shrink-0 shadow-2xs"
                      >
                        <Landmark className="w-3 h-3 mr-1 text-indigo-600" />
                        <span>原本を確認</span>
                        <ExternalLink className="w-2.5 h-2.5 ml-1 text-slate-400" />
                      </button>
                    </div>

                    <div className="p-3 bg-white rounded-xl border border-slate-200 text-xs text-slate-700 leading-relaxed shadow-xs">
                      <div className="font-bold text-slate-900 mb-1">
                        🗣️ {item.speaker} {item.party && <span className="font-normal text-slate-500 text-[11px]">({item.party})</span>}
                      </div>
                      <p>{text}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
    </section>
  );
}
