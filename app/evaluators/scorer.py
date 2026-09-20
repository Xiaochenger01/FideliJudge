from __future__ import annotations

import statistics
from typing import Iterable

from app.core.config import get_scoring_config
from app.models import enums as E
from app.models.schemas import DimensionScores, JudgeResult, StabilityStats


class FidelityScorer:
    def score(self, judgements: list[JudgeResult]) -> tuple[float, DimensionScores, bool]:
        cfg = get_scoring_config()
        weights = cfg["weights"]
        penalties = cfg.get("penalties", {})

        dims = {
            "structure": 100.0,
            "entity": 100.0,
            "number": 100.0,
            "time": 100.0,
            "factual": 100.0,
        }
        mapping = {
            E.FORMAT: "structure",
            E.STRUCTURE: "structure",
            E.TERM: "entity",
            E.ENTITY: "entity",
            E.NUMBER: "number",
            E.TIME: "time",
            E.FACT: "factual",
            E.DELETION: "factual",
            E.ADDITION: "structure",
            E.UNKNOWN: "factual",
        }

        buckets: dict[str, list[float]] = {k: [] for k in dims}
        critical = False
        for j in judgements:
            key = mapping.get(j.change_type, "factual")
            buckets[key].append(j.score)
            if j.risk_level == E.CRITICAL:
                critical = True

        for key, vals in buckets.items():
            if vals:
                dims[key] = sum(vals) / len(vals)

        overall = (
            weights["structure"] * dims["structure"]
            + weights["entity"] * dims["entity"]
            + weights["number"] * dims["number"]
            + weights["time"] * dims["time"]
            + weights["factual"] * dims["factual"]
        )

        # high-risk penalties (cannot be fully averaged away)
        max_risk = E.LOW
        rank = {E.LOW: 1, E.MEDIUM: 2, E.HIGH: 3, E.CRITICAL: 4}
        for j in judgements:
            if rank.get(j.risk_level, 0) > rank.get(max_risk, 0):
                max_risk = j.risk_level
        overall -= float(penalties.get(max_risk, 0))
        overall = max(0.0, min(100.0, overall))

        return overall, DimensionScores(**dims), critical

    def stability(self, scores: Iterable[float]) -> StabilityStats:
        vals = list(scores)
        if not vals:
            return StabilityStats(n=0, mean=0, std=0, variance=0, scores=[], agreement_rate=1.0)
        mean = float(statistics.mean(vals))
        std = float(statistics.pstdev(vals)) if len(vals) > 1 else 0.0
        var = float(statistics.pvariance(vals)) if len(vals) > 1 else 0.0
        # agreement: within 2 points of mean
        agree = sum(1 for s in vals if abs(s - mean) <= 2.0) / len(vals)
        return StabilityStats(
            n=len(vals),
            mean=round(mean, 4),
            std=round(std, 4),
            variance=round(var, 4),
            scores=[round(s, 4) for s in vals],
            agreement_rate=round(agree, 4),
        )
