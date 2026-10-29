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

def make_bill_key(sess, bno, title, idx):
    if sess and bno:
        return f"{sess}_{bno}"
    if sess and title:
        clean_t = re.sub(r"[^\w\u4e00-\u9fa5\u3040-\u309f\u30a0-\u30ff]", "", title)[:20]
        return f"{sess}_{clean_t}"
    return f"bill_{idx}"

def resolve_vote(votes_dict, party, speaker_name):
    clean_spk = clean_name(speaker_name)
    clean_p = clean_name(party)

    # 1. 議員個人の採決（造反・無所属等）
    for k, v in votes_dict.items():
        if clean_name(k) == clean_spk:
            return v, "個人採決"

    # 2. 会派の採決
    for k, v in votes_dict.items():
        ck = clean_name(k)
        if clean_p and (clean_p in ck or ck in clean_p):
            return v, "会派方針"
        if "維新" in clean_p and "維新" in ck: return v, "会派方針"
        if "自民" in clean_p and "自民" in ck: return v, "会派方針"
        if "公明" in clean_p and "公明" in ck: return v, "会派方針"
        if "共産" in clean_p and "共産" in ck: return v, "会派方針"
        if "民主" in clean_p and "民主" in ck: return v, "会派方針"
        if "減税" in clean_p and "減税" in ck: return v, "会派方針"

    return None, None

def get_stmt_id(stmt, idx):
    return str(stmt.get("id") or stmt.get("speech_id") or f"stmt_{stmt.get('speaker', '')}_{stmt.get('meeting_date', '')}_{idx}")

def get_paths(city):
    stmt_candidates = [
        FRONTEND_DATA / f"{city}_statements_summary.json",
        FRONTEND_DATA / f"{city}_statements.json"
    ]
    if city == "kyoto":
        stmt_candidates.extend([FRONTEND_DATA / "statements_summary.json", FRONTEND_DATA / "statements.json"])

    stmt_path = next((p for p in stmt_candidates if p.exists()), None)

    out_files = [FRONTEND_DATA / f"pledge_tracker_{city}.json"]
    if city == "kyoto":
        out_files.append(FRONTEND_DATA / "pledge_tracker.json")
    elif city == "osaka":
        out_files.append(FRONTEND_DATA / "osaka" / "pledge_tracker.json")

    return {
        "pledges": DATA_DIR / f"{city}_councilor_pledges.json",
        "pledges_alt": DATA_DIR / "councilor_pledges.json" if city == "kyoto" else None,
        "pledges_fallback": FRONTEND_DATA / f"pledge_tracker_{city}_2.json",
        "statements": stmt_path,
        "votes": FRONTEND_DATA / f"{city}_votes_summary.json",
        "votes_alt": FRONTEND_DATA / "votes_summary.json" if city == "kyoto" else None,
        "issues": FRONTEND_DATA / f"{city}_bill_issues.json",
        "issues_alt": FRONTEND_DATA / "bill_issues.json" if city == "kyoto" else None,
        "stmt_embeddings": DATA_DIR / f"embeddings_{city}_statements.json",
        "pledge_embeddings": DATA_DIR / f"embeddings_{city}_pledges.json",
        "bill_embeddings": DATA_DIR / f"embeddings_{city}_bills.json",
        "out_files": out_files
    }

def build_bill_data(paths, city):
    votes_p = paths["votes"] if paths["votes"].exists() else paths["votes_alt"]
    issues_p = paths["issues"] if paths["issues"].exists() else paths["issues_alt"]
    
    votes_list = json.loads(votes_p.read_text(encoding="utf-8")) if votes_p and votes_p.exists() else []
    issues_list = json.loads(issues_p.read_text(encoding="utf-8")) if issues_p and issues_p.exists() else []

    issue_lookup = {}
    for iss in issues_list:
        title = iss.get("title", "")
        sess = iss.get("session_name", "")
        bno = iss.get("bill_number", "")
        if sess and bno: issue_lookup[f"{sess}_{bno}"] = iss
        if title: issue_lookup[title] = iss

    bills = []
    seen_keys = set()

    for idx, v in enumerate(votes_list):
        sess = v.get("session_name", "")
        bno = v.get("bill_number", "")
        title = v.get("title", "")
        key = make_bill_key(sess, bno, title, idx)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        iss = issue_lookup.get(key) or issue_lookup.get(title) or {}
        conflict = iss.get("key_conflict") or iss.get("issue", "")
        background = iss.get("background", "")
        category = iss.get("category", "")
        text = f"{title} {category} {conflict} {background}".strip()

        bills.append({
            "id": key,
            "title": title,
            "session": sess,
            "bill_number": bno,
            "conflict": conflict,
            "votes": v.get("votes", {}),
            "source_url": v.get("source_url", ""),
            "text": text
        })

    bill_embeddings = {}
    if paths["bill_embeddings"].exists():
        try:
            bill_embeddings = json.loads(paths["bill_embeddings"].read_text(encoding="utf-8"))
        except Exception:
            bill_embeddings = {}

    uncached = [b for b in bills if b["id"] not in bill_embeddings]
    if uncached:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        
        print(f"⚡ {city.upper()} 議案Embedding計算: 未計算 {len(uncached)} 件 / 全議案 {len(bills)} 件...")
        batch_size = 50
        for i in range(0, len(uncached), batch_size):
            batch = uncached[i : i + batch_size]
            try:
                resp = genai.embed_content(model=EMBEDDING_MODEL, content=[b["text"] for b in batch])
                embs = resp.get("embedding", [])
                for b, emb in zip(batch, embs):
                    bill_embeddings[b["id"]] = emb
            except Exception as e:
                print(f"⚠️ 議案Embeddingエラー (offset {i}): {e}")

        paths["bill_embeddings"].write_text(json.dumps(bill_embeddings, ensure_ascii=False), encoding="utf-8")
        print(f"✅ {city.upper()} 議案Embedding保存完了: {len(bill_embeddings)} 件")

    return bills, bill_embeddings


def get_or_create_pledge_embeddings(councilor_list, emb_file):
    cache = {}
    if emb_file.exists():
        try:
            cache = json.loads(emb_file.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    pending = []
    for c in councilor_list:
        spk = clean_name(c.get("speaker") or c.get("name") or "")
        if not spk:
            continue
        for idx, p in enumerate(c.get("pledges", [])):
            key_num = f"{spk}_{idx+1}"
            key_p = f"{spk}_p_{idx+1}"
            p_id = p.get("id")
            key_id = f"{spk}_{p_id}" if p_id else None

            # 未計算の場合のみキューへ追加（キー形式の差異を吸収）
            if key_num not in cache:
                text = f"{p.get('category', '')} {p.get('target_issue', '')} {p.get('headline', '')}".strip()
                keys = [key_num, key_p]
                if key_id:
                    keys.append(key_id)
                pending.append((keys, text))

    if pending:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("⚠️ APIキーが見つからないため公約Embedding計算をスキップします。")
            return cache

        import google.generativeai as genai
        genai.configure(api_key=api_key)

        print(f"⚡ 公約テキストEmbedding計算: 未計算 {len(pending)} 件...")
        batch_size = 50
        for i in range(0, len(pending), batch_size):
            batch = pending[i : i + batch_size]
            try:
                resp = genai.embed_content(model=EMBEDDING_MODEL, content=[item[1] for item in batch])
                embs = resp.get("embedding", [])
                for (keys, _), emb in zip(batch, embs):
                    for k in keys:
                        cache[k] = emb
            except Exception as e:
                print(f"⚠️ 公約Embeddingエラー (offset {i}): {e}")

        emb_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"✅ 公約Embedding保存完了: {len(cache)} 件 -> {emb_file.name}")

    return cache

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    args = parser.parse_args()
    city = args.city.lower()
    paths = get_paths(city)

    print(f"\n=== {city.upper()} 公約トラッカー 統一ビルド（安定版） ===")

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

    stmt_embeddings = json.loads(paths["stmt_embeddings"].read_text(encoding="utf-8")) if paths["stmt_embeddings"].exists() else {}
    pledge_embeddings = get_or_create_pledge_embeddings(councilor_list, paths["pledge_embeddings"])
    
    bills, bill_embeddings = build_bill_data(paths, city)

    stmts_by_speaker = {}
    for idx, s in enumerate(statements):
        spk = clean_name(s.get("speaker") or s.get("speaker_name") or "")
        if spk:
            s_id = get_stmt_id(s, idx)
            s_with_id = dict(s)
            s_with_id["_computed_id"] = s_id
            stmts_by_speaker.setdefault(spk, []).append(s_with_id)

    STOP_WORDS = {"推進", "支援", "実現", "対策", "安心", "安全", "向上", "強化", "徹底", "拡充", "促進", "見直し", "充実", "整備", "取組", "地域", "市民", "市政", "京都", "大阪", "名古屋"}

    pledge_tracker = {}
    for c in councilor_list:
        raw_name = c.get("speaker") or c.get("name") or ""
        c_name = clean_name(raw_name)
        if not c_name: continue

        district = c.get("district", "")
        party = c.get("party") or c.get("partyGroup", "")
        bulletin_url = c.get("bulletin_url") or c.get("bulletin_pdf") or ""
        my_stmts = stmts_by_speaker.get(c_name, [])

        tracked_items = []
        for idx, p in enumerate(c.get("pledges", [])):
            full_p_id = f"{c_name}_{idx+1}"
            
            # 1. 質疑マッチング (sim >= 0.65)
            candidates = []
            if full_p_id in pledge_embeddings:
                p_vec = pledge_embeddings[full_p_id]
                for stmt in my_stmts:
                    sid = stmt.get("_computed_id")
                    if sid in stmt_embeddings:
                        sim = cosine_similarity(p_vec, stmt_embeddings[sid])
                        if sim >= 0.65:
                            candidates.append((sim, stmt))
                candidates.sort(key=lambda x: (x[0], x[1].get("meeting_date", "")), reverse=True)

            related_stmts = []
            for _, best in candidates[:2]:
                s_sum = best.get("statement_summary") or best.get("summary") or best.get("statement_text", "")
                related_stmts.append({
                    "date": best.get("meeting_date") or best.get("date") or "",
                    "committee": best.get("meeting_name") or best.get("committee") or "本会議",
                    "summary": s_sum[:200] + "...",
                    "speech_id": best.get("_computed_id", ""),
                    "official_url": best.get("official_url") or best.get("source_url") or ""
                })

            # 2. 議案・採決マッチング (アンカーゲート + sim >= 0.65)
            council_vote = None
            if full_p_id in pledge_embeddings and bill_embeddings:
                p_vec = pledge_embeddings[full_p_id]
                target_p_text = f"{p.get('target_issue', '')} {p.get('headline', '')}"
                p_keywords = [w for w in re.findall(r"[\u4e00-\u9fa5\u30a1-\u30fc]{2,}", target_p_text) if w not in STOP_WORDS]

                best_bill_sim = 0.0
                best_bill = None
                for b in bills:
                    b_id = b["id"]
                    if b_id in bill_embeddings:
                        bsim = cosine_similarity(p_vec, bill_embeddings[b_id])
                        if bsim > best_bill_sim:
                            best_bill_sim = bsim
                            best_bill = b

                has_anchor = any(kw in best_bill["text"] for kw in p_keywords) if best_bill else False

                # 基準:
                # sim >= 0.65 かつ主要名詞アンカー一致、または sim >= 0.74 超高精度
                if best_bill and ((best_bill_sim >= 0.65 and has_anchor) or best_bill_sim >= 0.74):
                    vote_action, vote_type = resolve_vote(best_bill["votes"], party, raw_name)
                    if vote_action:
                        council_vote = {
                            "bill_title": best_bill["title"],
                            "bill_number": best_bill["bill_number"],
                            "session": best_bill["session"],
                            "vote": vote_action,
                            "vote_type": vote_type,
                            "source_url": best_bill["source_url"]
                        }

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
                "council_vote": council_vote,
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
        out_p.write_text(json.dumps(pledge_tracker, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 保存完了: {out_p.resolve()}")

    print(f"🎉 {city.upper()} ビルド完了（対象: {len(councilor_list)} 名）")

if __name__ == "__main__":
    main()
