import re
from typing import Dict, Any, Optional, List, Set

CHAIR_ROLES = ["議長", "副議長", "委員長", "副委員長", "分科会長", "部会長"]
OFFICIAL_ROLES = ["市長", "副市長", "局長", "部長", "課長", "室長", "次長", "理事者", "担当部長", "技監", "統括", "参事", "室頭", "主幹"]

PROCEDURAL_PATTERNS = [
    r"^(ただ今|ただいま)から.*?(開会|開議|再開)いたします",
    r"^(これより|以上で|これをもって).*?(散会|閉会|休憩|終了)いたします",
    r"^本日の.*?日程は",
    r"^日程第\d+",
    r"^暫時休憩いたします",
    r"^理事者[、\s]+説明願います",
    r"^質疑のある方は举手願います",
    r"^質疑の申出がありますので",
    r"^それでは進行いたします",
    r"^よろしいですか[。、]?",
]

class StatementCleaner:
    def __init__(self, alias_map: Optional[Dict[str, str]] = None, councilors: Optional[List[str]] = None):
        self.alias_map = alias_map or {}
        self.councilors: Set[str] = set()
        if councilors:
            for c in councilors:
                self.councilors.add(self.normalize_speaker(c))

    def normalize_speaker(self, name: str) -> str:
        if not name:
            return ""
        cleaned = re.sub(r"[\s\u3000]+", "", str(name))
        return self.alias_map.get(cleaned, cleaned)

    def detect_role(self, speaker_name: str, speaker_header: str = "", active_chair: str = "") -> str:
        norm_name = self.normalize_speaker(speaker_name)
        target = f"{norm_name} {speaker_header or ''}"

        # 当該会議で議長・進行役として特定されている人物
        if active_chair and norm_name == active_chair:
            return "chair"

        for c in CHAIR_ROLES:
            if c in target:
                return "chair"

        if self.councilors:
            if norm_name in self.councilors or "議員" in target:
                return "councilor"
            return "official"

        for o in OFFICIAL_ROLES:
            if o in target:
                return "official"
        return "councilor"

    def is_chair_call(self, text: str) -> bool:
        if not text:
            return True
        t = text.strip()

        # 40文字以下の短文指名（◯◯委員、◯◯局長、◯◯室長、◯◯どうぞ 等）
        if len(t) <= 40:
            if re.search(r"^.*?(委員|局長|部長|室長|課長|次長|市長|副市長|理事者|君|様)(、どうぞ|どうぞ)?[。、]?$", t):
                return True
            if re.search(r"^(それでは[、\s]*)?.*?(願います|お願いいたします|どうぞ)[。、]?$", t):
                return True

        for pat in PROCEDURAL_PATTERNS:
            if re.search(pat, t):
                return True

        return False
