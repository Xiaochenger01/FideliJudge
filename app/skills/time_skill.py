from __future__ import annotations

import re
from typing import Any

from app.skills.base import BaseSkill

TIME_PATTERNS = [
    re.compile(r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"),
    re.compile(r"\d{4}\s*年\s*\d{1,2}\s*月"),
    re.compile(r"\d{4}\s*年"),
    re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"),
    re.compile(r"\d{4}[-/]\d{1,2}"),
    re.compile(r"(今天|昨天|明天|上周|本周|本月|去年|今年|近日|日前)"),
]


class TimeSkill(BaseSkill):
    name = "time_analysis"
    version = "1.0.0"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        before = context.get("before", "")
        after = context.get("after", "")
        return {
            "has_time_before": self.has_time(before),
            "has_time_after": self.has_time(after),
            "is_time_change": self.is_time_change(before, after),
            "granularity_loss": self.granularity_loss(before, after),
        }

    def has_time(self, text: str) -> bool:
        return any(p.search(text) for p in TIME_PATTERNS)

    def _level(self, text: str) -> int:
        if re.search(r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日|\d{4}[-/]\d{1,2}[-/]\d{1,2}", text):
            return 3
        if re.search(r"\d{4}\s*年\s*\d{1,2}\s*月|\d{4}[-/]\d{1,2}", text):
            return 2
        if re.search(r"\d{4}\s*年|\d{4}", text):
            return 1
        if self.has_time(text):
            return 1
        return 0

    def is_time_change(self, before: str, after: str) -> bool:
        if before == after:
            return False
        return self.has_time(before) or self.has_time(after)

    def granularity_loss(self, before: str, after: str) -> bool:
        return self._level(before) > self._level(after) > 0 or (
            self._level(before) > 0 and self._level(after) == 0
        )
