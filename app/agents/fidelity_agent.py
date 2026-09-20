from __future__ import annotations

from typing import Any, Optional

from app.agents.semantic_judge import SemanticJudge
from app.core.config import get_settings
from app.core.logger import logger
from app.core.trace import TraceBuilder, input_hash, new_task_id, new_trace_id, utc_now
from app.evaluators.scorer import FidelityScorer
from app.models import enums as E
from app.models.schemas import EvaluationResult, JudgeResult
from app.routing.router import RoutingEngine
from app.skills.change_classifier import ChangeClassifier
from app.skills.diff_skill import DiffSkill
from app.storage.repository import TaskRepository


class FidelityAgent:
    def __init__(self, repo: TaskRepository | None = None):
        self.repo = repo or TaskRepository()
        self.diff = DiffSkill()
        self.classifier = ChangeClassifier()
        self.judge = SemanticJudge()
        self.scorer = FidelityScorer()
        self.router = RoutingEngine()
        self.settings = get_settings()

    def evaluate(
        self,
        before_text: str,
        after_text: str,
        config_id: str = "default_v1",
        enable_stability: bool = False,
        stability_runs: int = 3,
        task_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        task_id = task_id or new_task_id()
        trace_id = trace_id or new_trace_id()
        trace = TraceBuilder(task_id, trace_id)
        ih = input_hash(before_text, after_text)

        self.repo.create_task(task_id, trace_id, before_text, after_text, config_id)
        try:
            self.repo.update_status(task_id, E.ANALYZING)
            diff_out = self.diff.run({"before": before_text, "after": after_text})
            changes = diff_out["changes"]
            trace.add_stage("diff", change_count=len(changes))

            self.repo.update_status(task_id, E.CLASSIFYING)
            classified = self.classifier.run({"changes": changes})["changes"]
            trace.add_stage(
                "classify",
                types=[c.change_type for c in classified],
            )

            self.repo.update_status(task_id, E.EVALUATING)
            judgements = self.judge.judge_all(classified, before_text, after_text)
            trace.add_stage("judge", count=len(judgements), provider=self.judge.provider.name)

            stability = None
            score_runs = []
            if enable_stability and stability_runs > 1:
                for _ in range(stability_runs):
                    js = self.judge.judge_all(classified, before_text, after_text)
                    s, _, _ = self.scorer.score(js)
                    score_runs.append(s)
                stability = self.scorer.stability(score_runs)
                judgements = self.judge.judge_all(classified, before_text, after_text)

            self.repo.update_status(task_id, E.SCORING)
            overall, dims, critical = self.scorer.score(judgements)
            if stability:
                overall = stability.mean
            low_conf = self.router.is_low_confidence(judgements)
            max_risk = self._max_risk(judgements)
            trace.add_stage("score", overall=overall, critical=critical, risk=max_risk)

            self.repo.update_status(task_id, E.ROUTING)
            route, route_reason = self.router.route(overall, judgements, critical, low_conf)
            summary = self._summary(overall, max_risk, route, route_reason, judgements)
            result = EvaluationResult(
                overall_score=round(overall, 2),
                route=route,
                risk_level=max_risk,
                summary=summary,
                issues=judgements,
                dimension_scores=dims,
                changes=classified,
                stability=stability,
                critical_issue=critical,
                low_confidence=low_conf,
            )
            trace.add_stage("route", route=route, reason=route_reason)

            self.repo.save_result(
                task_id=task_id,
                trace_id=trace_id,
                result=result,
                stages=trace.stages,
                model_name=self.settings.llm_model,
                model_version=self.settings.app_version,
                prompt_version=self.settings.prompt_version,
                input_hash=ih,
            )
            self.repo.update_status(task_id, E.COMPLETED)
            return {
                "task_id": task_id,
                "trace_id": trace_id,
                "status": E.COMPLETED,
                "result": result,
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("evaluation failed")
            self.repo.update_status(task_id, E.FAILED, error=str(exc))
            raise

    def _max_risk(self, judgements: list[JudgeResult]) -> str:
        rank = {E.LOW: 1, E.MEDIUM: 2, E.HIGH: 3, E.CRITICAL: 4}
        best = E.LOW
        for j in judgements:
            if rank.get(j.risk_level, 0) > rank.get(best, 0):
                best = j.risk_level
        return best

    def _summary(
        self,
        score: float,
        risk: str,
        route: str,
        route_reason: str,
        judgements: list[JudgeResult],
    ) -> str:
        types = sorted({j.change_type for j in judgements})
        return (
            f"综合保真度 {score:.1f}，最高风险 {risk}，路由 {route}。"
            f"变化类型: {', '.join(types)}。{route_reason}"
        )
