import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv
import io
import re
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
PUBLIC_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"
DIST_DATA_DIR = PROJECT_ROOT / "frontend" / "dist" / "data"

BASE_URL = "https://www.city.yokohama.lg.jp/shikai/koho/yokohama/dayori.html"
HEADERS = {"User-Agent": "Mozilla/5.0"}

SESSION_FALLBACK = {
    129: "令和5年 第2回市会定例会",
    130: "令和5年 第3回市会定例会",
    131: "令和5年 第4回市会定例会",
    132: "令和6年 第1回市会定例会",
    133: "令和6年 第2回市会定例会",
    134: "令和6年 第3回市会定例会",
    135: "令和6年 第4回市会定例会",
    136: "令和7年 第1回市会定例会",
    137: "令和7年 第2回市会定例会",
    138: "令和7年 第3回市会定例会",
    139: "令和7年 第4回市会定例会",
    140: "令和8年 第1回市会定例会",
    141: "令和8年 第2回市会定例会"
}

FACTION_MAP = {
    "自": "自由民主党横浜市会議員団",
    "公": "公明党横浜市会議員団",
    "立": "立憲民主党横浜市会議員団",
    "維": "日本維新の会横浜市会議員団・無所属の会",
    "共": "日本共産党横浜市会議員団",
    "国": "国民民主党横浜市会議員団",
    "民": "国民民主党横浜市会議員団",
    "よ": "地域政党よこはま横浜市会議員団",
    "太": "太田正孝",
    "井": "井上さくら",
    "市": "市民の党 日本",
    "斉": "斉藤達也",
    "無": "無所属（輿石かつ子）",
    "風": "横浜の風",
    "ゆ": "田中ゆき",
    "え": "長谷川えつこ",
    "ト": "大野トモイ",
    "大": "大野トモイ"
}

def clean_faction_name(raw_name):
    clean = re.sub(r"[\s ]+", "", str(raw_name))
    m = re.match(r"^([^（\(]+)", clean)
    prefix = m.group(1) if m else clean
    return FACTION_MAP.get(prefix, prefix)

def fetch_and_parse():
    print("🌐 ヨコハマ議会だよりのオープンデータページを取得中...")
    resp = requests.get(BASE_URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(resp.content.decode("utf-8", errors="replace"), "html.parser")

    target_csvs = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".csv"):
            m = re.search(r"(\d+)[-_]", href)
            if m and 129 <= int(m.group(1)) <= 142:
                target_csvs[int(m.group(1))] = urljoin(BASE_URL, href)

    all_bills = []

    for num in sorted(target_csvs.keys()):
        url = target_csvs[num]
        r = requests.get(url, headers=HEADERS, timeout=10)
        decoded = None
        for enc in ["utf-8-sig", "cp932", "shift_jis"]:
            try:
                decoded = r.content.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        reader = csv.reader(io.StringIO(decoded, newline=None))
        rows = [row for row in reader if any(c.strip() for c in row)]
        if not rows:
            continue

        # 1. ヘッダー行と会期名の特定
        header_idx = -1
        session_from_csv = ""
        for idx, row in enumerate(rows):
            joined = "".join(row)
            if any(h in joined for h in ["自(", "自（", "自民"]):
                header_idx = idx
                break
            elif "令和" in joined or "第" in joined:
                m_s = re.search(r"(令和[0-9０-９]+年\s*第[0-9０-９]+回\s*市会[定臨]例会)", joined)
                if m_s:
                    session_from_csv = m_s.group(1)

        session_name = session_from_csv if session_from_csv else SESSION_FALLBACK.get(num, f"第{num}号市会定例会")
        session_name = re.sub(r"\s+", " ", session_name).strip()

        header_row = rows[header_idx]

        # 2. 会派列と議決結果列の特定
        faction_cols = []
        result_col_idx = -1

        for c_idx, cell in enumerate(header_row):
            c_clean = cell.strip()
            if any(f in c_clean for f in ["自(", "自（", "公(", "公（", "立(", "立（", "維(", "維（", "共(", "共（", "国(", "民(", "よ(", "太(", "井(", "市(", "斉(", "無(", "風(", "ゆ(", "え(", "ト(", "大("]):
                faction_cols.append((c_idx, clean_faction_name(c_clean)))
            elif "結果" in c_clean or "議決" in c_clean:
                result_col_idx = c_idx

        if result_col_idx == -1:
            result_col_idx = len(header_row) - 1

        # 賛否列の先頭インデックス
        first_vote_col = faction_cols[0][0] if faction_cols else 3

        # 3. データ行の走査
        data_rows = rows[header_idx + 1:]
        current_sub_category = ""
        session_bill_count = 0

        for r in data_rows:
            # 議案名（先頭に●があるセル）を探索
            bill_title = ""
            for c_idx in range(min(first_vote_col, len(r))):
                val = r[c_idx].strip()
                if val.startswith("●"):
                    bill_title = val
                    break
                elif val and val not in ["○", "×", "-", "市長提出議案", "議員提出議案", "議員（委員会）提出議案", "議員（委員会） 提出議案"]:
                    current_sub_category = val

            # ●で始まらない場合でも、賛否列より左側に有効なテキストがあれば議案名とする
            if not bill_title:
                for c_idx in range(min(first_vote_col, len(r)) - 1, -1, -1):
                    val = r[c_idx].strip()
                    if val and val not in ["○", "×", "-", "市長提出議案", "議員提出議案", "議員（委員会）提出議案", "議員（委員会） 提出議案"]:
                        bill_title = val
                        break

            if not bill_title:
                continue

            # 議案名プレフィックスのクレンジング
            clean_title = re.sub(r"^●+", "", bill_title).strip()
            # 複数議案の場合は区切りを整える
            clean_title = re.sub(r"●+", " / ", clean_title)

            # 賛否の抽出
            votes = {}
            for col_idx, f_name in faction_cols:
                v_str = r[col_idx].strip() if col_idx < len(r) else ""
                if v_str in ["○", "◯", "〇"]:
                    votes[f_name] = "賛成"
                elif v_str in ["×", "✕", "X", "x"]:
                    votes[f_name] = "反対"
                elif v_str in ["-", "―", "欠"]:
                    votes[f_name] = "欠席"
                else:
                    votes[f_name] = "賛成"

            # 議決結果の抽出
            raw_result = r[result_col_idx].strip() if result_col_idx < len(r) else ""
            if "可決" in raw_result:
                result = "可決"
            elif "認定" in raw_result:
                result = "認定"
            elif "同意" in raw_result:
                result = "同意"
            elif "承認" in raw_result:
                result = "承認"
            elif "否決" in raw_result:
                result = "否決"
            else:
                disagree_count = sum(1 for v in votes.values() if v == "反対")
                result = "否決" if disagree_count >= 5 else "可決"

            session_bill_count += 1
            entry = {
                "session_name": session_name,
                "bill_number": f"第{session_bill_count}議案",
                "title": clean_title,
                "result": result,
                "votes": votes,
                "source_url": url
            }
            all_bills.append(entry)

        print(f"✅ No.{num:3d} ({session_name}) -> 議案: {session_bill_count:2d} 件抽出完了")

    print(f"\n📦 総議案数: {len(all_bills)} 件")

    # 保存処理
    out_public = PUBLIC_DATA_DIR / "yokohama_votes_summary.json"
    out_public.write_text(json.dumps(all_bills, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 保存完了: {out_public} ({out_public.stat().st_size:,} bytes)")

    if DIST_DATA_DIR.exists():
        out_dist = DIST_DATA_DIR / "yokohama_votes_summary.json"
        out_dist.write_text(json.dumps(all_bills, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"💾 保存完了: {out_dist}")

if __name__ == "__main__":
    fetch_and_parse()
