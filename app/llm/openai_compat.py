from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logger import logger
from app.llm.base import JudgeProvider
from app.llm.mock import MockJudgeProvider
from app.models import enums as E
from app.models.schemas import JudgeResult

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "semantic_judge_v1.txt"


class OpenAICompatProvider(JudgeProvider):
    name = "openai_compat"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.fallback = MockJudgeProvider()
        self.prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    def judge(self, payload: dict[str, Any]) -> JudgeResult:
        if not self.settings.llm_api_key:
            logger.warning("No API key; falling back to MockJudge")
            result = self.fallback.judge(payload)
            result.source = "fallback"
            result.confidence = min(result.confidence, 0.5)
            return result

        prompt = self.prompt_template.format(
            before=payload.get("before", ""),
            after=payload.get("after", ""),
            change_type=payload.get("change_type", "UNKNOWN"),
            context_before=payload.get("context_before", ""),
            context_after=payload.get("context_after", ""),
            risk_level=payload.get("risk_level", "MEDIUM"),
        )
        try:
            data = self._chat(prompt)
            return self._parse(data, payload)
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM judge failed: %s", exc)
            result = self.fallback.judge(payload)
            result.source = "fallback"
            result.confidence = min(result.confidence, 0.45)
            result.reason = f"LLM失败后回退: {result.reason}"
            return result

    def _chat(self, prompt: str) -> str:
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.settings.llm_model,
            "temperature": self.settings.llm_temperature,
            "messages": [
                {"role": "system", "content": "你是数据治理语义保真度评审员，只输出合法 JSON。"},
                {"role": "user", "content": prompt},
            ],
        }
        with httpx.Client(timeout=self.settings.llm_timeout) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _parse(self, content: str, payload: dict[str, Any]) -> JudgeResult:
        repaired = self._extract_json(content)
        if repaired is None:
            result = self.fallback.judge(payload)
            result.source = "fallback"
            result.confidence = 0.4
            result.reason = "JSON解析失败，已回退规则判断: " + result.reason
            return result
        return JudgeResult(
            change_id=payload.get("change_id"),
            is_faithful=bool(repaired.get("is_faithful", False)),
            risk_level=str(repaired.get("risk_level", E.MEDIUM)),
            change_type=str(repaired.get("change_type", payload.get("change_type", E.UNKNOWN))),
            score=float(repaired.get("score", 70)),
            reason=str(repaired.get("reason", "")),
            evidence=list(repaired.get("evidence") or []),
            confidence=float(repaired.get("confidence", 0.7)),
            source="llm",
        )

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None


def build_judge_provider() -> JudgeProvider:
    settings = get_settings()
    if settings.llm_provider in {"openai", "openai_compat"}:
        if not settings.llm_api_key:
            logger.warning(
                "FIDELI_LLM_PROVIDER=%s but no API key; using MockJudge. "
                "Set FIDELI_LLM_API_KEY or switch provider to mock.",
                settings.llm_provider,
            )
            return MockJudgeProvider()
        return OpenAICompatProvider()
    return MockJudgeProvider()
