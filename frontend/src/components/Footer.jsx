import React from 'react';
import { Scale, Mail, Calendar, ExternalLink } from 'lucide-react';
import GithubIcon from './GithubIcon';

export default function Footer({ onOpenMethodology , cityCode = 'kyoto'}) {
  return (
    <footer className="bg-slate-900 text-slate-400 py-12 px-6 mt-10">
      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-10">
        <div className="space-y-4">
          <h3 className="text-white font-extrabold text-sm flex items-center">
            <Scale className="w-4 h-4 mr-2" />運営ポリシーとプロセスの透明性
          </h3>
          <p className="text-xs leading-relaxed">
            本プラットフォームは特定の政党・政治団体を支持または批判するものではありません。先行研究を参照して設計した統一ルーブリックを用い、全議員に対して同一のプロンプトおよび生成パラメータ（temperature: 0.0）で機械的な処理を行っています。AIによる抽出や評価は一次資料へ効率的にアクセスするための補助ツールであり、最終的な判断は利用者に委ねられます。
          </p>

          <div className="text-[11px] text-slate-400 bg-slate-800/60 p-3 rounded-lg border border-slate-700/60 space-y-1">
            <div className="text-slate-300 font-bold flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-indigo-400" />
              分析対象データと期間
            </div>
            <p className="leading-relaxed">
              {cityCode === 'kobe' ? '神戸市会 公式' : cityCode === 'yokohama' ? '横浜市会 公式' : cityCode === 'nagoya' ? '名古屋市会 公式' : cityCode === 'osaka' ? '大阪市会 公式' : '京都市会 公式'}会議録（<strong>現任期：2023年5月〜最新公開分</strong>）<br />
              本会議（代表質問・個人質疑）・全常任委員会・特別委員会の全質疑スレッド
            </p>
          </div>

          <div className="pt-1">
            <button
              onClick={onOpenMethodology}
              className="text-xs font-bold text-indigo-400 hover:text-indigo-300 hover:underline inline-flex items-center cursor-pointer"
            >
              評価基準・技術仕様書（Methodology）を確認する →
            </button>
          </div>
        </div>

        <div className="space-y-4 md:text-right">
          <h3 className="text-white font-extrabold text-sm">開発・運営</h3>
          <div className="text-xs space-y-1.5">
            <a
              href="https://kanko-innovation.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 font-bold text-slate-200 hover:text-indigo-400 transition-colors"
            >
              <span>株式会社KICKs 公式サイト</span>
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </a>
            <p className="text-slate-400">代表 山本健人</p>
          </div>

          <div className="pt-2 flex flex-col items-start md:items-end space-y-2.5">
            <a
              href="https://github.com/ykento1011/kyoto-politician-tracker"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
            >
              <GithubIcon className="w-3.5 h-3.5" />
              <span>GitHub Repository</span>
            </a>

            <a
              href="https://forms.gle/vUaP885dxHEopaRX7"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-400 hover:text-indigo-400 transition-colors"
            >
              <Mail className="w-3.5 h-3.5" />
              <span>お問い合わせ（取材・改善要望・データ修正等）</span>
            </a>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto mt-8 pt-6 border-t border-slate-800 text-center md:text-left text-[11px] text-slate-400 flex flex-col md:flex-row justify-between items-center gap-2">
        <span>&copy; {new Date().getFullYear()} 株式会社KICKs All rights reserved.</span>
                  <span>
            {cityCode === 'kobe'
              ? '神戸市会議員・政策トラッカー「議会のミカタ 神戸」'
              : cityCode === 'yokohama'
              ? '横浜市会議員・政策トラッカー「議会のミカタ 横浜」'
              : cityCode === 'nagoya'
              ? '名古屋市会議員トラッカー「議会のミカタ 名古屋」'
              : cityCode === 'osaka'
              ? '大阪市会議員トラッカー「議会のミカタ 大阪」'
              : '京都市議会議員トラッカー「議会のミカタ 京都」'}
          </span>
      </div>
    </footer>
  );
}