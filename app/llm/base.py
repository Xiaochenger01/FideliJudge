from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.schemas import JudgeResult


class JudgeProvider(ABC):
    name: str = "base"

    @abstractmethod
    def judge(self, payload: dict[str, Any]) -> JudgeResult:
        ...
