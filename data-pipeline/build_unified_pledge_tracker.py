import os
import json
import re
import math
import argparse
from pathlib import Path
from dotenv import load_dotenv

CUR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR.parent
DATA_DIR = CUR / "data"
CONFIG_DIR = CUR / "config"
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist" / "data"

load_dotenv(CUR / ".env")
load_dotenv(PROJECT_ROOT / ".env")

EMBEDDING_MODEL = "models/gemini-embedding-2"

def clean_name(name: str) -> str:
    return re.sub(r"[\s\u3000]+", "", str(name or ""))

def cosine_similarity(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

def get_stmt_id(stmt, idx):
    return str(stmt.get("id") or stmt.get("speech_id") or f"stmt_{stmt.get('speaker', '')}_{stmt.get('meeting_date', '')}_{idx}")

def get_paths(city):
    stmt_candidates = [
        FRONTEND_DATA / f"{city}_statements_summary.json",
        FRONTEND_DATA / f"{city}_statements.json"
    ]
    if city == "kyoto":
        stmt_candidates.extend([FRONTEND_DATA / "statements_summary.json", FRONTEND_DATA / "statements.json"])

    stmt_path = None
    for p in stmt_candidates:
        if p.exists():
            stmt_path = p
            break

    out_files = [
        FRONTEND_DATA / f"pledge_tracker_{city}.json",
        FRONTEND_DIST / f"pledge_tracker_{city}.json"
    ]
    if city == "kyoto":
        out_files.extend([FRONTEND_DATA / "pledge_tracker.json", FRONTEND_DIST / "pledge_tracker.json"])
    elif city == "osaka":
        out_files.extend([FRONTEND_DATA / "osaka" / "pledge_tracker.json", FRONTEND_DIST / "osaka" / "pledge_tracker.json"])

    return {
        "rules": CONFIG_DIR / "pledge_matching_rules.json",
        "pledges": DATA_DIR / f"{city}_councilor_pledges.json",
        "pledges_alt": DATA_DIR / "councilor_pledges.json" if city == "kyoto" else None,
        "pledges_fallback": FRONTEND_DATA / f"pledge_tracker_{city}_2.json",
        "statements": stmt_path,
        "stmt_embeddings": DATA_DIR / f"embeddings_{city}_statements.json",
        "pledge_embeddings": DATA_DIR / f"embeddings_{city}_pledges.json",
        "out_files": out_files
    }

def get_or_create_pledge_embeddings(councilor_list, emb_file):
    if emb_file.exists():
        try:
            return json.loads(emb_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {}

    import google.generativeai as genai
    genai.configure(api_key=api_key)

    print("⚡ 公約テキストのEmbeddingを計算中...")
    cache = {}
    pending = []
    
    for c in councilor_list:
        spk = clean_name(c.get("speaker") or c.get("name") or "")
        for idx, p in enumerate(c.get("pledges", [])):
            full_id = f"{spk}_{idx+1}"
            text = f"{p.get('category', '')} {p.get('target_issue', '')} {p.get('headline', '')}".strip()
            pending.append((full_id, text))

    batch_size = 50
    for i in range(0, len(pending), batch_size):
        batch = pending[i : i + batch_size]
        try:
            resp = genai.embed_content(model=EMBEDDING_MODEL, content=[item[1] for item in batch])
            for (p_id, _), emb in zip(batch, resp["embedding"]):
                cache[p_id] = emb
        except Exception as e:
            print(f"⚠️ 公約Embeddingエラー: {e}")

    emb_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"✅ 公約Embedding保存完了: {len(cache)} 件")
    return cache

def main():
    parser = argparse.ArgumentParser(description="統一公約トラッカービルダー")
    parser.add_argument("--city", required=True, help="対象都市コード")
    args = parser.parse_args()
    city = args.city.lower()

    print(f"=== {city.upper()} 公約トラッカー 統一ビルドパイプライン ===")
    paths = get_paths(city)

    pledges_path = paths["pledges"] if paths["pledges"].exists() else paths["pledges_alt"]
    if not pledges_path or not pledges_path.exists():
        pledges_path = paths["pledges_fallback"]
    if not pledges_path or not pledges_path.exists():
        print("❌ 公約データが見つかりません。")
        return

    raw_data = json.loads(pledges_path.read_text(encoding="utf-8"))
    councilor_list = []
    if isinstance(raw_data, dict):
        if "councilors" in raw_data:
            councilor_list = raw_data["councilors"]
        else:
            for name, val in raw_data.items():
                item = dict(val)
                item["speaker"] = name
                councilor_list.append(item)
    elif isinstance(raw_data, list):
        councilor_list = raw_data

    statements = []
    if paths["statements"] and paths["statements"].exists():
        raw_stmts = json.loads(paths["statements"].read_text(encoding="utf-8"))
        statements = raw_stmts if isinstance(raw_stmts, list) else raw_stmts.get("statements", [])
        print(f"🔍 質疑データロード完了: {paths['statements'].name} ({len(statements)} 件)")

    stmt_embeddings = {}
    use_semantic = False
    if paths["stmt_embeddings"].exists():
        try:
            stmt_embeddings = json.loads(paths["stmt_embeddings"].read_text(encoding="utf-8"))
            use_semantic = True
            print(f"🧠 質疑Embeddingキャッシュ有効: {len(stmt_embeddings)} 件 (セマンティック照合モード)")
        except Exception:
            pass

    pledge_embeddings = {}
    if use_semantic:
        pledge_embeddings = get_or_create_pledge_embeddings(councilor_list, paths["pledge_embeddings"])

    stmts_by_speaker = {}
    for idx, s in enumerate(statements):
        spk = clean_name(s.get("speaker") or s.get("speaker_name") or "")
        if spk:
            s_id = get_stmt_id(s, idx)
            s_with_id = dict(s)
            s_with_id["_computed_id"] = s_id
            stmts_by_speaker.setdefault(spk, []).append(s_with_id)

    city_rules = []
    if paths["rules"].exists():
        city_rules = json.loads(paths["rules"].read_text(encoding="utf-8")).get(city, [])

    pledge_tracker = {}
    for c in councilor_list:
        raw_name = c.get("speaker") or c.get("name") or ""
        c_name = clean_name(raw_name)
        if not c_name:
            continue

        district = c.get("district", "")
        party = c.get("party") or c.get("partyGroup", "")
        bulletin_url = c.get("bulletin_url") or c.get("bulletin_pdf") or ""
        raw_pledges = c.get("pledges", [])
        my_stmts = stmts_by_speaker.get(c_name, [])

        tracked_items = []
        for idx, p in enumerate(raw_pledges):
            full_p_id = f"{c_name}_{idx+1}"
            candidates = []
            
            # 1. セマンティック照合（sim >= 0.65）
            if use_semantic and full_p_id in pledge_embeddings:
                p_vec = pledge_embeddings[full_p_id]
                for stmt in my_stmts:
                    sid = stmt.get("_computed_id")
                    if sid in stmt_embeddings:
                        s_vec = stmt_embeddings[sid]
                        sim = cosine_similarity(p_vec, s_vec)
                        if sim >= 0.65:
                            candidates.append((sim, stmt))
                candidates.sort(key=lambda x: (x[0], x[1].get("meeting_date", "")), reverse=True)
            
            # 2. ルール照合（フォールバック）
            if not candidates and not use_semantic:
                target_text = f"{p.get('target_issue', '')} {p.get('headline', '')}"
                matched_rule = next((r for r in city_rules if any(t in target_text for t in r.get("triggers", []))), None)
                if matched_rule:
                    reqs = matched_rule.get("required", [])
                    for stmt in my_stmts:
                        full_t = f"{stmt.get('statement_summary', '')} {stmt.get('statement_text', '')[:350]}"
                        if not reqs or any(r in full_t for r in reqs):
                            score = sum(full_t.count(t) for t in matched_rule.get("triggers", []))
                            if score > 0:
                                candidates.append((score, stmt))
                    candidates.sort(key=lambda x: (x[0], x[1].get("meeting_date", "")), reverse=True)

            related_stmts = []
            for _, best in candidates[:2]:
                s_sum = best.get("statement_summary") or best.get("summary") or best.get("statement_text", "")
                related_stmts.append({
                    "date": best.get("meeting_date") or best.get("date") or "",
                    "committee": best.get("meeting_name") or best.get("committee") or "本会議・委員会",
                    "summary": s_sum[:200] + ("..." if len(s_sum) > 200 else ""),
                    "speech_id": best.get("_computed_id", ""),
                    "official_url": best.get("official_url") or best.get("source_url") or ""
                })

            tracked_items.append({
                "id": f"pledge_{city}_{c_name}_{idx+1}",
                "headline": p.get("headline", ""),
                "category": p.get("category", "くらし・環境・エネルギー"),
                "target_issue": p.get("target_issue", ""),
                "stance": p.get("stance", "推進・拡充"),
                "election_promise": {
                    "quote": p.get("exact_quote") or p.get("quote") or "",
                    "source_name": "公式選挙公報 / 政策マニフェスト",
                    "bulletin_url": p.get("bulletin_url") or p.get("bulletin_pdf") or bulletin_url
                },
                "council_vote": None,
                "council_statement": related_stmts[0] if related_stmts else None,
                "council_statements": related_stmts
            })

        c_data = {
            "district": district,
            "party": party,
            "bulletin_url": bulletin_url,
            "tracked_items": tracked_items
        }
        pledge_tracker[raw_name] = c_data
        if c_name != raw_name:
            pledge_tracker[c_name] = c_data

    for out_p in paths["out_files"]:
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(pledge_tracker, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 保存完了: {out_p.resolve()}")

    print(f"🎉 {city.upper()} のビルドが完了しました！（対象: {len(councilor_list)} 名）\n")

if __name__ == "__main__":
    main()
