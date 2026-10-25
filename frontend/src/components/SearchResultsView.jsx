import React, { useState } from 'react';
import { 
  ArrowLeft, MessageCircle, User, Scale, Search, 
  GitCompare, ArrowRight, Info
} from 'lucide-react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import ThreadCard from './ThreadCard';
import BillsSection from './BillsSection';
import AiSearchAnswer from './AiSearchAnswer';
import { cleanName } from '../utils/styleHelpers';

// activeCityCode フォールバック
export default function SearchResultsView({
  submittedQuery,
  onClearSearch,
  filteredThreads = [],
  filteredBills = [],
  filteredSpeakers = [],
  speakerStats = [],
  issuesMap = {},
  onlyContestedBills,
  setOnlyContestedBills,
  onSpeakerClick,
  onViewContext,
  onOpenCompare,
  onSelectBill,
  onOpenMethodology,
  onOpenTopicDetail
}) {
  const activeCityCode = typeof cityCode !== 'undefined' ? cityCode : (typeof window !== 'undefined' && window.location.pathname.startsWith('/osaka') ? 'osaka' : 'kyoto');
  const [activeTab, setActiveTab] = useState('threads');

  // 💡 検索結果が完全に0件かどうかの判定
  const isEmptyResult = filteredThreads.length === 0 && filteredBills.length === 0 && filteredSpeakers.length === 0;

  const formatSummaryRadar = (speaker) => [
    { subject: '根拠・データ', A: speaker.avg_evidence || 0, fullMark: 5 },
    { subject: '対案・是正', A: speaker.avg_solution || 0, fullMark: 5 },
    { subject: '地域解像度', A: speaker.avg_local_focus || 0, fullMark: 5 },
    { subject: '議論の進展', A: speaker.avg_constructive || 0, fullMark: 5 },
  ];

  return (
    <main className="max-w-6xl mx-auto py-8 px-6 animate-in fade-in slide-in-from-bottom-4 duration-300 w-full space-y-6">
      
      {/* 戻るボタン */}
      <div className="flex items-center justify-between">
        <button 
          onClick={onClearSearch}
          className="inline-flex items-center text-xs font-bold text-slate-500 hover:text-indigo-600 bg-white hover:bg-slate-50 border border-slate-200 px-3.5 py-2 rounded-xl shadow-2xs transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          検索をクリアしてトップへ戻る
        </button>
      </div>

      {/* 検索ヘッダー */}
      <header className="space-y-1">
        <div className="flex items-center gap-2">
          <Search className="w-5 h-5 text-indigo-500" />
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">
            「{submittedQuery}」<span className="text-slate-500 text-lg font-bold">の検索結果</span>
          </h1>
        </div>
        <p className="text-xs font-bold text-slate-500 ml-7">
          関連質疑 {filteredThreads.length}件 / 関連議案 {filteredBills.length}件 / 言及した議員 {filteredSpeakers.length}名
        </p>
      </header>

      {/* 論点の要旨・ポイント解説 ＆ 一次情報位置カード（0件時は自動で非表示になります） */}
      <AiSearchAnswer cityCode={activeCityCode}
        query={submittedQuery}
        filteredThreads={filteredThreads}
        onOpenTopicDetail={onOpenTopicDetail}
      />

      {/* 💡 0件専用の案内画面（Empty State） */}
      {isEmptyResult ? (
        <section className="bg-white rounded-2xl border border-slate-200 p-8 md:p-12 shadow-sm animate-in fade-in duration-300">
          <div className="max-w-2xl mx-auto space-y-6 text-center">
            
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-50 border border-slate-100 mb-2">
              <Search className="w-7 h-7 text-slate-300" />
            </div>
            
            <div>
              <h2 className="text-xl font-black text-slate-800 mb-2">
                「{submittedQuery}」に関する議論は見つかりませんでした
              </h2>
              <p className="text-sm font-medium text-slate-500 leading-relaxed">
                本議会の現任期（2023年5月〜）の議事録ログには、このキーワードに直接一致する質疑は記録されていません。
              </p>
            </div>

            <div className="bg-slate-50/80 rounded-xl p-6 text-left border border-slate-200 space-y-4 shadow-inner">
              <div>
                <h3 className="text-xs font-black text-indigo-700 flex items-center gap-1.5 mb-2 uppercase tracking-wider">
                  <Info className="w-4 h-4 text-indigo-500" /> 
                  なぜ0件になるのですか？（当サイトの設計思想）
                </h3>
                <p className="text-xs text-slate-700 leading-relaxed font-medium">
                  当サイトは<strong>「議会の公式記録（ファクト）」</strong>のみを根拠とするシステムです。<br />
                  例えば、国や都道府県の管轄であり、<strong>本市の予算や権限が直接及ばないテーマは、市議会で取り上げられにくい傾向</strong>があります。<br /><br />
                  一般的なAIのように事実に基づかない推測（ハルシネーション）で適当な回答をすることを防ぐため、議事録に一次情報が存在しない場合は、意図的に「0件」としてご案内する安全設計としています。
                </p>
              </div>

              <div className="pt-4 border-t border-slate-200/80">
                <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-wider mb-2.5">
                  💡 おすすめの検索方法・関連キーワード
                </h4>
                <div className="flex flex-wrap gap-2">
                  <span className="px-2.5 py-1 text-xs font-bold text-slate-600 bg-white border border-slate-200 rounded-md">
                    都市計画・景観
                  </span>
                  <span className="px-2.5 py-1 text-xs font-bold text-slate-600 bg-white border border-slate-200 rounded-md">
                    オーバーツーリズム
                  </span>
                  <span className="px-2.5 py-1 text-xs font-bold text-slate-600 bg-white border border-slate-200 rounded-md">
                    空き家対策
                  </span>
                  <button 
                    onClick={onClearSearch}
                    className="px-2.5 py-1 text-xs font-bold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 border border-indigo-100 rounded-md transition-colors cursor-pointer"
                  >
                    トップへ戻って主要論点から探す →
                  </button>
                </div>
              </div>
            </div>

          </div>
        </section>
      ) : (
        /* 1件以上ある場合は通常のタブとコンテンツを表示 */
        <>
          {/* 表示切り替えタブ */}
          <div className="flex items-center overflow-x-auto border-b border-slate-200 pb-px hide-scrollbar pt-2">
            <button
              onClick={() => setActiveTab('threads')}
              className={`flex items-center px-5 py-3 text-sm font-black whitespace-nowrap transition-colors border-b-2 cursor-pointer ${
                activeTab === 'threads' 
                  ? 'border-indigo-600 text-indigo-700 bg-indigo-50/50' 
                  : 'border-transparent text-slate-500 hover:bg-slate-50'
              }`}
            >
              <MessageCircle className="w-4 h-4 mr-2" />
              質疑スレッド ({filteredThreads.length})
            </button>
            <button
              onClick={() => setActiveTab('bills')}
              className={`flex items-center px-5 py-3 text-sm font-black whitespace-nowrap transition-colors border-b-2 cursor-pointer ${
                activeTab === 'bills' 
                  ? 'border-indigo-600 text-indigo-700 bg-indigo-50/50' 
                  : 'border-transparent text-slate-500 hover:bg-slate-50'
              }`}
            >
              <Scale className="w-4 h-4 mr-2" />
              議案・賛否の記録 ({filteredBills.length})
            </button>
            <button
              onClick={() => setActiveTab('speakers')}
              className={`flex items-center px-5 py-3 text-sm font-black whitespace-nowrap transition-colors border-b-2 cursor-pointer ${
                activeTab === 'speakers' 
                  ? 'border-indigo-600 text-indigo-700 bg-indigo-50/50' 
                  : 'border-transparent text-slate-500 hover:bg-slate-50'
              }`}
            >
              <User className="w-4 h-4 mr-2" />
              関連する議員 ({filteredSpeakers.length})
            </button>
          </div>

          {/* タブコンテンツ */}
          <div className="animate-in fade-in duration-300 min-h-[400px]">
            {activeTab === 'threads' && (
              <div className="space-y-6">
                {filteredThreads.length > 0 ? (
                  filteredThreads.map((stmt) => (
                    <ThreadCard cityCode={activeCityCode} 
                      key={stmt.id} 
                      stmt={stmt} 
                      speakerInfo={speakerStats.find(s => s.speaker === cleanName(stmt.speaker))} 
                      onSpeakerClick={onSpeakerClick} 
                      onViewContext={onViewContext} 
                      showSpeakerHeader={true} 
                      onOpenMethodology={onOpenMethodology}
                    />
                  ))
                ) : (
                  <div className="text-center py-20 text-slate-500 bg-white rounded-2xl border border-slate-200">
                    このキーワードに一致する質疑は見つかりませんでした。
                  </div>
                )}
              </div>
            )}

            {activeTab === 'bills' && (
              <BillsSection
                filteredBills={filteredBills}
                onlyContestedBills={onlyContestedBills}
                setOnlyContestedBills={setOnlyContestedBills}
                issuesMap={issuesMap}
                onSelectBill={onSelectBill}
              />
            )}

            {activeTab === 'speakers' && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredSpeakers.length > 0 ? (
                  filteredSpeakers.map((speaker) => (
                    <article 
                      key={speaker.speaker} 
                      onClick={() => onSpeakerClick(speaker.speaker)} 
                      className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-lg hover:border-indigo-300 transition-all duration-300 cursor-pointer flex flex-col group relative"
                    >
                      <div className="p-5 border-b border-slate-100 flex justify-between items-start bg-slate-50/50">
                        <div>
                          <h2 className="text-lg font-black text-slate-900 tracking-tight group-hover:text-indigo-700 transition-colors">
                            {speaker.speaker}
                          </h2>
                          <div className="flex items-center gap-1.5 mt-0.5 text-[11px] font-bold text-slate-500">
                            <span className="bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded border border-slate-300">
                              {speaker.district}
                            </span>
                            <span className="truncate max-w-[150px]">{speaker.partyGroup}</span>
                          </div>
                        </div>
                        <div className="flex flex-col items-end">
                          <span className={`px-2 py-0.5 text-[10px] font-extrabold rounded border shadow-2xs ${speaker.style?.badgeClass || 'bg-slate-100 text-slate-600'}`}>
                            {speaker.style?.label || '標準'}
                          </span>
                        </div>
                      </div>

                      <div className="p-5 flex-grow flex flex-col items-center justify-center relative">
                        <div className="absolute top-3 left-4">
                          <div className="text-[9px] font-bold text-slate-400 uppercase">質疑スレッド</div>
                          <div className="text-lg font-black text-slate-700">
                            {speaker.count}<span className="text-[10px] font-medium text-slate-400 ml-0.5">件</span>
                          </div>
                        </div>
                        <div className="w-full h-36">
                          <ResponsiveContainer width="100%" height="100%">
                            <RadarChart cx="50%" cy="50%" outerRadius="70%" data={formatSummaryRadar(speaker)}>
                              <PolarGrid stroke="#e2e8f0" />
                              <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 9, fontWeight: 600 }} />
                              <PolarRadiusAxis domain={[0, 5]} tick={false} axisLine={false} />
                              <Radar dataKey="A" stroke="#6366f1" strokeWidth={2} fill="#818cf8" fillOpacity={0.4} />
                            </RadarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                      
                      <div className="p-3 bg-slate-50/50 border-t border-slate-100 flex items-center justify-between gap-2">
                        <button 
                          onClick={(e) => { e.stopPropagation(); onOpenCompare(speaker); }}
                          className="px-3 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-indigo-600 bg-white hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 transition-all flex items-center gap-1 cursor-pointer"
                        >
                          <GitCompare className="w-3.5 h-3.5 text-indigo-500" />
                          比較する
                        </button>
                        <span className="text-xs font-bold text-indigo-600 group-hover:translate-x-0.5 transition-transform">
                          詳細を見る →
                        </span>
                      </div>
                    </article>
                  ))
                ) : (
                  <div className="col-span-full text-center py-20 text-slate-500 bg-white rounded-2xl border border-slate-200">
                    このキーワードに言及している議員は見つかりませんでした。
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </main>
  );
}