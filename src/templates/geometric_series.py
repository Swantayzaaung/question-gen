"""Geometric series template."""

from __future__ import annotations
import random
from fractions import Fraction
from .base import ItemTemplate


class GeometricSeriesTemplate(ItemTemplate):
    skill_id = "geometric_series_sum"
    topic = "geometric_series"

    def sample_parameters(self, steps: int = 2, cleanliness: str = "clean", focus: str = "single") -> dict:
        for _ in range(50):
            a = random.randint(1, 10)

            if cleanliness == "clean":
                r_choices = [Fraction(1, 2), Fraction(1, 3), Fraction(2, 3), Fraction(3, 4), 2, 3]
            else:
                r_choices = [Fraction(1, 2), Fraction(2, 3), Fraction(3, 4), Fraction(1, 4), 2, 3, -Fraction(1, 2)]
            r = random.choice(r_choices)

            if steps >= 2 and abs(r) < 1:
                task = random.choice(["sum", "sum_to_infinity"])
            else:
                task = "sum"

            n = random.randint(4, 10)

            if task == "sum_to_infinity":
                if abs(r) >= 1:
                    continue
                S_inf = Fraction(a) / (1 - r)
                if cleanliness == "clean" and S_inf.denominator > 12:
                    continue
                return {
                    "first_term": a,
                    "common_ratio": str(r),
                    "common_ratio_val": float(r),
                    "n": None,
                    "task": "sum_to_infinity",
                    "computed_answer": str(S_inf),
                }
            else:
                S = Fraction(a) * (1 - r ** n) / (1 - r)
                if cleanliness == "clean" and S.denominator > 1:
                    continue
                if abs(float(S)) > 100000:
                    continue
                return {
                    "first_term": a,
                    "common_ratio": str(r),
                    "common_ratio_val": float(r),
                    "n": n,
                    "task": "sum",
                    "computed_answer": str(S),
                }

        return {
            "first_term": 4,
            "common_ratio": "1/2",
            "common_ratio_val": 0.5,
            "n": 5,
            "task": "sum",
            "computed_answer": "31/2",
        }

    def solve(self, params: dict) -> dict:
        a = params["first_term"]
        r_str = params["common_ratio"]
        r = Fraction(r_str) if "/" in str(r_str) else Fraction(r_str).limit_denominator(100)
        task = params["task"]

        if task == "sum_to_infinity":
            S = Fraction(a) / (1 - r)
            steps = [
                f"Geometric series: first term $a = {a}$, common ratio $r = {r_str}$.",
                f"Since $|r| = {abs(float(r)):.3f} < 1$, the series converges.",
                f"Sum to infinity: $S_\\infty = \\frac{{a}}{{1-r}} = \\frac{{{a}}}{{1-({r_str})}} = {S}$.",
            ]
            fa = str(int(S)) if S.denominator == 1 else f"{S.numerator}/{S.denominator}"
        else:
            n = params["n"]
            S = Fraction(a) * (1 - r ** n) / (1 - r)
            steps = [
                f"Geometric series: first term $a = {a}$, common ratio $r = {r_str}$.",
                f"Sum formula: $S_n = \\frac{{a(1-r^n)}}{{1-r}}$.",
                f"$S_{{{n}}} = \\frac{{{a}(1-({r_str})^{{{n}}})}}{{1-({r_str})}} = {S}$.",
            ]
            fa = str(int(S)) if S.denominator == 1 else f"{S.numerator}/{S.denominator}"

        return {"final_answer": fa, "solution_steps": steps}

    def build_question(self, params: dict):
        from schemas import GeneratedItem, QuestionPart
        sol = self.solve(params)
        a = params["first_term"]
        r_str = params["common_ratio"]
        task = params["task"]

        if task == "sum_to_infinity":
            question_text = (
                f"A geometric series has first term $a = {a}$ and common ratio $r = {r_str}$.\n\n"
            )
            parts = [
                QuestionPart(part="a", instruction="Show that the series converges.", marks=1),
                QuestionPart(part="b", instruction="Find the sum to infinity of the series.", marks=3),
            ]
        else:
            n = params["n"]
            question_text = (
                f"A geometric series has first term $a = {a}$ and common ratio $r = {r_str}$.\n\n"
            )
            parts = [
                QuestionPart(part="a", instruction=f"Find the sum of the first {n} terms.", marks=3),
            ]

        return GeneratedItem(
            item_id=self._new_item_id(),
            source="template",
            topic=self.topic,
            primary_skill=self.skill_id,
            secondary_skills=["geometric_series_convergence"] if task == "sum_to_infinity" else [],
            question_text=question_text,
            parts=parts,
            canonical_solution=sol["solution_steps"],
            final_answer=sol["final_answer"],
            answer_type="rational" if "/" in sol["final_answer"] else "integer",
            significant_steps=2 if task == "sum_to_infinity" else 2,
            marks=sum(p.marks for p in parts),
            parameters=params,
        )

    def validate_params(self, params: dict) -> list[str]:
        errors = []
        r_str = params.get("common_ratio")
        if r_str is None:
            errors.append("common_ratio required")
            return errors
        try:
            r = Fraction(str(r_str))
        except Exception:
            errors.append(f"Cannot parse common_ratio: {r_str}")
            return errors
        if r == 1:
            errors.append("common_ratio cannot be 1")
        if params.get("task") == "sum_to_infinity" and abs(r) >= 1:
            errors.append(f"|r| must be < 1 for sum to infinity, got {r}")
        return errors
