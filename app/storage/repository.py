from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.trace import utc_now
from app.models import enums as E
from app.models.schemas import (
    EvaluationResult,
    JudgeResult,
    TaskStatusResponse,
    TraceRecord,
)
from app.storage.database import Base, SessionLocal, init_db


class TaskRow(Base):
    __tablename__ = "evaluation_tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default=E.CREATED)
    before_text: Mapped[str] = mapped_column(Text)
    after_text: Mapped[str] = mapped_column(Text)
    config_id: Mapped[str] = mapped_column(String(64), default="default_v1")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trace_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TaskRepository:
    def __init__(self) -> None:
        init_db()

    def create_task(
        self,
        task_id: str,
        trace_id: str,
        before_text: str,
        after_text: str,
        config_id: str,
    ) -> None:
        now = utc_now()
        with SessionLocal() as session:
            row = TaskRow(
                task_id=task_id,
                trace_id=trace_id,
                status=E.CREATED,
                before_text=before_text,
                after_text=after_text,
                config_id=config_id,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.commit()

    def update_status(self, task_id: str, status: str, error: str | None = None) -> None:
        with SessionLocal() as session:
            row = session.get(TaskRow, task_id)
            if not row:
                return
            row.status = status
            row.updated_at = utc_now()
            if error is not None:
                row.error = error
            session.commit()

    def save_result(
        self,
        task_id: str,
        trace_id: str,
        result: EvaluationResult,
        stages: list[dict[str, Any]],
        model_name: str,
        model_version: str,
        prompt_version: str,
        input_hash: str,
    ) -> None:
        trace = TraceRecord(
            trace_id=trace_id,
            task_id=task_id,
            model_name=model_name,
            model_version=model_version,
            prompt_version=prompt_version,
            input_hash=input_hash,
            timestamp=utc_now(),
            stages=stages,
            changes=result.changes,
            judgements=result.issues,
            score=result.overall_score,
            route=result.route,
            meta={
                "risk_level": result.risk_level,
                "critical_issue": result.critical_issue,
                "low_confidence": result.low_confidence,
            },
        )
        with SessionLocal() as session:
            row = session.get(TaskRow, task_id)
            if not row:
                return
            row.result_json = result.model_dump_json()
            row.trace_json = trace.model_dump_json()
            row.updated_at = utc_now()
            session.commit()

    def get_task(self, task_id: str) -> TaskStatusResponse | None:
        with SessionLocal() as session:
            row = session.get(TaskRow, task_id)
            if not row:
                return None
            return TaskStatusResponse(
                task_id=row.task_id,
                trace_id=row.trace_id,
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
                error=row.error,
            )

    def get_result(self, task_id: str) -> EvaluationResult | None:
        with SessionLocal() as session:
            row = session.get(TaskRow, task_id)
            if not row or not row.result_json:
                return None
            return EvaluationResult.model_validate_json(row.result_json)

    def get_issues(self, task_id: str) -> list[JudgeResult]:
        result = self.get_result(task_id)
        return result.issues if result else []

    def get_trace(self, task_id: str) -> TraceRecord | None:
        with SessionLocal() as session:
            row = session.get(TaskRow, task_id)
            if not row or not row.trace_json:
                return None
            return TraceRecord.model_validate_json(row.trace_json)

    def list_recent(self, limit: int = 20) -> list[TaskStatusResponse]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(TaskRow).order_by(TaskRow.created_at.desc()).limit(limit)
            ).all()
            return [
                TaskStatusResponse(
                    task_id=r.task_id,
                    trace_id=r.trace_id,
                    status=r.status,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                    error=r.error,
                )
                for r in rows
            ]
