import json
from supabase import create_client, Client

# Step 1でメモしたURLとAPIキーに書き換えてください
SUPABASE_URL = "https://redywauvhaugiinkxzrc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJlZHl3YXV2aGF1Z2lpbmt4enJjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MjE1MjQwMywiZXhwIjoyMTA3NzI4NDAzfQ.kPH_6Ejwi6ZTejzgfVPKDHQ4jbAdtn1h5z3GL7HX020"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_data():
    input_file = "analyzed_kyoto_politicians.json"
    
    with open(input_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"🚀 {len(records)} 件のデータをSupabaseへアップロードします...")

    insert_data = []
    for row in records:
        # Geminiの解析結果を取り出す
        analysis = row.get("analysis", {})
        
        insert_data.append({
            "meeting_title": row.get("meeting_title"),
            "meeting_date": row.get("meeting_date"),
            "speaker": row.get("speaker"),
            "speaker_id": row.get("speaker_id", None), # まだ取得していない場合はNone
            "speaker_header": row.get("speaker_header"),
            "statement_text": row.get("statement_text"),
            "sequence_number": row.get("sequence_number"),
            "conversation_id": row.get("conversation_id"),
            "meeting_id": row.get("meeting_id"),
            "source_url": row.get("source_url"),
            "category": analysis.get("category", "未分類"),
            "summary": analysis.get("summary", ""),
            "keywords": analysis.get("keywords", [])
        })

    # Supabaseに一括挿入 (upsertを使うことで、conversation_idが被った場合は上書き更新される)
    try:
        response = supabase.table("statements").upsert(insert_data).execute()
        print("🎉 アップロード完了！SupabaseのTable Editor画面でデータを確認してください。")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    upload_data()