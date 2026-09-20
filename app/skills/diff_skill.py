from __future__ import annotations

import difflib
import re
from typing import Any

from app.core.trace import new_change_id
from app.models.schemas import ChangeItem, Position
from app.skills.base import BaseSkill

# Sentence-like units. Character-level opcodes are kept only as localization anchors.
_UNIT_RE = re.compile(r"[^。；！？!?\n]+[。；！？!?\n]*|[。；！？!?\n]+")


def split_units(text: str) -> list[tuple[int, int, str]]:
    """Split text into sentence-like units with character offsets."""
    if not text:
        return []
    units = [(m.start(), m.end(), m.group()) for m in _UNIT_RE.finditer(text)]
    if not units:
        return [(0, len(text), text)]
    covered = units[-1][1] if units else 0
    if covered < len(text):
        units.append((covered, len(text), text[covered:]))
    return [(s, e, t) for s, e, t in units if t]


def char_anchor(before_unit: str, after_unit: str) -> tuple[tuple[int, int], tuple[int, int]]:
    """Fine-grained character span inside an aligned unit pair."""
    matcher = difflib.SequenceMatcher(None, before_unit, after_unit, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            return (i1, i2), (j1, j2)
    return (0, len(before_unit)), (0, len(after_unit))


class DiffSkill(BaseSkill):
    name = "diff_analysis"
    version = "1.2.0"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        before: str = context["before"]
        after: str = context["after"]
        changes = self.diff_texts(before, after)
        return {"changes": changes}

    def diff_texts(self, before: str, after: str) -> list[ChangeItem]:
        if before == after:
            return []

        b_units = split_units(before)
        a_units = split_units(after)
        b_sents = [t for _, _, t in b_units]
        a_sents = [t for _, _, t in a_units]

        matcher = difflib.SequenceMatcher(None, b_sents, a_sents, autojunk=False)
        changes: list[ChangeItem] = []
        idx = 1
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            # 相邻句同时修改时 SequenceMatcher 会合成一块 replace。
            # 按句拆开，保证每处都有独立锚点。
            pairs = self._expand_opcode(tag, b_units, a_units, i1, i2, j1, j2)
            for b_u, a_u in pairs:
                item = self._make_change(idx, b_u, a_u)
                if item is None:
                    continue
                changes.append(item)
                idx += 1
        return changes

    def _expand_opcode(
        self,
        tag: str,
        b_units: list[tuple[int, int, str]],
        a_units: list[tuple[int, int, str]],
        i1: int,
        i2: int,
        j1: int,
        j2: int,
    ) -> list[tuple[tuple[int, int, str] | None, tuple[int, int, str] | None]]:
        b_slice = b_units[i1:i2]
        a_slice = a_units[j1:j2]
        if tag == "replace":
            n, m = len(b_slice), len(a_slice)
            paired = min(n, m)
            out: list[tuple[tuple[int, int, str] | None, tuple[int, int, str] | None]] = []
            for k in range(paired):
                out.append((b_slice[k], a_slice[k]))
            for k in range(paired, n):
                out.append((b_slice[k], None))
            for k in range(paired, m):
                out.append((None, a_slice[k]))
            return out
        if tag == "delete":
            return [(u, None) for u in b_slice]
        if tag == "insert":
            return [(None, u) for u in a_slice]
        return [(None, None)]

    def _make_change(
        self,
        idx: int,
        b_u: tuple[int, int, str] | None,
        a_u: tuple[int, int, str] | None,
    ) -> ChangeItem | None:
        before_text = b_u[2] if b_u else ""
        after_text = a_u[2] if a_u else ""
        if not before_text and not after_text:
            return None

        if b_u:
            pos_b_start, pos_b_end = b_u[0], b_u[1]
        elif a_u:
            pos_b_start = pos_b_end = 0
        else:
            pos_b_start = pos_b_end = 0

        if a_u:
            pos_a_start, pos_a_end = a_u[0], a_u[1]
        elif b_u:
            pos_a_start = pos_a_end = 0
        else:
            pos_a_start = pos_a_end = 0

        (bi1, bi2), (aj1, aj2) = char_anchor(before_text, after_text)
        return ChangeItem(
            change_id=new_change_id(idx),
            before_text=before_text,
            after_text=after_text,
            change_type="UNKNOWN",
            position_before=Position(
                start=pos_b_start + bi1,
                end=(pos_b_start + bi2) if b_u else pos_b_start,
            ),
            position_after=Position(
                start=pos_a_start + aj1,
                end=(pos_a_start + aj2) if a_u else pos_a_start,
            ),
        )
