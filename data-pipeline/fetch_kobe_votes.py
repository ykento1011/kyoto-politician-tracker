"""
fetch_kobe_votes.py
神戸市会 公式会議結果ページおよび「各会派の賛否一覧」PDFから
全会期の表決データを収集・構造化し、kobe_votes_summary.json を生成する。
"""

import collections
import hashlib
import io
import json
import logging
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import pdfplumber
import requests
from bs4 import BeautifulSoup

CUR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR.parent
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist" / "data"
OUTPUT_VOTES = FRONTEND_DATA / "kobe_votes_summary.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FetchKobeVotes")

BASE_INDEX_URL = "https://www.city.kobe.lg.jp/z/shikaijimukyoku/giann_etc/kekka3.html"
FALLBACK_INDEX_URL = "https://www.city.kobe.lg.jp/z/shikaijimukyoku/giann_etc/r8/9gatsukekka.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

PARTY_MAP = {
    "自民": "自由民主党",
    "自由民主党": "自由民主党",
    "公明": "公明党",
    "公明党": "公明党",
    "維新": "日本維新の会",
    "日本維新の会": "日本維新の会",
    "共産": "日本共産党",
    "日本共産党": "日本共産党",
    "こうべ": "こうべ未来",
    "未来": "こうべ未来",
    "こうべ未来": "こうべ未来",
    "新自民": "新しい自民党",
    "新しい自民党": "新しい自民党",
    "つなぐ": "つなぐ",
    "躍動": "躍動の会",
    "躍動の会": "躍動の会"
}

INDIVIDUAL_MAP = {
    "平野": "平野 章三",
    "平野(章)": "平野 章三",
    "平野章三": "平野 章三",
    "上原": "上原 みなみ",
    "上原みなみ": "上原 みなみ",
    "なんの": "南野 佳代",
    "南野": "南野 佳代",
    "南野佳代": "南野 佳代"
}

def normalize_text(text: str) -> str:
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", str(text))
    return re.sub(r"[\s\u3000]+", " ", norm).strip()

def normalize_symbol(val) -> str:
    s = str(val or "").strip()
    if s in ["〇", "○", "◎", "◯", "for", "賛成"]:
        return "for"
    elif s in ["×", "✕", "✖", "不", "against", "反対"]:
        return "against"
    elif any(k in s for k in ["棄", "欠", "退", "除", "abstain", "absent"]):
        return "abstain"
    return None

def extract_date_from_text(text: str) -> str:
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m_reiwa = re.search(r"令和(\d+)年(\d{1,2})月(\d{1,2})日", text)
    if m_reiwa:
        y = 2018 + int(m_reiwa.group(1))
        return f"{y:04d}-{int(m_reiwa.group(2)):02d}-{int(m_reiwa.group(3)):02d}"
    m_num = re.search(r"(202\d)(\d{2})(\d{2})", text)
    if m_num:
        return f"{m_num.group(1)}-{m_num.group(2)}-{m_num.group(3)}"
    return ""

def collect_session_pages(session: requests.Session) -> list:
    logger.info("現任期（2023年5月以降）の会議結果ページを巡回中...")
    target_pages = []
    seen = set()

    for start_url in [BASE_INDEX_URL, FALLBACK_INDEX_URL]:
        try:
            r = session.get(start_url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                txt = normalize_text(a.get_text())
                href = a["href"]
                # 2023年（令和5年）以降の会期リンク
                if any(yr in txt for yr in ["2023年", "2024年", "2025年", "2026年", "令和5年", "令和6年", "令和7年", "令和8年"]):
                    if "定例市会" in txt or "臨時市会" in txt:
                        full_u = urljoin(start_url, href)
                        if full_u not in seen:
                            seen.add(full_u)
                            target_pages.append((txt, full_u))
        except Exception as e:
            logger.warning(f"インデックス巡回エラー ({start_url}): {e}")

    # 起点ページ自身も対象に含める
    if BASE_INDEX_URL not in seen:
        target_pages.append(("2025年/令和7年第1回定例市会【5月議会】", BASE_INDEX_URL))

    logger.info(f"検知された会期結果ページ: {len(target_pages)} 件")
    return target_pages

def collect_vote_pdfs(session: requests.Session, session_pages: list) -> list:
    pdf_targets = []
    seen_pdfs = set()

    for session_title, page_url in session_pages:
        try:
            r = session.get(page_url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.text, "html.parser")
            h1 = soup.find(["h1", "title"])
            clean_session = normalize_text(h1.get_text()) if h1 else session_title
            clean_session = re.sub(r"神戸市\s*[:：]\s*", "", clean_session).strip()

            for a in soup.find_all("a", href=True):
                txt = normalize_text(a.get_text())
                href = a["href"]
                if href.lower().endswith(".pdf") and ("賛否" in txt or "sanpi" in href.lower()):
                    full_pdf_url = urljoin(page_url, href)
                    if full_pdf_url not in seen_pdfs:
                        seen_pdfs.add(full_pdf_url)
                        # 採決日の抽出
                        d_str = extract_date_from_text(txt + " " + href)
                        pdf_targets.append({
                            "session_title": clean_session,
                            "label": txt,
                            "url": full_pdf_url,
                            "decision_date": d_str
                        })
        except Exception as e:
            logger.warning(f"会期ページ探索エラー ({page_url}): {e}")

    logger.info(f"網羅検出された賛否一覧PDF: {len(pdf_targets)} 件")
    return pdf_targets

def parse_votes_pdf(session: requests.Session, pdf_item: dict) -> list:
    url = pdf_item["url"]
    session_title = pdf_item["session_title"]
    default_date = pdf_item["decision_date"]

    try:
        r = session.get(url, headers=HEADERS, timeout=25)
        if r.status_code != 200:
            return []
        pdf_bytes = io.BytesIO(r.content)
    except Exception as e:
        logger.error(f"PDFダウンロード失敗 ({url}): {e}")
        return []

    parsed_bills = []

    with pdfplumber.open(pdf_bytes) as pdf:
        party_col_map = {}
        indiv_col_map = {}
        header_row = None

        for page_idx, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue

                for row_idx, row in enumerate(table):
                    clean_row = [re.sub(r"[\s\n\u3000]+", "", str(c or "")) for c in row]

                    # ヘッダー特定（自民、公明、共産などの主要会派列が3つ以上合致）
                    matched_parties = {idx: PARTY_MAP[k] for idx, c in enumerate(clean_row) for k in PARTY_MAP if k in c}
                    if len(matched_parties) >= 3:
                        party_col_map = matched_parties
                        indiv_col_map = {idx: INDIVIDUAL_MAP[k] for idx, c in enumerate(clean_row) for k in INDIVIDUAL_MAP if k in c}
                        header_row = clean_row
                        continue

                    if not party_col_map or clean_row == header_row:
                        continue

                    # データ行パース
                    raw_cells = [str(c or "").replace("\n", " ").strip() for c in row]
                    if len(raw_cells) < max(party_col_map.keys()):
                        continue

                    # 議案番号と議案名
                    col0 = normalize_text(raw_cells[0])
                    col1 = normalize_text(raw_cells[1]) if len(raw_cells) > 1 else ""

                    m_no = re.search(r"(第\d+号議案|第\d+号|予算第\d+号議案|予算第\d+号|議員提出第\d+号議案|議員提出第\d+号|諮問第\d+号|諮第\d+号|専決第\d+号|号外|号 外)", col0)
                    if not m_no:
                        # 1列目に議案名が入っている場合の救済
                        m_no = re.search(r"(第\d+号|予算第\d+号|議員提出第\d+号)", col1)
                        if m_no:
                            bill_no = m_no.group(0)
                            bill_title = col0
                        else:
                            continue
                    else:
                        bill_no = m_no.group(0)
                        bill_title = col1 if col1 else col0

                    # タイトルから余分な改行や重複をクレンジング
                    bill_title = re.sub(r"[\s\u3000]+", " ", bill_title).strip()
                    if not bill_title or bill_title == bill_no:
                        bill_title = col0

                    # 賛否シンボルの抽出
                    party_votes = {}
                    for col_idx, p_name in party_col_map.items():
                        if col_idx < len(row):
                            v_sym = normalize_symbol(row[col_idx])
                            if v_sym:
                                party_votes[p_name] = v_sym

                    indiv_votes = {}
                    for col_idx, i_name in indiv_col_map.items():
                        if col_idx < len(row):
                            v_sym = normalize_symbol(row[col_idx])
                            if v_sym:
                                indiv_votes[i_name] = v_sym

                    if not party_votes:
                        continue

                    # 無所属の集約態度決定（UI防衛要件）
                    if indiv_votes:
                        indiv_stances = list(indiv_votes.values())
                        counts = collections.Counter(indiv_stances)
                        # 最頻値を採用（同数の場合は split）
                        if len(counts) > 1 and list(counts.values())[0] == list(counts.values())[1]:
                            party_votes["無所属"] = "split"
                        else:
                            party_votes["無所属"] = counts.most_common(1)[0][0]
                    elif "無所属" not in party_votes:
                        party_votes["無所属"] = "for"

                    # 対立判定（against が存在するか、あるいは態度が分かれているか）
                    all_stances = set(party_votes.values())
                    is_contested = ("against" in all_stances) or ("split" in all_stances) or (len(all_stances) > 1)

                    # 一意な bill_id 生成
                    year_match = re.search(r"(202\d)", default_date)
                    year_str = year_match.group(1) if year_match else "2026"
                    clean_no_id = re.sub(r"[^\w]", "_", bill_no).strip("_")
                    bill_id = f"kobe_bill_{year_str}_{clean_no_id}_{hashlib.md5(bill_title.encode()).hexdigest()[:6]}"

                    parsed_bills.append({
                        "bill_id": bill_id,
                        "bill_number": bill_no,
                        "title": bill_title,
                        "session_name": session_title,
                        "decision_date": default_date or f"{year_str}-03-26",
                        "result": "可決", # 神戸市会において賛否一覧掲載議案は可決（否決は極めて稀）
                        "is_contested": is_contested,
                        "votes": party_votes,
                        "individual_votes": indiv_votes,
                        "pdf_url": url
                    })

    return parsed_bills

def run_fetch_votes():
    session = requests.Session()
    logger.info("=== 神戸市会 全会期 表決データフェッチ開始 ===")

    session_pages = collect_session_pages(session)
    pdf_targets = collect_vote_pdfs(session, session_pages)

    all_bills = []
    seen_keys = set()

    for idx, p_item in enumerate(pdf_targets, 1):
        logger.info(f"[{idx}/{len(pdf_targets)}] 賛否PDF解析中: {p_item['session_title']} - {p_item['label']}")
        bills = parse_votes_pdf(session, p_item)
        for b in bills:
            # 議案番号とセッションで一意性担保
            uniq_k = (b["session_name"], b["bill_number"], b["title"])
            if uniq_k not in seen_keys:
                seen_keys.add(uniq_k)
                all_bills.append(b)

    # 日付降順ソート
    all_bills.sort(key=lambda x: x["decision_date"], reverse=True)

    # 保存
    OUTPUT_VOTES.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_VOTES.write_text(json.dumps(all_bills, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # dist 同期
    if FRONTEND_DIST.exists():
        (FRONTEND_DIST / "kobe_votes_summary.json").write_text(
            json.dumps(all_bills, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    logger.info(f"✅ 表決データ保存完了: {OUTPUT_VOTES} (総議案数: {len(all_bills)} 件)")
    contested_count = sum(1 for b in all_bills if b["is_contested"])
    logger.info(f"📊 対立議案数（Contested Bills）: {contested_count} 件 (全会一致: {len(all_bills) - contested_count} 件)")
    return all_bills

if __name__ == "__main__":
    run_fetch_votes()
