import os
import sys
import re
import json
import time
import urllib.request
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
ROOT = BASE_DIR.parent
BULLETINS_DIR = BASE_DIR / "bulletins_yokohama"
BULLETINS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON = DATA_DIR / "yokohama_councilor_pledges.json"
STATS_JSON = ROOT / "frontend" / "public" / "data" / "yokohama_speaker_stats.json"

ENV_PATH = BASE_DIR / ".env"
if not ENV_PATH.exists():
    ENV_PATH = ROOT / ".env"

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
MODEL_NAME = "gemini-2.5-flash"

class CouncilorPledgeItem(BaseModel):
    id: str = Field(description="公約ID (例: pledge_childcare, pledge_transport, pledge_fiscal, etc.)")
    category: str = Field(description="8大分野 (子育て・教育, 福祉・医療・健康, 都市再生・交通インフラ, 産業・観光・地域経済, 財政・行革, くらし・環境・エネルギー, 防災・減災・治安, 文化・景観・歴史)")
    target_issue: str = Field(description="対象テーマ")
    stance: str = Field(description="スタンス (推進・拡充, 反対・見直し, 制度維持, 負担軽減, etc.)")
    headline: str = Field(description="政策主張の25字以内要約見出し")
    exact_quote: str = Field(description="公報原本の該当枠に実際に印刷されている文字テキストそのままの正確な引用")

class CandidatePledgeExtraction(BaseModel):
    speaker: str = Field(description="候補者・議員名")
    district: str = Field(description="選挙区名")
    party: str = Field(description="所属党派・公認政党")
    pledges: List[CouncilorPledgeItem] = Field(description="看板公約・重点政策リスト（1〜すべて（件数制限なし））")

class BulletinPledgesResult(BaseModel):
    candidates: List[CandidatePledgeExtraction] = Field(description="全候補者リスト")

def load_yokohama_master():
    if not STATS_JSON.exists():
        print(f"❌ マスタファイルが見つかりません: {STATS_JSON}")
        sys.exit(1)
    stats = json.loads(STATS_JSON.read_text(encoding="utf-8"))
    mapping = {}
    for s in stats:
        name = s.get("speaker", "").strip()
        clean = name.replace(" ", "").replace(" ", "")
        mapping[clean] = s
        mapping[name] = s
    return mapping, stats

def download_pdf(url: str, save_path: Path):
    if save_path.exists() and save_path.stat().st_size > 1000:
        return True
    print(f"  📥 PDFダウンロード中: {url}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=30) as resp, open(save_path, "wb") as f:
            f.write(resp.read())
        return True
    except Exception as e:
        print(f"  ⚠️ ダウンロード失敗 ({e})。")
        return False

def process_district_pdf(district_name: str, pdf_url: str, master_map: dict) -> List[dict]:
    pdf_filename = pdf_url.split("/")[-1] if pdf_url else f"{district_name}.pdf"
    pdf_path = BULLETINS_DIR / pdf_filename

    if not download_pdf(pdf_url, pdf_path):
        return []

    print(f"\n==================================================")
    print(f"📄 【{district_name}】公報PDF解析中: {pdf_filename}")
    print(f"🔗 原本URL: {pdf_url}")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    print(f"⚡ PDF読み込み完了 ({len(pdf_bytes) / 1024:.1f} KB)。Gemini 2.5 解析中...")

    prompt = f"""あなたは地方選挙公報の政策監査を行う客観的なデータアナリストです。
添付されたPDFは、横浜市議会議員一般選挙（{district_name}）の公式選挙公報原本です。
紙面に掲載されている全候補者の情報を抽出し、各候補者が紙面で最も強調している「看板公約・重点政策（1〜すべて（件数制限なし））」を客観的・中立的に構造化してください。

【厳格な要件（SOP準拠・ハルシネーション絶対禁止）】
1. 候補者名（speaker）は、紙面に大きく掲げられている氏名（通称表記含む）を正確に記録すること。
2. 所属党派（party）を紙面から正確に特定すること。
3. exact_quote は、紙面の該当枠に実際に印刷されている文字テキストをそのまま抜き出すこと（要約や言い換え、推測は絶対不可）。
4. headline は、25字以内で中立的に要約すること。
"""

    parsed: Optional[BulletinPledgesResult] = None
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
            if response.parsed and hasattr(response.parsed, "candidates"):
                parsed = response.parsed
                break

            # parsed が None の場合の代替フォールバック解析
            if response.text:
                raw_text = response.text.strip()
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                json_str = match.group(0) if match else raw_text
                data = json.loads(json_str)
                parsed = BulletinPledgesResult.model_validate(data)
                if parsed and parsed.candidates:
                    break

            raise ValueError("有効な candidates 配列が取得できませんでした。")
        except Exception as e:
            print(f"  ⚠️ 解析試行 {attempt + 1} 失敗: {e}")
            time.sleep(3)

    if not parsed or not parsed.candidates:
        print(f"  ❌ {district_name} の解析に失敗しました。")
        return []

    results = []
    for cand in parsed.candidates:
        c_clean = cand.speaker.replace(" ", "").replace(" ", "")
        matched_stat = master_map.get(c_clean) or master_map.get(cand.speaker)

        if not matched_stat:
            for k, val in master_map.items():
                if len(k) >= 2 and (k in c_clean or c_clean in k):
                    matched_stat = val
                    break

        is_elected = matched_stat is not None
        elected_name = matched_stat.get("speaker") if matched_stat else cand.speaker

        cand_data = {
            "speaker": elected_name,
            "raw_name": cand.speaker,
            "district": district_name,
            "party": cand.party or (matched_stat.get("party") if matched_stat else ""),
            "is_incumbent_elected": is_elected,
            "bulletin_url": pdf_url,
            "pledges": [p.model_dump() for p in cand.pledges]
        }
        results.append(cand_data)

        status_tag = f"✅ 【現職市議】{elected_name}" if is_elected else f"ℹ️ 候補者: {cand.speaker}"
        print(f"  {status_tag} ({cand_data['party']}) - 公約数: {len(cand.pledges)}")
        for p in cand.pledges:
            print(f"     ・[{p.category}] {p.headline}")

    return results

def main():
    print("=" * 60)
    print("🚀 横浜市議選公報（全18区・86名）AI公約抽出パイプライン 再開")
    print("=" * 60)

    master_map, all_stats = load_yokohama_master()

    districts = {}
    for s in all_stats:
        d = s.get("district")
        url = s.get("bulletin_pdf_url")
        if d and url and d not in districts:
            districts[d] = url

    all_extracted = {}
    completed_districts = set()
    if OUTPUT_JSON.exists():
        try:
            cached = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
            for item in cached:
                all_extracted[item["raw_name"]] = item
                if item.get("district"):
                    completed_districts.add(item["district"])
            print(f"📦 既存キャッシュ読み込み: {len(all_extracted)} 名分 (完了済区: {len(completed_districts)} 区)")
        except Exception:
            pass

    for district_name, pdf_url in districts.items():
        if district_name in completed_districts:
            print(f"⏭️ 【{district_name}】は解析済みのためスキップします。")
            continue

        res_list = process_district_pdf(district_name, pdf_url, master_map)
        for r in res_list:
            all_extracted[r["raw_name"]] = r

        OUTPUT_JSON.write_text(json.dumps(list(all_extracted.values()), ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(1.5)

    print("\n" + "=" * 60)
    elected_matched = [c for c in all_extracted.values() if c.get("is_incumbent_elected")]
    print(f"🎉 抽出完了！ 総候補者数: {len(all_extracted)} 名")
    print(f"🎯 横浜市会 現職議員マッチング成功: {len(elected_matched)} / {len(all_stats)} 名")
    print(f"💾 結果を保存: {OUTPUT_JSON}")
    print("=" * 60)

if __name__ == "__main__":
    main()
