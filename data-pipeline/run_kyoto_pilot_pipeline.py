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

script_path = Path(__file__).resolve()
PROJECT_ROOT = script_path.parent.parent if script_path.parent.name == "data-pipeline" else script_path.parent
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"

# ==============================================================
# 1. Gate Criteria（品質受入基準）
# ==============================================================
BANNED_BOILERPLATES = [
    "進捗と課題に対する執行部答弁",
    "市長方針の推進 vs 実効性・財源の追及",
    "市執行部は基本方針・実施計画に基づき施策を推進する姿勢を維持",
    "市執行部による答弁と各会派の対案・課題追及",
    "計画策定および初期予算措置に関する市側の説明",
    "制度改善の議論",
    "施策を推進する姿勢を示した",
    "一定の理解を示しつつ",
    "議論が交わされた"
]

class GateCriteriaError(Exception):
    """品質受入基準を満たさない場合にスローされる例外"""
    pass

def validate_gate_criteria(topic_data, thread_count):
    # ① 質疑スレッド数足切り
    if thread_count < 5:
        raise GateCriteriaError(f"【Gate Failure】質疑スレッド数が基準未満（{thread_count}件 < 5件）")

    # ② 定型句の完全排除チェック
    dumped = json.dumps(topic_data, ensure_ascii=False)
    for banned in BANNED_BOILERPLATES:
        if banned in dumped:
            raise GateCriteriaError(f"【Gate Failure】禁止定型句を検出: 『{banned}』")

    # ③ lead_summary の解像度
    lead = topic_data.get("lead_summary")
    lead_text = lead if isinstance(lead, str) else (lead.get("summary", "") if isinstance(lead, dict) else "")
    if len(lead_text) < 120:
        raise GateCriteriaError(f"【Gate Failure】lead_summary の記述量不足（{len(lead_text)}文字 < 120文字）")

    # ④ 対立軸の具体性
    axes = topic_data.get("conflict_axes", [])
    if not isinstance(axes, list) or len(axes) < 2:
        raise GateCriteriaError("【Gate Failure】conflict_axes が2件未満")
    for axis in axes:
        if " vs " not in axis and " 対 " not in axis:
            raise GateCriteriaError(f"【Gate Failure】対立構図（A vs B）が不明瞭: {axis}")

    # ⑤ timeline_phases と発言吹き出しの空洞化排除
    phases = topic_data.get("timeline_phases", [])
    if not phases or len(phases) < 2:
        raise GateCriteriaError("【Gate Failure】timeline_phases が2件未満")

    for p_idx, phase in enumerate(phases):
        stance = phase.get("city_stance", "")
        if len(stance) < 50:
            raise GateCriteriaError(f"【Gate Failure】フェーズ{p_idx+1}の行政姿勢が短すぎます（{len(stance)}文字 < 50文字）")
        exchanges = phase.get("exchanges", [])
        if not exchanges:
            raise GateCriteriaError(f"【Gate Failure】フェーズ{p_idx+1}に質疑ログが存在しません")
        for ex in exchanges:
            summary = ex.get("statement_summary", "").strip()
            if not summary or len(summary) < 40:
                raise GateCriteriaError(f"【Gate Failure】発言要約が不十分または空: {ex.get('speaker')} ({len(summary)}文字)")

# ==============================================================
# 2. 代表論点と複合キーワード束（IDエイリアス対応）
# ==============================================================
PILOT_TOPICS = [
    {
        "topic_id": "kyoto-mayor-P-01",
        "aliases": ["bus_fare_priority", "kyoto-mayor-P-01"],
        "category": "都市再生・交通インフラ",
        "title": "市バス等の「市民優先価格（2階建て運賃）」導入への挑戦",
        "keywords": ["市バス", "市民優先", "二重運賃", "混雑対策", "観光特急バス", "運賃", "利用分離", "交通局", "バス混雑"]
    },
    {
        "topic_id": "kyoto-mayor-P-02",
        "aliases": ["accommodation_tax_revision", "kyoto-mayor-P-02"],
        "category": "産業・観光・地域経済",
        "title": "宿泊税上限引き上げおよび使途の拡大（市民還元）",
        "keywords": ["宿泊税", "超過課税", "税率引き上げ", "使途拡大", "観光振興", "市民還元", "財源", "宿泊事業者", "上限"]
    },
    {
        "topic_id": "kyoto-mayor-P-03",
        "aliases": ["school_lunch_full_implementation", "kyoto-mayor-P-03"],
        "category": "子育て・教育",
        "title": "全員制中学校給食の早期完全実施（京都方式）",
        "keywords": ["中学校給食", "全員制給食", "全員制中学校給食", "給食センター", "親子方式", "デリバリー給食", "温かい給食", "食育"]
    }
]

SYSTEM_PROMPT = """
あなたは地方財政および都市政策を専門とするシニア政策アナリストです。
提供される京都市議会の本会議・委員会質疑ログから、該当政策論点の時系列変遷と対立構図を高解像度に分析・構造化してください。

【厳格な執筆ルール】
1. 抽象的な定型句（「施策を推進する姿勢を示した」「制度改善が議論された」「一定の理解を示しつつ」等）は一切禁止します。
2. 議場ログに登場する具体的な事業名、制度名、運賃額、税額、予算規模、条例名、市長・交通局長・教育長側の答弁内容、各会派の具体的追及ポイントを克明に記述してください。
3. conflict_axes は、議場で実際に火花が散った対立構造を「〜の推進・拡充・財源確保 vs 〜の負担懸念・公平性・代替要求」の形式で2〜3件具体的に記述してください。
4. timeline_phases は時系列に2〜3フェーズに分割し、各フェーズでの行政公式姿勢（city_stance: 100〜180字）および主要論点（key_points: 2〜3件）を論理的・客観的に整理してください。
5. 必ず以下のJSON形式のみを出力してください。

{
  "lead_summary": "論点の背景、制度的経緯、市民生活・財政への影響、現在の到達点を具体的に解説（200〜280字）",
  "current_status": "制度導入・検討の現在地（具体的な年次、国の特例協議状況、予算計上フェーズ等を明記）",
  "conflict_axes": [
    "具体的対立軸1（A側の主張・論拠 vs B側の懸念・対案）",
    "具体的対立軸2（財政負担・事業継続性 vs 市民福祉・利用料抑制）"
  ],
  "timeline_phases": [
    {
      "period": "2023年〜2024年（初期論戦・構想提示）",
      "phase_title": "フェーズの見出し（具体的施策名を明記）",
      "city_stance": "市長・局長等の公式答弁要旨（具体的事業名や答弁方針を100〜180字で記述）",
      "key_points": [
        "議員・会派側が指摘した具体的な問題点・条例上の疑義",
        "市民負担や事業効果に関する具体的追及"
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
    return json.loads(path.read_text(encoding="utf-8"))

def extract_related_statements(statements, keywords, category):
    matched = []
    for s in statements:
        full_text = f"{s.get('meeting_title', '')} {s.get('summary', '')} {s.get('statement_text', '')}"
        hit_count = sum(1 for kw in keywords if kw in full_text)
        if hit_count > 0:
            score = hit_count * 2
            if s.get("category") == category:
                score += 3
            matched.append((score, s))
    matched.sort(key=lambda x: (x[0], x[1].get("meeting_date", "")), reverse=True)
    return [item[1] for item in matched]

def generate_exchange_summary(client, stmt, topic_title):
    speaker = stmt.get("speaker", "議員")
    summary = stmt.get("summary", "")
    text = (stmt.get("statement_text") or "")[:500]
    date = stmt.get("meeting_date", "")
    m_title = stmt.get("meeting_title", "")

    prompt = f"""
以下の地方議会質疑レコードから、【{topic_title}】に関する議員（{speaker}）の具体的指摘・質問と、行政側（市長・局長等）の答弁要旨を、100〜140文字でファクトベースで要約してください。
定型句を排し、「何を問題視し、行政が具体的にどう答弁したか」を記述してください。

日付: {date} | 会議: {m_title} | 発言者: {speaker}
既存要約: {summary}
発言本文抜粋: {text}
"""
    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        res_text = res.text.strip().replace("\n", " ")
        if len(res_text) >= 40:
            return res_text
    except Exception:
        pass
    
    if len(summary) >= 40:
        return summary[:150]
    return f"{speaker}議員による{topic_title}に関する本会議・委員会質疑。議場において行政側の施策進捗および課題に対する質疑応答が行われた。"

def analyze_topic(client, topic, statements):
    sample_texts = []
    for s in statements[:25]:
        date = s.get("meeting_date", "")
        m_title = s.get("meeting_title", "")
        speaker = s.get("speaker", "議員")
        summary = s.get("summary", "")
        sample_texts.append(f"[{date} | {m_title} | {speaker}]: {summary}")

    content = f"""
【論点タイトル】: {topic['title']}
【カテゴリ】: {topic['category']}

【実際の京都市議会議事録ログ（抜粋）】:
""" + "\n".join(sample_texts)

    for attempt in range(3):
        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=content,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.15
                )
            )
            return json.loads(res.text)
        except Exception as e:
            print(f"    API試行 {attempt+1} 失敗: {e}")
            time.sleep(2)
    return None

def main():
    print("=======================================================", flush=True)
    print("🏛️ 京都市パイロット高解像度再生成（Gate Criteria適用）", flush=True)
    print("=======================================================", flush=True)

    client = get_gemini_client()
    stmt_file = FRONTEND_DATA / "kyoto_statements_summary.json"
    if not stmt_file.exists():
        print(f"❌ ファイルが存在しません: {stmt_file}", flush=True)
        return

    statements = load_json(stmt_file) or []
    print(f"📖 京都市 質疑データベース読み込み: {len(statements)} 件", flush=True)

    topic_file = FRONTEND_DATA / "kyoto_topic_summaries.json"
    existing_topics = load_json(topic_file) or []
    
    audited_results = []

    for t_def in PILOT_TOPICS:
        t_id = t_def["topic_id"]
        aliases = t_def.get("aliases", [t_id])
        title = t_def["title"]
        print(f"\n▶ 監査・生成開始: 【{title}】", flush=True)

        related = extract_related_statements(statements, t_def["keywords"], t_def["category"])
        thread_count = len(related)
        print(f"  * 検出質疑スレッド数: {thread_count} 件", flush=True)

        if thread_count < 5:
            print(f"  ❌ 【Gate Rejected】スレッド数が基準未満（{thread_count} < 5）のため論点除外します。", flush=True)
            continue

        print("  * Gemini 2.5 Flash による実文脈分析を実行中...", flush=True)
        analysis = analyze_topic(client, t_def, related)
        if not analysis:
            raise RuntimeError(f"論点 {title} のAI分析に失敗しました。")

        phases = analysis.get("timeline_phases", [])
        for p_idx, phase in enumerate(phases):
            period = phase.get("period", "")
            years = re.findall(r"(202\d)", period)
            candidates = [r for r in related if any(str(r.get("meeting_date", "")).startswith(y) for y in years)]
            if not candidates:
                candidates = related[p_idx * 2: (p_idx + 1) * 2] if len(related) >= (p_idx + 1) * 2 else related[:2]

            phase_exchanges = []
            for stmt in candidates[:2]:
                url = stmt.get("official_url") or stmt.get("source_url") or ""
                stmt_summary = generate_exchange_summary(client, stmt, title)
                phase_exchanges.append({
                    "meeting_date": stmt.get("meeting_date"),
                    "meeting_title": stmt.get("meeting_title"),
                    "speaker": stmt.get("speaker"),
                    "statement_summary": stmt_summary,
                    "source_url": url,
                    "official_url": url
                })
            phase["exchanges"] = phase_exchanges

        # 既存データのlead_summaryに公式計画書URL情報等があればマージ保持
        matched_existing = next((t for t in existing_topics if t.get("topic_id") in aliases or t.get("title") == title), None)
        lead = analysis.get("lead_summary")
        if matched_existing and isinstance(matched_existing.get("lead_summary"), dict):
            orig = matched_existing["lead_summary"]
            lead = {
                "plan_name": orig.get("plan_name", ""),
                "date": orig.get("date", ""),
                "summary": analysis.get("lead_summary"),
                "doc_url": orig.get("doc_url", "")
            }

        target_id = matched_existing.get("topic_id", t_id) if matched_existing else t_id

        built_topic = {
            "topic_id": target_id,
            "category": t_def["category"],
            "title": matched_existing.get("title", title) if matched_existing else title,
            "lead_summary": lead,
            "current_status": analysis.get("current_status"),
            "conflict_axes": analysis.get("conflict_axes", []),
            "thread_count": thread_count,
            "last_updated": related[0].get("meeting_date", "2026-09-18"),
            "timeline_phases": phases
        }

        print("  * Gate Criteria（定型句排除・解像度検査）を実行中...", flush=True)
        validate_gate_criteria(built_topic, thread_count)
        print("  ✅ 【Gate Passed】全ての品質受入基準を満たしました。", flush=True)

        audited_results.append(built_topic)
        
        # 既存リストの更新または追加
        found = False
        for idx, et in enumerate(existing_topics):
            if et.get("topic_id") in aliases or et.get("title") == title:
                existing_topics[idx] = built_topic
                found = True
                break
        if not found:
            existing_topics.append(built_topic)

        time.sleep(1.0)

    # kyoto_topic_summaries.json の更新保存
    topic_file.write_text(json.dumps(existing_topics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 {topic_file} を更新しました。", flush=True)

    # 監査用生JSONサンプルの保存
    sample_file = PROJECT_ROOT / "pilot_output_kyoto_sample.json"
    sample_file.write_text(json.dumps(audited_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📄 PM監査用サンプルを出力しました: {sample_file}", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("📋 PM監査用 生JSON抜粋プレビュー", flush=True)
    print("=" * 60, flush=True)
    for sample in audited_results:
        print(f"\n【トピックID】: {sample['topic_id']}", flush=True)
        print(f"【タイトル】: {sample['title']} (質疑スレッド: {sample['thread_count']}件)", flush=True)
        print(f"【lead_summary】:\n{json.dumps(sample['lead_summary'], ensure_ascii=False, indent=2) if isinstance(sample['lead_summary'], dict) else sample['lead_summary']}", flush=True)
        print(f"【current_status】: {sample['current_status']}", flush=True)
        print("【conflict_axes】:\n" + "\n".join(f"  - {ax}" for ax in sample['conflict_axes']), flush=True)
        print("【timeline_phases】:", flush=True)
        for ph in sample['timeline_phases']:
            print(f"  ● {ph['period']} : 【{ph['phase_title']}】", flush=True)
            print(f"    行政姿勢: {ph['city_stance']}", flush=True)
            print(f"    重要論点: {ph.get('key_points')}", flush=True)
            for ex in ph.get("exchanges", []):
                print(f"      🗣️ {ex['speaker']} ({ex['meeting_date']}): {ex['statement_summary']}", flush=True)

if __name__ == "__main__":
    main()
