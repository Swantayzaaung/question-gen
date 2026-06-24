"""Abstract base class for item templates."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
import uuid


class ItemTemplate(ABC):
    skill_id: str = ""
    topic: str = ""

    @abstractmethod
    def sample_parameters(self, steps: int = 2, cleanliness: str = "clean", focus: str = "single") -> dict:
        """Sample a valid parameter set for this template."""
        ...

    @abstractmethod
    def build_question(self, params: dict) -> "object":
        """Build a GeneratedItem from parameters (without LLM)."""
        ...

    @abstractmethod
    def solve(self, params: dict) -> dict:
        """Return {'final_answer': ..., 'solution_steps': [...], ...}."""
        ...

    def validate_params(self, params: dict) -> list[str]:
        """Return list of validation errors (empty = valid)."""
        return []

    def _new_item_id(self) -> str:
        return f"tmpl_{self.topic}_{uuid.uuid4().hex[:8]}"
