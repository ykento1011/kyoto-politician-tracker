import json
import os
import re
import time
import unicodedata
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

BASE_URL = "https://www2.city.kyoto.lg.jp/shikai/honkaigi"

# --- 正本マスターから動的ロード (ハードコード完全排除) ---
MASTER_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "master", "councilors_kyoto.json")
def get_official_councilors():
    if os.path.exists(MASTER_JSON):
        with open(MASTER_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            names = set()
            for c in data:
                clean_n = re.sub(r"[\s\u3000]+", "", c.get("name", ""))
                names.add(clean_n)
                names.add(c.get("name", ""))
                for al in c.get("aliases", []):
                    names.add(re.sub(r"[\s\u3000]+", "", al))
                    names.add(al)
            return list(names)
    return []

VALID_COUNCILORS = get_official_councilors()

def clean_str(text):
    if not text:
        return ""
    t = unicodedata.normalize('NFKC', str(text))
    t = t.replace('\r', '').replace('\n', '').replace(' ', '').replace('\t', '')
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
    if "自民" in name or "自由民主" in name:
        return "自由民主党京都市会議員団"
    if "共産" in name:
        return "日本共産党京都市会議員団"
    if "維" in name or "維京国" in name:
        return "維新・京都・国民市会議員団"
    if "公明" in name:
        return "公明党京都市会議員団"
    if "改新" in name:
        return "改新京都"
    if "京都党" in name:
        return "地域政党京都党市会議員団"
    if "民主" in name or "フォーラム" in name:
        return "民主・市民フォーラム"

    for c in VALID_COUNCILORS:
        if c in name:
            return "井﨑敦子" if c == "井崎敦子" else c

    name = re.sub(r'議員$', '', name)
    name = re.sub(r'\(.*?\)|（.*?）', '', name)
    return name

def parse_page_notes(soup):
    mapping = {}
    norm_text = unicodedata.normalize('NFKC', soup.get_text())
    raw_pairs = re.findall(r'([^\s=、,;；。・]+)\s*=\s*([^\s=、,;；。]+)', norm_text)

    for raw_k, raw_v in raw_pairs:
        k = clean_str(raw_k)
        v = normalize_group_or_person(raw_v)
        if not k or not v:
            continue

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
    if h in notes_map:
        return notes_map[h]
    for k, v in notes_map.items():
        if k == h or (len(k) >= 2 and k in h):
            return v
    digits = re.search(r'\d+', h)
    if digits and digits.group(0) in notes_map:
        return notes_map[digits.group(0)]
    for c in VALID_COUNCILORS:
        if c in h:
            return "井﨑敦子" if c == "井崎敦子" else c
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

# 💡 動的に公開済みの会期・議案ページ（gian*.html）を発見するクローラー
def discover_sessions():
    """
    本会議ポータル（index.html）から現任期（令和5年=R05以降）の全会期議案ページを動的取得
    """
    index_url = f"{BASE_URL}/index.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    discovered = []

    try:
        r = requests.get(index_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        r.encoding = r.apparent_encoding or "shift_jis"
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"⚠️ ポータル巡回エラー: {e}")
        return []

    # 1. 令和5年（R05）以降の kekka.html / 定例会リンクを抽出
    # リンク例: R08/kekka.html, R07/kekka.html, R06/kekka.html, R05/kekka.html
    year_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        m = re.search(r'(R\d{2})/(?:kekka|index)\.html', href)
        if m:
            r_year = m.group(1)
            year_num = int(r_year[1:])
            if year_num >= 5:  # 現任期（令和5年=R05以降すべて）
                full_url = urljoin(index_url, href)
                year_links.append((r_year, full_url))

    # 重複除去（順序維持）
    seen_urls = set()
    unique_year_links = []
    for y, u in year_links:
        if u not in seen_urls:
            seen_urls.add(u)
            unique_year_links.append((y, u))

    # 2. 各年度の kekka.html から議案ページ（gian*.html）を抽出
    for r_year, kekka_url in unique_year_links:
        try:
            rk = requests.get(kekka_url, headers=headers, timeout=10)
            if rk.status_code != 200:
                continue
            rk.encoding = rk.apparent_encoding or "shift_jis"
            soup_k = BeautifulSoup(rk.text, "html.parser")

            # ページ内の各セクション（令和○年定例会（○月市会）など）と gian リンクを紐付け
            for a in soup_k.find_all('a', href=True):
                href = a['href']
                if 'gian' in href and href.endswith('.html'):
                    gian_url = urljoin(kekka_url, href)
                    
                    # 会期名の推定（親テキストや見出しから取得）
                    session_label = ""
                    parent_block = a.find_parent(['table', 'div', 'dl', 'section', 'ul', 'tr'])
                    if parent_block:
                        block_text = unicodedata.normalize('NFKC', parent_block.get_text())
                        m_sess = re.search(r'令和\s*(\d+|元)\s*年\s*(?:定例会)?\s*(?:（|[\(])?([^\)）\n]+市会)(?:）|[\)])?', block_text)
                        if m_sess:
                            session_label = f"令和{m_sess.group(1)}年{m_sess.group(2)}"
                    
                    # 見出しから取れなかった場合のフォールバック（ファイル名 gian9.html ➔ 9月市会）
                    if not session_label:
                        m_num = re.search(r'gian(\d+)\.html', href)
                        m_cnt = m_num.group(1) if m_num else ""
                        y_int = int(r_year[1:])
                        session_label = f"令和{y_int}年{m_cnt}月市会"

                    discovered.append({
                        "session_name": session_label,
                        "url": gian_url
                    })
        except Exception as e:
            print(f"⚠️ {kekka_url} 巡回エラー: {e}")

    # 重複URL除去
    res_list = []
    seen_gian = set()
    for item in discovered:
        if item["url"] not in seen_gian:
            seen_gian.add(item["url"])
            res_list.append(item)

    return res_list

def main():
    print("==================================================")
    print("🚀 京都市会 全会派・全無所属議員 賛否スクレイパー（動的クローリング版）")
    print("==================================================")

    # 動的に現任期の公開済み議案ページを検出
    target_sessions = discover_sessions()
    print(f"🔍 検出された公開済み会期: {len(target_sessions)} 件")

    all_bills = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for item in target_sessions:
        session_name = item["session_name"]
        url = item["url"]

        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                continue
            r.encoding = r.apparent_encoding or "shift_jis"
            soup = BeautifulSoup(r.text, "html.parser")
            records, entities = fetch_and_parse_table(soup, url, session_name)

            has_jimin = "自由民主党京都市会議員団" in entities
            councilor_names = [e for e in entities if e in VALID_COUNCILORS]
            print(f"  ✅ {session_name}: {len(records)} 件 (自民: {'〇' if has_jimin else '×'} / 議員実名: {', '.join(councilor_names) if councilor_names else 'なし'})")
            all_bills.extend(records)
            time.sleep(0.3)
        except Exception as e:
            print(f"  ⚠️ {session_name} ({url}) 取得エラー: {e}")

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