import os
import sys
import json
import time
import re
from pathlib import Path
from typing import List, Optional
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
BULLETINS_DIR = BASE_DIR / "bulletins_osaka"
DATA_DIR = BASE_DIR / "data"
OUTPUT_JSON = DATA_DIR / "osaka_councilor_pledges.json"
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip("'").strip('"')

# 大阪市の公報公式PDFベースURL (01.pdf 〜 24.pdf)
BASE_OFFICIAL_URL = "https://www.city.osaka.lg.jp/contents/wdu240/shikai/kouhosha/"

class CouncilorPledgeItem(BaseModel):
    id: str = Field(description="公約ID (例: pledge_childcare, pledge_tourism, pledge_fiscal, pledge_disaster, etc.)")
    category: str = Field(description="8大分野 (子育て・教育, 福祉・医療・健康, 都市再生・交通インフラ, 産業・観光・地域経済, 財政・行革, くらし・環境・エネルギー, 防災・減災・治安, 文化・景観・歴史)")
    target_issue: str = Field(description="対象テーマ (保育無償化, 塾代助成, 児童虐待防止, 防犯カメラ, 万博・ベイエリア, DX行革, 高齢者福祉, 中小企業支援, etc.)")
    stance: str = Field(description="スタンス (推進・拡充, 反対・見直し, 制度維持, 負担軽減, etc.)")
    headline: str = Field(description="政策主張の25字以内要約見出し")
    exact_quote: str = Field(description="公報内の該当枠に実際に印刷されている文字テキストそのままの正確な引用")

class CandidatePledgeExtraction(BaseModel):
    speaker: str = Field(description="候補者・議員名（漢字フルネーム）")
    district: str = Field(description="選挙区名 (例: 北区, 住之江区, etc.)")
    party: str = Field(description="所属党派・公認政党")
    pledges: List[CouncilorPledgeItem] = Field(description="看板公約・重点政策リスト（必ず1〜3件抽出すること）")

class BulletinPledgesResult(BaseModel):
    candidates: List[CandidatePledgeExtraction] = Field(description="公報PDF内に掲載されている全候補者リスト")

def load_osaka_master_councilors():
    """大阪市議会議員マスタ（81名）の取得"""
    from build_pledge_tracker_osaka import COUNCILORS_MASTER
    name_map = {}
    for c in COUNCILORS_MASTER:
        clean = c["name"].replace(" ", "").replace(" ", "")
        name_map[clean] = c["name"]
        name_map[c["name"]] = c["name"]
        name_map[c["kana"]] = c["name"]
    return name_map

def process_bulletin_pdf(client: genai.Client, pdf_path: Path, master_map: dict) -> List[dict]:
    filename = pdf_path.name
    # 公式URL (01.pdf など) への変換
    m = re.match(r"^(\d{2})_", filename)
    official_num = m.group(1) if m else "01"
    bulletin_url = f"{BASE_OFFICIAL_URL}{official_num}.pdf"

    print(f"\n--- 公報PDF解析中: {filename} ---")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    print(f"  PDF読み込み完了 ({len(pdf_bytes) / 1024:.1f} KB)。Gemini 2.5 解析中...")

    prompt = """
あなたは地方選挙公報の政策監査を行う客観的なデータアナリストです。
添付されたPDFは、2023年4月9日執行「大阪市議会議員一般選挙」の公式選挙公報原本です。

【重要：抽出ルール（全候補者を識別し、必ず1〜3件の看板公約を抽出すること）】
1. PDF内の全候補者（枠）を漏れなく識別してください。
2. 候補者が掲げている政策を、以下の優先順位で【1人につき必ず1〜3件】抽出してください：
   - 【第1優先（具体的施策）】：数値や具体的な制度名を含む公約（例：0〜2歳児保育料無償化、塾代助成の所得制限撤廃、小中学校給食費無償化、淀川左岸線整備、書かない窓口・DX推進、児童虐待防止、防犯カメラ増設、敬老パス、身を切る改革など）。
   - 【第2優先（重点政策の柱）】：上記のような固有名詞がない場合、候補者が「私の政策」「マニフェスト」「公約」「重点政策」として【番号付きや箇条書き】で掲げている政策項目を必ず抽出してください。
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
        raw_name = cand["speaker"].replace(" ", "").replace(" ", "")
        # マスタに登録されている現職議員にヒットするか判定
        matched_canonical = master_map.get(raw_name)
        if not matched_canonical:
            # 部分一致判定
            for k, canonical in master_map.items():
                if k in raw_name or raw_name in k:
                    matched_canonical = canonical
                    break
        
        # 現職市議でない場合（落選候補者など）もデータとしては保持しつつログ出力
        display_name = matched_canonical if matched_canonical else cand["speaker"]
        is_current = bool(matched_canonical)

        formatted.append({
            "speaker": display_name,
            "raw_speaker": cand["speaker"],
            "is_current_councilor": is_current,
            "district": cand["district"],
            "party": cand["party"],
            "bulletin_file": filename,
            "bulletin_pdf": bulletin_url,
            "pledges": cand["pledges"]
        })
        status_mark = "✓ [現職市議]" if is_current else "○ [他候補者]"
        print(f"  {status_mark} {display_name} ({cand['party']}) - 看板公約: {len(cand['pledges'])}件")

    return formatted

def main():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("[エラー] GEMINI_API_KEY が取得できませんでした。data-pipeline/.env を確認してください。")
        return

    client = genai.Client(api_key=api_key)
    master_map = load_osaka_master_councilors()
    print(f"大阪市議会議員マスタ（現職）: {len(set(master_map.values()))} 名読み込み完了")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(list(BULLETINS_DIR.glob("*.pdf")))
    if not pdf_files:
        print(f"[エラー] {BULLETINS_DIR} にPDFが存在しません。")
        return

    councilor_pledges_dict = {}
    if OUTPUT_JSON.exists():
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                councilor_pledges_dict = json.load(f)
            print(f"既存の抽出結果: {len(councilor_pledges_dict)} 名分ロード完了")
        except Exception:
            pass

    # 既に抽出済みのファイルをチェック
    processed_files = set(
        v.get("bulletin_file") for v in councilor_pledges_dict.values() if v.get("bulletin_file")
    )

    for pdf_path in pdf_files:
        if pdf_path.name in processed_files:
            print(f"[スキップ] 抽出済み: {pdf_path.name}")
            continue

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                candidates = process_bulletin_pdf(client, pdf_path, master_map)
                for cand in candidates:
                    spk = cand["speaker"]
                    councilor_pledges_dict[spk] = {
                        "district": cand["district"],
                        "party": cand["party"],
                        "bulletin_file": cand["bulletin_file"],
                        "bulletin_pdf": cand["bulletin_pdf"],
                        "is_current_councilor": cand["is_current_councilor"],
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

    print(f"\n=== 大阪市議選 看板公約抽出完了 ===")
    print(f"出力ファイル: {OUTPUT_JSON}")
    print(f"登録者数: {len(councilor_pledges_dict)} 名")

if __name__ == "__main__":
    main()
