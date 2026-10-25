from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==========================================
# 1. HeroSection.jsx の動的対応
# ==========================================
hero_path = PROJECT_ROOT / "frontend" / "src" / "components" / "HeroSection.jsx"
hero_code = """import React from "react";
import { Search, Sparkles, Compass, ArrowRight } from "lucide-react";

const KYOTO_HOT_TOPICS = [
  "オーバーツーリズム",
  "市バス",
  "中小企業支援",
  "空き家対策",
  "伝統産業",
  "子育て支援",
];

const OSAKA_HOT_TOPICS = [
  "万博・夢洲跡地",
  "副首都ビジョン",
  "特区民泊",
  "路上喫煙禁止",
  "学校熱中症対策",
  "国保料府内統一",
];

export default function HeroSection({
  searchQuery,
  setSearchQuery,
  onSearchSubmit,
  onKeywordClick,
  onOpenGuide,
  cityCode = "kyoto"
}) {
  const isOsaka = cityCode === "osaka";
  const cityName = isOsaka ? "大阪市会" : "京都市会";
  const hotTopics = isOsaka ? OSAKA_HOT_TOPICS : KYOTO_HOT_TOPICS;

  return (
    <section className="text-center py-6 md:py-10 space-y-4">
      {/* サービスバッジ */}
      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-black shadow-2xs">
        <Sparkles className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
        {cityName} 公開データ × 生成AI分析
      </div>

      <h1 className="text-3xl md:text-5xl font-black text-slate-900 tracking-tight leading-tight">
        対話がわかる。政策が見える。
      </h1>
      <div className="space-y-2 max-w-xl mx-auto">
        <p className="text-xs md:text-sm text-slate-600 leading-relaxed font-medium">
          {isOsaka
            ? "大阪市会の本会議・全委員会における質疑スレッドを横断検索。統一ルーブリックによるAI評価と多角的な政策分析で、議員の政策対話の特徴を可視化します。"
            : "12万件超の発言記録を構造化し、5,100超の質疑スレッドを横断検索。文字数や登壇回数だけでは見えない議員それぞれの政策対話の特徴を、統一ルーブリックによるAI評価で可視化します。"}
        </p>
        <p className="text-xs md:text-sm font-black text-indigo-950">
          AIは入口。判断するのは市民です。
        </p>
      </div>

      {/* 分析対象バッジ */}
      <div className="inline-flex flex-wrap items-center justify-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-100/80 border border-slate-200 text-[11px] text-slate-600 font-bold">
        <span className="flex items-center gap-1 text-indigo-700">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-pulse" />
          分析対象
        </span>
        <span>現任期（2023年5月〜最新公開分）</span>
        <span className="text-slate-300">|</span>
        <span>
          {isOsaka
            ? "本会議・全常任委員会・特別委員会（現職81議員・1,260超の質疑スレッド）"
            : "本会議・全常任委員会・特別委員会（12万件超の発言・5,100超の質疑・全67議員・300件の議案賛否）"}
        </span>
      </div>

      {/* できることページへの直通バナー */}
      <div className="pt-1">
        <button
          onClick={onOpenGuide}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-white hover:bg-indigo-50 text-indigo-700 border border-indigo-200 text-xs font-bold transition-all shadow-2xs group cursor-pointer"
        >
          <Compass className="w-3.5 h-3.5 text-indigo-600" />
          <span>初めての方へ：当サイトでできること・活用ガイドを見る</span>
          <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform text-indigo-500" />
        </button>
      </div>

      {/* 検索入力窓 */}
      <div className="max-w-xl mx-auto pt-2">
        <form onSubmit={onSearchSubmit} className="relative flex items-center">
          <Search className="w-5 h-5 text-slate-400 absolute left-4 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={`${cityName}の論点、キーワード、議員名で議会全体を横断検索...`}
            className="w-full pl-12 pr-24 py-3.5 bg-white border border-slate-300 rounded-2xl shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm font-bold text-slate-800 placeholder:text-slate-400 transition-all"
          />
          <button
            type="submit"
            className="absolute right-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-black rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            検索
          </button>
        </form>

        {/* 注目の論点タグ */}
        <div className="flex items-center gap-1.5 flex-wrap justify-center mt-3 text-xs">
          <span className="text-[11px] font-bold text-slate-400">注目の論点:</span>
          {hotTopics.map((topic) => (
            <button
              key={topic}
              onClick={() => onKeywordClick(topic)}
              className="px-2.5 py-1 rounded-lg bg-white hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 text-slate-600 hover:text-indigo-600 text-[11px] font-bold transition-all cursor-pointer shadow-2xs"
            >
              {topic}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
"""
hero_path.write_text(hero_code, encoding="utf-8")
print("✅ HeroSection.jsx を更新しました。")

# ==========================================
# 2. App.jsx: HeroSection, MainTabView, Footer への cityCode 渡し
# ==========================================
app_path = PROJECT_ROOT / "frontend" / "src" / "App.jsx"
app_text = app_path.read_text(encoding="utf-8")

if "cityCode={cityCode}" not in app_text.split("<HeroSection")[1].split("/>")[0]:
    app_text = app_text.replace(
        "<HeroSection",
        "<HeroSection\n            cityCode={cityCode}"
    )

if "cityCode={cityCode}" not in app_text.split("<MainTabView")[1].split("/>")[0]:
    app_text = app_text.replace(
        "<MainTabView",
        "<MainTabView\n            cityCode={cityCode}"
    )

if "<Footer" in app_text and "cityCode={cityCode}" not in app_text.split("<Footer")[1].split("/>")[0]:
    app_text = app_text.replace(
        "<Footer",
        "<Footer cityCode={cityCode}"
    )

app_path.write_text(app_text, encoding="utf-8")
print("✅ App.jsx の props 渡しを更新しました。")

# ==========================================
# 3. MainTabView.jsx: 区フィルターの動的化（京都11区 / 大阪24区）
# ==========================================
mtv_path = PROJECT_ROOT / "frontend" / "src" / "components" / "MainTabView.jsx"
mtv_text = mtv_path.read_text(encoding="utf-8")

if "KYOTO_DISTRICTS" not in mtv_text:
    old_dist = "const DISTRICTS = ['北区', '上京区', '左京区', '中京区', '東山区', '下京区', '南区', '右京区', '西京区', '伏見区', '山科区'];"
    new_dist = """const KYOTO_DISTRICTS = ['北区', '上京区', '左京区', '中京区', '東山区', '下京区', '南区', '右京区', '西京区', '伏見区', '山科区'];
const OSAKA_DISTRICTS = [
  '北区', '都島区', '福島区', '此花区', '中央区', '西区', '港区', '大正区', 
  '天王寺区', '浪速区', '西淀川区', '淀川区', '東淀川区', '東成区', '生野区', 
  '旭区', '城東区', '鶴見区', '阿倍野区', '住之江区', '住吉区', '東住吉区', '平野区', '西成区'
];"""
    mtv_text = mtv_text.replace(old_dist, new_dist)

    mtv_text = re.sub(
        r"export default function MainTabView\(\{\s*",
        "export default function MainTabView({\n  cityCode = 'kyoto',\n",
        mtv_text
    )

    mtv_text = mtv_text.replace(
        "const [visibleSpeakersCount, setVisibleSpeakersCount] = useState(INITIAL_SPEAKERS_LIMIT);",
        """const activeDistricts = React.useMemo(() => {
    return cityCode === 'osaka' ? OSAKA_DISTRICTS : KYOTO_DISTRICTS;
  }, [cityCode]);
  const [visibleSpeakersCount, setVisibleSpeakersCount] = useState(INITIAL_SPEAKERS_LIMIT);"""
    )

    mtv_text = mtv_text.replace("DISTRICTS.map(", "activeDistricts.map(")
    mtv_path.write_text(mtv_text, encoding="utf-8")
    print("✅ MainTabView.jsx の区フィルターを更新しました。")

# ==========================================
# 4. Navbar.jsx: 切り替えプルダウンの常時表示
# ==========================================
nav_path = PROJECT_ROOT / "frontend" / "src" / "components" / "Navbar.jsx"
nav_text = nav_path.read_text(encoding="utf-8")
nav_text = nav_text.replace("hidden lg:block bg-slate-50", "bg-slate-50")
nav_path.write_text(nav_text, encoding="utf-8")
print("✅ Navbar.jsx の切り替えプルダウンを更新しました。")

# ==========================================
# 5. Footer.jsx: 都市名とリンクの動的化
# ==========================================
foot_path = PROJECT_ROOT / "frontend" / "src" / "components" / "Footer.jsx"
foot_text = foot_path.read_text(encoding="utf-8")

if "cityCode" not in foot_text:
    foot_text = re.sub(
        r"export default function Footer\(\{(.*?)\}\)",
        r"export default function Footer({\1, cityCode = 'kyoto'})",
        foot_text
    )
    foot_text = foot_text.replace("京都市会 公式", "{cityCode === 'osaka' ? '大阪市会 公式' : '京都市会 公式'}")
    foot_text = foot_text.replace("京都市議会議員", "{cityCode === 'osaka' ? '大阪市会議員' : '京都市議会議員'}")
    foot_text = foot_text.replace("https://www.city.kyoto.lg.jp/shikai/", "{cityCode === 'osaka' ? 'https://www.city.osaka.lg.jp/shikai/' : 'https://www.city.kyoto.lg.jp/shikai/'}")
    foot_path.write_text(foot_text, encoding="utf-8")
    print("✅ Footer.jsx を動的対応に更新しました。")

print("\n🎉 全コンポーネントの都市ブランディング更新が完了しました。")
