import React, { useState, useEffect, useMemo } from 'react';
import { MessageCircle, X, Loader2, ChevronUp, Landmark, ExternalLink } from 'lucide-react';
import { openOfficialMinute, getOfficialLinkTooltip } from '../utils/officialLink';

export default function TimelineModal({
  isOpen,
  onClose,
  selectedContext,
  isLoading,
  cityCode = 'kyoto'
}) {
  const [showPrevious, setShowPrevious] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setShowPrevious(false);
    }
  }, [isOpen, selectedContext]);

  const targetIndex = useMemo(() => {
    if (!selectedContext?.context) return -1;
    return selectedContext.context.findIndex((m) => m.is_target);
  }, [selectedContext]);

  // 評価対象のステートメント情報を取得
  const targetStatement = useMemo(() => {
    return selectedContext?.statement || selectedContext?.context?.find((m) => m.is_target) || null;
  }, [selectedContext]);

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 w-full max-w-2xl bg-white shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-300">
        
        {/* モーダルヘッダー */}
        <div className="px-5 py-3.5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white z-10">
          <div className="min-w-0">
            <h2 className="text-base font-extrabold text-slate-900 flex items-center truncate">
              <MessageCircle className="w-4 h-4 mr-1.5 text-indigo-600 shrink-0" />
              会議録タイムライン
            </h2>
            <p className="text-[10px] text-slate-500 mt-0.5 truncate">{selectedContext?.statement?.meeting_title}</p>
          </div>

          <div className="flex items-center justify-between sm:justify-end gap-2 shrink-0">
            {targetStatement && (
              <button
                onClick={() => openOfficialMinute(targetStatement, cityCode)}
                title={getOfficialLinkTooltip(targetStatement, cityCode)}
                className="inline-flex items-center text-xs font-bold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 px-3 py-1.5 rounded-lg transition-colors cursor-pointer group"
              >
                <Landmark className="w-3.5 h-3.5 mr-1.5 text-indigo-600" />
                <span>{cityCode === 'nagoya' ? '名古屋市会' : cityCode === 'osaka' ? '大阪市会' : '京都市会'} 議事録原本を確認</span>
                <ExternalLink className="w-3 h-3 ml-1 text-indigo-400 group-hover:text-indigo-600" />
              </button>
            )}

            <button 
              onClick={onClose} 
              className="p-1.5 text-slate-400 hover:bg-slate-100 rounded-full cursor-pointer transition-colors"
              title="閉じる"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* タイムラインメッセージ一覧 */}
        <div className="flex-1 overflow-y-auto p-5 bg-slate-50 space-y-4 relative">
          {isLoading ? (
            <div className="flex justify-center py-10">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
            </div>
          ) : selectedContext?.context?.length > 0 ? (
            <>
              {!showPrevious && targetIndex > 0 && (
                <button
                  onClick={() => setShowPrevious(true)}
                  className="w-full py-2.5 flex items-center justify-center text-xs font-bold text-indigo-600 bg-indigo-50/50 hover:bg-indigo-100 rounded-xl border border-indigo-100 transition-colors mb-2 cursor-pointer"
                >
                  <ChevronUp className="w-4 h-4 mr-1" />
                  これより前の文脈（{targetIndex}件のやり取り）を表示する
                </button>
              )}

              {selectedContext.context.map((msg, idx) => {
                if (msg.is_short_procedural && !msg.is_target) return null;
                if (!showPrevious && idx < targetIndex) return null;

                const speakerLabel = msg.speaker;

                return (
                  <div key={idx} className={`flex flex-col ${msg.is_target ? 'items-end' : 'items-start'} ${msg.is_target && !showPrevious ? 'mt-0' : 'mt-4'}`}>
                    {msg.is_target && (
                      <div className="w-full flex justify-center mb-3">
                        <span className="bg-indigo-100 text-indigo-800 text-[9px] font-black px-3 py-1 rounded-full border border-indigo-200">
                          ここから評価対象の質疑
                        </span>
                      </div>
                    )}

                    <div className={`text-[10px] font-bold mb-1 ${msg.is_target ? 'text-indigo-600 mr-1' : 'text-slate-500 ml-1'}`}>
                      {speakerLabel} {msg.is_admin && msg.is_short_procedural ? '(進行)' : ''}
                    </div>

                    <div
                      className={`max-w-[90%] rounded-xl px-4 py-3 text-sm leading-relaxed shadow-sm whitespace-pre-wrap break-words ${msg.is_target
                          ? 'bg-indigo-600 text-white rounded-tr-none border border-indigo-700'
                          : msg.is_admin
                            ? 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'
                            : 'bg-slate-200 text-slate-700 rounded-tl-none'
                        }`}
                    >
                      {msg.statement_text || msg.summary || msg.statement_summary || msg.question_summary || '（質疑テキスト）'}
                    </div>
                  </div>
                );
              })}
            </>
          ) : (
            <p className="text-center text-sm text-slate-400">データが見つかりません</p>
          )}
        </div>
      </div>
    </>
  );
}