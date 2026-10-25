import json, os, sys, random
from pathlib import Path
import google.generativeai as genai
from google.cloud import bigquery
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
from core.cleaner import StatementCleaner
from core.thread_builder import ThreadBuilder

load_dotenv(PROJECT_ROOT / "data-pipeline" / ".env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.5-flash-lite")

def main():
    print("📥 データを抽出中... (直近20会議)")
    client = bigquery.Client(project="gen-lang-client-0253904061")
    q_meetings = """
        SELECT m.id, m.name, m.date FROM `gen-lang-client-0253904061.sagebase_data.meetings` m
        JOIN `gen-lang-client-0253904061.sagebase_data.conferences` conf ON m.conference_id = conf.id
        WHERE conf.governing_body_id = 532 AND m.name LIKE '%常任委員会%'
        ORDER BY m.date DESC LIMIT 20
    """
    meetings = list(client.query(q_meetings).result())
    all_stmts = []
    for mtg in meetings:
        q_stmts = f"""
            SELECT c.sequence_number, c.speaker_name AS speaker, c.speaker_header, c.comment AS statement_text,
                   '{mtg.id}' AS meeting_id, '{mtg.name}' AS meeting_title, '{mtg.date}' AS meeting_date
            FROM `gen-lang-client-0253904061.sagebase_data.conversations` c
            JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON c.minutes_id = min.id
            WHERE min.meeting_id = {mtg.id} ORDER BY c.sequence_number ASC
        """
        all_stmts.extend([dict(r) for r in client.query(q_stmts).result()])
        
    with open(PROJECT_ROOT / "pipeline" / "config" / "cities" / "osaka.json", "r", encoding="utf-8") as f:
        osaka_cfg = json.load(f)
        
    cleaner = StatementCleaner(config=osaka_cfg)
    threads = ThreadBuilder(cleaner=cleaner, city_code="osaka").build_threads(all_stmts)
    
    # 質問が200文字以上の「実質的な質疑」に絞る
    target_threads = [th for th in threads if len(th["questioner"]["statement_text"]) > 200]
    
    print(f"✨ 200文字以上の実質的なQAスレッド候補数: {len(target_threads)} 件")
    print("="*60)
    
    if not target_threads:
        return

    # ランダムに3件抽出
    sample_threads = random.sample(target_threads, min(3, len(target_threads)))

    for i, th in enumerate(sample_threads):
        print(f"\n🔍 テスト評価 [{i+1}/3] - {th['questioner']['name']} 議員")
        print(f"質問冒頭: {th['questioner']['statement_text'][:60].replace(chr(10), ' ')}...")
        prompt = f"""
以下の質疑を4つの分析軸（各0〜5点）で整理し、客観的事実のみをJSON形式で出力してください。

【強制ルール（最重要）】
もしこのテキストが、議事進行や一方的な行政報告のみである場合、または「議員の質問内容と行政の答弁内容が全く噛み合っていない」場合は、すべてのスコアを強制的に `0` とし、カテゴリを「議事進行・エラー」としてください。

【質疑】
{th['questioner']['statement_text'][:2000]}
【答弁】
{th['respondent']['statement_text'][:2000]}

スキーマ: {{"category":"","summary":"","keywords":[],"scores":{{"evidence":0,"solution":0,"local_focus":0,"constructive":0}},"reasoning":""}}
"""
        res = model.generate_content(prompt, generation_config=genai.GenerationConfig(response_mime_type="application/json", temperature=0.0))
        
        try:
            result = json.loads(res.text)
            if isinstance(result, list): result = result[0]
            print(f"👉 カテゴリ: {result.get('category')}")
            print(f"👉 スコア: {result.get('scores')}")
            print(f"👉 メモ: {result.get('reasoning')}")
        except Exception as e:
            print(f"⚠️ JSONエラー: {e}")

if __name__ == "__main__":
    main()
