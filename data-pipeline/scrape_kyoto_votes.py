import json
import os
import re
import time
import unicodedata
from bs4 import BeautifulSoup
import requests

BASE_URL = "https://www2.city.kyoto.lg.jp/shikai/honkaigi"

TARGET_SESSIONS = [
    ("R05", "5", "令和5年5月市会"),
    ("R05", "7", "令和5年7月市会"),
    ("R05", "9", "令和5年9月市会"),
    ("R05", "11", "令和5年11月市会"),
    ("R05", "3", "令和6年3月市会"),  # 💡 '2' から '3' に変更（2024年市長選に伴う3月開会）    ("R06", "5", "令和6年5月市会"),
    ("R06", "7", "令和6年7月市会"),
    ("R06", "9", "令和6年9月市会"),
    ("R06", "11", "令和6年11月市会"),
    ("R06", "2", "令和7年2月市会"),
    ("R07", "5", "令和7年5月市会"),
    ("R07", "7", "令和7年7月市会"),
    ("R07", "9", "令和7年9月市会"),
    ("R07", "11", "令和7年11月市会"),
    ("R07", "2", "令和8年2月市会"),
    ("R08", "5", "令和8年5月市会"),
    ("R08", "7", "令和8年7月市会"),
    ("R08", "9", "令和8年9月市会"),
]

VALID_COUNCILORS = [
    "青野仁志", "赤阪仁", "天方ひろゆき", "井﨑敦子", "井崎敦子", "井上よしひろ", "宇佐美賢一",
    "江村理紗", "えもとかよこ", "大津裕太", "おんづか功", "片桐直哉", "加藤あい",
    "加藤昌洋", "神谷修平", "河合ようこ", "かわしま優子", "河村諒", "きくち一秀",
    "北尾ゆか", "北川みき", "北山ただお", "久保田正紀", "くまざわ真昭", "くらた共子",
    "こうち大輔", "小島信太郎", "さくらい泰広", "繁隆夫", "しまもと京司", "下村あきら",
    "菅谷浩平", "田中明秀", "田中たかのり", "谷口みゆき", "玉本なるみ", "津田大三",
    "寺田一博", "とがし豊", "富きくお", "中高しゅうじ", "中野洋一", "中村まり",
    "西野さち子", "西村義直", "西山信昌", "橋村芳和", "土方莉紗", "兵藤しんいち",
    "平井良人", "平田圭", "平山たかお", "平山よしかず", "増成竜治", "松田けい子",
    "みちはた弘之", "椋田隆知", "森かれん", "森田守", "森田ゆみ子", "もりもと英靖",
    "山田こうじ", "やまね智史", "山本恵一", "山本しゅうじ", "山本陽子", "湯浅光彦",
    "吉田孝雄"
]

def clean_str(text):
    if not text:
        return ""
    t = unicodedata.normalize('NFKC', str(text))
    t = t.replace('\r', '').replace('\n', '').replace(' ', '').replace(' ', '').replace('\t', '')
    return t.strip()

def normalize_vote(val):
    v = clean_str(val)
    if v in ["〇", "○", "◯", "O", "o"]:
        return "賛成"
    elif v in ["×", "✕", "x", "X"]:
        return "反対"
    elif v in ["-", "―", "欠席", "退席", "棄権"]:
        return "退席・棄権"
    return None

def normalize_group_or_person(raw_name):
    name = clean_str(raw_name)

    # 1. 自民党最優先
    if "自民" in name or "自由民主" in name:
        return "自由民主党京都市会議員団"
    # 2. 共産党
    if "共産" in name:
        return "日本共産党京都市会議員団"
    # 3. 維新
    if "維" in name or "維京国" in name:
        return "維新・京都・国民市会議員団"
    # 4. 公明党
    if "公明" in name:
        return "公明党京都市会議員団"
    # 5. 改新京都
    if "改新" in name:
        return "改新京都"
    # 6. 京都党
    if "京都党" in name:
        return "地域政党京都党市会議員団"
    # 7. 民主・市民フォーラム
    if "民主" in name or "フォーラム" in name:
        return "民主・市民フォーラム"

    # 8. 議員個人名
    for c in VALID_COUNCILORS:
        if c in name:
            return "井﨑敦子" if c == "井崎敦子" else c

    name = re.sub(r'議員$', '', name)
    name = re.sub(r'\(.*?\)|（.*?）', '', name)
    return name

def parse_page_notes(soup):
    """
    注記から「会派略称・無所属番号」と「正式名称・議員名」を確実に抽出
    """
    mapping = {}
    norm_text = unicodedata.normalize('NFKC', soup.get_text())

    # = の前後のペアを直接キャプチャ（空白区切り・カンマ区切りの両方に対応）
    raw_pairs = re.findall(r'([^\s=、,;；。・]+)\s*=\s*([^\s=、,;；。]+)', norm_text)

    for raw_k, raw_v in raw_pairs:
        k = clean_str(raw_k)
        v = normalize_group_or_person(raw_v)
        if not k or not v:
            continue

        # キーのクレンジング（無所属の抽出）
        if "無所属" in k:
            all_m = re.findall(r'無所属(?:\([0-9]+\)|\[[0-9]+\]|[0-9]+)?', k)
            if all_m:
                k_clean = all_m[-1].replace("(", "").replace(")", "").replace("[", "").replace("]", "")
                mapping[k_clean] = v
                digits = re.search(r'\d+', k_clean)
                if digits:
                    mapping[digits.group(0)] = v
            else:
                mapping["無所属"] = v
        else:
            # 会派略称
            for p in ["自民", "共産", "維新", "公明", "民主", "改新", "京都党"]:
                if p in k:
                    mapping[p] = v
                    break

    return mapping

def normalize_table_to_grid(table):
    rows = table.find_all('tr')
    grid = []

    for r_idx, tr in enumerate(rows):
        while len(grid) <= r_idx:
            grid.append([])

        c_idx = 0
        cells = tr.find_all(['th', 'td'])
        for cell in cells:
            while c_idx < len(grid[r_idx]) and grid[r_idx][c_idx] is not None:
                c_idx += 1

            rowspan = int(cell.get('rowspan', 1))
            colspan = int(cell.get('colspan', 1))
            text = clean_str(cell.get_text())

            while len(grid) < r_idx + rowspan:
                grid.append([])

            for r_offset in range(rowspan):
                target_r = r_idx + r_offset
                while len(grid[target_r]) < c_idx + colspan:
                    grid[target_r].append(None)
                for c_offset in range(colspan):
                    grid[target_r][c_idx + c_offset] = {
                        'text': text,
                        'is_th': cell.name == 'th'
                    }

            c_idx += colspan

    return grid

def resolve_column_entity(header_text, notes_map):
    h = clean_str(header_text)

    # 1. 完全一致
    if h in notes_map:
        return notes_map[h]

    # 2. 注記マップの部分一致（キーがヘッダーに含まれるか、ヘッダーがキーに含まれるか）
    for k, v in notes_map.items():
        if k == h or (len(k) >= 2 and k in h):
            return v

    # 3. 数字のみの列（「1」「2」など）がヘッダーにある場合
    digits = re.search(r'\d+', h)
    if digits and digits.group(0) in notes_map:
        return notes_map[digits.group(0)]

    # 4. 議員ホワイトリスト直結
    for c in VALID_COUNCILORS:
        if c in h:
            return "井﨑敦子" if c == "井崎敦子" else c

    # 5. 会派名判定
    return normalize_group_or_person(h)

def fetch_and_parse_table(soup, url, session_name):
    notes_map = parse_page_notes(soup)
    records = []
    all_col_entities = set()
    tables = soup.find_all('table')

    for table in tables:
        grid = normalize_table_to_grid(table)
        if len(grid) < 2:
            continue

        header_rows = 0
        for row in grid:
            th_count = sum(1 for c in row if c and c.get('is_th'))
            if th_count > len(row) * 0.4:
                header_rows += 1
            else:
                break
        header_rows = max(1, min(header_rows, 2))

        num_cols = len(grid[0]) if grid else 0
        synthesized_headers = []
        for c in range(num_cols):
            parts = []
            for r in range(header_rows):
                cell_info = grid[r][c]
                t = cell_info['text'] if cell_info else ""
                if t and t not in parts:
                    parts.append(t)
            synthesized_headers.append("".join(parts))

        if not any("件名" in h or "議案" in h for h in synthesized_headers):
            continue

        title_idx = -1
        result_idx = -1
        number_idx = -1
        col_entity_map = {}

        for c_idx, h_text in enumerate(synthesized_headers):
            if "番号" in h_text:
                number_idx = c_idx
            elif "件名" in h_text or "議案" in h_text:
                title_idx = c_idx
            elif "結果" in h_text or "審議結果" in h_text:
                result_idx = c_idx
            else:
                entity = resolve_column_entity(h_text, notes_map)
                if entity and entity not in ["件名", "番号", "結果", "付帯決議等"]:
                    col_entity_map[c_idx] = entity
                    all_col_entities.add(entity)

        for r_idx in range(header_rows, len(grid)):
            row = grid[r_idx]
            if len(row) < num_cols:
                continue

            title = row[title_idx]['text'] if title_idx >= 0 and row[title_idx] else ""
            result = row[result_idx]['text'] if result_idx >= 0 and row[result_idx] else ""
            bill_num = row[number_idx]['text'] if number_idx >= 0 and row[number_idx] else ""

            if not title or title in ["〇", "×", "件名", "議案件名"]:
                continue
            if bill_num in ["〇", "×", "番号"]:
                continue

            votes = {}
            for col_idx, entity_name in col_entity_map.items():
                if col_idx < len(row) and row[col_idx]:
                    vote_val = normalize_vote(row[col_idx]['text'])
                    if vote_val:
                        if entity_name in VALID_COUNCILORS or "議員団" in entity_name or entity_name in ["改新京都", "民主・市民フォーラム"]:
                            votes[entity_name] = vote_val

            if votes:
                records.append({
                    "session_name": session_name,
                    "bill_number": bill_num,
                    "title": title,
                    "result": result,
                    "votes": votes,
                    "source_url": url
                })

    return records, all_col_entities

def scrape_session(year, month, session_name):
    url = f"{BASE_URL}/{year}/gian{month}.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    res = None
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r
            actual_url = url
        elif r.status_code == 404 and month in ["2", "3"]:
            alt_month = "3" if month == "2" else "2"
            alt_url = f"{BASE_URL}/{year}/gian{alt_month}.html"
            r_alt = requests.get(alt_url, headers=headers, timeout=10)
            if r_alt.status_code == 200:
                res = r_alt
                actual_url = alt_url
    except Exception as e:
        print(f"  ⚠️ {url} 通信エラー: {e}")
        return []

    if not res:
        print(f"  ⚠️ {session_name}: ページなし（スキップ）")
        return []

    res.encoding = res.apparent_encoding or "shift_jis"
    soup = BeautifulSoup(res.text, "html.parser")
    records, entities = fetch_and_parse_table(soup, actual_url, session_name)

    has_jimin = "自由民主党京都市会議員団" in entities
    councilor_names = [e for e in entities if e in VALID_COUNCILORS]
    print(f"  ✅ {session_name}: {len(records)} 件 (自民: {'〇' if has_jimin else '×'} / 議員実名: {', '.join(councilor_names) if councilor_names else 'なし'})")
    return records

def main():
    print("==================================================")
    print("🚀 京都市会 全会派・全無所属議員 賛否スクレイパー（完全版）")
    print("==================================================")
    all_bills = []

    for year, month, session_name in TARGET_SESSIONS:
        bills = scrape_session(year, month, session_name)
        all_bills.extend(bills)
        time.sleep(0.3)

    output_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "votes_summary.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_bills, f, ensure_ascii=False, indent=2)

    print("==================================================")
    print(f"🎉 完了: 累計 {len(all_bills):,} 件の議案データを保存しました。")
    print(f"📁 保存先: {os.path.abspath(output_path)}")
    print("==================================================")

if __name__ == "__main__":
    main()