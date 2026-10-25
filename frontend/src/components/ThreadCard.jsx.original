import React from 'react';
import { FileText, Lightbulb, MessageCircle, User } from 'lucide-react';
import { cleanName, cleanAuditorNote } from '../utils/styleHelpers';

export default function ThreadCard({
  stmt,
  speakerInfo,
  onSpeakerClick,
  onViewContext,
  showSpeakerHeader = true
}) {
  const activeMetrics = [
    { label: '根拠・データ', val: stmt.evidence_score, color: 'bg-indigo-500' },
    { label: '対案・是正策', val: stmt.solution_score, color: 'bg-emerald-500' },
    { label: '地域解像度', val: stmt.local_focus_score, color: 'bg-amber-500' },
    { label: '議論の進展', val: stmt.constructive_score, color: 'bg-purple-500' }
  ].filter((m) => m.val > 0);

  return (
    <article className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col">
      
      {showSpeakerHeader ? (
        <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50">
          <button
            onClick={() => onSpeakerClick && onSpeakerClick(cleanName(stmt.speaker))}
            className="flex items-start text-left hover:bg-slate-100 p-1.5 -ml-1.5 rounded-lg transition-colors group"
          >
            <div className="w-9 h-9 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 mr-2.5 shrink-0 group-hover:bg-indigo-600 group-hover:text-white transition-colors mt-0.5">
              <User className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-black text-slate-900 group-hover:text-indigo-700 transition-colors">
                  {stmt.speaker} <span className="text-[10px] font-medium text-slate-500 font-normal">議員</span>
                </span>
                {speakerInfo && (
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border inline-block ${speakerInfo.style.badgeClass}`}>
                    {speakerInfo.style.label}
                  </span>
                )}
              </div>
              {/* 💡 要件3-3: 質疑カードの補助テキストとして選挙区・会派を表示 */}
              {speakerInfo && (
                <div className="text-[10px] font-bold text-slate-500 mt-0.5">
                  <span className="text-slate-600 mr-1">{speakerInfo.district}</span>/
                  <span className="ml-1 opacity-80">{speakerInfo.partyGroup}</span>
                </div>
              )}
            </div>
          </button>
          <div className="flex items-center gap-2 text-right">
            <span className="px-2 py-0.5 bg-white text-slate-600 text-[10px] font-bold rounded border border-slate-200 shrink-0">
              {stmt.category}
            </span>
            <span className="text-slate-400 text-xs font-medium shrink-0">{stmt.meeting_date}</span>
          </div>
        </div>
      ) : (
        <div className="p-4 border-b border-slate-100 flex items-center gap-3 bg-slate-50/50">
          <span className="px-2 py-0.5 bg-white text-slate-600 text-[10px] font-bold rounded border border-slate-200">
            {stmt.category}
          </span>
          <span className="text-slate-400 text-xs font-medium">{stmt.meeting_date}</span>
        </div>
      )}

      <div className="p-5 flex flex-col md:flex-row gap-6">
        <div className="md:w-3/5 flex flex-col gap-2">
          <h3 className="text-xs font-bold text-slate-500 mb-1 leading-snug">{stmt.meeting_title}</h3>
          <h4 className="text-[10px] font-bold text-slate-400 uppercase flex items-center">
            <FileText className="w-3 h-3 mr-1" />質疑スレッド要旨
          </h4>
          <p className="text-sm leading-relaxed text-slate-700 mt-1">{stmt.summary}</p>
        </div>

        <div className="md:w-2/5 bg-slate-50 p-4 rounded-xl border border-slate-100 flex flex-col">
          <span className="text-[10px] font-bold text-slate-400 uppercase mb-3 block">発揮された強み</span>
          
          {activeMetrics.length > 0 ? (
            <div className="space-y-2.5">
              {activeMetrics.map((metric) => (
                <div key={metric.label}>
                  <div className="flex justify-between text-xs font-bold text-slate-600 mb-1">
                    <span>{metric.label}</span>
                    <span className="font-mono text-slate-400">{metric.val}/5</span>
                  </div>
                  <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                    <div className={`h-full ${metric.color}`} style={{ width: `${(metric.val / 5) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-2 text-slate-400 text-xs font-medium">初期確認・状況整理の質疑</div>
          )}

          {activeMetrics.length > 0 && stmt.scoring_reasoning && (
            <div className="mt-4 pt-3 border-t border-slate-200/60">
              <h5 className="text-[10px] font-bold text-slate-400 uppercase mb-1.5 flex items-center">
                <Lightbulb className="w-3 h-3 text-amber-500 mr-1 shrink-0" /> AI Auditor Note
              </h5>
              <p className="text-[11px] text-slate-600 line-clamp-3 leading-relaxed">
                {cleanAuditorNote(stmt.scoring_reasoning)}
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white p-4 border-t border-slate-100">
        <button
          onClick={() => onViewContext(stmt)}
          className="w-full py-2 flex items-center justify-center text-xs font-bold text-indigo-600 bg-white hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 rounded-lg transition-colors"
        >
          <MessageCircle className="w-3.5 h-3.5 mr-1.5" />市側答弁を含む一連のタイムラインを表示
        </button>
      </div>
    </article>
  );
}