#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Agent vs human 3-class agreement (core course metric)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.fidelity_agent import FidelityAgent  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.evaluators.calibration import summarize  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    labels_path = ROOT / "datasets" / "human_labels.jsonl"
    cases_path = ROOT / "datasets" / "evaluation.jsonl"
    labels = {r["id"]: r for r in load_jsonl(labels_path)}
    cases = {r["id"]: r for r in load_jsonl(cases_path)}
    agent = FidelityAgent()
    pred, gold, details = [], [], []
    for case_id, lab in labels.items():
        case = cases[case_id]
        out = agent.evaluate(case["before"], case["after"])
        route = out["result"].route
        pred.append(route)
        gold.append(lab["human_route"])
        details.append({
            "id": case_id,
            "human_route": lab["human_route"],
            "agent_route": route,
            "agent_score": out["result"].overall_score,
            "match": route == lab["human_route"],
        })
    stats = summarize(pred, gold)
    b_pred = ["SAFE" if r == "AUTO_PASS" else "UNSAFE" for r in pred]
    b_gold = ["SAFE" if r == "AUTO_PASS" else "UNSAFE" for r in gold]
    binary_stats = summarize(b_pred, b_gold)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "annotator": "author_v1",
        "n": len(gold),
        "judge_provider": get_settings().llm_provider,
        "metrics_3class": stats,
        "metrics_binary_safe_unsafe": binary_stats,
        "details": details,
        "note": "三档路由 AUTO_PASS/REVIEW/REJECT；标注人为数据集作者。binary 将 REVIEW+REJECT 合并为 UNSAFE。",
    }
    out_dir = ROOT / "evaluation" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "human_agreement.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"3class": stats, "binary": binary_stats}, ensure_ascii=False, indent=2))
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
