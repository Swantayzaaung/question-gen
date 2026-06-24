"""Tests for the deterministic math verifier."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from verification.sympy_tools import equivalent, is_integer_answer, is_simple_fraction, is_surd_or_irrational
from verification.math_verifier import (
    _verify_arithmetic_series, _verify_geometric_series,
    _verify_differentiation, _verify_integration,
    _verify_binomial
)
from schemas import GeneratedItem, QuestionPart


def make_item(topic, primary_skill, params, final_answer):
    return GeneratedItem(
        item_id="test_item",
        source="template",
        topic=topic,
        primary_skill=primary_skill,
        question_text="Test question",
        parts=[QuestionPart(part="a", instruction="Find x", marks=3)],
        canonical_solution=["Step 1"],
        final_answer=final_answer,
        answer_type="integer",
        significant_steps=2,
        marks=3,
        parameters=params,
    )


class TestEquivalent:
    def test_same_integers(self):
        assert equivalent("5", "5")

    def test_different_integers(self):
        assert not equivalent("5", "6")

    def test_equivalent_expressions(self):
        assert equivalent("2*3", "6")
        assert equivalent("x^2 - 1", "(x-1)*(x+1)")

    def test_fraction_forms(self):
        assert equivalent("1/2", "0.5")

    def test_wrong_answers_rejected(self):
        assert not equivalent("3", "4")


class TestIsIntegerAnswer:
    def test_integer_string(self):
        assert is_integer_answer("6")
        assert is_integer_answer("-3")

    def test_non_integer(self):
        assert not is_integer_answer("1/3")
        assert not is_integer_answer("sqrt(2)")


class TestIsSimpleFraction:
    def test_simple_fractions(self):
        assert is_simple_fraction("1/2")
        assert is_simple_fraction("3/4")

    def test_large_denominator(self):
        assert not is_simple_fraction("1/13")


class TestIsSurdOrIrrational:
    def test_surd(self):
        assert is_surd_or_irrational("sqrt(2)")
        assert is_surd_or_irrational("2*sqrt(3)")

    def test_rational_not_irrational(self):
        assert not is_surd_or_irrational("6")
        assert not is_surd_or_irrational("1/3")


class TestArithmeticVerifier:
    def test_correct_sum(self):
        item = make_item("arithmetic_series", "arithmetic_series_sum",
                         {"first_term": 3, "common_difference": 2, "n": 10},
                         "120")
        result = _verify_arithmetic_series(item)
        assert result.is_correct

    def test_wrong_sum(self):
        item = make_item("arithmetic_series", "arithmetic_series_sum",
                         {"first_term": 3, "common_difference": 2, "n": 10},
                         "999")
        result = _verify_arithmetic_series(item)
        assert not result.is_correct

    def test_nth_term_match(self):
        item = make_item("arithmetic_series", "arithmetic_series_sum",
                         {"first_term": 3, "common_difference": 2, "n": 10},
                         "21")
        result = _verify_arithmetic_series(item)
        assert result.is_correct  # matches nth term


class TestGeometricVerifier:
    def test_correct_sum(self):
        # S_5 = 2*(1 - (1/2)^5) / (1 - 1/2) = 2*(31/32)/(1/2) = 31/8
        item = make_item("geometric_series", "geometric_series_sum",
                         {"first_term": 2, "common_ratio": "1/2", "n": 5, "task": "sum"},
                         "31/8")
        result = _verify_geometric_series(item)
        assert result.is_correct

    def test_wrong_sum(self):
        item = make_item("geometric_series", "geometric_series_sum",
                         {"first_term": 2, "common_ratio": "1/2", "n": 5, "task": "sum"},
                         "10")
        result = _verify_geometric_series(item)
        assert not result.is_correct

    def test_sum_to_infinity(self):
        # S_inf = 4 / (1 - 1/2) = 8
        item = make_item("geometric_series", "geometric_series_convergence",
                         {"first_term": 4, "common_ratio": "1/2", "n": None, "task": "sum_to_infinity"},
                         "8")
        result = _verify_geometric_series(item)
        assert result.is_correct

    def test_divergent_series_fails(self):
        item = make_item("geometric_series", "geometric_series_sum",
                         {"first_term": 2, "common_ratio": "2", "n": None, "task": "sum_to_infinity"},
                         "???")
        result = _verify_geometric_series(item)
        assert not result.is_correct


class TestDifferentiationVerifier:
    def test_stationary_points(self):
        # y = x^3 - 3x^2 - 9x + 5, stationary at x=-1 (y=10) and x=3 (y=-22)
        item = make_item("differentiation", "differentiation_stationary_points",
                         {"expression": "x**3 - 3*x**2 - 9*x + 5", "task": "stationary_points"},
                         "10")
        result = _verify_differentiation(item)
        assert result.is_correct  # y=10 at x=-1

    def test_stationary_point_computed(self):
        item = make_item("differentiation", "differentiation_stationary_points",
                         {"expression": "x**3 - 3*x**2 - 9*x + 5", "task": "stationary_points"},
                         "fake_answer")
        result = _verify_differentiation(item)
        # Even if answer doesn't match, stationary points are computed
        assert result.checks.get("stationary_points_xy") is not None


class TestIntegrationVerifier:
    def test_correct_area(self):
        # integral of x^2 - x - 2 from -1 to 2 = ... let's use sympy to check
        from fractions import Fraction
        # F(x) = x^3/3 - x^2/2 - 2x
        # F(2) = 8/3 - 2 - 4 = 8/3 - 6 = -10/3
        # F(-1) = -1/3 - 1/2 + 2 = -1/3 - 1/2 + 2 = 7/6
        # area = |F(2) - F(-1)| = |-10/3 - 7/6| = |-20/6 - 7/6| = 27/6 = 9/2
        item = make_item("integration", "integration_area_under_curve",
                         {"expression": "x**2 - x - 2", "lower_bound": -1, "upper_bound": 2, "task": "area"},
                         "9/2")
        result = _verify_integration(item)
        assert result.is_correct


class TestBinomialVerifier:
    def test_coefficient(self):
        # C(4,2)*1^2*2^2 = 6*4 = 24
        item = make_item("binomial_expansion", "binomial_expansion_positive_integer",
                         {"n": 4, "a": 1, "b": 2, "term_r": 2, "task": "coefficient"},
                         "24")
        result = _verify_binomial(item)
        assert result.is_correct

    def test_wrong_coefficient(self):
        item = make_item("binomial_expansion", "binomial_expansion_positive_integer",
                         {"n": 4, "a": 1, "b": 2, "term_r": 2, "task": "coefficient"},
                         "99")
        result = _verify_binomial(item)
        assert not result.is_correct
