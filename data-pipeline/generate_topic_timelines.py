import os
import json
import time
import re
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types

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

# 8大カテゴリー全網羅・20大コア論点マスター定義
TARGET_TOPICS = [
    # 1. 都市再生・交通インフラ
    {
        "topic_id": "bus_fare_priority",
        "category": "都市再生・交通インフラ",
        "title": "市バス混雑対策と「市民優先価格（二重運賃）」導入",
        "keywords": ["市民優先価格", "二重運賃", "二重価格", "観光特急バス", "EX100", "混雑対策", "市バス混雑"]
    },
    {
        "topic_id": "vacant_house_tax",
        "category": "都市再生・交通インフラ",
        "title": "空き家税（非居住住宅利活用促進税）の施行と若者定住対策",
        "keywords": ["空き家税", "非居住住宅", "利活用促進税", "タワマン", "若者流出", "住宅取得", "すまい応援金"]
    },
    {
        "topic_id": "urban_planning_height_relax",
        "category": "都市再生・交通インフラ",
        "title": "都市計画・高さ制限緩和（若者居住・産業用地確保）",
        "keywords": ["都市計画", "高さ規制", "高さ制限", "容積率", "新都市計画", "南部創造", "産業用地"]
    },

    # 2. 産業・観光・地域経済
    {
        "topic_id": "accommodation_tax_revision",
        "category": "産業・観光・地域経済",
        "title": "宿泊税の税率引き上げと使途拡大（市民還元）",
        "keywords": ["宿泊税", "法定外目的税", "使途", "特別徴収", "税率改定", "日帰り客"]
    },
    {
        "topic_id": "overtourism_clean_manners",
        "category": "産業・観光・地域経済",
        "title": "オーバーツーリズム対策（スマートごみ箱・マナー啓発）",
        "keywords": ["オーバーツーリズム", "スマートごみ箱", "散乱ごみ", "マナー啓発", "ツーリストシップ", "観光公害"]
    },
    {
        "topic_id": "traditional_industry_succession",
        "category": "産業・観光・地域経済",
        "title": "伝統産業・地域企業の事業承継と担い手育成",
        "keywords": ["伝統産業", "事業承継", "後継者", "西陣織", "京友禅", "地場産業", "職人育成"]
    },

    # 3. 子育て・教育
    {
        "topic_id": "school_lunch_free",
        "category": "子育て・教育",
        "title": "全員制中学校給食の導入と給食無償化の財源論争",
        "keywords": ["中学校給食", "全員制給食", "給食費無償化", "給食無償", "親子方式", "給食センター"]
    },
    {
        "topic_id": "children_medical_subsidy",
        "category": "子育て・教育",
        "title": "子ども医療費助成の対象拡充（通院助成の上限引き上げ）",
        "keywords": ["子ども医療費", "医療費助成", "通院助成", "子育て負担軽減", "ワンコイン"]
    },
    {
        "topic_id": "teacher_workload_ict",
        "category": "子育て・教育",
        "title": "教員の多忙化解消・働き方改革と学校ICT・不登校対策",
        "keywords": ["教員の多忙化", "教員不足", "働き方改革", "学校ICT", "GIGAスクール", "不登校"]
    },

    # 4. 福祉・医療・健康
    {
        "topic_id": "senior_bus_pass_reform",
        "category": "福祉・医療・健康",
        "title": "敬老乗車証の制度見直し（自己負担割合・交付基準）",
        "keywords": ["敬老乗車証", "敬老パス", "自己負担", "交付基準", "移動権", "高齢者移動"]
    },
    {
        "topic_id": "national_health_insurance_burden",
        "category": "福祉・医療・健康",
        "title": "国民健康保険料・介護保険料の負担軽減策",
        "keywords": ["国民健康保険", "国保料", "介護保険料", "均等割", "保険料引き上げ", "滞納"]
    },
    {
        "topic_id": "vaccine_public_subsidy",
        "category": "福祉・医療・健康",
        "title": "帯状疱疹ワクチン等の任意予防接種公費助成",
        "keywords": ["帯状疱疹", "ワクチン助成", "予防接種", "公費助成", "定期接種化"]
    },

    # 5. 財政・行革
    {
        "topic_id": "fiscal_reform_reconstruction",
        "category": "財政・行革",
        "title": "行財政改革計画と「特別の財政支援」からの完全脱却",
        "keywords": ["行財政改革", "財政健全化", "特別の財政支援", "市債", "公債費", "基金枯渇"]
    },
    {
        "topic_id": "council_reform_transparency",
        "category": "財政・行革",
        "title": "議員定数・報酬および政務活動費の透明性向上",
        "keywords": ["議員定数", "議員報酬", "政務活動費", "領収書公開", "議会改革", "使途公開"]
    },
    {
        "topic_id": "public_facility_management_privatization",
        "category": "財政・行革",
        "title": "公共施設等総合管理計画と民間委託・資産売却",
        "keywords": ["公共施設", "民間委託", "包括管理", "資産売却", "指定管理者", "跡地活用"]
    },

    # 6. くらし・環境・エネルギー
    {
        "topic_id": "waste_charging_recycling",
        "category": "くらし・環境・エネルギー",
        "title": "ごみ処理有料化手数料とプラスチック資源循環",
        "keywords": ["ごみ袋", "指定ごみ袋", "有料化手数料", "プラスチック資源", "分別回収", "クリーンセンター"]
    },
    {
        "topic_id": "water_tariff_earthquake_pipe",
        "category": "くらし・環境・エネルギー",
        "title": "水道料金体系の改定と基幹管路の耐震化更新",
        "keywords": ["水道料金", "水道管", "耐震化", "老朽管", "管路更新", "上下水道局"]
    },
    {
        "topic_id": "decarbonization_solar_obligation",
        "category": "くらし・環境・エネルギー",
        "title": "脱炭素都市・建築物太陽光パネル設置義務化の推進",
        "keywords": ["脱炭素", "カーボンニュートラル", "太陽光パネル", "再エネ", "省エネ基準", "ZEH"]
    },

    # 7. 防災・減災・治安
    {
        "topic_id": "wooden_houses_earthquake_retrofitting",
        "category": "防災・減災・治安",
        "title": "木造密集市街地・京町家の耐震改修と路地奥防災",
        "keywords": ["木造密集", "耐震改修", "京町家耐震", "細街路", "延焼遮断", "消防団", "避難所"]
    },
    {
        "topic_id": "flood_control_urban_inundation",
        "category": "防災・減災・治安",
        "title": "鴨川・桂川水系の内水氾濫対策と雨水幹線整備",
        "keywords": ["内水氾濫", "浸水被害", "雨水幹線", "桂川", "鴨川", "治水", "ハザードマップ"]
    },

    # 8. 文化・景観・歴史
    {
        "topic_id": "culture_agency_relocation_impact",
        "category": "文化・景観・歴史",
        "title": "文化庁京都移転の波及効果創出と文化芸術支援",
        "keywords": ["文化庁", "文化移転", "文化芸術", "文化財保護", "芸大移転", "文化創造"]
    },
    {
        "topic_id": "townscape_wire_undergrounding",
        "category": "文化・景観・歴史",
        "title": "歴史的景観の保全・無電柱化と屋外広告物対策",
        "keywords": ["無電柱化", "景観保全", "屋外広告物", "電柱地中化", "歴史的風土", "町並み"]
    }
]

SYSTEM_PROMPT = """
あなたは地方財政および都市政策を専門とする政策アナリストです。
提示される地方議会の複数年度にわたる質疑ログから、該当政策論点の「Policy Timeline（政策展開の時系列変遷）」を構造化してください。

【出力要件】
1. lead_summary: 論点の背景、全体の構図、現在の着地点を客観的に要約（180字以内）。
2. current_status: 制度導入・検討の「現在地」（例: 令和9年度導入に向け国交省と協議中）。
3. conflict_axes: 会派間や行政・議会間で争点となった主な対立軸（2〜3件）。
4. timeline_phases: 時系列を「2〜3のフェーズ」に分割し、各フェーズでの【市側の答弁姿勢】と【議員側の主な主張】を整理すること。
5. 出力は以下のJSON形式のみを返すこと。

{
  "lead_summary": "...",
  "current_status": "...",
  "conflict_axes": ["...", "..."],
  "timeline_phases": [
    {
      "period": "2024年（令和6年）",
      "phase_title": "問題の顕在化と行政の慎重姿勢",
      "city_stance": "市側の公式姿勢の要約",
      "key_points": ["議員側の指摘ポイント", "追及内容"]
    }
  ]
}
"""

def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(f"GEMINI_API_KEY が設定されていません。確認先: {ENV_PATH}")
    return genai.Client(api_key=api_key)

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

def build_topic_timeline(client, topic, statements):
    """未要約の論点に対してのみ Gemini で構造化サマリーを生成"""
    sample_texts = []
    step = max(1, len(statements) // 25)
    sampled = statements[::step][:25]

    for s in sampled:
        date = s.get("meeting_date", "")
        title = s.get("meeting_title", "")
        speaker = s.get("speaker", "")
        body = (s.get("statement_text") or "")[:200]
        sample_texts.append(f"[{date} | {title} | {speaker}]: {body}")

    prompt_content = f"""
【論点テーマ】: {topic['title']}
【カテゴリ】: {topic['category']}

【該当する議事録ログ（抜粋）】:
""" + "\n".join(sample_texts)

    for attempt in range(3):
        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_content,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            parsed = json.loads(res.text)
            return parsed
        except Exception as e:
            time.sleep(2 * (attempt + 1))
    return None

def main():
    print("==================================================", flush=True)
    print("🚀 8大カテゴリー全網羅・20大政策論点タイムライン生成", flush=True)
    print("==================================================", flush=True)

    if not os.path.exists(CRAWLED_FILE):
        print(f"❌ 元データが存在しません: {CRAWLED_FILE}", flush=True)
        return

    with open(CRAWLED_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    existing_summaries = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for item in saved:
                    existing_summaries[item["topic_id"]] = item
            print(f"📖 既存のキャッシュを検出: {len(existing_summaries)} 件", flush=True)
        except Exception as e:
            print(f"⚠️ 既存キャッシュ読み込み警告: {e}", flush=True)

    client = None
    output_topics = []

    for idx, topic in enumerate(TARGET_TOPICS, start=1):
        t_id = topic["topic_id"]
        print(f"\n[{idx}/{len(TARGET_TOPICS)}] 処理中: {topic['title']} ({topic['category']})", flush=True)
        related = extract_related_statements(raw_data, topic["keywords"])
        print(f"   ➔ 該当質疑数: {len(related)} 件", flush=True)

        if not related:
            print("   ⚠️ 該当発言が存在しないためスキップします。", flush=True)
            continue

        ai_analysis = existing_summaries.get(t_id)

        # 既存キャッシュがない場合のみ Gemini API を実行
        if not ai_analysis:
            if client is None:
                client = get_gemini_client()
            print("   ✨ 新規論点のため AI 解析を実行中...", flush=True)
            ai_analysis = build_topic_timeline(client, topic, related)
            if not ai_analysis:
                print("   ❌ AI 解析に失敗しました。スキップします。", flush=True)
                continue
            time.sleep(1.0) # API レートリミット保護

        phases = ai_analysis.get("timeline_phases", [])
        for phase in phases:
            target_years = extract_target_years(phase.get("period", ""))
            
            year_matched = [
                r for r in related 
                if any(str(r.get("meeting_date", "")).startswith(y) for y in target_years)
                and is_meaningful_statement(r)
                and r.get("source_url")
            ]

            candidates = year_matched if year_matched else [r for r in related if is_meaningful_statement(r) and r.get("source_url")]

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
            "topic_id": t_id,
            "category": topic["category"],
            "title": topic["title"],
            "lead_summary": ai_analysis.get("lead_summary"),
            "current_status": ai_analysis.get("current_status"),
            "conflict_axes": ai_analysis.get("conflict_axes", []),
            "thread_count": len(related),
            "last_updated": related[-1].get("meeting_date", "2026-09-18"),
            "timeline_phases": phases
        })

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_topics, f, ensure_ascii=False, indent=2)

    print("\n==================================================", flush=True)
    print(f"🎉 完了: 全 {len(output_topics)} 件の政策論点タイムラインを配備しました。", flush=True)
    print(f"📁 保存先: {OUTPUT_FILE}", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    main()