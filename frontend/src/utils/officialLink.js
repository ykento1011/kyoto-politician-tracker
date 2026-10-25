/**
 * 自治体公式会議録システム原本へのURL生成・遷移処理
 */

export function getOfficialMinuteUrl(stmt, cityCode = 'kyoto') {
  if (!stmt) return '';

  let targetUrl = stmt.source_url || '';

  // meeting_date から西暦年（view_years）を取得（例: 2026）
  const matchYear = (stmt.meeting_date || '').match(/^(\d{4})/);
  const viewYear = matchYear ? matchYear[1] : '';

  // 1. source_url が存在する場合
  if (targetUrl && targetUrl.startsWith('http')) {
    if (!targetUrl.includes('is_search=')) {
      targetUrl += (targetUrl.includes('?') ? '&' : '?') + 'is_search=false';
    }
    if (viewYear && !targetUrl.includes('view_years=')) {
      targetUrl += `&view_years=${viewYear}`;
    }
    return targetUrl;
  }

  // 2. council_id と schedule_id が個別にある場合
  const isOsaka = cityCode === 'osaka' || 
                  (typeof stmt?.committee_name === 'string' && stmt.committee_name.includes('大阪市'));
  const tenant = isOsaka ? 'cityosaka' : 'kyoto';

  if (stmt.council_id && stmt.schedule_id) {
    return `https://ssp.kaigiroku.net/tenant/${tenant}/MinuteView.html?council_id=${stmt.council_id}&schedule_id=${stmt.schedule_id}&is_search=false${viewYear ? `&view_years=${viewYear}` : ''}`;
  }

  // 3. フォールバック（各都市の公式検索トップ）
  return `https://ssp.kaigiroku.net/tenant/${tenant}/MinuteSearch.html`;
}

export function openOfficialMinute(stmt, cityCode = 'kyoto') {
  const url = getOfficialMinuteUrl(stmt, cityCode);
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer');
  }
}

export function getOfficialLinkTooltip(stmt, cityCode = 'kyoto') {
  const isOsaka = cityCode === 'osaka' || 
                  (typeof stmt?.committee_name === 'string' && stmt.committee_name.includes('大阪市'));
  const cityName = isOsaka ? '大阪市会' : '京都市会';
  if (stmt?.source_url) {
    return `${cityName}公式サーバー上の会議録原本を直接開きます`;
  }
  return `${cityName}公式の会議録システムを開きます`;
}
