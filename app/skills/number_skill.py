from __future__ import annotations

import re
from typing import Any

from app.skills.base import BaseSkill

# (?<![\d.])：不要用 (?<!\w)。Unicode 下 \w 含汉字，会导致「金额1850万」抽不到。
# 长单位放前面，避免「万元」先被切成「万」。
NUMBER_RE = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?)\s*(万元|亿元|%|％|万|亿|元|人|个|项|次)?"
)


class NumberSkill(BaseSkill):
    name = "number_analysis"
    version = "1.0.0"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        before = context.get("before", "")
        after = context.get("after", "")
        return {
            "has_number_before": self.has_number(before),
            "has_number_after": self.has_number(after),
            "is_number_change": self.is_number_change(before, after),
            "severity": self.severity(before, after),
        }

    def extract(self, text: str) -> list[tuple[float, str]]:
        out = []
        for m in NUMBER_RE.finditer(text):
            val = float(m.group(1))
            unit = m.group(2) or ""
            if unit == "万元":
                unit = "万"
            elif unit == "亿元":
                unit = "亿"
            elif unit == "％":
                unit = "%"
            out.append((val, unit))
        return out

    def has_number(self, text: str) -> bool:
        return bool(self.extract(text))

    def is_number_change(self, before: str, after: str) -> bool:
        if before == after:
            return False
        b = self.extract(before)
        a = self.extract(after)
        if not b and not a:
            return False
        if bool(b) != bool(a):
            return True
        # Compare numeric tokens ignoring formatting like 1,850 vs 1850
        b_norm = [(v, u) for v, u in b]
        a_norm = [(v, u) for v, u in a]
        return b_norm != a_norm

    def severity(self, before: str, after: str) -> str:
        b = self.extract(before)
        a = self.extract(after)
        if not b or not a:
            return "critical"
        # same unit, different value significantly
        for (bv, bu), (av, au) in zip(b, a):
            if bu == au and bv != av:
                if bu in {"%", "％"} and abs(bv - av) >= 0.5:
                    return "critical"
                if abs(bv - av) / max(abs(bv), 1e-9) >= 0.01:
                    return "critical"
                return "high"
        if len(b) != len(a):
            return "critical"
        return "high"
