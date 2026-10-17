import React, { useState, useMemo } from 'react';
import { Sparkles, MessageCircle, User, Calendar, Tag } from 'lucide-react';
import { cleanName } from '../utils/styleHelpers';

// クイックジャンルの定義
const GENRE_PRESETS = [
  { id: 'all', label: 'すべて' },
  { id: 'industry', label: '産業・観光', keywords: ['産業', '観光', '経済', '中小企業'] },
  { id: 'transit', label: '交通・都市', keywords: ['都市再生', '交通', '市バス', 'まちづくり'] },
  { id: 'welfare', label: '子育て・福祉', keywords: ['子育て', '福祉', '医療', '教育'] },
  { id: 'environment', label: 'くらし・防災', keywords: ['環境', '防災', '消防', '治安'] },
  { id: 'finance', label: '財政・行革', keywords: ['財政', '行革'] },
];

export default function HighlightedThreads({
  statements = [],
  onSpeakerClick,
  onViewContext
}) {
  const [selectedGenre, setSelectedGenre] = useState('all');
  const [period, setPeriod] = useState('recent'); // 'recent' (直近1年) | 'all' (任期全体)

  // 選択条件に基づき上位3件を動的に抽出
  const filteredHighlights = useMemo(() => {
    if (!statements || statements.length === 0) return [];

    // 1. 期間による絞り込み（最新日付から365日前までを「直近1年」とする）
    let target = [...statements];
    if (period === 'recent') {
      const dates = target.map(s => s.meeting_date).filter(Boolean).sort();
      if (dates.length > 0) {
        const latestDateStr = dates[dates.length - 1];
        const latestDate = new Date(latestDateStr);
        const oneYearAgo = new Date(latestDate);
        oneYearAgo.setDate(oneYearAgo.getDate() - 365);
        target = target.filter(s => new Date(s.meeting_date) >= oneYearAgo);
      }
    }

    // 2. ジャンルによる絞り込み
    if (selectedGenre !== 'all') {
      const preset = GENRE_PRESETS.find(g => g.id === selectedGenre);
      if (preset && preset.keywords) {
        target = target.filter(s => 
          preset.keywords.some(kw => (s.category || '').includes(kw))
        );
      }
    }

    // 3. スコア合計（満点優先）降順、同点は日付順にソート
    target.sort((a, b) => {
      const totalA = a.evidence_score + a.solution_score + a.local_focus_score + a.constructive_score;
      const totalB = b.evidence_score + b.solution_score + b.local_focus_score + b.constructive_score;
      if (totalB !== totalA) return totalB - totalA;
      return new Date(b.meeting_date) - new Date(a.meeting_date);
    });

    // 上位3件をフォーマット
    return target.slice(0, 3).map(thread => {
      const total = thread.evidence_score + thread.solution_score + thread.local_focus_score + thread.constructive_score;
      let badgeTitle = "";
      let reason = "";
      let badgeColor = "";

      if (total === 20) {
        badgeTitle = "最高評価（全項目満点）";
        reason = "4つの評価軸すべてで満点を獲得した、極めて質の高いモデル論戦です。";
        badgeColor = "bg-yellow-50 text-yellow-700 border-yellow-200";
      } else if (total >= 18) {
        badgeTitle = "マスタークラス評価";
        reason = "複数の軸で満点を獲得し、圧倒的な解像度と対案で議論を牽引しています。";
        badgeColor = "bg-blue-50 text-blue-700 border-blue-200";
      } else {
        badgeTitle = "高評価ピックアップ";
        reason = "データと対案に基づき、この分野において特に評価の高かった注目の質疑です。";
        badgeColor = "bg-emerald-50 text-emerald-700 border-emerald-200";
      }

      return {
        ...thread,
        highlightTheme: { title: badgeTitle, desc: reason, badgeColor }
      };
    });
  }, [statements, selectedGenre, period]);

  if (!statements || statements.length === 0) return null;

  return (
    <section className="bg-gradient-to-br from-indigo-50/40 via-white to-slate-50 p-5 md:p-6 rounded-2xl border border-indigo-100/60 shadow-sm space-y-4">
      
      {/* ヘッダーエリア */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-600">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-extrabold text-slate-900 tracking-tight">
              注目の政策論戦ピックアップ
            </h3>
            <p className="text-[10px] text-slate-400 font-medium">条件別のハイスコア質疑を自動抽出</p>
          </div>
        </div>

        {/* 期間切り替えトグル */}
        <div className="flex items-center bg-slate-100/80 p-0.5 rounded-lg border border-slate-200/80 self-start sm:self-auto text-[11px] font-bold">
          <button
            onClick={() => setPeriod('recent')}
            className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1 ${
              period === 'recent'
                ? 'bg-white text-indigo-700 shadow-2xs'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Calendar className="w-3 h-3" />
            直近1年
          </button>
          <button
            onClick={() => setPeriod('all')}
            className={`px-2.5 py-1 rounded-md transition-all ${
              period === 'all'
                ? 'bg-white text-indigo-700 shadow-2xs'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            任期全体
          </button>
        </div>
      </div>

      {/* ジャンル選択ピルボタン */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 hide-scrollbar">
        <span className="text-[10px] font-bold text-slate-400 shrink-0 mr-1 flex items-center">
          <Tag className="w-3 h-3 mr-0.5" />分野:
        </span>
        {GENRE_PRESETS.map((genre) => (
          <button
            key={genre.id}
            onClick={() => setSelectedGenre(genre.id)}
            className={`px-3 py-1 rounded-full text-xs font-bold transition-all shrink-0 border ${
              selectedGenre === genre.id
                ? 'bg-indigo-600 text-white border-indigo-600 shadow-2xs'
                : 'bg-white text-slate-600 hover:bg-slate-50 border-slate-200'
            }`}
          >
            {genre.label}
          </button>
        ))}
      </div>

      {/* カード一覧（モバイル横スクロール対応） */}
      {filteredHighlights.length > 0 ? (
        <div className="flex md:grid md:grid-cols-3 gap-4 overflow-x-auto md:overflow-visible pb-2 md:pb-0 snap-x snap-mandatory hide-scrollbar pt-1">
          {filteredHighlights.map((thread) => (
            <div
              key={thread.id}
              className="w-[85vw] sm:w-[340px] md:w-auto shrink-0 snap-center bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs hover:border-indigo-300 hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2.5">
                  <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded border ${thread.highlightTheme.badgeColor}`}>
                    {thread.highlightTheme.title}
                  </span>
                  <span className="text-[10px] text-slate-400 font-medium">{thread.meeting_date}</span>
                </div>

                <div className="flex items-center justify-between mb-2">
                  <button
                    onClick={() => onSpeakerClick(cleanName(thread.speaker))}
                    className="flex items-center text-xs font-black text-slate-800 hover:text-indigo-600 transition-colors"
                  >
                    <User className="w-3.5 h-3.5 mr-1 text-slate-400" />
                    {thread.speaker} 議員
                  </button>
                  <span className="text-[10px] font-bold text-slate-500 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100">
                    {thread.category}
                  </span>
                </div>

                <h4 className="text-xs font-bold text-slate-900 line-clamp-1 mb-2">
                  {thread.meeting_title}
                </h4>

                <div className="mb-2.5 p-2 bg-slate-50/80 rounded-lg border border-slate-100">
                  <p className="text-[9px] font-bold text-slate-400 mb-0.5 flex items-center">
                    <Sparkles className="w-3 h-3 mr-1 text-amber-500" />選出理由
                  </p>
                  <p className="text-[11px] text-slate-700 font-medium leading-relaxed">
                    {thread.highlightTheme.desc}
                  </p>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed line-clamp-3">
                  {thread.summary}
                </p>
              </div>

              <div className="pt-3 mt-3 border-t border-slate-100">
                <button
                  onClick={() => onViewContext(thread)}
                  className="w-full py-1.5 text-xs font-bold text-indigo-600 bg-indigo-50/60 hover:bg-indigo-600 hover:text-white rounded-lg transition-colors flex items-center justify-center"
                >
                  <MessageCircle className="w-3.5 h-3.5 mr-1" />
                  論戦タイムラインを読む
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-xs text-slate-400 bg-white/60 rounded-xl border border-dashed border-slate-200">
          指定された条件に一致する高評価論戦が見つかりませんでした。別のジャンルや「任期全体」をお試しください。
        </div>
      )}
    </section>
  );
}