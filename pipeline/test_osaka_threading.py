import json, os, sys, re
from pathlib import Path
import google.generativeai as genai
from google.cloud import bigquery
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / "data-pipeline" / ".env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.5-flash-lite")

OFFICIAL_ROLES = ["市長", "副市長", "局長", "区長", "部長", "室長", "課長", "次長", "理事者", "教育長", "技監", "参事", "主査", "担当部長", "担当課長"]

def is_official(speaker):
    return any(role in speaker for role in OFFICIAL_ROLES)

def build_osaka_threads(stmts):
    threads = []
    current_thread = None
    chair_name = stmts[0]["speaker"] if stmts else ""

    for s in stmts:
        spk = (s["speaker"] or "").strip()
        text = (s["statement_text"] or "").strip()

        # 委員長発言、短すぎる手続き発言、陳情・議案の一括説明はスキップ
        if spk == chair_name or "委員長" in spk:
            continue
        if len(text) < 15 and ("異議なし" in text or "お願いいたします" in text):
            continue
        if "陳情書" in text and "見解を申し上げます" in text:
            continue
        if "案件につきまして御説明申し上げます" in text:
            continue

        # 答弁者か質問者かを判定
        if is_official(spk) or text.startswith(("お答えいたします", "お答えします")):
            if current_thread is not None:
                current_thread["context_log"].append(f"【行政側 ({spk})】\n{text}")
                current_thread["has_response"] = True
        else:
            # 議員側の質問
            if current_thread is None or current_thread["speaker"] != spk:
                if current_thread is not None and current_thread["has_response"]:
                    threads.append(current_thread)
                current_thread = {
                    "speaker": spk,
                    "meeting_id": s["meeting_id"],
                    "meeting_title": s["meeting_title"],
                    "meeting_date": s["meeting_date"],
                    "context_log": [f"【議員 ({spk})】\n{text}"],
                    "has_response": False
                }
            else:
                # 同一議員の再質問
                current_thread["context_log"].append(f"【議員・再質問 ({spk})】\n{text}")

    if current_thread is not None and current_thread["has_response"]:
        threads.append(current_thread)

    return threads

def main():
    print("📥 会議 ID: 5336593 の発言を抽出中...")
    client = bigquery.Client(project="gen-lang-client-0253904061")
    q = """
        SELECT c.sequence_number, c.speaker_name AS speaker, c.comment AS statement_text,
               '5336593' AS meeting_id, '常任委員会（都市経済）' AS meeting_title, '2026-05-20' AS meeting_date
        FROM `gen-lang-client-0253904061.sagebase_data.conversations` c
        JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON c.minutes_id = min.id
        WHERE min.meeting_id = 5336593
        ORDER BY c.sequence_number ASC
    """
    stmts = [dict(r) for r in client.query(q).result()]
    print(f"生の発言数: {len(stmts)} 件")

    threads = build_osaka_threads(stmts)
    print(f"✨ 構築された実質質疑スレッド数: {len(threads)} 件")
    print("=" * 60)

    for i, th in enumerate(threads):
        spk = th["speaker"]
        convo = "\n\n".join(th["context_log"])
        print(f"\n🔍 スレッド [{i+1}/{len(threads)}] - {spk} 議員 (発言数: {len(th['context_log'])})")
        
        prompt = f"""
あなたは地方議会の政策質疑データを構造化・整理するCivic Tech分析AIです。
以下の質疑スレッドを4つの分析軸（各0〜5点）で整理し、客観的事実のみをJSON形式で出力してください。

【4軸の分析基準】
1. evidence (0-5: 根拠・データ): 客観的データ、過去実績、他都市事例等の提示度合い。
2. solution (0-5: 対案・是正策): 具体的な改善策、制度設計の提案度合い。
3. local_focus (0-5: 地域解像度): 特定の地域、施設、現場の具体名の提示度合い。
4. constructive (0-5: 質疑の展開): 答弁を踏まえた掘り下げ、論点絞り込みの度合い。

【質疑スレッド】
{convo[:8000]}

出力スキーマ:
{{
  "category": "カテゴリ名",
  "summary": "要旨",
  "keywords": ["キーワード"],
  "scores": {{"evidence": 0, "solution": 0, "local_focus": 0, "constructive": 0}},
  "reasoning": "事実ベースの分析メモ"
}}
"""
        res = model.generate_content(prompt, generation_config=genai.GenerationConfig(response_mime_type="application/json", temperature=0.0))
        result = json.loads(res.text)
        if isinstance(result, list): result = result[0]
        print(f"👉 要旨: {result.get('summary')}")
        print(f"👉 スコア: {result.get('scores')}")
        print(f"👉 メモ: {result.get('reasoning')}")

if __name__ == "__main__":
    main()
