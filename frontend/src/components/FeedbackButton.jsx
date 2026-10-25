import React from 'react';
import { MessageSquarePlus, ExternalLink } from 'lucide-react';

export default function FeedbackButton() {
  const FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSf-GwUeTmRg05kBYyf0LJRoGwexG7Jn_G0-C0q3GynYayxFBQ/viewform?usp=send_form";

  return (
    <aside aria-label="情報提供・修正フォーム" className="fixed bottom-5 right-5 z-40">
      <a
        href={FORM_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="group flex items-center gap-2 bg-white/95 hover:bg-amber-50 text-slate-700 hover:text-amber-900 px-3 py-2 sm:px-3.5 sm:py-2.5 rounded-full border border-slate-200/90 hover:border-amber-300 shadow-md hover:shadow-lg transition-all duration-200 backdrop-blur-xs cursor-pointer"
        title="一次資料の誤り報告・情報提供フォームを開く"
      >
        <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 group-hover:bg-amber-500 group-hover:text-white transition-colors shrink-0">
          <MessageSquarePlus className="w-3.5 h-3.5" />
        </div>
        <span className="text-xs font-bold tracking-tight hidden sm:inline">
          一次資料の修正・情報提供
        </span>
        <span className="text-xs font-bold tracking-tight sm:hidden">
          修正報告
        </span>
        <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-amber-600 transition-colors shrink-0" />
      </a>
    </aside>
  );
}