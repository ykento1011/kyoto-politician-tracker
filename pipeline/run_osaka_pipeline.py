import json, os, sys, time, threading, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai
from google.cloud import bigquery
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / "data-pipeline" / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY が設定されていません。")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3.5-flash-lite")

MAX_WORKERS = 4
cache_lock = threading.Lock()

OFFICIAL_ROLES = [
    "市長", "副市長", "局長", "区長", "部長", "室長", "課長", "次長", 
    "理事者", "教育長", "技監", "参事", "主査", "担当部長", "担当課長", "副首都"
]

PROCEDURAL_PATTERNS = [
    r"君登壇\）$",
    r"御異議なしと認め",
    r"お諮りいたします",
    r"動議に御異議",
    r"動議を提出いたします",
    r"(説明|見解表明|報告)は以上であります",
    r"理事者の(説明|答弁)を(求め|許し)ます",
    r"これより(議事に入り|委員会を再開|採決に入り)",
    r"審査の報告は終了",
    r"本日の日程は以上で終了",
    r"暫時休憩",
    r"協議会を(開き|閉じ)",
    r"撮影の?(申出|申し出|許可)",
    r"開会に先立ち",
    r"原案のとおり可決"
]
PROCEDURAL_REGEX = re.compile("|".join(PROCEDURAL_PATTERNS))

def is_official(speaker):
    return any(role in speaker for role in OFFICIAL_ROLES)

def is_procedural(text):
    text_clean = text.replace("\n", " ").strip()
    if len(text_clean) < 120 and PROCEDURAL_REGEX.search(text_clean):
        return True
    return False

def fetch_osaka_all_data(client):
    print("📥 BigQueryから大阪市の本会議・全委員会データを抽出中 (2023-05-01以降)...")
    q_meetings = """
        SELECT m.id AS meeting_id, m.name AS meeting_name, m.date AS meeting_date
        FROM `gen-lang-client-0253904061.sagebase_data.meetings` m
        JOIN `gen-lang-client-0253904061.sagebase_data.conferences` conf ON m.conference_id = conf.id
        WHERE conf.governing_body_id = 532 
          AND (m.name LIKE '%委員会%' OR m.name LIKE '%定例会%' OR m.name LIKE '%本会議%')
          AND m.name NOT LIKE '%市会運営%'
          AND m.name NOT LIKE '%資料編%'
          AND m.name NOT LIKE '%別冊%'
          AND m.date >= '2023-05-01'
        ORDER BY m.date DESC
    """
    meetings = list(client.query(q_meetings).result())
    print(f"🎯 対象会議数: {len(meetings)} 件")

    all_statements = []
    for mtg in meetings:
        q_stmts = f"""
            SELECT c.sequence_number, c.speaker_name AS speaker, c.comment AS statement_text,
                   '{mtg.meeting_id}' AS meeting_id, '{mtg.meeting_name}' AS meeting_title, '{mtg.meeting_date}' AS meeting_date
            FROM `gen-lang-client-0253904061.sagebase_data.conversations` c
            JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON c.minutes_id = min.id
            WHERE min.meeting_id = {mtg.meeting_id}
            ORDER BY c.sequence_number ASC
        """
        all_statements.extend([dict(r) for r in client.query(q_stmts).result()])

    print(f"✅ 合計 {len(all_statements):,} 件の発言を取得しました。")
    return all_statements

def build_osaka_threads(stmts):
    meetings = {}
    for s in stmts:
        mid = s["meeting_id"]
        if mid not in meetings:
            meetings[mid] = []
        meetings[mid].append(s)

    threads = []
    for mid, m_stmts in meetings.items():
        m_stmts = sorted(m_stmts, key=lambda x: x.get("sequence_number", 0))
        chair_name = m_stmts[0]["speaker"] if m_stmts else ""
        current_thread = None

        for s in m_stmts:
            spk = (s.get("speaker") or "").strip()
            text = (s.get("statement_text") or "").strip()

            if not spk or not text:
                continue
            if spk == chair_name or "委員長" in spk or "議長" in spk or "副議長" in spk:
                continue
            if is_procedural(text):
                continue
            if "陳情書" in text and "見解を申し上げます" in text:
                continue
            if "案件につきまして御説明申し上げます" in text:
                continue

            if is_official(spk) or text.startswith(("お答えいたします", "お答えします")):
                if current_thread is not None:
                    current_thread["context_log"].append(f"【行政側 ({spk})】\n{text}")
                    current_thread["has_response"] = True
            else:
                if current_thread is None or current_thread["speaker"] != spk:
                    if current_thread is not None and current_thread["has_response"] and len(current_thread["question_text"]) > 40:
                        threads.append(current_thread)
                    current_thread = {
                        "thread_id": f"th_{mid}_{s['sequence_number']}",
                        "speaker": spk,
                        "meeting_id": mid,
                        "meeting_title": s["meeting_title"],
                        "meeting_date": str(s["meeting_date"]),
                        "question_text": text,
                        "context_log": [f"【議員 ({spk})】\n{text}"],
                        "has_response": False
                    }
                else:
                    current_thread["context_log"].append(f"【議員・再質問 ({spk})】\n{text}")

        if current_thread is not None and current_thread["has_response"] and len(current_thread["question_text"]) > 40:
            threads.append(current_thread)

    return threads

def evaluate_thread(thread):
    convo = "\n\n".join(thread["context_log"])
    if len(convo) > 8000:
        convo = convo[:4000] + "\n\n...[中略]...\n\n" + convo[-4000:]

    prompt = f"""
あなたは地方議会の政策質疑データを構造化・整理するCivic Tech分析AIです。
以下の質疑スレッドを4つの分析軸（各0〜5点）で整理し、客観的事実のみをJSON形式で出力してください。

【厳格な禁止事項】
・評価語（「前向き」「鋭い」「至らなかった」等）は一切使用しないこと。
・reasoningには事実関係（何を参照し、何を尋ね、どう答えたか）のみを記述すること。

【4軸の分析基準】
1. evidence (0-5: 根拠・データ): 客観的データ、過去実績、他都市事例等の提示度合い。
2. solution (0-5: 対案・是正策): 具体的な改善策、制度設計の提案度合い。
3. local_focus (0-5: 地域解像度): 特定の地域、施設、現場の具体名の提示度合い。
4. constructive (0-5: 質疑の展開): 答弁を踏まえた掘り下げ、論点絞り込みの度合い。

【質疑スレッド】
{convo}

出力スキーマ:
{{
  "category": "子育て・教育, 都市再生・交通インフラ, 産業・観光・地域経済, 福祉・医療・健康, 財政・行革, くらし・環境・エネルギー, 防災・減災・治安, 文化・景観・歴史 から1つ",
  "summary": "要旨（80〜100文字程度）",
  "keywords": ["キーワード1", "キーワード2"],
  "scores": {{"evidence": 0, "solution": 0, "local_focus": 0, "constructive": 0}},
  "reasoning": "事実ベースの分析メモ"
}}
"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json", temperature=0.0)
            )
            data = json.loads(res.text)
            return data[0] if isinstance(data, list) else data
        except Exception as e:
            if "429" in str(e):
                time.sleep((attempt + 1) * 5)
            else:
                time.sleep(2)
    return None

def process_single_thread(thread, idx, total, eval_cache, checkpoint_file):
    tid = thread["thread_id"]
    res = evaluate_thread(thread)

    if res:
        scores = res.get("scores", {})
        eval_data = {
            "category": res.get("category", "未分類"),
            "summary": res.get("summary", ""),
            "keywords": res.get("keywords", []),
            "scores": {
                "evidence": int(scores.get("evidence", 0)),
                "solution": int(scores.get("solution", 0)),
                "local_focus": int(scores.get("local_focus", 0)),
                "constructive": int(scores.get("constructive", 0))
            },
            "reasoning": res.get("reasoning", "")
        }
    else:
        eval_data = {
            "category": "エラー",
            "summary": "AI分析エラー",
            "keywords": [],
            "scores": {"evidence": 0, "solution": 0, "local_focus": 0, "constructive": 0},
            "reasoning": "APIエラー"
        }

    with cache_lock:
        eval_cache[tid] = eval_data
        done = len(eval_cache)
        print(f"[{done}/{total}] {thread['meeting_date']} {thread['speaker']} -> {eval_data['scores']}")
        if done % 10 == 0:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(eval_cache, f, ensure_ascii=False, indent=2)

    return tid

def main():
    print("=" * 60)
    print("🚀 大阪市会 本会議＋全委員会 フルバッチパイプライン")
    print("=" * 60)

    client = bigquery.Client(project="gen-lang-client-0253904061")
    raw_stmts = fetch_osaka_all_data(client)

    print("\n🧵 スレッド構築中...")
    threads = build_osaka_threads(raw_stmts)
    print(f"✨ 抽出された有効な質疑スレッド数: {len(threads):,} 件")

    checkpoint_file = PROJECT_ROOT / "pipeline" / "osaka_eval_checkpoint.json"
    eval_cache = {}
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                eval_cache = json.load(f)
        except Exception:
            eval_cache = {}

    unprocessed = [th for th in threads if th["thread_id"] not in eval_cache]
    print(f"🎯 LLM評価対象: {len(unprocessed):,} 件")

    if unprocessed:
        print(f"⚡ 並列実行開始 (ワーカー数: {MAX_WORKERS})")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(process_single_thread, th, idx, len(threads), eval_cache, checkpoint_file)
                for idx, th in enumerate(unprocessed)
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"ワーカー例外: {e}")

    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(eval_cache, f, ensure_ascii=False, indent=2)

    frontend_data = []
    for th in threads:
        tid = th["thread_id"]
        res = eval_cache.get(tid, {})
        frontend_data.append({
            "id": tid,
            "speaker": th["speaker"],
            "meeting_id": th["meeting_id"],
            "meeting_date": th["meeting_date"],
            "meeting_title": th["meeting_title"],
            "category": res.get("category", "未分類"),
            "summary": res.get("summary", ""),
            "evidence_score": res.get("scores", {}).get("evidence", 0),
            "solution_score": res.get("scores", {}).get("solution", 0),
            "local_focus_score": res.get("scores", {}).get("local_focus", 0),
            "constructive_score": res.get("scores", {}).get("constructive", 0),
            "statement_text": th["question_text"]
        })

    out_file = PROJECT_ROOT / "frontend" / "public" / "data" / "osaka_statements_summary.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(frontend_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"🎉 全件バッチ完了！ フロントエンド用保存先: {out_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
