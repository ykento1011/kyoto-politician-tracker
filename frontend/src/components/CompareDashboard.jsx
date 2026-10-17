import React, { useState, useMemo } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from 'recharts';
import { ArrowLeft, GitCompare, Share2, Target, BarChart3, MessageCircle, User } from 'lucide-react';
import { cleanName } from '../utils/styleHelpers';
import ThreadCard from './ThreadCard';

const COMPARE_COLORS = ['#6366f1', '#10b981', '#f59e0b']; // Indigo, Emerald, Amber

export default function CompareDashboard({
  compareList,
  onClose,
  onViewContext,
  onSpeakerClick
}) {
  const [activeTab, setActiveTab] = useState('style');

  // SNS共有機能
  const handleShare = async () => {
    const url = window.location.href;
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

  // 1. 強み発揮率（%）の計算
  const calculateRates = (speaker) => {
    const total = speaker.statements.length;
    if (total === 0) return { solution: 0, local: 0, evidence: 0, constructive: 0 };
    return {
      solution: Math.round((speaker.statements.filter(s => s.solution_score >= 4).length / total) * 100),
      local: Math.round((speaker.statements.filter(s => s.local_focus_score >= 4).length / total) * 100),
      evidence: Math.round((speaker.statements.filter(s => s.evidence_score >= 4).length / total) * 100),
      constructive: Math.round((speaker.statements.filter(s => s.constructive_score >= 4).length / total) * 100),
    };
  };

  const radarData = useMemo(() => {
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

  // 2. 政策ポートフォリオ（カテゴリ比率）
  const portfolios = useMemo(() => {
    return compareList.map(spk => {
      const total = spk.statements.length || 1;
      const sorted = Object.entries(spk.catCounts).sort((a, b) => b[1] - a[1]);
      const top = sorted.slice(0, 4).map(([name, count]) => ({ name, pct: (count / total) * 100 }));
      const othersPct = sorted.slice(4).reduce((sum, [_, count]) => sum + (count / total) * 100, 0);
      if (othersPct > 0) top.push({ name: 'その他', pct: othersPct });
      return { speaker: spk.speaker, distribution: top };
    });
  }, [compareList]);

  // 3. Head-to-Head 共通論点スレッド抽出
  const headToHead = useMemo(() => {
    const sets = compareList.map(s => new Set(Object.keys(s.catCounts)));
    if (sets.length === 0) return null;
    let commonCats = [...sets[0]].filter(cat => sets.slice(1).every(set => set.has(cat)));
    
    if (commonCats.length === 0) return null;
    // 最も発言総数が多い共通カテゴリを選ぶ
    const bestCat = commonCats.sort((a, b) => {
      const countA = compareList.reduce((sum, spk) => sum + (spk.catCounts[a] || 0), 0);
      const countB = compareList.reduce((sum, spk) => sum + (spk.catCounts[b] || 0), 0);
      return countB - countA;
    })[0];

    const threads = compareList.map(spk => {
      const catThreads = spk.statements.filter(s => s.category.includes(bestCat));
      catThreads.sort((a, b) => {
        const scoreA = a.evidence_score + a.solution_score + a.local_focus_score + a.constructive_score;
        const scoreB = b.evidence_score + b.solution_score + b.local_focus_score + b.constructive_score;
        return scoreB - scoreA;
      });
      return { speaker: spk.speaker, thread: catThreads[0] };
    });

    return { category: bestCat, threads };
  }, [compareList]);

  return (
    <main className="max-w-6xl mx-auto py-8 px-6 animate-in fade-in slide-in-from-bottom-4 duration-300 w-full">
      
      {/* 画面トップ戻る＆シェア */}
      <div className="flex items-center justify-between mb-6">
        <button 
          onClick={onClose}
          className="inline-flex items-center text-xs font-bold text-slate-500 hover:text-indigo-600 transition-colors bg-white px-3 py-2 rounded-lg border border-slate-200 shadow-sm"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />一覧に戻る
        </button>
        <button 
          onClick={handleShare}
          className="inline-flex items-center text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 transition-colors px-4 py-2 rounded-lg shadow-md"
        >
          <Share2 className="w-3.5 h-3.5 mr-1.5" />この比較をシェア
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        
        {/* ヘッダー領域: 比較する議員の基本情報 */}
        <div className="p-6 md:p-8 bg-slate-50/50 border-b border-slate-100">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-600">
              <GitCompare className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-black text-slate-900">議員ポリシー徹底比較</h2>
              <p className="text-xs text-slate-500 font-medium">議場でのアプローチと注力政策の違い</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {compareList.map((spk, idx) => (
              <div key={spk.speaker} className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm relative overflow-hidden group">
                <div className="absolute top-0 left-0 w-1 h-full" style={{ backgroundColor: COMPARE_COLORS[idx] }} />
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-xl font-black text-slate-900">{spk.speaker}</h3>
                    <div className="text-[11px] font-bold text-slate-500 mt-1">
                      {spk.district} / <span className="text-slate-400">{spk.partyGroup}</span>
                    </div>
                  </div>
                  <button 
                    onClick={() => onSpeakerClick(spk.speaker)}
                    className="w-8 h-8 rounded-full bg-slate-50 hover:bg-indigo-50 text-slate-400 hover:text-indigo-600 flex items-center justify-center transition-colors border border-slate-200"
                    title="詳細ページへ"
                  >
                    <User className="w-4 h-4" />
                  </button>
                </div>
                <div className={`px-2 py-0.5 text-[10px] font-bold rounded border inline-block mb-3 ${spk.style.badgeClass}`}>
                  {spk.style.label}
                </div>
                <div className="text-[10px] text-slate-500 font-medium leading-relaxed">
                  {spk.style.desc}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* タブナビゲーション */}
        <div className="flex overflow-x-auto border-b border-slate-200 bg-white hide-scrollbar">
          <button onClick={() => setActiveTab('style')} className={`px-6 py-4 text-sm font-bold flex items-center whitespace-nowrap transition-colors border-b-2 ${activeTab === 'style' ? 'border-indigo-600 text-indigo-700 bg-indigo-50/30' : 'border-transparent text-slate-500 hover:bg-slate-50'}`}>
            <Target className="w-4 h-4 mr-2" />アプローチと強み
          </button>
          <button onClick={() => setActiveTab('portfolio')} className={`px-6 py-4 text-sm font-bold flex items-center whitespace-nowrap transition-colors border-b-2 ${activeTab === 'portfolio' ? 'border-indigo-600 text-indigo-700 bg-indigo-50/30' : 'border-transparent text-slate-500 hover:bg-slate-50'}`}>
            <BarChart3 className="w-4 h-4 mr-2" />注力政策ポートフォリオ
          </button>
          <button onClick={() => setActiveTab('head2head')} className={`px-6 py-4 text-sm font-bold flex items-center whitespace-nowrap transition-colors border-b-2 ${activeTab === 'head2head' ? 'border-indigo-600 text-indigo-700 bg-indigo-50/30' : 'border-transparent text-slate-500 hover:bg-slate-50'}`}>
            <MessageCircle className="w-4 h-4 mr-2" />共通論点 直接突き合わせ
          </button>
        </div>

        {/* タブコンテンツ */}
        <div className="p-6 md:p-8 bg-slate-50 min-h-[500px]">
          
          {/* タブ1: アプローチと強み */}
          {activeTab === 'style' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-in fade-in">
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                <h4 className="text-sm font-extrabold text-slate-800 mb-2">4軸レーダー重ね合わせ</h4>
                <p className="text-[11px] text-slate-500 mb-4">平均スコアの面積差から、全体的なスタイルの違いを把握できます。</p>
                <div className="w-full h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                      <PolarGrid stroke="#cbd5e1" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: '#334155', fontSize: 11, fontWeight: 700 }} />
                      <PolarRadiusAxis domain={[0, 5]} tick={false} axisLine={false} />
                      {compareList.map((spk, idx) => (
                        <Radar key={spk.speaker} name={spk.speaker} dataKey={`speaker_${idx}`} stroke={COMPARE_COLORS[idx]} strokeWidth={3} fill={COMPARE_COLORS[idx]} fillOpacity={0.15} />
                      ))}
                      <Legend />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-extrabold text-slate-800">強み発揮率（アプローチの確率）</h4>
                <p className="text-[11px] text-slate-500 mb-6">
                  登壇時に、そのアプローチ（スコア4以上）をどれくらいの確率で取るかを示します。<br/>
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
                    <div className="space-y-3">
                      {compareList.map((spk, idx) => {
                        const rate = calculateRates(spk)[metric.key];
                        return (
                          <div key={spk.speaker} className="flex items-center gap-3">
                            <span className="w-16 text-[10px] font-bold text-slate-500 truncate text-right">{spk.speaker}</span>
                            <div className="flex-1 bg-slate-100 h-2.5 rounded-full overflow-hidden flex">
                              <div className="h-full rounded-full transition-all duration-500" style={{ width: `${rate}%`, backgroundColor: COMPARE_COLORS[idx] }} />
                            </div>
                            <span className="w-8 text-[11px] font-black text-slate-700 text-right">{rate}%</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* タブ2: 注力政策ポートフォリオ */}
          {activeTab === 'portfolio' && (
            <div className="space-y-8 animate-in fade-in max-w-4xl mx-auto">
              <div className="text-center mb-6">
                <h4 className="text-base font-extrabold text-slate-800 mb-2">発言時間の投下ポートフォリオ</h4>
                <p className="text-xs text-slate-500">
                  全質疑の中で、どの政策分野に最も多くエネルギー（発言機会）を割いているかを帯グラフで比較します。<br/>
                  これにより、「どの議員が自分の関心テーマに一番近いか」が分かります。
                </p>
              </div>

              {portfolios.map((port, idx) => (
                <div key={port.speaker} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
                  <div className="absolute left-0 top-0 w-1 h-full" style={{ backgroundColor: COMPARE_COLORS[idx] }} />
                  <h5 className="text-sm font-black text-slate-800 mb-4 ml-2">{port.speaker} 議員</h5>
                  
                  {/* 積み上げ帯グラフ */}
                  <div className="w-full h-8 rounded-lg overflow-hidden flex mb-3 shadow-inner bg-slate-100">
                    {port.distribution.map((item, i) => {
                      // 簡易的に彩度を落として塗り分ける
                      const alpha = 1 - (i * 0.15); 
                      return (
                        <div 
                          key={item.name} 
                          className="h-full flex items-center justify-center hover:opacity-80 transition-opacity relative group"
                          style={{ width: `${item.pct}%`, backgroundColor: COMPARE_COLORS[idx], opacity: alpha }}
                        >
                          {item.pct > 8 && <span className="text-[9px] font-bold text-white truncate px-1">{item.name}</span>}
                        </div>
                      );
                    })}
                  </div>

                  {/* 凡例リスト */}
                  <div className="flex flex-wrap gap-x-4 gap-y-2 ml-2 mt-4">
                    {port.distribution.map((item, i) => (
                      <div key={item.name} className="flex items-center gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COMPARE_COLORS[idx], opacity: 1 - (i * 0.15) }} />
                        <span className="text-[11px] font-bold text-slate-600">{item.name} <span className="text-slate-400 font-medium">({item.pct.toFixed(1)}%)</span></span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* タブ3: 直接突き合わせ (Head-to-Head) */}
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
                      共通して登壇数の多い分野 <strong className="text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">【{headToHead.category}】</strong> における、両者の最も評価の高い質疑スレッドを並べました。<br/>
                      同じ課題に対して「どのような切り口で迫るか」のスタイルの違いをご確認ください。
                    </p>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {headToHead.threads.map((item, idx) => (
                      <div key={item.speaker} className="flex flex-col relative pt-4">
                        <div className="absolute top-0 left-4 px-3 py-1 rounded-t-lg text-[11px] font-black text-white shadow-sm z-10" style={{ backgroundColor: COMPARE_COLORS[idx] }}>
                          {item.speaker} のアプローチ
                        </div>
                        {item.thread ? (
                          <div className={`flex-1 border-2 rounded-2xl rounded-tl-none overflow-hidden bg-white shadow-sm`} style={{ borderColor: COMPARE_COLORS[idx] }}>
                            <ThreadCard
                              stmt={item.thread}
                              onSpeakerClick={() => {}}
                              onViewContext={onViewContext}
                              showSpeakerHeader={false}
                            />
                          </div>
                        ) : (
                          <div className="flex-1 border-2 border-slate-200 border-dashed rounded-2xl rounded-tl-none bg-white p-6 text-center text-slate-400 text-xs">
                            該当データなし
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

        </div>
      </div>
    </main>
  );
}