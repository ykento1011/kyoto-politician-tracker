{/* 💡 ③ 公約と議会活動の照合タブ */}
      {speakerDetailTab === 'pledges' && (
        <div className="space-y-6 animate-in fade-in">
          {/* 中立性・エビデンス宣言バナー */}
          <div className="bg-slate-100/90 rounded-2xl p-5 border border-slate-200 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs leading-relaxed">
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 font-black text-slate-800 text-xs">
                <ShieldCheck className="w-4 h-4 text-indigo-600 shrink-0" />
                <span>選挙公報原本に基づく看板政策のファクト対比</span>
              </div>
              <p className="text-slate-600 text-[11px]">
                選挙公報原本に掲載された本人の看板公約（原文引用）と、任期中の実際の議決（賛成/反対）および議場での関連質疑を客観的に並列提示しています。
              </p>
            </div>
            {currentSpeakerTracker?.bulletin_url && (
              <a
                href={currentSpeakerTracker.bulletin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-indigo-600 hover:text-indigo-800 font-bold text-xs shrink-0 transition-colors shadow-2xs cursor-pointer"
              >
                <Landmark className="w-3.5 h-3.5 text-indigo-500" />
                <span>選管公式公報PDF原本</span>
                <ExternalLink className="w-3 h-3 ml-0.5 opacity-60" />
              </a>
            )}
          </div>

          {/* 看板公約対比カード一覧 */}
          {currentSpeakerTracker && currentSpeakerTracker.tracked_items && currentSpeakerTracker.tracked_items.length > 0 ? (
            <div className="space-y-6">
              {currentSpeakerTracker.tracked_items.map((item, idx) => (
                <div key={idx} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden space-y-0">
                  {/* カードヘッダー */}
                  <div className="bg-slate-50/80 px-6 py-3.5 border-b border-slate-100 flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-black bg-indigo-50 text-indigo-700 border border-indigo-200">
                        {item.category || '市政政策'}
                      </span>
                      <h3 className="text-base font-black text-slate-900 leading-snug">
                        {item.headline}
                      </h3>
                    </div>
                    {item.stance && (
                      <span className="text-[11px] font-bold text-slate-500">
                        スタンス: <strong className="text-slate-800">{item.stance}</strong>
                      </span>
                    )}
                  </div>

                  {/* 2カラム対比グリッド */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">
                    {/* 左側：選挙公報での約束 */}
                    <div className="p-6 space-y-4 bg-indigo-50/15 flex flex-col justify-between">
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-black text-indigo-900 flex items-center gap-1.5 uppercase tracking-wider">
                            <BookmarkCheck className="w-4 h-4 text-indigo-600" />
                            2023年 選挙公報での訴え
                          </span>
                          <span className="text-[10px] font-bold text-slate-400">
                            公式選挙公報 原本
                          </span>
                        </div>

                        <div className="bg-white p-4 rounded-xl border border-indigo-100 shadow-2xs space-y-2">
                          <span className="text-[10px] font-black text-slate-400 block">公報紙面からの原文引用:</span>
                          <blockquote className="text-xs text-slate-800 font-bold leading-relaxed border-l-2 border-indigo-500 pl-3 italic">
                            “{item.election_promise?.quote || item.headline}”
                          </blockquote>
                        </div>
                      </div>

                      {item.election_promise?.bulletin_url && (
                        <div className="pt-2">
                          <a
                            href={item.election_promise.bulletin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[11px] font-bold text-indigo-600 hover:text-indigo-800 hover:underline"
                          >
                            <span>京都市選管 公式公報原本（PDF）で紙面を確認</span>
                            <ExternalLink className="w-3 h-3 opacity-60" />
                          </a>
                        </div>
                      )}
                    </div>

                    {/* 右側：市会での実際の行動（議決 & 質疑） */}
                    <div className="p-6 space-y-4 bg-white">
                      <span className="text-xs font-black text-slate-900 flex items-center gap-1.5 uppercase tracking-wider">
                        <Scale className="w-4 h-4 text-indigo-600" />
                        市会での実際の議決・発言ログ
                      </span>

                      {/* 議案への賛否 */}
                      {item.council_vote ? (
                        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-2.5">
                          <div className="flex items-center justify-between flex-wrap gap-1">
                            <span className="text-[10px] font-black text-slate-500 font-mono">
                              {item.council_vote.session_name} ({item.council_vote.bill_number})
                            </span>
                            <span className={`px-2 py-0.5 rounded text-[11px] font-black inline-flex items-center gap-1 ${
                              item.council_vote.my_vote === '賛成'
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : 'bg-rose-50 text-rose-700 border border-rose-200'
                            }`}>
                              {item.council_vote.my_vote === '賛成' ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                              投票態度: {item.council_vote.my_vote}
                            </span>
                          </div>

                          <h4 className="text-xs font-bold text-slate-800 leading-snug">
                            {item.council_vote.bill_title}
                          </h4>

                          {/* 💡 議案の背景・文脈解説 */}
                          {item.council_vote.context_note && (
                            <p className="text-[11px] text-slate-500 bg-white p-2 rounded border border-slate-100 leading-relaxed">
                              💡 <strong>背景:</strong> {item.council_vote.context_note}
                            </p>
                          )}

                          <div className="pt-1 flex items-center justify-between text-[10px] text-slate-500">
                            <span>議決結果: <strong className="text-slate-700">{item.council_vote.result}</strong></span>
                            {item.council_vote.source_url && (
                              <a
                                href={item.council_vote.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-indigo-600 hover:underline inline-flex items-center gap-0.5 font-bold"
                              >
                                公式議決記録 <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                              </a>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="bg-slate-50/70 p-3 rounded-xl border border-slate-100 text-[11px] text-slate-400 leading-relaxed">
                          ※単独の採決議案（条例案等）はありません（一般会計当初予算等に組み込まれて審議・執行される政策です）。
                        </div>
                      )}

                      {/* 💡 関連質疑発言（議場での生発言） */}
                      {item.council_statement ? (
                        <div className="p-4 rounded-xl bg-indigo-50/30 border border-indigo-100 space-y-2">
                          <div className="flex items-center justify-between text-[10px] font-bold text-slate-400">
                            <span className="font-mono text-slate-500">{item.council_statement.date} / {item.council_statement.committee}</span>
                            <span className="text-indigo-600 font-black px-1.5 py-0.2 bg-indigo-50 rounded border border-indigo-200">議場での発言・追及</span>
                          </div>
                          <p className="text-xs text-slate-800 leading-relaxed font-medium">
                            {item.council_statement.summary}
                          </p>
                          {item.council_statement.official_url && (
                            <div className="pt-1 text-right">
                              <a
                                href={item.council_statement.official_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[11px] font-bold text-indigo-600 hover:underline inline-flex items-center gap-0.5"
                              >
                                議事録原本で生ログを確認 <ExternalLink className="w-3 h-3 opacity-60" />
                              </a>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-[11px] text-slate-400 italic">
                          任期中に直接このテーマに言及した単独の質疑ログはありません。
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-slate-200 space-y-2">
              <AlertCircle className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-slate-600 font-bold text-sm">現在、この議員の選挙公報看板公約データを照合中です。</p>
            </div>
          )}
        </div>
      )}