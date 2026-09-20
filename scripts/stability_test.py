#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stability test: same input, N runs, report mean/std/variance.

Mock Judge is deterministic (std=0 is expected, not an LLM-stability result).
For a real stability claim, set an API key and temperature>0:

  export FIDELI_LLM_PROVIDER=openai_compat
  export FIDELI_LLM_API_KEY=sk-...
  export FIDELI_LLM_TEMPERATURE=0.7
  python scripts/stability_test.py 5
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.fidelity_agent import FidelityAgent  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.evaluators.scorer import FidelityScorer  # noqa: E402


DEMO_BEFORE = "项目于2025年6月11日完成验收，项目金额为1850万元。"
DEMO_AFTER = "项目于2025年完成验收，项目金额为1800万元。"


def main(n: int = 5) -> None:
    settings = get_settings()
    agent = FidelityAgent()
    scores = []
    routes = []
    for i in range(n):
        out = agent.evaluate(DEMO_BEFORE, DEMO_AFTER)
        result = out["result"]
        scores.append(result.overall_score)
        routes.append(result.route)
        print(f"run {i+1}: score={result.overall_score} route={result.route}")

    stats = FidelityScorer().stability(scores)
    deterministic = agent.judge.provider.name == "mock" and settings.llm_temperature == 0
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n": n,
        "scores": scores,
        "routes": routes,
        "stats": stats.model_dump(),
        "route_agreement": routes.count(routes[0]) / len(routes) if routes else 1.0,
        "judge_provider": agent.judge.provider.name,
        "temperature": settings.llm_temperature,
        "deterministic_mock": deterministic,
        "note": (
            "std=0 来自确定性 Mock Judge，不能当作 LLM 稳定性证据。"
            if deterministic
            else "非零温度下的多次运行，可作为 LLM-as-Judge 稳定性证据。"
        ),
    }
    out_dir = ROOT / "evaluation" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "stability_latest.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("stats", "deterministic_mock", "note")}, ensure_ascii=False, indent=2))
    print(f"Saved: {path}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    main(n)
