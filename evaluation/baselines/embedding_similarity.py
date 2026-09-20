from __future__ import annotations

import math
import re
from collections import Counter

# Honest lexical baseline: character n-gram TF-IDF cosine.
# This is NOT a neural embedding. Optional: install sentence-transformers and set
# FIDELI_USE_ST_EMBEDDING=1 to swap in a real encoder.


def _ngrams(text: str, n: int = 2) -> list[str]:
    chars = list(re.sub(r"\s+", "", text.lower()))
    if len(chars) < n:
        return chars or [text]
    return ["".join(chars[i : i + n]) for i in range(len(chars) - n + 1)]


def _tfidf_vec(before: str, after: str, n: int = 2) -> tuple[list[float], list[float]]:
    b_grams = _ngrams(before, n)
    a_grams = _ngrams(after, n)
    vocab = sorted(set(b_grams) | set(a_grams))
    df = Counter()
    for grams in (set(b_grams), set(a_grams)):
        for g in grams:
            df[g] += 1
    n_docs = 2

    def vec(grams: list[str]) -> list[float]:
        tf = Counter(grams)
        out = []
        for token in vocab:
            idf = math.log((1 + n_docs) / (1 + df[token])) + 1.0
            out.append(tf[token] * idf)
        norm = math.sqrt(sum(v * v for v in out)) or 1.0
        return [v / norm for v in out]

    return vec(b_grams), vec(a_grams)


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def embedding_similarity_score(before: str, after: str) -> float:
    """Char 2-gram TF-IDF cosine mapped to 0-100 (lexical, not neural)."""
    vb, va = _tfidf_vec(before, after)
    sim = cosine(vb, va)
    return round(max(0.0, min(1.0, sim)) * 100, 2)
