import os
import sys
import json
import re
from pathlib import Path

# パス解決（カレントディレクトリがルートでも data-pipeline でも対応）
ROOT = Path(".").resolve()
if ROOT.name == "data-pipeline":
    ROOT = ROOT.parent

# Python検索パスに data-pipeline と ルート を追加
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(ROOT))

FRONTEND_DATA = ROOT / "frontend" / "public" / "data"
EXTRACTED_JSON = ROOT / "data-pipeline" / "data" / "osaka_councilor_pledges.json"
STATEMENTS_PATH = FRONTEND_DATA / "osaka_statements_summary.json"
VOTES_PATH = FRONTEND_DATA / "osaka_votes_summary.json"

try:
    from build_pledge_tracker_osaka import COUNCILORS_MASTER
except ImportError:
    # 直接ロードのフォールバック
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_pledge_tracker_osaka", ROOT / "data-pipeline" / "build_pledge_tracker_osaka.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    COUNCILORS_MASTER = mod.COUNCILORS_MASTER

print("🚀 大阪市議会 公約原本トラッカー統合処理を開始します...")

# 1. 公報抽出データのロード
if not EXTRACTED_JSON.exists():
    print(f"❌ {EXTRACTED_JSON} が見つかりません。")
    exit(1)

with open(EXTRACTED_JSON, "r", encoding="utf-8") as f:
    extracted_data = json.load(f)

# 2. 質疑データおよび議決データのロード
statements = []
if STATEMENTS_PATH.exists():
    with open(STATEMENTS_PATH, "r", encoding="utf-8") as f:
        statements = json.load(f)

votes_data = []
if VOTES_PATH.exists():
    with open(VOTES_PATH, "r", encoding="utf-8") as f:
        votes_data = json.load(f)

# 議員ごとの発言ログをプール
councilor_speeches = {}
for s in statements:
    spk = s.get("speaker") or s.get("speaker_name") or ""
    clean_spk = spk.replace(" ", "").replace(" ", "")
    if clean_spk not in councilor_speeches:
        councilor_speeches[clean_spk] = []
    councilor_speeches[clean_spk].append(s)

# 3. 現職81名マスタと公報抽出データの名寄せ
extracted_index = {}
for raw_name, info in extracted_data.items():
    c_name = raw_name.replace(" ", "").replace(" ", "")
    district = info.get("district", "")
    extracted_index[c_name] = info
    extracted_index[(district, c_name)] = info

def find_extracted_for_councilor(c):
    c_name = c["name"].replace(" ", "").replace(" ", "")
    district = c["district"]
    kana = c["kana"]

    # 1. 漢字完全一致
    if c_name in extracted_index:
        return extracted_index[c_name]
    if (district, c_name) in extracted_index:
        return extracted_index[(district, c_name)]

    # 2. 同じ選挙区内で苗字一致や部分一致（例: 住之江区の「松崎」＝「松崎 とおる」）
    surname = c_name[:2] if len(c_name) >= 2 else c_name
    for key, info in extracted_index.items():
        if isinstance(key, tuple):
            d, name_key = key
            if d == district and (surname in name_key or name_key in c_name):
                return info

    # 3. かな表記一致
    for raw_name, info in extracted_data.items():
        clean_raw = raw_name.replace(" ", "").replace(" ", "")
        if info.get("district") == district:
            if surname in clean_raw:
                return info
    return None

def is_party_match(p1, p2):
    if not p1 or not p2: return False
    if p1 in p2 or p2 in p1: return True
    core_kw = ["維新", "公明", "共産", "自民", "自由民主", "立憲", "国民民主", "アップデート"]
    for kw in core_kw:
        if kw in p1 and kw in p2:
            return True
    return False

# 4. トラッカー辞書の構築
pledge_tracker = {}
matched_councilors = 0

for c in COUNCILORS_MASTER:
    c_name = c["name"]
    clean_name = c_name.replace(" ", "").replace(" ", "")
    district = c["district"]
    party = c["party"]
    kana = c["kana"]

    ext_info = find_extracted_for_councilor(c)
    my_speeches = councilor_speeches.get(clean_name, [])

    tracked_items = []
    bulletin_url = "https://www.city.osaka.lg.jp/contents/wdu240/shikai/kouhosha/"

    if ext_info and ext_info.get("pledges"):
        matched_councilors += 1
        bulletin_url = ext_info.get("bulletin_pdf", bulletin_url)
        extracted_pledges = ext_info.get("pledges", [])

        for idx, p in enumerate(extracted_pledges):
            cat = p.get("category", "くらし・環境・エネルギー")
            headline = p.get("headline", "")
            target_issue = p.get("target_issue", "")
            stance = p.get("stance", "推進・拡充")
            exact_quote = p.get("exact_quote", "")
            pledge_id = f"pledge_osaka_{clean_name}_{idx+1}"

            # 関連質疑の機械突合
            matched_speeches = []
            keywords = [w for w in re.split(r"[\s、。・／/（）\(\)]", target_issue + " " + headline) if len(w) >= 2]
            for sp in my_speeches:
                sp_cat = sp.get("category", "")
                sp_sum = sp.get("summary", "")
                sp_sub = sp.get("subject", "")
                
                is_cat_match = (sp_cat == cat)
                is_word_match = any(kw in sp_sum or kw in sp_sub for kw in keywords)
                if is_word_match or (is_cat_match and len(matched_speeches) < 2):
                    matched_speeches.append(sp)

            council_statements = []
            for sp in matched_speeches[:5]:
                speech_id = sp.get("speech_id") or sp.get("id") or ""
                council_statements.append({
                    "date": sp.get("meeting_date") or sp.get("date") or "2024-03-01",
                    "committee": sp.get("meeting_title") or sp.get("committee") or "大阪市会",
                    "summary": sp.get("summary") or sp.get("content") or "",
                    "speech_id": str(speech_id),
                    "official_url": sp.get("official_url") or "https://www.city.osaka.lg.jp/shikai/"
                })

            main_stmt = council_statements[0] if council_statements else None

            # 関連議案（議決）の突合
            matched_vote = None
            for b in votes_data:
                b_title = b.get("title", "")
                if any(kw in b_title for kw in keywords if len(kw) >= 3):
                    votes_dict = b.get("votes", {})
                    for group_name, vote_val in votes_dict.items():
                        if is_party_match(group_name, party):
                            matched_vote = {
                                "bill_title": b_title,
                                "bill_number": b.get("bill_number", ""),
                                "result": b.get("result", ""),
                                "stance": vote_val,
                                "source_url": b.get("source_url", "")
                            }
                            break
                if matched_vote:
                    break

            tracked_items.append({
                "id": pledge_id,
                "headline": headline,
                "category": cat,
                "target_issue": target_issue,
                "stance": stance,
                "election_promise": {
                    "quote": exact_quote,
                    "source_name": "令和5年 大阪市議会議員一般選挙 公報原本",
                    "bulletin_url": bulletin_url
                },
                "council_vote": matched_vote,
                "council_statement": main_stmt,
                "council_statements": council_statements
            })
    else:
        for idx, (cat, title) in enumerate(c.get("themes", [])):
            tracked_items.append({
                "id": f"pledge_osaka_{clean_name}_{idx+1}",
                "headline": title,
                "category": cat,
                "target_issue": title,
                "stance": "推進・拡充",
                "election_promise": {
                    "quote": exact_quote if exact_quote else "",
                    "source_name": "令和5年 大阪市議会議員一般選挙 公報原本",
                    "bulletin_url": bulletin_url
                },
                "council_vote": None,
                "council_statement": None,
                "council_statements": []
            })

    c_payload = {
        "district": district,
        "party": party,
        "bulletin_url": bulletin_url,
        "tracked_items": tracked_items
    }

    pledge_tracker[c_name] = c_payload
    pledge_tracker[clean_name] = c_payload
    pledge_tracker[kana] = c_payload
    if ext_info:
        raw_spk = ext_info.get("raw_speaker", "")
        if raw_spk:
            pledge_tracker[raw_spk] = c_payload
            pledge_tracker[raw_spk.replace(" ", "")] = c_payload

print(f"✅ 公報原本との名寄せ成功: 現職81名中 {matched_councilors} 名と直結")

# 5. フロントエンド配下の全パスへ書き出し
out_paths = [
    FRONTEND_DATA / "osaka" / "pledge_tracker.json",
    FRONTEND_DATA / "pledge_tracker_osaka.json",
    FRONTEND_DATA / "osaka_pledge_tracker.json"
]

for p in out_paths:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(pledge_tracker, f, ensure_ascii=False, indent=2)
    print(f"📁 書き出し完了: {p.relative_to(ROOT)}")

print("\n🎉 公報原本引用付きの公約トラッカー再生成が完了しました！")
