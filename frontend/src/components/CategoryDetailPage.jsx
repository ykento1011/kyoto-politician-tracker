import React, { useState, useMemo, useEffect } from 'react';
import {
    ArrowLeft, PieChart, Sparkles, Milestone,
    MessageSquare, ArrowRight, SlidersHorizontal, ArrowUpDown,
    Search, ChevronDown, User, Calendar, Landmark
} from 'lucide-react';
import ThreadCard from './ThreadCard';
import { cleanName } from '../utils/styleHelpers';

// 8大カテゴリーの包括的な政策総括マスター
const CATEGORY_OVERVIEWS = {
    '財政・行革': {
        lead: '財政破綻（特別の財政支援団体転落）の危機からの脱却と、行財政改革計画の着地が最大の焦点。敬老乗車証や保育料の見直しなど「身を切る改革・市民負担増」の是非と、市債残高圧縮・公債償還基金の回復状況を巡り、全会派で激しい攻防が交わされました。',
        key_points: [
            '「特別の財政支援」依存からの完全脱却と、単年度収支の黒字化達成度の評価',
            '市民サービス削減・負担増（敬老パス、保育料、施設利用料）の市民生活への影響',
            '市有資産の売却・民間包括委託（アウトソーシング）による行革効果と公共性の維持'
        ]
    },
    '都市再生・交通インフラ': {
        lead: '観光客急増に伴う市バスの慢性的大混雑への市民生活対策と、人口流出抑制に向けた都市構造の転換が二大テーマ。市民優先価格（二重運賃）導入への挑戦や、高さ・容積率規制の緩和による若者定住・産業用地確保、空き家税の施行準備が議論の中心となりました。',
        key_points: [
            '市バス混雑に対する「観光特急バス」の効果検証と「市民優先価格」導入の線引き',
            '京都駅南側やらくなん進都における高さ規制緩和と、歴史的景観保全のバランス',
            '空き家税（非居住住宅利活用促進税）の施行準備と、若年・子育て世帯向け定住支援策'
        ]
    },
    '産業・観光・地域経済': {
        lead: '急回復したインバウンド観光の恩恵をいかに市民生活に還元し、生活環境悪化を防ぐかという「オーバーツーリズムとの調和」が焦点。宿泊税の税率引き上げ・使途拡大の議論と、後継者不足が深刻化する伝統産業・中小企業への実効的な承継支援が争われました。',
        key_points: [
            '宿泊税の引き上げ（最高額改定）と、その税収使途の市民還元（道路・交通整備等）',
            '祇園・清水など特定地域における散乱ごみ（スマートごみ箱）、マナー問題対策',
            '西陣織・京友禅をはじめとする伝統産業の担い手育成と、新商品開発・販路開拓'
        ]
    },
    '子育て・教育': {
        lead: '長年の懸案であった全員制中学校給食の実現方式（大規模給食センター方式）を巡る議論が白熱。500億円規模に上る巨額投資や避難所機能の喪失への懸念と、給食費無償化の財源論争、さらに教員の多忙化・不登校対策が連動して追及されました。',
        key_points: [
            '塔南高校跡地の大規模給食センター建設計画と、学校調理方式を求める市民の声',
            '小中学校給食費の完全無償化に向けた財源確保と、国への制度化要望',
            '教員の長時間労働是正、学校ICT端末（GIGAスクール）の活用と不登校児童への支援'
        ]
    },
    '福祉・医療・健康': {
        lead: '高齢化と社会保障費増大が進む中、持続可能なセーフティネットのあり方が議論されました。敬老乗車証の自己負担率改定の影響検証、国民健康保険料・介護保険料の負担軽減策、帯状疱疹ワクチンの公費助成化などが主要な論点となりました。',
        key_points: [
            '敬老乗車証の制度見直しに伴う高齢者の外出機会・健康寿命への影響',
            '国保料の均等割引き下げなど低所得・子育て世帯の保険料負担軽減',
            '帯状疱疹ワクチンや子宮頸がんワクチンなど任意予防接種に対する助成拡充'
        ]
    },
    'くらし・環境・エネルギー': {
        lead: '2050年カーボンニュートラル実現に向けた脱炭素条例の推進と、市民生活インフラの維持が論点。新築建築物への太陽光パネル設置義務化やプラスチック資源一括回収の開始、老朽化した水道管路の耐震更新と料金体系のあり方が議論されました。',
        key_points: [
            '建築物への太陽光発電設備設置義務化と、歴史都市・景観基準との整合性',
            'プラスチック資源の一括分別回収開始に伴う収集体制・市民周知の徹底',
            '耐震基準を満たさない老朽水道管の破裂防止と、将来的な料金改定議論'
        ]
    },
    '防災・減災・治安': {
        lead: '能登半島地震の発生を受け、木造密集市街地や細街路（路地奥）を多く抱える京都特有の都市防災が再クローズアップ。京町家の耐震・防火改修支援や、桂川・鴨川水系の内水氾濫対策、避難所機能の強化が精力的に議論されました。',
        key_points: [
            '密集市街地・路地奥住宅の接道問題と、延焼遮断・耐震化への公的助成',
            'ゲリラ豪雨・線状降水帯による内水氾濫防止に向けた雨水幹線・貯留施設の整備',
            '避難所における段ボールベッド・プライバシー確保と女性・要支援者への配慮'
        ]
    },
    '文化・景観・歴史': {
        lead: '文化庁の京都全面移転を果たしたことを受け、その政策効果をいかに全国・地域に波及させるかが焦点。文化芸術活動への公的支援、歴史的街並みを支える無電柱化（電柱地中化）の推進とコスト縮減、屋外広告物規制の継承が討議されました。',
        key_points: [
            '文化庁移転に伴う文化政策のイノベーションと、市民・芸術家への恩恵波及',
            '観光地・歴史地区における無電柱化の推進ペースと事業費の抑制策',
            '伝統的な町並みを守る新景観政策の維持と、地域産業の活力維持の両立'
        ]
    }
};

const CATEGORY_TOPICS_MAP = {
    '都市再生・交通インフラ': [
        { id: 'bus_fare_priority', title: '市バス混雑・市民優先価格' },
        { id: 'hokuriku_shinkansen_extension', title: '北陸新幹線延伸・地下水と財政負担' }, // 💡 追加
        { id: 'vacant_house_tax', title: '空き家税・若者定住' },
        { id: 'urban_planning_height_relax', title: '高さ規制緩和・産業用地' }
    ],
    '産業・観光・地域経済': [
        { id: 'accommodation_tax_revision', title: '宿泊税引き上げ・使途拡大' },
        { id: 'overtourism_clean_manners', title: 'オーバーツーリズム・散乱ごみ' },
        { id: 'traditional_industry_succession', title: '伝統産業・事業承継' },
        { id: 'central_market_redevelopment', title: '中央卸売市場・食肉市場再整備' }
    ],
    '子育て・教育': [
        { id: 'school_lunch_free', title: '全員制中学校給食・無償化' },
        { id: 'children_medical_subsidy', title: '子ども医療費助成の拡充' },
        { id: 'teacher_workload_ict', title: '教員の多忙化・学校ICT' },
        { id: 'nursery_teacher_subsidy_reform', title: '民間保育所独自給与補助見直し' }
    ],
    '福祉・医療・健康': [
        { id: 'senior_bus_pass_reform', title: '敬老乗車証・制度見直し' },
        { id: 'national_health_insurance_burden', title: '国保料・介護保険料の軽減' },
        { id: 'vaccine_public_subsidy', title: '帯状疱疹ワクチン公費助成' },
        { id: 'poverty_hikikomori_support', title: '生活困窮・ひきこもり相談' }
    ],
    '財政・行革': [
        { id: 'fiscal_reform_reconstruction', title: '行財政改革・財政健全化' },
        { id: 'council_reform_transparency', title: '議員定数・政務活動費公開' },
        { id: 'public_facility_management_privatization', title: '公共施設包括管理・資産売却' },
        { id: 'city_hall_reconstruction_cost', title: '市役所新庁舎整備・分庁舎集約' }
    ],
    'くらし・環境・エネルギー': [
        { id: 'waste_charging_recycling', title: '指定ごみ袋・プラ資源循環' },
        { id: 'water_tariff_earthquake_pipe', title: '水道料金改定・管路耐震化' },
        { id: 'decarbonization_solar_obligation', title: '脱炭素・太陽光パネル義務化' },
        { id: 'bike_sharing_illegal_parking', title: '放置自転車対策・シェアサイクル' }
    ],
    '防災・減災・治安': [
        { id: 'wooden_houses_earthquake_retrofitting', title: '木密・京町家耐震・路地防災' },
        { id: 'flood_control_urban_inundation', title: '鴨川・桂川水系の内水氾濫対策' },
        { id: 'landslide_disaster_prevention', title: '土砂災害警戒区域・砂防対策' },
        { id: 'evacuation_center_bed_women', title: '避難所段ボールベッド・女性視点防災' }
    ],
    '文化・景観・歴史': [
        { id: 'culture_agency_relocation_impact', title: '文化庁移転の波及効果創出' },
        { id: 'townscape_wire_undergrounding', title: '歴史的景観・無電柱化' },
        { id: 'world_heritage_buffer_zone', title: '世界遺産バッファーゾーン保全' },
        { id: 'kyoto_arts_univ_sujin_impact', title: '京都芸大崇仁移転・地域活性化' }
    ]
};

// 会議体名を正規化して抽出するヘルパー
function getMeetingBodyName(stmt) {
    if (stmt.committee) return stmt.committee;
    const title = stmt.meeting_title || '';
    if (title.includes('本会議')) return '本会議';
    if (title.includes('予算特別委員会')) return '予算特別委員会';
    if (title.includes('決算特別委員会')) return '決算特別委員会';
    if (title.includes('総務消防委員会')) return '総務消防委員会';
    if (title.includes('文教はぐくみ委員会')) return '文教はぐくみ委員会';
    if (title.includes('まちづくり委員会')) return 'まちづくり委員会';
    if (title.includes('産業交通水道委員会')) return '産業交通水道委員会';
    if (title.includes('くらし環境委員会')) return 'くらし環境委員会';
    if (title.includes('市会運営委員会')) return '市会運営委員会';
    const match = title.match(/([^\s]+委員会)/);
    if (match) return match[1];
    return 'その他委員会';
}

const INITIAL_VISIBLE_COUNT = 15;

export default function CategoryDetailPage({
    categoryName,
    onBack,
    topicStats,
    filteredThreads = [],
    filteredBills = [],
    speakerStats = [],
    issuesMap = {},
    onlyContestedBills,
    setOnlyContestedBills,
    onSpeakerClick,
    onViewContext,
    onSelectBill,
    onOpenMethodology,
    onOpenTopicDetail
}) {
    const stat = topicStats.find(t => t.name === categoryName) || { count: filteredThreads.length, percentage: 0 };
    const overview = CATEGORY_OVERVIEWS[categoryName] || {
        lead: `京都市議会において「${categoryName}」分野に関する質疑が多数記録されています。`,
        key_points: []
    };
    const coreTopics = CATEGORY_TOPICS_MAP[categoryName] || [];

    // 絞り込みフィルター用のステート
    const [selectedYear, setSelectedYear] = useState('');
    const [selectedCommittee, setSelectedCommittee] = useState('');
    const [selectedSpeaker, setSelectedSpeaker] = useState('');
    const [filterQuery, setFilterQuery] = useState('');
    const [sortOrder, setSortOrder] = useState('recent'); // 'recent' | 'score'
    const [visibleCount, setVisibleCount] = useState(INITIAL_VISIBLE_COUNT);

    // カテゴリー内の全質疑から、選択肢リスト（年次・会議体・発言者）を動的に生成
    const availableYears = useMemo(() => {
        const set = new Set();
        filteredThreads.forEach(s => {
            if (s.meeting_date && s.meeting_date.length >= 4) {
                set.add(s.meeting_date.slice(0, 4));
            }
        });
        return Array.from(set).sort((a, b) => b.localeCompare(a));
    }, [filteredThreads]);

    const availableCommittees = useMemo(() => {
        const counts = {};
        filteredThreads.forEach(s => {
            const name = getMeetingBodyName(s);
            counts[name] = (counts[name] || 0) + 1;
        });
        return Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .map(([name]) => name);
    }, [filteredThreads]);

    const availableSpeakers = useMemo(() => {
        const counts = {};
        filteredThreads.forEach(s => {
            const name = cleanName(s.speaker);
            if (name) counts[name] = (counts[name] || 0) + 1;
        });
        return Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .map(([name, count]) => ({ name, count }));
    }, [filteredThreads]);

    // フィルター変更時に表示件数をリセット
    useEffect(() => {
        setVisibleCount(INITIAL_VISIBLE_COUNT);
    }, [selectedYear, selectedCommittee, selectedSpeaker, filterQuery, sortOrder]);

    // 絞り込み ＆ ソート処理
    const processedThreads = useMemo(() => {
        let list = [...filteredThreads];

        if (selectedYear) {
            list = list.filter(s => (s.meeting_date || '').startsWith(selectedYear));
        }

        if (selectedCommittee) {
            list = list.filter(s => getMeetingBodyName(s) === selectedCommittee);
        }

        if (selectedSpeaker) {
            list = list.filter(s => cleanName(s.speaker) === selectedSpeaker);
        }

        if (filterQuery.trim()) {
            const q = filterQuery.trim().toLowerCase();
            list = list.filter(s =>
                (s.statement_text && s.statement_text.toLowerCase().includes(q)) ||
                (s.summary && s.summary.toLowerCase().includes(q)) ||
                (s.meeting_title && s.meeting_title.toLowerCase().includes(q))
            );
        }

        if (sortOrder === 'recent') {
            list.sort((a, b) => String(b.meeting_date || '').localeCompare(String(a.meeting_date || '')));
        } else if (sortOrder === 'score') {
            list.sort((a, b) => {
                const scoreA = (a.solution_score || 0) + (a.evidence_score || 0) + (a.local_focus_score || 0) + (a.constructive_score || 0);
                const scoreB = (b.solution_score || 0) + (b.evidence_score || 0) + (b.local_focus_score || 0) + (b.constructive_score || 0);
                return scoreB - scoreA;
            });
        }

        return list;
    }, [filteredThreads, selectedYear, selectedCommittee, selectedSpeaker, filterQuery, sortOrder]);

    const displayedThreads = useMemo(() => {
        return processedThreads.slice(0, visibleCount);
    }, [processedThreads, visibleCount]);

    const isFiltered = Boolean(selectedYear || selectedCommittee || selectedSpeaker || filterQuery);

    const handleResetFilters = () => {
        setSelectedYear('');
        setSelectedCommittee('');
        setSelectedSpeaker('');
        setFilterQuery('');
    };

    return (
        <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans pb-24 selection:bg-indigo-500 selection:text-white">
            {/* 画面上部固定バー */}
            <div className="bg-white border-b border-slate-200 sticky top-0 z-30 px-6 py-3.5 shadow-2xs">
                <div className="max-w-5xl mx-auto flex items-center justify-between">
                    <button
                        onClick={onBack}
                        className="inline-flex items-center text-xs font-bold text-slate-600 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50 border border-slate-200 px-3.5 py-2 rounded-xl transition-colors cursor-pointer"
                    >
                        <ArrowLeft className="w-4 h-4 mr-1.5" />
                        マクロ論戦マップへ戻る
                    </button>

                    <span className="text-xs font-bold text-slate-400">
                        市政マクロ分析 / 分野別詳細
                    </span>
                </div>
            </div>

            <main className="max-w-5xl mx-auto px-6 pt-8 space-y-8">

                {/* ① ヘッダー部 */}
                <header className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-100 flex items-center gap-1">
                            <PieChart className="w-3.5 h-3.5" />
                            政策カテゴリー
                        </span>
                        <span className="text-xs text-slate-500 font-bold">
                            市議会全体の <span className="text-indigo-600 font-black">{stat.percentage}%</span>（{filteredThreads.length}質疑スレッド）
                        </span>
                    </div>

                    <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight">
                        {categoryName}
                    </h1>
                </header>

                {/* ② AI包括解説カード */}
                <section className="bg-white rounded-3xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-5">
                    <div className="flex items-center gap-2 text-indigo-600 font-black text-xs uppercase tracking-wider">
                        <Sparkles className="w-4 h-4 fill-indigo-100" />
                        AI包括解説：この任期における「{categoryName}」の論戦総括
                    </div>

                    <p className="text-sm md:text-base leading-relaxed text-slate-700 font-medium">
                        {overview.lead}
                    </p>

                    {overview.key_points.length > 0 && (
                        <div className="pt-4 border-t border-slate-100 space-y-2.5">
                            <span className="text-[11px] font-black text-slate-400 uppercase tracking-wider block">
                                この分野における主な対立軸・重要争点
                            </span>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                                {overview.key_points.map((pt, i) => (
                                    <div key={i} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs font-bold text-slate-700 leading-relaxed flex items-start gap-2">
                                        <span className="w-2 h-2 rounded-full bg-indigo-500 mt-1 shrink-0" />
                                        <span>{pt}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </section>

                {/* ③ 注目の政策タイムライン（Policy Timeline導線） */}
                {coreTopics.length > 0 && (
                    <section className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                                <Milestone className="w-4 h-4 text-indigo-600" />
                                この分野の注目の政策タイムライン（年代別の議論の変遷）
                            </h2>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            {coreTopics.map((ct) => (
                                <button
                                    key={ct.id}
                                    onClick={() => onOpenTopicDetail(ct.id)}
                                    className="p-4 bg-white rounded-2xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all text-left flex flex-col justify-between group cursor-pointer"
                                >
                                    <div>
                                        <span className="text-[10px] font-black text-indigo-600 uppercase tracking-wider block mb-1">
                                            Policy Timeline
                                        </span>
                                        <h3 className="text-sm font-extrabold text-slate-900 group-hover:text-indigo-600 transition-colors">
                                            {ct.title}
                                        </h3>
                                    </div>
                                    <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-slate-400 group-hover:text-indigo-600">
                                        <span>詳細タイムラインを見る</span>
                                        <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                                    </div>
                                </button>
                            ))}
                        </div>
                    </section>
                )}

                {/* ④ 質疑スレッド一覧（全件対象の高度フィルターバー付き） */}
                <section className="space-y-5 pt-4 border-t border-slate-200">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                            <h2 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                                <MessageSquare className="w-4 h-4 text-indigo-600" />
                                「{categoryName}」に関する質疑スレッド
                            </h2>
                            <p className="text-xs text-slate-400 font-bold mt-0.5">
                                該当: <span className="text-indigo-600">{processedThreads.length}</span> 件 / 全 {filteredThreads.length} 件
                            </p>
                        </div>
                    </div>

                    {/* フィルターバー */}
                    <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs space-y-3 text-xs">
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5">

                            {/* 年次フィルター */}
                            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5">
                                <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                <select
                                    value={selectedYear}
                                    onChange={(e) => setSelectedYear(e.target.value)}
                                    className="w-full bg-transparent font-bold text-slate-700 outline-none cursor-pointer"
                                >
                                    <option value="">すべての年次</option>
                                    {availableYears.map(y => (
                                        <option key={y} value={y}>{y}年</option>
                                    ))}
                                </select>
                            </div>

                            {/* 会議体フィルター */}
                            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5">
                                <Landmark className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                <select
                                    value={selectedCommittee}
                                    onChange={(e) => setSelectedCommittee(e.target.value)}
                                    className="w-full bg-transparent font-bold text-slate-700 outline-none cursor-pointer truncate"
                                >
                                    <option value="">すべての会議体</option>
                                    {availableCommittees.map(c => (
                                        <option key={c} value={c}>{c}</option>
                                    ))}
                                </select>
                            </div>

                            {/* 発言者フィルター（肩書を省いた氏名表記） */}
                            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5">
                                <User className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                <select
                                    value={selectedSpeaker}
                                    onChange={(e) => setSelectedSpeaker(e.target.value)}
                                    className="w-full bg-transparent font-bold text-slate-700 outline-none cursor-pointer truncate"
                                >
                                    <option value="">すべての発言者</option>
                                    {availableSpeakers.map(spk => (
                                        <option key={spk.name} value={spk.name}>
                                            {spk.name} ({spk.count}件)
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* キーワード内検索 */}
                            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5">
                                <Search className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                <input
                                    type="text"
                                    value={filterQuery}
                                    onChange={(e) => setFilterQuery(e.target.value)}
                                    placeholder="キーワードで絞り込み..."
                                    className="w-full bg-transparent font-bold text-slate-700 outline-none placeholder:text-slate-400"
                                />
                            </div>

                        </div>

                        {/* ソート順 ＆ リセット */}
                        <div className="flex items-center justify-between pt-2 border-t border-slate-100 flex-wrap gap-2">
                            <div className="flex items-center gap-1.5">
                                <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                                <select
                                    value={sortOrder}
                                    onChange={(e) => setSortOrder(e.target.value)}
                                    className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 font-bold text-slate-700 outline-none cursor-pointer"
                                >
                                    <option value="recent">登壇日が新しい順</option>
                                    <option value="score">AI評価スコア順</option>
                                </select>
                            </div>

                            {isFiltered && (
                                <button
                                    onClick={handleResetFilters}
                                    className="text-xs font-bold text-rose-600 hover:underline cursor-pointer"
                                >
                                    条件をすべてリセット
                                </button>
                            )}
                        </div>
                    </div>

                    {/* スレッドカードのレンダリング */}
                    <div className="space-y-6">
                        {displayedThreads.length > 0 ? (
                            displayedThreads.map((stmt) => (
                                <ThreadCard cityCode={cityCode}
                                    key={stmt.id}
                                    stmt={stmt}
                                    speakerInfo={speakerStats.find(s => s.speaker === cleanName(stmt.speaker))}
                                    onSpeakerClick={onSpeakerClick}
                                    onViewContext={onViewContext}
                                    showSpeakerHeader={true}
                                    onOpenMethodology={onOpenMethodology}
                                />
                            ))
                        ) : (
                            <div className="text-center py-16 bg-white rounded-2xl border border-slate-200 text-xs font-bold text-slate-400">
                                選択した条件に一致する質疑スレッドは見つかりませんでした。
                            </div>
                        )}
                    </div>

                    {/* ページネーション（さらに表示ボタン） */}
                    {visibleCount < processedThreads.length && (
                        <div className="text-center pt-4">
                            <button
                                onClick={() => setVisibleCount(prev => prev + 15)}
                                className="inline-flex items-center gap-1.5 px-6 py-3 rounded-xl bg-white hover:bg-slate-50 border border-slate-300 text-xs font-bold text-slate-700 shadow-2xs hover:shadow-xs transition-all cursor-pointer"
                            >
                                <span>さらに質疑を表示する（残り {processedThreads.length - visibleCount} 件）</span>
                                <ChevronDown className="w-4 h-4 text-slate-400" />
                            </button>
                        </div>
                    )}
                </section>

            </main>
        </div>
    );
}