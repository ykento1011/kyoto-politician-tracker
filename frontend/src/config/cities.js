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
    dataPathPrefix: '',
    files: {
      votesSummary: `/data/${cityCode}_votes_summary.json`,
      billIssues: `/data/${cityCode}_bill_issues.json`,
      mayorTracker: `/data/${cityCode}_mayor_tracker.json`,
      pledgeTracker: '/data/pledge_tracker.json',
      topicSummaries: `/data/${cityCode}_topic_summaries.json`,
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
    accentColor: '#d97706',
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
  yokohama: {
    code: 'yokohama',
    name: '横浜',
    fullName: '横浜市',
    councilName: '横浜市会',
    councilType: 'council',
    mayorName: '原澤市長',
    accentColor: '#0ea5e9',
    active: true,
    dataPathPrefix: 'yokohama_',
    files: {
      votesSummary: '/data/yokohama_votes_summary.json',
      billIssues: '/data/yokohama_bill_issues.json',
      mayorTracker: '/data/yokohama_mayor_tracker.json',
      pledgeTracker: '/data/pledge_tracker_yokohama.json',
      topicSummaries: '/data/yokohama_topic_summaries.json',
    },
    title: '議会のミカタ 横浜 ｜ AIは入口。判断するのは市民です。',
    description: '横浜市会公式会議録と議決データを客観的に構造化。2026年10月就任の原澤敦美市長の看板公約トラッカーと市会論戦マップ。一次原本（PDF・公式議事録）完全バインド。',
    canonicalUrl: 'https://gikai-mikata.jp/yokohama/',
    ogpImage: 'https://gikai-mikata.jp/ogp-yokohama.png',
  },
  kobe: {
    code: 'kobe',
    name: '神戸',
    fullName: '神戸市',
    councilName: '神戸市会',
    councilType: 'council',
    mayorName: '久元市長',
    accentColor: '#2563eb',
    active: true,
    dataPathPrefix: 'kobe_',
    files: {
      votesSummary: '/data/kobe_votes_summary.json',
      billIssues: '/data/kobe_bill_issues.json',
      mayorTracker: '/data/kobe_mayor_tracker.json',
      pledgeTracker: '/data/pledge_tracker_kobe.json',
      topicSummaries: '/data/kobe_topic_summaries.json',
    },
    title: '議会のミカタ 神戸 ｜ AIは入口。判断するのは市民です。',
    description: '神戸市会公式会議録と議決データを客観的に構造化。久元喜造市長の政策トラッカーと市会論戦マップ。一次原本完全バインド。',
    canonicalUrl: 'https://gikai-mikata.jp/kobe/',
    ogpImage: 'https://gikai-mikata.jp/ogp-kobe.png',
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
