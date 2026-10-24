import re
from typing import Dict, Any, Optional, List, Set

class StatementCleaner:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        rules = cfg.get("rules", {})

        self.alias_map: Dict[str, str] = cfg.get("alias_map", {})
        self.chair_roles: List[str] = rules.get("chair_roles", ["議長", "副議長", "委員長", "副委員長", "分科会長", "部会長"])
        self.official_roles: List[str] = rules.get("official_roles", ["市長", "副市長", "局長", "部長", "課長", "室長", "次長", "理事者", "担当部長", "技監", "統括", "参事", "主幹"])
        
        self.chair_call_patterns: List[str] = rules.get("chair_call_patterns", [
            r"^.*?(委員|局長|部長|室長|課長|次長|市長|副市長|理事者|君|様)(、どうぞ|どうぞ)?[。、]?$",
            r"^(それでは[、\s]*)?.*?(願います|お願いいたします|どうぞ)[。、]?$"
        ])
        self.procedural_patterns: List[str] = rules.get("procedural_patterns", [
            r"^(ただ今|ただいま)から.*?(開会|開議|再開)いたします",
            r"^(これより|以上で|これをもって).*?(散会|閉会|休憩|終了)いたします",
            r"^本日の.*?日程は",
            r"^日程第\d+",
            r"^暫時休憩いたします",
            r"^理事者[、\s]+説明願います",
            r"^質疑のある方は举手願います",
            r"^それでは進行いたします",
            r"^よろしいですか[。、]?"
        ])

        self.councilors: Set[str] = set()
        for c in cfg.get("councilors", []):
            self.councilors.add(self.normalize_speaker(c))

    def normalize_speaker(self, name: str) -> str:
        if not name:
            return ""
        cleaned = re.sub(r"[\s\u3000]+", "", str(name))
        return self.alias_map.get(cleaned, cleaned)

    def detect_role(self, speaker_name: str, speaker_header: str = "", active_chair: str = "") -> str:
        norm_name = self.normalize_speaker(speaker_name)
        target = f"{norm_name} {speaker_header or ''}"

        if active_chair and norm_name == active_chair:
            return "chair"

        for c in self.chair_roles:
            if c in target:
                return "chair"

        if self.councilors:
            if norm_name in self.councilors or "議員" in target:
                return "councilor"
            return "official"

        for o in self.official_roles:
            if o in target:
                return "official"

        return "councilor"

    def is_chair_call(self, text: str) -> bool:
        if not text:
            return True
        t = text.strip()

        if len(t) <= 40:
            for pat in self.chair_call_patterns:
                if re.search(pat, t):
                    return True

        for pat in self.procedural_patterns:
            if re.search(pat, t):
                return True

        return False
