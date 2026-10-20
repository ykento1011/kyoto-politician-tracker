/**
 * 京都市会 公式会議録システム原本への完全ダイレクト遷移処理
 */
export function openOfficialMinute(stmt) {
  if (!stmt) return;

  let targetUrl = stmt.source_url || '';

  // meeting_date から西暦年（view_years）を取得（例: 2026）
  const matchYear = (stmt.meeting_date || '').match(/^(\d{4})/);
  const viewYear = matchYear ? matchYear[1] : '';

  // 1. source_url が存在する場合（最優先・1クリック原本直行）
  if (targetUrl && targetUrl.startsWith('http')) {
    // 動作確認された安定パラメータ（is_search=false と view_years）を補完
    if (!targetUrl.includes('is_search=')) {
      targetUrl += (targetUrl.includes('?') ? '&' : '?') + 'is_search=false';
    }
    if (viewYear && !targetUrl.includes('view_years=')) {
      targetUrl += `&view_years=${viewYear}`;
    }
    window.open(targetUrl, '_blank', 'noopener,noreferrer');
    return;
  }

  // 2. council_id と schedule_id が個別にある場合
  if (stmt.council_id && stmt.schedule_id) {
    const directUrl = `https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=${stmt.council_id}&schedule_id=${stmt.schedule_id}&is_search=false${viewYear ? `&view_years=${viewYear}` : ''}`;
    window.open(directUrl, '_blank', 'noopener,noreferrer');
    return;
  }

  // 3. 完全なフォールバック（公式検索システムトップ）
  window.open('https://ssp.kaigiroku.net/tenant/kyoto/MinuteSearch.html', '_blank', 'noopener,noreferrer');
}

/**
 * ツールチップ文言
 */
export function getOfficialLinkTooltip(stmt) {
  if (stmt?.source_url) {
    return '京都市会公式サーバー上の会議録原本を直接開きます';
  }
  return '京都市会公式の会議録システムを開きます';
}