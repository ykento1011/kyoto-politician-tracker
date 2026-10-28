import os
import json
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

CUR = Path(".").resolve()
PROJECT_ROOT = CUR.parent if CUR.name == "data-pipeline" else CUR
BASE_DIR = PROJECT_ROOT / "data-pipeline"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"

load_dotenv(BASE_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY または GOOGLE_API_KEY が見つかりません。")
    exit(1)

import google.generativeai as genai
genai.configure(api_key=api_key)

EMBEDDING_MODEL = "models/gemini-embedding-2"

def get_stmt_id(stmt, idx):
    return str(stmt.get("id") or stmt.get("speech_id") or f"stmt_{stmt.get('speaker', '')}_{stmt.get('meeting_date', '')}_{idx}")

def get_stmt_text(stmt):
    speaker = stmt.get("speaker") or stmt.get("speaker_name") or ""
    comm = stmt.get("committee") or stmt.get("meeting_name") or ""
    summary = stmt.get("statement_summary") or stmt.get("summary") or stmt.get("question_summary") or stmt.get("statement_text") or ""
    return f"{speaker} {comm} {summary}".strip()

def main():
    parser = argparse.ArgumentParser(description="質疑Embeddingキャッシュ生成")
    parser.add_argument("--city", default="osaka", help="対象都市コード (osaka, kyoto, nagoya)")
    parser.add_argument("--batch-size", type=int, default=50, help="1リクエストあたりのバッチサイズ")
    args = parser.parse_args()
    city = args.city.lower()

    # 質疑ファイルの特定
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

    if not stmt_path:
        print(f"❌ {city} の質疑ファイルが見つかりません。")
        return

    statements = json.loads(stmt_path.read_text(encoding="utf-8"))
    if isinstance(statements, dict) and "statements" in statements:
        statements = statements["statements"]

    print(f"================================================================================")
    print(f" 🚀 【{city.upper()}】 質疑Embeddingキャッシュ生成 ({EMBEDDING_MODEL})")
    print(f"================================================================================")
    print(f"📁 読み込み元: {stmt_path.name} (全 {len(statements)} 件)")

    cache_file = DATA_DIR / f"embeddings_{city}_statements.json"
    cache = {}
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
            print(f"🔄 既存キャッシュをロード: {len(cache)} 件 処理済み")
        except Exception:
            cache = {}

    # 未処理の質疑を抽出
    pending = []
    for idx, s in enumerate(statements):
        sid = get_stmt_id(s, idx)
        if sid not in cache:
            text = get_stmt_text(s)
            if text:
                pending.append((sid, text))

    print(f"⚡ 新規計算対象: {len(pending)} 件")

    if not pending:
        print("🎉 全ての質疑がすでにキャッシュされています！")
        return

    batch_size = args.batch_size
    total_batches = (len(pending) + batch_size - 1) // batch_size

    for b_idx in range(total_batches):
        batch = pending[b_idx * batch_size : (b_idx + 1) * batch_size]
        batch_ids = [item[0] for item in batch]
        batch_texts = [item[1] for item in batch]

        success = False
        for retry in range(3):
            try:
                response = genai.embed_content(
                    model=EMBEDDING_MODEL,
                    content=batch_texts
                )
                embeddings = response["embedding"]
                
                for sid, emb in zip(batch_ids, embeddings):
                    cache[sid] = emb
                
                success = True
                break
            except Exception as e:
                print(f"\n⚠️ バッチ {b_idx + 1}/{total_batches} リトライ ({retry + 1}/3): {e}")
                time.sleep(3)

        if not success:
            print(f"❌ バッチ {b_idx + 1} の処理に失敗しました。現在の進捗を保存して中断します。")
            break

        # 進捗保存（各バッチごと）
        cache_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        progress = (b_idx + 1) / total_batches * 100
        print(f"\r  進捗: [{b_idx + 1}/{total_batches}] {progress:.1f}% ({len(cache)}/{len(statements)} 件完了)", end="", flush=True)
        time.sleep(1.0)  # レート制限対策のウェイト

    print(f"\n\n✅ キャッシュ保存完了: {cache_file.resolve()} (合計: {len(cache)} 件)")

if __name__ == "__main__":
    main()