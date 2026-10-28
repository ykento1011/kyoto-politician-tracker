import os
import sys
import argparse
import urllib.request
from pathlib import Path
from google import genai

def load_env():
    env_path = Path("../.env") if Path("../.env").exists() else Path(".env")
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip("'").strip('"')

def main():
    parser = argparse.ArgumentParser(description="統一選挙公報PDF 物理テキスト抽出スクリプト (SOP準拠)")
    parser.add_argument("--city", required=True, help="都市コード (例: yokohama, kyoto, osaka)")
    parser.add_argument("--pdf", required=True, help="PDFのURL または ローカルファイルパス")
    parser.add_argument("--candidate", required=True, help="抽出対象の候補者名 (例: 原澤敦美)")
    args = parser.parse_args()

    load_env()
    
    bulletins_dir = Path("bulletins")
    bulletins_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_path = Path(args.pdf)
    
    # URL指定の場合はダウンロード
    if args.pdf.startswith("http://") or args.pdf.startswith("https://"):
        print(f"📥 {args.city} の選挙公報PDFをダウンロード中...\n   URL: {args.pdf}")
        pdf_path = bulletins_dir / f"{args.city}_bulletin_temp.pdf"
        try:
            req = urllib.request.Request(args.pdf, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(pdf_path, 'wb') as out_file:
                out_file.write(response.read())
            print("✅ ダウンロード完了")
        except Exception as e:
            print(f"❌ PDFのダウンロードに失敗しました: {e}")
            print("👉 対策: PDFをブラウザで手動ダウンロードし、ローカルパスを指定して再実行してください。")
            sys.exit(1)
    else:
        if not pdf_path.exists():
            print(f"❌ 指定されたローカルファイルが存在しません: {pdf_path}")
            sys.exit(1)
        print(f"📄 ローカルPDFを使用します: {pdf_path}")

    print(f"🤖 Gemini Vision OCR を起動中... (対象候補者: {args.candidate})")
    client = genai.Client()

    try:
        uploaded_file = client.files.upload(file=str(pdf_path))
        
        prompt = f"""
        【厳格なSOP指示：ハルシネーションの絶対禁止】
        あなたは選挙公報の物理的OCR・文字起こしを行うオペレーターです。推測や要約、文脈の補完は絶対に禁止です。
        提供された選挙公報PDFの中に「{args.candidate}」候補の枠があります。
        その紙面に物理的に印刷されている【公約・政策部分のテキスト】を、一言一句違わずに正確に抽出してください。
        - 見出しがある場合は「■ 見出し」のようにプレーンテキストで箇条書きにしてください。
        - 実際の公報紙面にある通りの文字数・文面のみを出力してください。
        - {args.candidate}候補の記載がない、またはPDFが読み取れない場合は「【抽出不可】記載なし」とだけ出力してください。
        """
        
        response = client.models.generate_content(
            model='gemini-1.5-pro',
            contents=[uploaded_file, prompt]
        )
        
        out_txt = Path(f"{args.city}_{args.candidate}_raw_ocr.txt")
        out_txt.write_text(response.text, encoding="utf-8")
        
        print("\n" + "=" * 60)
        print(f"📝 抽出結果（{args.candidate} / 目視照合用プレビュー）")
        print("=" * 60)
        print(response.text.strip())
        print("=" * 60)
        print(f"✅ 抽出テキストを {out_txt.as_posix()} に保存しました。")
        print("【SOP Phase 2 準拠】この内容が実際の紙面と完全に一致しているか目視で確認してください。")

    except Exception as e:
        print(f"❌ Gemini抽出エラー: {e}")

if __name__ == "__main__":
    main()
