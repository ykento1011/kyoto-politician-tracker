import hashlib
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

try:
    from .base_scraper import BaseScraper
except ImportError:
    from scrapers.base_scraper import BaseScraper

class KaigirokuScraper(BaseScraper):
    """
    会議録ネット / SideStaff (ssp.kaigiroku.net 系) 汎用議会録スクレイパー
    """

    EXCLUDE_SPEAKERS = {
        "名簿", "日程", "議事日程", "目次", "出席議員", "説明員", "署名議員",
        "地方自治法第121条による出席者", "開会", "閉会", "散会", "宣告", "休憩", "再開",
        "資料", "資料編", "付帯事項", "諸般の報告"
    }

    def __init__(
        self,
        city_code: str,
        tenant_id: str,
        tenant_dir: str,
        output_path: Path,
        base_url: str = "https://ssp.kaigiroku.net",
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
        self.tenant_id = str(tenant_id)
        self.tenant_dir = tenant_dir
        self._session_initialized = False
        
        # 0件だった会議を記憶するキャッシュファイル
        self.cache_path = self.output_path.parent / f"{self.city_code}_processed_cache.json"

    def _init_session(self):
        if self._session_initialized:
            return
        top_url = f"{self.base_url}/tenant/{self.tenant_dir}/SpTop.html"
        browse_url = f"{self.base_url}/tenant/{self.tenant_dir}/SpMinuteBrowse.html"
        self.logger.info(f"セッション確立中: {top_url}")
        
        self.session.headers.update({
            "Referer": browse_url,
            "X-Requested-With": "XMLHttpRequest",
        })
        resp = self.get(top_url)
        self._session_initialized = True

    @staticmethod
    def _clean_json(text: str) -> str:
        if text.startswith("jQuery") or "(" in text[:30]:
            return re.sub(r"^[^\(]+\((.*)\);?$", r"\1", text, flags=re.DOTALL)
        return text

    def get_councils(self, start_date: str = "2023-05-01") -> List[Dict[str, Any]]:
        self._init_session()
        url = f"{self.base_url}/dnp/search/councils/index"
        payload = {"tenant_id": self.tenant_id, "power_user": "false"}
        self._wait_rate_limit()
        resp = self.session.post(url, data=payload, timeout=self.timeout)
        resp.encoding = "utf-8"
        data = json.loads(self._clean_json(resp.text))
        
        start_year = start_date[:4]
        councils_list = []
        view_years = data.get("councils", [{}])[0].get("view_years", [])
        for vy in view_years:
            year = vy.get("view_year", "")
            if year >= start_year:
                for ct in vy.get("council_type", []):
                    c_type_name = ct.get("council_type_name2") or ct.get("council_type_name1") or ""
                    for c in ct.get("councils", []):
                        councils_list.append({
                            "council_id": c.get("council_id"),
                            "name": self.normalize_text(c.get("name", "")),
                            "year": year,
                            "type_name": c_type_name,
                        })
        return councils_list

    def get_schedules(self, council_id: int) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/dnp/search/minutes/get_schedule_all"
        payload = {"tenant_id": self.tenant_id, "power_user": "false", "council_id": str(council_id)}
        self._wait_rate_limit()
        resp = self.session.post(url, data=payload, timeout=self.timeout)
        resp.encoding = "utf-8"
        data = json.loads(self._clean_json(resp.text))
        
        valid_schedules = []
        for s in data.get("schedules_and_materials", []):
            name = s.get("name", "")
            if any(skip in name for skip in ["目次", "資料編", "資料"]):
                continue
            valid_schedules.append({
                "schedule_id": s.get("schedule_id"),
                "name": name,
                "page_no": s.get("page_no", 0),
            })
        return valid_schedules

    def get_minutes(self, council_id: int, schedule_id: int) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/dnp/search/minutes/get_minute"
        payload = {"tenant_id": self.tenant_id, "power_user": "false", "council_id": str(council_id), "schedule_id": str(schedule_id)}
        self._wait_rate_limit()
        resp = self.session.post(url, data=payload, timeout=self.timeout)
        resp.encoding = "utf-8"
        data = json.loads(self._clean_json(resp.text))
        return data.get("tenant_minutes", [])

    def parse_speech_blocks(
        self,
        tenant_minutes: List[Dict[str, Any]],
        council: Dict[str, Any],
        schedule: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        council_id = council["council_id"]
        schedule_id = schedule["schedule_id"]
        council_name = council["name"]
        schedule_name = schedule["name"]
        year = council["year"]
        
        meeting_id = f"ssp_{council_id}_{schedule_id}"
        meeting_title = f"{council_name} {schedule_name}".strip()
        
        m_date = re.search(r"(\d{1,2})月(\d{1,2})日", schedule_name)
        if m_date and year:
            meeting_date = f"{int(year):04d}-{int(m_date.group(1)):02d}-{int(m_date.group(2)):02d}"
        else:
            meeting_date = self.extract_meeting_date(meeting_title)
            
        statements = []
        for idx, block in enumerate(tenant_minutes, 1):
            raw_title = self.normalize_text(block.get("title", ""))
            body_html = block.get("body", "")
            clean_body = re.sub(r"<[^>]+>", "", body_html).strip()
            clean_body = self.normalize_text(clean_body)
            
            if any(skip in raw_title for skip in self.EXCLUDE_SPEAKERS):
                continue
                
            speaker_clean = self.clean_speaker(raw_title)
            raw_speaker = raw_title
            
            if speaker_clean in self.EXCLUDE_SPEAKERS:
                continue
            
            if not speaker_clean or speaker_clean in ["閲覧", "会議録"]:
                m_spk = re.search(r"^[◯○◎◆■□▲△▼▽]([^\s\u3000]{2,30})", clean_body)
                if m_spk:
                    raw_speaker = m_spk.group(0)
                    speaker_clean = self.clean_speaker(raw_speaker)
            
            if not speaker_clean or speaker_clean in self.EXCLUDE_SPEAKERS:
                continue
            
            statement_text = clean_body
            strip_pat = re.escape(raw_speaker)
            statement_text = re.sub(rf"^[◯○◎◆■□▲△▼▽\s]*{strip_pat}[\s\u3000]*", "", statement_text).strip()
            
            minute_id = block.get("minute_id", idx)
            official_url = f"{self.base_url}/tenant/{self.tenant_dir}/MinuteView.html?council_id={council_id}&schedule_id={schedule_id}#minute_{minute_id}"
            
            if len(statement_text) >= 8 and not any(statement_text.startswith(kw) for kw in ["開会", "閉会", "散会", "休憩", "再開"]):
                statements.append({
                    "meeting_id": meeting_id,
                    "meeting_title": meeting_title,
                    "meeting_date": meeting_date,
                    "speaker": speaker_clean,
                    "speaker_raw": raw_speaker,
                    "statement_text": statement_text,
                    "official_url": official_url,
                    "sequence_number": minute_id,
                })
        return statements

    def run_fetch(self, start_date: str = "2023-05-01", max_councils: Optional[int] = None) -> int:
        self.logger.info(f"=== [{self.city_code.upper()}] 会議録ネット (SSP) 本番フェッチ開始 ===")
        
        all_raw_statements = self.load_existing_statements()
        processed_meeting_ids: Set[str] = set()
        
        # 1. 既存データから処理済みIDをロード
        for s in all_raw_statements:
            if m_id := s.get("meeting_id"):
                processed_meeting_ids.add(m_id)
                
        # 2. キャッシュ(0件だった会議)から処理済みIDをロード
        if self.cache_path.exists():
            try:
                cached_ids = set(json.loads(self.cache_path.read_text(encoding="utf-8")))
                processed_meeting_ids.update(cached_ids)
            except Exception:
                pass

        if all_raw_statements:
            self.logger.info(f"既存蓄積データ: {len(all_raw_statements)} 件 ({len(processed_meeting_ids)} 会議日程済・キャッシュ含む)")
            
        councils = self.get_councils(start_date=start_date)
        if max_councils:
            councils = councils[:max_councils]
            
        new_stmts_count = 0
        total_schedules_checked = 0
        new_processed_ids = set()
        
        for council in councils:
            try:
                schedules = self.get_schedules(council["council_id"])
            except Exception as e:
                self.logger.error(f"日程取得失敗 (council_id={council['council_id']}): {e}")
                continue
                
            for schedule in schedules:
                meeting_id = f"ssp_{council['council_id']}_{schedule['schedule_id']}"
                
                # 取得済み、または0件確認済みのIDは瞬時にスキップ
                if meeting_id in processed_meeting_ids:
                    continue
                    
                total_schedules_checked += 1
                display_title = f"{council['name']} - {schedule['name']}"
                self.logger.info(f"[{total_schedules_checked}] 新規取得中: {display_title} ({meeting_id})")
                
                try:
                    tenant_minutes = self.get_minutes(council["council_id"], schedule["schedule_id"])
                    stmts = self.parse_speech_blocks(tenant_minutes, council, schedule)
                    self.logger.info(f"  -> {len(stmts)} 件の発言を抽出")
                    
                    if stmts:
                        all_raw_statements.extend(stmts)
                        new_stmts_count += len(stmts)
                    
                    processed_meeting_ids.add(meeting_id)
                    new_processed_ids.add(meeting_id)
                    
                    # 5日程ごとに発言データとキャッシュを保存
                    if total_schedules_checked % 5 == 0:
                        if new_stmts_count > 0:
                            self.save_statements(all_raw_statements)
                        self.cache_path.write_text(json.dumps(list(processed_meeting_ids)), encoding="utf-8")
                        
                except Exception as e:
                    self.logger.error(f"会議録取得失敗 ({meeting_id}): {e}")
                    
        # 最終保存
        if new_stmts_count > 0 or not self.output_path.exists():
            self.save_statements(all_raw_statements)
        if new_processed_ids:
            self.cache_path.write_text(json.dumps(list(processed_meeting_ids)), encoding="utf-8")
            
        if new_stmts_count > 0:
            self.logger.info(f"🎉 差分フェッチ完了: 新規 {new_stmts_count} 件追加 (総計: {len(all_raw_statements)} 件)")
        else:
            self.logger.info(f"✅ 新規の未取得会議録はありませんでした (総計: {len(all_raw_statements)} 件維持)")
            
        return len(all_raw_statements)
