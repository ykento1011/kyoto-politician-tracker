import os
import json
from pathlib import Path

root = Path(".").resolve()
if root.name == "data-pipeline":
    root = root.parent

# ==========================================
# 1. ThreadCard.jsx の完全修復 (actualStmt エラーの撲滅)
# ==========================================
thread_card_path = root / "frontend" / "src" / "components" / "ThreadCard.jsx"

clean_thread_card_code = '''import React, { useState } from 'react';
import { FileText, Lightbulb, MessageCircle, User, Landmark, ExternalLink, ChevronDown } from 'lucide-react';
import { cleanName, cleanAuditorNote } from '../utils/styleHelpers';
import { openOfficialMinute, getOfficialLinkTooltip } from '../utils/officialLink';

export default function ThreadCard({
  stmt,
  statement,
  thread,
  speakerInfo,
  onSpeakerClick,
  onViewContext,
  showSpeakerHeader = true,
  cityCode
}) {
  // どの引数名(stmt, statement, thread)で渡されても確実に安全に取得
  const target = stmt || statement || thread || {};

  // URLパス または props/データから大阪を判定
  const isOsakaUrl = typeof window !== 'undefined' && window.location.pathname.startsWith('/osaka');
  const isOsakaThread = isOsakaUrl || 
                        cityCode === 'osaka' || 
                        target?.council === '大阪市会' || 
                        target?.council === '大阪市' ||
                        (typeof target?.meeting_name === 'string' && target.meeting_name.includes('大阪市')) ||
                        (typeof target?.committee_name === 'string' && target.committee_name.includes('大阪市'));

  const councilOriginalLabel = isOsakaThread ? '大阪市会 公式原本で確認' : '京都市会 公式原本で確認';

  const [isNoteExpanded, setIsNoteExpanded] = useState(false);

  const activeMetrics = [
    { label: '根拠・データ', val: target.evidence_score, color: 'bg-indigo-500' },
    { label: '対案・是正策', val: target.solution_score, color: 'bg-emerald-500' },
    { label: '地域解像度', val: target.local_focus_score, color: 'bg-amber-500' },
    { label: '議論の進展', val: target.constructive_score, color: 'bg-purple-500' }
  ].filter((m) => m.val > 0);

  const auditorNoteText = target.scoring_reasoning ? cleanAuditorNote(target.scoring_reasoning) : "";

  return (
    <article className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs hover:shadow-md transition-all duration-200 flex flex-col justify-between space-y-4">
      <div className="space-y-3">
        {/* 発言者ヘッダー */}
        {showSpeakerHeader && (
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 font-bold text-xs shrink-0">
                <User className="w-4 h-4 text-slate-500" />
              </div>
              <div>
                <button
                  onClick={() => onSpeakerClick && onSpeakerClick(target.speaker)}
                  className="font-bold text-sm text-slate-900 hover:text-indigo-600 transition-colors text-left cursor-pointer flex items-center gap-1.5"
                >
                  <span>{cleanName(target.speaker || '議員')}</span>
                </button>
                <div className="text-[10px] text-slate-400 font-medium">
                  {target.meeting_date || ''} {target.meeting_name || ''}
                </div>
              </div>
            </div>
            {target.category && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                {target.category}
              </span>
            )}
          </div>
        )}

        {/* 質疑タイトル・要約 */}
        <div className="space-y-1.5">
          <h3 className="font-bold text-sm text-slate-900 leading-snug">
            {target.topic || target.summary_topic || '政策質疑'}
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed line-clamp-3">
            {target.question_summary || target.content || ''}
          </p>
        </div>

        {/* スコア指標 */}
        {activeMetrics.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {activeMetrics.map((m, idx) => (
              <span key={idx} className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200/60 text-slate-600">
                <span className={`w-1.5 h-1.5 rounded-full ${m.color}`} />
                {m.label} <span className="font-mono text-slate-800">{m.val}</span>
              </span>
            ))}
          </div>
        )}

        {/* AI評価理由 (折りたたみ) */}
        {auditorNoteText && (
          <div className="pt-1">
            <button
              onClick={() => setIsNoteExpanded(!isNoteExpanded)}
              className="text-[11px] font-bold text-slate-500 hover:text-indigo-600 flex items-center gap-1 transition-colors cursor-pointer"
            >
              <Lightbulb className="w-3 h-3 text-amber-500" />
              <span>評価理由・分析メモ</span>
              <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${isNoteExpanded ? 'rotate-180' : ''}`} />
            </button>
            {isNoteExpanded && (
              <div className="mt-2 p-3 bg-amber-50/50 rounded-xl border border-amber-200/60 text-[11px] text-amber-950/80 leading-relaxed">
                {auditorNoteText}
              </div>
            )}
          </div>
        )}
      </div>

      {/* フッターアクション */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
        <button
          onClick={() => onViewContext && onViewContext(target)}
          className="inline-flex items-center gap-1 text-xs font-bold text-indigo-600 hover:text-indigo-700 transition-colors cursor-pointer"
        >
          <MessageCircle className="w-3.5 h-3.5" />
          <span>前後の対話を見る</span>
        </button>

        <button
          onClick={() => openOfficialMinute(target, isOsakaThread ? 'osaka' : 'kyoto')}
          title={getOfficialLinkTooltip(target, isOsakaThread ? 'osaka' : 'kyoto')}
          className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
        >
          <Landmark className="w-3 h-3" />
          <span>{councilOriginalLabel}</span>
          <ExternalLink className="w-2.5 h-2.5 opacity-60" />
        </button>
      </div>
    </article>
  );
}
'''
thread_card_path.write_text(clean_thread_card_code, encoding="utf-8")
print("✅ ThreadCard.jsx を安全なコードで完全修復しました。")

# ==========================================
# 2. Vercel SPA リライト設定を二重配備
# ==========================================
vercel_rewrite = {
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
root_vercel = root / "vercel.json"
frontend_vercel = root / "frontend" / "vercel.json"

root_vercel.write_text(json.dumps(vercel_rewrite, indent=2), encoding="utf-8")
frontend_vercel.write_text(json.dumps(vercel_rewrite, indent=2), encoding="utf-8")
print("✅ vercel.json を root および frontend/ の両方に配備しました。")

# ==========================================
# 3. 原因ファイル frontend/public/osaka/index.html を物理削除
# ==========================================
bad_html = root / "frontend" / "public" / "osaka" / "index.html"
if bad_html.exists():
    bad_html.unlink()
    print("✅ frontend/public/osaka/index.html を物理削除しました。")
else:
    print("ℹ️ frontend/public/osaka/index.html は既にローカルに存在しません。")
