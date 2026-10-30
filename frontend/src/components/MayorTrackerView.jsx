import React, { useState, useMemo, useEffect } from 'react';
import ReportIssueButton from './ReportIssueButton';
import { getCityConfig } from '../config/cities';
import {
  Landmark, ArrowLeft, ExternalLink, ShieldCheck, BookmarkCheck,
  CheckCircle2, Clock, FileText, Scale, Sparkles, MessageSquare,
  Filter, AlertCircle, ArrowRight, Coins, Calendar, BookCheck
} from 'lucide-react';

function renderKpiValue(val, colorClass = "text-slate-900") {
  if (!val) return null;
  const str = String(val).trim();
  const match = str.match(/^([^\d]*)(\d+(?:\.\d+)?)\s*(.*)$/);
  if (match) {
    const [, prefix, num, suffix] = match;
    return (
      <div className="flex items-baseline justify-center gap-0.5">
        {prefix && <span className="text-xs font-bold text-slate-500 mr-0.5">{prefix}</span>}
        <span className={`text-2xl sm:text-3xl font-black ${colorClass} tracking-tight`}>{num}</span>
        {suffix && <span className="text-xs font-black text-slate-700 ml-0.5">{suffix}</span>}
      </div>
    );
  }
  return (
    <div className={`text-base sm:text-lg font-black ${colorClass} tracking-tight truncate px-1`}>
      {str}
    </div>
  );
}

export default function MayorTrackerView({ data, onBack, onSelectBill, cityCode = 'kyoto' }) {
  // 💡 都市設定の動的取得（SOP v3.0: Zero Component Modification）
  const cityConfig = useMemo(() => {
    try {
      return getCityConfig ? getCityConfig(cityCode) : {};
    } catch {
      return {};
    }
  }, [cityCode]);

  // 💡 市長基本情報の完全動的解決
  const mayorInfo = useMemo(() => {
    const raw = (data && !Array.isArray(data) && data.mayor_info) ? data.mayor_info : {};
    const defaultCityName = data?.city_name || raw.city_label || cityConfig?.cityName || `${cityCode}市`;
    return {
      name: raw.name || data?.mayor_name || cityConfig?.mayorName || '市長',
      title: raw.title || data?.mayor_title || cityConfig?.mayorTitle || '市長',
      city_label: raw.city_label || data?.city_name || defaultCityName,
      term: raw.term || data?.term || cityConfig?.term || '',
      party: raw.party || data?.party || cityConfig?.party || '',
      profile_image: raw.profile_image || data?.profile_image || `/councilors/${cityCode}/mayor.jpg`,
      fallback_image: raw.fallback_image || null,
      bulletin_pdf: raw.bulletin_pdf || raw.bulletin_url || data?.bulletin_pdf || cityConfig?.bulletinPdf || null,
      bulletin_label: raw.bulletin_label || data?.bulletin_label || cityConfig?.bulletinLabel || '市長マニフェスト原本',
      strategy_main_pdf: raw.strategy_main_pdf || raw.profile_url || data?.strategy_main_pdf || cityConfig?.strategyPdf || null,
      strategy_main_label: raw.strategy_main_label || data?.strategy_main_label || cityConfig?.strategyLabel || '市公式 総合計画'
    };
  }, [data, cityCode, cityConfig]);

  // 💡 公約リスト（配列直接渡し / dict.pledges 両対応）
  const pledges = useMemo(() => {
    if (Array.isArray(data)) return data;
    if (data?.pledges && Array.isArray(data.pledges)) return data.pledges;
    return [];
  }, [data]);

  // 💡 KPI集計カードの動的解決
  const kpis = useMemo(() => {
    if (data && !Array.isArray(data) && Array.isArray(data.kpis) && data.kpis.length > 0) {
      return data.kpis;
    }
    const stats = (data && !Array.isArray(data) && data.summary_stats) ? data.summary_stats : {};
    const total = stats.total_pledges || stats.total || pledges.length || 0;
    const progressCount = stats.progress_pledges || pledges.filter(p => (p.stage_level ?? p.progress_stage ?? p.current_stage ?? 2) >= 3).length;
    const verifiedCount = pledges.filter(p => p.election_promise?.source_url || p.election_promise?.bulletin_url || p.manifesto_url || p.official_plan?.doc_url || p.official_plan_url).length;
    const verifiedRate = total > 0 ? Math.round((verifiedCount / total) * 100) : 100;

    return [
      {
        label: "重点公約追跡",
        value: `${total}件`,
        subtext: "選挙公約・原本資料照合",
        badge: "全件追跡"
      },
      {
        label: "予算化・推進中",
        value: `${progressCount}件`,
        subtext: "当初予算・計画連動",
        badge: "推進中"
      },
      {
        label: stats.budget_total ? "関連予算総額" : "一次資料照合率",
        value: stats.budget_total ? `¥${stats.budget_total}` : `${verifiedRate}%`,
        subtext: stats.budget_total ? "千円単位で事業紐付け" : "公報・計画書原本直結",
        badge: "透明性担保"
      }
    ];
  }, [data, pledges]);

  // 💡 政策ライフサイクル解説文の動的解決
  const lifecycle = useMemo(() => {
    if (data && !Array.isArray(data) && data.lifecycle_definition?.title) {
      return data.lifecycle_definition;
    }
    const cityName = mayorInfo.city_label || '市政';
    return {
      title: "公文書・議決・予算書に基づく政策ライフサイクル検証",
      description: `選挙公報の看板公約原本が「${cityName}総合計画」に反映され、どれだけの予算（主要事業説明書）が投じられ、市会での「条例提出・議決」を経て「執行」に至ったかを一次資料原本で客観追跡しています。`
    };
  }, [data, mayorInfo.city_label]);

  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedStageLevel, setSelectedStageLevel] = useState(0);

  const [imgSrc, setImgSrc] = useState(mayorInfo.profile_image);
  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    setImgSrc(mayorInfo.profile_image);
    setImgError(false);
  }, [mayorInfo.profile_image]);

  const categories = useMemo(() => {
    return [...new Set(pledges.map(p => p.category).filter(Boolean))];
  }, [pledges]);

  const filteredPledges = useMemo(() => {
    return pledges.filter(p => {
      const lvl = p.stage_level ?? p.progress_stage ?? p.current_stage ?? 2;
      if (selectedCategory && p.category !== selectedCategory) return false;
      if (selectedStageLevel > 0 && lvl !== selectedStageLevel) return false;
      return true;
    });
  }, [pledges, selectedCategory, selectedStageLevel]);

  const handleImageError = () => {
    if (!imgError) {
      setImgError(true);
      if (mayorInfo.fallback_image) setImgSrc(mayorInfo.fallback_image);
      else setImgSrc('');
    }
  };

  return (
    <main className="max-w-6xl mx-auto py-8 px-4 sm:px-6 animate-in fade-in duration-300 w-full space-y-8">
      {/* ナビゲーション */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <button onClick={onBack} className="inline-flex items-center text-xs font-bold text-slate-500 hover:text-indigo-600 transition-colors bg-white px-3 py-2 rounded-lg border border-slate-200 shadow-xs cursor-pointer">
          <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />ポータルに戻る
        </button>
        <div className="flex items-center gap-2 flex-wrap">
          {mayorInfo.bulletin_pdf && (
            <div className="inline-flex items-center gap-1">
              <a href={mayorInfo.bulletin_pdf} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-indigo-600 hover:bg-indigo-50 font-bold text-xs transition-colors shadow-2xs">
                <Landmark className="w-3.5 h-3.5 text-indigo-500" />
                <span>{mayorInfo.bulletin_label || '公約集'}</span>
                <ExternalLink className="w-3 h-3 opacity-60" />
              </a>
              <ReportIssueButton
                targetUrl={mayorInfo.bulletin_pdf}
                speaker={mayorInfo.name}
                meetingDate={mayorInfo.term || ''}
                targetId="mayor_bulletin_pdf"
                municipality={mayorInfo.city_label}
              />
            </div>
          )}
          {mayorInfo.strategy_main_pdf && (
            <div className="hidden sm:inline-flex items-center gap-1">
              <a href={mayorInfo.strategy_main_pdf} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 font-bold text-xs transition-colors shadow-2xs">
                <FileText className="w-3.5 h-3.5 text-slate-500" />
                <span>{mayorInfo.strategy_main_label || '市公式 総合計画'}</span>
                <ExternalLink className="w-3 h-3 opacity-60" />
              </a>
              <ReportIssueButton
                targetUrl={mayorInfo.strategy_main_pdf}
                speaker={mayorInfo.name}
                meetingDate=""
                targetId="mayor_strategy_main_pdf"
                municipality={mayorInfo.city_label}
              />
            </div>
          )}
        </div>
      </div>

      {/* ヘッダー */}
      <header className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-6">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6 pb-6 border-b border-slate-100">
          <div className="flex items-start gap-4 sm:gap-5">
            <div className="w-20 h-24 rounded-2xl overflow-hidden bg-slate-100 border border-slate-200 shrink-0 shadow-xs flex items-center justify-center relative">
              {!imgError && imgSrc ? (
                <img src={imgSrc} alt={mayorInfo.name} className="w-full h-full object-cover object-top" onError={handleImageError} />
              ) : (
                <div className="text-center p-2">
                  <span className="text-[10px] font-bold text-slate-400 block">{mayorInfo.city_label}</span>
                  <span className="text-xs font-black text-slate-600">{mayorInfo.name}</span>
                </div>
              )}
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2.5 flex-wrap">
                <span className="px-2.5 py-0.5 text-xs font-black rounded-md bg-indigo-600 text-white shadow-2xs">
                  {mayorInfo.title}
                </span>
                {mayorInfo.party && (
                  <span className="px-2.5 py-0.5 text-xs font-bold rounded-md bg-slate-100 text-slate-700 border border-slate-200/70">
                    {mayorInfo.party}
                  </span>
                )}
                <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">{mayorInfo.name}</h1>
              </div>
              <div className="flex items-center gap-2 text-xs font-bold text-slate-500 flex-wrap">
                <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 px-2.5 py-1 rounded-md border border-slate-200/70">
                  <Calendar className="w-3 h-3 text-slate-400" />
                  {mayorInfo.term}
                </span>
              </div>
            </div>
          </div>

          {/* KPIカード表示 */}
          {kpis && kpis.length > 0 && (
            <div className="w-full lg:w-auto grid grid-cols-1 sm:grid-cols-3 gap-2.5 sm:gap-3 bg-slate-50/80 p-3 sm:p-4 rounded-2xl border border-slate-200/80">
              {kpis.map((kpi, idx) => (
                <div key={idx} className="bg-white p-3 sm:p-3.5 rounded-xl border border-slate-200/60 shadow-2xs flex flex-col justify-between text-center min-w-[130px] sm:min-w-[145px]">
                  <div className="flex items-center justify-center gap-1">
                    <span className={`text-[11px] font-black block tracking-tight whitespace-nowrap ${idx===0 ? 'text-indigo-700' : idx===1 ? 'text-emerald-700' : 'text-slate-600'}`}>
                      {kpi.label}
                    </span>
                    {kpi.badge && (
                      <span className="text-[9px] font-extrabold bg-emerald-100 text-emerald-800 px-1 py-0.2 rounded shrink-0">
                        {kpi.badge}
                      </span>
                    )}
                  </div>
                  <div className="my-1 min-h-[32px] flex items-center justify-center">
                    {renderKpiValue(kpi.value, idx===0 ? 'text-slate-900' : idx===1 ? 'text-emerald-600' : 'text-slate-800')}
                  </div>
                  <span className={`text-[10px] font-bold block whitespace-nowrap leading-tight mt-0.5 ${idx===1 ? 'text-emerald-600' : 'text-slate-400'}`}>
                    {kpi.subtext}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-indigo-50/40 p-4 sm:p-4.5 rounded-2xl border border-indigo-100 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h2 className="text-xs font-black text-indigo-950">{lifecycle.title}</h2>
            <p className="text-[11px] text-slate-600 leading-relaxed font-medium">{lifecycle.description}</p>
          </div>
        </div>
      </header>

      {/* 絞り込みバー */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs font-bold text-slate-400 mr-1 flex items-center gap-1"><Filter className="w-3.5 h-3.5" />進捗:</span>
          {[{ level: 0, label: 'すべて' }, { level: 5, label: '成立・執行' }, { level: 4, label: '条例提出・審議' }, { level: 3, label: '予算計上・実証中' }, { level: 2, label: '市公式計画化' }].map(s => (
            <button key={s.level} onClick={() => setSelectedStageLevel(s.level)} className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${selectedStageLevel === s.level ? 'bg-indigo-600 text-white shadow-xs' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
              {s.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto">
          <span className="text-xs font-bold text-slate-400 shrink-0">分野:</span>
          <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} className="w-full md:w-48 bg-slate-100 border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-bold text-slate-700 outline-none cursor-pointer">
            <option value="">全分野 ({pledges.length})</option>
            {categories.map(cat => <option key={cat} value={cat}>{cat}</option>)}
          </select>
        </div>
      </div>

      {/* 公約カード一覧 */}
      <div className="space-y-8">
        {filteredPledges.map((pledge) => {
          // 防御的プロパティ解決（新旧・フラット型両対応）
          const plan = typeof pledge.official_plan === 'object' ? pledge.official_plan : (pledge.official_plan ? { plan_name: pledge.official_plan, doc_url: pledge.official_plan_url, summary: pledge.official_plan } : null);
          const budgets = Array.isArray(pledge.budget_records) ? pledge.budget_records : (pledge.budget_project ? [{ project_name: pledge.budget_project, doc_url: pledge.budget_url, fiscal_year: '令和8年度', amount_display: '予算計上済' }] : []);
          const bill = pledge.legislative_bill;
          const milestone = pledge.milestone || (pledge.progress_note ? { title: pledge.progress_note, date: pledge.last_updated } : null);
          const quoteText = pledge.election_promise?.quote || pledge.manifesto_quote || pledge.title || '';
          const quoteDocType = pledge.election_promise?.document_type || "公式公約・原本資料";
          const quoteSourceUrl = pledge.election_promise?.source_url || pledge.manifesto_url;
          const quoteBulletinUrl = pledge.election_promise?.bulletin_url || pledge.manifesto_url;

          const currentLvl = pledge.stage_level ?? pledge.progress_stage ?? pledge.current_stage ?? 2;
          
          const dynamicStages = [
            { level: 1, label: '1.公約表明' },
            { level: 2, label: '2.市公式計画化' },
            { level: 3, label: '3.予算措置' },
            { level: 4, label: bill ? '4.条例/議案提出' : '4.要綱策定・契約' },
            { level: 5, label: '5.成立・執行' }
          ];

          return (
            <article key={pledge.id} className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="bg-slate-50/80 px-6 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black bg-indigo-50 text-indigo-700 border border-indigo-200">{pledge.category}</span>
                  <h3 className="text-base sm:text-lg font-black text-slate-900 leading-snug">{pledge.headline || pledge.title}</h3>
                </div>
                <div className="shrink-0 flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-xs font-black inline-flex items-center gap-1.5 ${currentLvl >= 4 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-indigo-50 text-indigo-700 border border-indigo-200'}`}>
                    {currentLvl >= 5 ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <Clock className="w-3.5 h-3.5 text-indigo-600" />}
                    進捗: {pledge.stage_label || `${currentLvl}.段階`}
                  </span>
                </div>
              </div>

              <div className="px-6 py-4 bg-slate-50/40 border-b border-slate-100">
                <div className="grid grid-cols-5 gap-1 sm:gap-2">
                  {dynamicStages.map((st) => {
                    const isPassed = currentLvl >= st.level;
                    const isCurrent = currentLvl === st.level;
                    return (
                      <div key={st.level} className="text-center space-y-1">
                        <div className={`h-1.5 rounded-full transition-all ${isPassed ? 'bg-indigo-600' : 'bg-slate-200'}`} />
                        <span className={`text-[10px] font-black block truncate ${isCurrent ? 'text-indigo-600 font-extrabold' : isPassed ? 'text-slate-700' : 'text-slate-400'}`}>{st.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">
                <div className="lg:col-span-4 p-6 bg-indigo-50/15 space-y-4 flex flex-col justify-between">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-black text-indigo-950 flex items-center gap-1.5 uppercase tracking-wider">
                        <BookmarkCheck className="w-4 h-4 text-indigo-600" />一次資料原文引用
                      </span>
                      <span className="text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                        {quoteDocType}
                      </span>
                    </div>
                    <div className="bg-white p-4 rounded-2xl border border-indigo-100/80 shadow-2xs space-y-2">
                      {pledge.election_promise?.source_name && (
                        <div className="text-[10px] font-bold text-indigo-600 flex items-center gap-1 border-b border-indigo-50 pb-1">
                          <span>出典:</span>
                          {quoteSourceUrl ? (
                            <a 
                              href={quoteSourceUrl} 
                              target="_blank" 
                              rel="noopener noreferrer" 
                              className="font-mono hover:underline hover:text-indigo-800 inline-flex items-center gap-0.5 transition-colors"
                            >
                              {pledge.election_promise.source_name}
                              <ExternalLink className="w-2.5 h-2.5 opacity-70" />
                            </a>
                          ) : (
                            <span className="font-mono">{pledge.election_promise.source_name}</span>
                          )}
                        </div>
                      )}
                      <blockquote className="text-xs text-slate-800 font-medium leading-relaxed border-l-2 border-indigo-500 pl-3">
                        “{quoteText}”
                      </blockquote>
                      {pledge.election_promise?.note && (
                        <p className="text-[10px] text-slate-400 leading-normal pt-1 border-t border-slate-50">
                          {pledge.election_promise.note}
                        </p>
                      )}
                    </div>
                  </div>
                  {quoteBulletinUrl && (
                    <div className="pt-2 flex flex-wrap items-center gap-2">
                      <a
                        href={quoteBulletinUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[11px] font-black text-indigo-600 hover:text-indigo-800 hover:underline bg-white px-2.5 py-1 rounded-lg border border-indigo-200 shadow-2xs transition-colors"
                      >
                        <Landmark className="w-3.5 h-3.5" />
                        <span>公約原本PDF</span>
                        <ExternalLink className="w-3 h-3 opacity-60 ml-0.5" />
                      </a>
                      <ReportIssueButton
                        targetUrl={quoteBulletinUrl}
                        speaker={mayorInfo.name}
                        meetingDate={pledge.title || pledge.headline || ""}
                        targetId={`pledge_${pledge.id || pledge.pledge_id}`}
                        municipality={mayorInfo.city_label}
                      />
                    </div>
                  )}
                </div>

                <div className="lg:col-span-8 p-6 space-y-6 bg-white">
                  {/* ① 計画 */}
                  {plan && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-indigo-950 flex items-center gap-1.5"><BookCheck className="w-3.5 h-3.5 text-indigo-600" />市公式計画・方針に明記</span>
                        <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">市公式計画化</span>
                      </div>
                      <div className="p-4 rounded-2xl bg-indigo-50/25 border border-indigo-100/80 space-y-2">
                        <div className="flex items-center justify-between flex-wrap gap-1 text-[10px] font-bold text-slate-500">
                          {plan.doc_url ? (
                            <div className="inline-flex items-center gap-1">
                              <a href={plan.doc_url} target="_blank" rel="noopener noreferrer" className="font-mono bg-white text-indigo-900 px-2 py-0.5 rounded border border-indigo-200 font-extrabold hover:bg-indigo-100 hover:underline inline-flex items-center gap-1 transition-colors">
                                <span>{plan.plan_name}</span><ExternalLink className="w-3 h-3 opacity-60" />
                              </a>
                              <ReportIssueButton
                                targetUrl={plan.doc_url}
                                speaker={mayorInfo.name}
                                meetingDate={plan.date || ''}
                                targetId={plan.plan_name || 'plan_doc'}
                                municipality={mayorInfo.city_label}
                              />
                            </div>
                          ) : (
                            <span className="font-mono bg-white text-indigo-900 px-2 py-0.5 rounded border border-indigo-100 font-extrabold">{plan.plan_name}</span>
                          )}
                          {plan.date && <span className="text-slate-400">{plan.date} 策定</span>}
                        </div>
                        <p className="text-xs text-slate-800 leading-relaxed font-medium mt-1">{plan.summary}</p>
                      </div>
                    </div>
                  )}

                  {/* ② 予算 */}
                  {budgets.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-slate-700 flex items-center gap-1.5"><Coins className="w-3.5 h-3.5 text-emerald-600" />予算措置・計上実績</span>
                        <span className="text-[10px] text-slate-400 font-bold">計 {budgets.length} 事業</span>
                      </div>
                      <div className="space-y-3">
                        {budgets.map((b, bIdx) => (
                          <div key={bIdx} className="p-4 rounded-2xl bg-emerald-50/20 border border-emerald-100 space-y-2.5">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] font-mono font-bold bg-white text-emerald-800 px-2 py-0.5 rounded border border-emerald-200 shrink-0">{b.fiscal_year}</span>
                                <span className="text-xs font-black text-slate-800 leading-snug">{b.project_name}</span>
                              </div>
                              <div className="text-right shrink-0">
                                <span className="text-base sm:text-lg font-black text-emerald-700 font-mono">{b.amount_display}</span>
                              </div>
                            </div>
                            {b.funding_sources && b.funding_sources.length > 0 && (
                              <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-emerald-100/60">
                                <span className="text-[10px] font-bold text-slate-400">財源:</span>
                                {b.funding_sources.map((fs, fsIdx) => (
                                  <span key={fsIdx} className={`text-[10px] font-bold px-2 py-0.5 rounded border ${fs.color || 'bg-slate-50 text-slate-600'}`}>{fs.label}: {fs.amount}</span>
                                ))}
                              </div>
                            )}
                            {b.doc_url && (
                              <div className="pt-2 mt-1.5 border-t border-emerald-100/60 flex items-center justify-end gap-1 text-[10.5px]">
                                <span className="text-slate-400 font-medium shrink-0 mt-[1px]">出典:</span>
                                <a href={b.doc_url} target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-900 font-bold inline-flex items-start gap-1 hover:underline text-right group">
                                  <span className="leading-tight group-hover:underline">{b.doc_source}</span>
                                  <ExternalLink className="w-3 h-3 opacity-60 shrink-0 mt-[1px]" />
                                </a>
                                <ReportIssueButton
                                  targetUrl={b.doc_url}
                                  speaker={mayorInfo.name}
                                  meetingDate={b.fiscal_year || ''}
                                  targetId={b.item_name || b.doc_source || 'budget_doc'}
                                  municipality={mayorInfo.city_label}
                                />
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* ③ 条例 */}
                  {bill && (
                    <div className="space-y-2">
                      <span className="text-xs font-black text-slate-700 flex items-center gap-1.5"><Scale className="w-3.5 h-3.5 text-indigo-600" />提出条例案と市会審議結果</span>
                      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <span className="text-[10px] font-mono text-slate-500 font-black">{bill.session_name} ({bill.bill_number})</span>
                          <span className={`px-2 py-0.5 rounded text-[11px] font-black border ${bill.result === '可決' ? 'bg-emerald-100 text-emerald-800 border-emerald-200' : 'bg-amber-100 text-amber-800 border-amber-200'}`}>結果: {bill.result}</span>
                        </div>
                        {bill.doc_url ? (
                          <div className="flex items-start justify-between gap-1.5">
                            <a href={bill.doc_url} target="_blank" rel="noopener noreferrer" className="text-xs font-bold text-indigo-700 hover:text-indigo-900 hover:underline leading-snug inline-flex items-start gap-1.5 flex-1">
                              <span>{bill.bill_title}</span>
                              <ExternalLink className="w-3.5 h-3.5 opacity-60 shrink-0 mt-0.5" />
                            </a>
                            <ReportIssueButton
                              targetUrl={bill.doc_url}
                              speaker={mayorInfo.name}
                              meetingDate={bill.session_name || ''}
                              targetId={bill.bill_number || bill.bill_title || 'bill_doc'}
                              municipality={mayorInfo.city_label}
                            />
                          </div>
                        ) : (
                          <h4 className="text-xs font-bold text-slate-900 leading-snug">{bill.bill_title}</h4>
                        )}
                        {bill.party_votes && (
                          <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between flex-wrap gap-2">
                            <div className="flex items-center gap-1.5 flex-wrap text-xs">
                              <span className="text-[10px] font-bold text-slate-400">会派賛否:</span>
                              {Object.entries(bill.party_votes).map(([party, vote]) => (
                                <span key={party} className={`px-2 py-0.5 rounded text-[10px] font-black inline-flex items-center gap-1 ${String(vote).includes('賛成') ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'}`}>
                                  <span>{party}:</span><span>{vote}</span>
                                </span>
                              ))}
                            </div>
                            {onSelectBill && (
                              <button onClick={() => onSelectBill(bill)} className="px-2.5 py-1 text-[11px] font-bold text-indigo-600 hover:text-indigo-800 bg-white hover:bg-indigo-50 rounded-lg border border-indigo-200 transition-all flex items-center gap-1 shadow-2xs cursor-pointer">
                                <span>全議員の採決ログ詳細</span><ArrowRight className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* ④ マイルストーン */}
                  {milestone && (
                    <div className="space-y-1.5 pl-3 border-l-2 border-indigo-200">
                      <span className="text-[10px] font-black text-slate-400 block uppercase">主な政策マイルストーン</span>
                      <div className="flex items-start gap-2 text-xs">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-[1px]" />
                        {milestone.date && <span className="font-mono text-slate-500 font-bold shrink-0 mt-[2px]">{milestone.date}</span>}
                        {milestone.evidence_url ? (
                          <div className="inline-flex items-center gap-1">
                            <a href={milestone.evidence_url} target="_blank" rel="noopener noreferrer" className="font-bold text-indigo-700 hover:text-indigo-900 hover:underline inline-flex items-start gap-1">
                              <span className="leading-tight">{milestone.title}</span>
                              <ExternalLink className="w-3 h-3 opacity-60 shrink-0 mt-[2px]" />
                            </a>
                            <ReportIssueButton
                              targetUrl={milestone.evidence_url}
                              speaker={mayorInfo.name}
                              meetingDate={milestone.date || ''}
                              targetId={milestone.title || 'milestone_evidence'}
                              municipality={mayorInfo.city_label}
                            />
                          </div>
                        ) : (
                          <span className="font-bold text-slate-800 leading-tight">{milestone.title}</span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* ⑤ 質疑ログ */}
                  {pledge.debate_statements && pledge.debate_statements.length > 0 && (
                    <div className="space-y-2 pt-3 border-t border-slate-100">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-slate-700 flex items-center gap-1.5"><MessageSquare className="w-3.5 h-3.5 text-indigo-600" />市会での質疑・市長答弁ログ</span>
                        <span className="text-[10px] text-slate-400 font-bold">{pledge.debate_statements.length} 件</span>
                      </div>
                      <div className="space-y-2">
                        {pledge.debate_statements.map((stmt, sIdx) => (
                          <div key={sIdx} className={`p-3 rounded-xl border text-xs space-y-1.5 ${stmt.role === '市長答弁' || stmt.role === '首長・理事者答弁' ? 'bg-indigo-50/40 border-indigo-100/90 text-indigo-950' : 'bg-slate-50/80 border-slate-200/80 text-slate-800'}`}>
                            <div className="flex items-center justify-between flex-wrap gap-1">
                              <div className="flex items-center gap-1.5 font-bold">
                                <span className={`text-[10px] px-1.5 py-0.5 rounded font-black ${stmt.role.includes('答弁') ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700'}`}>{stmt.role}</span>
                                <span>{stmt.speaker}</span>
                              </div>
                              <span className="text-[10px] text-slate-400 font-mono">{stmt.session_name} ({stmt.date})</span>
                            </div>
                            <blockquote className="text-[11px] leading-relaxed font-medium text-slate-600 pl-2 border-l-2 border-indigo-300">“{stmt.quote_summary}”</blockquote>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </article>
          );
        })}
        {filteredPledges.length === 0 && (
          <div className="text-center py-16 bg-white rounded-3xl border border-dashed border-slate-200">
            <AlertCircle className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-slate-500 font-bold text-sm">該当する条件の公約項目がありません。</p>
          </div>
        )}
      </div>
    </main>
  );
}
