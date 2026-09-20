from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any


def new_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:12]}"


def new_trace_id() -> str:
    return f"trace_{uuid.uuid4().hex[:12]}"


def new_change_id(idx: int) -> str:
    return f"chg_{idx:03d}"


def input_hash(before: str, after: str) -> str:
    raw = f"{before}\n---\n{after}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TraceBuilder:
    def __init__(self, task_id: str, trace_id: str):
        self.task_id = task_id
        self.trace_id = trace_id
        self.stages: list[dict[str, Any]] = []

    def add_stage(self, name: str, status: str = "ok", **payload: Any) -> None:
        self.stages.append({
            "stage": name,
            "status": status,
            "timestamp": utc_now().isoformat(),
            **payload,
        })
