"""
fetch_kobe_discuss.py (Production Grade)
神戸市会 会議録検索システム（DiscussNet Premium）本番フェッチャー
現任期全56会期の「本文」文書を網羅走査し、kobe_raw_statements.json を生成する。
"""

import argparse
import hashlib
import json
import logging
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

CUR = Path(__file__).resolve().parent
OUTPUT_RAW = CUR / "kobe_raw_statements.json"
CHECKPOINT_FILE = CUR / "fetch_kobe_checkpoint.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FetchKobeDiscussProd")

BASE_URL = "https://www.city.kobe.hyogo.dbsr.jp"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def normalize_text(text: str) -> str:
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", str(text))
    return re.sub(r"[\s\u3000]+", " ", norm).strip()

def clean_speaker(speaker_raw: str) -> str:
    s = normalize_text(speaker_raw)
    s = re.sub(r"^[◯○◎◆■□▲△▼▽\s]+", "", s)

    m = re.search(r"([^\(（]+)[（\(](.+?)[）\)]", s)
    if m:
        role_part = m.group(1).strip()
        name_part = m.group(2).replace("議員", "").replace("君", "").replace("くん", "").strip()
        name_clean = re.sub(r"[\s\u3000]+", " ", name_part).strip()

        if re.search(r"^\d+番", role_part):
            return name_clean
        if any(r in role_part for r in ["市長", "議長", "副市長", "局長", "部長", "委員長"]):
            return f"{role_part}（{name_clean}）"
        return name_clean

    s = re.sub(r"^\d+番\s*", "", s)
    s = s.replace("議員", "").replace("君", "").replace("くん", "").strip()
    return re.sub(r"[\s\u3000]+", " ", s)

def extract_meeting_date(text: str, default_date: str = "") -> str:
    m = re.search(r"(?:令和|R)(\d+)年(\d+)月(\d+)日", text)
    if m:
        y, month, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{2018 + y:04d}-{month:02d}-{d:02d}"
    
    m2 = re.search(r"(202\d)年(\d+)月(\d+)日", text)
    if m2:
        return f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"

    return default_date or datetime.now().strftime("%Y-%m-%d")

def get_term_links(session: requests.Session, start_date: str = "2023-05-01") -> list:
    logger.info(f"トップページより会期一覧を取得中...")
    resp = session.get(BASE_URL, headers=HEADERS, timeout=15)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    term_links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        txt = normalize_text(a.get_text())
        if "TermStart=" in href:
            parsed = parse_qs(urlparse(href).query)
            term_start = parsed.get("TermStart", [""])[0]
            if term_start >= start_date:
                full_url = urljoin(BASE_URL, href)
                if full_url not in seen:
                    seen.add(full_url)
                    term_links.append((txt, full_url, term_start))

    logger.info(f"対象任期内の会期数: {len(term_links)} 会期検知")
    return term_links

def get_document_links(session: requests.Session, term_links: list) -> list:
    doc_links = []
    seen = set()

    for term_title, term_url, term_start in term_links:
        try:
            r = session.get(term_url, headers=HEADERS, timeout=15)
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.text, "html.parser")

            for a in soup.find_all("a", href=True):
                txt = normalize_text(a.get_text())
                href = a["href"]
                if "本文" in txt and "Template=document" in href:
                    clean_href = re.sub(r"#.*$", "", href)
                    sep = "&" if "?" in clean_href else "?"
                    full_doc_url = urljoin(term_url, f"{clean_href}{sep}VoiceType=all")

                    if full_doc_url not in seen:
                        seen.add(full_doc_url)
                        doc_links.append({
                            "title": txt,
                            "url": full_doc_url,
                            "term_title": term_title,
                            "term_start": term_start
                        })
            time.sleep(0.2)
        except Exception as e:
            logger.warning(f"会期パースエラー ({term_url}): {e}")

    logger.info(f"網羅探索完了: 合計 {len(doc_links)} 件の本文会議録を特定")
    return doc_links

def parse_meeting_document(html_text: str, doc_url: str, default_title: str, default_date: str) -> list:
    soup = BeautifulSoup(html_text, "html.parser")

    h_title = soup.find(["h1", "h2", "title"])
    meeting_title = normalize_text(h_title.get_text()) if h_title else default_title
    meeting_title = re.sub(r"\s*-\s*神戸市.*$", "", meeting_title).strip()
    if not meeting_title or meeting_title == "閲覧":
        meeting_title = default_title

    meeting_date = extract_meeting_date(meeting_title + " " + soup.get_text()[:1000], default_date=default_date)

    parsed_query = parse_qs(urlparse(doc_url).query)
    doc_id = parsed_query.get("Id", [""])[0]
    if not doc_id:
        m_id = re.search(r"/(\d+)(?:\?|$)", doc_url)
        doc_id = m_id.group(1) if m_id else hashlib.md5(doc_url.encode()).hexdigest()[:8]
    meeting_id = f"doc_{doc_id}"

    blocks = soup.find_all("li", class_=re.compile(r"voice[-_]block"))
    if not blocks:
        blocks = soup.find_all(["div", "section"], class_=re.compile(r"voice[-_]detail|voice[-_]block"))

    statements = []

    for idx, block in enumerate(blocks, 1):
        spk_name_tag = block.find(class_=re.compile(r"speaker__name"))
        if spk_name_tag:
            raw_speaker = normalize_text(spk_name_tag.get_text())
        else:
            b_text = normalize_text(block.get_text())
            m_s = re.search(r"([◯○◎◆■□][^\s\u3000]{2,20})", b_text)
            raw_speaker = m_s.group(1) if m_s else "議事"

        speaker_clean = clean_speaker(raw_speaker)

        num_tag = block.find(class_=re.compile(r"speaker__number"))
        btn_tag = block.find("button", attrs={"data-voice_code": True})
        seq_str = num_tag.get_text(strip=True) if num_tag else (btn_tag["data-voice_code"] if btn_tag else str(idx))
        try:
            seq_num = int(seq_str)
        except ValueError:
            seq_num = idx

        body_tag = block.find(["p", "div"], class_=re.compile(r"voice[-_]text|voice__text"))
        statement_text = normalize_text(body_tag.get_text()) if body_tag else normalize_text(block.get_text())

        if raw_speaker and statement_text.startswith(raw_speaker):
            statement_text = statement_text[len(raw_speaker):].strip()

        official_url = f"{re.sub(r'&VoiceType=.*$', '', doc_url)}#voice_{seq_num}"

        if len(statement_text) >= 5:
            statements.append({
                "meeting_id": meeting_id,
                "meeting_title": meeting_title,
                "meeting_date": meeting_date,
                "speaker": speaker_clean,
                "speaker_raw": raw_speaker,
                "statement_text": statement_text,
                "official_url": official_url,
                "sequence_number": seq_num
            })

    return statements

def run_production_fetch(start_date: str = "2023-05-01"):
    session = requests.Session()
    logger.info("=== 神戸市会 DiscussNet 全任期本番フェッチ開始 ===")

    # 既存データのロード（レジューム対応）
    all_raw_statements = []
    processed_urls = set()
    if OUTPUT_RAW.exists():
        try:
            all_raw_statements = json.loads(OUTPUT_RAW.read_text(encoding="utf-8"))
            for s in all_raw_statements:
                base_u = re.sub(r"#.*$", "", s.get("official_url", ""))
                processed_urls.add(base_u)
            logger.info(f"既存の蓄積データを検知: {len(all_raw_statements)} 件 ({len(processed_urls)} 会議録済)")
        except Exception:
            all_raw_statements = []

    term_links = get_term_links(session, start_date=start_date)
    doc_links = get_document_links(session, term_links)

    new_count = 0
    total_docs = len(doc_links)

    for idx, doc in enumerate(doc_links, 1):
        clean_target_url = re.sub(r"&VoiceType=all", "", doc["url"])
        if clean_target_url in processed_urls:
            continue

        title_display = f"{doc['term_title']} - {doc['title']}"
        logger.info(f"[{idx}/{total_docs}] 取得中: {title_display}")

        try:
            r = session.get(doc["url"], headers=HEADERS, timeout=25)
            r.encoding = r.apparent_encoding
            stmts = parse_meeting_document(r.text, doc["url"], title_display, doc["term_start"])
            logger.info(f"  -> {len(stmts)} 件の発言を抽出")
            all_raw_statements.extend(stmts)
            processed_urls.add(clean_target_url)
            new_count += len(stmts)

            # 5文書ごとに途中セーブ
            if idx % 5 == 0:
                OUTPUT_RAW.write_text(json.dumps(all_raw_statements, ensure_ascii=False, indent=2), encoding="utf-8")
                logger.info(f"💾 中間チェックポイント保存 ({len(all_raw_statements)} 件)")

            time.sleep(0.3)
        except Exception as e:
            logger.error(f"パース失敗 ({doc['url']}): {e}")

    # 最終保存
    OUTPUT_RAW.write_text(json.dumps(all_raw_statements, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"🎉 全会期本番フェッチ完了: {OUTPUT_RAW} (総発言数: {len(all_raw_statements)} 件, 新規: {new_count} 件)")
    return len(all_raw_statements)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="神戸市会 DiscussNet 全任期本番フェッチャー")
    parser.add_argument("--start-date", type=str, default="2023-05-01", help="現任期開始日 (YYYY-MM-DD)")
    args = parser.parse_args()

    run_production_fetch(start_date=args.start_date)
