from __future__ import annotations

from typing import Any

from app.core.config import get_scoring_config
from app.llm.base import JudgeProvider
from app.models import enums as E
from app.models.schemas import JudgeResult


class MockJudgeProvider(JudgeProvider):
    """Deterministic heuristic judge — stable for demos and eval skeleton."""

    name = "mock"

    def judge(self, payload: dict[str, Any]) -> JudgeResult:
        cfg = get_scoring_config()
        ctype = payload.get("change_type", E.UNKNOWN)
        before = payload.get("before", "")
        after = payload.get("after", "")
        risk_hint = payload.get("risk_level", cfg.get("default_risk", {}).get(ctype, E.MEDIUM))

        score = float(cfg.get("default_scores", {}).get(ctype, 70))
        risk = risk_hint

        # Refine by signals in payload
        signals = payload.get("signals", {})
        evidence: list[str] = []
        reason = ""

        if ctype == E.FORMAT:
            reason = "仅格式/空白/标点差异，未改变语义"
            evidence = ["格式归一", "语义未变"]
            return JudgeResult(
                change_id=payload.get("change_id"),
                is_faithful=True,
                risk_level=E.LOW,
                change_type=ctype,
                score=98,
                reason=reason,
                evidence=evidence,
                confidence=0.99,
                source="mock_llm",
            )

        if ctype == E.TERM:
            reason = "属于术语/机构简称归一，实体指向未发生实质变化"
            evidence = ["简称归一", "核心名称保留"]
            return JudgeResult(
                change_id=payload.get("change_id"),
                is_faithful=True,
                risk_level=E.MEDIUM,
                change_type=ctype,
                score=92,
                reason=reason,
                evidence=evidence,
                confidence=0.94,
                source="mock_llm",
            )

        if ctype == E.TIME:
            if signals.get("granularity_loss"):
                reason = "时间信息发生精度损失，可能影响可追溯性与事实粒度"
                evidence = [f"原文时间片段: {before}", f"修改后: {after}", "粒度降低"]
                score, risk = 58, E.HIGH
            else:
                reason = "检测到时间相关变化，需确认是否影响事实"
                evidence = [f"{before} → {after}"]
                score, risk = 70, E.HIGH
            return JudgeResult(
                change_id=payload.get("change_id"),
                is_faithful=False,
                risk_level=risk,
                change_type=ctype,
                score=score,
                reason=reason,
                evidence=evidence,
                confidence=0.9,
                source="mock_llm",
            )

        if ctype == E.NUMBER:
            sev = signals.get("number_severity", "high")
            if sev == "critical":
                reason = "核心数值发生变化，属于高风险误改/过度清洗嫌疑"
                score, risk = 35, E.CRITICAL
            else:
                reason = "数值或单位发生变化，可能损失事实精度"
                score, risk = 55, E.HIGH
            evidence = [f"{before} → {after}", f"severity={sev}"]
            return JudgeResult(
                change_id=payload.get("change_id"),
                is_faithful=False,
                risk_level=risk,
                change_type=ctype,
                score=score,
                reason=reason,
                evidence=evidence,
                confidence=0.93,
                source="mock_llm",
            )

        if ctype == E.FACT:
            reason = "事实状态/极性发生变化，严重威胁语义保真"
            evidence = [f"{before} → {after}", "事实冲突"]
            return JudgeResult(
                change_id=payload.get("change_id"),
                is_faithful=False,
                risk_level=E.CRITICAL,
                change_type=ctype,
                score=25,
                reason=reason,
                evidence=evidence,
                confidence=0.95,
                source="mock_llm",
            )

        if ctype == E.DELETION:
            reason = "关键信息被删除，存在过度清洗风险"
            evidence = [f"删除内容: {before}"]
            return JudgeResult(
                change_id=payload.get("change_id"),
                is_faithful=False,
                risk_level=risk if risk in {E.HIGH, E.CRITICAL} else E.HIGH,
                change_type=ctype,
                score=40,
                reason=reason,
                evidence=evidence,
                confidence=0.88,
                source="mock_llm",
            )

        if ctype == E.ENTITY:
            reason = "实体表述发生变化，需确认是否仍指向同一对象"
            evidence = [f"{before} → {after}"]
            return JudgeResult(
                change_id=payload.get("change_id"),
                is_faithful=False,
                risk_level=E.HIGH,
                change_type=ctype,
                score=62,
                reason=reason,
                evidence=evidence,
                confidence=0.8,
                source="mock_llm",
            )

        # UNKNOWN / ADDITION / STRUCTURE
        reason = f"检测到 {ctype} 类型变化，按保守策略评估"
        evidence = [f"{before} → {after}"]
        is_faithful = score >= 85
        return JudgeResult(
            change_id=payload.get("change_id"),
            is_faithful=is_faithful,
            risk_level=risk,
            change_type=ctype,
            score=score,
            reason=reason,
            evidence=evidence,
            confidence=0.7,
            source="mock_llm",
        )
