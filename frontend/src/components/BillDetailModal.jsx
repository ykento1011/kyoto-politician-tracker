import React, { useMemo } from 'react';
import { 
  X, CheckCircle2, XCircle, Sparkles, ExternalLink, User, 
  Flame, Tag, Scale, ArrowRight, AlertTriangle 
} from 'lucide-react';

// 異体字・旧字体のエイリアス辞書
const ALIAS_MAP = {
  '井崎敦子': '井﨑敦子',
  '井﨑敦子': '井崎敦子',
  '繁隆夫': '繁隆夫',
  '繁隆夫': '繁隆夫'
};

export default function BillDetailModal({
  isOpen,
  onClose,
  bill,
  issue,
  speakerStats = [],
  onSpeakerClick
, cityCode = 'kyoto'}) {
  if (!isOpen || !bill) return null;

  // 各議員の所属会派・無所属ステータスに基づき、賛成議員・反対議員を特定
  const { agreeCouncilors, disagreeCouncilors } = useMemo(() => {
    const agree = [];
    const disagree = [];
    const votes = bill.votes || {};

    speakerStats.forEach(spk => {
      const isIndependent = !spk.partyGroup || spk.partyGroup === '無所属';
      let voteVal = null;

      // 1. 会派による一括照合
      if (!isIndependent && spk.partyGroup) {
        for (const [groupName, v] of Object.entries(votes)) {
          if (groupName.includes(spk.partyGroup) || spk.partyGroup.includes(groupName)) {
            voteVal = v;
            break;
          }
        }
      }

      // 2. 個人名（無所属など）による照合（異体字・空白揺らぎも自動吸収）
      if (!voteVal) {
        const rawName = spk.speaker || '';
        const cleanSpkName = rawName.replace(/\s+/g, '');
        const aliasName = ALIAS_MAP[cleanSpkName] || ALIAS_MAP[rawName];

        for (const [key, v] of Object.entries(votes)) {
          const cleanKey = key.replace(/\s+/g, '');
          if (
            cleanKey.includes(cleanSpkName) || cleanSpkName.includes(cleanKey) ||
            (aliasName && (cleanKey.includes(aliasName) || aliasName.includes(cleanKey)))
          ) {
            voteVal = v;
            break;
          }
        }
      }

      if (voteVal === '賛成') agree.push(spk);
      else if (voteVal === '反対') disagree.push(spk);
    });

    return { agreeCouncilors: agree, disagreeCouncilors: disagree };
  }, [bill, speakerStats]);

  const votes = bill.votes || {};
  const vValues = Object.values(votes);
  const isContested = vValues.includes('賛成') && vValues.includes('反対');
  const result = bill.result || '';

  return (
    <div 
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-3xl shadow-2xl border border-slate-200 w-full max-w-3xl overflow-hidden max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* モーダルヘッダー */}
        <div className="p-6 border-b border-slate-100 flex items-start justify-between bg-slate-50/70">
          <div className="space-y-1.5 flex-1 pr-4">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] font-black text-slate-500 bg-slate-200/80 px-2 py-0.5 rounded font-mono">
                {bill.session_name} ({bill.bill_number})
              </span>
              {isContested ? (
                <span className="text-[10px] font-black px-2 py-0.5 rounded bg-rose-50 text-rose-600 border border-rose-200 flex items-center gap-1">
                  <Flame className="w-2.5 h-2.5 fill-rose-500 text-rose-500" />激論議案
                </span>
              ) : (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
                  全会一致
                </span>
              )}
              {result && (
                <span className={`text-[10px] font-black px-2 py-0.5 rounded ${
                  result.includes('可決') || result.includes('認定') || result.includes('同意')
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-rose-50 text-rose-700 border border-rose-200'
                }`}>
                  結果: {result}
                </span>
              )}
            </div>
            <h2 className="text-lg md:text-xl font-black text-slate-900 leading-snug">
              {bill.title}
            </h2>
          </div>

          <button 
            onClick={onClose}
            className="w-9 h-9 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-400 hover:text-slate-700 flex items-center justify-center transition-colors shrink-0 cursor-pointer"
            title="閉じる"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* モーダルコンテンツ */}
        <div className="p-6 overflow-y-auto space-y-6">
          
          {/* AI争点解説 */}
          {issue ? (
            <div className="bg-gradient-to-br from-indigo-50/50 to-slate-50 p-5 rounded-2xl border border-indigo-100/80 space-y-3">
              <div>
                <div className="flex items-center gap-1.5 text-xs font-black text-indigo-900 mb-1">
                  <Sparkles className="w-4 h-4 text-amber-500" />
                  対立の核心: {issue.key_conflict}
                </div>
                <p className="text-xs text-slate-600 leading-relaxed font-medium">
                  {issue.background}
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                <div className="bg-emerald-50/80 p-3.5 rounded-xl border border-emerald-100">
                  <span className="text-xs font-black text-emerald-800 flex items-center gap-1 mb-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />賛成派の主な論理
                  </span>
                  <p className="text-slate-700 text-xs leading-relaxed">{issue.agree_logic}</p>
                </div>
                <div className="bg-rose-50/80 p-3.5 rounded-xl border border-rose-100">
                  <span className="text-xs font-black text-rose-800 flex items-center gap-1 mb-1">
                    <XCircle className="w-3.5 h-3.5 text-rose-600" />反対派の主な論理
                  </span>
                  <p className="text-slate-700 text-xs leading-relaxed">{issue.disagree_logic}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 text-xs text-slate-500">
              {Object.values(bill.votes || {}).includes('反対') ? '会派間で賛否が分かれた重要議案です。' : '全会一致で可決・認定された議案です。会派間の対立論点は生じていません。'}
            </div>
          )}

          {/* 賛否議員一覧 */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-extrabold text-slate-900 flex items-center gap-1.5">
                <User className="w-4 h-4 text-indigo-600" />
                賛否議員一覧（クリックで各議員の詳細へ）
              </h3>
              <span className="text-[10px] text-slate-400 font-medium">
                ※会派拘束および無所属記録に基づき算出
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              {/* 賛成議員ブロック */}
              <div className="bg-emerald-50/30 rounded-2xl p-4 border border-emerald-100">
                <div className="flex items-center justify-between mb-3 pb-2 border-b border-emerald-100">
                  <span className="text-xs font-black text-emerald-800 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    賛成した議員 ({agreeCouncilors.length}名)
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5 max-h-56 overflow-y-auto pr-1">
                  {agreeCouncilors.map(c => (
                    <button
                      key={c.speaker}
                      onClick={() => {
                        onClose();
                        onSpeakerClick(c.speaker);
                      }}
                      className="px-2.5 py-1 bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-700 rounded-lg border border-slate-200 hover:border-emerald-300 text-xs font-bold transition-all flex items-center gap-1 shadow-2xs group cursor-pointer"
                      title={`${c.district} / ${c.partyGroup}`}
                    >
                      <span>{c.speaker}</span>
                      <ArrowRight className="w-2.5 h-2.5 text-slate-300 group-hover:text-emerald-600 transition-colors" />
                    </button>
                  ))}
                  {agreeCouncilors.length === 0 && (
                    <span className="text-xs text-slate-400">賛成議員データなし</span>
                  )}
                </div>
              </div>

              {/* 反対議員ブロック */}
              <div className="bg-rose-50/30 rounded-2xl p-4 border border-rose-100">
                <div className="flex items-center justify-between mb-3 pb-2 border-b border-rose-100">
                  <span className="text-xs font-black text-rose-800 flex items-center gap-1">
                    <XCircle className="w-3.5 h-3.5 text-rose-600" />
                    反対した議員 ({disagreeCouncilors.length}名)
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5 max-h-56 overflow-y-auto pr-1">
                  {disagreeCouncilors.map(c => (
                    <button
                      key={c.speaker}
                      onClick={() => {
                        onClose();
                        onSpeakerClick(c.speaker);
                      }}
                      className="px-2.5 py-1 bg-white hover:bg-rose-50 text-slate-700 hover:text-rose-700 rounded-lg border border-slate-200 hover:border-rose-300 text-xs font-bold transition-all flex items-center gap-1 shadow-2xs group cursor-pointer"
                      title={`${c.district} / ${c.partyGroup}`}
                    >
                      <span>{c.speaker}</span>
                      <ArrowRight className="w-2.5 h-2.5 text-slate-300 group-hover:text-rose-600 transition-colors" />
                    </button>
                  ))}
                  {disagreeCouncilors.length === 0 && (
                    <span className="text-xs text-slate-400">反対議員なし（全会一致）</span>
                  )}
                </div>
              </div>

            </div>
          </div>

          {/* 会派・無所属別投票態度一覧 */}
          {Object.keys(votes).length > 0 && (
            <div className="space-y-2 pt-2 border-t border-slate-100">
              <span className="text-[11px] font-bold text-slate-500 block">会派・無所属別の評決結果</span>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {Object.entries(votes).map(([grp, v]) => {
                  const isAgree = v === '賛成';
                  return (
                    <div key={grp} className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-200/80 text-xs">
                      <span className="font-bold text-slate-700 truncate mr-2" title={grp}>{grp}</span>
                      <span className={`font-black shrink-0 inline-flex items-center gap-0.5 text-[11px] ${
                        isAgree ? 'text-emerald-600' : 'text-rose-600'
                      }`}>
                        {isAgree ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                        {v}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 公式リンク */}
          {bill.source_url && (
            <div className="pt-2 text-right">
              <a 
                href={bill.source_url || (cityCode === "osaka" ? "https://www.city.osaka.lg.jp/shikai/page/0000001592.html" : "https://www.city.kyoto.lg.jp/shikai/")} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="inline-flex items-center text-xs font-bold text-indigo-600 hover:underline"
              >
                {cityCode === 'osaka' ? '大阪市会 公式審議結果ページを開く' : '京都市会 公式審議結果ページを開く'} <ExternalLink className="w-3 h-3 ml-1" />
              </a>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}