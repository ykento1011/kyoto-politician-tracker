import React, { useState, useEffect } from 'react';
import { Sparkles, Landmark, ExternalLink, Loader2, AlertCircle, Info } from 'lucide-react';
import { openOfficialMinute, getOfficialLinkTooltip } from '../utils/officialLink';

const DAILY_LIMIT = 10;
const COOLDOWN_MS = 10000;

function checkRateLimit() {
  const today = new Date().toISOString().slice(0, 10);
  const raw = localStorage.getItem('gikai_ai_limit');
  let data = { date: today, count: 0, lastTime: 0 };

  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      if (parsed.date === today) {
        data = parsed;
      }
    } catch (e) {}
  }

  const now = Date.now();
  if (now - data.lastTime < COOLDOWN_MS) {
    return { allowed: false, reason: 'cooldown' };
  }
  if (data.count >= DAILY_LIMIT) {
    return { allowed: false, reason: 'daily_exceeded', remaining: 0 };
  }

  return { allowed: true, remaining: DAILY_LIMIT - data.count };
}

function recordUsage() {
  const today = new Date().toISOString().slice(0, 10);
  const raw = localStorage.getItem('gikai_ai_limit');
  let count = 0;

  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      if (parsed.date === today) count = parsed.count;
    } catch (e) {}
  }

  const updated = { date: today, count: count + 1, lastTime: Date.now() };
  localStorage.setItem('gikai_ai_limit', JSON.stringify(updated));
}

export default function AiSearchAnswer({ query, filteredThreads }) {
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [limitNotice, setLimitNotice] = useState(null);

  useEffect(() => {
    const cleanQuery = (query || '').trim();
    if (cleanQuery.length < 2 || !filteredThreads || filteredThreads.length === 0) {
      setAnswer('');
      setSources([]);
      setLimitNotice(null);
      return;
    }

    const limitStatus = checkRateLimit();
    if (!limitStatus.allowed) {
      if (limitStatus.reason === 'daily_exceeded') {
        setLimitNotice('本日のAI回答利用上限（10回）に達しました。下の会議録一覧をご参照ください。');
      } else {
        setLimitNotice('少し時間をおいてから再度お試しください。');
      }
      return;
    }

    const fetchAnswer = async () => {
      setIsLoading(true);
      setLimitNotice(null);

      const topContexts = filteredThreads.slice(0, 3);
      setSources(topContexts);

      try {
        const res = await fetch('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: cleanQuery,
            contexts: topContexts
          })
        });

        if (!res.ok) {
          throw new Error('回答の取得に失敗しました');
        }

        const data = await res.json();
        if (data.error) throw new Error(data.error);

        setAnswer(data.answer);
        recordUsage();
      } catch (err) {
        console.warn('AI回答スキップ:', err);
      } finally {
        setIsLoading(false);
      }
    };

    const timer = setTimeout(fetchAnswer, 800);
    return () => clearTimeout(timer);
  }, [query, filteredThreads]);

  if (!query || query.trim().length < 2) return null;

  if (limitNotice) {
    return (
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-xs text-slate-500 flex items-center gap-2">
        <Info className="w-4 h-4 text-slate-400 shrink-0" />
        <span>{limitNotice}</span>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-indigo-200/80 p-5 shadow-sm space-y-3.5 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-black text-indigo-700">
          <Sparkles className="w-4 h-4 text-indigo-600 fill-indigo-100" />
          <span>議会ログに基づく AI 政策アンサー</span>
        </div>
        <span className="text-[10px] font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
          Gemini 2.5 Flash
        </span>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 py-3 text-xs text-slate-500 font-medium">
          <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
          <span>該当する議事録を精査し、要点を抽出中...</span>
        </div>
      ) : answer ? (
        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-800 leading-relaxed bg-indigo-50/40 p-4 rounded-xl border border-indigo-100/60">
            {answer}
          </p>

          {sources.length > 0 && (
            <div className="pt-1 flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-bold text-slate-400">根拠となった会議録:</span>
              {sources.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => openOfficialMinute(s)}
                  title={getOfficialLinkTooltip(s)}
                  className="inline-flex items-center text-[10px] font-bold text-slate-600 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50 border border-slate-200 px-2 py-1 rounded-md transition-colors cursor-pointer group"
                >
                  <Landmark className="w-3 h-3 mr-1 text-indigo-500" />
                  <span>{s.speaker}議員 ({s.meeting_date})</span>
                  <ExternalLink className="w-2.5 h-2.5 ml-1 text-slate-400 group-hover:text-indigo-600" />
                </button>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}