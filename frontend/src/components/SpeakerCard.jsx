import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { GitCompare, Check, ChevronRight } from 'lucide-react';

export default function SpeakerCard({
  speaker,
  onSpeakerClick,
  onToggleCompare,
  isCompared = false,
  onOpenCompare
}) {
  const radarData = [
    { subject: '根拠・データ', A: speaker.avg_evidence || 0, fullMark: 5 },
    { subject: '対案・是正', A: speaker.avg_solution || 0, fullMark: 5 },
    { subject: '地域解像度', A: speaker.avg_local_focus || 0, fullMark: 5 },
    { subject: '議論の進展', A: speaker.avg_constructive || 0, fullMark: 5 },
  ];

  return (
    <div
      onClick={() => onSpeakerClick(speaker.speaker)}
      className={`bg-white rounded-2xl border transition-all duration-200 hover:shadow-md cursor-pointer flex flex-col justify-between overflow-hidden group relative ${
        isCompared
          ? 'border-indigo-500 ring-2 ring-indigo-500/20'
          : 'border-slate-200 hover:border-indigo-300'
      }`}
    >
      <div className="p-6">
        {/* 上段：議員名・選挙区・会派・比較ボタン */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-lg font-black text-slate-900 group-hover:text-indigo-600 transition-colors">
                {speaker.speaker}
              </h3>
              <span className="text-[11px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                {speaker.district || '京都'}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium mt-0.5 truncate max-w-[200px]">
              {speaker.partyGroup || '京都市会'}
            </p>
          </div>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleCompare(speaker, e);
            }}
            className={`p-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1 cursor-pointer shrink-0 ${
              isCompared
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-slate-50 hover:bg-indigo-50 text-slate-500 hover:text-indigo-600 border border-slate-200'
            }`}
            title={isCompared ? '比較から外す' : 'ポリシー比較に追加'}
          >
            {isCompared ? <Check className="w-3.5 h-3.5" /> : <GitCompare className="w-3.5 h-3.5" />}
            <span className="text-[10px] hidden sm:inline">{isCompared ? '比較中' : '比較'}</span>
          </button>
        </div>

        {/* スタイル判定バッジ・要約 */}
        {speaker.style && (
          <div className="mb-3">
            <span className={`px-2 py-0.5 text-[10px] font-black rounded border inline-block mb-1.5 ${speaker.style.badgeClass || 'bg-indigo-50 text-indigo-700 border-indigo-200'}`}>
              {speaker.style.label}
            </span>
            <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">
              {speaker.style.desc}
            </p>
          </div>
        )}

        {/* 4軸レーダーチャート */}
        <div className="w-full h-36 my-2 bg-slate-50/60 rounded-xl p-1 border border-slate-100 flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius="62%" data={radarData}>
              <PolarGrid stroke="#e2e8f0" />
              <PolarAngleAxis 
                dataKey="subject" 
                tick={{ fill: '#64748b', fontSize: 9, fontWeight: 700 }} 
              />
              <PolarRadiusAxis domain={[0, 5]} tick={false} axisLine={false} />
              <Radar 
                dataKey="A" 
                stroke="#6366f1" 
                strokeWidth={2} 
                fill="#818cf8" 
                fillOpacity={0.35} 
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* 注力テーマタグ */}
        {speaker.topCategories && speaker.topCategories.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {speaker.topCategories.slice(0, 3).map((cat) => (
              <span key={cat} className="text-[10px] font-bold text-slate-500 bg-slate-50 border border-slate-200/80 px-2 py-0.5 rounded-md">
                #{cat}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* フッター帯 */}
      <div className="bg-slate-50/80 px-6 py-3 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-slate-500 group-hover:bg-indigo-50/50 transition-colors">
        <span>登壇質疑数: {speaker.count ?? 0}件</span>
        <span className="inline-flex items-center text-indigo-600 font-black text-[11px] group-hover:translate-x-0.5 transition-transform">
          詳細を見る
          <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
        </span>
      </div>
    </div>
  );
}