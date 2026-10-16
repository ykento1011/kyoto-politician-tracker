import json
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. 複数の階層（カレント、親ディレクトリ、frontendフォルダ）から .env を探索して読み込む
current_dir = Path(__file__).resolve().parent
env_candidates = [
    current_dir / ".env",
    current_dir.parent / ".env",
    current_dir.parent / "frontend" / ".env",
    current_dir.parent / "frontend" / ".env.local"
]

for env_path in env_candidates:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

# 2. 変数名のゆらぎに対応
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY") 
    or os.getenv("SUPABASE_SERVICE_KEY")        # ← ここを追加
    or os.getenv("SUPABASE_KEY") 
    or os.getenv("VITE_SUPABASE_ANON_KEY")
)

# 読み込み確認
if not SUPABASE_URL:
    raise ValueError(
        f"SUPABASE_URL が見つかりません。以下のいずれかのパスに .env を配置し、SUPABASE_URL または VITE_SUPABASE_URL を設定してください:\n"
        + "\n".join([str(p) for p in env_candidates])
    )

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY (または SUPABASE_SERVICE_ROLE_KEY / VITE_SUPABASE_ANON_KEY) が設定されていません。")

print(f"Connecting to Supabase: {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload():
    json_path = current_dir / "analyzed_kyoto_politicians.json"
    if not json_path.exists():
        raise FileNotFoundError(f"{json_path} が存在しません。")

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    payload = []
    for r in records:
        analysis = r.get("analysis", {})
        scores = analysis.get("scores", {})
        
        payload.append({
            "conversation_id": r.get("conversation_id"),
            "meeting_id": r.get("meeting_id"),
            "meeting_title": r.get("meeting_title"),
            "meeting_date": r.get("meeting_date"),
            "speaker": r.get("speaker"),
            "speaker_id": str(r.get("speaker_id")) if r.get("speaker_id") else None,
            "speaker_header": r.get("speaker_header"),
            "statement_text": r.get("statement_text"),
            "sequence_number": r.get("sequence_number"),
            "source_url": r.get("source_url"),
            "category": analysis.get("category", "事務・進行"),
            "summary": analysis.get("summary", ""),
            "keywords": analysis.get("keywords", []),
            "evidence_score": scores.get("evidence", 0),
            "solution_score": scores.get("solution", 0),
            "local_focus_score": scores.get("local_focus", 0),
            "constructive_score": scores.get("constructive", 0),
            "total_quality_score": scores.get("total_quality", 0),
            "is_evaluated": analysis.get("is_evaluated", False),
            "scoring_reasoning": analysis.get("reasoning", "")
        })

    # 100件ずつ一括Upsert実行
    batch_size = 100
    for i in range(0, len(payload), batch_size):
        batch = payload[i:i + batch_size]
        supabase.table("statements").upsert(batch, on_conflict="conversation_id").execute()
        print(f"Uploaded: {min(i + batch_size, len(payload))} / {len(payload)}")

    print("✅ Supabaseへの全件アップロードが完了しました！")

if __name__ == "__main__":
    upload()