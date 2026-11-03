import json
import re
import unicodedata
import argparse
from pathlib import Path

CUR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR.parent
MASTER_DIR = CUR / "master"
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"
MAYORS_FILE = MASTER_DIR / "mayors.json"

KANJI_VARIANTS = str.maketrans({
    "髙": "高", "﨑": "崎", "繁": "繁", "齋": "斎", "齊": "斉",
    "邊": "辺", "邉": "辺", "栁": "柳", "德": "徳", "廣": "広",
    "櫻": "桜", "嶋": "島", "惠": "恵", "眞": "真", "冨": "富",
    "峰": "峯", "薮": "藪", "塚": "塚"
})

def normalize_name(t: str) -> str:
    t = unicodedata.normalize("NFKC", str(t or ""))
    t = re.sub(r"[\s ]+", "", t)
    return t.translate(KANJI_VARIANTS)

def sync_master_data(city: str):
    city = city.lower()
    master_file = MASTER_DIR / f"{city}_councilors.json"
    override_file = MASTER_DIR / f"manual_overrides_{city}.json"
    
    if not master_file.exists():
        print(f"❌ 正本マスターが存在しません: {master_file}")
        return

    # 1. マスター読み込み
    master_councilors = json.loads(master_file.read_text(encoding="utf-8-sig"))
    
    # 2. 手動オーバーライド層のマージ
    manual_overrides = {}
    if override_file.exists():
        try:
            manual_overrides = json.loads(override_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️ manual_overrides 読み込み失敗: {e}")
            
    print(f"=== [{city.upper()}] 正本マスター同期（登録: {len(master_councilors)} 名 / 手動オーバーライド: {len(manual_overrides)} 件） ===")

    valid_speaker_map = {}
    speaker_stats_dict = {}
    updated_master_list = []

    for c in master_councilors:
        name = c["name"]
        raw_clean = re.sub(r"[\s ]+", "", name)
        norm_n = normalize_name(name)
        
        # 手動オーバーライドの適用
        if name in manual_overrides or raw_clean in manual_overrides:
            ov = manual_overrides.get(name) or manual_overrides.get(raw_clean)
            c.update(ov)
            print(f"🔧 手動オーバーライド適用: {name} -> {ov}")
        
        is_active = c.get("is_active", True)
        entry = {
            "name": name,
            "speaker": name,
            "party": c.get("party", ""),
            "partyGroup": c.get("partyGroup", c.get("party", "")),
            "district": c.get("district", ""),
            "aliases": c.get("aliases", []),
            "term": c.get("term", "2023-2027"),
            "status": c.get("status", "active" if is_active else "retired"),
            "is_active": is_active,
            "resigned_date": c.get("resigned_date"),
            "resigned_reason": c.get("resigned_reason")
        }
        
        updated_master_list.append(c)

        # 原名・空白除去・正規化名すべてでマッピング
        speaker_stats_dict[name] = entry
        speaker_stats_dict[raw_clean] = entry
        speaker_stats_dict[norm_n] = entry
        
        # 退任議員も含めて有効発言者として保持
        valid_speaker_map[name] = name
        valid_speaker_map[raw_clean] = name
        valid_speaker_map[norm_n] = name

        for al in c.get("aliases", []):
            norm_al = normalize_name(al)
            clean_al = re.sub(r"[\s ]+", "", al)
            speaker_stats_dict[clean_al] = entry
            speaker_stats_dict[norm_al] = entry
            valid_speaker_map[clean_al] = name
            valid_speaker_map[norm_al] = name

    # 3. 首長の登録（mayors.json から動的取得）
    if MAYORS_FILE.exists():
        try:
            m_data = json.loads(MAYORS_FILE.read_text(encoding="utf-8"))
            if city in m_data:
                m_name = m_data[city]["name"]
                m_clean = re.sub(r"[\s ]+", "", m_name)
                m_norm = normalize_name(m_name)
                valid_speaker_map[m_clean] = m_name
                valid_speaker_map[m_norm] = m_name
                print(f"🏛️ 首長発言者登録: {m_name}")
        except Exception:
            pass

    # 4. フロントエンド公開用 councilors.json の保存
    FRONTEND_DATA.mkdir(parents=True, exist_ok=True)
    frontend_master_file = FRONTEND_DATA / f"{city}_councilors.json"
    frontend_master_file.write_bytes(json.dumps(updated_master_list, ensure_ascii=False, indent=2).encode("utf-8"))
    print(f"✅ [{city.upper()}] {frontend_master_file.name} を同期完了（全登録数: {len(updated_master_list)} 名）")
    if city == "kyoto":
        (FRONTEND_DATA / "councilors.json").write_bytes(json.dumps(updated_master_list, ensure_ascii=False, indent=2).encode("utf-8"))

    # 5. speaker_stats.json の保存
    stats_file = FRONTEND_DATA / f"{city}_speaker_stats.json"
    stats_file.write_bytes(json.dumps(speaker_stats_dict, ensure_ascii=False, indent=2).encode("utf-8"))
    if city == "kyoto":
        (FRONTEND_DATA / "speaker_stats.json").write_bytes(json.dumps(speaker_stats_dict, ensure_ascii=False, indent=2).encode("utf-8"))
    print(f"✅ [{city.upper()}] {stats_file.name} を同期完了（マッピングキー数: {len(speaker_stats_dict)}）")

    # 6. 会議録サマリーの同期（過去発言の保護と発言者名正規化）
    summary_candidates = [
        FRONTEND_DATA / f"{city}_statements_summary.json",
        FRONTEND_DATA / f"statements_summary_{city}.json"
    ]
    if city == "kyoto":
        summary_candidates.append(FRONTEND_DATA / "statements_summary.json")

    target_files = [p for p in summary_candidates if p.exists()]
    if target_files:
        raw_stmts = json.loads(target_files[0].read_text(encoding="utf-8-sig"))
        statements = raw_stmts.get("statements", []) if isinstance(raw_stmts, dict) else raw_stmts
        filtered_stmts = []
        excluded_speakers = set()

        for s in statements:
            spk = s.get("speaker") or s.get("speaker_name") or ""
            norm_spk = normalize_name(spk)
            clean_spk = re.sub(r"[\s ]+", "", spk)

            matched_canonical = valid_speaker_map.get(clean_spk) or valid_speaker_map.get(norm_spk) or valid_speaker_map.get(spk)
            if matched_canonical:
                s["speaker"] = matched_canonical
                filtered_stmts.append(s)
            else:
                excluded_speakers.add(spk)

        out_content = filtered_stmts if isinstance(raw_stmts, list) else {**raw_stmts, "statements": filtered_stmts}
        for out_p in target_files:
            out_p.write_bytes(json.dumps(out_content, ensure_ascii=False, indent=2).encode("utf-8"))
            
        print(f"✅ [{city.upper()}] 質疑ログ同期完了: {len(filtered_stmts)} 件保持 / フィルタ対象: {len(excluded_speakers)} 名")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="all", help="対象都市 (kyoto, osaka, nagoya, yokohama, kobe, all)")
    args = parser.parse_args()
    
    target = args.city.lower()
    cities = ["kyoto", "osaka", "nagoya", "yokohama", "kobe"] if target == "all" else [target]
    for c in cities:
        sync_master_data(c)
