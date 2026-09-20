from __future__ import annotations

import re
from typing import Any

from app.skills.base import BaseSkill

ORG_SUFFIXES = [
    "有限责任公司", "股份有限公司", "有限公司", "集团有限公司",
    "集团公司", "公司", "研究院", "研究所", "大学", "医院", "局", "厅", "部",
]

ENTITY_HINTS = re.compile(
    r"(公司|集团|大学|医院|银行|政府|委员会|项目组|先生|女士|市|省|区|县)"
)


_END_PUNCT = "。；！？!?，,："


class EntitySkill(BaseSkill):
    name = "entity_analysis"
    version = "1.1.0"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        before = context.get("before", "")
        after = context.get("after", "")
        return {
            "is_entity_change": self.is_entity_change(before, after),
            "is_abbreviation": self.is_likely_abbreviation(before, after),
        }

    def _norm(self, text: str) -> str:
        return text.strip().strip(_END_PUNCT)

    def is_likely_abbreviation(self, before: str, after: str) -> bool:
        b, a = self._norm(before), self._norm(after)
        if not b or not a:
            return False
        longer, shorter = (b, a) if len(b) >= len(a) else (a, b)
        if shorter not in longer:
            # strip org suffixes then compare
            core_b = self._strip_suffix(b)
            core_a = self._strip_suffix(a)
            if core_b == core_a and core_b:
                return True
            if core_a and core_a in core_b:
                return True
            return False
        # shorter is substring of longer and length close for org names
        return True

    def _strip_suffix(self, text: str) -> str:
        s = text
        for suf in sorted(ORG_SUFFIXES, key=len, reverse=True):
            if s.endswith(suf):
                s = s[: -len(suf)]
                break
        return s

    def is_entity_change(self, before: str, after: str) -> bool:
        b, a = self._norm(before), self._norm(after)
        if not b or not a or b == a:
            return False
        if self.is_likely_abbreviation(b, a):
            return True
        if ENTITY_HINTS.search(b) or ENTITY_HINTS.search(a):
            return True
        # Chinese proper-noun-ish length
        if (
            not re.search(r"\d", b + a)
            and re.fullmatch(r"[\u4e00-\u9fffA-Za-z·]{2,30}", b)
            and re.fullmatch(r"[\u4e00-\u9fffA-Za-z·]{2,30}", a)
        ):
            return True
        return False
