import json
import re
import unicodedata
import argparse
from pathlib import Path

CUR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR.parent
MASTER_DIR = CUR / "master"
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"

# 人名で頻出する異体字・旧字体の正規化テーブル
KANJI_VARIANTS = str.maketrans({
    "髙": "高", "﨑": "崎", "繁": "繁", "齋": "斎", "齊": "斉",
    "邊": "辺", "邉": "辺", "栁": "柳", "德": "徳", "廣": "広",
    "櫻": "桜", "嶋": "島", "惠": "恵", "眞": "真", "冨": "富",
    "峰": "峯", "薮": "藪", "塚": "塚"
})

def normalize_name(t: str) -> str:
    """空白除去 + NFKC正規化 + 異体字正規化"""
    t = unicodedata.normalize("NFKC", str(t or ""))
    t = re.sub(r"[\s\u3000]+", "", t)
    return t.translate(KANJI_VARIANTS)

def sync_master_data(city: str):
    city = city.lower()
    master_file = MASTER_DIR / f"councilors_{city}.json"
    
    if not master_file.exists():
        print(f"❌ 正本マスターが存在しません: {master_file}")
        return

    # 1. 市サイト公式スクレイピングマスターの読み込み
    master_councilors = json.loads(master_file.read_text(encoding="utf-8-sig"))
    print(f"=== [{city.upper()}] 正本マスター同期（市サイト公式: {len(master_councilors)} 名） ===")

    # 2. 異体字吸収インデックスの構築
    valid_speaker_map = {}
    speaker_stats_dict = {}

    for c in master_councilors:
        name = c["name"]
        norm_n = normalize_name(name)
        raw_clean = re.sub(r"[\s\u3000]+", "", name)
        
        entry = {
            "name": name,
            "party": c.get("party", ""),
            "district": c.get("district", ""),
            "aliases": c.get("aliases", [])
        }
        
        # 原名・空白除去名・異体字正規化名すべてでマッピング
        speaker_stats_dict[name] = entry
        speaker_stats_dict[raw_clean] = entry
        speaker_stats_dict[norm_n] = entry
        
        valid_speaker_map[raw_clean] = name
        valid_speaker_map[norm_n] = name
        
        # エイリアス（ふりがな等）も正規化登録
        for al in c.get("aliases", []):
            norm_al = normalize_name(al)
            clean_al = re.sub(r"[\s\u3000]+", "", al)
            speaker_stats_dict[clean_al] = entry
            speaker_stats_dict[norm_al] = entry
            valid_speaker_map[clean_al] = name
            valid_speaker_map[norm_al] = name

    # 首長の登録
    MAYORS = {"kyoto": "松井孝治", "osaka": "横山英幸", "nagoya": "広沢一郎", "yokohama": "山中竹春"}
    if city in MAYORS:
        m_name = MAYORS[city]
        valid_speaker_map[normalize_name(m_name)] = m_name

    # 3. speaker_stats.json の保存
    stats_file = FRONTEND_DATA / f"{city}_speaker_stats.json"
    stats_file.write_bytes(json.dumps(speaker_stats_dict, ensure_ascii=False, indent=2).encode("utf-8"))
    if city == "kyoto":
        (FRONTEND_DATA / "speaker_stats.json").write_bytes(json.dumps(speaker_stats_dict, ensure_ascii=False, indent=2).encode("utf-8"))
    print(f"✅ [{city.upper()}] {stats_file.name} を同期完了")

    # 4. 会議録サマリーの同期
    summary_candidates = [
        FRONTEND_DATA / f"{city}_statements_summary.json",
        FRONTEND_DATA / f"statements_summary_{city}.json"
    ]
    if city == "kyoto":
        summary_candidates.append(FRONTEND_DATA / "statements_summary.json")

    target_files = [p for p in summary_candidates if p.exists()]
    if target_files:
        raw_stmts = json.loads(target_files[0].read_text(encoding="utf-8-sig"))
        
        filtered_stmts = []
        excluded_speakers = set()

        for s in raw_stmts:
            spk = s.get("speaker") or s.get("speaker_name") or ""
            norm_spk = normalize_name(spk)
            
            if norm_spk in valid_speaker_map:
                s["speaker"] = valid_speaker_map[norm_spk]
                filtered_stmts.append(s)
            else:
                excluded_speakers.add(spk)

        for out_p in target_files:
            out_p.write_bytes(json.dumps(filtered_stmts, ensure_ascii=False, indent=2).encode("utf-8"))
            
        print(f"✅ [{city.upper()}] 質疑ログ同期完了: {len(filtered_stmts)} 件保持 / 非現職排除: {len(excluded_speakers)} 名")
        if excluded_speakers:
            print(f"   (排除された非現職・行政幹部: {sorted(list(excluded_speakers))})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True, help="対象都市 (kyoto, yokohama, osaka, nagoya)")
    args = parser.parse_args()
    sync_master_data(args.city)
