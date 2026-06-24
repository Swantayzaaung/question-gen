"""
Merges parsed question paper + mark scheme into unified question records,
then computes solvability signals for each part.
"""

import json
from pathlib import Path


FIELD_DISTANCE = {
    ("integer",     "integer"):     0,
    ("integer",     "rational"):    1,
    ("integer",     "irrational"):  2,
    ("integer",     "expression"):  1,
    ("integer",     "coordinates"): 1,
    ("integer",     "proof"):       0,
    ("rational",    "rational"):    0,
    ("rational",    "integer"):     0,
    ("rational",    "irrational"):  2,
    ("rational",    "expression"):  1,
    ("irrational",  "irrational"):  0,
    ("irrational",  "integer"):     1,
    ("irrational",  "rational"):    1,
    ("algebraic",   "expression"):  0,
    ("algebraic",   "integer"):     1,
    ("algebraic",   "rational"):    1,
}


def get_field_distance(input_types: list[str], answer_type: str) -> int:
    if not input_types or not answer_type:
        return 1
    input_type = input_types[0] if input_types else "integer"
    return FIELD_DISTANCE.get((input_type, answer_type), 1)


def solvability_score(significant_steps: int, field_distance: int, adjunct_count: int) -> float:
    """
    Inverse-weighted composite score. Returns 0.0 (worst) to 1.0 (best).
    Weights: steps=0.30, cleanliness=0.40, adjuncts=0.30
    """
    if significant_steps is None:
        significant_steps = 1

    step_penalty    = min(significant_steps / 5.0, 1.0)
    clean_penalty   = min(field_distance / 3.0, 1.0)
    adjunct_penalty = min(adjunct_count / 3.0, 1.0)

    raw = 0.30 * step_penalty + 0.40 * clean_penalty + 0.30 * adjunct_penalty
    return round(1.0 - raw, 3)


def solvability_label(score: float) -> str:
    if score >= 0.75:
        return "HIGH"
    if score >= 0.50:
        return "MODERATE"
    return "LOW"


def merge(paper_path: str, ms_path: str, output_path: str = None) -> list[dict]:
    with open(paper_path) as f:
        paper = {q["question_number"]: q for q in json.load(f)["questions"]}
    with open(ms_path) as f:
        ms = {q["question_number"]: q for q in json.load(f)["questions"]}

    records = []
    for qnum in sorted(paper.keys()):
        pq = paper.get(qnum, {})
        mq = ms.get(qnum, {})

        paper_parts  = {p["part"]: p for p in pq.get("parts", [])}
        ms_parts     = {p["part"]: p for p in mq.get("parts", [])}
        all_parts    = sorted(set(paper_parts) | set(ms_parts))

        topic_signals   = pq.get("topic_signals", [])
        adjunct_count   = max(0, len(topic_signals) - 1)
        input_types     = pq.get("given_value_types", ["integer"])

        merged_parts = []
        for part_label in all_parts:
            pp = paper_parts.get(part_label, {})
            mp = ms_parts.get(part_label, {})

            answer_type      = mp.get("answer_type") or "integer"
            significant_steps = mp.get("significant_steps") or 0
            field_dist       = get_field_distance(input_types, answer_type)
            score            = solvability_score(significant_steps, field_dist, adjunct_count)

            merged_parts.append({
                "part":              part_label,
                "question_text":     pp.get("question_text"),
                "marks":             pp.get("marks") or mp.get("marks_total"),
                "command_word":      pp.get("command_word"),
                "significant_steps": significant_steps,
                "mark_breakdown":    mp.get("mark_breakdown", {}),
                "worked_steps":      mp.get("worked_steps", []),
                "final_answer":      mp.get("final_answer"),
                "answer_type":       answer_type,
                "field_distance":    field_dist,
                "solvability_score": score,
                "solvability":       solvability_label(score),
            })

        records.append({
            "question_number": qnum,
            "topic_head":      topic_signals[0] if topic_signals else None,
            "topic_signals":   topic_signals,
            "adjunct_count":   adjunct_count,
            "given_values":    pq.get("given_values", []),
            "given_value_types": input_types,
            "parts":           merged_parts,
        })

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(records, f, indent=2)

    return records
