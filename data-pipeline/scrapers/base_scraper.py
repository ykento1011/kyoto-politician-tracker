import abc
import hashlib
import json
import logging
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class BaseScraper(abc.ABC):
    """
    議会データスクレイパー共通基底クラス
    - 自治体サーバー保護のための Rate Limiting（最低 1.0〜1.5秒の待機強制）
    - シビックテック正規 User-Agent 設定
    - 指数バックオフ付きリトライ機構（HTTP 429, 500, 502, 503, 504）
    - 文字列正規化・議員名/役職クレンジング・日付抽出
    - 差分取得（Incremental Fetch）とアトミック保存
    """

    DEFAULT_USER_AGENT = "GikaiNoMikataBot/1.0 (+https://gikai-mikata.jp; info@gikai-mikata.jp)"

    def __init__(
        self,
        city_code: str,
        base_url: str,
        output_path: Path,
        rate_limit_seconds: float = 1.2,
        user_agent: Optional[str] = None,
        timeout: int = 25,
        max_retries: int = 3,
    ):
        self.city_code = city_code.lower()
        self.base_url = base_url.rstrip("/")
        self.output_path = Path(output_path)
        self.rate_limit_seconds = max(1.0, float(rate_limit_seconds))
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.timeout = timeout
        self._last_request_time = 0.0

        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({"User-Agent": self.user_agent})

        self.logger = logging.getLogger(f"Scraper.{self.city_code.upper()}")

    def _wait_rate_limit(self):
        """自治体サーバー保護のため、リクエスト間に最低 rate_limit_seconds の待機を強制"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_time = time.time()

    def get(self, url: str, **kwargs) -> requests.Response:
        self._wait_rate_limit()
        kwargs.setdefault("timeout", self.timeout)
        resp = self.session.get(url, **kwargs)
        resp.encoding = resp.apparent_encoding
        return resp

    def load_existing_statements(self) -> List[Dict[str, Any]]:
        if self.output_path.exists():
            try:
                data = json.loads(self.output_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception as e:
                self.logger.warning(f"既存データの読み込みに失敗しました ({e})。新規作成します。")
        return []

    def save_statements(self, statements: List[Dict[str, Any]]):
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.output_path.with_suffix(".tmp.json")
        temp_path.write_text(json.dumps(statements, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.output_path)
        self.logger.info(f"💾 データを保存しました: {self.output_path} (総発言数: {len(statements)} 件)")

    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        norm = unicodedata.normalize("NFKC", str(text))
        return re.sub(r"[\s\u3000]+", " ", norm).strip()

    @staticmethod
    def clean_speaker(speaker_raw: str) -> str:
        """発言者文字列から記号・議席番号・役職等を整理してクリーンな氏名を抽出"""
        s = BaseScraper.normalize_text(speaker_raw)
        s = re.sub(r"^[◯○◎◆■□▲△▼▽\s]+", "", s)

        # 役職＋（氏名） または （氏名） に対応
        m = re.search(r"([^\(（]*)[（\(](.+?)[）\)]", s)
        if m:
            role_part = m.group(1).strip()
            name_part = m.group(2).replace("議員", "").replace("君", "").replace("くん", "").strip()
            name_clean = re.sub(r"[\s\u3000]+", " ", name_part).strip()

            if not role_part or re.search(r"^\d+番", role_part):
                return name_clean
            if any(r in role_part for r in ["市長", "議長", "副市長", "局長", "部長", "委員長"]):
                return f"{role_part}（{name_clean}）"
            return name_clean

        s = re.sub(r"^\d+番\s*", "", s)
        s = s.replace("議員", "").replace("君", "").replace("くん", "").strip()
        return re.sub(r"[\s\u3000]+", " ", s)

    @staticmethod
    def extract_meeting_date(text: str, default_date: str = "") -> str:
        m = re.search(r"(?:令和|R)(\d+)年(\d+)月(\d+)日", text)
        if m:
            y, month, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return f"{2018 + y:04d}-{month:02d}-{d:02d}"

        m2 = re.search(r"(202\d)年(\d+)月(\d+)日", text)
        if m2:
            return f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"

        return default_date or datetime.now().strftime("%Y-%m-%d")

    @abc.abstractmethod
    def run_fetch(self, start_date: str = "2023-05-01", **kwargs) -> int:
        pass
