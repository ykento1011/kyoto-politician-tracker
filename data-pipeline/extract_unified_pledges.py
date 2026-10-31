import os
import sys
import json
import time
import argparse
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

CUR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR.parent
DATA_DIR = CUR / "data"
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"

for env_path in [CUR / ".env", PROJECT_ROOT / ".env"]:
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip("'\"")

CITY_CONFIGS = {
    "kobe": {
        "name": "神戸市",
        "election_name": "神戸市議会議員一般選挙",
        "pdf_dirs": [CUR / "raw_pdfs" / "kobe", CUR / "bulletins_kobe"],
        "base_url": "https://www.city.kobe.lg.jp/documents/23740/",
        "canonical_map": {}
    },

    "kyoto": {
        "name": "京都市",
        "election_name": "京都市議会議員一般選挙",
        "pdf_dirs": [CUR / "raw_pdfs" / "kyoto", CUR / "bulletins"],
        "base_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000313/313230/",
        "canonical_map": {"井﨑敦子": "井崎敦子", "繁隆夫": "繁隆夫", "繫隆夫": "繁隆夫"}
    },
    "osaka": {
        "name": "大阪市",
        "election_name": "大阪市議会議員一般選挙",
        "pdf_dirs": [CUR / "raw_pdfs" / "osaka", CUR / "bulletins_osaka"],
        "base_url": "https://www.city.osaka.lg.jp/contents/wdu010/senkyo/",
        "canonical_map": {}
    },
    "nagoya": {
        "name": "名古屋市",
        "election_name": "名古屋市議会議員一般選挙",
        "pdf_dirs": [CUR / "raw_pdfs" / "nagoya", CUR / "bulletins_nagoya"],
        "base_url": "https://warp.ndl.go.jp/20250211/20250205095834/www.city.nagoya.jp/senkyokanri/cmsfiles/contents/0000165/165666/",
        "canonical_map": {}
    },
    "yokohama": {
        "name": "横浜市",
        "election_name": "横浜市会一般選挙",
        "pdf_dirs": [CUR / "raw_pdfs" / "yokohama", CUR / "bulletins_yokohama"],
        "base_url": "https://www.city.yokohama.lg.jp/city-info/senkyo/data/",
        "canonical_map": {}
    }
}

class CouncilorPledgeItem(BaseModel):
    id: str = Field(description="公約ID")
    category: str = Field(description="8大分野")
    target_issue: str = Field(description="対象テーマ")
    stance: str = Field(description="スタンス")
    headline: str = Field(description="政策主張の要約見出し")
    exact_quote: str = Field(description="公報原本に印刷されている文字テキストそのままの正確な引用")

class CandidatePledgeExtraction(BaseModel):
    speaker: str = Field(description="候補者名")
    district: str = Field(description="選挙区名")
    party: str = Field(description="所属党派")
    pledges: List[CouncilorPledgeItem] = Field(description="重点政策・看板公約の全リスト")

class BulletinPledgesResult(BaseModel):
    candidates: List[CandidatePledgeExtraction] = Field(description="公報PDF内の全候補者")

def clean_name(name: str) -> str:
    return name.replace(" ", "").replace(" ", "")

def load_master_councilors(city: str) -> set:
    candidates = [
        FRONTEND_DATA / f"{city}_councilors.json",
        FRONTEND_DATA / f"{city}_statements_summary.json",
        FRONTEND_DATA / f"statements_summary_{city}.json",
        FRONTEND_DATA / "statements_summary.json" if city == "kyoto" else None
    ]
    for path in filter(None, candidates):
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return {clean_name(d.get("name") or d.get("speaker", "")) for d in data if (d.get("name") or d.get("speaker"))}
            except Exception:
                pass
    return set()

def normalize_name(raw_name: str, valid_names: set, canonical_map: dict) -> str:
    cleaned = clean_name(raw_name)
    if cleaned in canonical_map:
        cleaned = canonical_map[cleaned]
    if cleaned in valid_names:
        return cleaned
    for v in valid_names:
        if cleaned in v or v in cleaned:
            return v
    return cleaned

def parse_pdf(client: genai.Client, pdf_path: Path, city_cfg: dict, valid_names: set) -> List[dict]:
    filename = pdf_path.name
    bulletin_url = city_cfg["base_url"] + filename
    print(f"\n--- 解析中: {filename} ({city_cfg['name']}) ---")

    pdf_bytes = pdf_path.read_bytes()
    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")

    prompt = f"""
添付されたPDFは、公式の「{city_cfg['election_name']}」選挙公報原本です。
候補者が掲げている重点政策・看板公約を【上限なくすべて（全件）】抽出してください。
【最重要】「exact_quote」には、紙面に実際に印刷されている原文テキストを一言一句違わずそのまま抜き出してください。
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[pdf_part, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BulletinPledgesResult,
            temperature=0.0,
            max_output_tokens=16384,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        ),
    )

    result_json = json.loads(response.text)
    extracted = result_json.get("candidates", [])

    formatted = []
    for cand in extracted:
        norm_name = normalize_name(cand["speaker"], valid_names, city_cfg["canonical_map"])
        formatted.append({
            "speaker": norm_name,
            "raw_speaker": cand["speaker"],
            "district": cand.get("district", ""),
            "party": cand.get("party", ""),
            "bulletin_file": filename,
            "bulletin_pdf": bulletin_url,
            "pledges": cand.get("pledges", [])
        })
        print(f"  ✓ 抽出成功: {norm_name} ({cand.get('party', '')}) - 公約数: {len(cand.get('pledges', []))}件")
    return formatted

def main():
    parser = argparse.ArgumentParser(description="全都市統合公報PDF公約抽出パイプライン（差分キャッシュ対応）")
    parser.add_argument("--city", required=True, choices=list(CITY_CONFIGS.keys()))
    parser.add_argument("--file", help="特定PDFファイルのみ指定")
    parser.add_argument("--force", action="store_true", help="既存データを無視して全再取得")
    args = parser.parse_args()

    city = args.city
    cfg = CITY_CONFIGS[city]

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("[エラー] GEMINI_API_KEY が取得できません。")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    valid_names = load_master_councilors(city)

    target_dir = None
    for d in cfg["pdf_dirs"]:
        if d.exists() and list(d.glob("*.pdf")):
            target_dir = d
            break

    if not target_dir:
        print(f"[エラー] {cfg['name']} のPDFフォルダが見つかりません。")
        sys.exit(1)

    pdf_files = [target_dir / args.file] if args.file else sorted(list(target_dir.glob("*.pdf")))
    output_json = DATA_DIR / f"{city}_councilor_pledges.json"
    
    results_dict = {}
    processed_files = set()
    if output_json.exists():
        try:
            results_dict = json.loads(output_json.read_text(encoding="utf-8"))
            for spk_data in results_dict.values():
                b_pdf = spk_data.get("bulletin_pdf", "")
                if b_pdf:
                    processed_files.add(b_pdf.split("/")[-1].split("?")[0])
        except Exception:
            results_dict = {}

    print(f"[{cfg['name']}] PDF全件: {len(pdf_files)} 件 (うち抽出済: {len(processed_files)} 件)")

    for pdf_path in pdf_files:
        # 他都市の異物混入ファイルを自動除外
        if city != "yokohama" and "yokohama" in pdf_path.name.lower():
            print(f"🚫 他都市ファイルを除外: {pdf_path.name}")
            continue

        # 差分判定：すでに抽出済みのPDFはスキップ
        if not args.force and pdf_path.name in processed_files:
            print(f"⏭️ スキップ (抽出済): {pdf_path.name}")
            continue

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                candidates = parse_pdf(client, pdf_path, cfg, valid_names)
                for cand in candidates:
                    spk = cand["speaker"]
                    results_dict[spk] = {
                        "district": cand["district"],
                        "party": cand["party"],
                        "bulletin_pdf": cand["bulletin_pdf"],
                        "pledges": cand["pledges"]
                    }
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                output_json.write_text(json.dumps(results_dict, ensure_ascii=False, indent=2), encoding="utf-8")
                processed_files.add(pdf_path.name)
                time.sleep(2)
                break
            except Exception as e:
                print(f"[試行 {attempt}/{max_retries} 失敗] {pdf_path.name}: {e}")
                time.sleep(4)

    print(f"\n🎉 [{cfg['name']}] 看板公約抽出完了: {output_json} (登録議員数: {len(results_dict)} 名)")

if __name__ == "__main__":
    main()
