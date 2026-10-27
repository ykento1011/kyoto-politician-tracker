// 各都市の基本メタデータ、表示呼称、データファイルパス規則の一元管理
export const CITIES = {
  kyoto: {
    code: 'kyoto',
    name: '京都',
    fullName: '京都市',
    councilName: '京都市会',
    councilType: 'council',
    mayorName: '松井市長',
    accentColor: '#4f46e5',
    active: true,
    // 既存のファイル命名規則を完全維持（京都は接頭辞なし、大阪は osaka_）
    dataPathPrefix: '',
    files: {
      votesSummary: '/data/votes_summary.json',
      billIssues: '/data/bill_issues.json',
      mayorTracker: '/data/mayor_tracker.json',
      pledgeTracker: '/data/pledge_tracker.json',
      topicSummaries: '/data/topic_summaries.json',
    },
    title: '議会のミカタ 京都 ｜ AIは入口。判断するのは市民です。',
    description: '京都市会公式会議録12万発言と議決データを客観的に構造化。4軸による質疑分析、賛否が分かれた議案の記録、看板公約の照合オープンデータ基盤。',
    ogpImage: 'https://gikai-mikata.jp/ogp-kyoto.png',
  },
  osaka: {
    code: 'osaka',
    name: '大阪',
    fullName: '大阪市',
    councilName: '大阪市会',
    councilType: 'council',
    mayorName: '横山市長',
    accentColor: '#0284c7',
    active: true,
    dataPathPrefix: 'osaka_',
    files: {
      votesSummary: '/data/osaka_votes_summary.json',
      billIssues: '/data/osaka_bill_issues.json',
      mayorTracker: '/data/osaka_mayor_tracker.json',
      pledgeTracker: '/data/pledge_tracker_osaka.json',
      topicSummaries: '/data/osaka_topic_summaries.json',
    },
    title: '議会のミカタ 大阪 ｜ AIは入口。判断するのは市民です。',
    description: '大阪市会公式会議録と議決データを客観的に構造化。現職81議員の質疑スレッド分析、賛否ログ、横山市長政策進捗トラッカーを一次情報で確認。',
    ogpImage: 'https://gikai-mikata.jp/ogp-osaka.png',
  },
  nagoya: {
    code: 'nagoya',
    name: '名古屋',
    fullName: '名古屋市',
    councilName: '名古屋市会',
    councilType: 'council',
    mayorName: '広沢市長',
    accentColor: '#d97706', // アンバー（名古屋城の金鯱イメージ）
    active: true,
    dataPathPrefix: 'nagoya_',
    files: {
      votesSummary: '/data/nagoya_votes_summary.json',
      billIssues: '/data/nagoya_bill_issues.json',
      mayorTracker: '/data/nagoya_mayor_tracker.json',
      pledgeTracker: '/data/pledge_tracker_nagoya.json',
      topicSummaries: '/data/nagoya_topic_summaries.json',
    },
    title: '議会のミカタ 名古屋 ｜ AIは入口。判断するのは市民です。',
    description: '名古屋市会公式会議録と電子採決ログを客観的に構造化。現職68議員の質疑スレッド分析、議案賛否ログ、広沢市長政策進捗トラッカーを一次情報で確認。',
    ogpImage: 'https://gikai-mikata.jp/ogp-nagoya.png',
  },
};

export const PORTAL_CONFIG = {
  title: '議会のミカタ ｜ AIは入口。判断するのは市民です。',
  description: '京都・大阪など政令指定都市の市会・市議会公式会議録と議決データを客観的に構造化。一次資料原本で確認・判断できるオープンデータ基盤。',
  canonicalUrl: 'https://gikai-mikata.jp/',
  ogpImage: 'https://gikai-mikata.jp/ogp-portal.png',
};

// ヘルパー: 指定された都市コードの設定を安全に取得
export function getCityConfig(cityCode) {
  if (!cityCode) return null;
  return CITIES[cityCode] || null;
}

// ヘルパー: 都市に応じたデータファイルのURLを取得
export function getCityDataUrl(cityCode, fileKey) {
  const city = getCityConfig(cityCode);
  if (!city) return null;
  return city.files[fileKey] || null;
}
