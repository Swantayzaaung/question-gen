"""
Edexcel IAL Pure Mathematics P2 skill graph.
"""

from __future__ import annotations
from schemas import Skill

SKILLS: dict[str, Skill] = {
    "arithmetic_series_nth_term": Skill(
        skill_id="arithmetic_series_nth_term",
        topic="arithmetic_series",
        display_name="Arithmetic series: nth term",
        prerequisites=[],
        allowed_command_words=["find", "show", "prove", "write down"],
        typical_marks=2,
        common_misconceptions=[
            "uses n instead of n-1 in formula",
            "confuses first term and common difference",
        ],
    ),
    "arithmetic_series_sum": Skill(
        skill_id="arithmetic_series_sum",
        topic="arithmetic_series",
        display_name="Arithmetic series: sum of n terms",
        prerequisites=["arithmetic_series_nth_term"],
        allowed_command_words=["find", "calculate", "show", "prove"],
        typical_marks=3,
        common_misconceptions=[
            "uses_n_minus_one_wrong",
            "average_term_error",
            "common_difference_error",
        ],
    ),
    "geometric_series_nth_term": Skill(
        skill_id="geometric_series_nth_term",
        topic="geometric_series",
        display_name="Geometric series: nth term",
        prerequisites=[],
        allowed_command_words=["find", "write down", "show"],
        typical_marks=2,
        common_misconceptions=[
            "missing_power_n",
            "ratio_sign_error",
        ],
    ),
    "geometric_series_sum": Skill(
        skill_id="geometric_series_sum",
        topic="geometric_series",
        display_name="Geometric series: sum of n terms",
        prerequisites=["geometric_series_nth_term"],
        allowed_command_words=["find", "calculate", "show"],
        typical_marks=3,
        common_misconceptions=[
            "arithmetic_instead_of_geometric",
            "wrong_sum_formula",
            "rounded_too_early",
        ],
    ),
    "geometric_series_convergence": Skill(
        skill_id="geometric_series_convergence",
        topic="geometric_series",
        display_name="Geometric series: sum to infinity",
        prerequisites=["geometric_series_sum"],
        allowed_command_words=["find", "show", "prove", "state"],
        typical_marks=3,
        common_misconceptions=[
            "applies_formula_when_diverges",
            "wrong_convergence_condition",
        ],
    ),
    "differentiation_power_rule": Skill(
        skill_id="differentiation_power_rule",
        topic="differentiation",
        display_name="Differentiation: power rule",
        prerequisites=[],
        allowed_command_words=["differentiate", "find", "show"],
        typical_marks=2,
        common_misconceptions=[
            "derivative_power_error",
            "forgets_to_decrease_power",
        ],
    ),
    "differentiation_chain_rule": Skill(
        skill_id="differentiation_chain_rule",
        topic="differentiation",
        display_name="Differentiation: chain rule",
        prerequisites=["differentiation_power_rule"],
        allowed_command_words=["differentiate", "find", "show"],
        typical_marks=3,
        common_misconceptions=["forgot_chain_rule"],
    ),
    "differentiation_stationary_points": Skill(
        skill_id="differentiation_stationary_points",
        topic="differentiation",
        display_name="Differentiation: stationary points",
        prerequisites=["differentiation_power_rule"],
        allowed_command_words=["find", "determine", "show", "classify"],
        typical_marks=4,
        common_misconceptions=[
            "solves_y_equals_zero_instead_of_derivative_zero",
            "missing_y_coordinate",
            "classification_error",
        ],
    ),
    "integration_power_rule": Skill(
        skill_id="integration_power_rule",
        topic="integration",
        display_name="Integration: power rule",
        prerequisites=["differentiation_power_rule"],
        allowed_command_words=["integrate", "find", "show"],
        typical_marks=2,
        common_misconceptions=["integration_power_error"],
    ),
    "integration_area_under_curve": Skill(
        skill_id="integration_area_under_curve",
        topic="integration",
        display_name="Integration: area under curve",
        prerequisites=["integration_power_rule"],
        allowed_command_words=["find", "calculate", "show"],
        typical_marks=4,
        common_misconceptions=[
            "sign_area_error",
            "bound_order_error",
        ],
    ),
    "logarithm_laws": Skill(
        skill_id="logarithm_laws",
        topic="logarithms",
        display_name="Logarithm laws",
        prerequisites=[],
        allowed_command_words=["find", "solve", "show", "simplify"],
        typical_marks=3,
        common_misconceptions=[
            "invalid_log_domain",
            "treats_log_sum_as_sum_logs",
            "extraneous_solution",
        ],
    ),
    "exponential_equations": Skill(
        skill_id="exponential_equations",
        topic="logarithms",
        display_name="Exponential equations",
        prerequisites=["logarithm_laws"],
        allowed_command_words=["solve", "find", "show"],
        typical_marks=3,
        common_misconceptions=["wrong_base_conversion"],
    ),
    "trigonometric_identities": Skill(
        skill_id="trigonometric_identities",
        topic="trigonometry",
        display_name="Trigonometric identities",
        prerequisites=[],
        allowed_command_words=["prove", "show", "simplify"],
        typical_marks=3,
        common_misconceptions=[],
    ),
    "trigonometric_equations": Skill(
        skill_id="trigonometric_equations",
        topic="trigonometry",
        display_name="Trigonometric equations",
        prerequisites=["trigonometric_identities"],
        allowed_command_words=["solve", "find"],
        typical_marks=4,
        common_misconceptions=[],
    ),
    "coordinate_line_equation": Skill(
        skill_id="coordinate_line_equation",
        topic="coordinate_geometry",
        display_name="Coordinate geometry: line equation",
        prerequisites=[],
        allowed_command_words=["find", "show", "write down"],
        typical_marks=3,
        common_misconceptions=[],
    ),
    "coordinate_circle_equation": Skill(
        skill_id="coordinate_circle_equation",
        topic="coordinate_geometry",
        display_name="Coordinate geometry: circle equation",
        prerequisites=["coordinate_line_equation"],
        allowed_command_words=["find", "show", "write down"],
        typical_marks=3,
        common_misconceptions=[],
    ),
    "binomial_expansion_positive_integer": Skill(
        skill_id="binomial_expansion_positive_integer",
        topic="binomial_expansion",
        display_name="Binomial expansion: positive integer n",
        prerequisites=[],
        allowed_command_words=["expand", "find", "write down", "show"],
        typical_marks=3,
        common_misconceptions=[
            "coefficient_index_error",
            "missing_binomial_coefficient",
            "sign_error",
            "power_pairing_error",
        ],
    ),
    "binomial_coefficient_term": Skill(
        skill_id="binomial_coefficient_term",
        topic="binomial_expansion",
        display_name="Binomial expansion: find specific term/coefficient",
        prerequisites=["binomial_expansion_positive_integer"],
        allowed_command_words=["find", "show", "write down"],
        typical_marks=3,
        common_misconceptions=[
            "coefficient_index_error",
            "missing_binomial_coefficient",
        ],
    ),
}


def get_skill(skill_id: str) -> Skill | None:
    return SKILLS.get(skill_id)


def get_skills_by_topic(topic: str) -> list[Skill]:
    return [s for s in SKILLS.values() if s.topic == topic]


def get_prerequisites(skill_id: str) -> list[Skill]:
    skill = SKILLS.get(skill_id)
    if not skill:
        return []
    return [SKILLS[p] for p in skill.prerequisites if p in SKILLS]


# Map topic names to their primary skills
TOPIC_PRIMARY_SKILLS: dict[str, str] = {
    "arithmetic_series": "arithmetic_series_sum",
    "geometric_series": "geometric_series_sum",
    "differentiation": "differentiation_stationary_points",
    "integration": "integration_area_under_curve",
    "logarithms": "logarithm_laws",
    "binomial_expansion": "binomial_expansion_positive_integer",
    "trigonometry": "trigonometric_equations",
    "coordinate_geometry": "coordinate_line_equation",
}
