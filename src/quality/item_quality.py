"""
Quality gates for generated items.
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def evaluate_quality(item, source_examples: list[dict] = None) -> "object":
    """
    Run quality gates on a generated item. Returns QualityResult.
    """
    from schemas import QualityResult
    from verification.similarity import find_max_similarity, DUPLICATE_THRESHOLD

    issues = []
    checks_passed = 0
    total_checks = 8

    # 1. Math verified
    if item.verifier_result and item.verifier_result.is_correct:
        checks_passed += 1
    else:
        issues.append("Math not verified")

    # 2. Has question text
    if item.question_text and len(item.question_text.strip()) > 20:
        checks_passed += 1
    else:
        issues.append("Question text too short or missing")

    # 3. Has final answer
    if item.final_answer and item.final_answer.strip():
        checks_passed += 1
    else:
        issues.append("Final answer missing")

    # 4. Significant steps > 0
    if item.significant_steps and item.significant_steps > 0:
        checks_passed += 1
    else:
        issues.append("significant_steps must be > 0")

    # 5. Marks plausible
    if 1 <= item.marks <= 12:
        checks_passed += 1
    else:
        issues.append(f"Marks {item.marks} outside plausible range [1, 12]")

    # 6. Has parts
    if item.parts:
        checks_passed += 1
    else:
        issues.append("No parts defined")

    # 7. No obvious ambiguity (no "etc" or vague wording)
    vague_patterns = [r'\betc\b', r'\bvaguely\b', r'\bsomething\b']
    has_ambiguity = any(re.search(p, item.question_text, re.I) for p in vague_patterns)
    if not has_ambiguity:
        checks_passed += 1
    else:
        issues.append("Question contains ambiguous wording")

    # 8. Near-duplicate check
    near_dup_score = 0.0
    if source_examples:
        texts = [e.get("question_text", "") for e in source_examples if e.get("question_text")]
        if texts:
            near_dup_score = find_max_similarity(item.question_text, texts)

    syllabus_ok = True
    if near_dup_score < DUPLICATE_THRESHOLD:
        checks_passed += 1
    else:
        issues.append(f"Near-duplicate detected (similarity={near_dup_score:.2f})")

    score = checks_passed / total_checks
    passed = score >= 0.75 and "Math not verified" not in issues

    return QualityResult(
        passed=passed,
        score=round(score, 3),
        issues=issues,
        near_duplicate_score=round(near_dup_score, 3),
        syllabus_ok=syllabus_ok,
        ambiguity_ok=not has_ambiguity,
        difficulty_ok=True,
    )
