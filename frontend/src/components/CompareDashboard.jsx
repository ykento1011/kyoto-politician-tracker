import React, { useState, useMemo, useEffect } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from 'recharts';
import { 
  ArrowLeft, GitCompare, Share2, Target, BarChart3, MessageCircle, User, 
  Plus, X, Users, Scale, AlertCircle, UserPlus, ArrowUpDown, ArrowUp, ArrowDown, 
  Table, Sparkles, Trophy 
} from 'lucide-react';
import ThreadCard from './ThreadCard';

// 伏見区（12名）などの最大定数に対応する12色カラーパレット
const COMPARE_COLORS = [
  '#6366f1', // 1: Indigo
  '#10b981', // 2: Emerald
  '#f59e0b', // 3: Amber
  '#ec4899', // 4: Pink
  '#0ea5e9', // 5: Sky
  '#8b5cf6', // 6: Violet
  '#f97316', // 7: Orange
  '#14b8a6', // 8: Teal
  '#e11d48', // 9: Rose
  '#84cc16', // 10: Lime
  '#06b6d4', // 11: Cyan
  '#64748b', // 12: Slate
];

const MAX_COMPARE = 12;

const ALIAS_MAP = {
  '井崎敦子': '井﨑敦子',
  '井﨑敦子': '井崎敦子',
  '繁隆夫': '繁隆夫',
  '繁隆夫': '繁隆夫'
};

function SpeakerAvatar({ speakerName }) {
  const cleanName = speakerName ? speakerName.replace(/\s+/g, '') : '';
  const [src, setSrc] = useState(`/councilors/${cleanName}.jpg`);
  const [tried, setTried] = useState(false);
  const [error, setError] = useState(false);

  const handleError = () => {
    if (!tried && ALIAS_MAP[cleanName]) {
      setTried(true);
      setSrc(`/councilors/${ALIAS_MAP[cleanName]}.jpg`);
    } else {
      setError(true);
    }
  };

  return (
    <div className="w-12 h-14 rounded-xl overflow-hidden bg-slate-100 border border-slate-200 shrink-0 flex items-center justify-center shadow-2xs">
      {!error ? (
        <img
          src={src}
          alt={speakerName}
          onError={handleError}
          className="w-full h-full object-cover"
          loading="lazy"
        />
      ) : (
        <User className="w-6 h-6 text-slate-300" />
      )}
    </div>
  );
}

function getVoteForSpeaker(bill, speakerObj) {
  if (!bill || !bill.votes || !speakerObj) return null;
  const votes = bill.votes;
  const spkName = (speakerObj.speaker || '').replace(/[\s ]+/g, '');
  const party = (speakerObj.partyGroup || '').replace(/[\s ]+/g, '');
  const aliasName = ALIAS_MAP[spkName];

  for (const [k, v] of Object.entries(votes)) {
    const cleanK = k.replace(/[\s ]+/g, '');
    if (
      cleanK === spkName || cleanK.includes(spkName) || spkName.includes(cleanK) ||
      (aliasName && (cleanK === aliasName || cleanK.includes(aliasName) || aliasName.includes(cleanK)))
    ) {
      return v;
    }
  }

  if (party) {
    for (const [k, v] of Object.entries(votes)) {
      const cleanK = k.replace(/[\s ]+/g, '');
      if (cleanK === party) return v;
    }
    const coreParty = party.replace(/京都市会議員団|市会議員団|議員団|市議団/, '');
    for (const [k, v] of Object.entries(votes)) {
      const cleanK = k.replace(/[\s ]+/g, '').replace(/京都市会議員団|市会議員団|議員団|市議団/, '');
      if (coreParty && cleanK && (cleanK.includes(coreParty) || coreParty.includes(cleanK))) {
        return v;
      }
    }
  }

  return null;
}

export default function CompareDashboard({
  compareList = [],
  allSpeakers = [],
  onAddSpeaker,
  onRemoveSpeaker,
  onClose,
  onViewContext,
  onSpeakerClick,
  votesData = [],
  issuesMap = {},
  onSelectBill
}) {
  const [activeTab, setActiveTab] = useState('style');
  const [internalVotes, setInternalVotes] = useState(votesData || []);

  // 💡 人数が4名以上の場合は初期表示を「ヒートマップ表」にし、2〜3名なら「レーダー」にする
  const [styleViewMode, setStyleViewMode] = useState(compareList.length > 3 ? 'heatmap' : 'radar');

  // 人数が大きく変動した際にビューを最適化
  useEffect(() => {
    if (compareList.length > 3) {
      setStyleViewMode('heatmap');
    }
  }, [compareList.length]);

  // ヒートマップ表のソート状態（デフォルト: 対案・是正の降順）
  const [sortKey, setSortKey] = useState('solution');
  const [sortOrder, setSortOrder] = useState('desc');

  useEffect(() => {
    if (votesData && votesData.length > 0) {
      setInternalVotes(votesData);
    } else {
      fetch('/data/votes_summary.json')
        .then(res => res.ok ? res.json() : [])
        .then(data => setInternalVotes(data))
        .catch(err => console.error("Failed to load votes:", err));
    }
  }, [votesData]);

  const handleShare = async () => {
    const compareNames = compareList.map(s => s.speaker).join(',');
    const url = `${window.location.origin}/?compare=${encodeURIComponent(compareNames)}`;
    const text = `議会のミカタ 京都で ${compareList.map(s => s.speaker).join(' vs ')} の質疑スタイル・注力政策を徹底比較しました！`;

    try {
      if (navigator.share) {
        await navigator.share({ title: '議員ポリシー徹底比較', text, url });
      } else {
        await navigator.clipboard.writeText(`${text}\n${url}`);
        alert('共有用リンクをクリップボードにコピーしました！');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const sameDistrictCandidates = useMemo(() => {
    if (compareList.length === 0 || !allSpeakers.length) return [];
    const baseSpeaker = compareList[0];
    return allSpeakers.filter(s =>
      s.district === baseSpeaker.district &&
      !compareList.some(c => c.speaker === s.speaker)
    );
  }, [compareList, allSpeakers]);

  const handleAddAllDistrict = () => {
    const availableSlots = MAX_COMPARE - compareList.length;
    if (availableSlots <= 0) {
      alert(`比較できる議員は最大${MAX_COMPARE}名までです。`);
      return;
    }
    const toAdd = sameDistrictCandidates.slice(0, availableSlots);
    onAddSpeaker(toAdd);
  };

  const speakersByDistrict = useMemo(() => {
    if (!allSpeakers) return {};
    const map = {};
    allSpeakers.forEach(spk => {
      const d = spk.district || 'その他';
      if (!map[d]) map[d] = [];
      map[d].push(spk);
    });
    return map;
  }, [allSpeakers]);

  const calculateRates = (speaker) => {
    const total = speaker?.statements?.length || 0;
    if (total === 0) return { solution: 0, local: 0, evidence: 0, constructive: 0 };
    return {
      solution: Math.round((speaker.statements.filter(s => s.solution_score >= 4).length / total) * 100),
      local: Math.round((speaker.statements.filter(s => s.local_focus_score >= 4).length / total) * 100),
      evidence: Math.round((speaker.statements.filter(s => s.evidence_score >= 4).length / total) * 100),
      constructive: Math.round((speaker.statements.filter(s => s.constructive_score >= 4).length / total) * 100),
    };
  };

  // 💡 ヒートマップ比較用のリッチデータ構築（スコア・発揮率・総合平均を統合）
  const heatmapRows = useMemo(() => {
    const rows = compareList.map((spk, idx) => {
      const rates = calculateRates(spk);
      const evScore = spk.avg_evidence || 0;
      const solScore = spk.avg_solution || 0;
      const locScore = spk.avg_local_focus || 0;
      const conScore = spk.avg_constructive || 0;
      const overall = Number(((evScore + solScore + locScore + conScore) / 4).toFixed(2));

      return {
        ...spk,
        originalIndex: idx,
        color: COMPARE_COLORS[idx % COMPARE_COLORS.length],
        rates,
        evScore,
        solScore,
        locScore,
        conScore,
        overall
      };
    });

    // ソート処理
    return rows.sort((a, b) => {
      let valA = 0;
      let valB = 0;
      if (sortKey === 'solution') { valA = a.solScore; valB = b.solScore; }
      else if (sortKey === 'evidence') { valA = a.evScore; valB = b.evScore; }
      else if (sortKey === 'local') { valA = a.locScore; valB = b.locScore; }
      else if (sortKey === 'constructive') { valA = a.conScore; valB = b.conScore; }
      else if (sortKey === 'overall') { valA = a.overall; valB = b.overall; }
      else if (sortKey === 'count') { valA = a.count || 0; valB = b.count || 0; }

      return sortOrder === 'desc' ? valB - valA : valA - valB;
    });
  }, [compareList, sortKey, sortOrder]);

  // 各指標の最高値を算出（1位バッジ用）
  const topValues = useMemo(() => {
    if (heatmapRows.length === 0) return {};
    return {
      solution: Math.max(...heatmapRows.map(r => r.solScore)),
      evidence: Math.max(...heatmapRows.map(r => r.evScore)),
      local: Math.max(...heatmapRows.map(r => r.locScore)),
      constructive: Math.max(...heatmapRows.map(r => r.conScore)),
      overall: Math.max(...heatmapRows.map(r => r.overall))
    };
  }, [heatmapRows]);

  const toggleSort = (key) => {
    if (sortKey === key) {
      setSortOrder(prev => (prev === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortKey(key);
      setSortOrder('desc');
    }
  };

  const radarData = useMemo(() => {
    if (compareList.length < 2) return [];
    const subjects = [
      { key: 'avg_evidence', subject: '根拠・データ' },
      { key: 'avg_solution', subject: '対案・是正' },
      { key: 'avg_local_focus', subject: '地域解像度' },
      { key: 'avg_constructive', subject: '議論の進展' },
    ];
    return subjects.map(item => {
      const row = { subject: item.subject, fullMark: 5 };
      compareList.forEach((spk, idx) => { row[`speaker_${idx}`] = spk[item.key] || 0; });
      return row;
    });
  }, [compareList]);

  const portfolios = useMemo(() => {
    return compareList.map(spk => {
      const total = spk.statements?.length || 1;
      const sorted = Object.entries(spk.catCounts || {}).sort((a, b) => b[1] - a[1]);
      const top = sorted.slice(0, 4).map(([name, count]) => ({ name, pct: (count / total) * 100 }));
      const othersPct = sorted.slice(4).reduce((sum, [_, count]) => sum + (count / total) * 100, 0);
      if (othersPct > 0) top.push({ name: 'その他', pct: othersPct });
      return { speaker: spk.speaker, distribution: top };
    });
  }, [compareList]);

  const headToHead = useMemo(() => {
    if (compareList.length < 2) return null;
    const sets = compareList.map(s => new Set(Object.keys(s.catCounts || {})));
    if (sets.length === 0) return null;
    let commonCats = [...sets[0]].filter(cat => sets.slice(1).every(set => set.has(cat)));

    if (commonCats.length === 0) return null;
    const bestCat = commonCats.sort((a, b) => {
      const countA = compareList.reduce((sum, spk) => sum + (spk.catCounts?.[a] || 0), 0);
      const countB = compareList.reduce((sum, spk) => sum + (spk.catCounts?.[b] || 0), 0);
      return countB - countA;
    })[0];

    const threads = compareList.map(spk => {
      const catThreads = (spk.statements || []).filter(s => s.category?.includes(bestCat));
      catThreads.sort((a, b) => {
        const scoreA = (a.evidence_score || 0) + (a.solution_score || 0) + (a.local_focus_score || 0) + (a.constructive_score || 0);
        const scoreB = (b.evidence_score || 0) + (b.solution_score || 0) + (b.local_focus_score || 0) + (b.constructive_score || 0);
        return scoreB - scoreA;
      });
      return { speaker: spk.speaker, thread: catThreads[0] };
    });

    return { category: bestCat, threads };
  }, [compareList]);

  const commonVotes = useMemo(() => {
    const list = internalVotes || [];
    if (compareList.length < 2 || list.length === 0) return [];

    const enriched = list.map(bill => {
      const spkVotes = compareList.map(spk => ({
        speaker: spk.speaker,
        vote: getVoteForSpeaker(bill, spk)
      }));

      const vValues = Object.values(bill.votes || {});
      const isContested = vValues.includes('賛成') && vValues.includes('反対');
      const validVotes = spkVotes.map(s => s.vote).filter(Boolean);
      const isSplitBetweenSelected = validVotes.includes('賛成') && validVotes.includes('反対');
      const hasAnyVote = validVotes.length > 0;

      return {
        ...bill,
        spkVotes,
        isContested,
        isSplitBetweenSelected,
        hasAnyVote
      };
    });

    let result = enriched.filter(b => b.hasAnyVote && (b.isContested || b.isSplitBetweenSelected));
    if (result.length === 0) result = enriched.filter(b => b.hasAnyVote);

    result.sort((a, b) => {
      if (a.isSplitBetweenSelected && !b.isSplitBetweenSelected) return -1;
      if (!a.isSplitBetweenSelected && b.isSplitBetweenSelected) return 1;
      return (b.session_name || '').localeCompare(a.session_name || '');
    });

    return result;
  }, [compareList, internalVotes]);

  // ヒートマップセルのカラー計算ヘルパー
  const getCellBg = (score) => {
    if (score >= 4.0) return 'bg-indigo-600/20 text-indigo-950 font-black';
    if (score >= 3.6) return 'bg-indigo-500/15 text-indigo-900 font-bold';
    if (score >= 3.2) return 'bg-indigo-500/10 text-slate-800 font-medium';
    if (score >= 2.8) return 'bg-slate-100/80 text-slate-700';
    return 'bg-slate-50 text-slate-400';
  };

  return (
    <main className="max-w-6xl mx-auto py-8 px-6 animate-in fade-in slide-in-from-bottom-4 duration-300 w-full">

      <div className="flex items-center justify-between mb-6">
        <button
          onClick={onClose}
          className="inline-flex items-center text-xs font-bold text-slate-500 hover:text-indigo-600 transition-colors bg-white px-3 py-2 rounded-lg border border-slate-200 shadow-sm cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />一覧に戻る
        </button>
        <button
          onClick={handleShare}
          disabled={compareList.length < 2}
          className={`inline-flex items-center text-xs font-bold text-white transition-colors px-4 py-2 rounded-lg shadow-md ${compareList.length >= 2 ? 'bg-slate-900 hover:bg-slate-800 cursor-pointer' : 'bg-slate-400 cursor-not-allowed opacity-60'}`}
        >
          <Share2 className="w-3.5 h-3.5 mr-1.5" />この比較をシェア
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">

        <div className="p-6 md:p-8 bg-slate-50/50 border-b border-slate-100">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-600">
              <GitCompare className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-black text-slate-900">議員ポリシー徹底比較</h2>
              <p className="text-xs text-slate-500 font-medium">
                議場でのアプローチと注力政策の違い（伏見区など最大{MAX_COMPARE}名まで同時比較可能）
              </p>
            </div>
          </div>

          {/* 議員スロット一覧 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {compareList.map((spk, idx) => (
              <div key={spk.speaker} className="p-4 rounded-2xl bg-white border border-slate-200 shadow-sm relative overflow-hidden group flex flex-col justify-between">
                <div className="absolute top-0 left-0 w-1.5 h-full" style={{ backgroundColor: COMPARE_COLORS[idx % COMPARE_COLORS.length] }} />

                <div>
                  <div className="flex items-start gap-3 mb-2.5">
                    <SpeakerAvatar speakerName={spk.speaker} />

                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between">
                        <h3 className="text-base font-black text-slate-900 truncate leading-snug">{spk.speaker}</h3>
                        <div className="flex items-center gap-1 shrink-0 ml-1">
                          <button onClick={() => onSpeakerClick(spk.speaker)} className="w-6 h-6 rounded-full bg-slate-50 hover:bg-indigo-50 text-slate-400 hover:text-indigo-600 flex items-center justify-center transition-colors border border-slate-200 cursor-pointer" title="詳細ページへ"><User className="w-3 h-3" /></button>
                          <button onClick={() => onRemoveSpeaker(spk)} className="w-6 h-6 rounded-full bg-slate-50 hover:bg-rose-50 text-slate-400 hover:text-rose-600 flex items-center justify-center transition-colors border border-slate-200 cursor-pointer" title="比較から外す"><X className="w-3 h-3" /></button>
                        </div>
                      </div>
                      <div className="text-[10px] font-bold text-slate-500 truncate mt-0.5">
                        {spk.district} / <span className="text-slate-400">{spk.partyGroup}</span>
                      </div>
                      <div className={`px-1.5 py-0.2 text-[9px] font-bold rounded border inline-block mt-1 ${spk.style?.badgeClass}`}>
                        {spk.style?.label}
                      </div>
                    </div>
                  </div>

                  <div className="text-[10px] text-slate-500 font-medium leading-relaxed line-clamp-2">
                    {spk.style?.desc}
                  </div>
                </div>

                <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[10px] font-bold text-slate-400">
                  <span>質疑: {spk.count}件</span>
                  <span className="font-mono font-black" style={{ color: COMPARE_COLORS[idx % COMPARE_COLORS.length] }}>#{idx + 1}</span>
                </div>
              </div>
            ))}

            {/* 議員追加枠 */}
            {compareList.length < MAX_COMPARE && (
              <div className="p-4 rounded-2xl bg-white border-2 border-dashed border-indigo-200 hover:border-indigo-300 transition-colors flex flex-col justify-between shadow-2xs">
                <div>
                  <div className="flex items-center gap-1.5 text-indigo-700 font-black text-xs mb-1">
                    <Plus className="w-3.5 h-3.5" />
                    <span>比較相手の議員を追加（残り{MAX_COMPARE - compareList.length}名）</span>
                  </div>

                  {sameDistrictCandidates.length > 0 && (
                    <div className="mb-3">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-extrabold text-slate-400 flex items-center gap-1">
                          <Users className="w-3 h-3 text-indigo-500" />
                          同じ【{compareList[0]?.district}】の議員:
                        </span>
                        <button
                          onClick={handleAddAllDistrict}
                          className="text-[10px] font-black text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-2 py-0.5 rounded border border-indigo-200 transition-all flex items-center gap-1 cursor-pointer"
                          title="同じ区の議員を枠の空き分だけまとめて追加"
                        >
                          <UserPlus className="w-2.5 h-2.5" />
                          <span>同区全員追加</span>
                        </button>
                      </div>

                      <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto pr-1">
                        {sameDistrictCandidates.map(candidate => (
                          <button key={candidate.speaker} onClick={() => onAddSpeaker(candidate)} className="px-2 py-0.5 rounded-md bg-indigo-50 hover:bg-indigo-600 hover:text-white text-indigo-700 text-[11px] font-bold transition-all border border-indigo-200/80 flex items-center gap-1 cursor-pointer group">
                            <span>+ {candidate.speaker}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-2 pt-2 border-t border-slate-100">
                  <span className="text-[10px] font-extrabold text-slate-400 block mb-1">全議員から選択:</span>
                  <select onChange={(e) => { if (!e.target.value) return; const target = allSpeakers.find(s => s.speaker === e.target.value); if (target) onAddSpeaker(target); e.target.value = ''; }} className="w-full bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-bold text-slate-700 outline-none cursor-pointer transition-colors" defaultValue="">
                    <option value="" disabled>議員名を選択...</option>
                    {Object.entries(speakersByDistrict).map(([district, spkList]) => (
                      <optgroup key={district} label={district}>
                        {spkList.filter(s => !compareList.some(c => c.speaker === s.speaker)).map(s => (
                          <option key={s.speaker} value={s.speaker}>{s.speaker} ({s.partyGroup?.replace(/京都市会議員団|議員団/, '')})</option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>
        </div>

        {compareList.length < 2 ? (
          <div className="p-12 text-center bg-slate-50 min-h-[400px] flex flex-col items-center justify-center space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600"><GitCompare className="w-6 h-6" /></div>
            <h3 className="text-base font-extrabold text-slate-800">比較する相手の議員を選択してください</h3>
            <p className="text-xs text-slate-500 max-w-md leading-relaxed">
              上の枠から「同区全員追加」や候補議員をクリックすると、4軸ポリシーマトリクスや注力政策の直接突き合わせが自動表示されます。
            </p>
          </div>
        ) : (
          <>
            <div className="flex overflow-x-auto border-b border-slate-200 bg-white hide-scrollbar">
              <button onClick={() => setActiveTab('style')} className={`px-6 py-4 text-sm font-bold flex items-center whitespace-nowrap transition-colors border-b-2 cursor-pointer ${activeTab === 'style' ? 'border-indigo-600 text-indigo-700 bg-indigo-50/30' : 'border-transparent text-slate-500 hover:bg-slate-50'}`}>
                <Target className="w-4 h-4 mr-2" />アプローチと強み
              </button>
              <button onClick={() => setActiveTab('portfolio')} className={`px-6 py-4 text-sm font-bold flex items-center whitespace-nowrap transition-colors border-b-2 cursor-pointer ${activeTab === 'portfolio' ? 'border-indigo-600 text-indigo-700 bg-indigo-50/30' : 'border-transparent text-slate-500 hover:bg-slate-50'}`}>
                <BarChart3 className="w-4 h-4 mr-2" />注力政策ポートフォリオ
              </button>
              <button onClick={() => setActiveTab('head2head')} className={`px-6 py-4 text-sm font-bold flex items-center whitespace-nowrap transition-colors border-b-2 cursor-pointer ${activeTab === 'head2head' ? 'border-indigo-600 text-indigo-700 bg-indigo-50/30' : 'border-transparent text-slate-500 hover:bg-slate-50'}`}>
                <MessageCircle className="w-4 h-4 mr-2" />代表質疑 突き合わせ
              </button>
              <button onClick={() => setActiveTab('bills')} className={`px-6 py-4 text-sm font-bold flex items-center whitespace-nowrap transition-colors border-b-2 cursor-pointer ${activeTab === 'bills' ? 'border-indigo-600 text-indigo-700 bg-indigo-50/30' : 'border-transparent text-slate-500 hover:bg-slate-50'}`}>
                <Scale className="w-4 h-4 mr-2" />議案・賛否の比較
              </button>
            </div>

            <div className="p-6 md:p-8 bg-slate-50 min-h-[500px]">

              {/* ① アプローチと強み */}
              {activeTab === 'style' && (
                <div className="space-y-6 animate-in fade-in">
                  
                  {/* 表示切り替えコントロールバー */}
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                    <div>
                      <h4 className="text-sm font-black text-slate-800">
                        {styleViewMode === 'heatmap' ? '4軸アプローチ比較マトリクス（ランキング表）' : '4軸レーダー重ね合わせ'}
                      </h4>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {styleViewMode === 'heatmap'
                          ? '列名をクリックすると各分野のランキング順に並び替えできます（色の濃さはスコアの高さに対応）'
                          : '平均スコアの面積差から、全体的なスタイルの違いを把握できます'}
                      </p>
                    </div>

                    <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 shrink-0">
                      <button
                        onClick={() => setStyleViewMode('heatmap')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                          styleViewMode === 'heatmap' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-slate-500 hover:text-slate-700'
                        }`}
                      >
                        <Table className="w-3.5 h-3.5" />
                        <span>ヒートマップ表</span>
                      </button>
                      <button
                        onClick={() => setStyleViewMode('radar')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                          styleViewMode === 'radar' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-slate-500 hover:text-slate-700'
                        }`}
                      >
                        <Target className="w-3.5 h-3.5" />
                        <span>レーダー重ね合わせ</span>
                      </button>
                    </div>
                  </div>

                  {/* 💡 案A: 4軸ヒートマップ・ランキングマトリクス */}
                  {styleViewMode === 'heatmap' && (
                    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden animate-in fade-in">
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs whitespace-nowrap">
                          <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-extrabold uppercase tracking-wider">
                            <tr>
                              <th className="px-5 py-4 min-w-[200px] sticky left-0 bg-slate-50 z-10">
                                議員名 / 会派
                              </th>
                              
                              {[
                                { key: 'solution', label: '対案・是正の提示', desc: '具体的改善策' },
                                { key: 'evidence', label: '根拠・データ活用', desc: 'ファクト重視' },
                                { key: 'local', label: '地域課題の解像度', desc: '現場・市民の声' },
                                { key: 'constructive', label: '議論の進展力', desc: '行政監視・追及' },
                                { key: 'overall', label: '4軸総合平均', desc: 'バランス' },
                              ].map(col => {
                                const isActive = sortKey === col.key;
                                return (
                                  <th
                                    key={col.key}
                                    onClick={() => toggleSort(col.key)}
                                    className={`px-4 py-3.5 text-center cursor-pointer transition-colors hover:bg-indigo-50/60 min-w-[130px] border-l border-slate-100 ${
                                      isActive ? 'bg-indigo-50/80 text-indigo-900 font-black' : ''
                                    }`}
                                  >
                                    <div className="inline-flex items-center gap-1">
                                      <span>{col.label}</span>
                                      {isActive ? (
                                        sortOrder === 'desc' ? <ArrowDown className="w-3.5 h-3.5 text-indigo-600" /> : <ArrowUp className="w-3.5 h-3.5 text-indigo-600" />
                                      ) : (
                                        <ArrowUpDown className="w-3 h-3 text-slate-300 opacity-60" />
                                      )}
                                    </div>
                                    <span className="block text-[10px] font-medium text-slate-400 mt-0.5">{col.desc}</span>
                                  </th>
                                );
                              })}
                            </tr>
                          </thead>

                          <tbody className="divide-y divide-slate-100 font-medium">
                            {heatmapRows.map((row) => (
                              <tr key={row.speaker} className="hover:bg-slate-50/80 transition-colors group">
                                
                                {/* 議員情報 */}
                                <td className="px-5 py-3 sticky left-0 bg-white group-hover:bg-slate-50/80 z-10 border-r border-slate-100">
                                  <div className="flex items-center gap-3">
                                    <div className="w-1.5 h-10 rounded-full shrink-0" style={{ backgroundColor: row.color }} />
                                    <div className="w-9 h-11 rounded-lg overflow-hidden bg-slate-100 border border-slate-200 shrink-0">
                                      <img
                                        src={`/councilors/${(row.speaker || '').replace(/\s+/g, '')}.jpg`}
                                        alt={row.speaker}
                                        className="w-full h-full object-cover"
                                        onError={(e) => { e.target.style.display = 'none'; }}
                                      />
                                    </div>
                                    <div className="min-w-0">
                                      <button
                                        onClick={() => onSpeakerClick(row.speaker)}
                                        className="font-black text-slate-900 hover:text-indigo-600 transition-colors text-sm text-left truncate block cursor-pointer"
                                      >
                                        {row.speaker}
                                      </button>
                                      <div className="text-[10px] text-slate-400 truncate mt-0.5">
                                        {row.district} / {row.partyGroup}
                                      </div>
                                    </div>
                                  </div>
                                </td>

                                {/* 1. 対案・是正 */}
                                <td className={`px-4 py-3 text-center border-l border-slate-100 ${getCellBg(row.solScore)}`}>
                                  <div className="flex flex-col items-center justify-center">
                                    <div className="flex items-center gap-1">
                                      <span className="text-sm font-black font-mono">{row.solScore.toFixed(2)}</span>
                                      {row.solScore === topValues.solution && (
                                        <span className="px-1 py-0.2 rounded bg-amber-400 text-amber-950 text-[9px] font-black inline-flex items-center gap-0.5 shadow-2xs">
                                          <Trophy className="w-2.5 h-2.5" /> 1位
                                        </span>
                                      )}
                                    </div>
                                    <span className="text-[10px] text-slate-500 font-bold mt-0.5">
                                      発揮率 {row.rates.solution}%
                                    </span>
                                  </div>
                                </td>

                                {/* 2. 根拠・データ */}
                                <td className={`px-4 py-3 text-center border-l border-slate-100 ${getCellBg(row.evScore)}`}>
                                  <div className="flex flex-col items-center justify-center">
                                    <div className="flex items-center gap-1">
                                      <span className="text-sm font-black font-mono">{row.evScore.toFixed(2)}</span>
                                      {row.evScore === topValues.evidence && (
                                        <span className="px-1 py-0.2 rounded bg-amber-400 text-amber-950 text-[9px] font-black inline-flex items-center gap-0.5 shadow-2xs">
                                          <Trophy className="w-2.5 h-2.5" /> 1位
                                        </span>
                                      )}
                                    </div>
                                    <span className="text-[10px] text-slate-500 font-bold mt-0.5">
                                      発揮率 {row.rates.evidence}%
                                    </span>
                                  </div>
                                </td>

                                {/* 3. 地域課題の解像度 */}
                                <td className={`px-4 py-3 text-center border-l border-slate-100 ${getCellBg(row.locScore)}`}>
                                  <div className="flex flex-col items-center justify-center">
                                    <div className="flex items-center gap-1">
                                      <span className="text-sm font-black font-mono">{row.locScore.toFixed(2)}</span>
                                      {row.locScore === topValues.local && (
                                        <span className="px-1 py-0.2 rounded bg-amber-400 text-amber-950 text-[9px] font-black inline-flex items-center gap-0.5 shadow-2xs">
                                          <Trophy className="w-2.5 h-2.5" /> 1位
                                        </span>
                                      )}
                                    </div>
                                    <span className="text-[10px] text-slate-500 font-bold mt-0.5">
                                      発揮率 {row.rates.local}%
                                    </span>
                                  </div>
                                </td>

                                {/* 4. 議論の進展力 */}
                                <td className={`px-4 py-3 text-center border-l border-slate-100 ${getCellBg(row.conScore)}`}>
                                  <div className="flex flex-col items-center justify-center">
                                    <div className="flex items-center gap-1">
                                      <span className="text-sm font-black font-mono">{row.conScore.toFixed(2)}</span>
                                      {row.conScore === topValues.constructive && (
                                        <span className="px-1 py-0.2 rounded bg-amber-400 text-amber-950 text-[9px] font-black inline-flex items-center gap-0.5 shadow-2xs">
                                          <Trophy className="w-2.5 h-2.5" /> 1位
                                        </span>
                                      )}
                                    </div>
                                    <span className="text-[10px] text-slate-500 font-bold mt-0.5">
                                      発揮率 {row.rates.constructive}%
                                    </span>
                                  </div>
                                </td>

                                {/* 5. 4軸総合平均 */}
                                <td className="px-4 py-3 text-center border-l border-slate-100 bg-slate-50/50">
                                  <div className="flex items-center justify-center gap-1">
                                    <span className="text-sm font-black text-slate-900 font-mono">{row.overall.toFixed(2)}</span>
                                    {row.overall === topValues.overall && (
                                      <span className="px-1 py-0.2 rounded bg-amber-100 text-amber-800 text-[9px] font-bold">
                                        最高
                                      </span>
                                    )}
                                  </div>
                                </td>

                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* 従来のレーダーチャート重ね合わせ（手動切り替え可能） */}
                  {styleViewMode === 'radar' && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-in fade-in">
                      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                        <h4 className="text-sm font-extrabold text-slate-800 mb-2">4軸レーダー重ね合わせ</h4>
                        <p className="text-[11px] text-slate-500 mb-4">平均スコアの面積差から、全体的なスタイルの違いを把握できます。</p>
                        <div className="w-full h-80">
                          <ResponsiveContainer width="100%" height="100%">
                            <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                              <PolarGrid stroke="#cbd5e1" />
                              <PolarAngleAxis dataKey="subject" tick={{ fill: '#334155', fontSize: 11, fontWeight: 700 }} />
                              <PolarRadiusAxis domain={[0, 5]} tick={false} axisLine={false} />
                              {compareList.map((spk, idx) => (
                                <Radar
                                  key={spk.speaker}
                                  name={spk.speaker}
                                  dataKey={`speaker_${idx}`}
                                  stroke={COMPARE_COLORS[idx % COMPARE_COLORS.length]}
                                  strokeWidth={2}
                                  fill={COMPARE_COLORS[idx % COMPARE_COLORS.length]}
                                  fillOpacity={0.1}
                                />
                              ))}
                              <Legend />
                            </RadarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <h4 className="text-sm font-extrabold text-slate-800">強み発揮率（アプローチの確率）</h4>
                        <p className="text-[11px] text-slate-500 mb-6">
                          登壇時に、そのアプローチ（スコア4以上）をどれくらいの確率で取るかを示します。<br />
                          ※点数ではなく、「どのような手法を好むか」の比較に役立ちます。
                        </p>

                        {[
                          { key: 'solution', label: '具体的対案の提示率' },
                          { key: 'local', label: '現場課題の代弁率' },
                          { key: 'evidence', label: '客観データの活用率' },
                          { key: 'constructive', label: '行政への鋭い追及率' },
                        ].map(metric => (
                          <div key={metric.key} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                            <div className="text-xs font-bold text-slate-700 mb-3">{metric.label}</div>
                            <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
                              {compareList.map((spk, idx) => {
                                const rate = calculateRates(spk)[metric.key];
                                return (
                                  <div key={spk.speaker} className="flex items-center gap-2.5">
                                    <span className="w-20 text-[10px] font-bold text-slate-600 truncate text-right">{spk.speaker}</span>
                                    <div className="flex-1 bg-slate-100 h-2.5 rounded-full overflow-hidden flex">
                                      <div
                                        className="h-full rounded-full transition-all duration-500"
                                        style={{ width: `${rate}%`, backgroundColor: COMPARE_COLORS[idx % COMPARE_COLORS.length] }}
                                      />
                                    </div>
                                    <span className="w-8 text-[11px] font-black text-slate-700 text-right font-mono">{rate}%</span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                </div>
              )}

              {/* ② 注力政策ポートフォリオ */}
              {activeTab === 'portfolio' && (
                <div className="space-y-6 animate-in fade-in max-w-4xl mx-auto">
                  <div className="text-center mb-6">
                    <h4 className="text-base font-extrabold text-slate-800 mb-2">発言時間の投下ポートフォリオ</h4>
                    <p className="text-xs text-slate-500">
                      全質疑の中で、どの政策分野に最も多くエネルギー（発言機会）を割いているかを帯グラフで比較します。
                    </p>
                  </div>

                  {portfolios.map((port, idx) => (
                    <div key={port.speaker} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
                      <div className="absolute left-0 top-0 w-1.5 h-full" style={{ backgroundColor: COMPARE_COLORS[idx % COMPARE_COLORS.length] }} />
                      <div className="flex items-center gap-2 mb-3 ml-2">
                        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COMPARE_COLORS[idx % COMPARE_COLORS.length] }} />
                        <h5 className="text-sm font-black text-slate-800">{port.speaker} 議員</h5>
                      </div>

                      <div className="w-full h-7 rounded-lg overflow-hidden flex mb-2.5 shadow-inner bg-slate-100">
                        {port.distribution.map((item, i) => {
                          const alpha = 1 - (i * 0.15);
                          return (
                            <div key={item.name} className="h-full flex items-center justify-center hover:opacity-80 transition-opacity relative group" style={{ width: `${item.pct}%`, backgroundColor: COMPARE_COLORS[idx % COMPARE_COLORS.length], opacity: alpha }}>
                              {item.pct > 10 && <span className="text-[9px] font-bold text-white truncate px-1">{item.name}</span>}
                            </div>
                          );
                        })}
                      </div>

                      <div className="flex flex-wrap gap-x-3 gap-y-1 ml-2">
                        {port.distribution.map((item, i) => (
                          <div key={item.name} className="flex items-center gap-1">
                            <span className="text-[10px] font-bold text-slate-600">{item.name} <span className="text-slate-400 font-medium">({item.pct.toFixed(1)}%)</span></span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* ③ 代表質疑 突き合わせ */}
              {activeTab === 'head2head' && (
                <div className="animate-in fade-in">
                  {!headToHead ? (
                    <div className="text-center py-20 bg-white rounded-2xl border border-dashed border-slate-300">
                      <p className="text-slate-500 font-bold">比較対象の議員間で、共通して質疑が行われた政策分野が見つかりませんでした。</p>
                    </div>
                  ) : (
                    <>
                      <div className="text-center mb-8">
                        <h4 className="text-base font-extrabold text-slate-800 mb-2">代表質疑 直接突き合わせ</h4>
                        <p className="text-xs text-slate-500 max-w-2xl mx-auto leading-relaxed">
                          共通して登壇数の多い分野 <strong className="text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">【{headToHead.category}】</strong> における、各議員の最も評価の高い質疑スレッドを並べました。
                        </p>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {headToHead.threads.map((item, idx) => (
                          <div key={item.speaker} className="flex flex-col relative pt-4">
                            <div className="absolute top-0 left-4 px-3 py-1 rounded-t-lg text-[11px] font-black text-white shadow-sm z-10" style={{ backgroundColor: COMPARE_COLORS[idx % COMPARE_COLORS.length] }}>
                              {item.speaker} のアプローチ
                            </div>
                            {item.thread ? (
                              <div className="flex-1 border-2 rounded-2xl rounded-tl-none overflow-hidden bg-white shadow-sm" style={{ borderColor: COMPARE_COLORS[idx % COMPARE_COLORS.length] }}>
                                <ThreadCard stmt={item.thread} onSpeakerClick={() => { }} onViewContext={onViewContext} showSpeakerHeader={false} />
                              </div>
                            ) : (
                              <div className="flex-1 border-2 border-slate-200 border-dashed rounded-2xl rounded-tl-none bg-white p-6 text-center text-slate-400 text-xs">該当データなし</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* ④ 議案・賛否の比較 */}
              {activeTab === 'bills' && (
                <div className="animate-in fade-in max-w-6xl mx-auto space-y-4">
                  <div className="text-center mb-4">
                    <h4 className="text-base font-extrabold text-slate-800 mb-1">議案に対する賛否スタンスの違い</h4>
                    <p className="text-xs text-slate-500">
                      議案をクリックすると、AI争点解説や各会派の投票状況を確認できます。
                    </p>
                  </div>

                  {commonVotes.length === 0 ? (
                    <div className="text-center py-20 bg-white rounded-2xl border border-dashed border-slate-300 space-y-2">
                      <AlertCircle className="w-8 h-8 text-slate-400 mx-auto" />
                      <p className="text-slate-600 font-bold">比較対象の議員に関する投票記録を読み込み中、または該当がありません。</p>
                    </div>
                  ) : (
                    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm whitespace-nowrap">
                          <thead className="bg-slate-50 border-b border-slate-200 text-[11px] font-black text-slate-500 uppercase tracking-wider">
                            <tr>
                              <th className="px-5 py-3.5 sticky left-0 bg-slate-50 z-10 min-w-[300px]">
                                議案名
                              </th>
                              {compareList.map((spk, idx) => (
                                <th key={spk.speaker} className="px-4 py-3.5 text-center min-w-[100px]" style={{ color: COMPARE_COLORS[idx % COMPARE_COLORS.length] }}>
                                  {spk.speaker}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {commonVotes.map(bill => (
                              <tr 
                                key={`${bill.session_name}_${bill.bill_number}`}
                                onClick={() => onSelectBill && onSelectBill(bill)}
                                className="hover:bg-indigo-50/40 transition-colors cursor-pointer group"
                              >
                                <td className="px-5 py-3.5 whitespace-normal sticky left-0 bg-white group-hover:bg-indigo-50/40 z-10">
                                  <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                                    <span className="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px] font-bold">{bill.session_name}</span>
                                    <span className="text-[10px] font-bold text-slate-400">{bill.bill_number}</span>
                                  </div>
                                  <div className="font-bold text-slate-800 text-xs leading-snug group-hover:text-indigo-600 transition-colors" title={bill.title}>
                                    {bill.title}
                                  </div>
                                </td>
                                
                                {compareList.map(spk => {
                                  const voteItem = bill.spkVotes?.find(sv => sv.speaker === spk.speaker);
                                  const vote = voteItem?.vote;
                                  
                                  let badgeClass = "bg-slate-100 text-slate-400 border-slate-200";
                                  if (vote === '賛成') badgeClass = "bg-emerald-50 text-emerald-700 border-emerald-200 shadow-2xs font-black";
                                  if (vote === '反対') badgeClass = "bg-rose-50 text-rose-700 border-rose-200 shadow-2xs font-black";
                                  
                                  return (
                                    <td key={spk.speaker} className="px-4 py-3.5 text-center border-l border-slate-50 group-hover:border-indigo-50/40">
                                      {vote ? (
                                        <span className={`px-2 py-0.5 rounded-md text-xs border inline-block min-w-[48px] ${badgeClass}`}>
                                          {vote}
                                        </span>
                                      ) : (
                                        <span className="text-[10px] text-slate-400 font-bold bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100">
                                          -
                                        </span>
                                      )}
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}

            </div>
          </>
        )}
      </div>
    </main>
  );
}