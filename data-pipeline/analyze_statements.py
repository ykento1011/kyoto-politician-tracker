import json
import time
import os
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ==========================================
# 1. Gemini APIの設定
# ==========================================
# ※ここに御自身のAPIキーを入力してください
API_KEY = "AQ.Ab8RN6I41kyH0zQHCCF1ruLVEezphzVPWKqP3Wgud0zo-xKNzw"
genai.configure(api_key=API_KEY)

# 最新の高速・高精度モデルを使用
model = genai.GenerativeModel('gemini-2.5-flash')

def analyze_text_with_gemini(speaker, text):
    """
    Geminiに発言テキストを渡し、政策トピックと要約をJSON形式で抽出させる
    """
    # 事務的な短い発言（「おはようございます」「～委員、どうぞ」等）は解析をスキップして節約
    if len(text) < 100:
        return {"category": "事務・挨拶", "summary": text.strip(), "keywords": []}

    prompt = f"""
    あなたは優秀な政治ジャーナリストです。以下の地方議会での議員（または行政側）の発言を分析し、指定されたJSONフォーマットで厳密に出力してください。
    
    【発言者】: {speaker}
    【発言内容】:
    {text}
    
    【出力JSONフォーマット】
    {{
      "category": "政策カテゴリ（例: 都市計画, 観光対策, 福祉, 交通, 教育, その他）から最も適切なものを1つ",
      "summary": "発言の核心となる主張や質問の意図を100文字以内で要約",
      "keywords": ["キーワード1", "キーワード2", "キーワード3"]
    }}
    
    ※出力は必ずJSONオブジェクトのみとし、Markdownの装飾（```jsonなど）は一切含めないでください。
    """
    
    try:
        response = model.generate_content(
            prompt,
            # セキュリティフィルターの誤検知を防ぐための設定
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            },
            generation_config={"temperature": 0.1} # 安定した回答を得るために温度を下げる
        )
        
        # 不要なMarkdownを取り除いてJSONとしてパース
        raw_output = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(raw_output)
        
    except Exception as e:
        print(f"  ⚠️ Gemini APIエラー ({speaker}): {e}")
        return {"category": "解析エラー", "summary": "解析に失敗しました", "keywords": []}

def main():
    input_file = "sagebase_crawled_data.json"
    output_file = "analyzed_kyoto_politicians.json"

    # データの読み込み
    with open(input_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"📊 {len(records)} 件のデータをGeminiでフル解析します...")
    
    analyzed_records = []
    
    # 1000件すべてを解析するループ
    for idx, row in enumerate(records, 1):
        print(f"[{idx}/{len(records)}] 解析中: {row['speaker']} の発言...")
        
        # Gemini APIを呼び出し
        analysis_result = analyze_text_with_gemini(row["speaker"], row["statement_text"])
        
        # 元のデータに解析結果を結合
        row["analysis"] = analysis_result
        analyzed_records.append(row)
        
        # レートリミット（APIの連続リクエスト制限）対策の待機 (2秒)
        time.sleep(2)

    # 結果を保存
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analyzed_records, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 フル解析完了！ 結果を {output_file} に保存しました。")

if __name__ == "__main__":
    main()