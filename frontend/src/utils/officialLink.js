/**
 * 京都市会 会議録システムへの遷移および検索支援
 * @param {Object} statement - 発言データオブジェクト
 */
export function openOfficialMinute(statement) {
  if (!statement) return;

  // 1. 直リンクURLを保持している場合はそのまま開く
  if (statement.official_url) {
    window.open(statement.official_url, '_blank', 'noopener,noreferrer');
    return;
  }

  // 2. 検索利便性のため、会議名と発言者名をクリップボードへ自動コピー
  const searchKeywords = [
    statement.meeting_date,
    statement.meeting_title,
    statement.speaker
  ].filter(Boolean).join(' ');

  if (navigator.clipboard && searchKeywords) {
    navigator.clipboard.writeText(searchKeywords).catch(() => {});
  }

  // 3. 京都市会 会議録検索システムのベースURLを開く
  const defaultUrl = 'https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html';
  window.open(defaultUrl, '_blank', 'noopener,noreferrer');
}

/**
 * リンクボタンのツールチップ表示テキスト生成
 * @param {Object} statement - 発言データオブジェクト
 * @returns {string} ツールチップ文字列
 */
export function getOfficialLinkTooltip(statement) {
  if (!statement) return '京都市会 公式会議録で原文を確認';
  const title = statement.meeting_title ? `（${statement.meeting_title}）` : '';
  return `京都市会 公式会議録で原本を確認 ${title}`;
}