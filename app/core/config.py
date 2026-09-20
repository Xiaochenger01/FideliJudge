from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Settings(BaseModel):
    app_name: str = "FideliJudge"
    app_version: str = "0.1.0"
    database_url: str = Field(default_factory=lambda: os.getenv(
        "FIDELI_DATABASE_URL",
        f"sqlite:///{ROOT / 'data' / 'fideli.db'}",
    ))
    llm_provider: str = Field(default_factory=lambda: os.getenv("FIDELI_LLM_PROVIDER", "mock"))
    llm_api_key: str = Field(default_factory=lambda: os.getenv("FIDELI_LLM_API_KEY", ""))
    llm_base_url: str = Field(default_factory=lambda: os.getenv("FIDELI_LLM_BASE_URL", "https://api.openai.com/v1"))
    llm_model: str = Field(default_factory=lambda: os.getenv("FIDELI_LLM_MODEL", "gpt-4o-mini"))
    llm_timeout: float = 30.0
    llm_temperature: float = 0.0
    prompt_version: str = "v1.0"


@lru_cache
def get_settings() -> Settings:
    model_cfg = _load_yaml("model.yaml")
    agent = model_cfg.get("agent", {})
    model = model_cfg.get("model", {})
    s = Settings(
        app_name=agent.get("name", "FideliJudge"),
        app_version=str(agent.get("version", "0.1.0")),
        llm_provider=os.getenv("FIDELI_LLM_PROVIDER", model.get("provider", "mock")),
        llm_model=os.getenv("FIDELI_LLM_MODEL", model.get("name", "gpt-4o-mini")),
        llm_base_url=os.getenv("FIDELI_LLM_BASE_URL", model.get("base_url", "https://api.openai.com/v1")),
        llm_timeout=float(model.get("timeout", 30)),
        llm_temperature=float(os.getenv("FIDELI_LLM_TEMPERATURE", model.get("temperature", 0))),
        prompt_version=str(model.get("prompt_version", "v1.0")),
    )
    return s


@lru_cache
def get_routing_config() -> dict[str, Any]:
    return _load_yaml("routing.yaml")


@lru_cache
def get_scoring_config() -> dict[str, Any]:
    return _load_yaml("scoring.yaml")


@lru_cache
def get_model_config() -> dict[str, Any]:
    return _load_yaml("model.yaml")
