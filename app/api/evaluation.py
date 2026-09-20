from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents.fidelity_agent import FidelityAgent
from app.core.trace import new_task_id, new_trace_id
from app.models import enums as E
from app.models.schemas import (
    EvaluationCreateRequest,
    EvaluationCreateResponse,
    EvaluationResult,
    TaskStatusResponse,
    TraceRecord,
)
from app.storage.repository import TaskRepository

router = APIRouter(prefix="/api/v1", tags=["evaluations"])
repo = TaskRepository()
agent = FidelityAgent(repo=repo)


@router.post("/evaluations", response_model=EvaluationCreateResponse)
def create_evaluation(req: EvaluationCreateRequest) -> EvaluationCreateResponse:
    task_id = new_task_id()
    trace_id = new_trace_id()
    # Phase 1: synchronous pipeline for demo reliability
    out = agent.evaluate(
        before_text=req.before_text,
        after_text=req.after_text,
        config_id=req.config_id,
        enable_stability=req.enable_stability,
        stability_runs=req.stability_runs,
        task_id=task_id,
        trace_id=trace_id,
    )
    return EvaluationCreateResponse(
        task_id=out["task_id"],
        trace_id=out["trace_id"],
        status=out["status"],
    )


@router.get("/evaluations/{task_id}", response_model=TaskStatusResponse)
def get_evaluation(task_id: str) -> TaskStatusResponse:
    task = repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.get("/evaluations/{task_id}/result", response_model=EvaluationResult)
def get_result(task_id: str) -> EvaluationResult:
    result = repo.get_result(task_id)
    if not result:
        task = repo.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="task not found")
        if task.status == E.FAILED:
            raise HTTPException(status_code=500, detail=task.error or "failed")
        raise HTTPException(status_code=409, detail=f"result not ready: {task.status}")
    return result


@router.get("/evaluations/{task_id}/issues")
def get_issues(task_id: str):
    task = repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return {"task_id": task_id, "issues": repo.get_issues(task_id)}


@router.get("/evaluations/{task_id}/trace", response_model=TraceRecord)
def get_trace(task_id: str) -> TraceRecord:
    trace = repo.get_trace(task_id)
    if not trace:
        raise HTTPException(status_code=404, detail="trace not found")
    return trace
