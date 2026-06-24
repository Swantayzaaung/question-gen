"""
Question generator.
New flow: template → deterministic verify → LLM wording → re-verify → quality gate → store.
Fallback: LLM-only generation marked needs_review.
"""

from __future__ import annotations
import json
import os
import re
import sys
import uuid
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).parent))
from database import query_by_topic, get_all_topics, store_generated_item, init_db
from annotator import solvability_score, solvability_label

# Initialise DB (idempotent)
init_db()

_api_key = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=_api_key) if _api_key else None

PRESETS = {
    1: {"label": "Easy",        "steps": 1, "cleanliness": "clean", "focus": "single"},
    2: {"label": "Accessible",  "steps": 2, "cleanliness": "clean", "focus": "single"},
    3: {"label": "Moderate",    "steps": 3, "cleanliness": "mixed", "focus": "single"},
    4: {"label": "Challenging", "steps": 3, "cleanliness": "mixed", "focus": "multi"},
    5: {"label": "Hard",        "steps": 4, "cleanliness": "messy", "focus": "multi"},
}

STEPS_DESCRIPTIONS = {
    1: "exactly one significant technique (e.g. apply a single named formula, no chaining)",
    2: "exactly two significant techniques chained together",
    3: "three significant techniques",
    4: "four significant techniques",
    5: "five or more significant techniques",
}

CLEANLINESS_DESCRIPTIONS = {
    "clean": "The final answer MUST be a clean integer or a simple fraction with denominator ≤ 12. No surds, no decimals.",
    "mixed": "The final answer may be a simple surd (e.g. 2√3) or a fraction with moderate denominator. Avoid messy irrationals.",
    "messy": "The final answer may be an irrational number, a surd, or a decimal approximation. Messiness is acceptable.",
}

FOCUS_DESCRIPTIONS = {
    "single": "The question must stay entirely within the topic of {topic}. Do NOT bring in other syllabus areas.",
    "multi":  "The question may draw on one related syllabus topic in addition to {topic} (e.g. a calculus question that also uses trigonometry).",
}


def params_to_score(steps: int, cleanliness: str, focus: str) -> float:
    step_pen  = min((steps - 1) / 4, 1.0) * 0.30
    clean_map = {"clean": 0, "mixed": 1, "messy": 2}
    clean_pen = (clean_map.get(cleanliness, 0) / 2) * 0.40
    focus_pen = (0 if focus == "single" else 1) * 0.30
    return round(1.0 - step_pen - clean_pen - focus_pen, 3)


# ─── Template-based generation ──────────────────────────────────────────────

def _generate_from_template(topic: str, steps: int, cleanliness: str, focus: str):
    """
    Generate a deterministically-verified item using a template.
    Returns GeneratedItem or None.
    """
    from templates import get_template
    from verification.math_verifier import verify_item
    from quality.item_quality import evaluate_quality

    tmpl = get_template(topic)
    if not tmpl:
        return None

    try:
        params = tmpl.sample_parameters(steps=steps, cleanliness=cleanliness, focus=focus)
        errors = tmpl.validate_params(params)
        if errors:
            print(f"  Template param validation failed: {errors}")
            return None

        item = tmpl.build_question(params)
        vr = verify_item(item)
        item.verifier_result = vr

        if vr.is_correct:
            item.status = "verified"
        else:
            item.status = "needs_review"
            print(f"  Template item did not verify: {vr.errors}")

        # Quality gate
        examples = query_by_topic(topic, limit=10)
        qr = evaluate_quality(item, examples)
        item.quality_result = qr

        if item.status == "verified" and qr.passed:
            item.status = "approved"
        elif item.status == "verified":
            item.status = "needs_review"
            print(f"  Quality gate failed: {qr.issues}")

        return item
    except Exception as e:
        print(f"  Template generation error: {e}")
        return None


def _llm_rephrase(item, topic: str) -> bool:
    """
    Ask LLM to rephrase question wording in Edexcel style.
    Returns True if rephrasing succeeded without changing math.
    The item is mutated in place.
    """
    if not client:
        return True  # Skip LLM if no API key; keep template wording

    original_params = dict(item.parameters)
    original_answer = item.final_answer

    prompt = f"""You are rephrasing a math exam question into Edexcel IAL Pure Mathematics style.

ORIGINAL QUESTION:
{item.question_text}

PARTS:
{json.dumps([p.model_dump() for p in item.parts], indent=2)}

CANONICAL ANSWER: {item.final_answer}
TOPIC: {topic}

RULES:
- You MAY improve prose, Edexcel phrasing, and formatting.
- You MUST NOT change numbers, equations, domains, marks, or the final answer.
- You MUST NOT add new sub-parts or remove existing ones.
- Keep all LaTeX math formatting with $ and $$.
- Return ONLY valid JSON with fields: question_text, parts (array with part/instruction/marks).

JSON only, no other text."""

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)

        # Verify LLM didn't change mathematical content
        from verification.sympy_tools import equivalent
        new_answer = data.get("final_answer", original_answer)
        if new_answer and new_answer != original_answer:
            if not equivalent(new_answer, original_answer):
                print("  LLM changed final answer — keeping original wording")
                return True  # keep original

        if "question_text" in data:
            item.question_text = data["question_text"]
        if "parts" in data:
            from schemas import QuestionPart
            try:
                item.parts = [QuestionPart(**p) for p in data["parts"]]
            except Exception:
                pass  # keep original parts
        item.source = "hybrid"
        return True
    except Exception as e:
        print(f"  LLM rephrase error: {e}")
        return True  # keep original


# ─── LLM-only fallback ────────────────────────────────────────────────────────

GENERATION_PROMPT = """You are writing an Edexcel International A Level (IAL) Pure Mathematics exam question.

Topic: {topic}

REQUIREMENTS — follow these exactly:
1. Steps: The worked solution must use {steps_description}
2. Answer: {cleanliness_description}
3. Scope: {focus_description}

Here are {n_examples} real exam questions on this topic for style reference:

{examples}

---

Write ONE new original question meeting the requirements above.
Do not copy or closely paraphrase the examples.

FORMAT ALL MATHEMATICS USING LaTeX:
- Inline math: $...$ e.g. "Find the value of $x$"
- Display math on its own line: $$...$$

Return ONLY a JSON object with this structure:
{{
  "question_text": "Full question text with LaTeX math.",
  "parts": [{{"part": "a", "instruction": "what to do", "marks": 3}}],
  "worked_solution": ["Step 1: ...", "Step 2: ..."],
  "final_answer": "LaTeX-formatted final answer",
  "answer_type": "integer | rational | irrational | expression | coordinates | proof",
  "significant_steps": <integer>,
  "topics_used": ["primary topic"],
  "given_values": ["numerical values given"],
  "given_value_types": ["integer | rational | irrational | algebraic"]
}}"""


def _format_examples(examples: list[dict]) -> str:
    out = []
    for i, ex in enumerate(examples, 1):
        steps = json.loads(ex.get("worked_steps", "[]")) if isinstance(ex.get("worked_steps"), str) else []
        out.append(f"Example {i}:")
        out.append(f"  Question: {ex.get('question_text', '(no text)')}")
        out.append(f"  Answer: {ex.get('final_answer', '?')}")
        if steps:
            out.append("  Solution:")
            for s in steps:
                out.append(f"    - {s}")
        out.append("")
    return "\n".join(out)


def _generate_llm_fallback(topic: str, steps: int, cleanliness: str, focus: str,
                           max_attempts: int = 3) -> dict | None:
    """LLM-only generation. Returns raw dict marked needs_review."""
    if not client:
        return None

    examples = query_by_topic(topic, limit=3)
    if len(examples) < 3:
        examples = query_by_topic(topic, min_score=0.0, max_score=1.0, limit=3)

    prompt = GENERATION_PROMPT.format(
        topic=topic.replace("_", " "),
        steps_description=STEPS_DESCRIPTIONS.get(steps, f"{steps} significant techniques"),
        cleanliness_description=CLEANLINESS_DESCRIPTIONS.get(cleanliness, ""),
        focus_description=FOCUS_DESCRIPTIONS.get(focus, "").format(topic=topic.replace("_", " ")),
        n_examples=len(examples),
        examples=_format_examples(examples),
    )

    best = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            result = json.loads(raw)
            best = result
            if result.get("significant_steps") == steps:
                break
        except Exception:
            continue

    return best


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_question(topic: str, steps: int = 2, cleanliness: str = "clean",
                      focus: str = "single", max_attempts: int = 3) -> dict | None:
    """
    Primary generation function.
    Tries template-based generation first, falls back to LLM-only.
    Always returns a dict compatible with the frontend.
    """
    target_score = params_to_score(steps, cleanliness, focus)

    # Phase 1: Template generation
    item = _generate_from_template(topic, steps, cleanliness, focus)

    if item:
        # LLM rephrase (optional — skipped if no API key)
        if client:
            _llm_rephrase(item, topic)

        # Store in DB
        try:
            store_generated_item(item)
        except Exception as e:
            print(f"  Warning: could not store item: {e}")

        d = item.to_api_dict()
        d["solvability_score"] = target_score
        d["solvability"] = solvability_label(target_score)
        d["params"] = {"steps": steps, "cleanliness": cleanliness, "focus": focus}
        d["worked_solution"] = item.canonical_solution
        return d

    # Phase 2: LLM fallback
    print(f"  No template for '{topic}', using LLM fallback (needs_review)")
    result = _generate_llm_fallback(topic, steps, cleanliness, focus, max_attempts)
    if result is None:
        return None

    # Compute score from actual item properties, not blindly assign target
    actual_steps = result.get("significant_steps", steps)
    actual_answer_type = result.get("answer_type", "")
    actual_cleanliness = cleanliness  # we can't independently verify without SymPy for arbitrary LLM output
    computed_score = params_to_score(actual_steps, actual_cleanliness, focus)

    result["solvability_score"] = computed_score
    result["solvability"] = solvability_label(computed_score)
    result["params"] = {"steps": steps, "cleanliness": cleanliness, "focus": focus}
    result["status"] = "needs_review"
    result["source"] = "llm"
    # Mark clearly that this is unverified
    result["verification_note"] = "LLM-only generation. Not deterministically verified. Do not treat as approved."
    return result


def list_topics() -> list[str]:
    from templates import TEMPLATE_MAP
    db_topics = [t["topic_head"] for t in get_all_topics() if t["topic_head"]]
    template_topics = list(TEMPLATE_MAP.keys())
    all_topics = list(dict.fromkeys(template_topics + db_topics))
    return all_topics


def display_question(result: dict):
    if not result:
        print("  No question generated.")
        return
    print()
    print("━" * 60)
    print("  GENERATED QUESTION")
    print("━" * 60)
    print(result.get("question_text", "(no question text)"))
    for part in result.get("parts", []):
        if isinstance(part, dict):
            print(f"  ({part.get('part', '?')}) {part.get('instruction', '')}  [{part.get('marks', '?')} marks]")
    print()
    print(f"  Status: {result.get('status', 'unknown')}")
    print(f"  Source: {result.get('source', 'unknown')}")
    print(f"  Answer: {result.get('final_answer', '?')}")
    print("━" * 60)


if __name__ == "__main__":
    import argparse

    available = list_topics()

    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="geometric_series", choices=available)
    parser.add_argument("--steps", type=int, default=2)
    parser.add_argument("--cleanliness", default="clean")
    parser.add_argument("--focus", default="single")
    args = parser.parse_args()

    result = generate_question(args.topic, steps=args.steps,
                               cleanliness=args.cleanliness, focus=args.focus)
    display_question(result)
