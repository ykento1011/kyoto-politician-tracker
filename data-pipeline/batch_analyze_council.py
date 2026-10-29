import json
import os
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY が設定されていません。")

genai.configure(api_key=GEMINI_API_KEY)
# 💡 最安・現行世代の 3.5-flash-lite を指定
model = genai.GenerativeModel('gemini-3.5-flash-lite')

MAX_WORKERS = 8
cache_lock = threading.Lock()

# 議員ホワイトリスト (67名)
# --- 正本マスターから動的ロード (ハードコード完全排除) ---
MASTER_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "master", "councilors_kyoto.json")
def get_official_councilors():
    if os.path.exists(MASTER_JSON):
        with open(MASTER_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            names = set()
            for c in data:
                clean_n = re.sub(r"[\s\u3000]+", "", c.get("name", ""))
                names.add(clean_n)
                names.add(c.get("name", ""))
                for al in c.get("aliases", []):
                    names.add(re.sub(r"[\s\u3000]+", "", al))
                    names.add(al)
            return list(names)
    return []

VALID_COUNCILORS = get_official_councilors()

def clean_name(name):
    if not name:
        return ""
    return str(name).replace(" ", "").replace(" ", "")

def find_meeting_chair(stmts):
    open_keywords = ["開会いたします", "開議宣告", "会議を開きます", "開議いたします", "質疑を行います"]
    for s in stmts[:15]:
        t = str(s.get("statement_text", ""))
        if any(kw in t for kw in open_keywords):
            return clean_name(s.get("speaker", ""))
    return None

def is_procedural_call(text):
    t = text.strip()
    if len(t) <= 65:
        if re.search(r'(?:委員長|副委員長|分科会長|副分科会長|主査|副主査|議長|副議長|委員|議員|部長|局長|室長|次長|課長|理事|副市長|市長|管理者)(?:。|様)?$', t):
            return True
        if re.search(r'^(?:どうぞ|それでは|続いて|次に)[。、]?', t) and len(t) < 25:
            return True
        if t in ['（「異議なし」と呼ぶ者あり）', '異議なし。', '結構です。', '多数であります。', '留保で。', '留保でお願いします。']:
            return True
        if re.search(r'どうぞ[。、]?$', t) and len(t) < 60:
            return True
        if re.search(r'(?:ほかに|何か)ございませんか[。、]?', t) and len(t) < 40:
            return True
        if any(keyword in t for keyword in [
            '提出できるとのことですので', '提出を求めることに決定いたします', 
            '本請願については留保', '委員会を再開いたします', '分科会を再開いたします', '質疑を行います'
        ]):
            return True
    return False

def build_debate_threads(statements_list):
    meetings = {}
    for stmt in statements_list:
        mid = stmt.get("meeting_id")
        if mid not in meetings:
            meetings[mid] = []
        meetings[mid].append(stmt)

    threads = []
    for mid, stmts in meetings.items():
        first_title = stmts[0].get("meeting_title", "")
        if "市会運営委員会" in first_title or "理事会" in first_title:
            continue

        stmts = sorted(stmts, key=lambda x: x.get("sequence_number", 0))
        chair = find_meeting_chair(stmts)
        current_thread = None
        
        for stmt in stmts:
            raw_speaker = str(stmt.get("speaker", ""))
            clean_speaker = clean_name(raw_speaker)
            text = str(stmt.get("statement_text", "")).strip()
            
            is_chair = (chair is not None and clean_speaker == chair)
            is_short_proc = is_procedural_call(text)
            
            if is_chair or is_short_proc:
                if current_thread is not None:
                    current_thread["related_statements"].append(stmt)
                continue

            is_councilor = clean_speaker in VALID_COUNCILORS

            if is_councilor:
                if current_thread is None or current_thread["speaker"] != raw_speaker:
                    if current_thread is not None:
                        threads.append(current_thread)
                    current_thread = {
                        "speaker": raw_speaker,
                        "meeting_id": mid,
                        "meeting_title": stmt.get("meeting_title", ""),
                        "meeting_date": stmt.get("meeting_date", ""),
                        "main_statement": stmt,
                        "context_log": [f"【議員 ({raw_speaker})】\n{text}"],
                        "related_statements": [stmt],
                        "has_admin_response": False
                    }
                else:
                    current_thread["context_log"].append(f"【議員・再質問 ({raw_speaker})】\n{text}")
                    current_thread["related_statements"].append(stmt)
            else:
                if current_thread is not None:
                    current_thread["has_admin_response"] = True
                    current_thread["related_statements"].append(stmt)
                    current_thread["context_log"].append(f"【行政側・答弁 ({raw_speaker})】\n{text}")
                    
        if current_thread is not None:
            threads.append(current_thread)

    return threads

def is_procedural_or_voting(thread):
    """
    議事進行・単なる挨拶・採決・討論発言を徹底排除し、実質的な政策質疑のみを通過させる
    """
    if not thread.get("has_admin_response", False):
        return True

    conversation_text = "\n\n".join(thread["context_log"])

    # 1. 議員本人の発言部分のみを抽出して実質質問の有無を検証
    councilor_texts = [text for text in thread["context_log"] if "【議員" in text]
    joined_councilor = " ".join(councilor_texts).strip()

    # 議員の発言が極端に短く、かつ具体的な質問・提案キーワードを含まない場合は除外
    if len(joined_councilor) < 120 and not re.search(r"(?:か[。？\?]|伺い|お尋ね|どうでしょうか|いかがでしょうか|確認|提案|見解|求め|教え)", joined_councilor):
        return True

    # 2. 挨拶・御礼・就任・日程調整の定型パターン
    greeting_patterns = [
        r"よろしくお願いい?たします[。]?$",
        r"一言ご挨拶を?申し上げます",
        r"以上をもちまして.*?質疑を終了",
        r"日程の順序について",
        r"本件に対する質疑はこの程度に留め",
        r"質疑の終結を決定することに御異議",
        r"ご静聴ありがとうございました",
        r"質問を留保いたします",
        r"留保で(?:お願いします|。)"
    ]
    if any(re.search(p, conversation_text) for p in greeting_patterns) and len(conversation_text) < 350:
        return True

    # 3. 採決・討論・意見書の手続きパターン
    procedural_patterns = [
        r"慎重に?(?:審議|検討)した結果",
        r"(?:原案|修正案)(?:のとおり|に)?(?:賛成|反対)(?:いたします|します|いたします。)",
        r"(?:賛成|反対)討論を.*?行います",
        r"討論結了",
        r"意見書案",
        r"委員長報告",
        r"付帯決議を付します",
        r"一括して表決に付します",
        r"これより表決を採ります",
        r"挙手を求めます",
        r"可決すべきものと決定",
        r"本日の(?:委員会|分科会|本会議|会議)を散会いたします"
    ]
    # 💡 修正箇所：第2引数を conversation_text に修正
    has_procedural = any(re.search(p, conversation_text) for p in procedural_patterns)
    has_substantive_question = bool(re.search(r"(?:伺いたい|お聞かせいただきたい|どうでしょうか|いかがでしょうか|教えていただきたい|求めて、?終わります|質問を終わります)", conversation_text))
    
    if has_procedural and not has_substantive_question:
        return True
    
    if len(conversation_text) < 500 and any(re.search(p, conversation_text) for p in [r"表決を採ります", r"採決を(?:行い|行います)", r"御異議ございませんか。?\s*（「異議なし」"]):
        return True

    return False

def evaluate_thread_with_gemini(thread):
    conversation_text = "\n\n".join(thread["context_log"])
    
    # 12,000文字超の場合は前後を抽出して推論遅延とトークン肥大化を防止
    if len(conversation_text) > 12000:
        conversation_text = conversation_text[:6000] + "\n\n...[中略: 議論継続中]...\n\n" + conversation_text[-6000:]

    speaker = thread["speaker"]
    
    # 💡 指摘1・2を反映：constructiveを「質疑の展開」に改変、solutionから「行政の不備」を排除
    prompt = f"""
あなたは京都市議会の政策質疑データを構造化・整理するCivic Tech分析AIです。
以下のテキストは、議員（{speaker}）と行政側による質疑応答スレッドです。
この質疑の内容を、4つの分析軸（各0〜5点）で整理し、観察された客観的事実のみをJSON形式で出力してください。

【厳格な禁止事項（重要）】
・議員や質疑に対する「講評」「評価」「良し悪しの判断」は一切行わないこと。
・「前向き」「建設的」「鋭い」「引き出した」「迫った」「強く求めた」などの成果強調表現は禁止。
・「至らなかった」「乏しい」「終始した」「低得点となる」「評価できる/できない」「要望の域に留まった」などの減点理由・評価語は禁止。
・分析メモ（reasoning）には、点数の理由や合否を書くのではなく、「何を参照し、何を尋ね、行政がどう答えたか」という客観的事実のみを記述すること。

【4軸の分析基準（整理用の物差し）】
1. evidence (0-5: 根拠・データ):
   - 0-2: 一般的な状況確認、意見表明中心
   - 3: 過去の実績、予算額、他都市事例等の言及
   - 4-5: 条例条文、公的統計、公文書、具体的数値データの明示
2. solution (0-5: 対案・是正策):
   - 0-2: 現状確認、一般的な要望
   - 3: 実務的な改善策や運用の選択肢の提示
   - 4-5: 制度設計・財源を含む対案、または具体的な改善・見直しについて質問・提案した内容
3. local_focus (0-5: 地域解像度):
   - 0-2: 国政論や一般的な総論
   - 3: 特定の行政区、担当部局、個別事業・制度への言及
   - 4-5: 町名、学区、商店街、公共施設、交差点、路線名など生活現場の具体名
4. constructive (0-5: 質疑の展開):
   - 0-2: 冒頭質問のみ、または単発の確認
   - 3: 答弁内容を踏まえた論点の絞り込み・再質問
   - 4-5: 答弁内容を踏まえ、制度の運用実態や今後の方向性について掘り下げて確認・質問した展開

【分析メモ（reasoning）の記述フォーマット】
以下の構成で、事実のみを簡潔に（120〜150文字程度で）記述してください：
「[参照した資料・公的データ・数値] を参照した質疑。[質問・提案・要望した論点] について質問・提案し、行政側から [説明・答弁の要点] について説明・答弁があった質疑として整理されています。」
※点数が低い場合でも「〜が不足していた」とは書かず、「〜について質問し、行政側から〜と説明があった質疑として整理されています」と淡々と事実のみを書いてください。

【要旨（summary）の記述フォーマット】
「議員の質問・提案 ➔ 行政側の答弁」の事実関係のみを客観的に記述してください（80〜100文字程度）。「引き出した」「迫った」などの評価語は使用しないでください。

【質疑スレッド ログ】
{conversation_text}

出力は以下のJSONスキーマのみとしてください。
{{
  "category": "子育て・教育, 都市再生・交通インフラ, 産業・観光・地域経済, 福祉・医療・健康, 財政・行革, くらし・環境・エネルギー, 防災・減災・治安, 文化・景観・歴史 の中から最も適切なものを1つ",
  "summary": "質問と答弁の事実要旨（客観的事実のみ）",
  "keywords": ["キーワード1", "キーワード2", "キーワード3"],
  "scores": {{
    "evidence": 0,
    "solution": 0,
    "local_focus": 0,
    "constructive": 0
  }},
  "reasoning": "事実ベースの分析メモ（フォーマット遵守）"
}}
"""
    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            return json.loads(response.text)
        except Exception as e:
            if "429" in str(e):
                wait_time = (attempt + 1) * 6
                time.sleep(wait_time)
            else:
                time.sleep(2)
    return None

def process_single_thread(thread, index, total, eval_cache, checkpoint_file):
    main_stmt = thread["main_statement"]
    mid = main_stmt["meeting_id"]
    seq = main_stmt["sequence_number"]
    key = f"{mid}_{seq}"

    spk = thread["speaker"]
    m_date = thread["meeting_date"]
    m_title = thread["meeting_title"].split()[-1][:18]

    result = evaluate_thread_with_gemini(thread)
    
    if result:
        scores = result.get("scores", {})
        eval_data = {
            "category": result.get("category", "未分類"),
            "summary": result.get("summary", ""),
            "keywords": result.get("keywords", []),
            "scores": {
                "evidence": int(scores.get("evidence", 0)),
                "solution": int(scores.get("solution", 0)),
                "local_focus": int(scores.get("local_focus", 0)),
                "constructive": int(scores.get("constructive", 0))
            },
            "is_evaluated": True,
            "reasoning": result.get("reasoning", "")
        }
    else:
        # 💡 指摘3：エラー時の文言を「分析」に統一
        eval_data = {
            "is_evaluated": False,
            "reasoning": "Gemini API分析スキップまたはエラー",
            "scores": {"evidence": 0, "solution": 0, "local_focus": 0, "constructive": 0},
            "category": "質疑外発言"
        }

    with cache_lock:
        eval_cache[key] = eval_data
        completed_count = len(eval_cache)
        print(f"[{completed_count}/{total}] {m_date} {spk}議員 (#{seq} @ {m_title}) -> {eval_data['scores']}")
        
        if completed_count % 5 == 0 or completed_count == total:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(eval_cache, f, ensure_ascii=False, indent=2)

    return key

def main():
    input_file = "sagebase_crawled_data.json"
    output_file = "analyzed_kyoto_politicians_term.json"
    checkpoint_file = "eval_checkpoint.json"

    print("==================================================")
    print("📖 データセット読み込み中...")
    with open(input_file, "r", encoding="utf-8") as f:
        statements = json.load(f)

    print(f"📄 総発言数: {len(statements):,} 件")
    print("==================================================")

    # 1. スレッド構築
    threads = build_debate_threads(statements)
    print(f"🧵 抽出された候補スレッド数: {len(threads):,} スレッド")

    # 2. 実質質疑スレッドの選別
    target_threads = []
    skipped_count = 0
    for th in threads:
        if is_procedural_or_voting(th):
            skipped_count += 1
        else:
            target_threads.append(th)

    print(f"⏩ 非質疑スキップ数: {skipped_count:,} スレッド")
    print(f"🎯 AI分析対象スレッド数: {len(target_threads):,} スレッド")
    print(f"⚡ 並列ワーカー数: {MAX_WORKERS} スレッド並行処理 (gemini-3.5-flash-lite)")
    print("==================================================")

    # 3. チェックポイントの読み込み
    eval_cache = {}
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                eval_cache = json.load(f)
            # 💡 指摘3：ログを「分析済み」に統一
            print(f"🔄 チェックポイント検出: 分析済み {len(eval_cache):,} 件をスキップして再開します。")
        except Exception:
            eval_cache = {}

    # 4. 未処理スレッドの抽出
    unprocessed_threads = []
    for idx, th in enumerate(target_threads):
        key = f"{th['main_statement']['meeting_id']}_{th['main_statement']['sequence_number']}"
        if key not in eval_cache:
            unprocessed_threads.append((th, idx))

    print(f"🚀 残り処理スレッド数: {len(unprocessed_threads):,} 件")
    print("==================================================")

    start_time = time.time()

    # 5. マルチスレッド並列実行
    if unprocessed_threads:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(process_single_thread, th, idx, len(target_threads), eval_cache, checkpoint_file)
                for th, idx in unprocessed_threads
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"ワーカーエラー: {e}")

    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(eval_cache, f, ensure_ascii=False, indent=2)

    elapsed = int(time.time() - start_time)
    # 💡 指摘3：ログを「並列分析」に統一
    print(f"\n🎉 全スレッドの並列分析が完了しました！（所要時間: {elapsed//60}分{elapsed%60}秒）")

    # 6. 全発言データへのマッピングと最終保存
    print("📦 最終JSONへのデータ結合中...")
    stmt_dict = {f"{s['meeting_id']}_{s['sequence_number']}": s for s in statements}

    for s in statements:
        s["analysis"] = {
            "is_evaluated": False,
            "reasoning": "質疑外発言（進行・答弁等）",
            "scores": {"evidence": 0, "solution": 0, "local_focus": 0, "constructive": 0},
            "category": "質疑外発言"
        }

    for th in target_threads:
        main_stmt = th["main_statement"]
        key = f"{main_stmt['meeting_id']}_{main_stmt['sequence_number']}"
        if key in eval_cache and eval_cache[key].get("is_evaluated"):
            stmt_dict[key]["analysis"] = eval_cache[key]

            for rel_stmt in th["related_statements"]:
                if rel_stmt["sequence_number"] != main_stmt["sequence_number"]:
                    rel_key = f"{rel_stmt['meeting_id']}_{rel_stmt['sequence_number']}"
                    if rel_key in stmt_dict:
                        # 💡 指摘3：「代表発言に統合分析済み」に統一
                        stmt_dict[rel_key]["analysis"] = {
                            "is_evaluated": False,
                            "reasoning": "スレッド内の関連発言（代表発言に統合分析済み）",
                            "scores": {"evidence": 0, "solution": 0, "local_focus": 0, "constructive": 0},
                            "category": "質疑外発言（統合済み）"
                        }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(statements, f, ensure_ascii=False, indent=2)

    print(f"💾 最終ファイル出力完了: {output_file}")
    print("==================================================")

if __name__ == "__main__":
    main()