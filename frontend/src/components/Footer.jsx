import React from 'react';
import { Scale, Mail } from 'lucide-react';
import GithubIcon from './GithubIcon';

export default function Footer({ onOpenMethodology }) {
  return (
    <footer className="bg-slate-900 text-slate-400 py-12 px-6 mt-10">
      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-10">
        <div className="space-y-4">
          <h3 className="text-white font-extrabold text-sm flex items-center">
            <Scale className="w-4 h-4 mr-2" />運営ポリシー・中立性の宣誓
          </h3>
          <p className="text-xs leading-relaxed">
            本プラットフォームは特定の政党・政治団体を支持または批判するものではありません。AI（Gemini）による客観的ルーブリック評価は、全議員に対して完全に同一のプロンプトと基準で機械的に適用されています。
          </p>
          <div className="pt-1">
            <button
              onClick={onOpenMethodology}
              className="text-xs font-bold text-indigo-400 hover:text-indigo-300 hover:underline inline-flex items-center cursor-pointer"
            >
              評価基準・AIプロンプト仕様書（Methodology）を詳しく確認する →
            </button>
          </div>
        </div>

        <div className="space-y-4 md:text-right">
          <h3 className="text-white font-extrabold text-sm">開発・運営</h3>
          <div className="text-xs space-y-1">
            <p>株式会社KICKs</p>
            <p>代表 山本健人</p>
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
              href="https://forms.gle/36F9b6xeC8NqzNsU9"
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
    </footer>
  );
}