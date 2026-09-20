#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run baselines + FideliJudge on evaluation.jsonl and write a report."""
from __future__ import annotations

import difflib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.fidelity_agent import FidelityAgent  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from evaluation.baselines.embedding_similarity import embedding_similarity_score  # noqa: E402
from evaluation.baselines.single_llm import single_llm_score  # noqa: E402
from evaluation.baselines.text_similarity import similarity_score  # noqa: E402


def load_cases(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def binary_pred_from_route(route: str) -> str:
    return "SAFE" if route == "AUTO_PASS" else "UNSAFE"


def metrics(y_true: list[str], y_pred: list[str]) -> dict:
    tp = fp = tn = fn = 0
    for t, p in zip(y_true, y_pred):
        if t == "UNSAFE" and p == "UNSAFE":
            tp += 1
        elif t == "SAFE" and p == "UNSAFE":
            fp += 1
        elif t == "SAFE" and p == "SAFE":
            tn += 1
        else:
            fn += 1
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc = (tp + tn) / len(y_true) if y_true else 0.0
    return {
        "accuracy": round(acc, 4),
        "precision_unsafe": round(prec, 4),
        "recall_unsafe": round(rec, 4),
        "f1_unsafe": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def first_char_spans(before: str, after: str) -> tuple[tuple[int, int], tuple[int, int]] | None:
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            return (i1, i2), (j1, j2)
    return None


def spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def main() -> None:
    dataset = ROOT / "datasets" / "evaluation.jsonl"
    if not dataset.exists():
        from scripts.build_dataset import main as build
        build()
    cases = load_cases(dataset)
    settings = get_settings()
    agent = FidelityAgent()

    gold = []
    gold_routes = []
    pred_ours = []
    pred_routes = []
    pred_sim = []
    pred_emb = []
    pred_llm = []
    details = []
    loc_hits = 0
    loc_total = 0
    sources = Counter()

    for case in cases:
        gold.append(case["label"])
        gold_routes.append(case.get("route", "REVIEW"))
        out = agent.evaluate(case["before"], case["after"])
        result = out["result"]
        ours_label = binary_pred_from_route(result.route)
        pred_ours.append(ours_label)
        pred_routes.append(result.route)

        sim = similarity_score(case["before"], case["after"])
        emb = embedding_similarity_score(case["before"], case["after"])
        llm = single_llm_score(case["before"], case["after"])
        pred_sim.append("SAFE" if sim >= 90 else "UNSAFE")
        pred_emb.append("SAFE" if emb >= 90 else "UNSAFE")
        pred_llm.append("SAFE" if llm >= 85 else "UNSAFE")

        pred_types = [c.change_type for c in result.changes] or [i.change_type for i in result.issues]
        for issue in result.issues:
            sources[issue.source] += 1

        if case["before"] != case["after"]:
            loc_total += 1
            tokens = case.get("anchor_tokens") or []
            if tokens:
                blob = "".join(c.before_text + c.after_text for c in result.changes)
                hit = all(t in blob for t in tokens)
            else:
                gold_spans = first_char_spans(case["before"], case["after"])
                hit = False
                if gold_spans:
                    gb, ga = gold_spans
                    for c in result.changes:
                        pb = (c.position_before.start, c.position_before.end)
                        pa = (c.position_after.start, c.position_after.end)
                        if spans_overlap(pb, gb) or spans_overlap(pa, ga):
                            hit = True
                            break
            if hit:
                loc_hits += 1

        details.append({
            "id": case["id"],
            "gold": case["label"],
            "gold_route": case.get("route"),
            "ours_route": result.route,
            "ours_score": result.overall_score,
            "ours_risk": result.risk_level,
            "ours_label": ours_label,
            "pred_types": pred_types,
            "sim_score": sim,
            "emb_score": emb,
            "ablation_wo_diff_score": llm,
        })

    oc_gold, oc_pred = [], []
    for case, d in zip(cases, details):
        if case["change_type"] in {"DELETION", "FACT"}:
            oc_gold.append(case["label"])
            oc_pred.append(d["ours_label"])

    route_acc = (
        sum(p == g for p, g in zip(pred_routes, gold_routes)) / len(gold_routes)
        if gold_routes else 0.0
    )

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset.relative_to(ROOT).as_posix(),
        "n": len(cases),
        "ablation": "sentence_align",
        "judge_mode": {
            "provider": agent.judge.provider.name,
            "config_provider": settings.llm_provider,
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "note": "本轮默认 mock（规则+确定性 Judge）。接真实 LLM 需设置 FIDELI_LLM_API_KEY。",
        },
        "judge_source_counts": dict(sources),
        "methods": {
            "fideli_judge": {
                **metrics(gold, pred_ours),
                "route_accuracy": round(route_acc, 4),
                "localization_accuracy": round(loc_hits / loc_total, 4) if loc_total else 0.0,
            },
            "text_similarity": metrics(gold, pred_sim),
            "char_ngram_tfidf": metrics(gold, pred_emb),
            "ablation_wo_diff": {
                **metrics(gold, pred_llm),
                "note": "复用本系统 ChangeClassifier + MockJudge，无 Diff 锚点。不是外部基线。",
            },
        },
        "overcleaning_f1": metrics(oc_gold, oc_pred),
        "caveats": {
            "localization": "含 anchor_tokens 的样本按是否覆盖全部关键片段计；其余为 span 重叠，短文本上偏乐观。",
            "overcleaning_f1": "仅在 gold change_type ∈ {DELETION, FACT} 的子集上计算，需含 SAFE 负样本才有意义。",
            "ablation_wo_diff": "复用分类器，短单句上会接近主方法；长文才拉开与字面相似度的差距。",
            "human_labels": "author_v1 与数据集 route 同源，不是独立标注；需另找同学填写 datasets/peer_labels.jsonl。",
        },
        "details": details,
    }

    out_dir = ROOT / "evaluation" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"eval_{stamp}.json"
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    out_path.write_text(payload, encoding="utf-8")
    (out_dir / "latest.json").write_text(payload, encoding="utf-8")
    (out_dir / "ablation_sentence_align.json").write_text(payload, encoding="utf-8")

    print(json.dumps({
        "judge_mode": report["judge_mode"],
        "judge_source_counts": report["judge_source_counts"],
        "methods": report["methods"],
        "overcleaning_f1": report["overcleaning_f1"],
        "caveats": report["caveats"],
    }, ensure_ascii=False, indent=2))
    print(f"Report saved: {out_path}")


if __name__ == "__main__":
    main()
