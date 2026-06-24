"""
Near-duplicate detection using token n-gram Jaccard similarity.
Falls back to simple token overlap if sklearn unavailable.
"""

from __future__ import annotations
import re


def _tokenize(text: str) -> list[str]:
    text = re.sub(r'\$+[^$]+\$+', ' MATH ', text)
    text = re.sub(r'[^a-zA-Z0-9 ]', ' ', text.lower())
    return [t for t in text.split() if t]


def _ngrams(tokens: list[str], n: int = 2) -> set[tuple]:
    return set(zip(*[tokens[i:] for i in range(n)]))


def jaccard_similarity(text_a: str, text_b: str, n: int = 2) -> float:
    """Jaccard similarity of bigram token sets."""
    a_toks = _tokenize(text_a)
    b_toks = _tokenize(text_b)

    if not a_toks or not b_toks:
        return 0.0

    a_ng = _ngrams(a_toks, n)
    b_ng = _ngrams(b_toks, n)

    if not a_ng and not b_ng:
        return 1.0
    if not a_ng or not b_ng:
        return 0.0

    intersection = len(a_ng & b_ng)
    union = len(a_ng | b_ng)
    return intersection / union if union else 0.0


def find_max_similarity(question_text: str, candidates: list[str]) -> float:
    """Return max Jaccard similarity against a list of candidate texts."""
    if not candidates:
        return 0.0
    return max(jaccard_similarity(question_text, c) for c in candidates)


DUPLICATE_THRESHOLD = 0.55
