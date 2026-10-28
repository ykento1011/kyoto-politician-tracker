// officialLink.js - 公式議事録パーマリンク生成ユーティリティ

export function getOfficialMinuteUrl(stmt, cityCode = 'kyoto') {
  if (!stmt) return '';

  // 1. 各種プロパティから正規URLを取得（優先度: official_url -> source_url -> url -> doc_url）
  let targetUrl = stmt.official_url || stmt.source_url || stmt.url || stmt.doc_url || stmt.evidence_url || '';

  // meeting_date から西暦年（view_years）を取得（例: 2026）
  const matchYear = (stmt.meeting_date || '').match(/^(\d{4})/);
  const viewYear = matchYear ? matchYear[1] : '';

  // 2. targetUrl が既に存在する場合
  if (targetUrl && typeof targetUrl === 'string' && targetUrl.startsWith('http')) {
    // 検索トップ(MinuteSearch)のURLが渡された場合は MinuteView へ補正
    if (targetUrl.includes('MinuteSearch.html')) {
      targetUrl = targetUrl.replace('MinuteSearch.html', 'MinuteView.html');
    } else if (targetUrl.includes('SpMinuteSearch.html')) {
      targetUrl = targetUrl.replace('SpMinuteSearch.html', 'MinuteView.html');
    }

    // MinuteView のパラメータ補正
    if (targetUrl.includes('MinuteView.html')) {
      if (!targetUrl.includes('is_search=')) {
        targetUrl += (targetUrl.includes('?') ? '&' : '?') + 'is_search=false';
      }
      if (viewYear && !targetUrl.includes('view_years=')) {
        targetUrl += `&view_years=${viewYear}`;
      }
    }
    return targetUrl;
  }

  // 3. council_id と schedule_id がある場合
  // 💡 横浜市は独自ドメイン・HTTP運用（http://giji.city.yokohama.lg.jp/tenant/yokohama/）
  const isYokohama = cityCode === 'yokohama' || stmt.council_id?.toString().startsWith('yh_');
  const baseUrl = isYokohama
    ? 'http://giji.city.yokohama.lg.jp/tenant/yokohama/MinuteView.html'
    : `https://ssp.kaigiroku.net/tenant/${cityCode === 'nagoya' ? 'nagoya' : cityCode === 'osaka' ? 'cityosaka' : 'kyoto'}/MinuteView.html`;

  if (stmt.council_id && stmt.schedule_id) {
    return `${baseUrl}?council_id=${stmt.council_id}&schedule_id=${stmt.schedule_id}&is_search=false${viewYear ? `&view_years=${viewYear}` : ''}`;
  }

  // 4. フォールバック
  return baseUrl;
}

export function openOfficialMinute(stmt, cityCode = 'kyoto') {
  const url = getOfficialMinuteUrl(stmt, cityCode);
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer');
  }
}

export function getOfficialLinkTooltip(stmt, cityCode = 'kyoto') {
  const cityName = cityCode === 'yokohama' ? '横浜市会' : cityCode === 'nagoya' ? '名古屋市会' : cityCode === 'osaka' ? '大阪市会' : '京都市会';
  const url = stmt?.official_url || stmt?.source_url || stmt?.url;
  if (url && url.includes('MinuteView.html')) {
    return `${cityName}公式サーバー上の該当会議録原本を直接開きます`;
  }
  return `${cityName}公式の会議録システムを開きます`;
}
