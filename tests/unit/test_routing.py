from __future__ import annotations

from app.models.schemas import JudgeResult
from app.routing.router import RoutingEngine


def test_critical_veto():
    route, _ = RoutingEngine().route(
        overall_score=92,
        judgements=[
            JudgeResult(
                is_faithful=False,
                risk_level="CRITICAL",
                change_type="FACT",
                score=20,
                reason="fact flip",
                evidence=[],
                confidence=0.9,
            )
        ],
        critical_issue=True,
    )
    assert route == "REJECT"


def test_high_forces_review():
    route, _ = RoutingEngine().route(
        overall_score=88,
        judgements=[
            JudgeResult(
                is_faithful=False,
                risk_level="HIGH",
                change_type="TIME",
                score=60,
                reason="time loss",
                evidence=[],
                confidence=0.9,
            )
        ],
        critical_issue=False,
    )
    assert route == "REVIEW"


def test_auto_pass():
    route, _ = RoutingEngine().route(
        overall_score=96,
        judgements=[
            JudgeResult(
                is_faithful=True,
                risk_level="LOW",
                change_type="FORMAT",
                score=98,
                reason="format",
                evidence=[],
                confidence=0.99,
            )
        ],
        critical_issue=False,
    )
    assert route == "AUTO_PASS"


def test_mock_llm_low_confidence_does_not_force_review():
    from app.routing.router import RoutingEngine

    judgements = [
        JudgeResult(
            is_faithful=True,
            risk_level="LOW",
            change_type="FORMAT",
            score=98,
            reason="format",
            evidence=[],
            confidence=0.5,
            source="mock_llm",
        )
    ]
    assert RoutingEngine.is_low_confidence(judgements) is False
    route, _ = RoutingEngine().route(96, judgements, False, low_confidence=False)
    assert route == "AUTO_PASS"


def test_real_llm_fallback_low_confidence_detected():
    from app.routing.router import RoutingEngine

    judgements = [
        JudgeResult(
            is_faithful=True,
            risk_level="LOW",
            change_type="TERM",
            score=90,
            reason="fallback",
            evidence=[],
            confidence=0.45,
            source="fallback",
        )
    ]
    assert RoutingEngine.is_low_confidence(judgements) is True
