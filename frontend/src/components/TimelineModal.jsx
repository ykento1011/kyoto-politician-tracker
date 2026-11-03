import React, { useState, useEffect, useMemo } from 'react';
import { MessageCircle, X, Loader2, ChevronUp, Landmark, ExternalLink } from 'lucide-react';
import { openOfficialMinute, getOfficialLinkTooltip } from '../utils/officialLink';
import useScrollLock from '../hooks/useScrollLock';
import { useSwipeToClose } from '../hooks/useSwipeToClose';

/**
 * 発言録アイテムコンポーネント（チャットバブル & 行数制限アコーディオン）
 */
function TimelineMessageItem({ msg }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const text = msg.statement_text || msg.summary || msg.statement_summary || msg.question_summary || '（質疑テキスト）';

  // 180文字以上 または 改行が4行以上ある場合にアコーディオンを適用
  const lineCount = (text.match(/\n/g) || []).length + 1;
  const isLongText = text.length >= 180 || lineCount >= 4;

  // 質問（議員） vs 答弁（首長・行政幹部）の判定
  const isQuestion = msg.is_target || (!msg.is_admin && msg.speaker && !msg.speaker.includes('市長') && !msg.speaker.includes('副市長') && !msg.speaker.includes('局長') && !msg.speaker.includes('部長') && !msg.speaker.includes('委員長') && !msg.speaker.includes('議長'));

  const bubbleBg = isQuestion
    ? 'bg-indigo-50/70 border-l-4 border-indigo-500 text-slate-800'
    : 'bg-slate-50 border-l-4 border-slate-400 text-slate-800';

  const fadeGradient = isQuestion
    ? 'from-indigo-50/90 to-transparent'
    : 'from-slate-50/90 to-transparent';

  const roleBadge = isQuestion ? '質問' : (msg.is_admin ? '答弁 / 進行' : '答弁');
  const badgeColor = isQuestion
    ? 'bg-indigo-100 text-indigo-700 border-indigo-200'
    : 'bg-slate-200/80 text-slate-700 border-slate-300';

  return (
    <div className="w-full flex flex-col mb-3">
      {msg.is_target && (
        <div className="w-full flex justify-center mb-2">
          <span className="bg-indigo-100 text-indigo-800 text-[10px] font-black px-3 py-1 rounded-full border border-indigo-200">
            ここから評価対象の質疑
          </span>
        </div>
      )}

      {/* 発言者バッジヘッダー */}
      <div className="flex items-center gap-1.5 mb-1.5 ml-1">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${badgeColor}`}>
          {roleBadge}
        </span>
        <span className="text-xs font-bold text-slate-700">
          {msg.speaker} {msg.is_admin && msg.is_short_procedural ? '(進行)' : ''}
        </span>
      </div>

      {/* 発言録バブル本体 */}
      <div className={`p-3.5 rounded-r-xl rounded-bl-xl border-y border-r border-slate-200/60 shadow-2xs ${bubbleBg}`}>
        {/* DOM 上はテキストを常にレンダリングし、CSS で高さを制限（E2E テスト保護） */}
        <div className={!isExpanded && isLongText ? "relative max-h-24 overflow-hidden" : ""}>
          <p className="text-[13.5px] leading-relaxed whitespace-pre-wrap break-words">
            {text}
          </p>
          {!isExpanded && isLongText && (
            <div className={`absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t ${fadeGradient} pointer-events-none`} />
          )}
        </div>

        {isLongText && (
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="mt-2 min-h-[36px] text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 cursor-pointer transition-colors"
          >
            {isExpanded ? "閉じる ▲" : `続きを読む (${text.length}文字) ▼`}
          </button>
        )}
      </div>
    </div>
  );
}

export default function TimelineModal({
  isOpen,
  onClose,
  selectedContext,
  isLoading,
  cityCode = 'kyoto'
}) {
  const [showPrevious, setShowPrevious] = useState(false);
  useScrollLock(isOpen);
  const swipeHandlers = useSwipeToClose(onClose, 60);

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
      {/* 背景オーバーレイ */}
      <div 
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-40 animate-in fade-in duration-200" 
        onClick={onClose} 
      />

      {/* モーダルコンテナ（モバイル: 下部スライドイン / デスクトップ: 中央ポップアップ） */}
      <div 
        data-testid="statement-modal"
        className="
          fixed inset-x-0 bottom-0 z-50 flex flex-col
          max-h-[88vh] rounded-t-3xl bg-white shadow-2xl
          animate-in slide-in-from-bottom duration-200
          sm:inset-0 sm:m-auto sm:max-w-2xl sm:max-h-[85vh] sm:rounded-2xl sm:slide-in-from-bottom-0
          overflow-hidden
        "
      >
        {/* モバイル専用ドラッグハンドル */}
        <div
        className="w-12 h-1.5 bg-slate-300 rounded-full mx-auto my-3 shrink-0 sm:hidden cursor-grab touch-none active:bg-slate-400 transition-colors"
        {...swipeHandlers}
      />

        {/* モーダルヘッダー */}
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between gap-3 bg-white z-10 shrink-0">
          <div className="min-w-0">
            <h2 className="text-base font-extrabold text-slate-900 flex items-center truncate">
              <MessageCircle className="w-4 h-4 mr-1.5 text-indigo-600 shrink-0" />
              会議録タイムライン
            </h2>
            <p className="text-[10px] text-slate-500 mt-0.5 truncate">{selectedContext?.statement?.meeting_title}</p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {targetStatement && (
              <button
                onClick={() => openOfficialMinute(targetStatement, cityCode)}
                title={getOfficialLinkTooltip(targetStatement, cityCode)}
                className="hidden sm:inline-flex items-center text-xs font-bold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 px-3 py-1.5 rounded-lg transition-colors cursor-pointer group"
              >
                <Landmark className="w-3.5 h-3.5 mr-1.5 text-indigo-600" />
                <span>{cityCode === 'nagoya' ? '名古屋市会' : cityCode === 'osaka' ? '大阪市会' : '京都市会'} 原本</span>
                <ExternalLink className="w-3 h-3 ml-1 text-indigo-400 group-hover:text-indigo-600" />
              </button>
            )}

            <button 
              onClick={onClose} 
              data-testid="close-modal"
              className="min-w-[44px] min-h-[44px] flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full cursor-pointer transition-colors"
              title="閉じる"
              aria-label="閉じる"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* タイムラインメッセージ一覧（チャットバブルスレッド） */}
        <div className="flex-1 overflow-y-auto overscroll-contain p-4 sm:p-5 bg-slate-50/70 space-y-2 relative">
          {isLoading ? (
            <div className="flex justify-center py-10">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
            </div>
          ) : selectedContext?.context?.length > 0 ? (
            <>
              {!showPrevious && targetIndex > 0 && (
                <button
                  onClick={() => setShowPrevious(true)}
                  className="w-full py-2.5 flex items-center justify-center text-xs font-bold text-indigo-600 bg-indigo-50/70 hover:bg-indigo-100 rounded-xl border border-indigo-100 transition-colors mb-3 cursor-pointer min-h-[40px]"
                >
                  <ChevronUp className="w-4 h-4 mr-1" />
                  これより前の文脈（{targetIndex}件のやり取り）を表示する
                </button>
              )}

              {selectedContext.context.map((msg, idx) => {
                if (msg.is_short_procedural && !msg.is_target) return null;
                if (!showPrevious && idx < targetIndex) return null;

                return (
                  <TimelineMessageItem 
                    key={idx} 
                    msg={msg} 
                  />
                );
              })}
            </>
          ) : (
            <p className="text-center text-sm text-slate-400 py-6">データが見つかりません</p>
          )}
        </div>

        {/* 下部 Sticky アクションバー（原本リンク & 44px閉じるボタン & Safe Area対応） */}
        <div className="sticky bottom-0 bg-white/95 backdrop-blur border-t border-slate-100 p-3 pb-safe flex items-center gap-2 z-10 shrink-0">
          {targetStatement && (
            <button
              onClick={() => openOfficialMinute(targetStatement, cityCode)}
              title={getOfficialLinkTooltip(targetStatement, cityCode)}
              className="flex-1 min-h-[44px] flex items-center justify-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl px-3 transition-colors cursor-pointer group"
            >
              <Landmark className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
              <span className="truncate">一次公文書を確認</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-600 shrink-0" />
            </button>
          )}
          <button
            onClick={onClose}
            data-testid="close-modal"
            className="flex-1 min-h-[44px] flex items-center justify-center text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-xl px-3 transition-colors cursor-pointer"
          >
            閉じる
          </button>
        </div>
      </div>
    </>
  );
}
