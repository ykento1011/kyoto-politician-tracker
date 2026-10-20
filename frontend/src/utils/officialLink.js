/**
 * クリップボード通知用トーストの表示
 */
function showCopyToast(copiedText) {
  const existing = document.getElementById('official-link-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.id = 'official-link-toast';
  toast.innerHTML = `
    <div style="display: flex; align-items: center; gap: 8px;">
      <span style="font-size: 16px;">📋</span>
      <div>
        <div style="font-size: 11px; opacity: 0.8;">検索ワードをコピーしました（Ctrl + V）</div>
        <div style="font-size: 13px; font-weight: 800; color: #a5b4fc;">「${copiedText}」</div>
      </div>
    </div>
  `;
  toast.style.cssText = `
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #0f172a;
    color: #ffffff;
    padding: 12px 18px;
    border-radius: 12px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1);
    z-index: 99999;
    opacity: 0;
    transform: translateY(10px);
    transition: all 0.25s ease-out;
    pointer-events: none;
    font-family: sans-serif;
  `;
  document.body.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  });

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

/**
 * 京都市会 公式会議録システムへの安全な遷移処理
 */
export async function openOfficialMinute(stmt) {
  if (!stmt) return;

  // 確実に 200 OK で開く公式検索システムのトップ
  const searchBaseUrl = 'https://ssp.kaigiroku.net/tenant/kyoto/MinuteSearch.html';

  // 検索窓で最もヒットしやすいキーワード（議員名）
  const speaker = (stmt.speaker || '').replace(/[（(].*?[)）]/g, '').trim();
  const date = stmt.meeting_date || '';
  const searchKeyword = speaker || date;

  // クリップボードへコピー
  if (searchKeyword && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(searchKeyword);
      showCopyToast(searchKeyword);
    } catch (err) {
      console.warn('クリップボードのコピーに失敗しました:', err);
    }
  }

  // 公式検索システムを別タブで開く
  window.open(searchBaseUrl, '_blank', 'noopener,noreferrer');
}

/**
 * ツールチップ文言
 */
export function getOfficialLinkTooltip(stmt) {
  const speaker = (stmt?.speaker || '').replace(/[（(].*?[)）]/g, '').trim();
  return `京都市会の公式検索システムを開きます（「${speaker}」が自動コピーされます）`;
}