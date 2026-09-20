#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Baseline-only quick scores for the demo case."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.baselines.embedding_similarity import embedding_similarity_score
from evaluation.baselines.single_llm import single_llm_score
from evaluation.baselines.text_similarity import similarity_score


def main() -> None:
    before = "项目于2025年6月11日完成验收，项目金额为1850万元。"
    after = "项目于2025年完成验收，项目金额为1800万元。"
    print({
        "text_similarity": similarity_score(before, after),
        "embedding_similarity": embedding_similarity_score(before, after),
        "single_llm": single_llm_score(before, after),
    })


if __name__ == "__main__":
    main()
