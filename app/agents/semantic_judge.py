from __future__ import annotations

from typing import Any

from app.core.config import get_scoring_config
from app.llm.base import JudgeProvider
from app.llm.openai_compat import build_judge_provider
from app.models import enums as E
from app.models.schemas import ChangeItem, JudgeResult
from app.skills.number_skill import NumberSkill
from app.skills.time_skill import TimeSkill


class SemanticJudge:
    def __init__(self, provider: JudgeProvider | None = None):
        self.provider = provider or build_judge_provider()
        self.time_skill = TimeSkill()
        self.number_skill = NumberSkill()
        self.skip_types = set(get_scoring_config().get("skip_llm_types", []))

    def judge_change(
        self,
        change: ChangeItem,
        before_full: str,
        after_full: str,
    ) -> JudgeResult:
        # Cheap rule path for pure format
        if change.change_type in self.skip_types:
            return JudgeResult(
                change_id=change.change_id,
                is_faithful=True,
                risk_level=E.LOW,
                change_type=change.change_type,
                score=98 if change.change_type == E.FORMAT else 95,
                reason="规则判定：格式/结构变化，不调用 LLM",
                evidence=["rule_skip_llm"],
                confidence=0.99,
                source="rule",
            )

        signals: dict[str, Any] = {
            "granularity_loss": self.time_skill.granularity_loss(change.before_text, change.after_text),
            "number_severity": self.number_skill.severity(change.before_text, change.after_text)
            if change.change_type == E.NUMBER
            else None,
        }
        payload = {
            "change_id": change.change_id,
            "before": change.before_text,
            "after": change.after_text,
            "change_type": change.change_type,
            "risk_level": change.risk_hint,
            "context_before": before_full,
            "context_after": after_full,
            "signals": signals,
        }
        return self.provider.judge(payload)

    def judge_all(
        self,
        changes: list[ChangeItem],
        before_full: str,
        after_full: str,
    ) -> list[JudgeResult]:
        if not changes:
            return [
                JudgeResult(
                    is_faithful=True,
                    risk_level=E.LOW,
                    change_type=E.FORMAT,
                    score=100,
                    reason="治理前后文本完全一致",
                    evidence=["identical"],
                    confidence=1.0,
                    source="rule",
                )
            ]
        return [self.judge_change(c, before_full, after_full) for c in changes]
