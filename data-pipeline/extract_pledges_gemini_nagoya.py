import os
import sys
import re
import json
import time
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
BULLETINS_DIR = BASE_DIR / "bulletins_nagoya"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON = DATA_DIR / "nagoya_councilor_pledges.json"
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
MODEL_NAME = "gemini-2.5-flash"

# WARP 公式アーカイブ公報ベースURL
BASE_OFFICIAL_URL = "https://warp.ndl.go.jp/20250211/20250205095834/www.city.nagoya.jp/senkyokanri/cmsfiles/contents/0000165/165666/"

class CouncilorPledgeItem(BaseModel):
    id: str = Field(description="公約ID (例: pledge_childcare, pledge_transport, pledge_fiscal, pledge_disaster, etc.)")
    category: str = Field(description="8大分野 (子育て・教育, 福祉・医療・健康, 都市再生・交通インフラ, 産業・観光・地域経済, 財政・行革, くらし・環境・エネルギー, 防災・減災・治安, 文化・景観・歴史)")
    target_issue: str = Field(description="対象テーマ (保育所整備, 給食無償化, 市バス・地下鉄維持, 名古屋城天守閣木造復元, 防災減災, 行革・減税, 高齢者支援, etc.)")
    stance: str = Field(description="スタンス (推進・拡充, 反対・見直し, 制度維持, 負担軽減, etc.)")
    headline: str = Field(description="政策主張の25字以内要約見出し")
    exact_quote: str = Field(description="公報原本の掲載枠に実際に印刷されている文字テキストそのままの正確な引用")

class CandidatePledgeExtraction(BaseModel):
    speaker: str = Field(description="候補者・議員名（漢字フルネーム、通称名があれば併記）")
    district: str = Field(description="選挙区名 (例: 千種区, 中区, etc.)")
    party: str = Field(description="所属党派・公認政党")
    pledges: List[CouncilorPledgeItem] = Field(description="看板公約・重点政策リスト（1〜すべて（件数制限なし）抽出すること）")

class BulletinPledgesResult(BaseModel):
    candidates: List[CandidatePledgeExtraction] = Field(description="公報PDF内に掲載されている全候補者リスト")

def load_nagoya_master():
    """名古屋市会議員マスタ（68名）の取得"""
    p_stat = ROOT / "frontend" / "public" / "data" / "nagoya_speaker_stats.json"
    if not p_stat.exists():
        return {}
    stats = json.loads(p_stat.read_text(encoding="utf-8"))
    mapping = {}
    for s in stats:
        name = s.get("speaker", "").strip()
        clean = name.replace(" ", "").replace(" ", "")
        mapping[clean] = s
        mapping[name] = s
    return mapping

def process_pdf(pdf_path: Path, master_map: dict) -> List[dict]:
    filename = pdf_path.name
    m = re.match(r"^(\d{2})_", filename)
    official_num = m.group(1) if m else "01"
    bulletin_url = f"{BASE_OFFICIAL_URL}{official_num}.pdf"

    print(f"\n==================================================")
    print(f"📄 公報PDF解析中: {filename}")
    print(f"🔗 原本URL: {bulletin_url}")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    print(f"⚡ PDF読み込み完了 ({len(pdf_bytes) / 1024:.1f} KB)。Gemini 2.5 解析中...")

    prompt = """あなたは地方選挙公報の政策監査を行う客観的なデータアナリストです。
添付されたPDFは、2023年4月9日執行「名古屋市議会議員一般選挙」の公式選挙公報原本です。

このPDFから、紙面に掲載されている全候補者の情報を抽出し、各候補者が紙面で最も強調している「看板公約・重点政策（1〜すべて（件数制限なし））」を客観的・中立的に構造化してください。

【厳格な要件】
1. 候補者名（speaker）は、紙面に大きく掲げられている氏名（通称表記含む）を正確に記録すること。
2. 所属党派（party）を紙面から正確に特定すること（自民、減税日本、公明、民主、共産、維新、無所属など）。
3. 看板公約（pledges）は、キャッチコピーやスローガンのみでなく、具体的な政策項目（例: 名古屋城木造復元、市民税減税、敬老パス拡充、学校給食無償化、防災対策、中小企業支援など）を抽出すること。
4. exact_quote は、紙面の該当枠に実際に印刷されている文字テキストをそのまま抜き出すこと（要約や言い換えは不可）。
5. headline は、有権者が一目でわかるように25字以内で中立的に要約すること。
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
        print(f"  ❌ {filename} の解析に失敗しました。")
        return []

    results = []
    for cand in parsed.candidates:
        c_clean = cand.speaker.replace(" ", "").replace(" ", "")
        # マスタ突き合わせ
        matched_stat = master_map.get(c_clean) or master_map.get(cand.speaker)
        
        # 部分一致の探索
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
            "district": cand.district or (matched_stat.get("district") if matched_stat else ""),
            "party": cand.party or (matched_stat.get("partyGroup") if matched_stat else ""),
            "is_incumbent_elected": is_elected,
            "bulletin_url": bulletin_url,
            "pledges": [p.model_dump() for p in cand.pledges]
        }
        results.append(cand_data)
        
        status_tag = f"✅ 【現職市議】{elected_name}" if is_elected else f"ℹ️ 候補者: {cand.speaker}"
        print(f"  {status_tag} ({cand_data['district']} / {cand_data['party']}) - 公約数: {len(cand.pledges)}")
        for p in cand.pledges:
            print(f"     ・[{p.category}] {p.headline} ({p.stance})")

    return results

def main():
    print("=" * 60)
    print("🚀 名古屋市議選公報（16区）AI公約抽出パイプライン 開始")
    print(f"📂 対象ディレクトリ: {BULLETINS_DIR}")
    print("=" * 60)

    master_map = load_nagoya_master()
    print(f"📋 名古屋市会議員マスタ: {len(set(s['speaker'] for s in master_map.values()))} 名")

    pdf_files = sorted(list(BULLETINS_DIR.glob("*.pdf")))
    if not pdf_files:
        print("❌ 解析対象のPDFファイルが見つかりません。")
        return

    # 既存データの読み込み（キャッシュ再開対応）
    all_extracted = {}
    if OUTPUT_JSON.exists():
        try:
            cached = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
            for item in cached:
                all_extracted[item["raw_name"]] = item
            print(f"📦 既存キャッシュ読み込み: {len(all_extracted)} 件の候補者データ")
        except Exception:
            pass

    for idx, pdf in enumerate(pdf_files, 1):
        # 該当PDFを処理
        res_list = process_pdf(pdf, master_map)
        for r in res_list:
            all_extracted[r["raw_name"]] = r
        
        # 各区ごとに中間保存
        OUTPUT_JSON.write_text(json.dumps(list(all_extracted.values()), ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(1.5)

    print("\n" + "=" * 60)
    elected_matched = [c for c in all_extracted.values() if c.get("is_incumbent_elected")]
    print(f"🎉 抽出完了！ 総候補者数: {len(all_extracted)} 名")
    print(f"🎯 名古屋市会 現職議員マッチング成功: {len(elected_matched)} / 68 名")
    print(f"💾 結果を保存: {OUTPUT_JSON}")
    print("=" * 60)

if __name__ == "__main__":
    main()