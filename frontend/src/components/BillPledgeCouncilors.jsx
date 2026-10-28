import React, { useMemo } from 'react';
import { BookmarkCheck, CheckCircle2, XCircle, ArrowRight } from 'lucide-react';

/**
 * 議案（bill）に紐づく公約を掲げた議員一覧を逆引き表示するコンポーネント
 * @param {Object} bill - 対象議案オブジェクト ({ session_name, bill_number, title })
 * @param {Object} pledgeData - pledge_tracker_{city}.json のデータ
 * @param {Function} onSelectSpeaker - 議員クリック時のハンドラー
 */
export default function BillPledgeCouncilors({ bill, pledgeData, onSelectSpeaker }) {
  const matchedCouncilors = useMemo(() => {
    if (!bill || !pledgeData) return [];

    const billTitle = bill.title || '';
    const billNum = bill.bill_number || '';
    const session = bill.session_name || bill.session || '';

    const list = [];

    Object.entries(pledgeData).forEach(([speaker, data]) => {
      (data.tracked_items || []).forEach(item => {
        const cv = item.council_vote;
        if (!cv) return;

        // タイトル完全一致、または会期＋議案番号の一致判定
        const isMatch = 
          (cv.bill_title && cv.bill_title === billTitle) ||
          (cv.session === session && cv.bill_number === billNum && billNum !== '');

        if (isMatch) {
          list.push({
            speaker,
            district: data.district,
            party: data.party,
            headline: item.headline,
            vote: cv.vote,
            voteType: cv.vote_type
          });
        }
      });
    });

    return list;
  }, [bill, pledgeData]);

  if (matchedCouncilors.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-slate-100 space-y-2">
      <div className="flex items-center gap-1.5 text-[11px] font-black text-indigo-950">
        <BookmarkCheck className="w-3.5 h-3.5 text-indigo-600" />
        <span>このテーマを看板公約に掲げていた議員 ({matchedCouncilors.length}名)</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {matchedCouncilors.map((c, idx) => {
          const isAgree = c.vote === '賛成' || c.vote === '〇';
          const isDisagree = c.vote === '反対' || c.vote === '×';

          return (
            <div
              key={idx}
              onClick={() => onSelectSpeaker && onSelectSpeaker(c.speaker)}
              className={`p-2 rounded-xl border text-xs transition-all ${
                onSelectSpeaker 
                  ? 'cursor-pointer hover:border-indigo-300 hover:bg-indigo-50/40 bg-slate-50/70' 
                  : 'bg-slate-50'
              }`}
            >
              <div className="flex items-center justify-between gap-1 mb-1">
                <div className="font-bold text-slate-800">
                  {c.speaker} <span className="text-[10px] text-slate-400 font-normal">({c.party})</span>
                </div>

                {isAgree && (
                  <span className="inline-flex items-center text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                    <CheckCircle2 className="w-2.5 h-2.5 mr-0.5" /> 【賛成】
                  </span>
                )}
                {isDisagree && (
                  <span className="inline-flex items-center text-[10px] font-bold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                    <XCircle className="w-2.5 h-2.5 mr-0.5" /> 【反対】
                  </span>
                )}
                {!isAgree && !isDisagree && (
                  <span className="text-[10px] text-slate-500 font-medium">{c.vote}</span>
                )}
              </div>

              <div className="text-[11px] text-slate-600 line-clamp-1">
                📌 {c.headline}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}