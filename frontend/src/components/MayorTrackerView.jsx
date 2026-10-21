import React, { useState, useMemo } from 'react';
import {
  Landmark, ArrowLeft, ExternalLink, ShieldCheck, BookmarkCheck,
  CheckCircle2, Clock, FileText, Scale, Sparkles,
  PieChart, Filter, AlertCircle, ArrowRight, Layers, Coins, Building2
} from 'lucide-react';

export default function MayorTrackerView({
  data,
  onBack,
  onSelectBill,
  onOpenMethodology
}) {
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedStageLevel, setSelectedStageLevel] = useState(0);

  // 画像フォールバック制御
  const [imgSrc, setImgSrc] = useState('/councilors/matsui_koji.jpg');
  const [imgError, setImgError] = useState(false);

  const mayorInfo = data?.mayor_info || {};
  const stats = data?.summary_stats || {};
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
    { level: 1, label: '1.公約表明', desc: '市長選公報・マニフェスト' },
    { level: 2, label: '2.施政方針', desc: '本会議演説・所信表明' },
    { level: 3, label: '3.予算措置', desc: '当初・補正予算計上' },
    { level: 4, label: '4.条例提出', desc: '市会での審議・可決' },
    { level: 5, label: '5.成立・執行', desc: '目標完了・制度運用' },
  ];

  const handleImageError = () => {
    if (imgSrc === '/councilors/matsui_koji.jpg') {
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
          {mayorInfo.bulletin_pdf && (
            <a
              href={mayorInfo.bulletin_pdf}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-indigo-600 hover:bg-indigo-50 font-bold text-xs transition-colors shadow-2xs"
            >
              <Landmark className="w-3.5 h-3.5 text-indigo-500" />
              <span>市長選公報 原本PDF</span>
              <ExternalLink className="w-3 h-3 opacity-60" />
            </a>
          )}
          {mayorInfo.manifesto_pdf && (
            <a
              href={mayorInfo.manifesto_pdf}
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

          {/* 財政ハイライトカード */}
          <div className="grid grid-cols-3 gap-3 sm:gap-6 bg-gradient-to-br from-indigo-50/80 to-slate-50 p-4 rounded-2xl border border-indigo-100 w-full md:w-auto shrink-0">
            <div className="text-center">
              <span className="text-[10px] font-black text-indigo-700 block uppercase">公約投入予算総額</span>
              <span className="text-lg sm:text-2xl font-black text-slate-900 font-mono">{stats.total_allocated_budget_jpy || '104億円'}</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">主要事業説明書定量</span>
            </div>
            <div className="text-center border-x border-indigo-100/80 px-2 sm:px-4">
              <span className="text-[10px] font-black text-emerald-700 block uppercase">宿泊税収（年見込）</span>
              <span className="text-lg sm:text-2xl font-black text-emerald-600 font-mono">{stats.accommodation_tax_revenue_jpy || '132億円'}</span>
              <span className="text-[10px] text-emerald-600 block mt-0.5">財源エンジン化</span>
            </div>
            <div className="text-center">
              <span className="text-[10px] font-black text-slate-500 block uppercase">過去負債返済</span>
              <span className="text-lg sm:text-2xl font-black text-slate-700 font-mono">{stats.debt_repayment_jpy || '年35億円'}</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">公債基金償還堅持</span>
            </div>
          </div>
        </div>

        {/* 政策ライフサイクルの検証原則 */}
        <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200/80 text-xs text-slate-600 leading-relaxed flex items-start gap-3">
          <ShieldCheck className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
          <div>
            <strong className="text-slate-800">政策ライフサイクル×予算定量検証の原則:</strong>
            <p className="text-[11px] text-slate-500 mt-0.5">
              市長は議案提出権と予算編成権を独占しています。本トラッカーは、単なるテキスト要約にとどまらず「①公約表明 ➔ ②施政方針演説 ➔ ③予算措置（計上額・財源内訳） ➔ ④条例提出と可決」という一次公文書の足跡を定量的に追跡します。
            </p>
          </div>
        </div>
      </header>

      {/* 絞り込みバー */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs font-bold text-slate-400 mr-1 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" />進捗フェーズ:
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

      {/* 看板公約カード一覧（14項目） */}
      <div className="space-y-8">
        {filteredPledges.map((pledge) => {
          const budgets = pledge.budget_records || [];
          const bill = pledge.legislative_bill;
          const speech = pledge.policy_address;
          const milestone = pledge.milestone;

          return (
            <article
              key={pledge.id}
              className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden"
            >
              {/* カードヘッダー */}
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

              {/* 5段階 政策ライフサイクル・プログレスバー */}
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

              {/* 2カラム対比グリッド（左: 選挙公約原本 ⇄ 右: 執行・予算定量・議決） */}
              <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">
                {/* 左側: 選挙公報原本引用 (4列) */}
                <div className="lg:col-span-4 p-6 bg-indigo-50/15 space-y-4 flex flex-col justify-between">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-black text-indigo-950 flex items-center gap-1.5 uppercase tracking-wider">
                        <BookmarkCheck className="w-4 h-4 text-indigo-600" />
                        選挙公報 原本引用
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
                        <span>京都市選管 公式公報原本（PDF）で確認</span>
                        <ExternalLink className="w-3 h-3 opacity-60 ml-0.5" />
                      </a>
                    </div>
                  )}
                </div>

                {/* 右側: 市政での具体的執行アクション（定量データ連動） (8列) */}
                <div className="lg:col-span-8 p-6 space-y-6 bg-white">
                  {/* ① 施政方針・所信表明演説 */}
                  {speech && (
                    <div className="space-y-2">
                      <span className="text-xs font-black text-slate-700 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-indigo-500" />
                        市会本会議での施政方針・所信表明
                      </span>
                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1.5">
                        <div className="flex items-center justify-between text-[10px] font-bold text-slate-500">
                          <span className="font-mono bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">
                            {speech.date} / {speech.session}
                          </span>
                          {speech.speech_url && (
                            <a
                              href={speech.speech_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-indigo-600 hover:underline inline-flex items-center gap-0.5 font-bold"
                            >
                              会議録原本 <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                            </a>
                          )}
                        </div>
                        <p className="text-xs text-slate-700 leading-relaxed font-medium">
                          {speech.summary}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* ② 予算定量データカード（最重要） */}
                  {budgets.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-slate-700 flex items-center gap-1.5">
                          <Coins className="w-3.5 h-3.5 text-emerald-600" />
                          予算措置・計上実績（定量エビデンス）
                        </span>
                        <span className="text-[10px] text-slate-400 font-bold">
                          計 {budgets.length} 事業
                        </span>
                      </div>

                      <div className="space-y-3">
                        {budgets.map((b, bIdx) => (
                          <div
                            key={bIdx}
                            className="p-4 rounded-2xl bg-emerald-50/20 border border-emerald-100 space-y-2.5"
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] font-mono font-bold bg-white text-emerald-800 px-2 py-0.5 rounded border border-emerald-200 shrink-0">
                                  {b.fiscal_year}
                                </span>
                                <span className="text-xs font-black text-slate-800 leading-snug">
                                  {b.project_name}
                                </span>
                              </div>
                              <div className="text-right shrink-0">
                                <span className="text-base sm:text-lg font-black text-emerald-700 font-mono">
                                  {b.amount_display}
                                </span>
                              </div>
                            </div>

                            {/* 財源内訳バッジ */}
                            <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-emerald-100/60">
                              <span className="text-[10px] font-bold text-slate-400">財源内訳:</span>
                              {b.funding_sources?.map((fs, fsIdx) => (
                                <span
                                  key={fsIdx}
                                  className={`text-[10px] font-bold px-2 py-0.5 rounded border ${fs.color || 'bg-slate-50 text-slate-600'}`}
                                >
                                  {fs.label}: {fs.amount}
                                </span>
                              ))}
                            </div>

                            {/* 主要事業説明書 原本リンク */}
                            {b.doc_url && (
                              <div className="pt-1 flex justify-between items-center text-[10px]">
                                <span className="text-slate-400 font-medium">出典: {b.doc_source}</span>
                                <a
                                  href={b.doc_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-emerald-700 hover:text-emerald-900 font-bold inline-flex items-center gap-0.5 hover:underline"
                                >
                                  主要事業説明書 原本PDF <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                                </a>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* ③ 提出条例案と会派別賛否態度 */}
                  {bill && (
                    <div className="space-y-2">
                      <span className="text-xs font-black text-slate-700 flex items-center gap-1.5">
                        <Scale className="w-3.5 h-3.5 text-indigo-600" />
                        提出条例案と市会審議結果（二元代表制）
                      </span>
                      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <span className="text-[10px] font-mono text-slate-500 font-black">
                            {bill.session_name} ({bill.bill_number})
                          </span>
                          <span className="px-2 py-0.5 rounded text-[11px] font-black bg-emerald-100 text-emerald-800 border border-emerald-200">
                            結果: {bill.result}
                          </span>
                        </div>
                        <h3 className="text-xs font-bold text-slate-900 leading-snug">
                          {bill.bill_title}
                        </h3>

                        {/* 会派別賛否バッジ */}
                        {bill.party_votes && (
                          <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between flex-wrap gap-2">
                            <div className="flex items-center gap-1.5 flex-wrap text-xs">
                              <span className="text-[10px] font-bold text-slate-400">会派賛否:</span>
                              {Object.entries(bill.party_votes).map(([party, vote]) => (
                                <span
                                  key={party}
                                  className={`px-2 py-0.5 rounded text-[10px] font-black inline-flex items-center gap-1 ${
                                    vote.includes('賛成')
                                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                      : 'bg-rose-50 text-rose-700 border border-rose-200'
                                  }`}
                                >
                                  <span>{party}:</span>
                                  <span>{vote}</span>
                                </span>
                              ))}
                            </div>

                            {/* モーダル連携ボタン */}
                            {onSelectBill && (
                              <button
                                onClick={() => onSelectBill(bill)}
                                className="px-2.5 py-1 text-[11px] font-bold text-indigo-600 hover:text-indigo-800 bg-white hover:bg-indigo-50 rounded-lg border border-indigo-200 transition-all flex items-center gap-1 shadow-2xs cursor-pointer"
                              >
                                <span>全議員の採決ログ詳細</span>
                                <ArrowRight className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* ④ 執行マイルストーン */}
                  {milestone && (
                    <div className="space-y-1.5 pl-3 border-l-2 border-indigo-200">
                      <span className="text-[10px] font-black text-slate-400 block uppercase">
                        直近の達成マイルストーン
                      </span>
                      <div className="flex items-center gap-2 text-xs">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                        <span className="font-mono text-slate-500 font-bold">{milestone.date}</span>
                        <span className="font-bold text-slate-800">{milestone.title}</span>
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