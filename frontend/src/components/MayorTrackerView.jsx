import React, { useState, useMemo } from 'react';
import {
  Landmark, ArrowLeft, ExternalLink, ShieldCheck, BookmarkCheck,
  CheckCircle2, Clock, FileText, ChevronRight, Scale, Sparkles,
  PieChart, Filter, AlertCircle, Award, ArrowRight, Layers
} from 'lucide-react';

export default function MayorTrackerView({
  data,
  onBack,
  onSelectBill,
  onOpenMethodology
}) {
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedStageLevel, setSelectedStageLevel] = useState(0);

  // 💡 画像読み込みエラー管理
  const [imgSrc, setImgSrc] = useState('/councilors/matsui_koji.jpg');
  const [imgError, setImgError] = useState(false);

  const mayorInfo = data?.mayor_info || {};
  const stats = data?.stats || {};
  const pledges = data?.pledges || [];

  const categories = useMemo(() => {
    return [...new Set(pledges.map(p => p.category).filter(Boolean))];
  }, [pledges]);

  const filteredPledges = useMemo(() => {
    return pledges.filter(p => {
      if (selectedCategory && p.category !== selectedCategory) return false;
      if (selectedStageLevel > 0 && p.stage_level !== selectedStageLevel) return false;
      return true;
    });
  }, [pledges, selectedCategory, selectedStageLevel]);

  const STAGES = [
    { level: 1, label: '公約表明', desc: '市長選公報・マニフェスト' },
    { level: 2, label: '施政方針反映', desc: '本会議演説・所信表明' },
    { level: 3, label: '予算計上・実証', desc: '当初・補正予算措置' },
    { level: 4, label: '条例提出・可決', desc: '市会での議案成立' },
    { level: 5, label: '本格執行・達成', desc: '目標完了・制度運用' },
  ];

  const handleImageError = () => {
    if (imgSrc === '/councilors/matsui_koji.jpg') {
      // 予備として日本語パスを試す
      setImgSrc('/councilors/松井孝治.jpg');
    } else {
      setImgError(true);
    }
  };

  return (
    <main className="max-w-6xl mx-auto py-8 px-4 sm:px-6 animate-in fade-in duration-300 w-full space-y-8">
      {/* ナビゲーション上部 */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center text-xs font-bold text-slate-500 hover:text-indigo-600 transition-colors bg-white px-3 py-2 rounded-lg border border-slate-200 shadow-xs cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />ポータルに戻る
        </button>

        <div className="flex items-center gap-2">
          {mayorInfo.election_bulletin_pdf && (
            <a
              href={mayorInfo.election_bulletin_pdf}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-indigo-600 hover:bg-indigo-50 font-bold text-xs transition-colors shadow-2xs"
            >
              <Landmark className="w-3.5 h-3.5 text-indigo-500" />
              <span>市長選公報 原本PDF</span>
              <ExternalLink className="w-3 h-3 opacity-60" />
            </a>
          )}
          {mayorInfo.manifesto_url && (
            <a
              href={mayorInfo.manifesto_url}
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 font-bold text-xs transition-colors shadow-2xs"
            >
              <FileText className="w-3.5 h-3.5 text-slate-500" />
              <span>新京都戦略（骨子）</span>
              <ExternalLink className="w-3 h-3 opacity-60" />
            </a>
          )}
        </div>
      </div>

      {/* ヘッダーエリア：市長通信簿サマリー */}
      <header className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 pb-6 border-b border-slate-100">
          <div className="flex items-start gap-5">
            <div className="w-20 h-24 rounded-2xl overflow-hidden bg-slate-100 border border-slate-200 shrink-0 shadow-xs flex items-center justify-center">
              {!imgError ? (
                <img
                  src={imgSrc}
                  alt="松井孝治 京都市長"
                  className="w-full h-full object-cover object-top"
                  onError={handleImageError}
                />
              ) : (
                <div className="text-center p-2">
                  <span className="text-[10px] font-bold text-slate-400 block">京都市長</span>
                  <span className="text-xs font-black text-slate-600">松井孝治</span>
                </div>
              )}
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <span className="px-2.5 py-0.5 text-xs font-black rounded-md bg-indigo-600 text-white shadow-2xs">
                  第{mayorInfo.term_number || 27}代 京都市長
                </span>
                <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                  {mayorInfo.name || '松井 孝治'}
                </h1>
              </div>
              <p className="text-xs font-bold text-slate-500 mt-2 flex items-center gap-2 flex-wrap">
                <span>就任日: {mayorInfo.term_start}</span>
                <span>•</span>
                <span>任期: 2024年2月25日 〜 2028年2月24日</span>
              </p>
            </div>
          </div>

          <div className="bg-gradient-to-br from-indigo-50/80 to-slate-50 p-4 rounded-2xl border border-indigo-100 w-full md:w-auto shrink-0 flex items-center justify-around gap-6">
            <div className="text-center">
              <span className="text-[10px] font-black text-slate-400 block uppercase">追跡看板公約</span>
              <span className="text-2xl font-black text-slate-900 font-mono">{stats.total_pledges || 14}</span>
              <span className="text-[10px] text-slate-500 ml-0.5">項目</span>
            </div>
            <div className="w-px h-8 bg-slate-200" />
            <div className="text-center">
              <span className="text-[10px] font-black text-indigo-500 block uppercase">条例成立・可決</span>
              <span className="text-2xl font-black text-indigo-600 font-mono">{stats.bill_passed_count || 0}</span>
              <span className="text-[10px] text-indigo-500 ml-0.5">件</span>
            </div>
            <div className="w-px h-8 bg-slate-200" />
            <div className="text-center">
              <span className="text-[10px] font-black text-emerald-600 block uppercase">政策具体化率</span>
              <span className="text-2xl font-black text-emerald-600 font-mono">{stats.execution_rate_percentage || 0}%</span>
            </div>
          </div>
        </div>

        {/* 政策ライフサイクル検証の原則説明 */}
        <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200/80 text-xs text-slate-600 leading-relaxed flex items-start gap-3">
          <ShieldCheck className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
          <div>
            <strong className="text-slate-800">政策ライフサイクルの検証原則:</strong>
            <p className="text-[11px] text-slate-500 mt-0.5">
              首長（市長）は議決権を持たない代わりに予算編成権と議案提出権を独占しています。本トラッカーでは主観的評価を行わず、「公約原本の言及 ➔ 施政方針での表明 ➔ 予算書への計上 ➔ 条例改正案の市会可決」という客観的な公文書の足跡のみを追跡します。
            </p>
          </div>
        </div>
      </header>

      {/* 絞り込みバー */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs font-bold text-slate-400 mr-1 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" />進捗度:
          </span>
          {[
            { level: 0, label: 'すべて' },
            { level: 4, label: '条例可決・成立' },
            { level: 3, label: '予算計上・実証中' },
            { level: 2, label: '施政方針表明' },
          ].map(s => (
            <button
              key={s.level}
              onClick={() => setSelectedStageLevel(s.level)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                selectedStageLevel === s.level
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <span className="text-xs font-bold text-slate-400 shrink-0">分野:</span>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full md:w-48 bg-slate-100 border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-bold text-slate-700 outline-none cursor-pointer"
          >
            <option value="">全分野 ({pledges.length})</option>
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
      </div>

      {/* 14項目 看板公約カード一覧 */}
      <div className="space-y-8">
        {filteredPledges.map((pledge) => {
          const lc = pledge.lifecycle || {};
          const speeches = lc.policy_speeches || [];
          const budgets = lc.budgets || [];
          const bills = lc.bills || [];
          const milestones = lc.milestones || [];

          return (
            <article
              key={pledge.id}
              className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden"
            >
              <div className="bg-slate-50/80 px-6 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black bg-indigo-50 text-indigo-700 border border-indigo-200">
                    {pledge.category}
                  </span>
                  <span className="text-xs font-mono text-slate-400 font-bold">{pledge.id}</span>
                  <h2 className="text-base sm:text-lg font-black text-slate-900 leading-snug">
                    {pledge.headline}
                  </h2>
                </div>
                <div className="shrink-0 flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-xs font-black inline-flex items-center gap-1.5 ${
                    pledge.stage_level >= 4
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                  }`}>
                    {pledge.stage_level >= 4 ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
                    進捗: {pledge.stage_label}
                  </span>
                </div>
              </div>

              <div className="px-6 py-4 bg-slate-50/40 border-b border-slate-100">
                <div className="grid grid-cols-5 gap-1 sm:gap-2">
                  {STAGES.map((st) => {
                    const isPassed = pledge.stage_level >= st.level;
                    const isCurrent = pledge.stage_level === st.level;

                    return (
                      <div key={st.level} className="text-center space-y-1">
                        <div className={`h-1.5 rounded-full transition-all ${
                          isPassed ? 'bg-indigo-600' : 'bg-slate-200'
                        }`} />
                        <span className={`text-[10px] font-black block truncate ${
                          isCurrent ? 'text-indigo-600 font-extrabold' : isPassed ? 'text-slate-700' : 'text-slate-400'
                        }`}>
                          {st.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">
                {/* 左側: 選挙公約 原本引用 */}
                <div className="lg:col-span-4 p-6 bg-indigo-50/15 space-y-4 flex flex-col justify-between">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-black text-indigo-950 flex items-center gap-1.5 uppercase tracking-wider">
                        <BookmarkCheck className="w-4 h-4 text-indigo-600" />
                        選挙公約 原本引用
                      </span>
                      <span className="text-[10px] font-bold text-slate-400">公式選挙公報</span>
                    </div>

                    <div className="bg-white p-4 rounded-2xl border border-indigo-100/80 shadow-2xs space-y-2">
                      <span className="text-[10px] font-bold text-slate-400 block">公報紙面の正確な記載:</span>
                      <blockquote className="text-xs text-slate-800 font-bold leading-relaxed border-l-2 border-indigo-500 pl-3 italic">
                        “{pledge.election_promise?.quote}”
                      </blockquote>
                    </div>
                  </div>

                  {pledge.election_promise?.bulletin_url && (
                    <div className="pt-2">
                      <a
                        href={pledge.election_promise.bulletin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-indigo-600 hover:text-indigo-800 hover:underline"
                      >
                        <Landmark className="w-3.5 h-3.5" />
                        <span>選管公式公報原本（PDF）で確認</span>
                        <ExternalLink className="w-3 h-3 opacity-60 ml-0.5" />
                      </a>
                    </div>
                  )}
                </div>

                {/* 右側: 執行パイプライン */}
                <div className="lg:col-span-8 p-6 space-y-6 bg-white">
                  {speeches.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-black text-slate-700 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-indigo-500" />
                        市会本会議での施政方針・所信表明
                      </span>
                      <div className="space-y-2">
                        {speeches.map((sp, idx) => (
                          <div key={idx} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1.5">
                            <div className="flex items-center justify-between text-[10px] font-bold text-slate-500">
                              <span className="font-mono bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">
                                {sp.date} / {sp.session_name}
                              </span>
                              {sp.official_url && (
                                <a
                                  href={sp.official_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-indigo-600 hover:underline inline-flex items-center gap-0.5 font-bold"
                                >
                                  会議録原本 <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                                </a>
                              )}
                            </div>
                            <p className="text-xs text-slate-700 leading-relaxed font-medium">
                              {sp.summary}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {budgets.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-black text-slate-700 flex items-center gap-1.5">
                        <PieChart className="w-3.5 h-3.5 text-emerald-500" />
                        計上された予算措置
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        {budgets.map((bg, idx) => (
                          <div key={idx} className="p-3 rounded-xl bg-emerald-50/30 border border-emerald-100 space-y-1">
                            <div className="flex justify-between items-center text-[10px] font-bold">
                              <span className="text-emerald-800 font-mono bg-white px-1.5 py-0.2 rounded border border-emerald-200">
                                {bg.fiscal_year}
                              </span>
                              <span className="text-emerald-700 font-black font-mono text-xs">{bg.amount_text}</span>
                            </div>
                            <div className="text-xs font-bold text-slate-800 truncate" title={bg.item_name}>
                              {bg.item_name}
                            </div>
                            {bg.note && <p className="text-[10px] text-slate-500 leading-normal">{bg.note}</p>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {bills.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-black text-slate-700 flex items-center gap-1.5">
                        <Scale className="w-3.5 h-3.5 text-indigo-600" />
                        提出条例案と市会審議結果（二元代表制）
                      </span>
                      <div className="space-y-2">
                        {bills.map((bill, idx) => (
                          <div key={idx} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                            <div className="flex items-center justify-between flex-wrap gap-2">
                              <span className="text-[10px] font-mono text-slate-500 font-black">
                                {bill.session_name} ({bill.bill_number})
                              </span>
                              <span className="px-2 py-0.5 rounded text-[11px] font-black bg-emerald-100 text-emerald-800 border border-emerald-200">
                                審議結果: {bill.status} ({bill.passed_date})
                              </span>
                            </div>
                            <h3 className="text-xs font-bold text-slate-900 leading-snug">
                              {bill.bill_title}
                            </h3>

                            {bill.party_votes && (
                              <div className="pt-2 border-t border-slate-200/60 flex items-center gap-2 flex-wrap text-xs">
                                <span className="text-[10px] font-bold text-slate-400">会派賛否:</span>
                                {Object.entries(bill.party_votes).map(([party, vote]) => (
                                  <span
                                    key={party}
                                    className={`px-2 py-0.5 rounded text-[10px] font-black inline-flex items-center gap-1 ${
                                      vote === '賛成'
                                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                        : 'bg-rose-50 text-rose-700 border border-rose-200'
                                    }`}
                                  >
                                    <span>{party}:</span>
                                    <span>{vote}</span>
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {milestones.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-black text-slate-700 flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-indigo-500" />
                        執行マイルストーン
                      </span>
                      <div className="space-y-1.5 pl-2 border-l-2 border-indigo-100">
                        {milestones.map((ms, idx) => (
                          <div key={idx} className="flex items-start gap-2 text-xs">
                            <span className={`w-2 h-2 rounded-full mt-1 shrink-0 ${
                              ms.is_completed ? 'bg-indigo-600' : 'bg-slate-300'
                            }`} />
                            <span className="font-mono text-slate-400 text-[11px] shrink-0">{ms.date}</span>
                            <span className={`font-medium ${ms.is_completed ? 'text-slate-800' : 'text-slate-400'}`}>
                              {ms.title}
                            </span>
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