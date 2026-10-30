"""
kobe_adapter.py
神戸市会専用アダプター（Osaka/Yokohama 品質フィルター完全準拠版）
"""

import json
import logging
import re
import unicodedata
from pathlib import Path

logger = logging.getLogger("KobeAdapter")
CUR = Path(__file__).resolve().parent
MASTER_FILE = CUR / "master" / "kobe_councilors.json"
RAW_FILE = CUR / "kobe_raw_statements.json"

class KobeAdapter:
    city_code = "kobe"
    official_minute_url = "https://www.city.kobe.hyogo.dbsr.jp/"

    @classmethod
    def clean_name(cls, name: str) -> str:
        if not name:
            return ""
        c = re.sub(r"^(?:議員|団長|副団長|幹事長|代表|会長|委員|委員長)?", "", str(name)).strip()
        norm = unicodedata.normalize("NFKC", c)
        return re.sub(r"[\s\u3000]+", "", norm)

    @classmethod
    def build_councilor_lookup(cls) -> dict:
        if not MASTER_FILE.exists():
            raise FileNotFoundError(f"マスターファイルが見つかりません: {MASTER_FILE}")

        councilors = json.loads(MASTER_FILE.read_text(encoding="utf-8"))
        lookup = {}
        for idx, c in enumerate(councilors, 1):
            c_id = c.get("id") or f"kobe_c_{idx:03d}"
            c_entry = {
                "id": c_id,
                "name": c["name"],
                "party": c.get("party", "無所属"),
                "district": c.get("district", ""),
                "ward": c.get("district", "")
            }
            clean_k = cls.clean_name(c["name"])
            lookup[clean_k] = c_entry
            for alias in c.get("aliases", []):
                lookup[cls.clean_name(alias)] = c_entry
        return lookup

    @classmethod
    def normalize_speaker(cls, speaker: str) -> str:
        s = unicodedata.normalize("NFKC", str(speaker or "")).strip()
        s = re.sub(r"^[◯○◎◆■□▲△▼▽\s]+", "", s)
        s = re.sub(r"^\d+番\s*", "", s)
        m = re.search(r"[（\(](.+?)[）\)]", s)
        if m:
            s = m.group(1)
        s = s.replace("議員", "").replace("君", "").replace("くん", "").strip()
        return re.sub(r"[\s\u3000]+", " ", s)

    @classmethod
    def is_admin(cls, speaker: str, text: str) -> bool:
        spk = unicodedata.normalize("NFKC", speaker or "")
        admin_keywords = [
            "市長", "副市長", "局長", "部長", "次長", "課長", "室長",
            "教育長", "代表監査委員", "管理者", "理事者", "説明員",
            "陳情者", "参考人", "公述人", "議長", "副議長", "委員長", "分科会長"
        ]
        if any(k in spk for k in admin_keywords):
            return True
        if spk.endswith("長") or "事務局" in spk:
            return True
        return False

    @classmethod
    def is_procedural(cls, text: str) -> bool:
        t = unicodedata.normalize("NFKC", text or "").strip()
        if len(t) < 15:
            return True
        procedural_phrases = [
            "開会いたします", "散会いたします", "休憩いたします", "再開いたします",
            "会議を開きます", "本日の会議はこれをもって", "延会いたします",
            "御異議がありませんので", "異議なしと認めます", "決定をいたしました",
            "順次各局の審査を行います", "これより質疑に入ります", "質疑を終結いたします",
            "以上で陳情審査を終わります", "諸般の報告を申し上げます", "日程第", "お諮りいたします"
        ]
        return any(p in t for p in procedural_phrases)

    @classmethod
    def clean_statement_text(cls, text: str) -> str:
        t = unicodedata.normalize("NFKC", text or "").strip()
        t = re.sub(r"^\d+\s*:\s*", "", t)
        t = re.sub(r"^\([^\)]*?開[会議]\)\s*", "", t)
        t = re.sub(r"^[◯○◎◆■□▲△▼▽][^\s ]+[\s ]*", "", t)
        return t.strip()

    @classmethod
    def fetch_data(cls, client=None) -> list:
        if not RAW_FILE.exists():
            raise FileNotFoundError(f"生データが見つかりません: {RAW_FILE}")
        return json.loads(RAW_FILE.read_text(encoding="utf-8"))

    @classmethod
    def build_threads(cls, raw_stmts: list) -> list:
        councilor_lookup = cls.build_councilor_lookup()
        threads = []
        current_thread = None

        def is_valid_thread(th):
            return th is not None and th.get("has_response", False) and len(th.get("question_text", "")) >= 40

        for stmt in raw_stmts:
            raw_spk = stmt.get("speaker_raw", "")
            spk = stmt.get("speaker", "")
            raw_text = stmt.get("statement_text", "")
            cleaned_text = cls.clean_statement_text(raw_text)

            is_adm = cls.is_admin(raw_spk, cleaned_text) or cls.is_admin(spk, cleaned_text)
            norm_name = cls.normalize_speaker(spk)
            clean_k = cls.clean_name(norm_name)
            councilor_info = councilor_lookup.get(clean_k)

            if cls.is_procedural(cleaned_text) and not current_thread:
                continue

            # 1. 議員による質問
            if not is_adm and councilor_info:
                # 同一議員による再質問
                if current_thread and current_thread["speaker"] == councilor_info["name"]:
                    current_thread["context_log"].append(f"【議員 ({councilor_info['name']})】\n{cleaned_text}")
                    if len(current_thread["question_text"]) < 500:
                        current_thread["question_text"] += f"\n{cleaned_text}"
                    continue

                # 確定条件を満たす場合のみ蓄積（答弁あり・40字以上）
                if is_valid_thread(current_thread):
                    threads.append(current_thread)

                seq = len(threads) + 1
                meeting_id = stmt.get("meeting_id", "m")
                th_id = f"th_{meeting_id}_{seq}"

                current_thread = {
                    "thread_id": th_id,
                    "id": th_id,
                    "speaker": councilor_info["name"],
                    "councilor_id": councilor_info.get("id"),
                    "meeting_id": meeting_id,
                    "meeting_date": stmt.get("meeting_date"),
                    "meeting_title": stmt.get("meeting_title"),
                    "party": councilor_info.get("party", "無所属"),
                    "district": councilor_info.get("district", ""),
                    "ward": councilor_info.get("district", ""),
                    "official_url": stmt.get("official_url"),
                    "sequence_number": seq,
                    "question_text": cleaned_text,
                    "has_response": False,
                    "context_log": [f"【議員 ({councilor_info['name']})】\n{cleaned_text}"]
                }
            # 2. 理事者答弁
            elif current_thread:
                role_label = "答弁" if is_adm else "発言"
                if is_adm:
                    current_thread["has_response"] = True
                current_thread["context_log"].append(f"【{role_label} ({norm_name})】\n{cleaned_text}")

        if is_valid_thread(current_thread):
            threads.append(current_thread)

        print(f"✅ [KOBE] {len(threads):,} 件の実質質疑スレッドを構築しました（答弁あり・40字以上）。")
        return threads
