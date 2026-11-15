import React from 'react';

// Keep the recorded source link; this guide is a separate, conditional route.
export default function KyotoMinuteGuideLink({ statement, cityCode, className = '' }) {
  if (cityCode !== 'kyoto') return null;
  const source = statement?.official_url || statement?.source_url || statement?.url || statement?.doc_url || statement?.evidence_url;
  try {
    const url = new URL(source);
    if (!['http:', 'https:'].includes(url.protocol) || url.hostname !== 'ssp.kaigiroku.net' || !url.pathname.startsWith('/tenant/kyoto/')) return null;
  } catch {
    return null;
  }

  return (
    <p className={`text-xs leading-relaxed text-slate-500 ${className}`}>
      原典を直接開けない場合は、
      <a
        href="https://www2.city.kyoto.lg.jp/shikai/kaigiroku/index.html"
        target="_blank"
        rel="noopener noreferrer"
        onClick={event => event.stopPropagation()}
        className="text-indigo-700 underline underline-offset-2 hover:text-indigo-900"
      >
        京都市会公式の会議録検索
      </a>
      からご確認ください。
    </p>
  );
}
