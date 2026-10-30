import socket

# --- 1. IPv4 強制パッチ (Windows IPv6 タイムアウト回避) ---
orig_getaddrinfo = socket.getaddrinfo
def ipv4_only_getaddrinfo(*args, **kwargs):
    responses = orig_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]
socket.getaddrinfo = ipv4_only_getaddrinfo
# --------------------------------------------------------

import os
import sys
import json
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
load_dotenv("data-pipeline/.env")

script_path = Path(__file__).resolve()
PROJECT_ROOT = script_path.parent.parent if script_path.parent.name == "data-pipeline" else script_path.parent
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"

file_lock = Lock()

# ==============================================================
# 2. Gate Criteria & 安全装置
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
    pass

def validate_topic_gate(topic_data, thread_count):
    if thread_count < 5:
        raise GateCriteriaError(f"質疑スレッド数が基準未満（{thread_count}件 < 5件）")

    dumped = json.dumps(topic_data, ensure_ascii=False)
    for banned in BANNED_BOILERPLATES:
        if banned in dumped:
            raise GateCriteriaError(f"禁止定型句を検出: 『{banned}』")

    lead = topic_data.get("lead_summary")
    lead_text = lead if isinstance(lead, str) else (lead.get("summary", "") if isinstance(lead, dict) else "")
    if len(lead_text) < 100:
        raise GateCriteriaError(f"lead_summary の記述量不足（{len(lead_text)}文字）")

    axes = topic_data.get("conflict_axes", [])
    if not isinstance(axes, list) or len(axes) < 2:
        raise GateCriteriaError("conflict_axes が2件未満")
    for axis in axes:
        if " vs " not in axis and " 対 " not in axis:
            raise GateCriteriaError(f"対立構図（A vs B）が不明瞭: {axis}")

    phases = topic_data.get("timeline_phases", [])
    if not phases or len(phases) < 2:
        raise GateCriteriaError("timeline_phases が2件未満")

    for p_idx, phase in enumerate(phases):
        stance = phase.get("city_stance", "")
        if len(stance) < 40:
            raise GateCriteriaError(f"フェーズ{p_idx+1}の行政姿勢が短すぎます（{len(stance)}文字）")
        exchanges = phase.get("exchanges", [])
        if not exchanges:
            raise GateCriteriaError(f"フェーズ{p_idx+1}に質疑ログがありません")
        for ex in exchanges:
            summary = ex.get("statement_summary", "").strip()
            if not summary or len(summary) < 30:
                raise GateCriteriaError(f"発言要約が不十分: {ex.get('speaker')} ({len(summary)}文字)")

SYSTEM_PROMPT = """
あなたは地方財政および都市政策を専門とするシニア政策アナリストです。
提供される市議会の本会議・委員会質疑ログから、該当政策論点の時系列変遷と対立構図を高解像度に分析・構造化してください。

【厳格な執筆ルール】
1. 抽象的な定型句（「施策を推進する姿勢を示した」「制度改善が議論された」等）は一切禁止します。
2. 議場ログに登場する具体的な事業名、制度名、金額、税率、予算規模、条例名、市長・局長等の答弁内容、各会派の具体的追及ポイントを克明に記述してください。
3. conflict_axes は、議場で実際に火花が散った対立構造を「〜の推進・拡充・財源確保 vs 〜の負担懸念・公平性・代替要求」の形式で2〜3件具体的に記述してください。
4. timeline_phases は時系列に2〜3フェーズに分割し、各フェーズでの行政公式姿勢（city_stance: 100〜180字）および主要論点（key_points: 2〜3件）を論理的・客観的に整理してください。
5. 必ず以下のJSON形式のみを出力してください。

{
  "lead_summary": "論点の背景、制度的経緯、市民生活・財政への影響、現在の到達点を具体的に解説（180〜280字）",
  "current_status": "制度導入・検討の現在地（具体的な年次、国の協議状況、予算計上フェーズ等を明記）",
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
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def extract_related_statements(statements, topic):
    title = topic.get("title", "")
    category = topic.get("category", "")
    t_id = topic.get("topic_id", "")
    
    kw_raw = re.split(r"[（）()、・\s/「」【】]", title)
    keywords = [w for w in kw_raw if len(w) >= 2 and w not in ["導入", "推進", "検討", "計画", "事業", "対策", "改革", "挑戦", "確保"]]
    
    extra_kws = {
        "bus": ["市バス", "運賃", "混雑", "優先価格", "2階建て運賃", "交通局"],
        "tax": ["宿泊税", "超過課税", "税率", "市民還元"],
        "lunch": ["中学校給食", "全員制給食", "給食センター", "食育"],
        "medical": ["医療費", "子ども医療", "小児", "助成", "通院"],
        "child": ["保育料", "第2子", "無償化", "子育て", "待機児童"],
        "metro": ["民営化", "地下鉄", "運賃", "メトロ"],
        "expo": ["万博", "IR", "夢洲", "跡地利用", "交通アクセス"],
        "castle": ["天守閣", "木造復元", "名古屋城", "現状変更"],
        "redevelopment": ["再開発", "駅前", "区画整理", "タワー", "まちづくり"],
        "disaster": ["防災", "耐震", "避難所", "浸水", "ハザードマップ"]
    }
    for k, v in extra_kws.items():
        if k in t_id.lower() or any(kw in title for kw in v):
            keywords.extend(v)
    keywords = list(set(keywords))

    matched = []
    for s in statements:
        full_text = f"{s.get('meeting_title', '')} {s.get('summary', '')} {s.get('statement_text', '')}"
        hit_count = sum(1 for kw in keywords if kw in full_text)
        if hit_count > 0:
            score = hit_count * 2
            if s.get("category") == category:
                score += 4
            matched.append((score, s))

    matched.sort(key=lambda x: (x[0], x[1].get("meeting_date", "")), reverse=True)
    return [item[1] for item in matched]

def select_best_exchanges_for_phase(candidates, phase_title, key_points, max_count=2):
    phase_text = f"{phase_title} " + " ".join(key_points)
    scored = []
    for s in candidates:
        s_text = f"{s.get('summary', '')} {s.get('statement_text', '')}"
        overlap = sum(1 for w in re.split(r"[\s、。]", phase_text) if len(w) >= 2 and w in s_text)
        scored.append((overlap, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:max_count]]

def clean_or_summarize_exchange(client, stmt, topic_title, phase_context=""):
    speaker = stmt.get("speaker", "議員")
    summary = (stmt.get("summary") or "").strip()
    
    if len(summary) >= 45 and not any(p in summary for p in ["進行が行われ", "日程に入り", "開会した"]):
        return summary[:160]

    text = (stmt.get("statement_text") or "")[:400]
    date = stmt.get("meeting_date", "")
    m_title = stmt.get("meeting_title", "")
    prompt = f"""
地方議会質疑を100〜140字で要約せよ。【{topic_title}】（{phase_context}）
発言者: {speaker} | 日付: {date} | 会議: {m_title}
発言抜粋: {text}
"""
    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        t = res.text.strip().replace("\n", " ")
        if len(t) >= 35:
            return t
    except Exception:
        pass
    return summary[:150] if summary else f"{speaker}議員による{topic_title}に関する質疑。"

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

【実際の議会議事録ログ（抜粋）】:
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
            time.sleep(1.0 * (attempt + 1))
    return None

def process_single_topic(topic, statements, client, topic_file, idx, total):
    t_id = topic.get("topic_id", "")
    title = topic.get("title", "")
    
    related = extract_related_statements(statements, topic)
    thread_count = len(related)
    
    if thread_count < 5:
        print(f"  [{idx}/{total}] ❌ 足切り除外: 【{title}】 (質疑数 {thread_count} < 5件)", flush=True)
        return {"status": "dropped", "topic_id": t_id, "title": title, "count": thread_count}

    print(f"  [{idx}/{total}] ▶ 分析開始: 【{title}】 (該当スレッド {thread_count}件)...", flush=True)

    analysis = analyze_topic(client, topic, related)
    if not analysis:
        print(f"  [{idx}/{total}] ⚠️ AI分析失敗: 【{title}】", flush=True)
        return {"status": "failed", "topic_id": t_id, "title": title}

    phases = analysis.get("timeline_phases", [])
    for p_idx, phase in enumerate(phases):
        period = phase.get("period", "")
        years = re.findall(r"(202\d)", period)
        year_matched = [r for r in related if any(str(r.get("meeting_date", "")).startswith(y) for y in years)]
        cand_pool = year_matched if len(year_matched) >= 2 else related

        best_exs = select_best_exchanges_for_phase(
            cand_pool, 
            phase.get("phase_title", ""), 
            phase.get("key_points", []),
            max_count=2
        )

        phase_exchanges = []
        for stmt in best_exs:
            url = stmt.get("official_url") or stmt.get("source_url") or ""
            s_sum = clean_or_summarize_exchange(client, stmt, title, phase.get("phase_title", ""))
            phase_exchanges.append({
                "meeting_date": stmt.get("meeting_date"),
                "meeting_title": stmt.get("meeting_title"),
                "speaker": stmt.get("speaker"),
                "statement_summary": s_sum,
                "source_url": url,
                "official_url": url
            })
        phase["exchanges"] = phase_exchanges

    lead = analysis.get("lead_summary")
    if isinstance(topic.get("lead_summary"), dict):
        orig = topic["lead_summary"]
        lead = {
            "plan_name": orig.get("plan_name", ""),
            "date": orig.get("date", ""),
            "summary": analysis.get("lead_summary") if isinstance(analysis.get("lead_summary"), str) else orig.get("summary", ""),
            "doc_url": orig.get("doc_url", "")
        }

    built_topic = {
        "topic_id": t_id,
        "category": topic.get("category"),
        "title": title,
        "lead_summary": lead,
        "current_status": analysis.get("current_status"),
        "conflict_axes": analysis.get("conflict_axes", []),
        "thread_count": thread_count,
        "last_updated": related[0].get("meeting_date", "2026-09-18"),
        "timeline_phases": phases
    }

    validate_topic_gate(built_topic, thread_count)

    with file_lock:
        current_data = load_json(topic_file) or []
        updated = False
        for i, item in enumerate(current_data):
            if item.get("topic_id") == t_id or item.get("title") == title:
                current_data[i] = built_topic
                updated = True
                break
        if not updated:
            current_data.append(built_topic)
        topic_file.write_text(json.dumps(current_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  [{idx}/{total}] ✅ Gate Passed 完了: 【{title}】", flush=True)
    return {"status": "success", "topic_id": t_id, "title": title, "count": thread_count, "built": built_topic}

def process_city_parallel(city, client, max_workers=3):
    print(f"\n=======================================================", flush=True)
    print(f"🏛️ 都市処理開始: {city.upper()} (並列ワーカー数: {max_workers})", flush=True)
    print(f"=======================================================", flush=True)

    topic_file = FRONTEND_DATA / f"{city}_topic_summaries.json"
    stmt_file = FRONTEND_DATA / f"{city}_statements_summary.json"

    raw_topics = load_json(topic_file) or []
    statements = load_json(stmt_file) or []

    print(f"📖 既存論点マスター: {len(raw_topics)} 件 / 質疑ログ: {len(statements)} 件", flush=True)

    valid_topics = []
    dropped_count = 0
    t_start = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_topic, t, statements, client, topic_file, idx, len(raw_topics)): t
            for idx, t in enumerate(raw_topics, start=1)
        }

        for future in as_completed(futures):
            t_orig = futures[future]
            try:
                res = future.result()
                if res["status"] == "success":
                    valid_topics.append(res["built"])
                elif res["status"] == "dropped":
                    dropped_count += 1
            except Exception as e:
                print(f"  ⚠️ エラー例外: 【{t_orig.get('title')}】 {e}", flush=True)

    final_list = [t for t in (load_json(topic_file) or []) if any(vt["topic_id"] == t.get("topic_id") for vt in valid_topics)]
    topic_file.write_text(json.dumps(final_list, ensure_ascii=False, indent=2), encoding="utf-8")

    elapsed = time.time() - t_start
    print(f"\n🎉 {city.upper()} 完了: 有効 {len(final_list)}件 / 除外 {dropped_count}件 ({elapsed:.1f}秒)", flush=True)

    return {
        "city": city,
        "valid_count": len(final_list),
        "dropped_count": dropped_count,
        "elapsed_sec": round(elapsed, 1),
        "sample": final_list[0] if final_list else None
    }

def main():
    client = get_gemini_client()
    target_city = sys.argv[1] if len(sys.argv) > 1 else "all"
    cities = ["kyoto", "osaka", "nagoya", "yokohama", "kobe"] if target_city == "all" else [target_city]

    metrics_summary = []
    print("🚀 高速並列 政策論点パイプライン起動 (IPv4強制最適化済)", flush=True)
    t_all_start = time.time()

    for c in cities:
        res = process_city_parallel(c, client, max_workers=3)
        metrics_summary.append(res)

    total_time = round(time.time() - t_all_start, 1)
    print("\n" + "=" * 65, flush=True)
    print(f"📊 全都市生成完了メトリクスレポート (総所要時間: {total_time}秒)", flush=True)
    print("=" * 65, flush=True)
    for m in metrics_summary:
        print(f"都市: {m['city'].upper():<8} | 採用論点数: {m['valid_count']:<2} | 除外施策数: {m['dropped_count']:<2} | 所要時間: {m['elapsed_sec']}秒")

    report_file = PROJECT_ROOT / "pipeline_generation_metrics.json"
    report_file.write_text(json.dumps(metrics_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📄 メトリクス詳細保存: {report_file}", flush=True)

if __name__ == "__main__":
    main()
