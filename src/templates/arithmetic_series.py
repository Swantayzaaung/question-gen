"""Arithmetic series template."""

from __future__ import annotations
import random
from fractions import Fraction
from .base import ItemTemplate


class ArithmeticSeriesTemplate(ItemTemplate):
    skill_id = "arithmetic_series_sum"
    topic = "arithmetic_series"

    def sample_parameters(self, steps: int = 2, cleanliness: str = "clean", focus: str = "single") -> dict:
        """
        Generate a, d, n such that S_n is a clean integer/fraction.
        steps=1: given a, d, n directly → find S_n
        steps=2: given a, d, find n first then S_n
        steps=3: given S_n equation, solve for unknowns
        """
        for _ in range(50):
            a = random.randint(1, 20)
            if cleanliness == "clean":
                d = random.choice([1, 2, 3, 4, 5, -1, -2, -3])
            else:
                d = random.randint(-5, 10)
                if d == 0:
                    d = 1

            if steps == 1:
                n = random.randint(5, 20)
                task = "find_sum"
            elif steps == 2:
                # Given a, l (last term), find S
                n = random.randint(5, 20)
                task = "given_last_term"
            else:
                n = random.randint(5, 25)
                task = "find_sum"

            S = Fraction(n, 2) * (2 * a + (n - 1) * d)
            Tn = a + (n - 1) * d

            if Tn <= 0 and d < 0 and n > 5:
                continue  # might cause negative terms oddly

            if cleanliness == "clean" and S.denominator != 1:
                continue

            return {
                "first_term": a,
                "common_difference": d,
                "n": n,
                "task": task,
                "computed_sum": str(S),
                "computed_nth_term": str(Tn),
            }
        # Fallback safe params
        return {"first_term": 3, "common_difference": 2, "n": 10, "task": "find_sum",
                "computed_sum": "120", "computed_nth_term": "21"}

    def solve(self, params: dict) -> dict:
        a = params["first_term"]
        d = params["common_difference"]
        n = params["n"]
        S = Fraction(n, 2) * (2 * a + (n - 1) * d)
        Tn = a + (n - 1) * d

        steps = [
            f"The arithmetic series has first term $a = {a}$ and common difference $d = {d}$.",
            f"The $n$th term is $u_n = a + (n-1)d = {a} + (n-1)({d})$.",
            f"For $n = {n}$: $u_{{{n}}} = {Tn}$.",
            f"Sum of {n} terms: $S_{{{n}}} = \\frac{{{n}}}{{2}}(2 \\times {a} + ({n}-1) \\times {d}) = \\frac{{{n}}}{{2}} \\times {2*a+(n-1)*d} = {S}$.",
        ]

        return {
            "final_answer": str(int(S)) if S.denominator == 1 else str(float(S)),
            "solution_steps": steps,
            "nth_term": str(Tn),
        }

    def build_question(self, params: dict):
        from schemas import GeneratedItem, QuestionPart
        sol = self.solve(params)
        a = params["first_term"]
        d = params["common_difference"]
        n = params["n"]

        question_text = (
            f"An arithmetic series has first term $a = {a}$ and common difference $d = {d}$.\n\n"
        )
        parts = [
            QuestionPart(part="a", instruction=f"Find the {n}th term of the series.", marks=2),
            QuestionPart(part="b", instruction=f"Find the sum of the first {n} terms.", marks=3),
        ]
        total_marks = sum(p.marks for p in parts)

        return GeneratedItem(
            item_id=self._new_item_id(),
            source="template",
            topic=self.topic,
            primary_skill=self.skill_id,
            secondary_skills=["arithmetic_series_nth_term"],
            question_text=question_text,
            parts=parts,
            canonical_solution=sol["solution_steps"],
            final_answer=sol["final_answer"],
            answer_type="integer" if "." not in sol["final_answer"] else "rational",
            significant_steps=2,
            marks=total_marks,
            parameters=params,
        )

    def validate_params(self, params: dict) -> list[str]:
        errors = []
        n = params.get("n")
        if not isinstance(n, int) or n <= 0:
            errors.append("n must be a positive integer")
        d = params.get("common_difference")
        if d == 0:
            errors.append("common_difference should not be 0 for arithmetic series")
        return errors
