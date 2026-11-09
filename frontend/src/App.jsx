import { getCityConfig, getCityDataUrl, PORTAL_CONFIG } from './config/cities';
const safeFetchJson = async (url) => {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const text = await res.text();
    if (text.trim().startsWith('<')) return null; // HTMLフォールバック防止
    return JSON.parse(text);
  } catch (e) {
    return null;
  }
};
import React, { useState, useEffect, useMemo, useCallback, lazy, Suspense } from 'react';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import HeroSection from './components/HeroSection';
import PortalTopView from './components/PortalTopView';
import MainTabView from './components/MainTabView';
import SpeakerDetailView from './components/SpeakerDetailView';
const SearchResultsView = lazy(() => import('./components/SearchResultsView'));
const CompareDashboard = lazy(() => import('./components/CompareDashboard'));
import HighlightedThreads from './components/HighlightedThreads';
import MacroTopicMap from './components/MacroTopicMap';
const ContestedBillsView = lazy(() => import('./components/ContestedBillsView'));
const TopicDetailPage = lazy(() => import('./components/TopicDetailPage'));
const CategoryDetailPage = lazy(() => import('./components/CategoryDetailPage'));
const MayorTrackerView = lazy(() => import('./components/MayorTrackerView'));
const TimelineModal = lazy(() => import('./components/TimelineModal'));
const BillDetailModal = lazy(() => import('./components/BillDetailModal'));
const AboutPage = lazy(() => import('./components/AboutPage'));
const Methodology = lazy(() => import('./components/Methodology'));
const GuidePage = lazy(() => import('./components/GuidePage'));
import { useStatements } from './hooks/useStatements';
import FeedbackButton from './components/FeedbackButton';

function getCategoryForBill(b) {
  const text = `${b.title || ''} ${b.key_conflict || ''} ${b.background || ''}`;
  if (text.includes('都市計画') || text.includes('建築') || text.includes('開発') || text.includes('住宅') || text.includes('新幹線')) return '都市再生・交通インフラ';
  if (text.includes('観光') || text.includes('宿泊税') || text.includes('産業') || text.includes('万博') || text.includes('芸術大学') || text.includes('市場')) return '産業・観光・地域経済';
  if (text.includes('医療') || text.includes('健康保険') || text.includes('国保') || text.includes('介護') || text.includes('保護') || text.includes('衛生')) return '福祉・医療・健康';
  if (text.includes('子ども') || text.includes('給食') || text.includes('学校') || text.includes('保育') || text.includes('児童')) return '子育て・教育';
  if (text.includes('予算') || text.includes('決算') || text.includes('報酬') || text.includes('給与') || text.includes('定数') || text.includes('手続')) return '財政・行革';
  if (text.includes('原発') || text.includes('温暖化') || text.includes('環境') || text.includes('下水') || text.includes('水道')) return 'くらし・環境・エネルギー';
  if (text.includes('防災') || text.includes('消防') || text.includes('災害') || text.includes('耐震')) return '防災・減災・治安';
  if (text.includes('文化') || text.includes('景観') || text.includes('世界遺産') || text.includes('歴史')) return '文化・景観・歴史';
  return '市政全般';
}


const CITY_COUNCIL_CONFIG = {
  kyoto: { councilName: '京都市会', officialUrl: 'https://www.city.kyoto.lg.jp/shikai/', election: '京都市選挙管理委員会', ogp: 'https://gikai-mikata.jp/ogp-kyoto.png' },
  osaka: { councilName: '大阪市会', officialUrl: 'https://www.city.osaka.lg.jp/shikai/', election: '大阪市選挙管理委員会', ogp: 'https://gikai-mikata.jp/ogp-osaka.png' },
  nagoya: { councilName: '名古屋市会', officialUrl: 'https://www.city.nagoya.jp/shikai/', election: '名古屋市選挙管理委員会', ogp: 'https://gikai-mikata.jp/ogp-nagoya.png' },
  yokohama: { councilName: '横浜市会', officialUrl: 'https://www.city.yokohama.lg.jp/shikai/', election: '横浜市選挙管理委員会', ogp: 'https://gikai-mikata.jp/ogp-yokohama.png' },
  kobe: { councilName: '神戸市会', officialUrl: 'https://www.city.kobe.lg.jp/shikai/', election: '神戸市選挙管理委員会', ogp: 'https://gikai-mikata.jp/ogp-kobe.png' }
};

function parseCurrentRoute() {
  const params = new URLSearchParams(window.location.search);
  const hash = window.location.hash || '';
  const pathname = window.location.pathname;

  if (hash.startsWith('#topic=')) {
    return { type: 'topic', topicId: hash.replace('#topic=', '') };
  }
  if (hash.startsWith('#category=')) {
    return { type: 'category', categoryName: decodeURIComponent(hash.replace('#category=', '')) };
  }

  const view = params.get('view');
  if (view === 'mayor' || pathname === '/mayor') return { type: 'mayor' };
  if (view === 'guide' || pathname === '/guide') return { type: 'guide' };
  if (view === 'about' || pathname === '/about') return { type: 'about' };
  if (view === 'methodology' || pathname === '/methodology') return { type: 'methodology' };
  if (view === 'contested' || pathname === '/contested') return { type: 'contested', category: params.get('cat') || '' };

  const compareParam = params.get('compare');
  if (compareParam !== null) {
    const names = compareParam === 'open' ? [] : compareParam.split(',').map(s => decodeURIComponent(s.trim())).filter(Boolean);
    return { type: 'compare', names };
  }

  // 💡 パーマリンク (?p= または ?speaker= または /politicians/:id) の解釈
  const pParam = params.get('p') || params.get('speaker');
  if (pParam) {
    return { type: 'speaker', speakerName: decodeURIComponent(pParam.trim()) };
  }
  const polMatch = pathname.match(/\/politicians\/([^\/]+)/);
  if (polMatch) {
    return { type: 'speaker', speakerName: decodeURIComponent(polMatch[1].trim()) };
  }

  const qParam = params.get('q');
  if (qParam) {
    return { type: 'search', query: decodeURIComponent(qParam.trim()) };
  }

  return { type: 'portal' };
}

export default function App() {
  // 💡 URLのパスから都市を判定（/ はポータル、/kyoto は京都、/osaka は大阪、/nagoya は名古屋）
  const [cityCode, setCityCode] = useState(() => {
    if (typeof window !== 'undefined') {
      const path = window.location.pathname;
      const params = new URLSearchParams(window.location.search);
      const hash = window.location.hash || '';

      if (path.startsWith('/kobe') || params.get('city') === 'kobe') {
        return 'kobe';
      } else if (path.startsWith('/yokohama') || params.get('city') === 'yokohama') {
        return 'yokohama';
      } else if (path.startsWith('/nagoya') || params.get('city') === 'nagoya') {
        return 'nagoya';
      }
      if (path.startsWith('/osaka') || params.get('city') === 'osaka') {
        return 'osaka';
      }
      if (path.startsWith('/kyoto') || params.get('city') === 'kyoto') {
        return 'kyoto';
      }

      // 💡 後方互換性保護：ルート(/)なのに古いクエリがある場合は /kyoto/ へ自動リダイレクト
      const hasOldKyotoQuery = Boolean(
        params.get('p') || params.get('speaker') || params.get('view') || params.get('compare') || 
        params.get('q') || params.get('cat') || hash.startsWith('#topic=') || hash.startsWith('#category=')
      );
      if (hasOldKyotoQuery) {
        const target = '/kyoto/' + window.location.search + window.location.hash;
        window.history.replaceState({}, '', target);
        return 'kyoto';
      }

      // クエリのない純粋な / は総合ポータル
      return null;
    }
    return null;
  });

  const {
    statements,
    isLoading,
    searchQuery,
    setSearchQuery,
    submittedQuery,
    setSubmittedQuery,
    selectedCategory,
    setSelectedCategory,
    selectedDistrict,
    setSelectedDistrict,
    sortPerspective,
    setSortPerspective,
    viewMode,
    setViewMode,
    speakerCategory,
    setSpeakerCategory,
    speakerSort,
    setSpeakerSort,
    compareList,
    handleViewContext,
    selectedContext,
    isPanelOpen,
    setIsPanelOpen,
    isLoadingContext,
    topicStats,
    speakerStats,
    filteredSpeakers,
    filteredThreads
  } = useStatements(cityCode);

  const [votesData, setVotesData] = useState([]);
  const [billIssuesList, setBillIssuesList] = useState([]);
  const [issuesMap, setIssuesMap] = useState({});
  const [mayorTrackerData, setMayorTrackerData] = useState(null);
  const [selectedBillForModal, setSelectedBillForModal] = useState(null);
  const [onlyContestedBills, setOnlyContestedBills] = useState(true);

  const [selectedSession, setSelectedSession] = useState('');
  const [selectedResult, setSelectedResult] = useState('');

  const [currentRoute, setCurrentRoute] = useState(() => parseCurrentRoute());

  useEffect(() => {
    if (!cityCode) {
      setVotesData([]);
      setBillIssuesList([]);
      setIssuesMap({});
      setMayorTrackerData(null);
      return;
    }
    const prefix = cityCode === 'kyoto' ? '' : `${cityCode}_`;

    // 💡 safeFetchJsonを使うことでHTMLフォールバックによるJSONパースエラーを防止
    safeFetchJson(getCityDataUrl(cityCode, 'votesSummary') || `/data/${prefix}votes_summary.json`)
      .then(data => setVotesData(data || []))
      .catch(err => console.error('Failed to load votes:', err));

    safeFetchJson(getCityDataUrl(cityCode, 'billIssues') || `/data/${prefix}bill_issues.json`)
      .then(data => {
        const list = data || [];
        setBillIssuesList(list);
        const map = {};
        list.forEach(item => {
          map[`${item.session_name}_${item.bill_number}`] = item;
        });
        setIssuesMap(map);
      })
      .catch(err => console.error('Failed to load bill issues:', err));

    safeFetchJson(getCityDataUrl(cityCode, 'mayorTracker') || `/data/${prefix}mayor_tracker.json`)
      .then(data => setMayorTrackerData(data || null))
      .catch(err => console.error('Failed to load mayor tracker:', err));
  }, [cityCode]);

  useEffect(() => {
    const onLocationChange = () => {
      // 💡 ブラウザの戻る・進む時に URL パスから cityCode を再同期
      const currentPath = window.location.pathname;
      const currentParams = new URLSearchParams(window.location.search);
      let detectedCity = null;
      
      if (currentPath.startsWith('/kobe') || currentParams.get('city') === 'kobe') {
        detectedCity = 'kobe';
      } else if (currentPath.startsWith('/yokohama') || currentParams.get('city') === 'yokohama') {
        detectedCity = 'yokohama';
      } else if (currentPath.startsWith('/nagoya') || currentParams.get('city') === 'nagoya') {
        detectedCity = 'nagoya';
      } else if (currentPath.startsWith('/osaka') || currentParams.get('city') === 'osaka') {
        detectedCity = 'osaka';
      } else if (currentPath.startsWith('/kyoto') || currentParams.get('city') === 'kyoto') {
        detectedCity = 'kyoto';
      }
      
      setCityCode(detectedCity);

      const nextRoute = parseCurrentRoute();
      setCurrentRoute(nextRoute);

      if (nextRoute.type === 'search') {
        setSearchQuery(nextRoute.query);
        setSubmittedQuery(nextRoute.query);
      } else {
        setSubmittedQuery('');
      }
    };

    // 初回マウント時にも実行して URL クエリと cityCode を同期
    onLocationChange();

    window.addEventListener('popstate', onLocationChange);
    window.addEventListener('hashchange', onLocationChange);
    window.addEventListener('app-navigate', onLocationChange);
    return () => {
      window.removeEventListener('popstate', onLocationChange);
      window.removeEventListener('hashchange', onLocationChange);
      window.removeEventListener('app-navigate', onLocationChange);
    };
  }, [setSearchQuery, setSubmittedQuery]);

  // 💡 都市および議員パーマリンクに応じたSEOメタタグ & JSON-LDの動的同期
  useEffect(() => {
    // ① 議員個別ビュー時の動的 SEO / Schema.org JSON-LD 更新
    if (currentRoute.type === 'speaker' && activeSpeaker && cityCode) {
      const cfg = CITY_COUNCIL_CONFIG[cityCode] || { councilName: '市会', officialUrl: 'https://gikai-mikata.jp/', election: '選挙管理委員会', ogp: 'https://gikai-mikata.jp/ogp-portal.png' };
      const speakerClean = (activeSpeaker.speaker || '').replace(/\s+/g, '');
      const districtStr = activeSpeaker.district ? `・${activeSpeaker.district}` : '';
      const partyStr = activeSpeaker.party ? `・${activeSpeaker.party}` : '';
      const title = `${activeSpeaker.speaker}（${cfg.councilName}${districtStr}）の政策・公約・採決態度 ｜ 議会のミカタ`;
      const description = `${cfg.councilName}（${activeSpeaker.district || ''}${partyStr}）${activeSpeaker.speaker}議員。重点公約、議案採決態度、および質疑実績ログの可視化データ。`;
      const canonicalUrl = `https://gikai-mikata.jp/${cityCode}/?speaker=${encodeURIComponent(activeSpeaker.speaker)}`;
      const ogpImage = activeSpeaker.image_url || cfg.ogp;

      document.title = title;
      const setMeta = (selector, attr, val) => {
        let el = document.querySelector(selector);
        if (!el) {
          el = document.createElement(selector.startsWith('link') ? 'link' : 'meta');
          if (selector.includes('name=')) el.setAttribute('name', selector.match(/name="(.*?)"/)[1]);
          if (selector.includes('property=')) el.setAttribute('property', selector.match(/property="(.*?)"/)[1]);
          if (selector.includes('rel=')) el.setAttribute('rel', selector.match(/rel="(.*?)"/)[1]);
          document.head.appendChild(el);
        }
        el.setAttribute(attr, val);
      };

      setMeta('meta[name="description"]', 'content', description);
      setMeta('link[rel="canonical"]', 'href', canonicalUrl);
      setMeta('meta[property="og:title"]', 'content', title);
      setMeta('meta[property="og:description"]', 'content', description);
      setMeta('meta[property="og:url"]', 'content', canonicalUrl);
      setMeta('meta[property="og:image"]', 'content', ogpImage);
      setMeta('meta[name="twitter:title"]', 'content', title);
      setMeta('meta[name="twitter:description"]', 'content', description);
      setMeta('meta[name="twitter:image"]', 'content', ogpImage);

      // JSON-LD (Schema.org/Person) の動的注入
      // 💡 instant スクリプトが存在すれば統合・詳細上書き
      let scriptTag = document.getElementById('speaker-jsonld-instant') || document.getElementById('speaker-jsonld');
      if (!scriptTag) {
        scriptTag = document.createElement('script');
        scriptTag.id = 'speaker-jsonld';
        scriptTag.type = 'application/ld+json';
        document.head.appendChild(scriptTag);
      } else {
        scriptTag.id = 'speaker-jsonld';
      }
      const jsonLdData = {
        "@context": "https://schema.org",
        "@type": "ProfilePage",
        "mainEntity": {
          "@type": "Person",
          "@id": `${canonicalUrl}#person`,
          "name": activeSpeaker.speaker,
          "jobTitle": `${cfg.councilName}議員`,
          "worksFor": { "@type": "GovernmentOrganization", "name": cfg.councilName, "url": cfg.officialUrl },
          "memberOf": { "@type": "Organization", "name": activeSpeaker.party || '無所属' },
          "description": description,
          "image": ogpImage,
          "url": canonicalUrl,
          "hasCredential": {
            "@type": "EducationalOccupationalCredential",
            "credentialCategory": "ElectedOfficial",
            "recognizedBy": { "@type": "GovernmentOrganization", "name": cfg.election }
          }
        }
      };
      scriptTag.textContent = JSON.stringify(jsonLdData);

      return () => {
        const existing = document.getElementById('speaker-jsonld');
        if (existing) existing.remove();
      };
    }
    let title = "議会のミカタ ｜ AIは入口。判断するのは市民です。";
    let description = "京都・大阪の市会公式会議録と議決データを客観的に構造化。4軸による議員質疑分析、賛否が分かれた議案ログ、市長公約の予算措置・条例可決・執行進捗を一次情報で確認・判断できるオープンデータ・プラットフォーム。";
    let canonicalUrl = "https://gikai-mikata.jp/";
    let ogpImage = "https://gikai-mikata.jp/ogp-portal.png";

    if (cityCode === 'kobe') {
      title = '議会のミカタ 神戸 ｜ AIは入口。判断するのは市民です。';
      description = '神戸市会公式会議録と議決データを客観的に構造化。久元市長政策進捗トラッカーを一次情報で確認。';
      canonicalUrl = 'https://gikai-mikata.jp/kobe/';
      ogpImage = 'https://gikai-mikata.jp/ogp-kobe.png';
    } else if (cityCode === 'yokohama') {
      title = '議会のミカタ 横浜 ｜ AIは入口。判断するのは市民です。';
      canonicalUrl = 'https://gikai-mikata.jp/yokohama/';
      ogpImage = 'https://gikai-mikata.jp/ogp-yokohama.png';
    } else if (cityCode === 'osaka') {
      title = "議会のミカタ 大阪 ｜ AIは入口。判断するのは市民です。";
      description = "大阪市会公式会議録と議決データを客観的に構造化。現職81議員・1,260超の質疑スレッド分析、賛否が分かれた議案の記録、横山市長政策進捗トラッカー（一次資料・予算照合）により、市民が自ら確認・判断できるオープンデータ基盤。";
      canonicalUrl = "https://gikai-mikata.jp/osaka/";
      ogpImage = "https://gikai-mikata.jp/ogp-osaka.png";
    } else if (cityCode === 'nagoya') {
      title = '議会のミカタ 名古屋 ｜ AIは入口。判断するのは市民です。';
      description = '名古屋市会公式会議録と電子採決ログを客観的に構造化。広沢市長政策進捗トラッカーを一次情報で確認。';
      canonicalUrl = 'https://gikai-mikata.jp/nagoya/';
      ogpImage = 'https://gikai-mikata.jp/ogp-nagoya.png';
    } else if (cityCode === 'kyoto') {
      title = "議会のミカタ 京都 ｜ AIは入口。判断するのは市民です。";
      description = "京都市会公式会議録12万発言と議決データを客観的に構造化。4軸による質疑分析、賛否が分かれた議案の記録、選挙公報原本に基づく看板公約の照合により、市民が自ら一次情報で確認・判断できるオープンデータ・プラットフォーム。";
      canonicalUrl = "https://gikai-mikata.jp/kyoto/";
      ogpImage = "https://gikai-mikata.jp/ogp-kyoto.png";
    }

    // document.title
    document.title = title;

    // メタタグ更新ヘルパー
    const setMeta = (selector, attr, value) => {
      let el = document.querySelector(selector);
      if (!el) {
        el = document.createElement('meta');
        const [attrName, attrVal] = selector.replace(/[\[\]'"]/g, '').split('=');
        el.setAttribute(attrName, attrVal);
        document.head.appendChild(el);
      }
      el.setAttribute(attr, value);
    };

    setMeta("meta[name='description']", "content", description);
    setMeta("meta[property='og:title']", "content", title);
    setMeta("meta[property='og:description']", "content", description);
    setMeta("meta[property='og:url']", "content", canonicalUrl);
    setMeta("meta[property='og:image']", "content", ogpImage);
    setMeta("meta[name='twitter:title']", "content", title);
    setMeta("meta[name='twitter:description']", "content", description);

    // Canonical
    let linkCanonical = document.querySelector("link[rel='canonical']");
    if (linkCanonical) {
      linkCanonical.setAttribute("href", canonicalUrl);
    }
  }, [cityCode]);

  const navigate = useCallback((url, replace = false) => {
    let finalUrl = url;
    if (cityCode) {
      const basePath = `/${cityCode}`;
      if (url.startsWith('/kyoto') || url.startsWith('/osaka') || url.startsWith('/nagoya') || url.startsWith('/yokohama') || url.startsWith('/kobe')) {
        finalUrl = url;
      } else if (url === '/') {
        finalUrl = `${basePath}/`;
      } else if (url.startsWith('/?')) {
        finalUrl = `${basePath}/${url.slice(1)}`;
      } else {
        finalUrl = url.startsWith('/') ? `${basePath}${url}` : `${basePath}/${url}`;
      }
    }

    if (replace) {
      window.history.replaceState({}, '', finalUrl);
    } else {
      window.history.pushState({}, '', finalUrl);
    }
    window.dispatchEvent(new Event('app-navigate'));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [cityCode]);

  const resolveSpeaker = useCallback((spk) => {
    if (!spk) return null;
    const name = typeof spk === 'string' ? spk.replace(/\s+/g, '') : spk.speaker?.replace(/\s+/g, '');
    return (speakerStats || []).find(s => s.speaker.replace(/\s+/g, '') === name) || null;
  }, [speakerStats]);

  const handleGoHome = useCallback(() => {
    setSearchQuery('');
    setSubmittedQuery('');
    navigate('/');
  }, [navigate, setSearchQuery, setSubmittedQuery]);

  const handleGoPortal = useCallback(() => {
    setCityCode(null);
    window.history.pushState({}, '', '/');
    window.dispatchEvent(new Event('app-navigate'));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleSpeakerClick = useCallback((speakerInput) => {
    const speakerName = typeof speakerInput === 'string' ? speakerInput : speakerInput?.speaker;
    if (!speakerName) return;
    navigate(`/?speaker=${encodeURIComponent(speakerName)}`);
  }, [navigate]);

  const handleOpenCompare = useCallback((initialSpeaker) => {
    let names = [];
    if (initialSpeaker) {
      const name = typeof initialSpeaker === 'string' ? initialSpeaker : initialSpeaker.speaker;
      if (name) names = [name];
    } else if (compareList.length > 0) {
      names = compareList.map(s => s.speaker);
    }
    const param = names.length > 0 ? names.join(',') : 'open';
    navigate(`/?compare=${encodeURIComponent(param)}`);
  }, [compareList, navigate]);

  const handleAddSpeakerToCompare = useCallback((spkOrList) => {
    const rawAdd = Array.isArray(spkOrList) ? spkOrList : [spkOrList];
    const newNames = rawAdd.map(s => (typeof s === 'string' ? s : s?.speaker)).filter(Boolean);

    const currentNames = (currentRoute.type === 'compare' ? currentRoute.names : compareList.map(s => s.speaker)) || [];
    const combined = [...currentNames];
    newNames.forEach(n => {
      if (!combined.includes(n)) combined.push(n);
    });
    const finalNames = combined.slice(0, 12);

    navigate(`/?compare=${encodeURIComponent(finalNames.join(','))}`, true);
  }, [currentRoute, compareList, navigate]);

  const handleRemoveSpeakerFromCompare = useCallback((spk) => {
    const targetName = typeof spk === 'string' ? spk : spk?.speaker;
    const currentNames = (currentRoute.type === 'compare' ? currentRoute.names : compareList.map(s => s.speaker)) || [];
    const nextNames = currentNames.filter(n => n !== targetName);
    const param = nextNames.length > 0 ? nextNames.join(',') : 'open';

    navigate(`/?compare=${encodeURIComponent(param)}`, true);
  }, [currentRoute, compareList, navigate]);

  const navigateToView = useCallback((viewName) => {
    navigate(`/?view=${viewName}`);
  }, [navigate]);

  const handleOpenCategoryDetail = useCallback((catName) => {
    navigate(`/#category=${encodeURIComponent(catName)}`);
  }, [navigate]);

  const handleOpenTopicDetail = useCallback((topicId) => {
    navigate(`/#topic=${topicId}`);
  }, [navigate]);

  const handleSearchSubmit = useCallback((e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    navigate(`/?q=${encodeURIComponent(searchQuery.trim())}`);
  }, [searchQuery, navigate]);

  const handleKeywordClick = useCallback((keyword) => {
    setSearchQuery(keyword);
    navigate(`/?q=${encodeURIComponent(keyword.trim())}`);
  }, [setSearchQuery, navigate]);

  const activeCompareList = useMemo(() => {
    if (currentRoute.type !== 'compare') return compareList;
    if (!currentRoute.names || currentRoute.names.length === 0) return [];
    return currentRoute.names.map(name => resolveSpeaker(name)).filter(Boolean);
  }, [currentRoute, compareList, resolveSpeaker]);

  const activeSpeaker = useMemo(() => {
    if (currentRoute.type !== 'speaker' || !currentRoute.speakerName) return null;
    return resolveSpeaker(currentRoute.speakerName);
  }, [currentRoute, resolveSpeaker]);

  const threadsForSpeaker = useMemo(() => {
    if (!activeSpeaker) return [];
    let list = activeSpeaker.statements ? [...activeSpeaker.statements] : [];
    if (speakerCategory) {
      list = list.filter(s => s.category === speakerCategory || (s.category && s.category.includes(speakerCategory)));
    }
    if (speakerSort === 'recent') {
      list.sort((a, b) => new Date(b.meeting_date || 0) - new Date(a.meeting_date || 0));
    } else if (speakerSort === 'solution') {
      list.sort((a, b) => (b.solution_score || 0) - (a.solution_score || 0));
    } else if (speakerSort === 'local_focus') {
      list.sort((a, b) => (b.local_focus_score || 0) - (a.local_focus_score || 0));
    } else if (speakerSort === 'constructive') {
      list.sort((a, b) => (b.constructive_score || 0) - (a.constructive_score || 0));
    } else if (speakerSort === 'evidence') {
      list.sort((a, b) => (b.evidence_score || 0) - (a.evidence_score || 0));
    }
    return list;
  }, [activeSpeaker, speakerCategory, speakerSort]);

  const getIssueCountForCategory = useMemo(() => {
    const counts = {};
    billIssuesList.forEach(b => {
      const cat = getCategoryForBill(b);
      counts[cat] = (counts[cat] || 0) + 1;
    });
    return (catName) => counts[catName] || 0;
  }, [billIssuesList]);

  const uniqueSessions = useMemo(() => [...new Set((votesData || []).map(b => b.session_name).filter(Boolean))], [votesData]);
  const uniqueResults = useMemo(() => [...new Set((votesData || []).map(b => b.result).filter(Boolean))], [votesData]);

  const filteredBills = useMemo(() => {
    let list = votesData || [];
    if (submittedQuery.trim() !== '') {
      const q = submittedQuery.toLowerCase();
      list = list.filter(b =>
        (b.title && b.title.toLowerCase().includes(q)) ||
        (b.bill_number && b.bill_number.toLowerCase().includes(q)) ||
        (b.session_name && b.session_name.toLowerCase().includes(q))
      );
    }
    if (selectedSession) list = list.filter(b => b.session_name === selectedSession);
    if (selectedResult) list = list.filter(b => b.result === selectedResult);
    if (onlyContestedBills) {
      list = list.filter(bill => {
        const votes = Object.values(bill.votes || {});
          return votes.includes('賛成') && votes.includes('反対');
      });
    }
    return list;
  }, [votesData, submittedQuery, selectedSession, selectedResult, onlyContestedBills]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        <p className="text-sm font-black text-slate-500 tracking-wider">議会データを読み込み中...</p>
      </div>
    );
  }

  // 💡 総合ポータル画面（/ アクセス時）のレンダリング
  if (!cityCode) {
    return (
      <PortalTopView
        onSelectCity={(targetCity) => {
          window.history.pushState({}, '', `/${targetCity}/`);
          setCityCode(targetCity);
          window.dispatchEvent(new Event('app-navigate'));
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
        onOpenAbout={() => {
          setCityCode('kyoto');
          window.history.pushState({}, '', '/kyoto/?view=about');
          window.dispatchEvent(new Event('app-navigate'));
        }}
        onOpenMethodology={() => {
          setCityCode('kyoto');
          window.history.pushState({}, '', '/kyoto/?view=methodology');
          window.dispatchEvent(new Event('app-navigate'));
        }}
        onOpenGuide={() => {
          setCityCode('kyoto');
          window.history.pushState({}, '', '/kyoto/?view=guide');
          window.dispatchEvent(new Event('app-navigate'));
        }}
      />
    );
  }

  const renderModals = () => (
    <Suspense fallback={null}>
      <BillDetailModal
        cityCode={cityCode}
        isOpen={Boolean(selectedBillForModal)}
        onClose={() => setSelectedBillForModal(null)}
        bill={selectedBillForModal}
        issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null}
        speakerStats={speakerStats}
        onSpeakerClick={handleSpeakerClick}
      />
      <TimelineModal
        cityCode={cityCode}
        isOpen={isPanelOpen}
        onClose={() => setIsPanelOpen(false)}
        selectedContext={selectedContext}
        isLoading={isLoadingContext}
      />
    </Suspense>
  );

  const renderNavbar = (isCompare = false) => (
    <Navbar
      onLogoClick={handleGoHome}
      onOpenGuide={() => navigateToView('guide')}
      onOpenAbout={() => navigateToView('about')}
      onOpenMethodology={() => navigateToView('methodology')}
      onOpenCompare={() => handleOpenCompare()}
      onOpenMayor={() => navigateToView('mayor')}
      isCompareMode={isCompare}
      cityCode={cityCode} // 💡 NavbarにcityCodeを渡す
    />
  );

  // --- 排他的画面ルーティング ---
  const suspenseSpinner = (
    <div className="min-h-[50vh] flex items-center justify-center">
      <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  if (currentRoute.type === 'mayor') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <Suspense fallback={suspenseSpinner}>
            <MayorTrackerView
              data={mayorTrackerData}
              cityCode={cityCode}
              onBack={handleGoHome}
              onSelectBill={setSelectedBillForModal}
              onOpenMethodology={() => navigateToView('methodology')}
            />
          </Suspense>
        </div>
        {renderModals()}
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'guide') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <Suspense fallback={suspenseSpinner}>
            <GuidePage onBack={handleGoHome} onOpenMethodology={() => navigateToView('methodology')} onOpenAbout={() => navigateToView('about')} />
          </Suspense>
        </div>
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'about') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <Suspense fallback={suspenseSpinner}>
            <AboutPage onBack={handleGoHome} onOpenMethodology={() => navigateToView('methodology')} />
          </Suspense>
        </div>
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'methodology') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <Suspense fallback={suspenseSpinner}>
            <Methodology onBack={handleGoHome} />
          </Suspense>
        </div>
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'topic') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <Suspense fallback={suspenseSpinner}>
            <TopicDetailPage topicId={currentRoute.topicId} cityCode={cityCode} statements={statements} onBack={handleGoHome} onViewContext={handleViewContext} />
          </Suspense>
        </div>
        {renderModals()}
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'category') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <Suspense fallback={suspenseSpinner}>
            <CategoryDetailPage
              cityCode={cityCode}
              categoryName={currentRoute.categoryName}
              onBack={handleGoHome}
              topicStats={topicStats}
              filteredThreads={statements.filter(s => s.category === currentRoute.categoryName)}
              filteredBills={votesData.filter(b => getCategoryForBill(b) === currentRoute.categoryName)}
              speakerStats={speakerStats}
              issuesMap={issuesMap}
              onlyContestedBills={onlyContestedBills}
              setOnlyContestedBills={setOnlyContestedBills}
              onSpeakerClick={handleSpeakerClick}
              onViewContext={handleViewContext}
              onSelectBill={setSelectedBillForModal}
              onOpenMethodology={() => navigateToView('methodology')}
              onOpenTopicDetail={handleOpenTopicDetail}
            />
          </Suspense>
        </div>
        {renderModals()}
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'contested') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <Suspense fallback={suspenseSpinner}>
            <ContestedBillsView initialCategory={currentRoute.category} billIssues={billIssuesList} votesData={votesData} onClose={handleGoHome} onSpeakerClick={handleSpeakerClick} />
          </Suspense>
        </div>
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'compare') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(true)}
        <div className="flex-grow">
          <Suspense fallback={suspenseSpinner}>
            <CompareDashboard
              cityCode={cityCode}
              compareList={activeCompareList}
              allSpeakers={speakerStats}
              onAddSpeaker={handleAddSpeakerToCompare}
              onRemoveSpeaker={handleRemoveSpeakerFromCompare}
              onClose={handleGoHome}
              onViewContext={handleViewContext}
              onSpeakerClick={handleSpeakerClick}
              votesData={votesData}
              issuesMap={issuesMap}
              onSelectBill={setSelectedBillForModal}
              onOpenMethodology={() => navigateToView('methodology')}
            />
          </Suspense>
        </div>
        <Suspense fallback={null}>
          <BillDetailModal
            cityCode={cityCode} isOpen={Boolean(selectedBillForModal)} onClose={() => setSelectedBillForModal(null)} bill={selectedBillForModal} issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null} speakerStats={speakerStats} onSpeakerClick={(spk) => { setSelectedBillForModal(null); handleSpeakerClick(spk); }} />
          <TimelineModal
            cityCode={cityCode}
            isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
        </Suspense>
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'speaker' && activeSpeaker) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <SpeakerDetailView
            cityCode={cityCode}
            selectedSpeaker={activeSpeaker}
            speakerStats={speakerStats}
            speakerFilteredThreads={threadsForSpeaker}
            topicStats={topicStats}
            speakerCategory={speakerCategory}
            setSpeakerCategory={setSpeakerCategory}
            speakerSort={speakerSort}
            setSpeakerSort={setSpeakerSort}
            votesData={votesData}
            issuesMap={issuesMap}
            onOpenCompare={(spk) => handleOpenCompare(spk)}
            onBack={handleGoHome}
            onSpeakerClick={handleSpeakerClick}
            onViewContext={handleViewContext}
            onOpenMethodology={() => navigateToView('methodology')}
            onSelectBill={setSelectedBillForModal}
          />
        </div>
        <Suspense fallback={null}>
          <TimelineModal
            cityCode={cityCode}
            isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
          <BillDetailModal
            cityCode={cityCode} isOpen={Boolean(selectedBillForModal)} onClose={() => setSelectedBillForModal(null)} bill={selectedBillForModal} issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null} speakerStats={speakerStats} onSpeakerClick={handleSpeakerClick} />
        </Suspense>
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  if (currentRoute.type === 'search') {
    return (
      <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between">
        {renderNavbar(false)}
        <div className="flex-grow">
          <Suspense fallback={suspenseSpinner}>
            <SearchResultsView cityCode={cityCode}
              submittedQuery={currentRoute.query}
              onClearSearch={handleGoHome}
              filteredThreads={filteredThreads}
              filteredBills={filteredBills}
              filteredSpeakers={filteredSpeakers}
              speakerStats={speakerStats}
              issuesMap={issuesMap}
              onlyContestedBills={onlyContestedBills}
              setOnlyContestedBills={setOnlyContestedBills}
              onSpeakerClick={handleSpeakerClick}
              onViewContext={handleViewContext}
              onOpenCompare={(spk) => handleOpenCompare(spk)}
              onSelectBill={setSelectedBillForModal}
              onOpenMethodology={() => navigateToView('methodology')}
              onOpenTopicDetail={handleOpenTopicDetail}
            />
          </Suspense>
        </div>
        <Suspense fallback={null}>
          <BillDetailModal
            cityCode={cityCode} isOpen={Boolean(selectedBillForModal)} onClose={() => setSelectedBillForModal(null)} bill={selectedBillForModal} issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null} speakerStats={speakerStats} onSpeakerClick={handleSpeakerClick} />
          <TimelineModal
            cityCode={cityCode}
            isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} selectedContext={selectedContext} isLoading={isLoadingContext} />
        </Suspense>
        <FeedbackButton />
        <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans flex flex-col justify-between selection:bg-indigo-500 selection:text-white">
      {renderNavbar(false)}

      <main className="max-w-6xl mx-auto py-8 px-6 w-full flex-grow space-y-10">
        <HeroSection
          cityCode={cityCode}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onSearchSubmit={handleSearchSubmit}
          onKeywordClick={handleKeywordClick}
          onOpenGuide={() => navigateToView('guide')}
        />

        <MacroTopicMap
          cityCode={cityCode}
          topicStats={topicStats}
          selectedCategory={selectedCategory}
          onOpenCategoryDetail={handleOpenCategoryDetail}
          getIssueCountForCategory={getIssueCountForCategory}
          onOpenTopicDetail={handleOpenTopicDetail}
        />

        <HighlightedThreads
          statements={statements}
          onViewContext={handleViewContext}
          onSpeakerClick={handleSpeakerClick}
          onOpenMethodology={() => navigateToView('methodology')}
        />

        <MainTabView
          cityCode={cityCode}
          viewMode={viewMode}
          setViewMode={setViewMode}
          filteredSpeakers={filteredSpeakers}
          filteredThreads={filteredThreads}
          filteredBills={filteredBills}
          topicStats={topicStats}
          speakerStats={speakerStats}
          selectedDistrict={selectedDistrict}
          setSelectedDistrict={setSelectedDistrict}
          selectedCategory={selectedCategory}
          setSelectedCategory={setSelectedCategory}
          sortPerspective={sortPerspective}
          setSortPerspective={setSortPerspective}
          selectedSession={selectedSession}
          setSelectedSession={setSelectedSession}
          selectedResult={selectedResult}
          setSelectedResult={setSelectedResult}
          uniqueSessions={uniqueSessions}
          uniqueResults={uniqueResults}
          onlyContestedBills={onlyContestedBills}
          setOnlyContestedBills={setOnlyContestedBills}
          issuesMap={issuesMap}
          onSpeakerClick={handleSpeakerClick}
          onOpenCompare={(spk) => handleOpenCompare(spk)}
          onViewContext={handleViewContext}
          onSelectBill={setSelectedBillForModal}
          onOpenMethodology={() => navigateToView('methodology')}
        />
      </main>

      <Suspense fallback={null}>
        <BillDetailModal
          cityCode={cityCode}
          isOpen={Boolean(selectedBillForModal)}
          onClose={() => setSelectedBillForModal(null)}
          bill={selectedBillForModal}
          issue={selectedBillForModal ? issuesMap[`${selectedBillForModal.session_name}_${selectedBillForModal.bill_number}`] : null}
          speakerStats={speakerStats}
          onSpeakerClick={handleSpeakerClick}
        />

        <TimelineModal
          cityCode={cityCode}
          isOpen={isPanelOpen}
          onClose={() => setIsPanelOpen(false)}
          selectedContext={selectedContext}
          isLoading={isLoadingContext}
        />
      </Suspense>
      <FeedbackButton />
      <Footer cityCode={cityCode} onOpenMethodology={() => navigateToView('methodology')} />
    </div>
  );
}
