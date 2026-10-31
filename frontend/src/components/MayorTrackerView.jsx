import React, { useState, useMemo } from 'react';
import { 
  CheckCircle2, Clock, AlertCircle, ExternalLink, 
  FileText, Landmark, ShieldCheck, ChevronRight, 
  ArrowLeft, Search, Filter, BookOpen, Layers, Check
} from 'lucide-react';

const STAGES = [
  { level: 1, label: '公約表明', num: '①' },
  { level: 2, label: '市公式確定計画', num: '②' },
  { level: 3, label: '予算措置', num: '③' },
  { level: 4, label: '条例提出・可決', num: '④' },
  { level: 5, label: '成立・執行', num: '⑤' },
];

export default function MayorTrackerView({ data, cityCode, onBack }) {
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  if (!data || !data.pledges) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center">
        <AlertCircle className="w-12 h-12 text-slate-400 mx-auto mb-4" />
        <h2 className="text-lg font-bold text-slate-700">市長トラッカーデータを読み込めませんでした</h2>
        <button onClick={onBack} className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700">
          ポータルへ戻る
        </button>
      </div>
    );
  }

  const { mayor_info, summary_stats, kpis, pledges } = data;

  const categories = useMemo(() => {
    const cats = new Set(pledges.map(p => p.category).filter(Boolean));
    return ['ALL', ...Array.from(cats)];
  }, [pledges]);

  const filteredPledges = useMemo(() => {
    return pledges.filter(p => {
      const matchCat = selectedCategory === 'ALL' || p.category === selectedCategory;
      const q = searchQuery.toLowerCase();
      const matchQuery = !q || 
        (p.headline && p.headline.toLowerCase().includes(q)) ||
        (p.election_promise?.quote && p.election_promise.quote.toLowerCase().includes(q)) ||
        (p.official_plan?.plan_name && p.official_plan.plan_name.toLowerCase().includes(q));
      return matchCat && matchQuery;
    });
  }, [pledges, selectedCategory, searchQuery]);

  return (
    <div className="min-h-screen bg-[#F8FAFC] pb-16">
      {/* ナビゲーションバー */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <button 
            onClick={onBack}
            className="inline-flex items-center gap-2 text-sm font-bold text-slate-600 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            トップへ戻る
          </button>
          <div className="text-xs font-semibold text-slate-500">
            {data.city_name} 政策ライフサイクル検証基盤
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 pt-8">
        {/* 首長情報ヘッダー */}
        <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm mb-6">
          <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
            <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-2xl overflow-hidden bg-slate-100 border-2 border-slate-200 shrink-0 flex items-center justify-center">
              {mayor_info?.profile_image ? (
                <img 
                  src={mayor_info.profile_image} 
                  alt={mayor_info.name} 
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    if (mayor_info.fallback_image && e.target.src !== mayor_info.fallback_image) {
                      e.target.src = mayor_info.fallback_image;
                    } else {
                      e.target.style.display = 'none';
                    }
                  }}
                />
              ) : (
                <Landmark className="w-10 h-10 text-slate-400" />
              )}
            </div>

            <div className="flex-grow text-center sm:text-left">
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  {mayor_info?.city_label || data.city_name}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200">
                  {mayor_info?.party || '無所属'}
                </span>
                <span className="text-xs text-slate-500 font-medium">
                  {mayor_info?.term}
                </span>
              </div>

              <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight mb-3">
                {mayor_info?.name || data.mayor_name} <span className="text-base sm:text-lg font-bold text-slate-500">{mayor_info?.title || '市長'}</span>
              </h1>

              {/* 一次資料原本リンクボタン群 */}
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-3 pt-2">
                {mayor_info?.bulletin_pdf && (
                  <a 
                    href={mayor_info.bulletin_pdf} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-2xs"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>{mayor_info.bulletin_label || '選挙公報原本（一次資料PDF）'}</span>
                    <ExternalLink className="w-3 h-3 opacity-80" />
                  </a>
                )}
                {mayor_info?.strategy_main_pdf && (
                  <a 
                    href={mayor_info.strategy_main_pdf} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 transition-colors"
                  >
                    <BookOpen className="w-3.5 h-3.5 text-slate-500" />
                    <span>{mayor_info.strategy_main_label || '市総合計画（基本構想）'}</span>
                    <ExternalLink className="w-3 h-3 opacity-60" />
                  </a>
                )}
              </div>
            </div>
          </div>

          {/* KPI 指標カード */}
          {kpis && kpis.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6 pt-6 border-t border-slate-100">
              {kpis.map((kpi, idx) => (
                <div key={idx} className="bg-slate-50/80 rounded-xl p-4 border border-slate-100">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-slate-500">{kpi.label}</span>
                    {kpi.badge && (
                      <span className="text-[10px] font-black px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">
                        {kpi.badge}
                      </span>
                    )}
                  </div>
                  <div className="text-xl sm:text-2xl font-black text-slate-900">{kpi.value}</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">{kpi.subtext}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 💡 データ仕様と定量の完全性（検証方針バナー） */}
        <div className="bg-gradient-to-r from-slate-900 to-indigo-950 rounded-2xl p-6 text-white shadow-md mb-8">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center shrink-0 mt-0.5 text-indigo-300">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-base sm:text-lg font-black tracking-tight text-white">
                  市長政策トラッカーのデータ仕様と定量の完全性
                </h2>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-500/30 text-indigo-200 border border-indigo-400/30">
                  一次資料100%厳格準拠
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                現職首長の主要な看板公約を対象に、<strong className="text-white">「①公約表明 ➔ ②市公式確定計画（自治体の公式確定計画） ➔ ③予算措置 ➔ ④条例提出・可決 ➔ ⑤成立・執行」</strong>の5段階を追跡しています。
              </p>
              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed pt-1 border-t border-white/10">
                予算データに関しては、AIの推論を経由せず、自治体発行の<strong className="text-white">『主要事業説明書』等のPDF原本から直接抽出した「千円単位の計上額」および「特定財源内訳（宿泊税充当額、国費、市債、一般財源）」</strong>を紐付けています。各公約カードから主要事業説明書PDF原本への直接リンクを完備し、原資料を確認できる状態で掲載し検証可能性を担保しています。
              </p>
            </div>
          </div>
        </div>

        {/* フィルター＆検索バー */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0">
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-colors ${
                  selectedCategory === cat 
                    ? 'bg-slate-900 text-white' 
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                {cat === 'ALL' ? 'すべての分野' : cat}
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text"
              placeholder="公約名・施策を検索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* 公約カード一覧 */}
        <div className="space-y-6">
          {filteredPledges.map((p) => {
            const currentLevel = p.stage_level || 2;
            const isCompleted = currentLevel === 5;

            return (
              <div key={p.id} className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-7 shadow-sm hover:border-slate-300 transition-all">
                
                {/* 1. カード上部メタ情報 */}
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-700">
                      {p.category}
                    </span>
                    <span className="text-xs font-mono font-bold text-slate-400">{p.id}</span>
                  </div>
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black border ${
                    isCompleted 
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-300' 
                      : 'bg-indigo-50 text-indigo-800 border-indigo-200'
                  }`}>
                    {isCompleted ? <Check className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
                    {p.stage_label || `${currentLevel}.${STAGES[currentLevel - 1]?.label}`}
                  </span>
                </div>

                {/* 2. 公約見出し */}
                <h3 className="text-lg sm:text-xl font-black text-slate-900 mb-4 leading-snug">
                  {p.headline}
                </h3>

                {/* 3. 💡 5段階ビジュアルトラッカー（ステッパー） */}
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-200/80 mb-5">
                  <div className="text-[11px] font-bold text-slate-500 mb-3 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-indigo-600" />
                    <span>政策ライフサイクル進捗（5段階トラッカー）</span>
                  </div>
                  <div className="grid grid-cols-5 gap-1 sm:gap-2 relative">
                    {STAGES.map((s, sIdx) => {
                      const isPast = s.level < currentLevel;
                      const isCurrent = s.level === currentLevel;
                      const isReached = s.level <= currentLevel;

                      return (
                        <div key={s.level} className="flex flex-col items-center text-center relative z-10">
                          {/* ステップアイコン/サークル */}
                          <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-xs font-bold mb-1.5 transition-all shadow-2xs ${
                            isReached
                              ? isCompleted
                                ? 'bg-emerald-600 text-white'
                                : isCurrent
                                  ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
                                  : 'bg-indigo-500 text-white'
                              : 'bg-white text-slate-400 border border-slate-200'
                          }`}>
                            {isReached ? (
                              <Check className="w-3.5 h-3.5 sm:w-4 sm:h-4 stroke-[3]" />
                            ) : (
                              <span>{s.level}</span>
                            )}
                          </div>
                          {/* ステップラベル */}
                          <div className={`text-[10px] sm:text-xs leading-tight ${
                            isReached ? 'font-bold text-slate-900' : 'font-medium text-slate-400'
                          }`}>
                            <span className="hidden sm:inline">{s.num} </span>
                            {s.label}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* 4. 選挙公報原本 引用枠 */}
                {p.election_promise?.quote && (
                  <div className="bg-amber-50/70 border-l-4 border-amber-400 p-3.5 rounded-r-xl mb-5 text-xs text-amber-950 leading-relaxed">
                    <div className="font-black text-[11px] text-amber-800 uppercase tracking-wider mb-1 flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5" />
                        {p.election_promise.source_name || '選挙公報 原文引用'}
                      </span>
                      {p.election_promise.bulletin_url && (
                        <a 
                          href={p.election_promise.bulletin_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-900 hover:underline"
                        >
                          公報原本で確認 <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      )}
                    </div>
                    “{p.election_promise.quote}”
                  </div>
                )}

                {/* 5. 一次資料・政策進捗 3カラム詳細グリッド */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 pt-4 border-t border-slate-100 text-xs">
                  
                  {/* カラム1: ② 市公式確定計画 */}
                  <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-100 flex flex-col justify-between">
                    <div>
                      <div className="font-bold text-slate-700 flex items-center justify-between mb-2">
                        <span className="flex items-center gap-1.5">
                          <BookOpen className="w-3.5 h-3.5 text-blue-600" />
                          ② 市公式確定計画
                        </span>
                        {p.official_plan?.doc_url && (
                          <a 
                            href={p.official_plan.doc_url} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className="text-blue-600 hover:text-blue-800"
                            title="計画公文書を開く"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                      <div className="font-bold text-slate-900 text-xs mb-1">
                        {p.official_plan?.plan_name || '計画策定・位置づけ中'}
                      </div>
                      <div className="text-[11px] text-slate-600 leading-relaxed">
                        {p.official_plan?.summary || '市の基本方針および個別実施計画に明記'}
                      </div>
                    </div>
                    {p.official_plan?.doc_url && (
                      <div className="pt-2.5 mt-2 border-t border-slate-200/60">
                        <a 
                          href={p.official_plan.doc_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[10px] font-bold text-blue-600 hover:underline"
                        >
                          公式計画原本を確認 <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </div>
                    )}
                  </div>

                  {/* カラム2: ③ 予算措置（定量の完全性・千円単位・特定財源内訳） */}
                  <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-100 flex flex-col justify-between">
                    <div>
                      <div className="font-bold text-slate-700 flex items-center justify-between mb-2">
                        <span className="flex items-center gap-1.5">
                          <Landmark className="w-3.5 h-3.5 text-amber-600" />
                          ③ 予算措置（主要事業説明書）
                        </span>
                        {p.budget_records?.[0]?.doc_url && (
                          <a 
                            href={p.budget_records[0].doc_url} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className="text-amber-600 hover:text-amber-800"
                            title="予算書PDF原本を開く"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>

                      {p.budget_records && p.budget_records.length > 0 ? (
                        <>
                          <div className="font-bold text-slate-900 text-xs mb-1">
                            {p.budget_records[0].project_name}
                          </div>
                          <div className="flex items-baseline gap-2 mb-2">
                            <span className="text-base font-black text-slate-900">
                              {p.budget_records[0].amount_display}
                            </span>
                            {p.budget_records[0].amount_thousand_yen && (
                              <span className="text-[10px] font-bold text-slate-500">
                                ({p.budget_records[0].amount_thousand_yen})
                              </span>
                            )}
                          </div>

                          {/* 💡 特定財源内訳ピル一覧 */}
                          {p.budget_records[0].funding_sources && p.budget_records[0].funding_sources.length > 0 && (
                            <div className="mb-2 space-y-1">
                              <div className="text-[10px] font-bold text-slate-500">財源内訳:</div>
                              <div className="flex flex-wrap gap-1">
                                {p.budget_records[0].funding_sources.map((fs, fIdx) => (
                                  <span key={fIdx} className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-white text-slate-700 border border-slate-200">
                                    <span className="text-slate-400">{fs.label}:</span>
                                    <span className="text-slate-900">{fs.amount}</span>
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          <div className="text-[10px] text-slate-500">
                            {p.budget_records[0].doc_source}
                          </div>
                        </>
                      ) : (
                        <div className="text-[11px] text-slate-500 py-2">当初予算の編成・要求段階</div>
                      )}
                    </div>

                    {p.budget_records?.[0]?.doc_url && (
                      <div className="pt-2.5 mt-2 border-t border-slate-200/60">
                        <a 
                          href={p.budget_records[0].doc_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-700 hover:underline"
                        >
                          主要事業説明書PDF原本で確認 <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </div>
                    )}
                  </div>

                  {/* カラム3: ④ 条例・最新実績（⑤ 成立・執行） */}
                  <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-100 flex flex-col justify-between">
                    <div>
                      <div className="font-bold text-slate-700 flex items-center gap-1.5 mb-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        ④ 条例提出・⑤ 執行実績
                      </div>

                      {p.legislative_bill && (
                        <div className="mb-2.5 bg-white p-2 rounded-lg border border-slate-200/80">
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                              {p.legislative_bill.result || '可決'}
                            </span>
                            <span className="text-[10px] font-mono text-slate-400">{p.legislative_bill.bill_number}</span>
                          </div>
                          <div className="text-xs font-bold text-slate-900 leading-tight">
                            {p.legislative_bill.bill_title}
                          </div>
                        </div>
                      )}

                      {p.milestone ? (
                        <div className="text-[11px] text-slate-700 leading-relaxed">
                          <span className="font-bold text-slate-900">{p.milestone.date}: </span>
                          <span>{p.milestone.title}</span>
                        </div>
                      ) : (
                        <div className="text-[11px] text-slate-500">順次、定例会提出および制度執行中</div>
                      )}
                    </div>

                    {p.milestone?.evidence_url && (
                      <div className="pt-2.5 mt-2 border-t border-slate-200/60">
                        <a 
                          href={p.milestone.evidence_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 hover:underline"
                        >
                          確定エビデンス（報道発表等） <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </div>
                    )}
                  </div>

                </div>

                {/* 6. 市長直接答弁ログ（任期厳格連動・公式議事録原本直結） */}
                {p.debate_statements && p.debate_statements.length > 0 ? (
                  <div className="mt-4 pt-3.5 border-t border-slate-100">
                    <div className="text-[11px] font-bold text-slate-700 mb-2 flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5 text-indigo-600" />
                        市長直接答弁（公式議事録リンク）
                      </span>
                      <span className="text-[10px] text-indigo-600 font-semibold bg-indigo-50 px-2 py-0.5 rounded-full">
                        任期厳格連動
                      </span>
                    </div>
                    <div className="space-y-2">
                      {p.debate_statements.map((stmt, sIdx) => (
                        <div key={sIdx} className="bg-slate-50/90 rounded-xl p-3 border border-slate-200/70 text-xs">
                          <div className="flex flex-wrap items-center justify-between gap-1 mb-1.5 text-[11px]">
                            <span className="font-bold text-indigo-950">{stmt.speaker}</span>
                            <span className="text-slate-500 text-[10px]">{stmt.date} ｜ {stmt.session_name}</span>
                          </div>
                          <blockquote className="text-[11px] leading-relaxed text-slate-700 pl-2.5 border-l-2 border-indigo-500 mb-2.5 font-medium">
                            “{stmt.quote_summary}”
                          </blockquote>
                          {stmt.official_url && (
                            <div className="flex justify-end">
                              <a 
                                href={stmt.official_url || stmt.url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-[10px] font-bold text-indigo-600 hover:text-indigo-800 hover:underline bg-white px-2.5 py-1 rounded-lg border border-indigo-200 shadow-2xs transition-colors"
                              >
                                <ExternalLink className="w-2.5 h-2.5" />
                                <span>公式議事録原本で確認</span>
                              </a>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  cityCode === 'yokohama' && (
                    <div className="mt-3 pt-2 text-[10px] text-slate-400 text-right">
                      ※ 2026年10月新任就任のため、市会答弁ログは今後の定例会質疑に応じて順次反映されます。
                    </div>
                  )
                )}

              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
