from __future__ import annotations

import difflib


def similarity_score(before: str, after: str) -> float:
    """Baseline 1: SequenceMatcher ratio mapped to 0-100."""
    return round(difflib.SequenceMatcher(None, before, after).ratio() * 100, 2)
