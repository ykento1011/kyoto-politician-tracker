import json
import os
import re
from pathlib import Path

# キーワード定義（政策カテゴリー精査用）
INDUSTRY_KEYWORDS = [
    "中小企業", "伝統産業", "地場産業", "観光", "インバウンド", "オーバーツーリズム",
    "商店街", "商業", "宿泊税", "スタートアップ", "事業承継", "雇用", "地域経済", "物価高騰対策"
]
CULTURE_KEYWORDS = [
    "文化庁", "文化芸術", "伝統文化", "京町家", "景観", "歴史的風土", "文化財", "博物館", "美術館", "芸術家"
]
TRANSIT_KEYWORDS = [
    "市バス", "地下鉄", "敬老乗車証", "歩いて暮らせる", "公共交通", "混雑対策", "運賃"
]
FINANCE_KEYWORDS = [
    "財政", "行革", "行財政", "予算", "決算", "市債", "借金", "人件費", "議員定数", "報酬", "外部監査", "補助金"
]

def clean_speaker_name(speaker):
    if not speaker:
        return "理事者"
    name = str(speaker).strip()
    name = re.sub(r"(議員|委員長|副委員長|市長|副市長|局長|部長|理事者)$", "", name).strip()
    return name

def refine_category(category_raw, title, summary):
    cat_str = ", ".join(str(x) for x in category_raw) if isinstance(category_raw, list) else str(category_raw or "")
    full_text = f"{title or ''} {summary or ''}"

    if "産業交通水道" in (title or ""):
        if any(k in full_text for k in TRANSIT_KEYWORDS):
            return "都市再生・交通インフラ"
        return "産業・観光・地域経済"

    if any(k in full_text for k in CULTURE_KEYWORDS):
        return "文化・景観・歴史"

    if any(k in full_text for k in INDUSTRY_KEYWORDS):
        return "産業・観光・地域経済"

    if any(k in full_text for k in FINANCE_KEYWORDS) or ("総務消防" in (title or "") and "財政" in full_text):
        return "財政・行革"

    if "都市計画" in cat_str or "交通" in cat_str or "道路" in full_text:
        return "都市再生・交通インフラ"
    if "福祉" in cat_str or "医療" in cat_str or "健康" in cat_str:
        return "福祉・医療・健康"
    if "環境" in cat_str or "エネルギー" in cat_str or "ごみ" in full_text:
        return "くらし・環境・エネルギー"
    if "教育" in cat_str or "子育て" in cat_str or "学校" in full_text or "保育" in full_text:
        return "子育て・教育"
    if "防災" in cat_str or "消防" in (title or "") or "防犯" in full_text:
        return "防災・減災・治安"
    if "財政" in cat_str or "行政" in cat_str:
        return "財政・行革"

    return "産業・観光・地域経済" if "産業" in cat_str else (cat_str if cat_str else "市政全般")

def generate_summary():
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent

    input_file = current_dir / "analyzed_kyoto_politicians_term.json"
    output_dir = project_root / "frontend" / "public" / "data"
    output_file = output_dir / "statements_summary.json"

    if not input_file.exists():
        raise FileNotFoundError(f"元データファイルが見つかりません: {input_file}")

    output_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print(f"📖 読み込み中: {input_file.name}")
    with open(input_file, "r", encoding="utf-8") as f:
        statements = json.load(f)

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

        meeting_title = s.get("meeting_title", "")
        summary_text = analysis.get("summary", "")
        cat_raw = analysis.get("category", "政策質疑")
        refined_cat = refine_category(cat_raw, meeting_title, summary_text)

        compact_records.append({
            "id": stmt_id,
            "meeting_id": m_id,
            "sequence_number": seq,
            "meeting_title": meeting_title,
            "meeting_date": s.get("meeting_date"),
            "speaker": clean_speaker_name(s.get("speaker")),
            "category": refined_cat,
            "summary": summary_text,
            "scoring_reasoning": analysis.get("reasoning", ""),
            "statement_snippet": snippet,
            "statement_text": snippet,
            "evidence_score": int(scores.get("evidence", 0)),
            "solution_score": int(scores.get("solution", 0)),
            "local_focus_score": int(scores.get("local_focus", 0)),
            "constructive_score": int(scores.get("constructive", 0)),
            "source_url": s.get("source_url", "")
        })

    compact_records.sort(key=lambda x: str(x.get("meeting_date", "")), reverse=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(compact_records, f, ensure_ascii=False, separators=(',', ':'))

    file_size_mb = output_file.stat().st_size / (1024 * 1024)

    print(f"🎉 生成完了: {output_file}")
    print(f"📊 総質疑数: {len(compact_records):,} 件 (全件カテゴリー精査・原本URL付与済み)")
    print(f"💾 ファイルサイズ: {file_size_mb:.2f} MB")
    print("==================================================")

if __name__ == "__main__":
    generate_summary()
