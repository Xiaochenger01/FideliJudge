from __future__ import annotations

from app.evaluators.scorer import FidelityScorer
from app.models.schemas import StabilityStats


def run_stability(scores: list[float]) -> StabilityStats:
    return FidelityScorer().stability(scores)
