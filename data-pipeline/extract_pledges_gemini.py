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
BULLETINS_DIR = BASE_DIR / "bulletins"
DATA_DIR = BASE_DIR / "data"
OUTPUT_JSON = DATA_DIR / "councilor_pledges.json"
DATA_SUMMARY_PATH = BASE_DIR.parent / "frontend" / "public" / "data" / "statements_summary.json"
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip("'").strip('"')

BASE_URL = "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000313/313230/"

NAME_CANONICAL_MAP = {
    "井﨑敦子": "井崎敦子",
    "井﨑 敦子": "井崎敦子",
    "井崎 敦子": "井崎敦子",
    "繁隆夫": "繁隆夫",
    "繫隆夫": "繁隆夫",
    "繁 隆夫": "繁隆夫",
}

class CouncilorPledgeItem(BaseModel):
    id: str = Field(description="公約ID (例: pledge_childcare, pledge_tourism, pledge_fiscal, etc.)")
    category: str = Field(description="8大分野 (子育て・教育, 福祉・医療・健康, 都市再生・交通インフラ, 産業・観光・地域経済, 財政・行革, くらし・環境・エネルギー, 防災・減災・治安, 文化・景観・歴史)")
    target_issue: str = Field(description="対象テーマ (中学校給食, 子どもの医療費, 観光政策, 敬老乗車証, 行財政改革, 防災, 地場産業, 景観規制, etc.)")
    stance: str = Field(description="スタンス (推進・拡充, 反対・見直し, 制度維持, 負担軽減, etc.)")
    headline: str = Field(description="政策主張の25字以内要約見出し")
    exact_quote: str = Field(description="公報内の該当枠に実際に印刷されている文字テキストそのままの正確な引用")

class CandidatePledgeExtraction(BaseModel):
    speaker: str = Field(description="候補者・議員名（漢字フルネーム）")
    district: str = Field(description="選挙区名")
    party: str = Field(description="所属党派・公認政党")
    pledges: List[CouncilorPledgeItem] = Field(description="看板公約・重点政策リスト（記載されているものをすべて抽出すること）")

class BulletinPledgesResult(BaseModel):
    candidates: List[CandidatePledgeExtraction] = Field(description="公報PDF内に掲載されている全候補者リスト")

def load_target_councilors():
    if not DATA_SUMMARY_PATH.exists():
        return set()
    try:
        with open(DATA_SUMMARY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(d.get("speaker", "").replace(" ", "").replace(" ", "") for d in data)
    except Exception:
        return set()

def normalize_name(raw_name: str, valid_names: set) -> str:
    cleaned = raw_name.replace(" ", "").replace(" ", "")
    if cleaned in NAME_CANONICAL_MAP:
        cleaned = NAME_CANONICAL_MAP[cleaned]
    if cleaned in valid_names:
        return cleaned
    for v in valid_names:
        if cleaned in v or v in cleaned:
            return v
    return cleaned

def process_bulletin_pdf(client: genai.Client, pdf_path: Path, valid_names: set) -> List[dict]:
    filename = pdf_path.name
    bulletin_url = BASE_URL + filename
    print(f"\n--- 公報PDF解析中: {filename} ---")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    print(f"  PDF読み込み完了 ({len(pdf_bytes) / 1024:.1f} KB)。Gemini 2.5 解析中...")

    prompt = """
あなたは地方選挙公報の政策監査を行う客観的なデータアナリストです。
添付されたPDFは、2023年4月9日執行「京都市議会議員一般選挙」の公式選挙公報原本です。

【重要：抽出ルール（0件を撲滅し、全員からすべて抽出すること）】
1. PDF内の全候補者を漏れなく識別してください。
2. 候補者が掲げている政策を、以下の優先順位で【記載されているすべての項目を】抽出してください：
   - 【第1優先（具体的施策）】：数値や具体的な制度名を含む公約（例：北陸新幹線延伸中止、全員制中学校給食、子ども医療費無料化、敬老パス維持、議員定数削減、宿泊税など）。
   - 【第2優先（重点政策の柱）】：上記のような固有名詞がない候補者の場合、その候補者が「私の政策」「マニフェスト」「公約」「重点政策」として【番号付きや箇条書き】で掲げている政策項目（例：中野洋一氏の「子育て・教育の拡充」「市民生活第一の観光政策」など）を必ず抽出してください。
3. 【最重要】「exact_quote」には、公報内の該当枠に実際に印刷されている文字テキストを一切要約・改変せず、そのまま正確に抜き出してください。
4. 単なるあいさつ文だけで一切政策を掲げていない特異なケースを除き、原則として公約数を0件にしないでください。
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[pdf_part, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BulletinPledgesResult,
            temperature=0.0,
        ),
    )

    result_json = json.loads(response.text)
    extracted = result_json.get("candidates", [])
    
    formatted = []
    for cand in extracted:
        norm_name = normalize_name(cand["speaker"], valid_names)
        formatted.append({
            "speaker": norm_name,
            "raw_speaker": cand["speaker"],
            "district": cand["district"],
            "party": cand["party"],
            "bulletin_file": filename,
            "bulletin_pdf": bulletin_url,
            "pledges": cand["pledges"]
        })
        print(f"  ✓ 抽出成功: {norm_name} ({cand['party']}) - 看板公約: {len(cand['pledges'])}件")

    return formatted

def main():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("[エラー] GEMINI_API_KEY が取得できませんでした。data-pipeline/.env を確認してください。")
        return

    client = genai.Client(api_key=api_key)
    valid_names = load_target_councilors()
    print(f"現任期議員マスタ: {len(valid_names)} 名読み込み完了")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(list(BULLETINS_DIR.glob("*.pdf")))
    if not pdf_files:
        print(f"[エラー] {BULLETINS_DIR} にPDFが存在しません。")
        return

    councilor_pledges_dict = {}

    # 既存データで公約が0件だった議員を再抽出するため、0件のファイルは再解析する
    processed_files = set()
    if OUTPUT_JSON.exists():
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                councilor_pledges_dict = json.load(f)
            # 0件の公約が含まれるファイルは再実行対象から除外しない
            zero_speakers = [k for k, v in councilor_pledges_dict.items() if len(v.get("pledges", [])) == 0]
            print(f"既存の抽出結果: {len(councilor_pledges_dict)} 名 (うち公約0件: {len(zero_speakers)} 名)")
        except Exception:
            pass

    for pdf_path in pdf_files:
        # 0件の議員がいたファイル（03sakyo1, 03sakyo2, 05higashiyama, 07shimogyo, 11fushimi2, 11fushimi3）は必ず再抽出
        needs_reprocess = any(
            pdf_path.name in v.get("bulletin_pdf", "") and len(v.get("pledges", [])) == 0
            for v in councilor_pledges_dict.values()
        )
        if not needs_reprocess and pdf_path.name in processed_files:
            print(f"[スキップ] 正常抽出済み: {pdf_path.name}")
            continue

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                candidates = process_bulletin_pdf(client, pdf_path, valid_names)
                for cand in candidates:
                    spk = cand["speaker"]
                    councilor_pledges_dict[spk] = {
                        "district": cand["district"],
                        "party": cand["party"],
                        "bulletin_pdf": cand["bulletin_pdf"],
                        "pledges": cand["pledges"]
                    }
                
                with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                    json.dump(councilor_pledges_dict, f, ensure_ascii=False, indent=2)
                
                processed_files.add(pdf_path.name)
                time.sleep(2)
                break
            except Exception as e:
                print(f"[試行 {attempt}/{max_retries} 失敗] {pdf_path.name}: {e}")
                time.sleep(4)

    print(f"\n=== 看板公約抽出完了 ===")
    print(f"出力ファイル: {OUTPUT_JSON}")
    print(f"登録議員数: {len(councilor_pledges_dict)} 名")

if __name__ == "__main__":
    main()