from __future__ import annotations

import re
from typing import Any

from app.models import enums as E
from app.models.schemas import ChangeItem
from app.skills.base import BaseSkill
from app.skills.entity_skill import ORG_SUFFIXES, EntitySkill
from app.skills.fact_skill import FactSkill
from app.skills.number_skill import NumberSkill
from app.skills.time_skill import TimeSkill


_PUNCT_RE = re.compile(r"^[\s\W_]+$", re.UNICODE)
_WS_RE = re.compile(r"\s+")
_BOILERPLATE_RE = re.compile(
    r"(自动生成|请勿回复|免责声明|仅供参考|页眉|页脚|第\d+页|内部资料|机密)"
)
_PREFIX_STRIP = "：:，, "


class ChangeClassifier(BaseSkill):
    name = "change_classifier"
    version = "1.2.0"

    def __init__(self) -> None:
        self.time_skill = TimeSkill()
        self.number_skill = NumberSkill()
        self.entity_skill = EntitySkill()
        self.fact_skill = FactSkill()

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        changes: list[ChangeItem] = context.get("changes", [])
        classified: list[ChangeItem] = []
        for ch in changes:
            signals = self.classify_signals(ch.before_text, ch.after_text)
            if not signals:
                signals = [(E.UNKNOWN, E.MEDIUM)]
            for i, (ctype, risk) in enumerate(signals):
                cid = ch.change_id if len(signals) == 1 else f"{ch.change_id}_{ctype.lower()}"
                classified.append(ch.model_copy(update={
                    "change_id": cid if i == 0 or cid != ch.change_id else f"{ch.change_id}_{i:02d}",
                    "change_type": ctype,
                    "risk_hint": risk,
                }))
        return {"changes": classified}

    def classify_one(self, before: str, after: str) -> tuple[str, str]:
        return self.classify_signals(before, after)[0]

    def classify_signals(self, before: str, after: str) -> list[tuple[str, str]]:
        b = before.strip()
        a = after.strip()

        # Format (including punct-only add/delete) must win over DELETION/ADDITION.
        if self._is_format_only(b, a):
            return [(E.FORMAT, E.LOW)]

        hits: list[tuple[str, str]] = []

        if not b and a:
            if self._is_boilerplate(a):
                return [(E.FORMAT, E.LOW)]
            hits.append((E.ADDITION, E.MEDIUM))
        elif b and not a:
            if self._is_boilerplate(b):
                return [(E.FORMAT, E.LOW)]
            if self.fact_skill.looks_factual(b) or self.time_skill.has_time(b) or self.number_skill.has_number(b):
                hits.append((E.DELETION, E.CRITICAL))
            else:
                hits.append((E.DELETION, E.HIGH))
            return hits

        # 截断删除放在时间/数值判定之后，避免把「2025年6月→2025年」误判成删人名
        if self.time_skill.is_time_change(b, a):
            granularity = self.time_skill.granularity_loss(b, a)
            hits.append((E.TIME, E.HIGH if granularity else E.MEDIUM))

        if self.number_skill.is_number_change(b, a):
            severity = self.number_skill.severity(b, a)
            hits.append((E.NUMBER, E.CRITICAL if severity == "critical" else E.HIGH))

        if not hits:
            trunc = self._truncation_deletion(b, a)
            if trunc:
                hits.append(trunc)
                return hits

        if self.fact_skill.is_fact_change(b, a):
            hits.append((E.FACT, E.CRITICAL))

        if self.entity_skill.is_entity_change(b, a):
            if self.entity_skill.is_likely_abbreviation(b, a):
                hits.append((E.TERM, E.MEDIUM))
            else:
                hits.append((E.ENTITY, E.HIGH))
        elif self.entity_skill.is_likely_abbreviation(b, a):
            hits.append((E.TERM, E.MEDIUM))

        if hits:
            return hits

        if (b and _PUNCT_RE.match(b)) or (a and _PUNCT_RE.match(a)):
            return [(E.STRUCTURE, E.LOW)]

        return [(E.UNKNOWN, E.MEDIUM)]

    def _is_format_only(self, b: str, a: str) -> bool:
        if b == a:
            return True

        def strip_punct(s: str) -> str:
            return re.sub(r"[\s，。；：、,.!?;:\"'（）()【】\[\]]+", "", s)

        if strip_punct(b) == strip_punct(a):
            return True
        nb = _WS_RE.sub("", b)
        na = _WS_RE.sub("", a)
        return nb == na

    def _is_boilerplate(self, text: str) -> bool:
        return bool(_BOILERPLATE_RE.search(text))

    def _truncation_deletion(self, b: str, a: str) -> tuple[str, str] | None:
        if not a or not b or len(b) <= len(a):
            return None
        prefix = a.rstrip(_PREFIX_STRIP)
        if not prefix or not b.startswith(prefix):
            return None
        dropped = b[len(prefix):].strip(_PREFIX_STRIP + "。")
        if not dropped:
            return None
        if any(dropped == suf or dropped.endswith(suf) for suf in ORG_SUFFIXES):
            return None
        if (
            self.fact_skill.looks_factual(dropped)
            or self.number_skill.has_number(dropped)
            or self.time_skill.has_time(dropped)
            or len(dropped) >= 2
        ):
            return (E.DELETION, E.CRITICAL)
        return None
