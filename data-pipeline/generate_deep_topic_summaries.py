import os
import sys
import json
import re
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
load_dotenv("data-pipeline/.env")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"

SYSTEM_PROMPT = """
あなたは地方議会・自治体政策の専門アナリストです。
提供される市議会の複数年度にわたる質疑・答弁データから、該当論点の「Policy Timeline（政策展開の時系列変遷）」を高解像度に構造化してください。

【厳格な執筆ルール】
1. 抽象的・定型的な文章（例:「市執行部は施策を推進する姿勢を示した」「制度改善が議論された」等）は一切禁止します。
2. 必ず議場ログに登場する具体的な事業名、制度名、予算額、数値、市長・局長側の公式答弁内容、対立理由を克明に記述してください。
3. conflict_axes は、議場で実際に激論となった対立構造を「〜の推進・拡充 vs 〜の懸念・財源負担・代替案」の形式で2〜3件具体的に記述してください。
4. timeline_phases は時系列に2〜3フェーズに分割し、各フェーズの「行政姿勢（city_stance）」および「論点・着眼点（key_points）」をそれぞれ100〜180文字で論理的に記述してください。
5. 必ず以下のJSONフォーマットのみを出力してください。

{
  "lead_summary": "論点の背景、制度的経緯、市民生活への影響、現在の着地点を具体的に解説（200〜260文字）",
  "current_status": "制度導入・検討の現在地（例: 令和8年度予算案に調査費計上、国交省との特例協議が進行中）",
  "conflict_axes": [
    "具体的対立軸1（A側の主張・論拠 vs B側の懸念・対案）",
    "具体的対立軸2（財政負担・事業継続性 vs 市民福祉・利用料抑制）"
  ],
  "timeline_phases": [
    {
      "period": "2023年〜2024年（初期検討・課題の顕在化）",
      "phase_title": "制度構想の提示と初期の財政・運用論争",
      "city_stance": "市執行部（市長・担当局）が議場で表明した具体的な方針、予算化の根拠、答弁内容（120〜180文字）",
      "key_points": [
        "議員・会派側が指摘した具体的な問題点や条例上の疑義",
        "市民負担や事業効果に関する追及ポイント"
      ]
    }
  ]
}
"""

def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません。")
    return genai.Client(api_key=api_key)

def load_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def match_statements_for_topic(statements, topic, max_count=30):
    title = topic.get("title", "")
    t_id = topic.get("topic_id", "")
    category = topic.get("category", "")
    
    # キーワード候補の抽出
    keywords = [w for w in re.split(r"[（）()、・\s/「」]", title) if len(w) >= 2]
    
    matched = []
    for s in statements:
        s_cat = s.get("category", "")
        summary = s.get("summary", "")
        text = s.get("statement_text", "")
        m_title = s.get("meeting_title", "")
        full_text = f"{m_title} {summary} {text}"
        
        hit_count = sum(1 for kw in keywords if kw in full_text)
        if hit_count > 0:
            score = hit_count * 2
            if s_cat == category:
                score += 3
            matched.append((score, s))
            
    matched.sort(key=lambda x: (x[0], x[1].get("meeting_date", "")), reverse=True)
    return [item[1] for item in matched[:max_count]]

def summarize_exchange_statement(client, statement, topic_title):
    speaker = statement.get("speaker", "議員")
    summary = statement.get("summary", "")
    text = (statement.get("statement_text") or "")[:500]
    date = statement.get("meeting_date", "")
    m_title = statement.get("meeting_title", "")
    
    if len(summary) >= 60 and not any(p in summary for p in ["提案理由説明が行われ", "進行が行われ"]):
        return summary[:160]

    prompt = f"""
以下の地方議会質疑レコードから、【{topic_title}】に関する議員（{speaker}）の指摘・質問と、それに対する行政側の答弁骨子を、110〜140文字で明瞭・客観的に要約してください。
主観や定型句を排し、何が問われ、行政がどう答えたかを明確にしてください。

日付: {date}
会議: {m_title}
発言者: {speaker}
既存要約: {summary}
発言本文: {text}
"""
    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        return res.text.strip().replace("\n", " ")
    except Exception:
        return summary[:150] if summary else f"{speaker}議員による{topic_title}に関する本会議・委員会質疑。"

def analyze_topic_with_gemini(client, topic, matched_statements):
    sample_texts = []
    for s in matched_statements[:20]:
        date = s.get("meeting_date", "")
        m_title = s.get("meeting_title", "")
        speaker = s.get("speaker", "議員")
        summary = s.get("summary", "")
        sample_texts.append(f"[{date} | {m_title} | {speaker}]: {summary}")

    content = f"""
【論点タイトル】: {topic.get('title')}
【カテゴリ】: {topic.get('category')}
【現在の暫定説明】: {topic.get('lead_summary') if isinstance(topic.get('lead_summary'), str) else ''}

【実際の議会質疑・審議ログ（抜粋）】:
""" + "\n".join(sample_texts)

    for attempt in range(3):
        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=content,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            return json.loads(res.text)
        except Exception as e:
            time.sleep(2 * (attempt + 1))
    return None

def process_city_topics(city, client, limit_topics=None):
    print(f"\n=======================================================")
    print(f"🏛️ 都市処理開始: {city.upper()}")
    print(f"=======================================================")
    
    topic_file = FRONTEND_DATA / f"{city}_topic_summaries.json"
    stmt_file = FRONTEND_DATA / f"{city}_statements_summary.json"
    
    topics = load_json(topic_file) or []
    statements = load_json(stmt_file) or []
    
    print(f"  論点数: {len(topics)} 件 / 質疑ログ数: {len(statements)} 件")
    if not topics or not statements:
        print("  ❌ 必要なデータファイルが存在しません。スキップします。")
        return

    updated_topics = []
    count = 0

    for idx, t in enumerate(topics, start=1):
        if limit_topics and count >= limit_topics:
            updated_topics.append(t)
            continue

        t_id = t.get("topic_id")
        title = t.get("title")
        print(f"\n[{idx}/{len(topics)}] 解析対象: 【{title}】 (ID: {t_id})")

        # 質疑データのマッチング
        matched = match_statements_for_topic(statements, t, max_count=25)
        print(f"    ➔ 該当質疑スレッド: {len(matched)} 件")

        if not matched:
            print("    ⚠️ マッチする発言がないため現状維持します。")
            updated_topics.append(t)
            continue

        # Gemini でリッチな論点分析を実行
        print("    ✨ Gemini 2.5 Flash による政策アナリスト分析を実行中...")
        analysis = analyze_topic_with_gemini(client, t, matched)
        if not analysis:
            print("    ❌ AI解析に失敗しました。")
            updated_topics.append(t)
            continue

        # フェーズごとの質疑スレッド紐付け & 要約生成
        phases = analysis.get("timeline_phases", [])
        for p_idx, phase in enumerate(phases):
            period = phase.get("period", "")
            # 年のマッチング
            years = re.findall(r"(202\d)", period)
            phase_candidates = [m for m in matched if any(str(m.get("meeting_date", "")).startswith(y) for y in years)]
            if not phase_candidates:
                phase_candidates = matched[p_idx * 2: (p_idx + 1) * 2] if len(matched) >= (p_idx + 1) * 2 else matched[:2]

            phase_exchanges = []
            for stmt in phase_candidates[:2]:
                url = stmt.get("official_url") or stmt.get("source_url") or ""
                stmt_sum = summarize_exchange_statement(client, stmt, title)
                phase_exchanges.append({
                    "meeting_date": stmt.get("meeting_date"),
                    "meeting_title": stmt.get("meeting_title"),
                    "speaker": stmt.get("speaker"),
                    "statement_summary": stmt_sum,
                    "source_url": url,
                    "official_url": url
                })
            phase["exchanges"] = phase_exchanges

        # 構造の統合（lead_summary が既存で辞書・URL情報を持っている場合は維持・融合）
        lead = analysis.get("lead_summary")
        if isinstance(t.get("lead_summary"), dict):
            orig_lead = t.get("lead_summary")
            lead = {
                "plan_name": orig_lead.get("plan_name", ""),
                "date": orig_lead.get("date", ""),
                "summary": analysis.get("lead_summary"),
                "doc_url": orig_lead.get("doc_url", "")
            }

        new_topic = {
            **t,
            "lead_summary": lead,
            "current_status": analysis.get("current_status"),
            "conflict_axes": analysis.get("conflict_axes", []),
            "thread_count": len(matched),
            "last_updated": matched[0].get("meeting_date", t.get("last_updated")),
            "timeline_phases": phases
        }
        updated_topics.append(new_topic)
        count += 1
        print("    ✅ リッチ分析データを統合完了")
        time.sleep(1.0)

    # 保存
    save_json(topic_file, updated_topics)
    print(f"\n🎉 {city.upper()} の論点マスターを更新しました: {topic_file}")

def main():
    client = get_gemini_client()
    target_city = sys.argv[1] if len(sys.argv) > 1 else "kyoto"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None

    if target_city == "all":
        for c in ["kyoto", "osaka", "nagoya", "yokohama", "kobe"]:
            process_city_topics(c, client, limit_topics=limit)
    else:
        process_city_topics(target_city, client, limit_topics=limit)

if __name__ == "__main__":
    main()
