from __future__ import annotations

from app.llm.mock import MockJudgeProvider
from app.skills.change_classifier import ChangeClassifier


def single_llm_score(before: str, after: str) -> float:
    """Ablation: full-text judge without Diff localization.

    Reuses this project's ChangeClassifier + MockJudge. Do not report it as
    an external baseline; it is "w/o Diff".
    """
    if before == after:
        return 100.0
    ctype, risk = ChangeClassifier().classify_one(before, after)
    result = MockJudgeProvider().judge({
        "before": before,
        "after": after,
        "change_type": ctype,
        "risk_level": risk,
        "signals": {},
    })
    return float(result.score)
