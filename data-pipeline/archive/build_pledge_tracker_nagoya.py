import json
import re
from pathlib import Path

CUR = Path(".").resolve()
PROJECT_ROOT = CUR.parent if CUR.name == "data-pipeline" else CUR
BASE_DIR = PROJECT_ROOT / "data-pipeline"
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist" / "data"

PLEDGES_EXTRACTED = BASE_DIR / "data" / "nagoya_councilor_pledges.json"
STATEMENTS_FILE = FRONTEND_DATA / "nagoya_statements_summary.json"

OUTPUT_FILES = [
    FRONTEND_DATA / "pledge_tracker_nagoya.json",
    FRONTEND_DIST / "pledge_tracker_nagoya.json"
]

STRICT_TOPIC_RULES = [
    {
        "name": "学校給食無償化・完全給食",
        "triggers": ["給食", "完全給食"],
        "check": lambda full: "給食" in full and any(w in full for w in ["無償", "無料", "公費", "負担", "オーガニック", "センター", "全員", "公会計"])
    },
    {
        "name": "学校トイレ洋式化・空調",
        "triggers": ["トイレ洋式化", "学校のトイレ", "トイレの洋式化"],
        # 災害時の簡易トイレ・仮設トイレを除外
        "check": lambda full: ("学校" in full or "校" in full) and "トイレ" in full and any(w in full for w in ["洋式", "便器", "改修", "キレイ"])
    },
    {
        "name": "名古屋城木造復元",
        "triggers": ["名古屋城", "天守閣", "木造復元", "木造化"],
        "check": lambda full: any(w in full for w in ["名古屋城", "天守閣"]) and any(w in full for w in ["木造", "復元", "バリアフリー", "エレベーター"])
    },
    {
        "name": "敬老パス・高齢者交通支援",
        "triggers": ["敬老パス", "敬老バス", "敬老乗車証", "バス・タクシー", "交通費援助"],
        "check": lambda full: any(w in full for w in ["敬老パス", "敬老バス", "敬老乗車証"]) or ("タクシー" in full and any(w in full for w in ["高齢", "助成", "援助", "福祉"]))
    },
    {
        "name": "市民税減税",
        "triggers": ["市民税減税", "減税"],
        "check": lambda full: "減税" in full and any(w in full for w in ["市民税", "5%", "恒久", "税率"])
    },
    {
        "name": "議員報酬・身を切る改革",
        "triggers": ["議員報酬", "800万円", "政務活動費", "定数削減"],
        "check": lambda full: any(w in full for w in ["議員報酬", "800万", "政務活動費", "定数削減"])
    },
    {
        "name": "地下鉄・駅設備",
        "triggers": ["地下鉄", "今池駅", "本山駅", "ホーム柵", "可動式ホーム柵", "駅エレベーター"],
        "check": lambda full: ("地下鉄" in full or "駅" in full) and any(w in full for w in ["ホーム柵", "利便", "エレベーター", "トイレ", "活用", "コンコース", "可動式"])
    },
    {
        "name": "体育館空調",
        "triggers": ["体育館空調", "体育館エアコン", "体育館に空調"],
        "check": lambda full: "体育館" in full and any(w in full for w in ["空調", "エアコン"])
    },
    {
        "name": "子ども医療費",
        "triggers": ["子ども医療費", "子どもの医療費", "医療費無料化", "18歳まで無料", "医療費助成"],
        "check": lambda full: "医療費" in full and any(w in full for w in ["子ども", "18歳", "高校", "小児", "通院", "無償", "無料", "助成"])
    },
    {
        "name": "区役所・庁舎建て替え",
        "triggers": ["名東区役所", "東区役所", "複合庁舎", "緑区総合庁舎"],
        "check": lambda full: any(w in full for w in ["区役所", "庁舎"]) and any(w in full for w in ["建替", "建て替え", "整備", "移転", "複合"])
    },
    {
        "name": "千種図書館整備",
        "triggers": ["千種図書館", "アクティブライブラリー"],
        "check": lambda full: "図書館" in full or "アクティブライブラリー" in full
    },
    {
        "name": "雨水・防潮壁・治水",
        "triggers": ["雨水", "ゲリラ豪雨", "防潮壁", "治水", "津波", "高潮"],
        "check": lambda full: any(w in full for w in ["雨水", "豪雨", "防潮", "治水", "津波", "高潮", "内水", "矢板"])
    },
    {
        "name": "凶悪犯罪・防犯体制",
        "triggers": ["凶悪犯罪", "強盗", "詐欺", "防犯カメラ"],
        "check": lambda full: any(w in full for w in ["犯罪", "詐欺", "強盗", "防犯カメラ", "治安", "特殊詐欺"])
    },
    {
        "name": "介護者・高齢者支援",
        "triggers": ["介護者への支援", "介護者", "紙オムツ", "リフレッシュ制度", "家族介護"],
        # 医療的ケア児（教育問題）を完全除外
        "check": lambda full: "医療的ケア" not in full and any(w in full for w in ["介護者", "家族介護", "紙オムツ", "ヤングケアラー", "要介護", "介護保険"])
    },
    {
        "name": "障がい者福祉",
        "triggers": ["障がい施策", "障害施策", "障がい者の方に優しい", "障害者福祉"],
        "check": lambda full: any(w in full for w in ["障害者", "障がい者", "障害福祉", "障がい福祉", "手帳", "就労継続"])
    },
    {
        "name": "リニア・商店街振興",
        "triggers": ["リニア", "商店街"],
        "check": lambda full: "リニア" in full or "商店街" in full
    }
]

def clean_name(name: str) -> str:
    return re.sub(r"[\s\u3000]+", "", name)

def find_related_statements_final(pledge, speaker_stmts, max_count=2):
    if not speaker_stmts:
        return []

    target_text = f"{pledge.get('target_issue', '')} {pledge.get('headline', '')} {pledge.get('exact_quote', '')}"
    
    matched_rule = None
    for rule in STRICT_TOPIC_RULES:
        if any(trig in target_text for trig in rule["triggers"]):
            matched_rule = rule
            break

    candidates = []
    
    if matched_rule:
        for stmt in speaker_stmts:
            s_sum = stmt.get("statement_summary") or stmt.get("summary") or stmt.get("question_summary") or ""
            s_txt = stmt.get("statement_text") or stmt.get("question_text") or stmt.get("text") or ""
            full_text = f"{s_sum} {s_txt[:350]}"
            
            if matched_rule["check"](full_text):
                score = sum(full_text.count(t) for t in matched_rule["triggers"]) * 10
                candidates.append((score, stmt))
    else:
        # ルールにない個別公約：4文字以上の明確な名詞の一致のみ許可
        stop_words = {
            "推進", "支援", "実現", "対策", "安心", "安全", "向上", "強化", 
            "名古屋", "要望", "市民", "取組", "充実", "創設", "見直し", "徹底",
            "促進", "目指す", "課題", "問題", "事業", "地域", "社会", "生活", "対応",
            "挑戦", "発展", "確立", "確保", "継続", "整備", "福祉", "環境", "経済", "教育", "施策"
        }
        words = re.findall(r"[\u4e00-\u9fa5]{3,}|[ァ-ンヴー]{3,}|[A-Za-z]{3,}", target_text)
        core_keywords = [w for w in words if w not in stop_words]
        
        if core_keywords:
            for stmt in speaker_stmts:
                s_sum = stmt.get("statement_summary") or stmt.get("summary") or stmt.get("question_summary") or ""
                s_txt = stmt.get("statement_text") or stmt.get("question_text") or stmt.get("text") or ""
                full_text = f"{s_sum} {s_txt[:300]}"
                
                hits = [kw for kw in core_keywords if kw in full_text]
                if len(hits) >= 2:
                    score = sum(len(h) * 2 for h in hits)
                    candidates.append((score, stmt))

    if not candidates:
        return []

    candidates.sort(key=lambda x: (x[0], x[1].get("meeting_date", "")), reverse=True)

    results = []
    for _, best_stmt in candidates[:max_count]:
        official_url = (
            best_stmt.get("official_url") or 
            best_stmt.get("source_url") or 
            best_stmt.get("url") or 
            ""
        )
        s_date = best_stmt.get("meeting_date") or best_stmt.get("date") or ""
        s_committee = best_stmt.get("meeting_name") or best_stmt.get("committee") or best_stmt.get("meeting_title") or "名古屋市会 本会議・委員会"
        s_sum = best_stmt.get("statement_summary") or best_stmt.get("summary") or best_stmt.get("question_summary") or best_stmt.get("statement_text", "")
        
        results.append({
            "date": s_date,
            "committee": s_committee,
            "summary": s_sum[:200] + ("..." if len(s_sum) > 200 else ""),
            "speech_id": str(best_stmt.get("id") or best_stmt.get("speech_id") or ""),
            "official_url": official_url
        })
    return results

def main():
    print("=== 名古屋市議 看板公約トラッカー 最終完全純化ビルド ===")

    if not PLEDGES_EXTRACTED.exists():
        fallback_pledges = FRONTEND_DATA / "pledge_tracker_nagoya_2.json"
        pledges_path = fallback_pledges if fallback_pledges.exists() else None
    else:
        pledges_path = PLEDGES_EXTRACTED

    if not pledges_path:
        print("❌ 公約元データが見つかりません。")
        return

    raw_pledge_data = json.loads(pledges_path.read_text(encoding="utf-8"))
    councilor_pledges_list = raw_pledge_data.get("councilors", []) if isinstance(raw_pledge_data, dict) else raw_pledge_data
    statements = json.loads(STATEMENTS_FILE.read_text(encoding="utf-8")) if STATEMENTS_FILE.exists() else []

    stmts_by_speaker = {}
    for s in statements:
        spk = s.get("speaker", "").strip()
        c_spk = clean_name(spk)
        stmts_by_speaker.setdefault(c_spk, []).append(s)

    pledge_tracker = {}

    for c in councilor_pledges_list:
        raw_name = c.get("speaker") or c.get("name") or ""
        c_name = clean_name(raw_name)
        if not c_name:
            continue

        district = c.get("district", "")
        party = c.get("party") or c.get("partyGroup", "")
        bulletin_url = c.get("bulletin_url", "")
        raw_pledges = c.get("pledges", [])
        my_stmts = stmts_by_speaker.get(c_name, [])

        tracked_items = []
        for idx, p in enumerate(raw_pledges):
            p_id = p.get("id") or f"p_{idx+1}"
            cat = p.get("category", "くらし・環境・エネルギー")
            target_issue = p.get("target_issue", "")
            headline = p.get("headline", "")
            exact_quote = p.get("exact_quote") or p.get("quote") or ""
            stance = p.get("stance", "推進・拡充")
            item_bulletin_url = p.get("bulletin_url") or bulletin_url

            related_stmts = find_related_statements_final(p, my_stmts, max_count=2)
            main_stmt = related_stmts[0] if related_stmts else None

            tracked_items.append({
                "id": f"pledge_nagoya_{c_name}_{idx+1}",
                "headline": headline,
                "category": cat,
                "target_issue": target_issue,
                "stance": stance,
                "election_promise": {
                    "quote": exact_quote,
                    "source_name": "令和5年 名古屋市議会議員一般選挙 公式選挙公報",
                    "bulletin_url": item_bulletin_url
                },
                "council_vote": None,
                "council_statement": main_stmt,
                "council_statements": related_stmts
            })

        councilor_data = {
            "district": district,
            "party": party,
            "bulletin_url": bulletin_url,
            "tracked_items": tracked_items
        }

        pledge_tracker[raw_name] = councilor_data
        if c_name != raw_name:
            pledge_tracker[c_name] = councilor_data

    for out_p in OUTPUT_FILES:
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(pledge_tracker, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 生成・保存完了: {out_p.resolve()}")

    print("🎉 最終完全純化ビルドが完了しました！")

if __name__ == "__main__":
    main()