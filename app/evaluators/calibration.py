from __future__ import annotations

import math
from typing import Sequence

ROUTE_RANK = {"AUTO_PASS": 2, "REVIEW": 1, "REJECT": 0, "SAFE": 2, "UNSAFE": 0}


def agreement_rate(pred: list[str], gold: list[str]) -> float:
    if not pred or len(pred) != len(gold):
        return 0.0
    return sum(p == g for p, g in zip(pred, gold)) / len(gold)


def _contingency(pred: Sequence[str], gold: Sequence[str]) -> dict[str, dict[str, int]]:
    labels = sorted(set(pred) | set(gold))
    table = {a: {b: 0 for b in labels} for a in labels}
    for p, g in zip(pred, gold):
        table[g][p] += 1
    return table


def cohen_kappa(pred: list[str], gold: list[str]) -> float:
    """Cohen's κ for categorical agreement (Agent vs Human)."""
    n = len(pred)
    if n == 0 or n != len(gold):
        return 0.0
    labels = sorted(set(pred) | set(gold))
    po = agreement_rate(pred, gold)
    pe = 0.0
    for lab in labels:
        pe += (sum(g == lab for g in gold) / n) * (sum(p == lab for p in pred) / n)
    if abs(1.0 - pe) < 1e-12:
        return 1.0 if po >= 1.0 - 1e-12 else 0.0
    return (po - pe) / (1.0 - pe)


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2 or n != len(ys):
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def pearson(pred: list[str], gold: list[str], rank_map: dict[str, int] | None = None) -> float:
    mapping = rank_map or ROUTE_RANK
    xs = [float(mapping.get(p, 1)) for p in pred]
    ys = [float(mapping.get(g, 1)) for g in gold]
    return _pearson(xs, ys)


def _rankdata(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda t: t[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg
        i = j + 1
    return ranks


def spearman(pred: list[str], gold: list[str], rank_map: dict[str, int] | None = None) -> float:
    mapping = rank_map or ROUTE_RANK
    xs = [float(mapping.get(p, 1)) for p in pred]
    ys = [float(mapping.get(g, 1)) for g in gold]
    return _pearson(_rankdata(xs), _rankdata(ys))


def summarize(pred: list[str], gold: list[str]) -> dict[str, float]:
    return {
        "n": float(len(gold)),
        "accuracy": round(agreement_rate(pred, gold), 4),
        "cohen_kappa": round(cohen_kappa(pred, gold), 4),
        "spearman": round(spearman(pred, gold), 4),
        "pearson": round(pearson(pred, gold), 4),
    }
