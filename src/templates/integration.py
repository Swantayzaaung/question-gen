"""Integration template — area under a polynomial curve."""

from __future__ import annotations
import random
from fractions import Fraction
from .base import ItemTemplate


class IntegrationTemplate(ItemTemplate):
    skill_id = "integration_area_under_curve"
    topic = "integration"

    def sample_parameters(self, steps: int = 2, cleanliness: str = "clean", focus: str = "single") -> dict:
        for _ in range(50):
            # Generate polynomial with roots at a and b (so curve crosses x-axis)
            root1 = random.randint(-3, 0)
            root2 = random.randint(1, 5)
            # y = (x - root1)(x - root2) = x^2 - (r1+r2)x + r1*r2
            r1r2_sum = root1 + root2
            r1r2_prod = root1 * root2
            lower = root1
            upper = root2

            # Integrate x^2 - (r1+r2)x + r1r2 from lower to upper
            def integral_poly(x):
                return Fraction(x**3, 3) - Fraction(r1r2_sum * x**2, 2) + Fraction(r1r2_prod * x)

            area = integral_poly(upper) - integral_poly(lower)
            if area < 0:
                area = -area  # area is always positive

            if cleanliness == "clean" and area.denominator > 6:
                continue

            expr_b_str = f"-{r1r2_sum}" if r1r2_sum > 0 else f"+{-r1r2_sum}" if r1r2_sum < 0 else ""
            expr_c_str = f"+{r1r2_prod}" if r1r2_prod > 0 else str(r1r2_prod) if r1r2_prod < 0 else ""
            expression = f"x^2{expr_b_str}x{expr_c_str}"

            return {
                "expression": expression,
                "lower_bound": lower,
                "upper_bound": upper,
                "task": "area",
                "computed_area": str(area),
                "roots": [root1, root2],
            }

        return {
            "expression": "x^2 - x - 2",
            "lower_bound": -1,
            "upper_bound": 2,
            "task": "area",
            "computed_area": "9/2",
            "roots": [-1, 2],
        }

    def solve(self, params: dict) -> dict:
        expr = params["expression"]
        lower = params["lower_bound"]
        upper = params["upper_bound"]
        area = params["computed_area"]

        steps = [
            f"Find $\\int_{{{lower}}}^{{{upper}}} {expr.replace('*', '')} \\, dx$.",
            f"Integrate term by term using $\\int x^n dx = \\frac{{x^{{n+1}}}}{{n+1}}$.",
            f"Evaluate $\\left[ F(x) \\right]_{{{lower}}}^{{{upper}}} = F({upper}) - F({lower})$.",
            f"Area $= {area}$ square units.",
        ]
        fa_frac = Fraction(area)
        if fa_frac.denominator == 1:
            fa = str(int(fa_frac))
        else:
            fa = f"\\frac{{{fa_frac.numerator}}}{{{fa_frac.denominator}}}"

        return {"final_answer": str(area), "solution_steps": steps, "latex_answer": fa}

    def build_question(self, params: dict):
        from schemas import GeneratedItem, QuestionPart
        sol = self.solve(params)
        expr = params["expression"].replace("*", "")
        lower = params["lower_bound"]
        upper = params["upper_bound"]

        question_text = (
            f"The curve $C$ has equation $y = {expr}$.\n\n"
            f"The region $R$ is bounded by the curve $C$ and the $x$-axis, "
            f"between $x = {lower}$ and $x = {upper}$.\n\n"
        )
        parts = [
            QuestionPart(part="a", instruction="Find $\\int ({expr}) \\, dx$.".replace("{expr}", expr), marks=2),
            QuestionPart(part="b", instruction=f"Find the area of the region $R$.", marks=3),
        ]

        return GeneratedItem(
            item_id=self._new_item_id(),
            source="template",
            topic=self.topic,
            primary_skill=self.skill_id,
            secondary_skills=["integration_power_rule"],
            question_text=question_text,
            parts=parts,
            canonical_solution=sol["solution_steps"],
            final_answer=sol["final_answer"],
            answer_type="rational",
            significant_steps=2,
            marks=sum(p.marks for p in parts),
            parameters=params,
        )

    def validate_params(self, params: dict) -> list[str]:
        errors = []
        if params.get("lower_bound") is None or params.get("upper_bound") is None:
            errors.append("lower_bound and upper_bound required")
        elif params["lower_bound"] >= params["upper_bound"]:
            errors.append("lower_bound must be < upper_bound")
        if not params.get("expression"):
            errors.append("expression required")
        return errors
