"""
Auto-grading for assignment submissions.

Each assignment question is a snapshot dict (from the paper tray / generator output):
  { question_text, parts: [{part, instruction, marks}], final_answer, worked_solution,
    topic, item_id?, ... }

Scoring model: an answer judged equivalent to the canonical final answer earns the
question's full marks; otherwise 0. Teachers can override per-answer scores afterwards.
"""

from __future__ import annotations

from verification.sympy_tools import equivalent


def question_max_marks(question: dict) -> float:
    parts = question.get("parts") or []
    total = sum(p.get("marks", 0) or 0 for p in parts)
    return float(total) if total > 0 else 1.0


def detect_misconceptions_safe(question: dict, submitted: str) -> list[str]:
    """Misconception tagging needs a GeneratedItem-shaped object; degrade gracefully."""
    try:
        from pedagogy.misconception_tags import detect_misconceptions
        from schemas import GeneratedItem, QuestionPart

        item = GeneratedItem(
            item_id=question.get("item_id") or "snapshot",
            source=question.get("source") or "llm",
            topic=question.get("topic") or "unknown",
            primary_skill=question.get("primary_skill") or question.get("topic") or "unknown",
            question_text=question.get("question_text") or "",
            parts=[QuestionPart(**p) for p in (question.get("parts") or [])
                   if {"part", "instruction", "marks"} <= set(p)],
            final_answer=str(question.get("final_answer") or ""),
            answer_type=question.get("answer_type") or "expression",
            significant_steps=int(question.get("significant_steps") or 1),
            marks=int(question_max_marks(question)),
        )
        return detect_misconceptions(item, submitted)
    except Exception:
        return []


def grade_answer(question: dict, submitted: str) -> dict:
    canonical = str(question.get("final_answer") or "").strip()
    submitted = (submitted or "").strip()

    if not submitted:
        is_correct = False
    elif not canonical:
        is_correct = False  # nothing to grade against — teacher must mark manually
    else:
        try:
            is_correct = bool(equivalent(submitted, canonical))
        except Exception:
            is_correct = False

    max_score = question_max_marks(question)
    return {
        "submitted_answer": submitted,
        "is_correct": is_correct,
        "auto_score": max_score if is_correct else 0.0,
        "max_score": max_score,
        "detected_misconceptions": [] if is_correct else detect_misconceptions_safe(question, submitted),
    }


def grade_submission(questions: list[dict], answers: list[str]) -> tuple[list[dict], float]:
    """Grade every answer against its question. Returns (per-answer results, auto_total)."""
    results = []
    auto_total = 0.0
    for i, question in enumerate(questions):
        submitted = answers[i] if i < len(answers) else ""
        graded = grade_answer(question, submitted)
        graded["question_index"] = i
        results.append(graded)
        auto_total += graded["auto_score"]
    return results, auto_total
