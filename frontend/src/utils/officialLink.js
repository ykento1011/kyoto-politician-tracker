/**
 * 京都市会 公式会議録システムへの安全な遷移処理
 */
export async function openOfficialMinute(stmt, onCopiedCallback) {
  if (!stmt) return;

  const searchBaseUrl = 'https://ssp.kaigiroku.net/tenant/kyoto/MinuteSearch.html';

  // 最もヒットしやすい議員名（または日付）を抽出
  const speaker = (stmt.speaker || '').replace(/[（(].*?[)）]/g, '').trim();
  const date = stmt.meeting_date || '';
  const searchKeyword = speaker || date;

  // クリップボードへコピー
  if (searchKeyword && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(searchKeyword);
      if (onCopiedCallback) {
        onCopiedCallback(searchKeyword);
      }
    } catch (err) {
      console.warn('クリップボードのコピーに失敗しました:', err);
    }
  }

  // 念のためパラメータも付与して別タブで開く
  const targetUrl = searchKeyword 
    ? `${searchBaseUrl}?word=${encodeURIComponent(searchKeyword)}` 
    : searchBaseUrl;

  window.open(targetUrl, '_blank', 'noopener,noreferrer');
}

/**
 * ツールチップ文言
 */
export function getOfficialLinkTooltip(stmt) {
  const speaker = (stmt?.speaker || '').replace(/[（(].*?[)）]/g, '').trim();
  return `「${speaker}」をコピーして京都市会の公式検索画面を開きます。開いた画面で貼り付け（Ctrl+V / ペースト）してください。`;
}