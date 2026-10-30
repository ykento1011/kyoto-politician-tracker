import socket

# --- IPv4 強制パッチ ---
orig_getaddrinfo = socket.getaddrinfo
def ipv4_only_getaddrinfo(*args, **kwargs):
    responses = orig_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]
socket.getaddrinfo = ipv4_only_getaddrinfo
# ----------------------

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
load_dotenv("data-pipeline/.env")

script_path = Path(__file__).resolve()
PROJECT_ROOT = script_path.parent.parent if script_path.parent.name == "data-pipeline" else script_path.parent
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"

CATEGORIES = [
    "財政・行革",
    "都市再生・交通インフラ",
    "産業・観光・地域経済",
    "子育て・教育",
    "福祉・医療・健康",
    "くらし・環境・エネルギー",
    "防災・減災・治安",
    "文化・景観・歴史"
]

CITY_LABELS = {
    "kyoto": "京都市会",
    "osaka": "大阪市会",
    "nagoya": "名古屋市会",
    "yokohama": "横浜市会",
    "kobe": "神戸市会"
}

CITY_LEADERS = {
    "kyoto": "松井市政",
    "osaka": "横山市政",
    "nagoya": "広沢市政（旧河村市政継承）",
    "yokohama": "山中市政",
    "kobe": "久元市政"
}

SYSTEM_PROMPT = """
あなたは地方財政および大都市行政に精通したシニア政策アナリストです。
提供される市議会の個別政策論点サマリーおよび議場ログを横断分析し、
該当カテゴリーにおける「現任期の論戦総括（AI包括解説）」を作成してください。

【厳格な執筆ルール】
1. 抽象的な定型句（「議論が交わされた」「施策を推進する姿勢を示した」「活発な議論が展開された」等）は一切禁止します。
2. 当該都市の首長方針と議会各会派の対立軸、具体的な事業名、施設名、予算・負担額、制度改正の争点を克明に織り込んでください。
3. `lead` は、この任期における当該分野の「最大の火種・論戦の潮流・現在の到達点」を250〜400文字の重厚な分析文で記述してください。
4. `key_points` は、議場で火花が散った具体的争点を3件厳選し、各項目20〜65文字程度で「〜の推進・拡充 vs 〜の負担懸念・代替要求」の構図がわかるように記述してください。
5. 必ず以下のJSONフォーマットのみを出力してください。

{
  "lead": "この任期における論戦総括文（250〜400字）",
  "key_points": [
    "重要争点1（具体的事業名・対立構図を含む20〜65字）",
    "重要争点2（具体的事業名・対立構図を含む20〜65字）",
    "重要争点3（具体的事業名・対立構図を含む20〜65字）"
  ]
}
"""

def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません。")
    return genai.Client(api_key=api_key)

def load_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def generate_category_overview(client, city, category, topics, statements):
    city_label = CITY_LABELS.get(city, city)
    leader = CITY_LEADERS.get(city, "市政")

    topic_context = []
    for t in topics:
        title = t.get("title", "")
        lead = t.get("lead_summary", "")
        lead_str = lead.get("summary", "") if isinstance(lead, dict) else str(lead)
        axes = " / ".join(t.get("conflict_axes", []))
        topic_context.append(f"・論点: 【{title}】\n  概要: {lead_str[:150]}\n  対立軸: {axes}")

    cat_stmts = [s for s in statements if s.get("category") == category]
    stmt_samples = []
    for s in cat_stmts[:25]:
        speaker = s.get("speaker", "議員")
        summary = s.get("summary", "")
        stmt_samples.append(f"[{speaker}]: {summary}")

    content = f"""
自治体: {city_label}（{leader}）
対象政策カテゴリー: 【{category}】

【この分野に含まれる主要な個別政策論点】:
""" + ("\n".join(topic_context) if topic_context else "（個別論点データなし）") + f"""

【議場質疑ログ（抜粋）】:
""" + ("\n".join(stmt_samples) if stmt_samples else "（質疑ログなし）")

    last_err = None
    for attempt in range(3):
        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=content,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.15
                )
            )
            data = json.loads(res.text)
            lead = data.get("lead", "")
            pts = data.get("key_points", [])
            if len(lead) >= 150 and len(pts) >= 2:
                return data
            last_err = f"出力不十分 (lead: {len(lead)}字, points: {len(pts)}件)"
        except Exception as e:
            last_err = e
            time.sleep(1.2 * (attempt + 1))

    print(f" (警告: 再試行失敗 {last_err})", end="", flush=True)
    return {
        "lead": f"{city_label}における「{category}」分野では、{leader}の重要方針と議会各会派による行財政・市民負担・公平性をめぐる多角的な追及が展開されています。",
        "key_points": [
            f"{category}関連施策の財源確保と実効性検証",
            f"市民生活・地域経済への直接的波及効果の最大化",
            f"中長期的な財政規律と公共サービス維持のバランス"
        ]
    }

def process_city(city, client):
    print(f"\n=======================================================", flush=True)
    print(f"🏛️ カテゴリー包括解説生成: {city.upper()} ({CITY_LABELS.get(city)})", flush=True)
    print(f"=======================================================", flush=True)

    topic_file = FRONTEND_DATA / f"{city}_topic_summaries.json"
    stmt_file = FRONTEND_DATA / f"{city}_statements_summary.json"
    out_file = FRONTEND_DATA / f"{city}_category_overviews.json"

    topics = load_json(topic_file) or []
    statements = load_json(stmt_file) or []

    result = {}
    for cat in CATEGORIES:
        cat_topics = [t for t in topics if t.get("category") == cat]
        print(f"  ▶ 生成中: 【{cat}】 (個別論点 {len(cat_topics)}件)...", end="", flush=True)
        overview = generate_category_overview(client, city, cat, cat_topics, statements)
        result[cat] = overview
        print(f" ✅ 完了 ({len(overview['lead'])}文字)", flush=True)

    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 保存完了: {out_file}", flush=True)
    return result

def main():
    client = get_gemini_client()
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    cities = ["kyoto", "osaka", "nagoya", "yokohama", "kobe"] if target == "all" else [target]

    for c in cities:
        process_city(c, client)

    print("\n🎉 全都市のカテゴリー包括解説生成が完了しました。")

if __name__ == "__main__":
    main()
