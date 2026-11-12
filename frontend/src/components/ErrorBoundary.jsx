import React from 'react';
import { AlertTriangle, Home, RotateCcw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      errorMessage: error?.message || '予期せぬ描画エラーが発生しました。',
    };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Caught rendering error:', error, errorInfo);
  }

  handleResetToTop = () => {
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.delete('speaker');
      url.searchParams.delete('compare');
      url.hash = '';
      window.history.pushState({}, '', url);
      window.location.reload();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="max-w-xl mx-auto my-12 p-6 bg-white rounded-2xl border border-rose-200 shadow-sm text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-black text-slate-900">
            ページの表示中にエラーが発生しました
          </h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            一部のデータ形式の読み込みに失敗した可能性があります。トップページへ戻るか、再読み込みをお試しください。
          </p>
          {this.state.errorMessage && (
            <pre className="text-[11px] text-left bg-slate-50 border border-slate-200 rounded-lg p-3 text-rose-700 overflow-x-auto">
              {this.state.errorMessage}
            </pre>
          )}
          <div className="flex items-center justify-center gap-3 pt-2">
            <button
              type="button"
              onClick={this.handleResetToTop}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-colors cursor-pointer"
            >
              <Home className="w-3.5 h-3.5" />
              トップページ（一覧）へ戻る
            </button>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              再読み込み
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
