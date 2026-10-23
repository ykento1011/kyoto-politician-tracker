import json
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PLEDGES_JSON = DATA_DIR / "councilor_pledges.json"
VOTES_JSON = BASE_DIR.parent / "frontend" / "public" / "data" / "votes_summary.json"
OUTPUT_TRACKER_JSON = BASE_DIR.parent / "frontend" / "public" / "data" / "pledge_tracker.json"

POSSIBLE_STATEMENT_PATHS = [
    BASE_DIR.parent / "frontend" / "public" / "data" / "statements_summary.json",
    BASE_DIR.parent / "frontend" / "public" / "data" / "statements.json",
]

# 💡 選挙公報原本（ひらがな・通称名・旧字体）から議会公式漢字名への完全エイリアスマップ
ALIAS_MAP = {
    # 異体字・旧字体
    "井崎敦子": "井﨑敦子",
    "繁隆夫": "繁隆夫",
    "繫隆夫": "繁隆夫",

    # ひらがな・通称名（選挙公報表記 ➔ 公式名簿漢字名）
    "しげ隆夫": "繁隆夫",
    "西山のぶまさ": "西山信昌",
    "江村りさ": "江村理紗",
    "青野ひとし": "青野仁志",
    "宇佐美けんいち": "宇佐美賢一",
    "大津ゆうた": "大津裕太",
    "こじま信太郎": "小島信太郎",
    "島本きょうじ": "しまもと京司",
    "田中あきひで": "田中明秀",
    "寺田かずひろ": "寺田一博",
    "土方りさ": "土方莉紗",
    "はしむら芳和": "橋村芳和",
    "ますなり竜治": "増成竜治",
    "ムクダ隆知": "椋田隆知",
    "ゆあさ光彦": "湯浅光彦",
    "吉田たかお": "吉田孝雄",
    "平田けい": "平田圭",
    "河村りょう": "河村諒",
    "きくちかずひで": "きくち一秀",
    "兵藤甚一": "兵藤しんいち",
    "兵藤慎一": "兵藤しんいち",
    "津田大造": "津田大三",
    "熊澤昭真": "熊澤昭子",
    "山本じゅうじ": "山本しゅうじ",
    "植田元気": "植田げんき",
    "やまずえ啓": "やまずえあきら",
    "もりもと英情": "もりもと英靖",
    "森本英情": "もりもと英靖",
}

# 💡 主要な政策テーマの照合ルールを拡充
TOPIC_RULES = {
    "北陸新幹線": {
        "positive": ["北陸新幹線", "新幹線"],
        "negative": [],
        "context": "北陸新幹線の延伸計画（京都地下ルート・環境影響・財政負担）に関する意見書・議案です。"
    },
    "敬老乗車証": {
        "positive": ["敬老乗車証", "敬老パス"],
        "negative": [],
        "context": "敬老乗車証の自己負担引き上げや対象年齢・交付基準改定に関する条例改正案です。"
    },
    "中学校給食": {
        "positive": ["学校給食センター", "中学校給食", "学校給食", "給食費"],
        "negative": [],
        "context": "全員制中学校給食の実施に向けた給食センター整備運営契約や給食関連予算案です。"
    },
    "子どもの医療費": {
        "positive": ["子ども医療", "子ども医療費", "小児医療", "乳幼児医療"],
        "negative": ["老人", "高齢者"],
        "context": "子どもの医療費助成拡充（通院自己負担軽減・対象年齢引き上げ）に関する関連施策です。"
    },
    "議員定数・報酬": {
        "positive": ["議員報酬", "議員定数", "期末手当", "身を切る改革"],
        "negative": [],
        "context": "議員報酬や定数削減、手当支給基準に関する条例改正案です。"
    },
    "行財政改革": {
        "positive": ["行財政改革", "公債特別会計", "財政健全化", "財政再建"],
        "negative": [],
        "context": "市の財政再建計画、市公債管理、行財政改革の進捗に関する決算・予算議案です。"
    },
    "観光・宿泊税": {
        "positive": ["宿泊税", "観光振興", "オーバーツーリズム", "観光課題"],
        "negative": [],
        "context": "宿泊税の引き上げや使途拡大、観光客対策に関する議案・予算です。"
    },
    "景観・高さ規制": {
        "positive": ["都市計画", "景観", "高さ規制", "建築基準", "タワーマンション"],
        "negative": [],
        "context": "市内各地の高さ規制緩和やタワーマンション・都市再生計画に関する条例案です。"
    },
    "中小企業・地場産業": {
        "positive": ["中小企業", "地場産業", "伝統産業", "商店街", "産業振興", "賃上げ"],
        "negative": [],
        "context": "中小企業支援、伝統産業後継者育成、商店街活性化に関する経済施策です。"
    },
    "福祉・高齢者支援": {
        "positive": ["高齢者福祉", "介護保険", "認知症", "障害者", "地域包括ケア", "健康長寿"],
        "negative": [],
        "context": "介護保険制度、認知症施策、高齢者・障害者の生活支援に関する福祉施策です。"
    },
    "子育て・教育環境": {
        "positive": ["保育料", "待機児童", "学童保育", "教育環境", "不登校", "子育て支援"],
        "negative": [],
        "context": "保育体制の拡充、学童保育支援、学校教育環境の改善に関する施策です。"
    },
    "防災・インフラ": {
        "positive": ["防災", "減災", "避難所", "水害", "雨水幹線", "道路拡幅", "耐震"],
        "negative": [],
        "context": "避難所機能の強化、治水・雨水対策、道路等の都市インフラ整備に関する施策です。"
    }
}

def clean_name(name: str) -> str:
    cleaned = re.sub(r"[\s ]+", "", name)
    return ALIAS_MAP.get(cleaned, cleaned)

def get_speaker_vote_on_bill(bill, speaker_name, party_name):
    votes = bill.get("votes", {})
    spk_clean = clean_name(speaker_name)
    party_clean = party_name.replace("京都市会議員団", "").replace("市会議員団", "").replace("議員団", "")

    for k, v in votes.items():
        k_clean = clean_name(k)
        if k_clean == spk_clean or k_clean in spk_clean or spk_clean in k_clean:
            return v

    if party_clean:
        for k, v in votes.items():
            k_clean = clean_name(k).replace("京都市会議員団", "").replace("市会議員団", "").replace("議員団", "")
            if k_clean and (k_clean in party_clean or party_clean in k_clean):
                return v

    return None

def find_related_bill(pledge, votes_data, speaker_name, party_name):
    target_text = f"{pledge.get('target_issue', '')} {pledge.get('headline', '')} {pledge.get('exact_quote', '')}"
    
    matched_rule = None
    for topic_name, rule in TOPIC_RULES.items():
        if topic_name in target_text or any(p in target_text for p in rule["positive"]):
            matched_rule = rule
            break

    if not matched_rule:
        return None

    matched_bills = []
    for bill in votes_data:
        title = bill.get("title", "")
        has_pos = any(p in title for p in matched_rule["positive"])
        has_neg = any(n in title for n in matched_rule["negative"])

        if has_pos and not has_neg:
            my_vote = get_speaker_vote_on_bill(bill, speaker_name, party_name)
            if my_vote:
                v_vals = list(bill.get("votes", {}).values())
                is_contested = "賛成" in v_vals and "反対" in v_vals
                matched_bills.append({
                    "bill": bill,
                    "my_vote": my_vote,
                    "is_contested": is_contested,
                    "context_note": matched_rule["context"]
                })

    if not matched_bills:
        return None

    matched_bills.sort(key=lambda x: (1 if x["is_contested"] else 0, x["bill"].get("session_name", "")), reverse=True)
    best = matched_bills[0]
    b = best["bill"]

    return {
        "session_name": b.get("session_name", ""),
        "bill_number": b.get("bill_number", ""),
        "bill_title": b.get("title", ""),
        "my_vote": best["my_vote"],
        "result": b.get("result", "可決"),
        "source_url": b.get("source_url", ""),
        "context_note": best["context_note"]
    }

def find_related_statements(pledge, speaker_stmts, max_count=2):
    """その議員の発言ログから合致する質疑をスコア順に最大2件取得"""
    if not speaker_stmts:
        return []

    target_text = f"{pledge.get('target_issue', '')} {pledge.get('headline', '')} {pledge.get('exact_quote', '')}"

    search_keywords = []
    for topic_name, rule in TOPIC_RULES.items():
        if topic_name in target_text or any(p in target_text for p in rule["positive"]):
            search_keywords.extend(rule["positive"])
            break

    # 💡 一般キーワード抽出：重複排除し、上位8単語まで幅広く拾う
    if not search_keywords:
        words = re.findall(r"[\u4e00-\u9fa5]{2,}", target_text)
        unique_words = list(dict.fromkeys(words))
        # 抽象的すぎる語句を除外
        stop_words = {"推進", "支援", "実現", "対策", "安心", "安全", "向上", "強化", "京都", "伏見", "市民"}
        filtered = [w for w in unique_words if w not in stop_words]
        search_keywords = filtered[:8] if filtered else unique_words[:5]

    matched_stmts = []
    for stmt in speaker_stmts:
        summary = stmt.get("summary", "") or ""
        category = stmt.get("category", "") or ""
        text = stmt.get("statement_text", "") or stmt.get("text", "") or stmt.get("question", "") or ""
        topic = stmt.get("topic", "") or ""
        full_text = f"{summary} {category} {text} {topic}"

        hit_count = sum(1 for kw in search_keywords if kw in full_text)
        if hit_count > 0:
            score = (
                hit_count * 10 +
                (stmt.get("solution_score", 0) or 0) +
                (stmt.get("evidence_score", 0) or 0) +
                (stmt.get("constructive_score", 0) or 0)
            )
            matched_stmts.append((score, stmt))

    if not matched_stmts:
        return []

    matched_stmts.sort(key=lambda x: x[0], reverse=True)
    
    results = []
    for _, best_stmt in matched_stmts[:max_count]:
        official_url = (
            best_stmt.get("minute_url") or 
            best_stmt.get("url") or 
            best_stmt.get("source_url") or 
            ""
        )
        results.append({
            "date": best_stmt.get("meeting_date", ""),
            "committee": best_stmt.get("committee_name", "") or best_stmt.get("meeting_title", "本会議"),
            "summary": best_stmt.get("summary", ""),
            "speech_id": best_stmt.get("id", ""),
            "official_url": official_url
        })
    return results

def load_speaker_statements_map():
    for path in POSSIBLE_STATEMENT_PATHS:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                mapping = {}
                if isinstance(data, list) and len(data) > 0 and "statements" in data[0]:
                    for item in data:
                        spk = clean_name(item.get("speaker", ""))
                        mapping[spk] = item.get("statements", [])
                    print(f"[成功] 質疑ログ検出: {path.name} (議員数: {len(mapping)}名)")
                    return mapping

                elif isinstance(data, list) and len(data) > 0 and "summary" in data[0]:
                    for stmt in data:
                        spk = clean_name(stmt.get("speaker", ""))
                        if spk not in mapping:
                            mapping[spk] = []
                        mapping[spk].append(stmt)
                    print(f"[成功] 質疑ログフラットリスト検出: {path.name} (発言総数: {len(data)}件)")
                    return mapping
            except Exception as e:
                print(f"[警告] {path.name} の読み込みエラー: {e}")
                continue

    return {}

def main():
    if not PLEDGES_JSON.exists():
        print(f"[エラー] {PLEDGES_JSON} が存在しません。")
        return

    with open(PLEDGES_JSON, "r", encoding="utf-8") as f:
        pledges_data = json.load(f)

    votes_data = []
    if VOTES_JSON.exists():
        with open(VOTES_JSON, "r", encoding="utf-8") as f:
            votes_data = json.load(f)

    speaker_statements_map = load_speaker_statements_map()

    tracker_result = {}
    matched_vote_count = 0
    matched_stmt_count = 0

    for raw_speaker_name, info in pledges_data.items():
        norm_speaker = clean_name(raw_speaker_name)
        district = info.get("district", "")
        party = info.get("party", "")
        bulletin_pdf = info.get("bulletin_pdf", "")
        pledges = info.get("pledges", [])

        # 💡 正規化された漢字名で議事録マップから質疑を取得
        speaker_stmts = speaker_statements_map.get(norm_speaker, [])

        tracked_items = []
        for p in pledges:
            vote_record = find_related_bill(p, votes_data, norm_speaker, party)
            stmt_records = find_related_statements(p, speaker_stmts, max_count=2)

            if vote_record:
                matched_vote_count += 1
            if stmt_records:
                matched_stmt_count += len(stmt_records)

            tracked_items.append({
                "id": p.get("id", ""),
                "headline": p.get("headline", ""),
                "category": p.get("category", "市政政策"),
                "target_issue": p.get("target_issue", ""),
                "stance": p.get("stance", ""),
                "election_promise": {
                    "quote": p.get("exact_quote", ""),
                    "source_name": "令和5年 京都市議会議員選挙 公報原本",
                    "bulletin_url": bulletin_pdf
                },
                "council_vote": vote_record,
                "council_statement": stmt_records[0] if stmt_records else None,
                "council_statements": stmt_records
            })

        item_payload = {
            "district": district,
            "party": party,
            "bulletin_url": bulletin_pdf,
            "tracked_items": tracked_items
        }

        # 💡 漢字名（公式）と公報表記（ひらがな）の両方で辞書に登録（100%ヒット保証）
        tracker_result[norm_speaker] = item_payload
        if raw_speaker_name != norm_speaker:
            tracker_result[raw_speaker_name] = item_payload

    OUTPUT_TRACKER_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_TRACKER_JSON, "w", encoding="utf-8") as f:
        json.dump(tracker_result, f, ensure_ascii=False, indent=2)

    print(f"\n=== 看板公約トラッカー結合完了 ===")
    print(f"出力先: {OUTPUT_TRACKER_JSON}")
    print(f"追跡対象議員エントリ数: {len(tracker_result)} 件")
    print(f"議決マッチング総数: {matched_vote_count} 件")
    print(f"質疑発言マッチング総数: {matched_stmt_count} 件")

if __name__ == "__main__":
    main()