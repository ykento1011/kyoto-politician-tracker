import React, { useState } from 'react';
import { Flag } from 'lucide-react';
import ReportIssueModal from './ReportIssueModal';

export default function ReportIssueButton({
  targetUrl,
  speaker = '',
  meetingDate = '',
  targetId = '',
  municipality = '京都市'
}) {
  const [isOpen, setIsOpen] = useState(false);

  if (!targetUrl) return null;

  return (
    <>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(true);
        }}
        className="text-slate-400 hover:text-rose-500 p-1 rounded hover:bg-rose-50 transition-colors cursor-pointer inline-flex items-center shrink-0"
        title="一次資料のリンク切れ・資料の誤りを報告"
        aria-label="一次資料の不備を報告"
      >
        <Flag className="w-3.5 h-3.5" />
      </button>

      <ReportIssueModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        reportContext={{
          targetUrl,
          speaker,
          meetingDate,
          targetId,
          municipality
        }}
      />
    </>
  );
}
