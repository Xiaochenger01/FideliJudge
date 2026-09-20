from __future__ import annotations

from app.evaluators.calibration import cohen_kappa, summarize


def test_perfect_agreement():
    labels = ["AUTO_PASS", "REVIEW", "REJECT"]
    stats = summarize(labels, labels)
    assert stats["accuracy"] == 1.0
    assert stats["cohen_kappa"] == 1.0
    assert stats["spearman"] == 1.0


def test_kappa_chance():
    pred = ["AUTO_PASS", "AUTO_PASS", "REJECT", "REJECT"]
    gold = ["AUTO_PASS", "REJECT", "AUTO_PASS", "REJECT"]
    k = cohen_kappa(pred, gold)
    assert abs(k) < 1e-9
