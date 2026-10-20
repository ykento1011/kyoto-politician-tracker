import os
import json
import time
import re
import sys
from dotenv import load_dotenv

# パス設定と .env の明示的読み込み
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
ENV_PATH = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

CRAWLED_FILE = os.path.join(BASE_DIR, "sagebase_crawled_data.json")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "frontend", "public", "data", "topic_summaries.json")

# 監視・分析対象のコア論点定義
TARGET_TOPICS = [
    {
        "topic_id": "bus_fare_priority",
        "category": "都市再生・交通インフラ",
        "title": "市バス混雑対策と「市民優先価格（二重運賃）」導入",
        "keywords": ["市民優先価格", "二重運賃", "二重価格", "観光特急バス", "EX100", "混雑対策", "市バス混雑"]
    },
    {
        "topic_id": "accommodation_tax_revision",
        "category": "産業・観光・地域経済",
        "title": "宿泊税の税率引き上げと使途の使途拡大（市民還元）",
        "keywords": ["宿泊税", "法定外目的税", "使途", "特別徴収", "税率改定", "日帰り客"]
    },
    {
        "topic_id": "school_lunch_free",
        "category": "子育て・教育",
        "title": "全員制中学校給食の導入と給食無償化の財源論争",
        "keywords": ["中学校給食", "全員制給食", "給食費無償化", "給食無償", "親子方式", "給食センター"]
    },
    {
        "topic_id": "vacant_house_tax",
        "category": "都市再生・交通インフラ",
        "title": "空き家税（非居住住宅利活用促進税）の施行と若者定住対策",
        "keywords": ["空き家税", "非居住住宅", "利活用促進税", "タワマン", "若者流出", "住宅取得"]
    }
]

def extract_related_statements(raw_data, keywords):
    """キーワードに合致する質疑ログを抽出し、時系列順に整列"""
    matched = []
    for item in raw_data:
        text = str(item.get("statement_text") or "")
        title = str(item.get("meeting_title") or "")
        combined = f"{title} {text}"
        if any(k in combined for k in keywords):
            matched.append(item)
    matched.sort(key=lambda x: str(x.get("meeting_date") or ""))
    return matched

def extract_target_years(period_str):
    """フェーズの期間文字列から該当する西暦年リストを抽出"""
    years = []
    m = re.findall(r"(202\d)", str(period_str))
    if m:
        years.extend(m)
    if "令和5" in period_str or "2023" in period_str:
        years.append("2023")
    if "令和6" in period_str or "2024" in period_str:
        years.append("2024")
    if "令和7" in period_str or "2025" in period_str:
        years.append("2025")
    if "令和8" in period_str or "2026" in period_str:
        years.append("2026")
    return list(set(years))

def is_meaningful_statement(stmt):
    """単なる資料読み上げや開会・役付挨拶などの事務的発言を除外"""
    text = stmt.get("statement_text", "")
    if len(text) < 45:
        return False
    noise_patterns = [
        "資料の１ページをお開き", "機構・役付職員一覧", "御説明申し上げます", 
        "事務事業概要について", "よろしくお願いいたします。\nそれでは", "会議録署名議員"
    ]
    if any(p in text for p in noise_patterns):
        return False
    return True

def main():
    print("==================================================", flush=True)
    print("🚀 論点中心ビュー（Policy Timeline）データ高速生成", flush=True)
    print("==================================================", flush=True)

    if not os.path.exists(CRAWLED_FILE):
        print(f"❌ 元データが存在しません: {CRAWLED_FILE}", flush=True)
        return

    with open(CRAWLED_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 既存の topic_summaries.json があれば AI 要約テキストを再利用
    existing_summaries = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for item in saved:
                    existing_summaries[item["topic_id"]] = item
            print(f"📖 既存のAI要約キャッシュを検出: {len(existing_summaries)} 件を再利用します。", flush=True)
        except Exception as e:
            print(f"⚠️ 既存キャッシュ読み込みスキップ: {e}", flush=True)

    output_topics = []

    for topic in TARGET_TOPICS:
        t_id = topic["topic_id"]
        print(f"\n🔍 処理中: {topic['title']} ...", flush=True)
        related = extract_related_statements(raw_data, topic["keywords"])
        print(f"   ➔ 関連発言数: {len(related)} 件", flush=True)

        if not related:
            continue

        cached = existing_summaries.get(t_id)
        if not cached:
            print("   ⚠️ 既存要約が存在しないためスキップします。", flush=True)
            continue

        phases = cached.get("timeline_phases", [])
        print(f"   ⏳ フェーズ（{len(phases)}段階）ごとの発言ログを年代別に紐付け中...", flush=True)

        for phase in phases:
            target_years = extract_target_years(phase.get("period", ""))
            
            # そのフェーズの年代に合致する実質質疑を抽出
            year_matched = [
                r for r in related 
                if any(str(r.get("meeting_date", "")).startswith(y) for y in target_years)
                and is_meaningful_statement(r)
                and r.get("source_url")
            ]

            # 該当年の実質質疑があればそこから、無ければ全体の実質質疑から選定
            candidates = year_matched if year_matched else [r for r in related if is_meaningful_statement(r) and r.get("source_url")]

            # 各フェーズに最大2件の実質発言を紐付け
            phase["exchanges"] = []
            for m in candidates[:2]:
                phase["exchanges"].append({
                    "meeting_date": m.get("meeting_date"),
                    "meeting_title": m.get("meeting_title"),
                    "speaker": m.get("speaker"),
                    "statement_summary": (m.get("statement_text") or "")[:140].replace("\n", " ") + "...",
                    "source_url": m.get("source_url")
                })

        output_topics.append({
            "topic_id": cached["topic_id"],
            "category": cached["category"],
            "title": cached["title"],
            "lead_summary": cached["lead_summary"],
            "current_status": cached["current_status"],
            "conflict_axes": cached.get("conflict_axes", []),
            "thread_count": len(related),
            "last_updated": related[-1].get("meeting_date", "2026-09-18"),
            "timeline_phases": phases
        })

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_topics, f, ensure_ascii=False, indent=2)

    print("\n==================================================", flush=True)
    print(f"🎉 完了: {len(output_topics)} 件の論点データを年代別に正確に紐付けました。", flush=True)
    print(f"📁 保存先: {OUTPUT_FILE}", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    main()