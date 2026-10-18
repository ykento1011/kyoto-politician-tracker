import React, { useMemo, useState } from 'react';
import { 
  Sparkles, Target, MapPin, Database, TrendingUp, 
  Shuffle, BookOpen, ChevronDown, ChevronUp, CheckCircle2 
} from 'lucide-react';
import ThreadCard from './ThreadCard';
import { cleanName } from '../utils/styleHelpers';

// 💡 今日の日付文字列（YYYY-MM-DD）から決まるシード付き乱数生成
function getDailyRng() {
  const todayStr = new Date().toISOString().slice(0, 10);
  let h = 0;
  for (let i = 0; i < todayStr.length; i++) {
    h = Math.imul(31, h) + todayStr.charCodeAt(i) | 0;
  }
  return function() {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return ((h ^= h >>> 16) >>> 0) / 4294967296;
  };
}

export default function HighlightedThreads({ 
  statements = [], 
  onSpeakerClick, 
  onViewContext, 
  onOpenMethodology 
}) {
  // 💡 初期状態は折りたたんで場所を取らない（クリックで開閉）
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('solution');

  // 4つの観点ごとにハイスコアプールから日替わりで1件ずつ抽出
  const highlights = useMemo(() => {
    if (!statements || statements.length === 0) return {};

    const rng = getDailyRng();

    const criteriaList = [
      { key: 'solution', scoreKey: 'solution_score', minScore: 4 },
      { key: 'local', scoreKey: 'local_focus_score', minScore: 4 },
      { key: 'evidence', scoreKey: 'evidence_score', minScore: 4 },
      { key: 'constructive', scoreKey: 'constructive_score', minScore: 4 },
    ];

    const result = {};
    const usedSpeakers = new Set();

    criteriaList.forEach(({ key, scoreKey, minScore }) => {
      let pool = statements.filter(s => (s[scoreKey] || 0) >= 5);
      if (pool.length < 3) {
        pool = statements.filter(s => (s[scoreKey] || 0) >= minScore);
      }
      if (pool.length === 0) pool = [...statements];

      let nonOverlappingPool = pool.filter(s => !usedSpeakers.has(cleanName(s.speaker)));
      const finalPool = nonOverlappingPool.length > 0 ? nonOverlappingPool : pool;

      const randomIndex = Math.floor(rng() * finalPool.length);
      const picked = finalPool[randomIndex] || pool[0];

      if (picked) {
        result[key] = picked;
        usedSpeakers.add(cleanName(picked.speaker));
      }
    });

    return result;
  }, [statements]);

  const tabs = [
    { 
      key: 'solution', 
      label: '具体的対案の提示', 
      shortLabel: '対案',
      icon: Target, 
      desc: '問題点の指摘にとどまらず、実現可能な代案や制度改善を提案した質疑',
      colorClass: 'text-emerald-700 bg-emerald-50 border-emerald-200' 
    },
    { 
      key: 'local', 
      label: '現場解像度・市民の声', 
      shortLabel: '現場',
      icon: MapPin, 
      desc: '地域の切実な困りごとや現場当事者の実態に根ざした質疑',
      colorClass: 'text-amber-700 bg-amber-50 border-amber-200' 
    },
    { 
      key: 'evidence', 
      label: '客観データ・根拠', 
      shortLabel: 'データ',
      icon: Database, 
      desc: '統計数字、他都市の先行事例、公的データを根拠に展開した質疑',
      colorClass: 'text-indigo-700 bg-indigo-50 border-indigo-200' 
    },
    { 
      key: 'constructive', 
      label: '行政監視・議論の進展', 
      shortLabel: '進展',
      icon: TrendingUp, 
      desc: '市側の答弁の論理の穴を突き、新たな見解や前向きな答弁を引き出した質疑',
      colorClass: 'text-rose-700 bg-rose-50 border-rose-200' 
    },
  ];

  const currentTabInfo = tabs.find(t => t.key === activeTab) || tabs[0];
  const activeStatement = highlights[activeTab];

  if (!activeStatement) return null;

  return (
    <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden transition-all duration-300">
      
      {/* 💡 常駐表示されるコンパクトなトリガーバー */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="p-4 md:px-6 md:py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 cursor-pointer hover:bg-slate-50/80 transition-colors select-none"
      >
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 text-xs font-black px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200 shrink-0">
              <Sparkles className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
              注目の政策論戦ピックアップ
            </span>
            <span className="text-[10px] font-bold text-slate-400 hidden sm:inline-flex items-center gap-1">
              <Shuffle className="w-3 h-3 text-slate-400" />
              日替わり選出
            </span>
          </div>

          {/* 閉じた状態でも選ばれた議員名がひと目でわかるミニバッジ */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {tabs.map(t => {
              const spk = highlights[t.key]?.speaker;
              if (!spk) return null;
              return (
                <span key={t.key} className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 border border-slate-200/80">
                  <span className="text-slate-400 mr-1">{t.shortLabel}:</span>{spk}
                </span>
              );
            })}
          </div>
        </div>

        {/* 開閉ボタン */}
        <div className="flex items-center gap-2 text-xs font-bold text-indigo-600 shrink-0 self-end md:self-auto">
          <span>{isOpen ? 'ピックアップを閉じる' : '質疑を見る'}</span>
          <div className="w-6 h-6 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600 border border-indigo-100">
            {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </div>
      </div>

      {/* 💡 クリック時にのみアコーディオン展開されるコンテンツ */}
      {isOpen && (
        <div className="p-6 pt-4 border-t border-slate-100 bg-slate-50/30 space-y-5 animate-in fade-in duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <p className="text-xs text-slate-500 font-medium leading-relaxed">
              AI評価で各観点（スコア4〜5）に輝いた質疑ログから、公平性を期して日替わりでローテーション紹介しています。
            </p>

            {onOpenMethodology && (
              <button
                onClick={(e) => { e.stopPropagation(); onOpenMethodology(); }}
                className="text-[11px] font-bold text-slate-500 hover:text-indigo-600 transition-colors inline-flex items-center gap-1 self-start sm:self-auto shrink-0 bg-white hover:bg-slate-100 px-2.5 py-1.5 rounded-lg border border-slate-200 cursor-pointer"
              >
                <BookOpen className="w-3.5 h-3.5 text-indigo-500" />
                <span>AI採点基準について</span>
              </button>
            )}
          </div>

          {/* 4つの観点タブセレクター */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isSelected = activeTab === tab.key;
              const targetStmt = highlights[tab.key];

              return (
                <button
                  key={tab.key}
                  onClick={(e) => { e.stopPropagation(); setActiveTab(tab.key); }}
                  className={`p-3 rounded-xl border text-left transition-all flex flex-col justify-between cursor-pointer ${
                    isSelected
                      ? 'bg-white border-indigo-400 shadow-sm ring-2 ring-indigo-500/20'
                      : 'bg-white hover:bg-slate-50 border-slate-200/80 hover:border-indigo-200'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className={`p-1.5 rounded-lg ${isSelected ? 'bg-indigo-50 text-indigo-600' : 'bg-slate-100 text-slate-600'}`}>
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      {targetStmt && (
                        <span className="text-[10px] font-black text-slate-700 truncate max-w-[80px]">
                          {targetStmt.speaker}
                        </span>
                      )}
                    </div>
                    <div className={`text-xs font-black leading-snug ${isSelected ? 'text-indigo-900' : 'text-slate-700'}`}>
                      {tab.label}
                    </div>
                  </div>

                  <div className="mt-2 text-[10px] text-slate-400 font-medium truncate">
                    {targetStmt ? `${targetStmt.meeting_date}・${targetStmt.meeting_title?.slice(0, 10)}...` : ''}
                  </div>
                </button>
              );
            })}
          </div>

          {/* 選択された観点の解説とThreadCard */}
          <div className="space-y-3 pt-1">
            <div className="bg-white p-3 rounded-xl border border-slate-200/80 flex items-start gap-2.5 shadow-2xs">
              <currentTabInfo.icon className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
              <div className="text-xs">
                <span className="font-black text-slate-800 mr-2">{currentTabInfo.label}：</span>
                <span className="text-slate-600 font-medium">{currentTabInfo.desc}</span>
              </div>
            </div>

            <ThreadCard
              stmt={activeStatement}
              onSpeakerClick={onSpeakerClick}
              onViewContext={onViewContext}
              showSpeakerHeader={true}
              onOpenMethodology={onOpenMethodology}
            />
          </div>
        </div>
      )}
    </section>
  );
}