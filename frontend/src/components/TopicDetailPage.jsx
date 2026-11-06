import { getCityDataUrl } from '../config/cities';
import React, { useState, useEffect, useMemo } from 'react';
import { 
  ArrowLeft, MessageCircle, Milestone, Calendar, Landmark, ExternalLink, 
  Layers, Clock, Share2, Check, ArrowUpDown, ChevronDown, ChevronUp, Scale
} from 'lucide-react';
import { openOfficialMinute, getOfficialLinkTooltip } from '../utils/officialLink';

/**
 * conflict_axes を新旧スキーマ問わず安全に構造化オブジェクトへ正規化する
 */
function normalizeConflictAxis(rawAxis) {
  if (!rawAxis) return null;

  // ① 新スキーマ（構造化オブジェクト）の場合
  if (typeof rawAxis === 'object' && rawAxis !== null && (rawAxis.issue_title || rawAxis.side_a)) {
    return {
      isStructured: true,
      isVs: true,
      issueTitle: rawAxis.issue_title || '',
      summary: rawAxis.summary || '',
      sideA: {
        title: rawAxis.side_a?.title || '推進・改革側の視点',
        actor: rawAxis.side_a?.actor || '市執行部・推進派',
        stance: rawAxis.side_a?.stance || '',
        points: Array.isArray(rawAxis.side_a?.points) ? rawAxis.side_a.points : []
      },
      sideB: {
        title: rawAxis.side_b?.title || '慎重・異論側の視点',
        actor: rawAxis.side_b?.actor || '議会慎重派・懸念派',
        stance: rawAxis.side_b?.stance || '',
        points: Array.isArray(rawAxis.side_b?.points) ? rawAxis.side_b.points : []
      }
    };
  }

  // ② 旧形式（文字列型）の後方互換パース
  const text = typeof rawAxis === 'object' 
    ? (rawAxis.axis || rawAxis.description || JSON.stringify(rawAxis)) 
    : String(rawAxis);

  const colonMatch = text.match(/^(.*?)[：:](.*)$/s);
  let titlePart = text;
  let descPart = '';

  if (colonMatch) {
    titlePart = colonMatch[1].trim();
    descPart = colonMatch[2].trim();
  }

  const vsParts = titlePart.split(/\s*(?:vs|VS|ｖｓ|ＶＳ)\s*/);
  const isVs = vsParts.length >= 2;
  const leftTitle = vsParts[0]?.trim() || '';
  const rightTitle = vsParts[1]?.trim() || '';

  let leftDesc = '';
  let rightDesc = '';

  if (descPart) {
    if (/\s*(?:vs|VS|ｖｓ|ＶＳ)\s*/.test(descPart)) {
      const dParts = descPart.split(/\s*(?:vs|VS|ｖｓ|ＶＳ)\s*/);
      leftDesc = dParts[0]?.trim() || '';
      rightDesc = dParts[1]?.trim() || '';
    } else {
      const splitMatch = descPart.match(/^(.*?(?:一方[、で]|これに対し[て、]?|しかし[、]?))(.*)$/s);
      if (splitMatch) {
        leftDesc = splitMatch[1].trim();
        rightDesc = splitMatch[2].trim();
      } else {
        leftDesc = descPart;
      }
    }
  }

  return {
    isStructured: false,
    isVs,
    issueTitle: isVs ? `${leftTitle} vs ${rightTitle}` : titlePart,
    summary: '',
    sideA: {
      title: leftTitle,
      actor: '視点 A',
      stance: '',
      points: leftDesc ? [leftDesc] : []
    },
    sideB: {
      title: rightTitle,
      actor: '視点 B',
      stance: '',
      points: rightDesc ? [rightDesc] : []
    },
    rawText: text
  };
}

export default function TopicDetailPage({ topicId, onBack, cityCode = 'kyoto', onViewContext, statements = [] }) {
  const cityName = cityCode === 'kobe' ? '神戸市会' : cityCode === 'nagoya' ? '名古屋市会' : cityCode === 'osaka' ? '大阪市会' : '京都市会';
  const [topic, setTopic] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [copiedShare, setCopiedShare] = useState(false);
  const [sortOrder, setSortOrder] = useState('desc');

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });

    const TOPIC_ALIASES = {
      "nagoya_city_univ_hospitals_dx": "nagoya-core-community-medical-system",
      "nagoya_castle_wooden_restoration": "nagoya-mayor-nagoya_p1",
      "nagoya_citizen_tax_cut": "nagoya-mayor-nagoya_p2",
      "nagoya_keiro_pass_reform": "nagoya-mayor-nagoya_p3",
      "nagoya_childcare_support": "nagoya-mayor-nagoya_p5",
      "nagoya_fiscal_reform": "nagoya-core-fiscal-discipline-reform",
      "nagoya_school_education": "nagoya-core-school-education-environment"
    };
    const targetTopicId = TOPIC_ALIASES[topicId] || topicId;

    const dataUrl = getCityDataUrl(cityCode, 'topicSummaries') || `/data/${cityCode}_topic_summaries.json`;
    fetch(dataUrl)
      .then((res) => res.json())
      .then((data) => {
        if (!Array.isArray(data) || data.length === 0) {
          setTopic(null);
          setIsLoading(false);
          return;
        }
        let found = data.find((t) => t.topic_id === targetTopicId);
        if (!found && topicId) {
          found = data.find((t) => t.topic_id.includes(topicId) || topicId.includes(t.topic_id));
        }
        setTopic(found || data[0]);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load topic:', err);
        setIsLoading(false);
      });
  }, [topicId, cityCode]);

  const handleViewExchangeContext = (ex) => {
    if (!ex) return;
    if (typeof onViewContext !== 'function') return;
    const allStmts = Array.isArray(statements) ? statements : [];

    let target = allStmts.find((s) => s.id === (ex.statement_id || ex.id));
    if (!target && ex.meeting_id && ex.sequence_number !== undefined) {
      target = allStmts.find(
        (s) =>
          String(s.meeting_id) === String(ex.meeting_id) &&
          String(s.sequence_number) === String(ex.sequence_number)
      );
    }
    if (!target) {
      target = {
        ...ex,
        id: ex.statement_id || ex.id || `topic_stmt_${ex.meeting_date}_${ex.sequence_number}`,
        meeting_id: String(ex.meeting_id || ''),
        sequence_number: ex.sequence_number,
        speaker: ex.speaker,
        meeting_date: ex.meeting_date,
        meeting_title: ex.meeting_title,
        committee_name: ex.meeting_title,
        statement_text: ex.statement_summary,
        summary: ex.statement_summary,
        official_url: ex.official_url || ex.source_url || ex.url
      };
    }
    onViewContext(target);
  };

  const handleShare = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
      setCopiedShare(true);
      setTimeout(() => setCopiedShare(false), 2500);
    }
  };

  const sortedPhases = useMemo(() => {
    if (!topic?.timeline_phases) return [];
    const list = [...topic.timeline_phases];
    return sortOrder === 'desc' ? list.reverse() : list;
  }, [topic, sortOrder]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center">
        <div className="text-sm font-bold text-slate-500">政策論点データを読み込み中...</div>
      </div>
    );
  }

  if (!topic) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] p-8 text-center space-y-4">
        <p className="text-sm font-bold text-slate-600">論点データが見つかりませんでした。</p>
        <button
          onClick={onBack}
          className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-bold"
        >
          トップへ戻る
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans pb-24 selection:bg-indigo-500 selection:text-white">
      {/* 画面上部固定バー */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-30 px-6 py-3.5 shadow-2xs">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <button
            onClick={onBack}
            className="inline-flex items-center text-xs font-bold text-slate-600 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50 border border-slate-200 px-3.5 py-2 rounded-xl transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4 mr-1.5" />
            論戦マップへ戻る
          </button>

          <button
            onClick={handleShare}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 hover:text-indigo-600 bg-white border border-slate-200 px-3 py-2 rounded-xl hover:bg-slate-50 transition-colors cursor-pointer"
          >
            {copiedShare ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-emerald-700">URLコピー完了</span>
              </>
            ) : (
              <>
                <Share2 className="w-3.5 h-3.5 text-slate-400" />
                <span>この論点をシェア</span>
              </>
            )}
          </button>
        </div>
      </div>

      <main className="max-w-4xl mx-auto px-6 pt-8 space-y-8">
        
        {/* ① ヘッダー部 */}
        <header className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-100 flex items-center gap-1">
              <Layers className="w-3.5 h-3.5" />
              {topic.category}
            </span>
            <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
              <Clock className="w-3 h-3" />
              最新質疑: {topic.last_updated}
            </span>
            <span className="text-xs text-slate-400 font-medium">
              ・ 累積 {topic.thread_count} 質疑スレッド
            </span>
          </div>

          <h1 className="text-2xl md:text-3xl font-black text-slate-900 tracking-tight leading-tight">
            {topic.title}
          </h1>
        </header>

        {/* ② AI エグゼクティブ・サマリー */}
        <section className="bg-white rounded-3xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-6">
          <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
            <Milestone className="w-4 h-4" />
            AI EXECUTIVE SUMMARY / 政策の現在地と争点
          </div>

          {/* 対立軸（VS構図）カード */}
            {topic.conflict_axes?.length > 0 && (
              <div className="space-y-5 pt-1">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 rounded-md text-[11px] font-black uppercase tracking-wider bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-1.5 shadow-2xs">
                      <Scale className="w-3.5 h-3.5 text-rose-600" />
                      主な争点・対立軸（VS構図）
                    </span>
                    <span className="text-xs font-bold text-slate-500 hidden sm:inline">
                      議会で激論となっている政策的対立構図
                    </span>
                  </div>
                  <span className="text-[11px] font-bold text-slate-400">
                    全 {topic.conflict_axes.length} 件の論点
                  </span>
                </div>

                <div className="space-y-5">
                  {(Array.isArray(topic.conflict_axes) ? topic.conflict_axes : []).map((axis, i) => {
                    const item = normalizeConflictAxis(axis);
                    if (!item || (!item.isVs && !item.isStructured)) {
                      return (
                        <div key={i} className="p-4 bg-slate-50 border border-slate-200 rounded-2xl text-xs text-slate-700 font-medium leading-relaxed">
                          {typeof axis === 'object' ? JSON.stringify(axis) : axis}
                        </div>
                      );
                    }

                    return (
                      <div key={i} className="bg-slate-50/90 border border-slate-200/90 rounded-2xl p-4 sm:p-5 shadow-2xs space-y-3.5">
                        {/* 論点ヘッダー */}
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between text-[11px] font-black text-slate-400">
                            <span className="px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">論点 {i + 1}</span>
                          </div>
                          {item.issueTitle && (
                            <h3 className="text-base sm:text-lg font-black text-slate-900 leading-snug">
                              {item.issueTitle}
                            </h3>
                          )}
                          {item.summary && (
                            <p className="text-xs sm:text-[13px] text-slate-600 font-medium leading-relaxed bg-white/70 p-2.5 rounded-xl border border-slate-200/60">
                              💡 {item.summary}
                            </p>
                          )}
                        </div>

                        {/* 対立グリッド */}
                        <div className="relative grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch pt-1">
                          {/* 視点 A */}
                          <div className="bg-white rounded-xl p-4 sm:p-4.5 border border-indigo-100 shadow-2xs flex flex-col justify-between space-y-3.5">
                            <div className="space-y-2">
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className="px-2 py-0.5 rounded text-[10px] font-black bg-indigo-50 text-indigo-700 border border-indigo-200/70">
                                  視点 A
                                </span>
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                                  👤 {item.sideA.actor}
                                </span>
                              </div>
                              <h4 className="text-sm sm:text-base font-black text-slate-900 leading-snug">
                                {item.sideA.title}
                              </h4>
                              {item.sideA.stance && (
                                <div className="p-2.5 rounded-lg bg-indigo-50/60 border border-indigo-100/70 text-xs font-bold text-indigo-950 leading-relaxed">
                                  {item.sideA.stance}
                                </div>
                              )}
                            </div>
                            {item.sideA.points.length > 0 && (
                              <ul className="text-xs text-slate-700 space-y-1.5 pt-2.5 border-t border-slate-100">
                                {item.sideA.points.map((pt, pIdx) => (
                                  <li key={pIdx} className="flex items-start gap-1.5 leading-relaxed">
                                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                                    <span>{pt}</span>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>

                          {/* 中央 VS バッジ */}
                          <div className="hidden md:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-slate-900 text-white font-black text-[11px] items-center justify-center border-2 border-white shadow-md z-10 pointer-events-none">
                            VS
                          </div>
                          <div className="flex md:hidden items-center justify-center -my-1">
                            <span className="px-3 py-0.5 rounded-full bg-slate-900 text-white font-black text-[10px] shadow-xs">
                              VS
                            </span>
                          </div>

                          {/* 視点 B */}
                          <div className="bg-white rounded-xl p-4 sm:p-4.5 border border-amber-100 shadow-2xs flex flex-col justify-between space-y-3.5">
                            <div className="space-y-2">
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className="px-2 py-0.5 rounded text-[10px] font-black bg-amber-50 text-amber-800 border border-amber-200/70">
                                  視点 B
                                </span>
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                                  👤 {item.sideB.actor}
                                </span>
                              </div>
                              <h4 className="text-sm sm:text-base font-black text-slate-900 leading-snug">
                                {item.sideB.title}
                              </h4>
                              {item.sideB.stance && (
                                <div className="p-2.5 rounded-lg bg-amber-50/60 border border-amber-100/70 text-xs font-bold text-amber-950 leading-relaxed">
                                  {item.sideB.stance}
                                </div>
                              )}
                            </div>
                            {item.sideB.points.length > 0 && (
                              <ul className="text-xs text-slate-700 space-y-1.5 pt-2.5 border-t border-slate-100">
                                {item.sideB.points.map((pt, pIdx) => (
                                  <li key={pIdx} className="flex items-start gap-1.5 leading-relaxed">
                                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                                    <span>{pt}</span>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 制度設計・検討の現在地 */}
          <div className="p-4 rounded-2xl bg-indigo-50/60 border border-indigo-100 text-indigo-950 space-y-1.5">
            <div className="text-[11px] font-black uppercase tracking-wider text-indigo-800">
              【制度設計・検討の現在地】
            </div>
            <p className="text-sm font-bold text-indigo-950 leading-relaxed">
              {topic.current_status}
            </p>
          </div>

          {/* 背景と根拠資料 */}
          <div className="space-y-3 pt-2">
            <h2 className="text-xs font-black text-slate-400 uppercase tracking-wider flex items-center justify-between">
              <span>論点の全体像・背景・根拠資料</span>
              {typeof topic.lead_summary === 'object' && topic.lead_summary?.doc_url && (
                <a
                  href={topic.lead_summary.doc_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50/70 hover:bg-indigo-100/80 px-2.5 py-1 rounded-lg border border-indigo-200/60 transition-colors"
                >
                  <ExternalLink className="w-3 h-3" />
                  <span>公式計画・行政資料を開く</span>
                </a>
              )}
            </h2>

            {typeof topic.lead_summary === 'object' && topic.lead_summary !== null ? (
              <div className="space-y-3">
                {(topic.lead_summary.plan_name || topic.lead_summary.source_name) && (
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 flex flex-wrap items-center justify-between gap-2 text-xs">
                    <div className="flex items-center gap-2 font-bold text-slate-800">
                      <Landmark className="w-3.5 h-3.5 text-indigo-600" />
                      <span>{topic.lead_summary.plan_name || topic.lead_summary.source_name}</span>
                    </div>
                    {topic.lead_summary.date && (
                      <span className="text-[11px] font-medium text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                        {topic.lead_summary.date}
                      </span>
                    )}
                  </div>
                )}
                <div className="p-4 bg-white border border-slate-200/80 rounded-2xl shadow-2xs">
                  <p className="text-sm leading-relaxed text-slate-600 font-medium whitespace-pre-line">
                    {topic.lead_summary.summary || topic.lead_summary.description || JSON.stringify(topic.lead_summary)}
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-white border border-slate-200/80 rounded-2xl shadow-2xs">
                <p className="text-sm leading-relaxed text-slate-600 font-medium whitespace-pre-line">
                  {topic.lead_summary || '詳細な政策背景は現在編集中です。'}
                </p>
              </div>
            )}
          </div>
        </section>

        {/* ③ Policy Timeline */}
        <section className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
            <div>
              <h2 className="text-lg font-black text-slate-900 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-indigo-600" />
                Policy Timeline / 議論の変遷
              </h2>
              <p className="text-xs text-slate-400 font-bold mt-0.5">
                {sortOrder === 'desc' ? '直近の到達点から過去の経緯へ遡って表示しています' : '過去の発端から現在へ時系列順に表示しています'}
              </p>
            </div>

            <button
              onClick={() => setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc')}
              className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50/80 hover:bg-indigo-100/70 border border-indigo-200/80 px-3 py-1.5 rounded-xl transition-colors cursor-pointer self-start sm:self-auto"
            >
              <ArrowUpDown className="w-3.5 h-3.5" />
              <span>{sortOrder === 'desc' ? '最新から表示中' : '過去から表示中'}</span>
              {sortOrder === 'desc' ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
            </button>
          </div>

          <div className="relative border-l-2 border-indigo-200 ml-4 space-y-8 pl-6 md:pl-8 py-2">
            {sortedPhases.map((phase, idx) => (
              <div key={idx} className="relative space-y-3.5">
                
                {/* タイムラインマーカー */}
                <div className="absolute -left-[33px] md:-left-[41px] top-1 w-4 h-4 rounded-full bg-white border-4 border-indigo-600 shadow-sm" />

                <div>
                  <span className="text-xs font-black text-indigo-600 tracking-wide uppercase">
                    {phase.period}
                  </span>
                  <h3 className="text-base font-extrabold text-slate-900 mt-0.5">
                    【{phase.phase_title}】
                  </h3>
                </div>

                {/* 市側の公式答弁姿勢 */}
                <div className="p-4 rounded-2xl bg-white border border-slate-200 text-xs space-y-1.5 shadow-2xs">
                  <span className="text-[10px] font-black text-slate-500 flex items-center gap-1.5 uppercase">
                    <Landmark className="w-3.5 h-3.5 text-indigo-600" /> 行政・市側の公式姿勢
                  </span>
                  <p className="text-slate-800 font-bold leading-relaxed">
                    {phase.city_stance}
                  </p>
                </div>

                {/* 議場での質疑ログ（アコーディオン） */}
                {phase.exchanges?.length > 0 && (
                  <details className="group bg-slate-50 border border-slate-200 rounded-2xl overflow-hidden shadow-2xs">
                    <summary className="flex items-center justify-between p-3.5 cursor-pointer text-xs font-bold text-slate-700 hover:bg-slate-100 transition-colors list-none [&::-webkit-details-marker]:hidden">
                      <span className="flex items-center gap-2">
                        <MessageCircle className="w-4 h-4 text-slate-400" />
                        議場での質疑・答弁の詳細（{phase.exchanges.length}件）
                      </span>
                      <ChevronDown className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" />
                    </summary>

                    <div className="p-4 border-t border-slate-200 bg-white space-y-3">
                      {phase.exchanges.map((ex, exIdx) => (
                        <div 
                          key={exIdx} 
                          onClick={() => handleViewExchangeContext(ex)} 
                          className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3 hover:bg-slate-100/60 hover:border-slate-300 transition-all cursor-pointer group shadow-2xs"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                            <span className="text-xs font-black text-slate-900">
                              🗣️ {ex.speaker}
                            </span>
                            <span className="text-[11px] font-medium text-slate-500">
                              {ex.meeting_date} {ex.meeting_title}
                            </span>
                          </div>

                          <p className="text-xs text-slate-700 leading-relaxed font-normal">
                            {ex.statement_summary}
                          </p>

                          <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 border-t border-slate-200/70 mt-3">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                openOfficialMinute(ex, cityCode);
                              }}
                              title={getOfficialLinkTooltip(ex, cityCode)}
                              className="inline-flex items-center justify-center text-xs font-semibold text-slate-600 bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 px-3 py-1.5 rounded-xl transition-colors cursor-pointer group shadow-2xs"
                            >
                              <Landmark className="w-3.5 h-3.5 mr-1.5 text-slate-500 group-hover:text-slate-700" />
                              <span>議事録原本を確認</span>
                              <ExternalLink className="w-3 h-3 ml-1.5 text-slate-400 group-hover:text-slate-600" />
                            </button>

                            <button
                              type="button"
                              onClick={() => handleViewExchangeContext(ex)}
                              className="inline-flex items-center justify-center text-xs font-bold text-indigo-600 bg-indigo-50/70 hover:bg-indigo-100/90 border border-indigo-200 hover:border-indigo-300 px-3.5 py-1.5 rounded-xl transition-colors cursor-pointer shadow-2xs"
                            >
                              <MessageCircle className="w-3.5 h-3.5 mr-1.5 text-indigo-600" />
                              <span>会議録・質疑の文脈を見る →</span>
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </details>
                )}

              </div>
            ))}
          </div>
        </section>

        {/* ページ下部戻るボタン */}
        <div className="pt-8 border-t border-slate-200 text-center">
          <button
            onClick={onBack}
            className="inline-flex items-center px-6 py-3 rounded-xl bg-slate-900 text-white font-bold text-xs hover:bg-slate-800 transition-all shadow-md cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            トップページ（マクロ論戦マップ）に戻る
          </button>
        </div>

      </main>
    </div>
  );
}
