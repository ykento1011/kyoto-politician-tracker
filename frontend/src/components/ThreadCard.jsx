import React, { useState } from 'react';
import { FileText, Lightbulb, MessageCircle, User, Landmark, ExternalLink, ChevronDown } from 'lucide-react';
import { cleanName, cleanAuditorNote } from '../utils/styleHelpers';
import { openOfficialMinute, getOfficialLinkTooltip, getOfficialMinuteUrl } from '../utils/officialLink';
import ReportIssueButton from './ReportIssueButton';

export default function ThreadCard({stmt, statement, thread, speakerInfo, onSpeakerClick, onViewContext, showSpeakerHeader = true, cityCode}) {
  const actualStmt = stmt || statement || thread || {};
  stmt = actualStmt;
    // statement または thread のいずれかが渡されても受け取れるように防御的処理
      // URLパス または props/データから大阪を直接判定
  const isOsakaUrl = typeof window !== 'undefined' && window.location.pathname.startsWith('/osaka');
  const isOsakaThread = isOsakaUrl || 
                        cityCode === 'osaka' || 
                        stmt?.council === '大阪市会' || 
                        stmt?.council === '大阪市' ||
                        actualStmt?.council === '大阪市会' ||
                        (typeof stmt?.meeting_name === 'string' && stmt.meeting_name.includes('大阪市')) ||
                        (typeof actualStmt?.meeting_name === 'string' && thread.meeting_name.includes('大阪市')) ||
                        (typeof stmt?.committee_name === 'string' && stmt.committee_name.includes('大阪市')) ||
                        (typeof actualStmt?.committee_name === 'string' && thread.committee_name.includes('大阪市'));
  const isNagoyaThread = stmt.official_url?.includes('nagoya') || stmt.meeting_title?.includes('名古屋') || window.location.pathname.includes('/nagoya');
  const councilOriginalLabel = isNagoyaThread ? '名古屋市会 公式原本で確認' : isOsakaThread ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認';

  const [isNoteExpanded, setIsNoteExpanded] = useState(false);

  const activeMetrics = [
    { label: '根拠・データ', val: stmt.evidence_score, color: 'bg-indigo-500' },
    { label: '対案・是正策', val: stmt.solution_score, color: 'bg-emerald-500' },
    { label: '地域解像度', val: stmt.local_focus_score, color: 'bg-amber-500' },
    { label: '議論の進展', val: stmt.constructive_score, color: 'bg-purple-500' }
  ].filter((m) => m.val > 0);

  const auditorNoteText = (stmt.scoring_reasoning || stmt.reasoning) ? cleanAuditorNote(stmt.scoring_reasoning || stmt.reasoning) : "";

  return (
    <article className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col">
      
      {/* 上部ヘッダー */}
      {showSpeakerHeader ? (
        <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50">
          <button
            onClick={() => onSpeakerClick && onSpeakerClick(cleanName(stmt.speaker))}
            className="flex items-start text-left hover:bg-slate-100 p-1.5 -ml-1.5 rounded-lg transition-colors group cursor-pointer"
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
          {/* 💡 修正：「発揮された強み」➔「4軸分析結果」 */}
          <span className="text-[10px] font-bold text-slate-500 uppercase mb-3 block">
            4軸分析結果
          </span>
          
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

          {/* 💡 修正：「AI Auditor Note」➔「分析メモ」 */}
          {activeMetrics.length > 0 && auditorNoteText && (
            <div className="mt-4 pt-3 border-t border-slate-200/60 transition-all">
              <div className="flex items-center justify-between mb-1.5">
                <h5 className="text-[10px] font-bold text-slate-500 uppercase flex items-center">
                  <Lightbulb className="w-3 h-3 text-amber-500 mr-1 shrink-0" /> 分析メモ
                </h5>
              </div>
              
              <p className={`text-[11px] text-slate-600 leading-relaxed transition-all ${
                isNoteExpanded ? '' : 'line-clamp-3'
              }`}>
                {auditorNoteText}
              </p>

              {auditorNoteText.length > 70 && (
                <div className="pt-1 mt-0.5">
                  <button
                    onClick={() => setIsNoteExpanded(!isNoteExpanded)}
                    className="inline-flex items-center text-[10px] font-bold text-indigo-600 hover:text-indigo-800 transition-colors cursor-pointer select-none"
                  >
                    <span>{isNoteExpanded ? '閉じる' : '全文を表示'}</span>
                    <ChevronDown className={`w-3 h-3 ml-0.5 transition-transform duration-200 ${
                      isNoteExpanded ? 'rotate-180' : ''
                    }`} />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* アクションボタンエリア */}
      <div className="bg-white p-3 sm:p-4 border-t border-slate-100 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => openOfficialMinute(stmt, isNagoyaThread ? 'nagoya' : isOsakaThread ? 'osaka' : 'kyoto')}
            title={getOfficialLinkTooltip(stmt, isNagoyaThread ? 'nagoya' : isOsakaThread ? 'osaka' : 'kyoto')}
            className="px-3.5 py-2 flex items-center justify-center text-xs font-bold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 hover:border-slate-300 rounded-lg transition-colors cursor-pointer group shrink-0"
          >
            <Landmark className="w-3.5 h-3.5 mr-1.5 text-indigo-600 group-hover:text-indigo-700" />
            <span>{councilOriginalLabel}</span>
            <ExternalLink className="w-3 h-3 ml-1.5 text-slate-400 group-hover:text-slate-600" />
          </button>
          <ReportIssueButton
            targetUrl={getOfficialMinuteUrl(stmt, isNagoyaThread ? 'nagoya' : isOsakaThread ? 'osaka' : 'kyoto')}
            speaker={stmt?.speaker || speakerInfo?.name || ''}
            meetingDate={stmt?.meeting_date || ''}
            targetId={stmt?.statement_id || stmt?.id || ''}
            municipality={isNagoyaThread ? '名古屋市会' : isOsakaThread ? '大阪市会' : '京都市会'}
          />
        </div>

        <button
          onClick={() => onViewContext(stmt)}
          className="flex-1 py-2 flex items-center justify-center text-xs font-bold text-indigo-600 bg-indigo-50/50 hover:bg-indigo-100/80 border border-indigo-200/70 hover:border-indigo-300 rounded-lg transition-colors cursor-pointer"
        >
          <MessageCircle className="w-3.5 h-3.5 mr-1.5" />市側答弁を含む一連のタイムラインを表示
        </button>
      </div>
    </article>
  );
}