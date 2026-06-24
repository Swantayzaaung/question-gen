"""
Strict data schemas for all generated/API-facing objects.
Uses Pydantic v2 for validation.
"""

from __future__ import annotations
from dataclasses import field
from typing import Optional
from pydantic import BaseModel, field_validator
from datetime import datetime
import uuid


class Skill(BaseModel):
    skill_id: str
    topic: str
    display_name: str
    prerequisites: list[str] = []
    syllabus_unit: str = "P2"
    allowed_command_words: list[str] = []
    typical_marks: int = 3
    common_misconceptions: list[str] = []


class QuestionPart(BaseModel):
    part: str
    instruction: str
    marks: int


class VerifierResult(BaseModel):
    is_correct: bool
    checks: dict = {}
    errors: list[str] = []
    warnings: list[str] = []
    computed_answer: Optional[str] = None


class QualityResult(BaseModel):
    passed: bool
    score: float
    issues: list[str] = []
    near_duplicate_score: Optional[float] = None
    syllabus_ok: bool = True
    ambiguity_ok: bool = True
    difficulty_ok: bool = True


class GeneratedItem(BaseModel):
    item_id: str
    source: str  # "template" | "llm" | "hybrid"
    topic: str
    primary_skill: str
    secondary_skills: list[str] = []
    question_text: str
    parts: list[QuestionPart] = []
    canonical_solution: list[str] = []
    final_answer: str
    answer_type: str  # "integer" | "rational" | "irrational" | "expression" | etc.
    significant_steps: int
    marks: int
    parameters: dict = {}
    verifier_result: Optional[VerifierResult] = None
    quality_result: Optional[QualityResult] = None
    status: str = "draft"  # "draft" | "verified" | "rejected" | "needs_review" | "approved"
    worked_solution: list[str] = []  # alias for compatibility
    topics_used: list[str] = []
    solvability_score: Optional[float] = None
    solvability: Optional[str] = None
    params: dict = {}
    created_at: str = ""
    updated_at: str = ""

    def model_post_init(self, __context):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.worked_solution:
            self.worked_solution = self.canonical_solution
        if not self.topics_used:
            self.topics_used = [self.topic]
        if not self.params:
            self.params = {"steps": self.significant_steps}

    @field_validator("source")
    @classmethod
    def validate_source(cls, v):
        assert v in ("template", "llm", "hybrid"), f"Invalid source: {v}"
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid = ("draft", "verified", "rejected", "needs_review", "approved")
        assert v in valid, f"Invalid status: {v}"
        return v

    def to_api_dict(self) -> dict:
        """Return dict suitable for API JSON response."""
        d = self.model_dump()
        if self.verifier_result:
            d["verifier_result"] = self.verifier_result.model_dump()
        if self.quality_result:
            d["quality_result"] = self.quality_result.model_dump()
        return d


class LearnerAttempt(BaseModel):
    attempt_id: str
    user_id: str
    item_id: str
    submitted_answer: str
    is_correct: bool
    time_seconds: Optional[float] = None
    hints_used: int = 0
    timestamp: str = ""
    detected_misconceptions: list[str] = []

    def model_post_init(self, __context):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.attempt_id:
            self.attempt_id = str(uuid.uuid4())


class MasteryState(BaseModel):
    user_id: str
    skill_id: str
    mastery_probability: float = 0.25
    last_practiced: Optional[str] = None
    next_due: Optional[str] = None
    correct_streak: int = 0
    incorrect_streak: int = 0

    @field_validator("mastery_probability")
    @classmethod
    def clamp_mastery(cls, v):
        return max(0.0, min(1.0, v))
