import os
import json
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIR = PROJECT_ROOT / "data-pipeline"
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"
MASTER_DIR = PIPELINE_DIR / "master"

CITIES = ["kyoto", "osaka", "nagoya", "yokohama", "kobe"]

def load_json(filepath):
    if not filepath.exists():
        return None
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠️ JSON読み込みエラー ({filepath.name}): {e}")
        return None

def load_mayor_policies(city):
    if city == "kobe":
        k_path = Path("data-pipeline/master/kobe_mayor_policies.json")
        if k_path.exists():
            return json.loads(k_path.read_text(encoding="utf-8"))
    targets = [
        FRONTEND_DATA / f"{city}_mayor_tracker.json",
        FRONTEND_DATA / "mayor_tracker.json" if city == "kyoto" else None
    ]
    target_f = next((p for p in targets if p and p.exists()), None)
    if not target_f:
        return []
    
    data = load_json(target_f)
    if not data:
        return []
        
    policies = []
    if isinstance(data, list):
        policies = [p for p in data if isinstance(p, dict)]
    elif isinstance(data, dict):
        for k in ["policies", "items", "pledges", "tracker", "data"]:
            if k in data and isinstance(data[k], list):
                policies = [p for p in data[k] if isinstance(p, dict)]
                break
        if not policies:
            policies = [v for v in data.values() if isinstance(v, dict)]
            
    return policies

def build_exchanges_for_topic(statements, keywords, category, limit=6):
    matched = []
    for stmt in statements:
        text_corpus = (
            str(stmt.get("statement_text", "")) + " " +
            str(stmt.get("speech_text", "")) + " " +
            str(stmt.get("statement_summary", "")) + " " +
            str(stmt.get("topic", ""))
        )
        
        score = 0
        for kw in keywords:
            if kw and kw in text_corpus:
                score += 2
        
        if stmt.get("category") == category:
            score += 1
            
        if score >= 2:
            matched.append((score, stmt))
            
    matched.sort(key=lambda x: (x[0], x[1].get("meeting_date", "")), reverse=True)
    selected = [m[1] for m in matched[:limit]]
    selected.sort(key=lambda x: x.get("meeting_date", ""))
    return selected

def create_timeline_phases(exchanges, default_lead, conflict_axes):
    if not exchanges:
        return [
            {
                "period": "現任期（2023年〜現在）",
                "phase_title": "本会議・委員会における論点審議",
                "city_stance": "市執行部は基本方針・実施計画に基づき施策を推進する姿勢を維持。",
                "key_points": [conflict_axes.split(" vs ")[0] if " vs " in conflict_axes else conflict_axes],
                "exchanges": []
            }
        ]
    
    if len(exchanges) <= 2:
        return [
            {
                "period": f"{exchanges[0].get('meeting_date', '2023-05')}〜{exchanges[-1].get('meeting_date', '現在')}",
                "phase_title": "本会議・委員会における集中論戦",
                "city_stance": "市執行部による答弁と各会派の対案・課題追及。",
                "key_points": [conflict_axes.split(" vs ")[0] if " vs " in conflict_axes else conflict_axes],
                "exchanges": exchanges
            }
        ]
    
    mid = len(exchanges) // 2
    p1_ex = exchanges[:mid]
    p2_ex = exchanges[mid:]
    
    return [
        {
            "period": f"{p1_ex[0].get('meeting_date', '2023-05')}〜{p1_ex[-1].get('meeting_date', '')}",
            "phase_title": "基本方針の提示と各会派による初期論点質疑",
            "city_stance": "計画策定および初期予算措置に関する市側の説明。",
            "key_points": [conflict_axes.split(" vs ")[0] if " vs " in conflict_axes else "初期論点"],
            "exchanges": p1_ex
        },
        {
            "period": f"{p2_ex[0].get('meeting_date', '')}〜{p2_ex[-1].get('meeting_date', '現在')}",
            "phase_title": "事業本格化に伴う実効性検証と対立論戦",
            "city_stance": "進捗と課題に対する執行部答弁および制度改善の議論。",
            "key_points": [conflict_axes.split(" vs ")[-1] if " vs " in conflict_axes else "継続論点"],
            "exchanges": p2_ex
        }
    ]

def generate_city_topics(city):
    print(f"\n--- [{city.upper()}] 政策トピック自動統合を開始 ---")
    
    stmt_file = FRONTEND_DATA / ("statements_summary.json" if city == "kyoto" else f"{city}_statements_summary.json")
    statements = load_json(stmt_file) or []
    print(f"  * 参照質疑スレッド数: {len(statements)} 件")
    
    mayor_policies = load_mayor_policies(city)
    
    evergreen_file = MASTER_DIR / "evergreen_topics.json"
    evergreen_topics = load_json(evergreen_file) or []
    
    final_topics = []
    seen_ids = set()
    
    # Tier 1: 首長重点施策トピック
    for idx, p in enumerate(mayor_policies, 1):
        pid = str(p.get("id") or p.get("pledge_id") or p.get("policy_id") or f"policy_{idx}")
        topic_id = f"{city}-mayor-{pid}"
        if topic_id in seen_ids:
            continue
        seen_ids.add(topic_id)
        
        title = p.get("headline") or p.get("title") or "市政重点施策"
        category = p.get("category", "財政・行革")
        lead = p.get("summary") or p.get("official_plan") or p.get("election_promise") or f"{title}に関する市議会での論戦ログ。"
        axes = p.get("conflict_axes") or "市長方針・公約の確実な推進 vs 実効性・財源・市民合意の追及"
        
        kw_source = list(p.get("keywords", [])) or [title]
        if p.get("election_promise"):
            kw_source.append(str(p.get("election_promise"))[:30])
        if p.get("official_plan"):
            kw_source.append(str(p.get("official_plan"))[:30])
        if p.get("budget_item"):
            kw_source.append(str(p.get("budget_item")))
            
        exchanges = build_exchanges_for_topic(statements, kw_source, category, limit=6)
        phases = create_timeline_phases(exchanges, lead, axes)
        
        status_val = p.get("stage_label") or p.get("status_text") or p.get("current_stage") or "計画進行中"
        
        final_topics.append({
            "topic_id": topic_id,
            "id": topic_id,
            "category": category,
            "title": title,
            "lead_summary": lead,
            "current_status": status_val,
            "conflict_axes": axes,
            "thread_count": sum(len(ph.get("exchanges", [])) for ph in phases),
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "timeline_phases": phases
        })
    print(f"  * Tier 1（首長施策トピック）: {len(final_topics)} 件")

    # Tier 2: 8大分野恒久エバーグリーントピック
    t2_count = 0
    for eg in evergreen_topics:
        topic_id = f"{city}-core-{eg['slug']}"
        if topic_id in seen_ids:
            continue
        seen_ids.add(topic_id)
        
        title = eg["title_template"]
        category = eg["category"]
        axes = eg["conflict_axes"]
        lead = eg["lead_template"]
        keywords = eg["keywords"]
        
        exchanges = build_exchanges_for_topic(statements, keywords, category, limit=6)
        phases = create_timeline_phases(exchanges, lead, axes)
        
        final_topics.append({
            "topic_id": topic_id,
            "id": topic_id,
            "category": category,
            "title": title,
            "lead_summary": lead,
            "current_status": "継続審議・推進中",
            "conflict_axes": axes,
            "thread_count": sum(len(ph.get("exchanges", [])) for ph in phases),
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "timeline_phases": phases
        })
        t2_count += 1
    print(f"  * Tier 2（8大分野恒久トピック）: {t2_count} 件")

    out_file = FRONTEND_DATA / ("topic_summaries.json" if city == "kyoto" else f"{city}_topic_summaries.json")
    out_file.write_text(json.dumps(final_topics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ 出力完了: {out_file.name} (計 {len(final_topics)} トピック)")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="政策トピック自動統合エンジン")
    parser.add_argument("--city", default="all", choices=["all", "kyoto", "osaka", "nagoya", "yokohama", "kobe"], help="対象都市")
    args = parser.parse_args()

    print("=" * 65)
    print("🚀 政策トピック自動統合エンジン（B×Cハイブリッド版）を実行")
    print("=" * 65)
    target_cities = [args.city] if args.city != "all" else ["kyoto", "osaka", "nagoya", "yokohama", "kobe"]
    for city in target_cities:
        generate_city_topics(city)
    print("\n🎉 政策トピック自動再構築が完了しました。")

if __name__ == "__main__":
    main()
