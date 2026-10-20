import json
import os
import re
from pathlib import Path

def clean_speaker_name(speaker):
    if not speaker:
        return "理事者"
    name = str(speaker).strip()
    name = re.sub(r"(議員|委員長|副委員長|市長|副市長|局長|部長|理事者)$", "", name).strip()
    return name

def generate_summary():
    # 💡 スクリプト配置位置（data-pipeline）を起点にパスを絶対解決
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent  # kyoto-politician-tracker

    input_file = current_dir / "analyzed_kyoto_politicians_term.json"
    output_dir = project_root / "frontend" / "public" / "data"
    output_file = output_dir / "statements_summary.json"

    if not input_file.exists():
        raise FileNotFoundError(f"元データファイルが見つかりません: {input_file}")

    # 出力先フォルダ（frontend/public/data）が存在しない場合は自動作成
    output_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print(f"📖 読み込み中: {input_file.name}")
    with open(input_file, "r", encoding="utf-8") as f:
        statements = json.load(f)

    # 評価済み（実質政策質疑）レコードのみ抽出
    evaluated_targets = [s for s in statements if s.get("analysis", {}).get("is_evaluated")]

    compact_records = []
    for s in evaluated_targets:
        analysis = s.get("analysis", {})
        scores = analysis.get("scores", {})

        m_id = s.get("meeting_id")
        seq = s.get("sequence_number")
        stmt_id = s.get("id") or f"{m_id}_{seq}"
        raw_text = str(s.get("statement_text", "")).strip()
        snippet = raw_text[:120].replace("\n", " ")

        # フロントエンドの一覧・集計・カード描画に必要な項目のみを厳選
        compact_records.append({
            "id": stmt_id,
            "meeting_id": m_id,
            "sequence_number": seq,
            "meeting_title": s.get("meeting_title"),
            "meeting_date": s.get("meeting_date"),
            "speaker": clean_speaker_name(s.get("speaker")),  # 💡 肩書を自動除去
            "category": analysis.get("category", "政策質疑"),
            "summary": analysis.get("summary", ""),
            "scoring_reasoning": analysis.get("reasoning", ""),
            # 起点発言テキストはカード表示・検索用に冒頭120文字にトリミング（容量節約）
            "statement_snippet": snippet,
            "statement_text": snippet,
            "evidence_score": int(scores.get("evidence", 0)),
            "solution_score": int(scores.get("solution", 0)),
            "local_focus_score": int(scores.get("local_focus", 0)),
            "constructive_score": int(scores.get("constructive", 0)),
            "source_url": s.get("source_url", "")
        })

    # 日付の新しい順（降順）にソート
    compact_records.sort(key=lambda x: str(x.get("meeting_date", "")), reverse=True)

    # 空白・改行を極限まで省いてJSON保存（配信容量の極小化：約1.5MB）
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(compact_records, f, ensure_ascii=False, separators=(',', ':'))

    file_size_mb = output_file.stat().st_size / (1024 * 1024)

    print(f"🎉 生成完了: {output_file}")
    print(f"📊 総質疑数: {len(compact_records):,} 件")
    print(f"💾 ファイルサイズ: {file_size_mb:.2f} MB（Cloudflare 25MB制限クリア）")
    print("==================================================")

if __name__ == "__main__":
    generate_summary()