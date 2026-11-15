import React from 'react';
import { ExternalLink } from 'lucide-react';
import { budgetSourceLabel } from './BudgetEvidence';

export default function ProgressEvidence({ event }) {
  if (!event) return null;
  return (
    <section className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-5" data-progress-event={event.kind}>
      <h4 className="text-sm font-bold text-amber-900">最新の公式発表</h4>
      <p className="text-xs text-slate-600 mt-1">発表日：{event.announced_at}</p>
      <p className="text-sm text-slate-900 leading-relaxed mt-2">{event.summary}</p>
      <p className="text-xs text-slate-600 mt-2">{event.source_title}</p>
      <a className="text-xs text-amber-800 font-bold inline-flex items-center gap-1 mt-2"
        href={event.source_url} target="_blank" rel="noopener noreferrer">
        {budgetSourceLabel(event.source_url)}<ExternalLink className="w-3 h-3" />
      </a>
    </section>
  );
}
