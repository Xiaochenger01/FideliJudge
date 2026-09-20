from __future__ import annotations

from app.core.config import get_routing_config
from app.models import enums as E
from app.models.schemas import JudgeResult


class RoutingEngine:
    def route(
        self,
        overall_score: float,
        judgements: list[JudgeResult],
        critical_issue: bool,
        low_confidence: bool = False,
    ) -> tuple[str, str]:
        cfg = get_routing_config()["routing"]
        auto_pass = float(cfg["auto_pass"])
        review = float(cfg["review"])

        risks = [j.risk_level for j in judgements]
        has_critical = critical_issue or E.CRITICAL in risks
        has_high = E.HIGH in risks

        if cfg.get("critical_block", True) and has_critical:
            return E.REJECT, "存在 CRITICAL 风险，一票否决"
        if overall_score < review:
            return E.REJECT, f"综合分 {overall_score:.1f} < 拒绝阈值 {review}"
        if low_confidence and cfg.get("low_confidence_forces_review", True):
            return E.REVIEW, "存在低置信度判断，转人工审核"
        if has_high and cfg.get("high_forces_review", True):
            return E.REVIEW, "存在 HIGH 风险，转人工审核"
        if overall_score < auto_pass:
            return E.REVIEW, f"综合分 {overall_score:.1f} 介于审核区间"
        if has_high or has_critical:
            return E.REVIEW, "高风险阻断自动通过"
        return E.AUTO_PASS, "分数达标且无高风险"

    @staticmethod
    def is_low_confidence(judgements: list[JudgeResult]) -> bool:
        cfg = get_routing_config()["routing"]
        threshold = float(cfg.get("low_confidence_threshold", 0.55))
        fallback_forces = bool(cfg.get("fallback_forces_review", False))
        for j in judgements:
            if j.source in {"rule", "mock_llm"}:
                continue
            if j.confidence < threshold:
                return True
            if fallback_forces and j.source == "fallback":
                return True
        return False
