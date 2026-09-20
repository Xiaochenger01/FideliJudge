from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Position(BaseModel):
    start: int
    end: int


class EvaluationCreateRequest(BaseModel):
    before_text: str = Field(..., min_length=1)
    after_text: str = Field(..., min_length=1)
    config_id: str = "default_v1"
    enable_stability: bool = False
    stability_runs: int = Field(default=3, ge=1, le=10)


class EvaluationCreateResponse(BaseModel):
    task_id: str
    trace_id: str
    status: str


class ChangeItem(BaseModel):
    change_id: str
    before_text: str
    after_text: str
    change_type: str
    position_before: Position
    position_after: Position
    risk_hint: str = "LOW"


class JudgeResult(BaseModel):
    change_id: Optional[str] = None
    is_faithful: bool
    risk_level: str
    change_type: str
    score: float
    reason: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    source: str = "rule"  # rule | mock_llm | llm | fallback


class DimensionScores(BaseModel):
    structure: float = 100.0
    entity: float = 100.0
    number: float = 100.0
    time: float = 100.0
    factual: float = 100.0


class StabilityStats(BaseModel):
    n: int
    mean: float
    std: float
    variance: float
    scores: list[float] = Field(default_factory=list)
    agreement_rate: float = 1.0


class EvaluationResult(BaseModel):
    overall_score: float
    route: str
    risk_level: str
    summary: str
    issues: list[JudgeResult] = Field(default_factory=list)
    dimension_scores: DimensionScores = Field(default_factory=DimensionScores)
    changes: list[ChangeItem] = Field(default_factory=list)
    stability: Optional[StabilityStats] = None
    critical_issue: bool = False
    low_confidence: bool = False


class TaskStatusResponse(BaseModel):
    task_id: str
    trace_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None


class TraceRecord(BaseModel):
    trace_id: str
    task_id: str
    model_name: str
    model_version: str
    prompt_version: str
    input_hash: str
    timestamp: datetime
    stages: list[dict[str, Any]] = Field(default_factory=list)
    changes: list[ChangeItem] = Field(default_factory=list)
    judgements: list[JudgeResult] = Field(default_factory=list)
    score: Optional[float] = None
    route: Optional[str] = None
    meta: dict[str, Any] = Field(default_factory=dict)
