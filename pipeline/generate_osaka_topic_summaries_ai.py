import os
import json
import re
import time
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / "data-pipeline" / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY が設定されていません。")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3.5-flash-lite")

STATEMENTS_PATH = PROJECT_ROOT / "frontend" / "public" / "data" / "osaka_statements_summary.json"
MASTER_PATH = PROJECT_ROOT / "frontend" / "src" / "utils" / "osakaCouncilorMaster.js"
OUTPUT_PATH = PROJECT_ROOT / "frontend" / "public" / "data" / "osaka_topic_summaries.json"

OSAKA_TOPIC_CONFIGS = [
    {
        "topic_id": "fukushuto_daitoshi_seido",
        "category": "財政・行革",
        "title": "副首都ビジョンと大都市制度（法定協議会・特別区）",
        "keywords": ["副首都", "法定協議会", "特別区", "大都市制度", "住民投票"]
    },
    {
        "topic_id": "osaka_expo_legacy_yumeshima",
        "category": "都市再生・交通インフラ",
        "title": "夢洲まちづくり・第2期区域と万博跡地活用",
        "keywords": ["夢洲", "第2期", "マスタープラン", "跡地", "地盤沈下"]
    },
    {
        "topic_id": "special_minpaku_regulation",
        "category": "産業・観光・地域経済",
        "title": "特区民泊の規制強化と違法民泊・住環境対策",
        "keywords": ["特区民泊", "民泊", "違法民泊", "立入検査", "宿泊"]
    },
    {
        "topic_id": "street_smoking_ban_spread",
        "category": "くらし・環境・エネルギー",
        "title": "市内全域路上喫煙禁止と喫煙所インフラ整備",
        "keywords": ["路上喫煙", "喫煙所", "過料", "たばこ", "分煙"]
    },
    {
        "topic_id": "school_heatstroke_ssr_support",
        "category": "子育て・教育",
        "title": "学校熱中症対策・不登校支援（SSR）の全校拡充",
        "keywords": ["熱中症", "ウォータークーラー", "不登校", "スペシャルサポートルーム", "SSR", "夜間学級"]
    },
    {
        "topic_id": "kokuho_kaigo_premium_burden",
        "category": "福祉・医療・健康",
        "title": "国保料府内統一と第9期介護保険料の負担軽減",
        "keywords": ["国民健康保険", "国保", "介護保険", "統一保険料", "ケアマネジャー"]
    },
    {
        "topic_id": "sewage_accident_disaster_digital",
        "category": "防災・減災・治安",
        "title": "地下インフラ事故防止と防災デジタル・個別避難計画",
        "keywords": ["事故", "ケーシング", "下水道", "個別避難計画", "防災デジタル", "消防"]
    },
    {
        "topic_id": "traditional_culture_outdoor_ad",
        "category": "文化・景観・歴史",
        "title": "上方伝統芸能の継承と屋外広告物景観基準の見直し",
        "keywords": ["伝統芸能", "上方", "屋外広告", "景観", "歴史", "文化振興"]
    }
]

def generate_ai_summary(topic_title, category, periods_data):
    prompt = f"""
あなたは地方自治・地方議会（大阪市会）の政策分析エキスパートです。
以下の大阪市会における質疑データ群を詳細に分析し、政策タイムラインの要約を厳密なJSON形式で作成してください。

【対象トピック】
カテゴリー: {category}
論点名: {topic_title}

【時系列ごとの質疑データ】
{json.dumps(periods_data, ensure_ascii=False, indent=2)}

【出力要件】
以下のスキーマに完全に従ったJSONを出力してください:
{{
  "lead_summary": "トピック全体の概要・議論の背景と争点を200字程度で簡潔にまとめた文章",
  "current_status": "最新期（2025〜2026年等）における市の施策到達点や直近の課題状況（150字程度）",
  "conflict_axes": [
    "対立軸・主要論点1（議会と理事者、または会派間の対立点）",
    "対立軸・主要論点2",
    "対立軸・主要論点3"
  ],
  "phases": [
    {{
      "period": "（入力のperiod文字列をそのまま使用）",
      "phase_title": "この時期の議論の特徴を表す20文字前後のサブタイトル",
      "city_stance": "市側・理事者（市長・局長等）の答弁姿勢・対応方針の要約（100〜150字）",
      "key_points": [
        "この時期に議員側から指摘された重要論点や課題1",
        "この時期に議員側から指摘された重要論点や課題2",
        "この時期に議員側から指摘された重要論点や課題3"
      ]
    }}
  ]
}}
"""
    for attempt in range(3):
        try:
            res = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json", temperature=0.2)
            )
            return json.loads(res.text)
        except Exception as e:
            print(f"  ⚠️ LLM呼び出しリトライ ({attempt+1}/3): {e}")
            time.sleep(2)
    return None

def main():
    print("=" * 65)
    print("🤖 大阪市会 8大分野重要政策 AI要約パイプライン")
    print("=" * 65)

    master_text = MASTER_PATH.read_text(encoding="utf-8")
    m = re.search(r"export const OSAKA_COUNCILOR_MASTER = ({.*?});", master_text, re.DOTALL)
    valid_councilors = set(json.loads(m.group(1)).keys()) if m else set()

    with open(STATEMENTS_PATH, "r", encoding="utf-8") as f:
        statements = json.load(f)

    active_stmts = [
        s for s in statements 
        if s.get("speaker") in valid_councilors or s.get("speaker", "").replace(" ", "") in valid_councilors
    ]
    print(f"現職アクティブスレッド: {len(active_stmts)} 件")

    final_topics = []

    for cfg in OSAKA_TOPIC_CONFIGS:
        kws = cfg["keywords"]
        cat = cfg["category"]
        title = cfg["title"]
        print(f"\n▶ 分析中: 【{cat}】 {title}")

        matched = []
        for s in active_stmts:
            s_cat = s.get("category", "")
            text = (s.get("summary", "") + " " + s.get("topic", "") + " " + s.get("meeting_title", "")).lower()
            if cat in s_cat and any(kw.lower() in text for kw in kws):
                matched.append(s)

        matched.sort(key=lambda x: x.get("meeting_date", ""))
        thread_count = len(matched)
        print(f"  - マッチした質疑スレッド: {thread_count} 件")

        phase_groups = {
            "2023年（令和5年）以前": [s for s in matched if s.get("meeting_date", "").startswith("2023")],
            "2024年（令和6年）": [s for s in matched if s.get("meeting_date", "").startswith("2024")],
            "2025年〜2026年（令和7・8年）": [s for s in matched if s.get("meeting_date", "") >= "2025"]
        }

        # LLMへの入力データ成形
        llm_periods_input = []
        for period_name, stmts in phase_groups.items():
            if not stmts:
                continue
            samples = [
                {
                    "date": s.get("meeting_date"),
                    "speaker": s.get("speaker"),
                    "meeting": s.get("meeting_title"),
                    "summary": s.get("summary")
                }
                for s in stmts[:6]  # 代表的な質疑を最大6件
            ]
            llm_periods_input.append({
                "period": period_name,
                "thread_count": len(stmts),
                "sample_statements": samples
            })

        print("  - Gemini 3.5 Flash で政策サマリー・対立軸・答弁スタンスを生成中...")
        ai_data = generate_ai_summary(title, cat, llm_periods_input)

        if not ai_data:
            print("  ❌ 要約生成に失敗したためスキップします。")
            continue

        # フェーズごとのやり取り（exchanges）を付与
        timeline_phases = []
        for p_info in ai_data.get("phases", []):
            p_name = p_info.get("period", "")
            p_stmts = phase_groups.get(p_name, [])
            exchanges = []
            for s in p_stmts[:3]:
                exchanges.append({
                    "meeting_date": s.get("meeting_date", ""),
                    "meeting_title": s.get("meeting_title", ""),
                    "speaker": s.get("speaker", ""),
                    "statement_summary": s.get("summary", ""),
                    "source_url": s.get("source_url", "")
                })

            timeline_phases.append({
                "period": p_name,
                "phase_title": p_info.get("phase_title", ""),
                "city_stance": p_info.get("city_stance", ""),
                "key_points": p_info.get("key_points", []),
                "exchanges": exchanges
            })

        topic_entry = {
            "topic_id": cfg["topic_id"],
            "category": cat,
            "title": title,
            "lead_summary": ai_data.get("lead_summary", ""),
            "current_status": ai_data.get("current_status", ""),
            "conflict_axes": ai_data.get("conflict_axes", []),
            "thread_count": thread_count if thread_count > 0 else 1,
            "last_updated": "2026-05-22",
            "timeline_phases": timeline_phases
        }
        final_topics.append(topic_entry)
        print("  ✅ 生成完了")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_topics, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 大阪版AI重要政策タイムライン（{len(final_topics)}件）の生成が完了しました！")
    print(f"出力先: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
