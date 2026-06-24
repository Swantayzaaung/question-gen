"""Tests for template-based item generation."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from templates import (
    ArithmeticSeriesTemplate, GeometricSeriesTemplate,
    DifferentiationTemplate, IntegrationTemplate,
    LogarithmsTemplate, BinomialExpansionTemplate, get_template
)
from schemas import GeneratedItem
from fractions import Fraction


class TestArithmeticSeries:
    def test_params_valid(self):
        t = ArithmeticSeriesTemplate()
        p = t.sample_parameters(steps=2, cleanliness="clean")
        assert p["n"] > 0
        assert isinstance(p["n"], int)
        assert p["common_difference"] != 0

    def test_solve_correct(self):
        t = ArithmeticSeriesTemplate()
        p = {"first_term": 3, "common_difference": 2, "n": 10, "task": "find_sum",
             "computed_sum": "120", "computed_nth_term": "21"}
        sol = t.solve(p)
        assert sol["final_answer"] == "120"

    def test_build_question(self):
        t = ArithmeticSeriesTemplate()
        p = t.sample_parameters()
        item = t.build_question(p)
        assert isinstance(item, GeneratedItem)
        assert item.topic == "arithmetic_series"
        assert item.final_answer

    def test_cleanliness_clean_gives_integer(self):
        t = ArithmeticSeriesTemplate()
        for _ in range(10):
            p = t.sample_parameters(cleanliness="clean")
            sol = t.solve(p)
            # Should be an integer string
            assert "." not in sol["final_answer"] or sol["final_answer"].endswith(".0")

    def test_validate_params_bad_n(self):
        t = ArithmeticSeriesTemplate()
        errors = t.validate_params({"first_term": 1, "common_difference": 2, "n": -1})
        assert any("positive" in e for e in errors)


class TestGeometricSeries:
    def test_params_valid(self):
        t = GeometricSeriesTemplate()
        p = t.sample_parameters(steps=2, cleanliness="clean")
        assert p["common_ratio"]
        r = Fraction(p["common_ratio"])
        assert r != 1

    def test_sum_to_infinity_requires_abs_r_less_1(self):
        t = GeometricSeriesTemplate()
        for _ in range(20):
            p = t.sample_parameters(steps=2)
            if p["task"] == "sum_to_infinity":
                r = abs(float(Fraction(p["common_ratio"])))
                assert r < 1

    def test_build_question(self):
        t = GeometricSeriesTemplate()
        p = t.sample_parameters()
        item = t.build_question(p)
        assert isinstance(item, GeneratedItem)
        assert item.final_answer

    def test_validate_bad_ratio(self):
        t = GeometricSeriesTemplate()
        errors = t.validate_params({"common_ratio": "1", "task": "sum", "n": 5})
        assert errors  # r=1 invalid

    def test_validate_divergent_sum_to_inf(self):
        t = GeometricSeriesTemplate()
        errors = t.validate_params({"common_ratio": "2", "task": "sum_to_infinity", "n": None})
        assert errors


class TestDifferentiation:
    def test_params_valid(self):
        t = DifferentiationTemplate()
        p = t.sample_parameters()
        assert "expression" in p
        assert "stat_x_values" in p
        assert len(p["stat_x_values"]) >= 1

    def test_build_question(self):
        t = DifferentiationTemplate()
        p = t.sample_parameters()
        item = t.build_question(p)
        assert item.topic == "differentiation"
        assert len(item.parts) == 3

    def test_known_params(self):
        t = DifferentiationTemplate()
        p = {
            "expression": "x^3 - 3*x^2 - 9*x + 5",
            "task": "stationary_points",
            "stat_x_values": [-1, 3],
            "stat_y_values": ["10", "-22"],
            "b": "-3", "c": "-9", "d": 5,
        }
        item = t.build_question(p)
        assert "10" in item.final_answer or "-22" in item.final_answer


class TestIntegration:
    def test_params_valid(self):
        t = IntegrationTemplate()
        p = t.sample_parameters()
        assert p["lower_bound"] < p["upper_bound"]
        assert p["expression"]

    def test_area_positive(self):
        t = IntegrationTemplate()
        for _ in range(10):
            p = t.sample_parameters()
            area = Fraction(p["computed_area"])
            assert area > 0

    def test_build_question(self):
        t = IntegrationTemplate()
        p = t.sample_parameters()
        item = t.build_question(p)
        assert item.topic == "integration"
        assert item.final_answer

    def test_validate_bad_bounds(self):
        t = IntegrationTemplate()
        errors = t.validate_params({"expression": "x", "lower_bound": 5, "upper_bound": 2})
        assert errors


class TestLogarithms:
    def test_params_valid(self):
        t = LogarithmsTemplate()
        p = t.sample_parameters()
        assert float(p["answer"]) > 0

    def test_build_question(self):
        t = LogarithmsTemplate()
        p = t.sample_parameters()
        item = t.build_question(p)
        assert item.topic == "logarithms"
        assert item.final_answer

    def test_validate_negative_answer(self):
        t = LogarithmsTemplate()
        errors = t.validate_params({"equation": "log(x)", "answer": "-3"})
        assert errors


class TestBinomial:
    def test_params_valid(self):
        t = BinomialExpansionTemplate()
        p = t.sample_parameters()
        n, r = p["n"], p["term_r"]
        assert 0 <= r <= n

    def test_coefficient_correct(self):
        import math
        t = BinomialExpansionTemplate()
        p = {"n": 4, "a": 1, "b": 2, "term_r": 2, "task": "coefficient"}
        sol = t.solve(p)
        # C(4,2)*1^2*2^2 = 6*4 = 24
        assert sol["final_answer"] == "24"

    def test_build_question(self):
        t = BinomialExpansionTemplate()
        p = t.sample_parameters()
        item = t.build_question(p)
        assert item.topic == "binomial_expansion"
        assert item.final_answer

    def test_validate_bad_r(self):
        t = BinomialExpansionTemplate()
        errors = t.validate_params({"n": 4, "a": 1, "b": 2, "term_r": 5})
        assert errors


class TestGetTemplate:
    def test_known_topics(self):
        for topic in ["arithmetic_series", "geometric_series", "differentiation",
                      "integration", "logarithms", "binomial_expansion"]:
            assert get_template(topic) is not None

    def test_unknown_topic(self):
        assert get_template("unknown_xyz") is None
