"""Tests for the adaptive scheduler and mastery model."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from adaptation.mastery import bkt_update, P_INIT


class TestBKTUpdate:
    def test_correct_increases_mastery(self):
        p = bkt_update(P_INIT, is_correct=True)
        assert p > P_INIT

    def test_incorrect_decreases_mastery(self):
        p_high = 0.8
        p = bkt_update(p_high, is_correct=False)
        assert p < p_high

    def test_hints_reduce_evidence(self):
        p_no_hint = bkt_update(P_INIT, is_correct=True, hints_used=0)
        p_with_hint = bkt_update(P_INIT, is_correct=True, hints_used=3)
        assert p_no_hint > p_with_hint

    def test_mastery_stays_in_0_1(self):
        p = P_INIT
        for _ in range(20):
            p = bkt_update(p, is_correct=True)
        assert 0 <= p <= 1

        p = 0.9
        for _ in range(10):
            p = bkt_update(p, is_correct=False)
        assert 0 <= p <= 1

    def test_wrong_answer_schedules_sooner(self):
        from adaptation.mastery import _next_due
        from datetime import datetime
        high_p = 0.8
        low_p = 0.8
        next_correct = datetime.fromisoformat(_next_due(high_p, is_correct=True))
        next_wrong   = datetime.fromisoformat(_next_due(low_p,  is_correct=False))
        assert next_wrong < next_correct

    def test_high_mastery_schedules_later(self):
        from adaptation.mastery import _next_due
        from datetime import datetime
        next_low  = datetime.fromisoformat(_next_due(0.3, is_correct=True))
        next_high = datetime.fromisoformat(_next_due(0.9, is_correct=True))
        assert next_high > next_low
