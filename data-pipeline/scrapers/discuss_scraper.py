import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, parse_qs, urlparse

from bs4 import BeautifulSoup

try:
    from .base_scraper import BaseScraper
except ImportError:
    from scrapers.base_scraper import BaseScraper

class DiscussScraper(BaseScraper):
    """
    DiscussWeb / DiscussNet Premium (dbsr.jp 系) 汎用議会録スクレイパー
    - 会期一覧の取得 (TermStart 基準)
    - 本文会議録URLの網羅収集 (VoiceType=all 付与)
    - voice-block パース (発言者、役職、発言番号、生テキスト、公式URL)
    - 差分取得（Incremental Fetch）: 不変の meeting_id (doc_{Id}) 基準で判定
    """

    def __init__(
        self,
        city_code: str,
        base_url: str,
        output_path: Path,
        rate_limit_seconds: float = 1.2,
        user_agent: Optional[str] = None,
        timeout: int = 25,
    ):
        super().__init__(
            city_code=city_code,
            base_url=base_url,
            output_path=output_path,
            rate_limit_seconds=rate_limit_seconds,
            user_agent=user_agent,
            timeout=timeout,
        )

    @staticmethod
    def extract_doc_id_from_url(url: str) -> str:
        """URLのクエリパラメータ Id またはパスから一意の文書IDを抽出"""
        parsed_query = parse_qs(urlparse(url).query)
        doc_id = parsed_query.get("Id", [""])[0]
        if not doc_id:
            m = re.search(r"/(\d+)(?:\?|$)", url)
            doc_id = m.group(1) if m else hashlib.md5(url.encode()).hexdigest()[:8]
        return doc_id

    def get_term_links(self, start_date: str = "2023-05-01") -> List[Tuple[str, str, str]]:
        """トップページから指定日以降の会期一覧リンクを取得"""
        self.logger.info("トップページより会期一覧を取得中...")
        resp = self.get(self.base_url)
        soup = BeautifulSoup(resp.text, "html.parser")

        term_links = []
        seen = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            txt = self.normalize_text(a.get_text())
            if "TermStart=" in href:
                parsed = parse_qs(urlparse(href).query)
                term_start = parsed.get("TermStart", [""])[0]
                if term_start >= start_date:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in seen:
                        seen.add(full_url)
                        term_links.append((txt, full_url, term_start))

        self.logger.info(f"対象任期内の会期数: {len(term_links)} 会期検知")
        return term_links

    def get_document_links(self, term_links: List[Tuple[str, str, str]]) -> List[Dict[str, str]]:
        """各会期ページから「本文」会議録URLを収集"""
        doc_links = []
        seen_doc_ids = set()

        for term_title, term_url, term_start in term_links:
            try:
                r = self.get(term_url)
                soup = BeautifulSoup(r.text, "html.parser")

                for a in soup.find_all("a", href=True):
                    txt = self.normalize_text(a.get_text())
                    href = a["href"]
                    if "本文" in txt and "Template=document" in href:
                        clean_href = re.sub(r"#.*$", "", href)
                        sep = "&" if "?" in clean_href else "?"
                        full_doc_url = urljoin(term_url, f"{clean_href}{sep}VoiceType=all")
                        
                        doc_id = self.extract_doc_id_from_url(full_doc_url)
                        if doc_id not in seen_doc_ids:
                            seen_doc_ids.add(doc_id)
                            doc_links.append({
                                "title": txt,
                                "url": full_doc_url,
                                "doc_id": doc_id,
                                "term_title": term_title,
                                "term_start": term_start
                            })
            except Exception as e:
                self.logger.warning(f"会期パースエラー ({term_url}): {e}")

        self.logger.info(f"網羅探索完了: 合計 {len(doc_links)} 件の本文会議録を特定")
        return doc_links

    def parse_meeting_document(
        self,
        html_text: str,
        doc_url: str,
        default_title: str,
        default_date: str
    ) -> List[Dict[str, Any]]:
        """個別会議録HTMLから発言レコード（Voice Blocks）をパース"""
        soup = BeautifulSoup(html_text, "html.parser")

        h_title = soup.find(["h1", "h2", "title"])
        meeting_title = self.normalize_text(h_title.get_text()) if h_title else default_title
        meeting_title = re.sub(r"\s*-\s*(神戸市|.*市会|.*市議会).*$", "", meeting_title).strip()
        if not meeting_title or meeting_title == "閲覧":
            meeting_title = default_title

        meeting_date = self.extract_meeting_date(
            meeting_title + " " + soup.get_text()[:1000],
            default_date=default_date
        )

        doc_id = self.extract_doc_id_from_url(doc_url)
        meeting_id = f"doc_{doc_id}"

        blocks = soup.find_all("li", class_=re.compile(r"voice[-_]block"))
        if not blocks:
            blocks = soup.find_all(["div", "section"], class_=re.compile(r"voice[-_]detail|voice[-_]block"))

        statements = []

        for idx, block in enumerate(blocks, 1):
            spk_name_tag = block.find(class_=re.compile(r"speaker__name"))
            if spk_name_tag:
                raw_speaker = self.normalize_text(spk_name_tag.get_text())
            else:
                b_text = self.normalize_text(block.get_text())
                m_s = re.search(r"([◯○◎◆■□][^\s\u3000]{2,20})", b_text)
                raw_speaker = m_s.group(1) if m_s else "議事"

            speaker_clean = self.clean_speaker(raw_speaker)

            num_tag = block.find(class_=re.compile(r"speaker__number"))
            btn_tag = block.find("button", attrs={"data-voice_code": True})
            seq_str = num_tag.get_text(strip=True) if num_tag else (btn_tag["data-voice_code"] if btn_tag else str(idx))
            try:
                seq_num = int(seq_str)
            except ValueError:
                seq_num = idx

            body_tag = block.find(["p", "div"], class_=re.compile(r"voice[-_]text|voice__text"))
            statement_text = self.normalize_text(body_tag.get_text()) if body_tag else self.normalize_text(block.get_text())

            if raw_speaker and statement_text.startswith(raw_speaker):
                statement_text = statement_text[len(raw_speaker):].strip()

            clean_base_url = re.sub(r"&VoiceType=.*$", "", doc_url)
            official_url = f"{clean_base_url}#voice_{seq_num}"

            if len(statement_text) >= 5:
                statements.append({
                    "meeting_id": meeting_id,
                    "meeting_title": meeting_title,
                    "meeting_date": meeting_date,
                    "speaker": speaker_clean,
                    "speaker_raw": raw_speaker,
                    "statement_text": statement_text,
                    "official_url": official_url,
                    "sequence_number": seq_num,
                })

        return statements

    def run_fetch(self, start_date: str = "2023-05-01", **kwargs) -> int:
        """差分取得（Incremental Fetch）による本番フェッチ"""
        self.logger.info(f"=== [{self.city_code.upper()}] DiscussNet 本番フェッチ開始 (開始日: {start_date}) ===")

        # 既存データのロード（meeting_id 基準で差分管理）
        all_raw_statements = self.load_existing_statements()
        processed_meeting_ids: Set[str] = set()
        for s in all_raw_statements:
            m_id = s.get("meeting_id")
            if m_id:
                processed_meeting_ids.add(m_id)

        if all_raw_statements:
            self.logger.info(
                f"既存蓄積データ: {len(all_raw_statements)} 件 "
                f"({len(processed_meeting_ids)} 会議録済)"
            )

        term_links = self.get_term_links(start_date=start_date)
        doc_links = self.get_document_links(term_links)

        # 既存 meeting_id にない会議録のみを抽出
        pending_docs = [
            d for d in doc_links
            if f"doc_{d['doc_id']}" not in processed_meeting_ids
        ]

        total_docs = len(doc_links)
        self.logger.info(
            f"走査予定: 全 {total_docs} 件中、新規未取得は {len(pending_docs)} 件です"
        )

        if not pending_docs:
            self.logger.info("✅ 新規の未取得会議録はありませんでした（手元のデータは最新です）")
            return len(all_raw_statements)

        new_stmts_count = 0
        for idx, doc in enumerate(pending_docs, 1):
            title_display = f"{doc['term_title']} - {doc['title']}"
            self.logger.info(f"[{idx}/{len(pending_docs)}] 取得中: {title_display}")

            try:
                resp = self.get(doc["url"])
                stmts = self.parse_meeting_document(
                    resp.text,
                    doc["url"],
                    title_display,
                    doc["term_start"]
                )
                self.logger.info(f"  -> {len(stmts)} 件の発言を抽出")
                all_raw_statements.extend(stmts)
                processed_meeting_ids.add(f"doc_{doc['doc_id']}")
                new_stmts_count += len(stmts)

                if idx % 5 == 0:
                    self.save_statements(all_raw_statements)
            except Exception as e:
                self.logger.error(f"パース失敗 ({doc['url']}): {e}")

        if new_stmts_count > 0:
            self.save_statements(all_raw_statements)
            self.logger.info(f"🎉 差分フェッチ完了: 新規 {new_stmts_count} 件追加 (総計: {len(all_raw_statements)} 件)")

        return len(all_raw_statements)
