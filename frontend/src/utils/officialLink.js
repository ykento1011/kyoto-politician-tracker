/**
 * 京都市会 公式会議録システムへのリンク処理およびフォールバック
 */
export async function openOfficialMinute(stmt) {
  if (!stmt) return;

  // 1. 直リンクの URL が既にデータ内に存在する場合
  if (stmt.source_url && stmt.source_url.startsWith('http')) {
    window.open(stmt.source_url, '_blank', 'noopener,noreferrer');
    return;
  }

  // 2. council_id と schedule_id がある場合、MinuteView URL を動的生成
  if (stmt.council_id && stmt.schedule_id) {
    const directUrl = `https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=${stmt.council_id}&schedule_id=${stmt.schedule_id}`;
    window.open(directUrl, '_blank', 'noopener,noreferrer');
    return;
  }

  // 3. meeting_id が数値_数値形式の場合（例: "6253_5"）
  if (stmt.meeting_id && String(stmt.meeting_id).includes('_')) {
    const parts = String(stmt.meeting_id).split('_');
    if (parts.length >= 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
      const directUrl = `https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=${parts[0]}&schedule_id=${parts[1]}`;
      window.open(directUrl, '_blank', 'noopener,noreferrer');
      return;
    }
  }

  // 4. フォールバック: 公式検索トップへ遷移 ＋ 検索キーワードを自動コピー
  const searchBaseUrl = 'https://ssp.kaigiroku.net/tenant/kyoto/MinuteSearch.html';
  const meetingDate = stmt.meeting_date || '';
  const speaker = stmt.speaker || '';

  // 検索窓にそのまま貼り付けてヒットしやすいキーワード（日付 + 発言者名）
  const clipboardText = `${meetingDate} ${speaker}`.trim();

  if (clipboardText && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(clipboardText);
    } catch (err) {
      console.warn('クリップボードへのコピーに失敗しました:', err);
    }
  }

  window.open(searchBaseUrl, '_blank', 'noopener,noreferrer');
}

/**
 * ボタン表示用ツールチップ文言の生成
 */
export function getOfficialLinkTooltip(stmt) {
  if (stmt?.source_url || (stmt?.council_id && stmt?.schedule_id)) {
    return '京都市会 公式サーバー上の原本を別タブで開きます';
  }
  return '京都市会の公式検索システムを開きます（検索用キーワード「日付＋議員名」が自動コピーされます）';
}