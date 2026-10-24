from typing import List, Dict, Any
from core.cleaner import StatementCleaner

class ThreadBuilder:
    def __init__(self, cleaner: StatementCleaner, city_code: str):
        self.cleaner = cleaner
        self.city_code = city_code

    def _detect_meeting_chair(self, statements: List[Dict[str, Any]]) -> str:
        """冒頭の開会宣言発言者、または短文指名を最も多く行っている発言者を進行役と特定"""
        if not statements:
            return ""
        # 冒頭3発言のチェック
        for s in statements[:3]:
            txt = (s.get("statement_text") or "").strip()
            if "開会いたします" in txt or "開議いたします" in txt or "審査を行います" in txt:
                return self.cleaner.normalize_speaker(s.get("speaker", ""))
        return ""

    def build_threads(self, statements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        threads = []
        sorted_stmts = sorted(statements, key=lambda x: int(x.get("sequence_number") or 0))

        # 会議の進行役を特定
        active_chair = self._detect_meeting_chair(sorted_stmts)

        current_questioner = None
        current_question_stmts = []
        current_response_stmts = []

        for stmt in sorted_stmts:
            raw_speaker = stmt.get("speaker", "")
            norm_speaker = self.cleaner.normalize_speaker(raw_speaker)
            raw_text = (stmt.get("statement_text") or "").strip()
            header = stmt.get("speaker_header", "")

            role = self.cleaner.detect_role(raw_speaker, header, active_chair=active_chair)

            # 進行役の発言、または短文指名ノイズは除外
            if role == "chair" or self.cleaner.is_chair_call(raw_text):
                continue

            if role == "councilor":
                # 別の議員へ交代した場合、直前の質疑応答スレッドを確定
                if current_questioner and norm_speaker != current_questioner:
                    if current_question_stmts and current_response_stmts:
                        threads.append(self._create_thread(current_question_stmts, current_response_stmts))
                    current_question_stmts = []
                    current_response_stmts = []

                current_questioner = norm_speaker
                current_question_stmts.append({
                    "speaker": norm_speaker,
                    "sequence_number": stmt.get("sequence_number"),
                    "text": raw_text,
                    "source_url": stmt.get("source_url", ""),
                    "meeting_id": stmt.get("meeting_id"),
                    "meeting_title": stmt.get("meeting_title"),
                    "meeting_date": stmt.get("meeting_date")
                })

            elif role == "official":
                # 質問議員が存在する場合のみ答弁として集約（冒頭の議案説明単独はスキップ）
                if current_questioner:
                    current_response_stmts.append({
                        "speaker": norm_speaker,
                        "sequence_number": stmt.get("sequence_number"),
                        "text": raw_text,
                        "source_url": stmt.get("source_url", "")
                    })

        # 最終スレッドの回収
        if current_question_stmts and current_response_stmts:
            threads.append(self._create_thread(current_question_stmts, current_response_stmts))

        return threads

    def _create_thread(self, q_list: List[Dict[str, Any]], r_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        first_q = q_list[0]
        first_r = r_list[0]
        seq_start = first_q["sequence_number"]
        seq_end = r_list[-1]["sequence_number"]
        meeting_id = first_q.get("meeting_id", "")

        q_full_text = "\n\n".join(f"【質疑】{q['text']}" for q in q_list)
        r_full_text = "\n\n".join(f"【答弁({r['speaker']})】{r['text']}" for r in r_list)

        # 答弁に関わった理事者（重複排除）
        respondents = list(dict.fromkeys(r["speaker"] for r in r_list))

        return {
            "thread_id": f"th_{meeting_id}_{seq_start}_{seq_end}",
            "city_code": self.city_code,
            "meeting_id": meeting_id,
            "meeting_title": first_q.get("meeting_title", ""),
            "meeting_date": first_q.get("meeting_date", ""),
            "questioner": {
                "name": first_q["speaker"],
                "statement_count": len(q_list),
                "statement_text": q_full_text
            },
            "respondent": {
                "names": respondents,
                "statement_count": len(r_list),
                "statement_text": r_full_text
            },
            "source_url": first_q.get("source_url", "")
        }
