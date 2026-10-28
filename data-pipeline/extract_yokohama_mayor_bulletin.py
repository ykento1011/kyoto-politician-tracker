import os
import sys
import urllib.request
from pathlib import Path
from google import genai

# 環境変数の読み込み (.env から GEMINI_API_KEY を取得)
env_path = Path(".env")
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip("'").strip('"')

pdf_url = "https://www.city.yokohama.lg.jp/city-info/senkyo/data/mayor/20261018kohosya_koho.files/R08_kouhou.pdf"
pdf_path = Path("data-pipeline/bulletins/yokohama_mayor_2026.pdf")
pdf_path.parent.mkdir(parents=True, exist_ok=True)

print(f"📥 選挙公報PDFをダウンロード中...\n   URL: {pdf_url}")
try:
    req = urllib.request.Request(pdf_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(pdf_path, 'wb') as out_file:
        out_file.write(response.read())
    print("✅ ダウンロード完了")
except Exception as e:
    print(f"❌ PDFのダウンロードに失敗しました。URLが有効か確認してください: {e}")
    sys.exit(1)

print("🤖 Gemini にPDFをアップロードし、物理テキスト抽出を実行中...")
client = genai.Client()

try:
    uploaded_file = client.files.upload(file=str(pdf_path))
    
    prompt = """
    【厳格なSOP指示：ハルシネーションの絶対禁止】
    あなたは選挙公報の物理的OCR・文字起こしを行うオペレーターです。推測や要約、補完は絶対に禁止です。
    提供された横浜市長選挙公報PDFの中に「原澤敦美（はらさわ あつみ）」候補の枠があります。
    その紙面に物理的に印刷されている【公約・政策部分のテキスト】を、一言一句違わずに正確に抽出してください。
    - 見出しがある場合は「■ 見出し」のようにプレーンテキストで箇条書きにしてください。
    - 長文ではなく、実際の公報紙面にある通りの文字数・文面のみを出力してください。
    - 紙面に記載がない政策は絶対に出力しないでください。
    """
    
    response = client.models.generate_content(
        model='gemini-1.5-pro',
        contents=[uploaded_file, prompt]
    )
    
    out_txt = Path("data-pipeline/yokohama_mayor_raw_ocr.txt")
    out_txt.write_text(response.text, encoding="utf-8")
    
    print("\n" + "=" * 60)
    print("📝 抽出結果（目視照合用プレビュー）")
    print("=" * 60)
    print(response.text)
    print("=" * 60)
    print(f"✅ 抽出テキストを {out_txt.as_posix()} に保存しました。")
    print("SOP Phase 2-5 に則り、この内容が紙面と完全に一致しているか目視で確認してください。")

except Exception as e:
    print(f"❌ Gemini抽出エラー: {e}")
