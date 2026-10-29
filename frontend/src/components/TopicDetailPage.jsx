import { getCityDataUrl } from '../config/cities';
import React, { useState, useEffect, useMemo } from 'react';
import { 
  ArrowLeft, MessageCircle, Milestone, Calendar, Landmark, ExternalLink, 
  Layers, Clock, Share2, Check, ArrowUpDown, ChevronDown, ChevronUp
} from 'lucide-react';
import { openOfficialMinute, getOfficialLinkTooltip } from '../utils/officialLink';

export default function TopicDetailPage({ topicId, onBack, cityCode = 'kyoto', onViewContext, statements = [] }) {
  const cityName = cityCode === 'nagoya' ? '名古屋市会' : cityCode === 'osaka' ? '大阪市会' : '京都市会';
  const [topic, setTopic] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [copiedShare, setCopiedShare] = useState(false);
  // 💡 デフォルトを「最新順 (desc)」に設定
  const [sortOrder, setSortOrder] = useState('desc'); // 'desc' (最新順) | 'asc' (時系列順)

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });

    const dataUrl = getCityDataUrl(cityCode, 'topicSummaries') || '/data/topic_summaries.json';
    fetch(dataUrl)
      .then((res) => res.json())
      .then((data) => {
        const found = data.find((t) => t.topic_id === topicId);
        setTopic(found || data[0]);
        setTopic(found);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load topic:', err);
        setIsLoading(false);
      });
  }, [topicId, cityCode]);

  // 💡 SpeakerDetailView と完全同一の質疑原本レコード解決ロジック
  

  // 💡 議員詳細・一覧と完全共通の質疑原本レコード解決・モーダル呼び出し
  const handleViewExchangeContext = (ex) => {
    if (!ex) return;
    if (typeof onViewContext !== 'function') {
      console.error('[TopicDetailPage] onViewContext が渡されていません', onViewContext);
      return;
    }
    const allStmts = Array.isArray(statements) ? statements : [];

    // 1. statement_id による原本直接探索
    let target = allStmts.find((s) => s.id === (ex.statement_id || ex.id));

    // 2. meeting_id と sequence_number による探索
    if (!target && ex.meeting_id && ex.sequence_number !== undefined) {
      target = allStmts.find(
        (s) =>
          String(s.meeting_id) === String(ex.meeting_id) &&
          String(s.sequence_number) === String(ex.sequence_number)
      );
    }

    // 3. 原本が見つからない場合のフォールバック（完全なstmt構造を保証）
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

    console.log('[TopicDetailPage] モーダルを開きます:', target);
    onViewContext(target);
  };

  const handleShare = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
      setCopiedShare(true);
      setTimeout(() => setCopiedShare(false), 2500);
    }
  };

  // 並び順に応じたフェーズリストの生成
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

          <div className="flex items-center gap-2">
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
        <section className="bg-white rounded-3xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-5">
          <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
            <Milestone className="w-4 h-4" />
            AI EXECUTIVE SUMMARY / 政策の現在地と争点
          </div>

          <div className="p-4 rounded-2xl bg-indigo-50/60 border border-indigo-100 text-indigo-950 space-y-1">
            <div className="text-[11px] font-black uppercase tracking-wider text-indigo-800">
              【制度設計・検討の現在地】
            </div>
            <p className="text-sm font-bold text-indigo-950 leading-relaxed">
              {topic.current_status}
            </p>
          </div>

          <div className="space-y-2">
            <h2 className="text-xs font-black text-slate-400 uppercase tracking-wider">
              論点の全体像・背景
            </h2>
            <p className="text-sm leading-relaxed text-slate-700 font-medium">
              {topic.lead_summary}
            </p>
          </div>

          {topic.conflict_axes?.length > 0 && (
            <div className="pt-4 border-t border-slate-100 space-y-2.5">
              <div className="text-[11px] font-black text-slate-500 uppercase tracking-wider">
                主な対立軸・残された課題
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {topic.conflict_axes.map((axis, i) => (
                  <div key={i} className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-xs font-medium text-slate-700 flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1 shrink-0" />
                    <span>{axis}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* ③ Policy Timeline（最新順デフォルト ＋ ソート切り替え） */}
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

            {/* 💡 並び順切り替えトグルボタン */}
            <button
              onClick={() => setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc')}
              className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50/80 hover:bg-indigo-100/70 border border-indigo-200/80 px-3 py-1.5 rounded-xl transition-colors cursor-pointer self-start sm:self-auto"
            >
              <ArrowUpDown className="w-3.5 h-3.5" />
              <span>{sortOrder === 'desc' ? '最新から表示中' : '過去から表示中'}</span>
              {sortOrder === 'desc' ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
            </button>
          </div>

          <div className="relative border-l-2 border-indigo-200 ml-4 space-y-10 pl-6 md:pl-8 py-2">
            {sortedPhases.map((phase, idx) => (
              <div key={idx} className="relative space-y-4">
                
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

                {/* 議場での主な発言ログ（肩書なし・原本直リンク） */}
                {phase.exchanges?.length > 0 && (
                  <div className="space-y-3 pt-1">
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider block">
                      議場での主な質疑と答弁
                    </span>

                    {phase.exchanges.map((ex, exIdx) => (
                      <div key={exIdx} onClick={() => handleViewExchangeContext(ex)} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3 hover:bg-slate-100/60 hover:border-slate-300 transition-all cursor-pointer group shadow-2xs">
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
                              <span>{cityCode === 'nagoya' ? '名古屋市会 議事録原本を確認' : cityCode === 'osaka' ? '大阪市会 議事録原本を確認' : '議事録原本を確認'}</span>
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