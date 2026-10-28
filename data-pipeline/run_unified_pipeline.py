from yokohama_adapter import YokohamaAdapter
import json, os, sys, time, threading, re, argparse
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

sa_path = PROJECT_ROOT / "data-pipeline" / "service_account.json"
if sa_path.exists() and sa_path.stat().st_size > 0:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(sa_path.resolve())

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3.5-flash-lite")

MAX_WORKERS = 8
cache_lock = threading.Lock()

# ==========================================
# 1. 共通コア：LLM評価ロジック・スキーマ（正本完全準拠）
# ==========================================

def evaluate_debate_thread(thread):
    convo = "\n\n".join(thread["context_log"])
    if len(convo) > 8000:
        convo = convo[:4000] + "\n\n...[中略]...\n\n" + convo[-4000:]

    speaker = thread["speaker"]

    prompt = f"""
あなたは地方議会の政策質疑データを構造化・整理するCivic Tech分析AIです。
以下のテキストは、議員（{speaker}）と行政側による質疑応答スレッドです。
この質疑の内容を、4つの分析軸（各1〜5点の整数）で整理し、観察された客観的事実のみをJSON形式で出力してください。

【厳格な禁止事項（重要）】
・議員や質疑に対する「講評」「評価」「良し悪しの判断」は一切行わないこと。
・「前向き」「建設的」「鋭い」「引き出した」「迫った」「強く求めた」などの成果強調表現は禁止。
・「至らなかった」「乏しい」「終始した」「低得点となる」「評価できる/できない」「要望の域に留まった」などの減点理由・評価語は禁止。
・分析メモ（reasoning）には、点数の理由や合否を書くのではなく、「何を参照し、何を尋ね、行政がどう答えたか」という客観的事実のみを記述すること。

【4軸の分析基準（1〜5の整数）】
1. evidence (1-5: 根拠・データ):
   - 1-2: 一般的な状況確認、意見表明中心
   - 3: 過去の実績、予算額、他都市事例等の言及
   - 4-5: 条例条文、公的統計、公文書、具体的数値データの明示
2. solution (1-5: 対案・是正策):
   - 1-2: 現状確認、一般的な要望
   - 3: 実務的な改善策や運用の選択肢の提示
   - 4-5: 制度設計・財源を含む対案、または具体的な改善・見直しについて質問・提案した内容
3. local_focus (1-5: 地域解像度):
   - 1-2: 国政論や一般的な総論
   - 3: 特定の行政区、担当部局、個別事業・制度への言及
   - 4-5: 町名、学区、商店街、公共施設、交差点、路線名など生活現場の具体名
4. constructive (1-5: 質疑の展開):
   - 1-2: 冒頭質問のみ、または単発の確認
   - 3: 答弁内容を踏まえた論点の絞り込み・再質問
   - 4-5: 答弁内容を踏まえ、制度の運用実態や今後の方向性について掘り下げて確認・質問した展開

【分析メモ（reasoning）の記述フォーマット】
以下の構成で、事実のみを簡潔に（120〜150文字程度で）記述してください：
「[参照した資料・公的データ・数値] を参照した質疑。[質問・提案・要望した論点] について質問・提案し、行政側から [説明・答弁の要点] について説明・答弁があった質疑として整理されています。」
※点数が低い場合でも「〜が不足していた」とは書かず、「〜について質問し、行政側から〜と説明があった質疑として整理されています」と淡々と事実のみを書いてください。

【要旨（summary）の記述フォーマット】
「議員の質問・提案 ➔ 行政側の答弁」の事実関係のみを客観的に記述してください（80〜100文字程度）。「引き出した」「迫った」などの評価語は使用しないでください。

【質疑スレッド ログ】
会議: {thread['meeting_date']} {thread['meeting_title']}
議員: {speaker}
内容:
{convo}

出力は以下のJSONスキーマのみとしてください。
{{
  "category": "子育て・教育, 都市再生・交通インフラ, 産業・観光・地域経済, 福祉・医療・健康, 財政・行革, くらし・環境・エネルギー, 防災・減災・治安, 文化・景観・歴史 の中から最も適切なものを1つ",
  "summary": "質問と答弁の事実要旨（客観的事実のみ、80〜100文字程度）",
  "statement_text": "質疑の核となる論点・テーマ（見出しとして使える20〜30字程度の短い文）",
  "keywords": ["キーワード1", "キーワード2", "キーワード3"],
  "scores": {{
    "evidence": 3,
    "solution": 3,
    "local_focus": 3,
    "constructive": 3
  }},
  "reasoning": "事実ベースの分析メモ（フォーマット遵守、120〜150文字程度）"
}}
"""
    for attempt in range(3):
        try:
            res = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json", temperature=0.0)
            )
            data = json.loads(res.text)
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            return data
        except Exception as e:
            if "429" in str(e):
                time.sleep((attempt + 1) * 3)
            else:
                time.sleep(1)
    return None

def parse_score(val):
    try:
        s = int(round(float(val)))
        return max(1, min(5, s))
    except Exception:
        return 3

# ==========================================
# 2. 都市アダプター：大阪市会
# ==========================================

class OsakaAdapter:
    city_code = "osaka"
    governing_body_id = 532
    official_keywords = ["市長", "副市長", "局長", "区長", "部長", "室長", "課長", "次長", "理事者", "教育長", "技監", "参事", "主査", "所長", "委員長"]
    official_minute_url = "https://ssp.kaigiroku.net/tenant/cityosaka/SpMinuteSearch.html"

    @classmethod
    def fetch_data(cls, client):
        print(f"📥 [{cls.city_code.upper()}] BigQueryから本会議・全委員会データを抽出中 (2023-05-01以降)...")
        q_meetings = f"""
            SELECT m.id AS meeting_id, m.name AS meeting_name, m.date AS meeting_date, m.url AS official_url FROM `gen-lang-client-0253904061.sagebase_data.meetings` m
            JOIN `gen-lang-client-0253904061.sagebase_data.conferences` conf ON m.conference_id = conf.id
            WHERE conf.governing_body_id = {cls.governing_body_id}
              AND (m.name LIKE '%委員会%' OR m.name LIKE '%定例会%' OR m.name LIKE '%本会議%')
              AND m.name NOT LIKE '%市会運営%'
              AND m.name NOT LIKE '%資料編%'
              AND m.name NOT LIKE '%別冊%'
              AND m.date >= '2023-05-01'
            ORDER BY m.date DESC
        """
        meetings = list(client.query(q_meetings).result())
        print(f"🎯 [{cls.city_code.upper()}] 対象会議数: {len(meetings)} 件")

        all_stmts = []
        for mtg in meetings:
            q_stmts = f"""
                SELECT c.sequence_number, c.speaker_name AS speaker, c.comment AS statement_text, '{mtg.meeting_id}' AS meeting_id, '{mtg.meeting_name}' AS meeting_title, '{mtg.meeting_date}' AS meeting_date, '{getattr(mtg, 'official_url', '')}' AS official_url
                FROM `gen-lang-client-0253904061.sagebase_data.conversations` c
                JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON c.minutes_id = min.id
                WHERE min.meeting_id = {mtg.meeting_id}
                ORDER BY c.sequence_number ASC
            """
            all_stmts.extend([dict(r) for r in client.query(q_stmts).result()])
        print(f"✅ [{cls.city_code.upper()}] 合計 {len(all_stmts):,} 件の発言を取得しました。")
        return all_stmts

    @classmethod
    def build_threads(cls, stmts):
        print(f"🧵 [{cls.city_code.upper()}] 質疑スレッドを構築中...")
        meetings = {}
        for s in stmts:
            mid = s["meeting_id"]
            if mid not in meetings:
                meetings[mid] = []
            meetings[mid].append(s)

        threads = []
        for mid, m_stmts in meetings.items():
            m_stmts = sorted(m_stmts, key=lambda x: x.get("sequence_number", 0))
            current_thread = None

            for s in m_stmts:
                spk = (s.get("speaker") or "").strip()
                text = (s.get("statement_text") or "").strip()
                if not spk or not text:
                    continue

                if "委員長" in spk or "議長" in spk:
                    continue

                is_admin = any(k in spk for k in cls.official_keywords)
                if is_admin:
                    if current_thread is not None:
                        current_thread["context_log"].append(f"【行政側 ({spk})】\n{text}")
                        current_thread["has_response"] = True
                else:
                    spk_clean = re.sub(r"(君|委員|議員)$", "", spk).strip()
                    if current_thread is None or current_thread["speaker"] != spk_clean:
                        if current_thread is not None and current_thread["has_response"] and len(current_thread["question_text"]) > 40:
                            threads.append(current_thread)
                        current_thread = {
                            "thread_id": f"th_{mid}_{s['sequence_number']}",
                            "speaker": spk_clean,
                            "meeting_id": mid,
                            "meeting_title": s["meeting_title"],
                            "meeting_date": str(s["meeting_date"]),
                            "question_text": text,
                            "context_log": [f"【議員 ({spk_clean})】\n{text}"],
                            "has_response": False,
                                "official_url": s.get("official_url")
                        }
                    else:
                        if current_thread is not None:
                            current_thread["context_log"].append(f"【議員・再質問 ({spk_clean})】\n{text}")
                            if len(current_thread["question_text"]) < 200:
                                current_thread["question_text"] += f"\n{text}"

            if current_thread is not None and current_thread["has_response"] and len(current_thread["question_text"]) > 40:
                threads.append(current_thread)

        print(f"✅ [{cls.city_code.upper()}] {len(threads):,} 件の質疑スレッドを構築しました。")
        return threads

# ==========================================
# 3. 都市アダプター：名古屋市会
# ==========================================

class NagoyaAdapter:
    city_code = "nagoya"
    governing_body_id = 958
    official_keywords = [
        "市長", "副市長", "局長", "区長", "部長", "室長", "課長", "次長", 
        "理事者", "教育長", "技監", "参事", "主査", "担当部長", "担当課長",
        "事務所長", "委員長", "緑政土木", "子ども青少年", "観光文化交流",
        "住宅都市", "健康福祉", "市民経済", "環境局", "上下水道", "交通局", "消防局"
    ]
    official_minute_url = "https://ssp.kaigiroku.net/tenant/nagoya/SpMinuteSearch.html"

    @classmethod
    def build_councilor_lookup(cls):
        master_path = PROJECT_ROOT / "frontend" / "public" / "data" / "nagoya_speaker_stats.json"
        if not master_path.exists():
            return {}, set()
        with open(master_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        fullnames, lookup, surname_map = set(), {}, {}
        for spk in data:
            name = (spk.get("speaker") or spk.get("name") or "").strip()
            if not name:
                continue
            fullnames.add(name)
            lookup[name] = name
            parts = re.split(r"[\s ]+", name)
            surname = parts[0]
            if surname not in surname_map:
                surname_map[surname] = []
            surname_map[surname].append(name)
        for surname, matches in surname_map.items():
            if len(matches) == 1:
                lookup[surname] = matches[0]
        lookup.update({
            "さわだ［晃］": "さわだ晃一", "沢田［ひ］": "沢田ひとみ",
            "佐藤［夕］": "佐藤ゆうこ", "佐藤［ゆう］": "佐藤ゆうこ",
            "中村［満］": "中村満", "中村［しゅう］": "中村しゅうへい",
            "渡辺［やす］": "渡辺やすのり", "渡邊［房］": "渡邊房代"
        })
        return lookup, fullnames

    @classmethod
    def fetch_data(cls, client):
        print(f"📥 [{cls.city_code.upper()}] BigQueryから本会議・全委員会データを抽出中 (2023-04-12以降)...")
        q_meetings = f"""
            SELECT m.id AS meeting_id, m.name AS meeting_name, m.date AS meeting_date, conf.name AS conf_name
            FROM `gen-lang-client-0253904061.sagebase_data.meetings` m
            JOIN `gen-lang-client-0253904061.sagebase_data.conferences` conf ON m.conference_id = conf.id
            WHERE conf.governing_body_id = {cls.governing_body_id}
              AND (m.name LIKE '%委員会%' OR m.name LIKE '%定例会%' OR m.name LIKE '%本会議%')
              AND m.name NOT LIKE '%議会運営%'
              AND m.date >= '2023-04-12'
            ORDER BY m.date DESC
        """
        meetings = list(client.query(q_meetings).result())
        print(f"🎯 [{cls.city_code.upper()}] 対象会議数: {len(meetings)} 件")

        all_stmts = []
        for mtg in meetings:
            q_stmts = f"""
                SELECT c.sequence_number, c.speaker_name AS speaker, c.comment AS statement_text, '{mtg.meeting_id}' AS meeting_id, '{mtg.meeting_name}' AS meeting_title, '{mtg.meeting_date}' AS meeting_date, '{getattr(mtg, 'official_url', '')}' AS official_url
                FROM `gen-lang-client-0253904061.sagebase_data.conversations` c
                JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON c.minutes_id = min.id
                WHERE min.meeting_id = {mtg.meeting_id}
                ORDER BY c.sequence_number ASC
            """
            all_stmts.extend([dict(r) for r in client.query(q_stmts).result()])
        print(f"✅ [{cls.city_code.upper()}] 合計 {len(all_stmts):,} 件の発言を取得しました。")
        return all_stmts

    @classmethod
    def build_threads(cls, stmts):
        print(f"🧵 [{cls.city_code.upper()}] 質疑スレッドを構築中...")
        lookup, fullnames = cls.build_councilor_lookup()
        
        def normalize_speaker(spk):
            clean = re.sub(r"(君|委員|議員)$", "", spk.strip()).strip()
            return lookup.get(clean, clean)

        def is_admin(spk, text):
            spk_c = spk.replace(" ", "").replace(" ", "")
            if any(k in spk_c for k in cls.official_keywords):
                return True
            if normalize_speaker(spk) not in fullnames:
                if any(p in text[:60] for p in ["にお答えいたします", "にお答えします", "についてお答えします", "お尋ねいただきました"]):
                    return True
            return False

        meetings = {}
        for s in stmts:
            mid = s["meeting_id"]
            if mid not in meetings:
                meetings[mid] = []
            meetings[mid].append(s)

        threads = []
        for mid, m_stmts in meetings.items():
            m_stmts = sorted(m_stmts, key=lambda x: x.get("sequence_number", 0))
            current_thread = None

            for s in m_stmts:
                spk = (s.get("speaker") or "").strip()
                text = (s.get("statement_text") or "").strip()
                if not spk or not text or "委員長" in spk or "議長" in spk:
                    continue

                if is_admin(spk, text):
                    if current_thread is not None:
                        current_thread["context_log"].append(f"【行政側 ({spk})】\n{text}")
                        current_thread["has_response"] = True
                else:
                    spk_norm = normalize_speaker(spk)
                    if current_thread is None or current_thread["speaker"] != spk_norm:
                        if current_thread is not None and current_thread["has_response"] and len(current_thread["question_text"]) > 40:
                            threads.append(current_thread)
                        current_thread = {
                            "thread_id": f"th_{mid}_{s['sequence_number']}",
                            "speaker": spk_norm,
                            "meeting_id": mid,
                            "meeting_title": s["meeting_title"],
                            "meeting_date": str(s["meeting_date"]),
                            "question_text": text,
                            "context_log": [f"【議員 ({spk_norm})】\n{text}"],
                            "has_response": False,
                                "official_url": s.get("official_url")
                        }
                    else:
                        if current_thread is not None:
                            current_thread["context_log"].append(f"【議員 ({spk_norm})】\n{text}")
                            if len(current_thread["question_text"]) < 200:
                                current_thread["question_text"] += f"\n{text}"

            if current_thread is not None and current_thread["has_response"] and len(current_thread["question_text"]) > 40:
                threads.append(current_thread)

        print(f"✅ [{cls.city_code.upper()}] {len(threads):,} 件の質疑スレッドを構築しました。")
        return threads

# ==========================================
# 4. 共通実行エンジン（CLIエントリポイント）
# ==========================================

ADAPTERS = {
    "osaka": OsakaAdapter,
    "nagoya": NagoyaAdapter,
    "yokohama": YokohamaAdapter
}

def run_pipeline(city_code, limit=None):
    if city_code not in ADAPTERS:
        raise ValueError(f"未対応の都市コードです: {city_code}")

    adapter = ADAPTERS[city_code]
    client = bigquery.Client(project="gen-lang-client-0253904061")

    raw_stmts = adapter.fetch_data(client)
    threads = adapter.build_threads(raw_stmts)

    checkpoint_file = PROJECT_ROOT / "pipeline" / f"{city_code}_eval_checkpoint.json"
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    eval_cache = {}
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                eval_cache = json.load(f)
            print(f"🔄 チェックポイント検出: {len(eval_cache):,} 件をスキップします。")
        except Exception:
            eval_cache = {}

    unprocessed = [th for th in threads if th["thread_id"] not in eval_cache]
    if limit is not None and limit > 0:
        print(f"🧪 [サンプリングモード] 評価対象を先頭 {limit} 件に制限します。")
        unprocessed = unprocessed[:limit]
    print(f"🎯 [{city_code.upper()}] LLM評価対象: {len(unprocessed):,} 件 (8並列実行)")

    def process_thread(thread):
        tid = thread["thread_id"]
        res = evaluate_debate_thread(thread)
        if res:
            scores = res.get("scores", {})
            eval_data = {
                "category": res.get("category", "子育て・教育"),
                "summary": res.get("summary", ""),
                "statement_text": res.get("statement_text", ""),
                "keywords": res.get("keywords", []),
                "scores": {
                    "evidence": parse_score(scores.get("evidence", 3)),
                    "solution": parse_score(scores.get("solution", 3)),
                    "local_focus": parse_score(scores.get("local_focus", 3)),
                    "constructive": parse_score(scores.get("constructive", 3))
                },
                "reasoning": res.get("reasoning", "")
            }
        else:
            eval_data = {
                "category": "子育て・教育",
                "summary": "分析スキップ",
                "statement_text": "質疑論点",
                "keywords": [],
                "scores": {"evidence": 3, "solution": 3, "local_focus": 3, "constructive": 3},
                "reasoning": "分析スキップまたは再試行対象"
            }

        with cache_lock:
            eval_cache[tid] = eval_data
            done = len(eval_cache)
            if done % 25 == 0 or done == len(threads):
                print(f"  ... 進捗 [{city_code.upper()}]: {done} / {len(threads)}")
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(eval_cache, f, ensure_ascii=False, indent=2)

    if unprocessed:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_thread, th) for th in unprocessed]
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
        scores = res.get("scores", {})
        frontend_data.append({
            "id": tid,
            "speaker": th["speaker"],
            "meeting_id": th["meeting_id"],
            "meeting_date": th["meeting_date"],
            "meeting_title": th["meeting_title"],
            "category": res.get("category", "子育て・教育"),
            "summary": res.get("summary", ""),
            "statement_text": res.get("statement_text") or th["question_text"][:30],
            "keywords": res.get("keywords", []),
            "reasoning": res.get("reasoning", ""),
            "scoring_reasoning": res.get("reasoning", ""),
            "evidence_score": scores.get("evidence", 3),
            "solution_score": scores.get("solution", 3),
            "local_focus_score": scores.get("local_focus", 3),
            "constructive_score": scores.get("constructive", 3),
            "official_url": th.get("official_url") or adapter.official_minute_url
        })

    frontend_data.sort(key=lambda x: x["meeting_date"], reverse=True)
    out_file = PROJECT_ROOT / "frontend" / "public" / "data" / f"{city_code}_statements_summary.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(frontend_data, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 [{city_code.upper()}] 完了！ {len(frontend_data):,} 件を {out_file.name} に保存しました。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="議会のミカタ 統合データパイプライン")
    parser.add_argument("--city", required=True, choices=["osaka", "nagoya", "yokohama"], help="対象都市コード")
    parser.add_argument("--limit", type=int, default=None, help="サンプリング実行件数")
    args = parser.parse_args()
    run_pipeline(args.city, limit=args.limit)