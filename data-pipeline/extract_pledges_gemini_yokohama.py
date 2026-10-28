import os
import sys
import json
import time
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR.parent
BULLETINS_DIR = BASE_DIR / "bulletins"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON = DATA_DIR / "yokohama_mayor_pledges.json"
ENV_PATH = BASE_DIR / ".env"

# APIキー読み込み
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("GEMINI_API_KEY="):
            os.environ["GEMINI_API_KEY"] = line.split("=", 1)[1].strip().strip("'\"")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY が見つかりません。")
    sys.exit(1)

client = genai.Client(api_key=api_key)
# 名古屋版で稼働実績のある 2.5-flash を指定
MODEL_NAME = "gemini-2.5-flash"

class CouncilorPledgeItem(BaseModel):
    id: str = Field(description="公約ID (例: pledge_childcare, pledge_transport, etc.)")
    category: str = Field(description="8大分野 (子育て・教育, 福祉・医療・健康, 都市再生・交通インフラ, 産業・観光・地域経済, 財政・行革, くらし・環境・エネルギー, 防災・減災・治安, 文化・景観・歴史)")
    target_issue: str = Field(description="対象テーマ")
    stance: str = Field(description="スタンス (推進・拡充, 反対・見直し, 制度維持, 負担軽減, etc.)")
    headline: str = Field(description="政策主張の25字以内要約見出し")
    exact_quote: str = Field(description="公報原本の掲載枠に実際に印刷されている文字テキストそのままの正確な引用")

class CandidatePledgeExtraction(BaseModel):
    speaker: str = Field(description="候補者名")
    pledges: List[CouncilorPledgeItem] = Field(description="看板公約・重点政策リスト")

class BulletinPledgesResult(BaseModel):
    candidates: List[CandidatePledgeExtraction] = Field(description="公報PDF内に掲載されている全候補者リスト")

def process_pdf(pdf_path: Path) -> List[dict]:
    print(f"\n==================================================")
    print(f"📄 公報PDF解析中: {pdf_path.name}")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    print(f"⚡ PDF読み込み完了 ({len(pdf_bytes) / 1024:.1f} KB)。Gemini 2.5 解析中...")

    prompt = """あなたは地方選挙公報の政策監査を行う客観的なデータアナリストです。
添付されたPDFは、横浜市長選挙の公式選挙公報原本です。
紙面に掲載されている全候補者の情報を抽出し、各候補者の「看板公約・重点政策」を客観的・中立的に構造化してください。
【厳格な要件】
1. exact_quote は、紙面の該当枠に実際に印刷されている文字テキストをそのまま抜き出すこと（要約や推測・補完は不可）。
2. 紙面に記載がない政策は出力しないこと。
"""
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[pdf_part, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=BulletinPledgesResult,
                    temperature=0.1,
                )
            )
            parsed: BulletinPledgesResult = response.parsed
            break
        except Exception as e:
            print(f"  ⚠️ 解析試行 {attempt + 1} 失敗: {e}")
            time.sleep(3)
    else:
        print(f"  ❌ 解析に失敗しました。")
        return []

    results = []
    for cand in parsed.candidates:
        cand_data = {
            "speaker": cand.speaker,
            "pledges": [p.model_dump() for p in cand.pledges]
        }
        results.append(cand_data)
        
        print(f"  ✅ 候補者: {cand.speaker} - 公約数: {len(cand.pledges)}")
        for p in cand.pledges:
            print(f"     ・[{p.category}] {p.headline}")

    return results

def main():
    pdf_path = Path("bulletins/yokohama_mayor_2026.pdf")
    if not pdf_path.exists():
        print(f"❌ PDFファイルが見つかりません: {pdf_path}")
        return

    res_list = process_pdf(pdf_path)
    if res_list:
        OUTPUT_JSON.write_text(json.dumps(res_list, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"💾 結果を保存: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
