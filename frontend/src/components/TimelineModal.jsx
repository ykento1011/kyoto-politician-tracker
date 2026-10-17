import React, { useState, useEffect, useMemo } from 'react';
import { MessageCircle, X, Loader2, ChevronUp } from 'lucide-react';

export default function TimelineModal({
  isOpen,
  onClose,
  selectedContext,
  isLoading
}) {
  const [showPrevious, setShowPrevious] = useState(false);

  useEffect(() => {
    if (isOpen) setShowPrevious(false);
  }, [isOpen, selectedContext]);

  const targetIndex = useMemo(() => {
    if (!selectedContext?.context) return -1;
    return selectedContext.context.findIndex((m) => m.is_target);
  }, [selectedContext]);

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 w-full max-w-2xl bg-white shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-300">
        <div className="px-5 py-4 border-b border-slate-200 flex justify-between items-center bg-white z-10">
          <div>
            <h2 className="text-base font-extrabold text-slate-900 flex items-center">
              <MessageCircle className="w-4 h-4 mr-1.5 text-indigo-600" />
              会議録タイムライン
            </h2>
            <p className="text-[10px] text-slate-500 mt-0.5">{selectedContext?.statement?.meeting_title}</p>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:bg-slate-100 rounded-full">
            <X className="w-5 h-5" />
          </button>
        </div>
        
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
                  className="w-full py-2.5 flex items-center justify-center text-xs font-bold text-indigo-600 bg-indigo-50/50 hover:bg-indigo-100 rounded-xl border border-indigo-100 transition-colors mb-2"
                >
                  <ChevronUp className="w-4 h-4 mr-1" />
                  これより前の文脈（{targetIndex}件のやり取り）を表示する
                </button>
              )}

              {selectedContext.context.map((msg, idx) => {
                if (msg.is_short_procedural && !msg.is_target) return null;
                if (!showPrevious && idx < targetIndex) return null;

                // 💡 要件4-1: 行政職員発言の肩書解像度向上
                const speakerLabel = msg.is_admin
                  ? (msg.speaker.includes('部長') || msg.speaker.includes('室長') || msg.speaker.includes('局長')
                      ? msg.speaker
                      : `${msg.speaker} (市側)`)
                  : `${msg.speaker} 議員`;

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
                      className={`max-w-[90%] rounded-xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                        msg.is_target
                          ? 'bg-indigo-600 text-white rounded-tr-none border border-indigo-700'
                          : msg.is_admin
                          ? 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'
                          : 'bg-slate-200 text-slate-700 rounded-tl-none'
                      }`}
                    >
                      {msg.statement_text}
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