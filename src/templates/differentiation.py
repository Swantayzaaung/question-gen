"""Differentiation template — stationary points of polynomials."""

from __future__ import annotations
import random
from .base import ItemTemplate


class DifferentiationTemplate(ItemTemplate):
    skill_id = "differentiation_stationary_points"
    topic = "differentiation"

    def sample_parameters(self, steps: int = 2, cleanliness: str = "clean", focus: str = "single") -> dict:
        """
        Generate a cubic y = x^3 + bx^2 + cx + d with rational stationary points.
        """
        for _ in range(100):
            # Construct cubic with known stationary points at x = p and x = q
            p = random.randint(-4, 4)
            q = random.randint(-4, 4)
            if p == q:
                continue
            # dy/dx = 3(x - p)(x - q) = 3x^2 - 3(p+q)x + 3pq
            # y = x^3 - 3/2*(p+q)x^2 + 3pq*x + d
            from fractions import Fraction
            b = Fraction(-3 * (p + q), 2)
            c = Fraction(3 * p * q)
            d = random.randint(-10, 10)

            if cleanliness == "clean" and b.denominator != 1:
                continue

            # Compute y at stationary points
            def y_at(x):
                return Fraction(x) ** 3 + b * Fraction(x) ** 2 + c * Fraction(x) + d

            yp = y_at(p)
            yq = y_at(q)

            if cleanliness == "clean" and (yp.denominator != 1 or yq.denominator != 1):
                continue

            # Build expression string
            # y = x^3 + bx^2 + cx + d
            terms = ["x^3"]
            if b != 0:
                if b == 1:
                    terms.append("x^2")
                elif b == -1:
                    terms.append("-x^2")
                elif b > 0:
                    terms.append(f"{b}x^2")
                else:
                    terms.append(f"{b}x^2")
            if c != 0:
                if c == 1:
                    terms.append("x")
                elif c == -1:
                    terms.append("-x")
                elif c > 0:
                    terms.append(f"{c}x")
                else:
                    terms.append(f"{c}x")
            if d != 0:
                terms.append(str(d))

            expr_str = " + ".join(terms).replace("+ -", "- ")

            return {
                "expression": expr_str,
                "task": "stationary_points",
                "stat_x_values": [p, q],
                "stat_y_values": [str(yp), str(yq)],
                "b": str(b), "c": str(c), "d": d,
            }

        return {
            "expression": "x^3 - 3*x^2 - 9*x + 5",
            "task": "stationary_points",
            "stat_x_values": [-1, 3],
            "stat_y_values": ["10", "-22"],
            "b": "-3", "c": "-9", "d": 5,
        }

    def solve(self, params: dict) -> dict:
        expr_str = params["expression"]
        xs = params["stat_x_values"]
        ys = params["stat_y_values"]

        # Build derivative from b, c
        from fractions import Fraction
        b = Fraction(params["b"])
        c = Fraction(params["c"])
        # dy/dx = 3x^2 + 2bx + c
        deriv_terms = ["3x^2"]
        if 2 * b != 0:
            if 2 * b == 1:
                deriv_terms.append("x")
            else:
                deriv_terms.append(f"{2*b}x")
        if c != 0:
            deriv_terms.append(str(c))
        deriv_str = " + ".join(deriv_terms).replace("+ -", "- ")

        steps = [
            f"Given $y = {expr_str.replace('*', '')}$.",
            f"Differentiate: $\\frac{{dy}}{{dx}} = {deriv_str}$.",
            f"Set $\\frac{{dy}}{{dx}} = 0$: ${deriv_str} = 0$.",
        ]
        for xv, yv in zip(xs, ys):
            steps.append(f"$x = {xv}$, giving $y = {yv}$. Stationary point: $({xv}, {yv})$.")

        # Classification
        if len(xs) == 2 and xs[0] < xs[1]:
            steps.append(
                f"$\\frac{{d^2y}}{{dx^2}} = 6x + {2*b}$. "
                f"At $x={xs[0]}$: value $= {6*xs[0] + float(2*b):.0f}$ "
                f"({'minimum' if 6*xs[0] + float(2*b) > 0 else 'maximum'}). "
                f"At $x={xs[1]}$: value $= {6*xs[1] + float(2*b):.0f}$ "
                f"({'minimum' if 6*xs[1] + float(2*b) > 0 else 'maximum'})."
            )

        final = f"({xs[0]}, {ys[0]}) and ({xs[1]}, {ys[1]})" if len(xs) == 2 else f"({xs[0]}, {ys[0]})"
        return {"final_answer": final, "solution_steps": steps}

    def build_question(self, params: dict):
        from schemas import GeneratedItem, QuestionPart
        sol = self.solve(params)
        expr = params["expression"].replace("*", "")

        question_text = f"A curve has equation $y = {expr}$.\n\n"
        parts = [
            QuestionPart(part="a", instruction="Find $\\frac{dy}{dx}$.", marks=2),
            QuestionPart(part="b", instruction="Find the coordinates of the stationary points of the curve.", marks=4),
            QuestionPart(part="c", instruction="Determine the nature of each stationary point.", marks=2),
        ]

        return GeneratedItem(
            item_id=self._new_item_id(),
            source="template",
            topic=self.topic,
            primary_skill=self.skill_id,
            secondary_skills=["differentiation_power_rule"],
            question_text=question_text,
            parts=parts,
            canonical_solution=sol["solution_steps"],
            final_answer=sol["final_answer"],
            answer_type="coordinates",
            significant_steps=3,
            marks=sum(p.marks for p in parts),
            parameters=params,
        )

    def validate_params(self, params: dict) -> list[str]:
        errors = []
        if not params.get("expression"):
            errors.append("expression required")
        xs = params.get("stat_x_values", [])
        if not xs:
            errors.append("stat_x_values required")
        return errors
