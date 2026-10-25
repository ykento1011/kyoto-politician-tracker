import React, { useState } from 'react';
import { X, Flag, AlertCircle, Send, CheckCircle2, Loader2 } from 'lucide-react';

export default function ReportIssueModal({ isOpen, onClose, reportContext }) {
  const [category, setCategory] = useState("link_broken");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("idle"); // idle, submitting, success, error

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus("submitting");

    try {
      const response = await fetch('/api/report-issue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, message, context: reportContext })
      });

      if (!response.ok) throw new Error("送信に失敗しました");
      
      setStatus("success");
      // 成功したら2秒後に自動で閉じる
      setTimeout(() => {
        onClose();
        setStatus("idle");
        setMessage("");
        setCategory("link_broken");
      }, 2000);
    } catch (error) {
      console.error(error);
      setStatus("error");
    }
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget && status !== "submitting") {
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 sm:p-6"
      onClick={handleOverlayClick}
      aria-modal="true"
      role="dialog"
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* ヘッダー */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-2 text-rose-600">
            <Flag className="w-4 h-4" />
            <h2 className="font-bold text-[15px]">一次資料の不備を報告</h2>
          </div>
          <button 
            onClick={onClose}
            disabled={status === "submitting"}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-full hover:bg-slate-200/50 transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* メインフォーム */}
        {status === "success" ? (
          <div className="p-8 text-center flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 mb-2">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-slate-800 text-lg">報告を送信しました</h3>
            <p className="text-sm text-slate-500">
              ご協力ありがとうございます。確認の上、データの修正に努めます。
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-5">
            
            {/* メタデータ確認 (読取専用) */}
            <div className="mb-5 bg-slate-50 border border-slate-200 rounded-lg p-3 text-[13px] text-slate-600 space-y-1.5">
              <div className="flex font-medium text-slate-700">
                <span className="w-16 shrink-0 text-slate-500 font-normal">対象資料:</span>
                <span className="truncate">{reportContext?.speaker || reportContext?.municipality || "不明"} / {reportContext?.meetingDate || "不明"}</span>
              </div>
              <div className="flex">
                <span className="w-16 shrink-0 text-slate-500">URL:</span>
                <a href={reportContext?.targetUrl} target="_blank" rel="noopener noreferrer" className="truncate text-indigo-600 hover:underline">
                  {reportContext?.targetUrl}
                </a>
              </div>
            </div>

            {/* 問題のカテゴリ */}
            <div className="mb-5">
              <label className="block text-[13px] font-bold text-slate-700 mb-2">
                どのような問題がありますか？ <span className="text-rose-500">*</span>
              </label>
              <div className="space-y-2">
                {[
                  { id: "link_broken", label: "リンク切れ（404・ページが開かない）" },
                  { id: "wrong_file", label: "リンク先の資料や発言内容が違う" },
                  { id: "broken_pdf", label: "PDFが壊れている・読めない" },
                  { id: "other", label: "その他・補足修正" }
                ].map(opt => (
                  <label key={opt.id} className="flex items-center gap-2.5 p-2.5 rounded-lg border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 cursor-pointer transition-colors has-[:checked]:border-indigo-500 has-[:checked]:bg-indigo-50 has-[:checked]:ring-1 has-[:checked]:ring-indigo-500">
                    <input 
                      type="radio" 
                      name="category" 
                      value={opt.id} 
                      checked={category === opt.id}
                      onChange={(e) => setCategory(e.target.value)}
                      className="w-4 h-4 text-indigo-600 focus:ring-indigo-500 border-slate-300" 
                    />
                    <span className="text-sm text-slate-700 font-medium">{opt.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* 補足メモ */}
            <div className="mb-5">
              <label htmlFor="report-message" className="block text-[13px] font-bold text-slate-700 mb-1.5">
                補足メモ（任意）
              </label>
              <textarea
                id="report-message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="正しいURLをご存知の場合や、詳細な状況があればご記入ください。"
                className="w-full text-sm p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white placeholder-slate-400 min-h-[80px] resize-y"
              />
            </div>

            {status === "error" && (
              <div className="mb-4 flex items-start gap-2 p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <p>送信エラーが発生しました。時間をおいて再度お試しください。</p>
              </div>
            )}

            {/* 送信ボタン */}
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={onClose}
                disabled={status === "submitting"}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-50"
              >
                キャンセル
              </button>
              <button
                type="submit"
                disabled={status === "submitting"}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 rounded-lg shadow-sm transition-all disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {status === "submitting" ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                <span>送信する</span>
              </button>
            </div>
            
          </form>
        )}
      </div>
    </div>
  );
}
