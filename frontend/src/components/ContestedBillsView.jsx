import React, { useState, useMemo } from 'react';
import { 
  ArrowLeft, Flame, Search, Filter, CheckCircle2, XCircle, 
  Sparkles, ExternalLink, Scale, ChevronDown, Tag, AlertTriangle
} from 'lucide-react';

export default function ContestedBillsView({

  // 賛否データを日本語に正規化するヘルパー関数
  const normalizeVote = (val) => {
    if (!val) return '不明';
    const v = String(val).toLowerCase();
    if (v === 'for' || v === '賛成') return '賛成';
    if (v === 'against' || v === '反対') return '反対';
    if (v === 'split' || v === '対応割れ') return '対応割れ';
    if (v === 'abstain' || v === '棄権') return '棄権';
    if (v === 'absent' || v === '欠席') return '欠席';
    return val;
  };

  initialCategory = '',
  billIssues = [],
  votesData = [],
  onClose,
  onSpeakerClick
}) {
  const [selectedCat, setSelectedCat] = useState(initialCategory);
  const [selectedSession, setSelectedSession] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [resultFilter, setResultFilter] = useState(''); // '可決', '否決', etc.

  // 議案番号＋会期で votesData をマップ化（会派別賛否の表示用）
  const votesMap = useMemo(() => {
    const map = {};
    votesData.forEach(v => {
      const key = `${v.session_name}_${v.bill_number}`;
      map[key] = v;
    });
    return map;
  }, [votesData]);

  // 利用可能な会期一覧の抽出
  const sessions = useMemo(() => {
    const set = new Set(billIssues.map(b => b.session_name).filter(Boolean));
    return Array.from(set);
  }, [billIssues]);

  // 分野判定ヘルパー
  const getCategoryForBill = (b) => {
    const text = `${b.title} ${b.key_conflict} ${b.background}`;
    if (text.includes('都市計画') || text.includes('建築') || text.includes('開発') || text.includes('住宅') || text.includes('新幹線')) return '都市再生・交通インフラ';
    if (text.includes('観光') || text.includes('宿泊税') || text.includes('産業') || text.includes('万博') || text.includes('芸術大学') || text.includes('市場')) return '産業・観光・地域経済';
    if (text.includes('医療') || text.includes('健康保険') || text.includes('国保') || text.includes('介護') || text.includes('保護') || text.includes('衛生')) return '福祉・医療・健康';
    if (text.includes('子ども') || text.includes('給食') || text.includes('学校') || text.includes('保育') || text.includes('児童')) return '子育て・教育';
    if (text.includes('予算') || text.includes('決算') || text.includes('報酬') || text.includes('給与') || text.includes('定数') || text.includes('手続')) return '財政・行革';
    if (text.includes('原発') || text.includes('温暖化') || text.includes('環境') || text.includes('下水') || text.includes('水道')) return 'くらし・環境・エネルギー';
    if (text.includes('防災') || text.includes('消防') || text.includes('災害') || text.includes('耐震')) return '防災・減災・治安';
    if (text.includes('文化') || text.includes('景観') || text.includes('世界遺産') || text.includes('歴史')) return '文化・景観・歴史';
    return '市政全般';
  };

  // フィルタリング処理
  const filteredBills = useMemo(() => {
    return billIssues.filter(bill => {
      const cat = getCategoryForBill(bill);
      if (selectedCat && cat !== selectedCat) return false;
      if (selectedSession && bill.session_name !== selectedSession) return false;
      
      const voteObj = votesMap[`${bill.session_name}_${bill.bill_number}`];
      const resultText = voteObj ? voteObj.result : '';
      if (resultFilter && !resultText.includes(resultFilter)) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const target = `${bill.title} ${bill.key_conflict} ${bill.background} ${bill.agree_logic} ${bill.disagree_logic}`.toLowerCase();
        if (!target.includes(q)) return false;
      }
      return true;
    });
  }, [billIssues, selectedCat, selectedSession, resultFilter, searchQuery, votesMap]);

  return (
    <main className="max-w-6xl mx-auto py-8 px-6 animate-in fade-in slide-in-from-bottom-4 duration-300 w-full">
      
      {/* 画面トップ戻るボタン */}
      <div className="flex items-center justify-between mb-6">
        <button 
          onClick={onClose}
          className="inline-flex items-center text-xs font-bold text-slate-500 hover:text-indigo-600 transition-colors bg-white px-3.5 py-2 rounded-xl border border-slate-200 shadow-2xs"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />トップ画面に戻る
        </button>
        <div className="text-xs font-bold text-slate-400">
          全任期激戦議案データベース（2023–2026年）
        </div>
      </div>

      {/* ヘッダーカード */}
      <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-200 shadow-sm mb-6">
        <div className="flex items-center gap-2.5 mb-2">
          <div className="w-10 h-10 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600">
            <Flame className="w-5 h-5 fill-rose-500" />
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-black text-slate-900">市議会 激戦・対立議案詳細アーカイブ</h1>
            <p className="text-xs text-slate-500 font-medium mt-0.5">
              全会一致とならず各会派の理念や政策方針が真っ向から対立した重要議案の全記録
            </p>
          </div>
        </div>

        {/* フィルター・検索バー */}
        <div className="mt-6 pt-6 border-t border-slate-100 flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="議案名・対立軸・キーワード（例: 給食、新幹線、宿泊税）で検索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs font-bold text-slate-800 placeholder-slate-400 outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedCat}
              onChange={(e) => setSelectedCat(e.target.value)}
              className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-700 outline-none cursor-pointer hover:border-indigo-400"
            >
              <option value="">全分野（すべて）</option>
              <option value="子育て・教育">子育て・教育</option>
              <option value="財政・行革">財政・行革</option>
              <option value="都市再生・交通インフラ">都市再生・交通インフラ</option>
              <option value="産業・観光・地域経済">産業・観光・地域経済</option>
              <option value="福祉・医療・健康">福祉・医療・健康</option>
              <option value="くらし・環境・エネルギー">くらし・環境・エネルギー</option>
              <option value="防災・減災・治安">防災・減災・治安</option>
              <option value="文化・景観・歴史">文化・景観・歴史</option>
            </select>

            <select
              value={selectedSession}
              onChange={(e) => setSelectedSession(e.target.value)}
              className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-700 outline-none cursor-pointer hover:border-indigo-400"
            >
              <option value="">全会期（すべて）</option>
              {sessions.map(s => <option key={s} value={s}>{s}</option>)}
            </select>

            <select
              value={resultFilter}
              onChange={(e) => setResultFilter(e.target.value)}
              className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-700 outline-none cursor-pointer hover:border-indigo-400"
            >
              <option value="">全議決結果</option>
              <option value="可決">可決</option>
              <option value="否決">否決</option>
              <option value="認定">認定</option>
              <option value="同意">同意</option>
            </select>
          </div>
        </div>
      </div>

      {/* 件数表示 */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-black text-slate-700">
          該当する激戦議案: <span className="text-rose-600 text-sm">{filteredBills.length}</span> 件
        </span>
        {(selectedCat || selectedSession || searchQuery || resultFilter) && (
          <button 
            onClick={() => { setSelectedCat(''); setSelectedSession(''); setSearchQuery(''); setResultFilter(''); }}
            className="text-[11px] font-bold text-indigo-600 hover:underline"
          >
            条件をリセット
          </button>
        )}
      </div>

      {/* 議案リスト */}
      <div className="space-y-4">
        {filteredBills.map((bill, idx) => {
          const voteObj = votesMap[`${bill.session_name}_${bill.bill_number}`];
          const votes = voteObj ? voteObj.votes : {};
          const result = voteObj ? voteObj.result : '';
          const categoryTag = getCategoryForBill(bill);

          return (
            <article key={bill.id || idx} className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
              
              {/* 議案タイトル・メタバッジ */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pb-3 border-b border-slate-100">
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-black text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                      {bill.session_name} ({bill.bill_number})
                    </span>
                    <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded flex items-center gap-1">
                      <Tag className="w-2.5 h-2.5" />{categoryTag}
                    </span>
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
                  <h2 className="text-base font-black text-slate-900 leading-snug">
                    {bill.title}
                  </h2>
                </div>

                {voteObj?.source_url && (
                  <a 
                    href={voteObj.source_url} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="text-[11px] font-bold text-slate-400 hover:text-indigo-600 inline-flex items-center gap-1 shrink-0 self-start sm:self-auto bg-slate-50 hover:bg-slate-100 px-2.5 py-1.5 rounded-lg border border-slate-200 transition-colors"
                  >
                    市会公式審議結果 <ExternalLink className="w-3 h-3 opacity-60" />
                  </a>
                )}
              </div>

              {/* 対立軸 ＆ 概要背景 */}
              <div className="bg-gradient-to-br from-slate-50 to-indigo-50/20 p-4 rounded-xl border border-slate-200/80 space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-black text-slate-900">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  対立の核心: {bill.key_conflict}
                </div>
                <p className="text-xs text-slate-600 leading-relaxed font-medium">
                  {bill.background}
                </p>
              </div>

              {/* 賛成派の論理 vs 反対派の論理 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                <div className="bg-emerald-50/60 p-4 rounded-xl border border-emerald-100/90 space-y-1.5">
                  <span className="text-xs font-black text-emerald-800 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />賛成派の政治的論理
                  </span>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {bill.agree_logic}
                  </p>
                </div>

                <div className="bg-rose-50/60 p-4 rounded-xl border border-rose-100/90 space-y-1.5">
                  <span className="text-xs font-black text-rose-800 flex items-center gap-1">
                    <XCircle className="w-3.5 h-3.5 text-rose-600" />反対派の政治的論理
                  </span>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {bill.disagree_logic}
                  </p>
                </div>
              </div>

              {/* 各会派・議員の賛否スタンス一覧 */}
              {Object.keys(votes).length > 0 && (
                <div className="pt-2 border-t border-slate-100">
                  <span className="text-[10px] font-bold text-slate-400 block mb-2">各会派・無所属の評決態度</span>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                    {Object.entries(votes).map(([grp, v]) => {
                      const normV = normalizeVote(v);
                        const isAgree = normV === '賛成';
                      return (
                        <div key={grp} className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100 text-xs">
                          <span className="font-bold text-slate-700 truncate mr-2" title={grp}>{grp}</span>
                          <span className={`font-black shrink-0 inline-flex items-center gap-0.5 text-[11px] ${
                            isAgree ? 'text-emerald-600' : 'text-rose-600'
                          }`}>
                            {isAgree ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />} {normV}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

            </article>
          );
        })}

        {filteredBills.length === 0 && (
          <div className="text-center py-24 bg-white rounded-2xl border border-dashed border-slate-300">
            <Flame className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-slate-500 font-bold text-sm">該当する激戦議案は見つかりませんでした。</p>
            <p className="text-slate-400 text-xs mt-1">検索条件を変更するか、リセットしてください。</p>
          </div>
        )}
      </div>

    </main>
  );
}