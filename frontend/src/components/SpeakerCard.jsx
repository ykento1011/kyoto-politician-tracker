import React, { useState } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { ChevronRight, User } from 'lucide-react';
import { cleanStyleLabel, cleanStyleDesc } from '../utils/styleHelpers';

const ALIAS_MAP = {
  '井崎敦子': '井﨑敦子',
  '井﨑敦子': '井崎敦子',
  '繁隆夫': '繁隆夫',
  '繁隆夫': '繁隆夫'
};

export default function SpeakerCard({
  speaker,
  onSpeakerClick
}) {
  const cleanName = speaker.speaker ? speaker.speaker.replace(/\s+/g, '') : '';
  const [currentSrc, setCurrentSrc] = useState(`/councilors/${cleanName}.jpg`);
  const [triedFallback, setTriedFallback] = useState(false);
  const [imgError, setImgError] = useState(false);

  const handleImageError = () => {
    if (!triedFallback && ALIAS_MAP[cleanName]) {
      setTriedFallback(true);
      setCurrentSrc(`/councilors/${ALIAS_MAP[cleanName]}.jpg`);
    } else {
      setImgError(true);
    }
  };

  const radarData = [
    { subject: '根拠・データ', A: speaker.avg_evidence || 0, fullMark: 5 },
    { subject: '対案・是正', A: speaker.avg_solution || 0, fullMark: 5 },
    { subject: '地域解像度', A: speaker.avg_local_focus || 0, fullMark: 5 },
    { subject: '議論の進展', A: speaker.avg_constructive || 0, fullMark: 5 },
  ];

  return (
    <div
      onClick={() => onSpeakerClick(speaker.speaker)}
      className="bg-white rounded-2xl border border-slate-200 hover:border-indigo-300 transition-all duration-200 hover:shadow-md cursor-pointer flex flex-col justify-between overflow-hidden group relative"
    >
      <div className="p-6">
        {/* 上段：顔写真・議員名・選挙区・会派 */}
        <div className="flex items-center gap-3.5 mb-3.5">
          <div className="w-14 h-18 rounded-xl overflow-hidden bg-slate-100 border border-slate-200 shrink-0 flex items-center justify-center shadow-2xs">
            {!imgError ? (
              <img
                src={currentSrc}
                alt={speaker.speaker}
                loading="lazy"
                decoding="async"
                onError={handleImageError}
                className="w-full h-full object-cover object-top"
              />
            ) : (
              <User className="w-6 h-6 text-slate-300" />
            )}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base sm:text-lg font-black text-slate-900 group-hover:text-indigo-600 transition-colors leading-snug truncate">
                {speaker.speaker}
              </h3>
              <span className="text-[10px] sm:text-[11px] font-bold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded shrink-0">
                {speaker.district || '京都'}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium mt-0.5 truncate">
              {speaker.partyGroup || '京都市会'}
            </p>
          </div>
        </div>

        {/* 💡 修正：質疑傾向ラベル・要約のサニタイズ */}
        {speaker.style && (
          <div className="mb-3">
            <span className={`px-2 py-0.5 text-[10px] font-black rounded border inline-block mb-1.5 ${speaker.style.badgeClass || 'bg-indigo-50 text-indigo-700 border-indigo-200'}`}>
              {cleanStyleLabel(speaker.style.label)}
            </span>
            <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">
              {cleanStyleDesc(speaker.style.desc)}
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
              <PolarRadiusAxis domain={[0, 5]} axisLine={false} tick={false} />
              <Radar
                dataKey="A"
                stroke="#6366f1"
                fill="#818cf8"
                fillOpacity={0.35}
                strokeWidth={2}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* 質疑の多いテーマタグ */}
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