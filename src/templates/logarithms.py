"""Logarithm template — solve log equations."""

from __future__ import annotations
import random
import math
from .base import ItemTemplate


class LogarithmsTemplate(ItemTemplate):
    skill_id = "logarithm_laws"
    topic = "logarithms"

    def sample_parameters(self, steps: int = 2, cleanliness: str = "clean", focus: str = "single") -> dict:
        """
        Generate log equations of the form:
        - log(x) + log(a) = log(b)  → x = b/a
        - log_b(x) = c              → x = b^c
        - a * log(x) = log(k)       → x = k^(1/a)
        """
        for _ in range(50):
            if steps == 1:
                # Simple: log_b(x) = c
                b = random.choice([2, 3, 5, 10])
                c = random.randint(1, 4)
                x = b ** c
                equation = f"\\log_{{{b}}} x = {c}"
                return {
                    "equation": f"log({x}) / log({b}) - {c}",  # for sympy: log(x)/log(b) = c
                    "equation_display": equation,
                    "task": "solve",
                    "answer": str(x),
                    "answer_type": "integer",
                }
            elif steps == 2:
                # log(x) + log(a) = log(b), x = b/a
                a = random.randint(2, 6)
                b = a * random.randint(2, 8)
                x = b // a
                if b % a != 0:
                    continue
                equation_display = f"\\ln x + \\ln {a} = \\ln {b}"
                return {
                    "equation": f"log(x) + log({a}) - log({b})",
                    "equation_display": equation_display,
                    "task": "solve",
                    "answer": str(x),
                    "answer_type": "integer",
                }
            else:
                # 2log(x) = log(k), x = sqrt(k)
                k_vals = [4, 9, 16, 25, 36, 49, 64, 100]
                k = random.choice(k_vals)
                x = int(math.isqrt(k))
                if x * x != k:
                    continue
                equation_display = f"2\\ln x = \\ln {k}"
                return {
                    "equation": f"2*log(x) - log({k})",
                    "equation_display": equation_display,
                    "task": "solve",
                    "answer": str(x),
                    "answer_type": "integer",
                }

        return {
            "equation": "log(x) + log(3) - log(12)",
            "equation_display": "\\ln x + \\ln 3 = \\ln 12",
            "task": "solve",
            "answer": "4",
            "answer_type": "integer",
        }

    def solve(self, params: dict) -> dict:
        eq_display = params.get("equation_display", params["equation"])
        answer = params["answer"]

        steps = [
            f"Equation: ${eq_display}$",
            "Apply logarithm laws to combine terms.",
            f"Solve for $x$: $x = {answer}$.",
            f"Check: $x = {answer} > 0$ ✓ (domain valid).",
        ]
        return {"final_answer": answer, "solution_steps": steps}

    def build_question(self, params: dict):
        from schemas import GeneratedItem, QuestionPart
        sol = self.solve(params)
        eq_display = params.get("equation_display", params["equation"])

        question_text = f"Solve the equation\n$$\n{eq_display}\n$$\n"
        parts = [
            QuestionPart(part="a", instruction="Solve for $x$, giving your answer exactly.", marks=3),
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
            answer_type=params.get("answer_type", "integer"),
            significant_steps=2,
            marks=sum(p.marks for p in parts),
            parameters=params,
        )

    def validate_params(self, params: dict) -> list[str]:
        errors = []
        try:
            ans = float(params.get("answer", 0))
            if ans <= 0:
                errors.append("Log solution must be positive")
        except Exception:
            errors.append("answer must be numeric")
        return errors
