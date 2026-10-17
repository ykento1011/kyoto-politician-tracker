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
VALID_COUNCILORS = [
    "青野仁志", "赤阪仁", "天方ひろゆき", "井﨑敦子", "井崎敦子", "井上よしひろ", "宇佐美賢一",
    "江村理紗", "えもとかよこ", "大津裕太", "おんづか功", "片桐直哉", "加藤あい",
    "加藤昌洋", "神谷修平", "河合ようこ", "かわしま優子", "河村諒", "きくち一秀",
    "北尾ゆか", "北川みき", "北山ただお", "久保田正紀", "くまざわ真昭", "くらた共子",
    "こうち大輔", "小島信太郎", "さくらい泰広", "繁隆夫", "しまもと京司", "下村あきら",
    "菅谷浩平", "田中明秀", "田中たかのり", "谷口みゆき", "玉本なるみ", "津田大三",
    "寺田一博", "とがし豊", "富きくお", "中高しゅうじ", "中野洋一", "中村まり",
    "西野さち子", "西村義直", "西山信昌", "橋村芳和", "土方莉紗", "兵藤しんいち",
    "平井良人", "平田圭", "平山たかお", "平山よしかず", "増成竜治", "松田けい子",
    "みちはた弘之", "椋田隆知", "森かれん", "森田守", "森田ゆみ子", "もりもと英靖",
    "山田こうじ", "やまね智史", "山本恵一", "山本しゅうじ", "山本陽子", "湯浅光彦",
    "吉田孝雄"
]

def clean_name(name):
    if not name:
        return ""
    # 半角・全角スペースの両方を確実に除去
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
    if not thread.get("has_admin_response", False):
        return True

    conversation_text = "\n\n".join(thread["context_log"])

    if len(conversation_text) < 150 and not re.search(r"(?:か[。？\?]|いかが|お聞かせ|お答え|伺い|求め|確認|提案)", conversation_text):
        return True
        
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
        r"本日の(?:委員会|分科会|本会議|会議)を散会いたします",
        r"留保で(?:お願いします|。)"
    ]
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
    
    prompt = f"""
あなたは京都市議会の政策質疑を客観的・中立的に評価するCivic Tech監査AIです。
以下のテキストは、ある議員（{speaker}）と行政側による「一連の質疑応答スレッド」です。
行政側の答弁やそれを受けた議員の再質問など、やり取り全体を通じて質疑の質を以下の厳格な客観的ルーブリックに基づき、各項目0〜5点の整数で厳格に採点してください。

【評価ルーブリック】
1. evidence (0-5: 根拠・データ):
   - 0点: 主観や感情的な主張、伝聞のみ。客観的根拠が皆無。
   - 3点: 京都市の過去の施策実績、予算額、他都市の類似事例などのファクトを引用。
   - 5点: 条例条文、公的統計データ、公式答弁ログ、公文書等の一次資料・具体的数値を明示して論理を構築。

2. solution (0-5: 対案・是正策):
   ※重要（行政監視機能の正当評価）：
   政策立案型（与党・是々非々型）の具体的対案提示だけでなく、行政監視型（追及型・野党型）の質疑において「行政の瑕疵・不正・怠慢・制度不備・税金無駄遣いを論理的に暴き、是正や見直し・再調査・改善を約束させた質疑」も最高水準の是正策（5点）として同等に高く評価すること。
   - 0点: 単なる批判・感情的反発・具体性のない抽象的な要望・不満のみ。
   - 3点: 行政手続きの改善や民間連携など、具体的かつ実現可能な改善策・選択肢を提示。
   - 5点: 財源の裏付けや制度設計を含む抜本的対案を提示、または行政の瑕疵・不正・不備を明確に特定し、是正・調査・見直し・改善を約束させた質疑。

3. local_focus (0-5: 地域解像度):
   - 0点: 国政レベルの抽象論や、京都市に特有でない一般論に終始。
   - 3点: 特定の行政区、担当局・事業名、京都市制度の個別運用課題にフォーカス。
   - 5点: 具体的な町名、学区、商店街、公共施設、道路・バス路線名など生活現場の具体名に深く言及。

4. constructive (0-5: 議論の進展):
   - 0点: 原稿の棒読み、行政答弁を無視した独り言、一方的な主張の繰り返し。
   - 3点: 行政答弁の内容（理由や現状説明）を踏まえ、論点を絞り込んで再質問。
   - 5点: 行政答弁の論理破綻や課題の核心を的確に突き、行政側の見解変化や前向きな答弁を引き出すなど議論を前進させた展開。

【質疑スレッド ログ】
{conversation_text}

出力は以下のJSONスキーマのみとしてください。
{{
  "category": "都市計画, 防災・減災, 福祉・医療, 子育て・教育, 財政・行革, 環境・エネルギー の中から適切なもの（複数可）",
  "summary": "この質疑セッション全体の要旨（100文字程度）",
  "keywords": ["キーワード1", "キーワード2", "キーワード3"],
  "scores": {{
    "evidence": 0,
    "solution": 0,
    "local_focus": 0,
    "constructive": 0
  }},
  "reasoning": "なぜそのスコアになったのか、ルーブリックに照らした根拠を簡潔に（150文字程度）"
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
        eval_data = {
            "is_evaluated": False,
            "reasoning": "Gemini API評価スキップまたはエラー",
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
    print(f"🎯 AI評価対象スレッド数: {len(target_threads):,} スレッド")
    print(f"⚡ 並列ワーカー数: {MAX_WORKERS} スレッド並行処理 (gemini-3.5-flash-lite)")
    print("==================================================")

    # 3. チェックポイントの読み込み
    eval_cache = {}
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                eval_cache = json.load(f)
            print(f"🔄 チェックポイント検出: 評価済み {len(eval_cache):,} 件をスキップして再開します。")
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
    print(f"\n🎉 全スレッドの並列評価が完了しました！（所要時間: {elapsed//60}分{elapsed%60}秒）")

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
                        stmt_dict[rel_key]["analysis"] = {
                            "is_evaluated": False,
                            "reasoning": "スレッド内の関連発言（代表発言に統合評価済み）",
                            "scores": {"evidence": 0, "solution": 0, "local_focus": 0, "constructive": 0},
                            "category": "質疑外発言（統合済み）"
                        }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(statements, f, ensure_ascii=False, indent=2)

    print(f"💾 最終ファイル出力完了: {output_file}")
    print("==================================================")

if __name__ == "__main__":
    main()