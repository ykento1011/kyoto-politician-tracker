// 各都市の基本メタデータ、表示呼称、データファイルパス規定の一元管理 (SSoT)
export const CITIES = {
  kyoto: {
    code: 'kyoto',
    name: '京都',
    fullName: '京都市',
    councilName: '京都市会',
    mayorName: '松井市長',
    accentColor: '#4f46e5',
    active: true,
    hotTopics: ['オーバーツーリズム', '市バス', '中小企業支援', '空き家対策', '伝統産業', '子育て支援'],
    scopeText: '本会議・全常任委員会・特別委員会（12万件超の発言・全67議員・300件の議案賛否）',
    partyStripRegex: /京都市会議員団|市会議員団|議員団|市議団/g,
    title: '議会のミカタ 京都 ｜ AIは入口。判断するのは市民です。',
    description: '京都市会公式会議録12万発言と議決データを客観的に構造化。4軸による質疑分析、賛否が分かれた議案の記録。',
    canonicalUrl: 'https://gikai-mikata.jp/kyoto/',
    ogpImage: 'https://gikai-mikata.jp/ogp-kyoto.png',
  },
  osaka: {
    code: 'osaka',
    name: '大阪',
    fullName: '大阪市',
    councilName: '大阪市会',
    mayorName: '横山市長',
    accentColor: '#0284c7',
    active: true,
    hotTopics: ['万博・夢洲跡地', '副首都ビジョン', '特区民泊', '路上喫煙禁止', '学校 熱中症'],
    scopeText: '本会議および全委員会（現職81議員・1,260超の質疑スレッド・議案賛否）',
    partyStripRegex: /大阪市会議員団|市会議員団|議員団|市議団/g,
    title: '議会のミカタ 大阪 ｜ AIは入口。判断するのは市民です。',
    description: '大阪市会公式会議録と議決データを客観的に構造化。現職81議員の質疑スレッド分析、横山市長政策進捗トラッカー。',
    canonicalUrl: 'https://gikai-mikata.jp/osaka/',
    ogpImage: 'https://gikai-mikata.jp/ogp-osaka.png',
  },
  nagoya: {
    code: 'nagoya',
    name: '名古屋',
    fullName: '名古屋市',
    councilName: '名古屋市会',
    mayorName: '広沢市長',
    accentColor: '#d97706',
    active: true,
    hotTopics: ['名古屋城木造復元', '市民税減税', '敬老パス', '子ども応援委員会', 'アジア競技大会'],
    scopeText: '本会議および各委員会・電子採決ログ（現職68議員の議案賛否・首長トラッカー）',
    partyStripRegex: /名古屋市会議員団|市会議員団|議員団|市議団/g,
    title: '議会のミカタ 名古屋 ｜ AIは入口。判断するのは市民です。',
    description: '名古屋市会公式会議録と電子採決ログを客観的に構造化。広沢市長政策進捗トラッカーを一次情報で確認。',
    canonicalUrl: 'https://gikai-mikata.jp/nagoya/',
    ogpImage: 'https://gikai-mikata.jp/ogp-nagoya.png',
  },
  yokohama: {
    code: 'yokohama',
    name: '横浜',
    fullName: '横浜市',
    councilName: '横浜市会',
    mayorName: '原澤市長',
    accentColor: '#0ea5e9',
    active: true,
    hotTopics: ['中学校給食全員実施', '小児医療費無償化', '防災・激甚災害対策', '都心臨海部・港湾GX', '敬老パス・シニア支援'],
    scopeText: '原澤敦美市長重点12公約トラッカー・18区現職86議員（本会議・常任委員会論戦移行期）',
    partyStripRegex: /横浜市会議員団|市会議員団|議員団|市議団/g,
    title: '議会のミカタ 横浜 ｜ AIは入口。判断するのは市民です。',
    description: '横浜市会公式会議録と議決データを客観的に構造化。原澤敦美市長の看板公約トラッカーと市会論戦マップ。',
    canonicalUrl: 'https://gikai-mikata.jp/yokohama/',
    ogpImage: 'https://gikai-mikata.jp/ogp-yokohama.png',
  },
  kobe: {
    code: 'kobe',
    mayorName: '久元 喜造',
    mayorTitle: '神戸市長',
    term: '2021年11月就任（第3期）〜',
    party: '無所属（自民・立憲・公明・国民推薦）',
    bulletinPdf: 'https://hisamoto-kizo.com/cms/wp-content/uploads/seisaku.pdf',
    bulletinLabel: '市長公約原本（100の政策PDF）',
    strategyPdf: 'https://www.city.kobe.lg.jp/documents/35913/kobe_vision_ver4-2_1.pdf',
    strategyLabel: '神戸2025ビジョン',
    name: '神戸',
    fullName: '神戸市',
    councilName: '神戸市会',
    mayorName: '久元市長',
    accentColor: '#2563eb',
    active: true,
    hotTopics: ['三宮再開発・バスターミナル', 'タワーマンション規制・都心居住', '神戸空港国際化', '医療産業都市', '中学校給食・全員喫食'],
    scopeText: '久元喜造市長政策トラッカー・全常任委員会・本会議質疑スレッド・議案採決ログ',
    partyStripRegex: /神戸市会議員団|市会議員団|議員団|市議団/g,
    title: '議会のミカタ 神戸 ｜ AIは入口。判断するのは市民です。',
    description: '神戸市会公式会議録と議決データを客観的に構造化。久元喜造市長の政策トラッカーと市会論戦マップ。',
    canonicalUrl: 'https://gikai-mikata.jp/kobe/',
    ogpImage: 'https://gikai-mikata.jp/ogp-kobe.png',
  },
};

export const PORTAL_CONFIG = {
  title: '議会のミカタ ｜ AIは入口。判断するのは市民です。',
  description: '政令指定都市の市会・市議会公式会議録と議決データを客観的に構造化。一次資料原本で確認・判断できるオープンデータ基盤。',
  canonicalUrl: 'https://gikai-mikata.jp/',
  ogpImage: 'https://gikai-mikata.jp/ogp-portal.png',
};

const FILE_KEY_MAP = {
  votesSummary: 'votes_summary.json',
  billIssues: 'bill_issues.json',
  mayorTracker: 'mayor_tracker.json',
  pledgeTracker: 'pledge_tracker.json',
  topicSummaries: 'topic_summaries.json',
  councilors: 'councilors.json',
  statementsSummary: 'statements_summary.json',
};

export function getCityConfig(cityCode) {
  if (!cityCode) return null;
  return CITIES[cityCode] || null;
}

export function getCityDataUrl(cityCode, fileKey) {
  if (!cityCode) return null;
  const fileName = FILE_KEY_MAP[fileKey] || `${fileKey}.json`;
  return `/data/${cityCode}_${fileName}`;
}
