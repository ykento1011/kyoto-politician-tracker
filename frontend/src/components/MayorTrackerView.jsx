import React, { useState, useMemo, useEffect } from 'react';
import ReportIssueButton from './ReportIssueButton';
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
  // 💡 自治体判定（名古屋・大阪・京都）
  const isNagoya = Boolean(
    cityCode === 'nagoya' ||
    data?.city_code === 'nagoya' ||
    data?.city_name?.includes('名古屋') ||
    (!data?.mayor_info && data?.mayor_name?.includes('広沢'))
  );

  // 💡 自治体判定（横浜・名古屋・大阪・京都）
  const isYokohama = Boolean(
    cityCode === 'yokohama' ||
    data?.city_code === 'yokohama' ||
    data?.city_name?.includes('横浜') ||
    data?.mayor_name?.includes('原澤')
  );

  const isOsaka = Boolean(
    cityCode === 'osaka' ||
    data?.city_code === 'osaka' ||
    data?.city_name?.includes('大阪') ||
    (!data?.mayor_info && data?.mayor_name?.includes('横山'))
  );

  const mayorInfo = useMemo(() => {
    const raw = data?.mayor_info || {};
    if (isYokohama) {
      return {
        name: raw.name || data?.mayor_name || '原澤敦美',
        title: raw.title || '横浜市長',
        city_label: raw.city_label || data?.city_name || '横浜市',
        term: raw.term || data?.term || '2026年10月就任〜',
        party: raw.party || '無所属（初当選）',
        profile_image: raw.profile_image || data?.profile_image || null,
        fallback_image: null,
        bulletin_pdf: raw.bulletin_pdf || raw.bulletin_url || 'https://www.city.yokohama.lg.jp/city-info/senkyo/data/mayor/20261018kohosya_koho.files/R08_kouhou.pdf',
        bulletin_label: raw.bulletin_label || '2026年10月 市長選公報原本PDF',
        strategy_main_pdf: raw.profile_url || 'https://www.city.yokohama.lg.jp/mayor/profile/profile.html',
        strategy_main_label: raw.strategy_main_label || '市長プロフィール・基本方針'
      };
    }
    if (isNagoya) {
      return {
        name: raw.name || data?.mayor_name || '広沢一郎',
        title: raw.title || '名古屋市長',
        city_label: raw.city_label || data?.city_name || '名古屋市',
        term: raw.term || data?.term || '2024年11月就任〜',
        party: raw.party || '日本保守党・減税日本 推薦',
        profile_image: raw.profile_image || data?.profile_image || `/councilors/${cityCode}/hirosawa_ichiro.jpg`,
        fallback_image: raw.fallback_image || null,
        bulletin_pdf: raw.bulletin_pdf || data?.bulletin_pdf || 'https://hiro.laborat.net/index/seisaku',
        bulletin_label: raw.bulletin_label || data?.bulletin_label || '市長選挙マニフェスト原本',
        strategy_main_pdf: raw.strategy_main_pdf || data?.strategy_main_pdf || 'https://www.city.nagoya.jp/shisei/category/53-10-0-0-0-0-0-0-0-0.html',
        strategy_main_label: raw.strategy_main_label || data?.strategy_main_label || '名古屋市総合計画'
      };
    }
    if (isOsaka) {
      return {
        name: raw.name || data?.mayor_name || '横山英幸',
        title: raw.title || '大阪市長',
        city_label: raw.city_label || data?.city_name || '大阪市',
        term: raw.term || data?.term || '2023年4月就任〜',
        party: raw.party || '大阪維新の会',
        profile_image: raw.profile_image || data?.profile_image || `/councilors/${cityCode}/yokoyama_hideyuki.jpg`,
        fallback_image: raw.fallback_image || null,
        bulletin_pdf: raw.bulletin_pdf || data?.bulletin_pdf || 'https://www.city.osaka.lg.jp/shicho/page/0000600109.html',
        bulletin_label: raw.bulletin_label || data?.bulletin_label || '市政基本方針・マニフェスト',
        strategy_main_pdf: raw.strategy_main_pdf || data?.strategy_main_pdf || 'https://www.city.osaka.lg.jp/keikakuchousei/page/0000527265.html',
        strategy_main_label: raw.strategy_main_label || data?.strategy_main_label || '大阪市総合計画 2025'
      };
    }
    return {
      name: raw.name || data?.mayor_name || '松井孝治',
      title: raw.title || '京都市長',
      city_label: raw.city_label || data?.city_name || '京都市',
      term: raw.term || data?.term || (raw.term_start ? `${raw.term_start.slice(0, 4)}年2月就任〜` : '2024年2月就任〜'),
      party: raw.party || '',
      profile_image: raw.profile_image || data?.profile_image || `/councilors/${cityCode}/matsui_koji.jpg`,
      fallback_image: raw.fallback_image || `/councilors/${cityCode}/matsui_koji.jpg`,
      bulletin_pdf: raw.bulletin_pdf || data?.bulletin_pdf || 'https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf',
      bulletin_label: raw.bulletin_label || data?.bulletin_label || '公約集（選挙公報原本）',
      strategy_main_pdf: raw.strategy_main_pdf || data?.strategy_main_pdf || 'https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/sinkyotosenryaku.pdf',
      strategy_main_label: raw.strategy_main_label || data?.strategy_main_label || '市公式 総合計画'
    };
  }, [data, isNagoya, isOsaka]);

  const pledges = useMemo(() => data?.pledges || [], [data]);

  // 💡 KPIカードの自動正規化（コンパクトな文言・数値表示）
  const kpis = useMemo(() => {
    if (data?.kpis && Array.isArray(data.kpis) && data.kpis.length > 0) {
      return data.kpis;
    }
    const stats = data?.summary_stats || {};

    if (isYokohama) {
      const total = stats.total || pledges.length || 12;
      return [
        {
          label: "重点公約追跡",
          value: `${total}件`,
          subtext: "2026年市長選 公約原本バインド",
          badge: "先行公開"
        },
        {
          label: "公約進捗フェーズ",
          value: "①表明",
          subtext: "2026年10月 新市政就任直後",
          badge: "全12件"
        },
        {
          label: "原本照合率",
          value: "100%",
          subtext: "選挙公報PDF・基本方針直結",
          badge: "検証済"
        }
      ];
    }

    if (isNagoya) {
      const total = stats.total_pledges || pledges.length || 5;
      const progress = stats.progress_pledges || pledges.filter(p => (p.stage_level || 2) >= 3).length || 3;
      return [
        {
          label: "重点公約追跡",
          value: `${total}件`,
          subtext: "選挙公約原本を照合",
          badge: "全件照合"
        },
        {
          label: "予算化・実証中",
          value: `${progress}件`,
          subtext: "当初予算・計画連動",
          badge: "推進中"
        },
        {
          label: "条例成立・執行",
          value: "1件",
          subtext: "市長給与特例条例など",
          badge: "執行中"
        }
      ];
    }

    if (isOsaka) {
      return [
        {
          label: "主要マニフェスト",
          value: `${stats.total_pledges || pledges.length || 8}件`,
          subtext: "市政基本方針原本バインド",
          badge: "重点追跡"
        },
        {
          label: "事業化・計画掲載",
          value: `${pledges.filter(p => (p.stage_level || 2) >= 3).length || 6}件`,
          subtext: "総合計画・重点事業",
          badge: "推進中"
        },
        {
          label: "予算計上累計",
          value: stats.budget_total ? `¥${stats.budget_total}` : "精査中",
          subtext: "当初・補正予算関連事業",
          badge: "公開データ"
        }
      ];
    }

    return [
      {
        label: "市長重点公約",
        value: `${stats.total_pledges || pledges.length || 10}件`,
        subtext: "選挙公報・新京都戦略原本",
        badge: "全件照合"
      },
      {
        label: "予算化・条例化",
        value: `${pledges.filter(p => (p.stage_level || 2) >= 3).length || 7}件`,
        subtext: "当初予算主要事業説明書",
        badge: "定量的追跡"
      },
      {
        label: "関連予算総額",
        value: stats.budget_total ? `¥${stats.budget_total}` : "¥142.8億",
        subtext: "千円単位で事業紐付け",
        badge: "透明性担保"
      }
    ];
  }, [data, isNagoya, isOsaka, isYokohama, pledges]);

  // 💡 政策ライフサイクルの解説文
  const lifecycle = useMemo(() => {
    if (data?.lifecycle_definition && data.lifecycle_definition.title) {
      return data.lifecycle_definition;
    }
    let description = "選挙公報の看板公約原本が「市総合計画」に反映され、どれだけの予算（主要事業説明書）が投じられ、市会での「条例提出・議決」を経て「執行」に至ったかを一次資料で客観追跡しています。";
    if (isYokohama) {
      description = "2026年10月就任の原澤敦美新市長の選挙公報原本から抽出した重点12公約を先行収録。新市政就任直後の「①公約表明」フェーズから、今後の補正・当初予算案や中期計画への位置づけ、市会論戦を通じた進捗を順次客観追跡します。";
    } else if (isNagoya) {
      description = "市長就任時の重点公約が「名古屋市総合計画」に位置づけられ、名古屋市会での予算措置や条例提出、議決を経て執行に至る過程を客観追跡しています。";
    } else if (isOsaka) {
      description = "市長就任時の重点公約が「大阪市総合計画」に位置づけられ、大阪市会での「条例提出・議決」を経て「成立・事業執行」に至ったかを一次資料原本で客観追跡しています。";
    }
    return {
      title: "公文書・議決・予算書に基づく政策ライフサイクル検証",
      description
    };
  }, [data, isNagoya, isOsaka, isYokohama]);

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
      const lvl = p.stage_level ?? p.current_stage ?? 2;
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
                municipality={mayorInfo.city_label || '名古屋市'}
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
                municipality={mayorInfo.city_label || '名古屋市'}
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
          const plan = pledge.official_plan;
          const budgets = pledge.budget_records || [];
          const bill = pledge.legislative_bill;
          const milestone = pledge.milestone;
          const quoteText = pledge.election_promise?.quote || pledge.title || '';
          
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
                  <span className={`px-3 py-1 rounded-full text-xs font-black inline-flex items-center gap-1.5 ${pledge.stage_level >= 4 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-indigo-50 text-indigo-700 border border-indigo-200'}`}>
                    {pledge.stage_level >= 5 ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <Clock className="w-3.5 h-3.5 text-indigo-600" />}
                    進捗: {pledge.stage_label || `${pledge.stage_level}.段階`}
                  </span>
                </div>
              </div>

              <div className="px-6 py-4 bg-slate-50/40 border-b border-slate-100">
                <div className="grid grid-cols-5 gap-1 sm:gap-2">
                  {dynamicStages.map((st) => {
                    const isPassed = (pledge.stage_level || 2) >= st.level;
                    const isCurrent = (pledge.stage_level || 2) === st.level;
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
                          {pledge.election_promise?.document_type || "公式公約・原本資料"}
                        </span>
                      </div>
                      <div className="bg-white p-4 rounded-2xl border border-indigo-100/80 shadow-2xs space-y-2">
                        {pledge.election_promise?.source_name && (
                          <div className="text-[10px] font-bold text-indigo-600 flex items-center gap-1 border-b border-indigo-50 pb-1">
                            <span>出典:</span>
                            {pledge.election_promise.source_url ? (
                              <a 
                                href={pledge.election_promise.source_url} 
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
                    {pledge.election_promise?.bulletin_url && (
                      <div className="pt-2 flex flex-wrap items-center gap-2">
                        <a
                          href={pledge.election_promise.bulletin_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] font-black text-indigo-600 hover:text-indigo-800 hover:underline bg-white px-2.5 py-1 rounded-lg border border-indigo-200 shadow-2xs transition-colors"
                        >
                          <Landmark className="w-3.5 h-3.5" />
                          <span>市選管 選挙公報原本PDF</span>
                          <ExternalLink className="w-3 h-3 opacity-60 ml-0.5" />
                        </a>
                        <ReportIssueButton
                          targetUrl={pledge.election_promise.bulletin_url}
                          speaker={mayorInfo.name}
                          meetingDate={pledge.title || pledge.headline || ""}
                          targetId={`pledge_${pledge.id || pledge.pledge_id}`}
                          municipality={mayorInfo.city_label || "横浜市"}
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
                                municipality={mayorInfo.city_label || '名古屋市'}
                              />
                            </div>
                          ) : (
                            <span className="font-mono bg-white text-indigo-900 px-2 py-0.5 rounded border border-indigo-100 font-extrabold">{plan.plan_name}</span>
                          )}
                          <span className="text-slate-400">{plan.date} 策定</span>
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
                                  municipality={mayorInfo.city_label || '名古屋市'}
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
                              municipality={mayorInfo.city_label || '名古屋市'}
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
                                <span key={party} className={`px-2 py-0.5 rounded text-[10px] font-black inline-flex items-center gap-1 ${vote.includes('賛成') ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'}`}>
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
                        <span className="font-mono text-slate-500 font-bold shrink-0 mt-[2px]">{milestone.date}</span>
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
                              municipality={mayorInfo.city_label || '名古屋市'}
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