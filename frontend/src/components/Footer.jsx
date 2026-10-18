import React from 'react';

export default function Footer() {
  return (
    <footer className="mt-20 border-t border-slate-200 bg-white py-10 px-4 text-center text-slate-500">
      <div className="max-w-4xl mx-auto space-y-3">
        <div className="text-xs font-extrabold text-slate-800 tracking-tight">
          京都市会議員 ポリティシャントラッカー
        </div>

        <p className="text-[11px] text-slate-500 leading-relaxed">
          分析対象データ：京都市会 会議録検索システム（現任期：2023年5月〜直近公開分まで）<br className="hidden sm:inline" />
          本会議（代表質問・個人質疑）・常任委員会・決算及び予算特別委員会における全発言・対話スレッド
        </p>

        <p className="text-[10px] text-slate-400 leading-relaxed max-w-2xl mx-auto">
          ※本プラットフォームは、地方自治体が公開する公式会議録オープンデータを元に、AIによる客観ルーブリック評価で対話構造を可視化した中立な市民向けプロジェクトです。特定の政党・会派・信条を支持または排除するものではありません。
        </p>

        <div className="text-[10px] text-slate-400 pt-3 border-t border-slate-100">
          &copy; {new Date().getFullYear()} Kyoto Politician Tracker. All rights reserved.
        </div>
      </div>
    </footer>
  );
}