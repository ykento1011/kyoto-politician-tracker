import json
import time
import os
import re
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# .env からAPIキーを安全に読み込み
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel('gemini-2.5-flash')

# 京都市会議員の実質的な発言者IDセット（行政職員・理事者を完全に排除した74件）
COUNCILOR_SPEAKER_IDS = {
    "113805", "113806", "1255938", "1255960", "1255979",
    "5311835", "5311838", "5311842", "5311853", "5311854",
    "5311855", "5311856", "5311857", "5311858", "5311859",
    "5311860", "5311861", "5311862", "5311863", "5311864",
    "5311865", "5311866", "5312839", "5312845", "5312846",
    "5312851", "5312853", "5312856", "5312858", "5312859",
    "5312860", "5312861", "5312862", "5312863", "5312865",
    "5312866", "5312867", "5312868", "5312869", "5312870",
    "5312871", "5312873", "5312877", "5312881", "5313038",
    "5313059", "5313864", "5313961", "5314690", "5314900",
    "5314926", "5314945", "5314953", "5314959", "5314967",
    "5315171", "5315402", "5315405", "5315415", "5315626",
    "5315885", "5315886", "5315923", "5315925", "5315936",
    "5316067", "5316434", "5316436", "5316437", "5316438",
    "5316439", "5316440", "5316441", "5316501"
}

def is_obvious_procedural(text, speaker_id=None):
    """
    議事録特有の定型文および発言者属性を検知し、APIを叩く前にローカルで瞬時に弾く強力なフィルター
    """
    # 1. 議員マスターデータに存在しないID（行政側の局長・副市長など）は100%カット
    if speaker_id and str(speaker_id) not in COUNCILOR_SPEAKER_IDS:
        return True

    # 改行を削除して1行の文字列として評価しやすくする
    clean_text = text.replace('\n', '').strip()

    # 2. 極端に短い発言（50文字未満）は、実質的な政策提案になり得ないため一律カット
    if len(clean_text) < 50:
        return True

    # 3. 会派の指名・呼び込み（例: "〇〇議員団。", "無所属の〇〇委員。" など）
    if re.fullmatch(r"^(?:無所属の)?[^\s]{1,10}(?:議員団|委員|議員)の?。?$", clean_text):
        return True

    # 4. 会派の賛否態度表明フォーマット（議事録特有の言い回しを捕捉）
    stance_pattern = r"(?:慎重に)?(?:審議|検討)(?:いたしました|した)結果.*(?:賛成|反対|承認)(?:します|いたします|します。|いたします。)$"
    if re.search(stance_pattern, clean_text) and len(clean_text) < 200:
        return True

    # 5. 委員長・進行役の定型アクション（結びの言葉）
    procedural_endings = [
        r"開会いたします。?$",
        r"散会いたします。?$",
        r"閉会いたします。?$",
        r"討論結了いたします。?$",
        r"御異議(?:ありませんか|ございませんか)。?$",
        r"異議なしと認め(?:ます|、そのように決定いたします)。?$",
        r"表決に付します。?$",
        r"表決を採ります。?$",
        r"お諮り(?:いた)?します。?$",
        r"御一任(?:願いたいと|いただきたいと)思います.*$"
    ]
    for pattern in procedural_endings:
        if re.search(pattern, clean_text):
            return True

    # 6. その他の完全一致ノイズ
    noise_exact_matches = [
        "（「異議なし」と呼ぶ者あり）",
        "多数であります。",
        "少数であります。",
        "お聞き及びのとおりであります。"
    ]
    for noise in noise_exact_matches:
        if noise in clean_text:
            return True

    # 7. その他のよくある事務連絡パターン
    if "委員長報告は省略されます" in clean_text or "委員長報告は口述されます" in clean_text:
        return True
    if clean_text.endswith("提出願うことといたしますので、よろしくお願いいたします。"):
        return True

    # すべてのフィルターをすり抜けたものだけが「実質的な発言の可能性あり」としてGeminiへ
    return False

def analyze_text_with_gemini(speaker, text, speaker_id=None):
    """
    1. Pythonの事前フィルターで明らかな議事進行や行政職員を弾く。
    2. フィルターを抜けたものをGeminiに送り、最終的な性質判定と採点を行わせる。
    """
    # 事前フィルターによる足切り
    if is_obvious_procedural(text, speaker_id):
        return {
            "category": "事務・進行",
            "summary": text.strip().replace("\n", " ")[:80] + ("..." if len(text) > 80 else ""),
            "keywords": ["議事進行"],
            "scores": {"evidence": 0, "solution": 0, "local_focus": 0, "constructive": 0, "total_quality": 0},
            "is_evaluated": False,
            "reasoning": "行政側の発言、定型的な開会・進行、または採決態度表明のためAI評価前にローカルで除外"
        }

    prompt = f"""
    あなたは自治体議会の「質疑の質」を客観的に監査する中立な政策アナリストです。
    以下の発言を分析し、JSON形式で出力してください。

    【発言者】: {speaker}
    【発言内容】:
    {text}

    【ステップ1：発言の性質判定】
    この発言が「実質的な政策質疑・提案を行っている【議員】の発言」であるか、
    それとも「議事進行・手続き・会派の賛否表明・【行政側（市長・副市長・局長・部長・室長等）の答弁】」であるかを判断してください。

    ※ 以下のものはすべて「事務・進行」とみなし、評価対象外（is_evaluated: false）としてください：
      1. 委員長や進行役による進行、日程調整、役員選出
      2. 会派としての「〜に賛成/反対します」という態度の表明のみ
      3. 市長・副市長・局長・部長・室長などの【行政側職員による答弁・解説・報告】
         （例: 「〜に関してでございます」「我々、公営企業でございます」「お答えいたします」等）

    もし上記に該当する場合、出力するJSONは以下のようにし、スコアはすべて0にしてください。
    {{
      "category": "事務・進行",
      "summary": "発言内容の簡単な要約（50文字以内）",
      "keywords": ["議事進行"],
      "scores": {{"evidence": 0, "solution": 0, "local_focus": 0, "constructive": 0, "total_quality": 0}},
      "is_evaluated": false,
      "reasoning": "この発言は行政側の答弁（または議事進行・賛否表明）であり、議員による政策質疑・提案ではないため評価対象外とした。"
    }}

    【ステップ2：実質的な質疑の場合の採点】
    もし「実質的な政策質疑・提案」である場合は、以下の基準（各1〜5点）で厳格に採点してください。
    1. evidence: 主観(1) → ニュース・一般論(3) → 統計・法規・他都市事例の明示(5)
    2. solution: 批判・要望のみ(1) → 原因分析(3) → 具体的制度設計・代替案(5)
    3. local_focus: 抽象的国政論(1) → 京都市全般(3) → 特定地域・現場の具体的課題(5)
    4. constructive: 一方的反発(1) → 行政の現状理解(3) → 合意形成・次の一歩の提起(5)

    【総合スコア: total_quality (0〜100点)】
    上記4要素を総合し、発言が「市政の前進にどれだけ寄与する密度の高い質疑か」を100点満点で算出してください。

    実質的質疑の場合のJSON出力は以下のようにしてください。
    {{
      "category": "該当する政策分野（例: 都市計画, 福祉・医療, 子育て・教育, 財政・行革など）",
      "summary": "政策提案の要約（100字以内）",
      "keywords": ["キーワード1", "キーワード2", "キーワード3"],
      "scores": {{
        "evidence": 1〜5の整数,
        "solution": 1〜5の整数,
        "local_focus": 1〜5の整数,
        "constructive": 1〜5の整数,
        "total_quality": 0〜100の整数
      }},
      "is_evaluated": true,
      "reasoning": "採点理由を100字程度で具体的に記述"
    }}
    ※出力はJSONのみとし、Markdown表記は含めないでください。
    """

    try:
        response = model.generate_content(
            prompt,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            },
            generation_config={"temperature": 0.1}
        )
        raw_output = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(raw_output)
    except Exception as e:
        print(f"  ⚠️ 解析エラー ({speaker}): {e}")
        return {
            "category": "解析エラー",
            "summary": "解析失敗",
            "keywords": [],
            "scores": {"evidence": 0, "solution": 0, "local_focus": 0, "constructive": 0, "total_quality": 0},
            "is_evaluated": False,
            "reasoning": f"APIエラー: {str(e)}"
        }

def main():
    input_file = "sagebase_crawled_data.json"
    output_file = "analyzed_kyoto_politicians.json"

    with open(input_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    target_records = records

    print(f"⚖️ 本番解析開始: 全 {len(target_records)} 件を解析中...")
    
    # 進行状況のトラッキング用
    skipped_count = 0
    evaluated_count = 0

    analyzed_records = []
    for idx, row in enumerate(target_records, 1):
        speaker = row.get("speaker", "不明")
        speaker_id = row.get("speaker_id", None)
        text = row.get("statement_text", "")
        
        result = analyze_text_with_gemini(speaker, text, speaker_id)
        row["analysis"] = result
        analyzed_records.append(row)
        
        # コンソールログの出力とスリープ制御（わかりやすく色分け）
        if result.get("is_evaluated", False):
            evaluated_count += 1
            print(f"[{idx}/{len(target_records)}] 🎯 採点完了: {speaker} ({result['scores']['total_quality']}点)")
            time.sleep(1.5)  # APIを叩いて実質的発言だった場合のみウェイト
        else:
            skipped_count += 1
            reason = result.get("reasoning", "")
            if "ローカルで除外" in reason:
                 print(f"[{idx}/{len(target_records)}] ⏩ スキップ(Local): {speaker}")
            else:
                 print(f"[{idx}/{len(target_records)}] 🤖 スキップ(AI判定): {speaker}")

        # 10件ごとに中間保存（万が一途中で落ちても大丈夫なように）
        if idx % 10 == 0:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(analyzed_records, f, indent=2, ensure_ascii=False)

    # 最終保存
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analyzed_records, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 全件解析完了！ {output_file} に結果を出力しました。")
    print(f"📊 最終結果: 実質的質疑 {evaluated_count}件 / 議事進行等でスキップ {skipped_count}件")

if __name__ == "__main__":
    main()