"""Binomial expansion template."""

from __future__ import annotations
import random
import math
from .base import ItemTemplate


def _binomial_coeff(n: int, r: int) -> int:
    return math.comb(n, r)


class BinomialExpansionTemplate(ItemTemplate):
    skill_id = "binomial_expansion_positive_integer"
    topic = "binomial_expansion"

    def sample_parameters(self, steps: int = 2, cleanliness: str = "clean", focus: str = "single") -> dict:
        for _ in range(30):
            n = random.randint(3, 6)
            a = random.randint(1, 3)
            b = random.choice([-3, -2, -1, 1, 2, 3])
            task = "coefficient" if steps <= 2 else "expand"
            r = random.randint(1, n - 1)

            coeff = _binomial_coeff(n, r) * (a ** (n - r)) * (b ** r)
            if abs(coeff) > 5000:
                continue

            return {
                "n": n,
                "a": a,
                "b": b,
                "term_r": r,
                "task": task,
                "computed_coefficient": str(coeff),
            }

        return {"n": 4, "a": 1, "b": 2, "term_r": 2, "task": "coefficient", "computed_coefficient": "24"}

    def solve(self, params: dict) -> dict:
        n = params["n"]
        a = params["a"]
        b = params["b"]
        r = params["term_r"]
        coeff = _binomial_coeff(n, r) * (a ** (n - r)) * (b ** r)

        b_str = f"+{b}x" if b > 0 else f"{b}x"
        expr = f"({a}{b_str})^{{{n}}}"

        steps = [
            f"Expand $({a}{b_str})^{{{n}}}$ using the binomial theorem.",
            f"General term: $\\binom{{{n}}}{{r}} {a}^{{{n}-r}} ({b}x)^r$.",
            f"For the $x^{{{r}}}$ term: $r = {r}$.",
            f"$\\binom{{{n}}}{{{r}}} \\times {a}^{{{n-r}}} \\times {b}^{{{r}}} = {_binomial_coeff(n,r)} \\times {a**(n-r)} \\times {b**r} = {coeff}$.",
        ]
        return {"final_answer": str(coeff), "solution_steps": steps}

    def build_question(self, params: dict):
        from schemas import GeneratedItem, QuestionPart
        sol = self.solve(params)
        n = params["n"]
        a = params["a"]
        b = params["b"]
        r = params["term_r"]
        b_str = f"+{b}x" if b > 0 else f"{b}x"

        question_text = (
            f"In the binomial expansion of $({a}{b_str})^{{{n}}}$,\n"
            f"find the coefficient of $x^{{{r}}}$.\n"
        )
        parts = [
            QuestionPart(part="a", instruction=f"Find the coefficient of $x^{{{r}}}$ in the expansion.", marks=3),
        ]

        return GeneratedItem(
            item_id=self._new_item_id(),
            source="template",
            topic=self.topic,
            primary_skill=self.skill_id,
            secondary_skills=[],
            question_text=question_text,
            parts=parts,
            canonical_solution=sol["solution_steps"],
            final_answer=sol["final_answer"],
            answer_type="integer",
            significant_steps=2,
            marks=3,
            parameters=params,
        )

    def validate_params(self, params: dict) -> list[str]:
        errors = []
        n = params.get("n")
        r = params.get("term_r")
        if not isinstance(n, int) or n < 1:
            errors.append("n must be a positive integer")
        if r is not None and (not isinstance(r, int) or r < 0 or r > n):
            errors.append(f"term_r must be between 0 and n={n}")
        return errors
