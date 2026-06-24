"""
Misconception detection by answer pattern heuristics.
Without work-shown, these are conservative inferences only.
"""

from __future__ import annotations

MISCONCEPTIONS: dict[str, list[dict]] = {
    "geometric_series": [
        {"tag": "arithmetic_instead_of_geometric", "hint": "Used n*a/2 style sum"},
        {"tag": "rounded_too_early", "hint": "Decimal in answer suggests premature rounding"},
    ],
    "arithmetic_series": [
        {"tag": "common_difference_error", "hint": "Answer off by n"},
        {"tag": "uses_n_minus_one_wrong", "hint": "Off-by-one in n"},
    ],
    "differentiation": [
        {"tag": "derivative_power_error", "hint": "Answer differs from correct by constant factor"},
        {"tag": "solves_y_equals_zero_instead_of_derivative_zero", "hint": "Answer matches curve roots"},
    ],
    "integration": [
        {"tag": "sign_area_error", "hint": "Sign reversed"},
        {"tag": "integration_power_error", "hint": "Power not increased by 1"},
    ],
    "logarithms": [
        {"tag": "extraneous_solution", "hint": "Negative value given as log solution"},
        {"tag": "invalid_log_domain", "hint": "Solution ≤ 0"},
    ],
    "binomial_expansion": [
        {"tag": "coefficient_index_error", "hint": "Off by index shift"},
        {"tag": "sign_error", "hint": "Sign of coefficient wrong"},
    ],
}


def detect_misconceptions(item, submitted_answer: str, work_shown: str = None) -> list[str]:
    """
    Return list of likely misconception tags.
    Conservative: only flag when there's a clear signal.
    """
    topic = item.topic
    tags = []

    # Check for negative answer when positive required (log domain)
    if topic == "logarithms":
        try:
            val = float(submitted_answer.replace("$", "").strip())
            if val <= 0:
                tags.append("invalid_log_domain")
        except Exception:
            pass

    # Check for obvious sign flip
    try:
        from verification.sympy_tools import equivalent, _parse
        fa = item.final_answer
        neg_submitted = f"-({submitted_answer})"
        if equivalent(neg_submitted, fa):
            tags.append("sign_error")
    except Exception:
        pass

    return tags


def get_misconception_hint(tag: str) -> str:
    for misconceptions in MISCONCEPTIONS.values():
        for m in misconceptions:
            if m["tag"] == tag:
                return m["hint"]
    return tag
