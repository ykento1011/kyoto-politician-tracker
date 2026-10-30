// 全都市の正規論点マスター（各都市の topic_summaries.json と完全連動）

  // --- SSOT 動的バインド ---
  const activeCategoryTopicsMap = useMemo(() => {
    const map = {};
    if (Array.isArray(topicSummaries)) {
      topicSummaries.forEach(t => {
        if (!t.category || !t.id || !t.title) return;
        if (!map[t.category]) map[t.category] = [];
        map[t.category].push({ id: t.id, title: t.title });
      });
    }
    return map;
  }, [topicSummaries]);


  return (
    <section className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-extrabold text-slate-800 flex items-center">
            <PieChart className="w-4 h-4 mr-1.5 text-indigo-500" />
            市議会マクロ論戦マップ
          </h3>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
            全{totalThreadsCount.toLocaleString()}スレッドの質疑量と、8大分野の重要政策タイムライン
          </p>
        </div>
      </div>
      
      {/* 8大カテゴリーのグリッド */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
        {topicStats.map(topic => {
          const issueCount = getIssueCountForCategory ? getIssueCountForCategory(topic.name) : 0;
          const coreTopics = activeCategoryTopicsMap[topic.name] || [];

          return (
            <div 
              key={topic.name} 
              onClick={() => onOpenCategoryDetail && onOpenCategoryDetail(topic.name)}
              className="flex flex-col justify-between p-3.5 rounded-xl border bg-white border-slate-200 hover:border-indigo-400 hover:shadow-md transition-all cursor-pointer group"
            >
              {/* カード上部：カテゴリ名と激論議案バッジ */}
              <div>
                <div className="flex items-center justify-between w-full mb-1">
                  <span className="text-xs font-bold text-slate-800 group-hover:text-indigo-600 transition-colors truncate">
                    {topic.name}
                  </span>
                  {issueCount > 0 ? (
                    <span className="text-[9px] font-black px-1.5 py-0.5 rounded bg-rose-50 text-rose-600 border border-rose-200 shrink-0 flex items-center gap-0.5">
                      <Flame className="w-2.5 h-2.5 fill-rose-500 text-rose-500" />
                      激論議案 {issueCount}
                    </span>
                  ) : (
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-slate-50 text-slate-400 border border-slate-200 shrink-0">
                      合意
                    </span>
                  )}
                </div>
                
                <div className="flex items-end justify-between mt-1">
                  <span className="text-lg font-black text-slate-900 group-hover:text-indigo-600 transition-colors">
                    {topic.percentage}<span className="text-[10px] text-slate-400 font-medium ml-0.5">%</span>
                  </span>
                  <span className="text-[10px] text-slate-400 font-medium">{topic.count}質疑</span>
                </div>
                
                <div className="w-full bg-slate-100 h-1 mt-2 rounded-full overflow-hidden">
                  <div className="bg-indigo-500 h-full rounded-full transition-all duration-500" style={{ width: `${topic.percentage}%` }}></div>
                </div>
              </div>

              {/* カード下部：代表トピックのリンク */}
              <div className="mt-3 pt-2.5 border-t border-slate-100 space-y-1">
                {coreTopics.map((ct, idx) => (
                  <div
                    key={idx}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onOpenTopicDetail) onOpenTopicDetail(ct.id);
                    }}
                    className="text-[11px] text-slate-600 hover:text-indigo-600 flex items-center justify-between group/link py-0.5 transition-colors"
                  >
                    <span className="truncate pr-1">• {ct.title}</span>
                    <ArrowRight className="w-3 h-3 text-slate-300 group-hover/link:text-indigo-500 shrink-0 transition-transform group-hover/link:translate-x-0.5" />
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
