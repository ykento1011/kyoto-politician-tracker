import React from 'react';
import { Award, ShieldCheck, Database, Calendar, HelpCircle, X, CheckCircle2 } from 'lucide-react';

export default function Methodology({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200 flex flex-col">
        {/* モーダルヘッダー */}
        <div className="sticky top-0 bg-white/95 backdrop-blur-sm border-b border-slate-200 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-slate-900">評価手法・分析方針について</h2>
              <p className="text-xs text-slate-500">透明性と客観性を担保するためのルーブリック評価基準</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 本文エリア */}
        <div className="p-6 space-y-6 text-slate-700 leading-relaxed text-sm">
          {/* 💡 データ対象期間と任期の明確化 */}
          <section className="bg-indigo-50/60 border border-indigo-100 rounded-2xl p-4.5 space-y-2.5">
            <h3 className="text-xs font-black text-indigo-900 uppercase tracking-wider flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-indigo-600" />
              分析対象期間と任期範囲
            </h3>
            <p className="text-xs text-indigo-950 font-bold leading-normal">
              対象任期：2023年（令和5年）5月 〜 直近公開会議録まで（現任期）
            </p>
            <p className="text-xs text-slate-600 leading-relaxed">
              期数の長いベテラン議員と新人議員が活動量や質で対等に比較されるよう、全議員共通のスタート地点である「2023年5月の改選以降の現任期」に統一しています。過去の任期データを含めないことで、直近の政策活動を公平に評価します。
            </p>
          </section>

          {/* 4つの評価指標 */}
          <section className="space-y-3">
            <h3 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              4つの客観ルーブリック指標（各1〜5点）
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              党派性や政治信条による有利・不利を排除し、議会での対話密度を以下の4つの軸で採点・集計しています。
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-xs font-extrabold text-slate-900 mb-1 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600" />
                  1. エビデンス・根拠性
                </div>
                <div className="text-[11px] text-slate-600 leading-relaxed">
                  統計データ、法令、他都市の先行事例、客観的な市民アンケートなどの事実に基づいた論理展開がなされているか。
                </div>
              </div>
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-xs font-extrabold text-slate-900 mb-1 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600" />
                  2. 解決策の提示力
                </div>
                <div className="text-[11px] text-slate-600 leading-relaxed">
                  単なる行政批判や現状追及に留まらず、予算配分や制度改善など具体的かつ実行可能な対案を提示できているか。
                </div>
              </div>
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-xs font-extrabold text-slate-900 mb-1 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600" />
                  3. 地域密着・現場視点
                </div>
                <div className="text-[11px] text-slate-600 leading-relaxed">
                  京都市各区・学区の地域課題、現場住民や中小企業・福祉施設などの生の声を反映した質疑であるか。
                </div>
              </div>
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-xs font-extrabold text-slate-900 mb-1 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600" />
                  4. 建設的対話・政策進展
                </div>
                <div className="text-[11px] text-slate-600 leading-relaxed">
                  市側（市長・局長等）から前向きな検討や具体的答弁を引き出し、政策議論を前進させる対話姿勢があるか。
                </div>
              </div>
            </div>
          </section>

          {/* データの収集範囲と中立性 */}
          <section className="space-y-3">
            <h3 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
              <Database className="w-4 h-4 text-indigo-600" />
              データの完全性と中立性の担保
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              京都市会が公式公開する「本会議（代表質問・一般質問）」「全常任委員会」「予算・決算特別委員会」の議事録を網羅しています。議長による進行や定型辞を除外し、議員の質問から市側の答弁、再質問までの一連のやり取りをスレッド単位で構造化しています。
            </p>
            <p className="text-xs text-slate-600 leading-relaxed">
              初期表示順序は、特定の議員に有利・不利が生じないよう、アクセス日ごとにランダムにシャッフルされるシード値方式を採用しています。
            </p>
          </section>
        </div>

        {/* モーダルフッター */}
        <div className="bg-slate-50 px-6 py-4 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 rounded-xl transition-colors shadow-sm"
          >
            閉じる
          </button>
        </div>
      </div>
    </div>
  );
}