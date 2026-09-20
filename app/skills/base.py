from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    name: str = "base"
    version: str = "1.0.0"

    @abstractmethod
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        ...
