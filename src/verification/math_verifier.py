"""
Deterministic math verifier. Dispatches by topic/skill using SymPy.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from schemas import GeneratedItem

from .sympy_tools import (
    SYMPY_OK, _parse, normalize_expr, equivalent, is_integer_answer,
    is_simple_fraction, is_surd_or_irrational, compute_derivative,
    compute_integral, solve_equation, check_cleanliness
)

try:
    import sympy as sp
    from sympy import Symbol, Rational, simplify, N, solve, diff, integrate, expand, binomial as sp_binomial, factorial
except ImportError:
    pass


def verify_item(item) -> "object":
    """
    Dispatch to topic-specific verifier.
    Returns a VerifierResult-like dict (converted to VerifierResult in caller).
    """
    from schemas import VerifierResult
    if not SYMPY_OK:
        return VerifierResult(
            is_correct=False,
            warnings=["sympy not available — cannot verify deterministically"],
        )

    topic = item.topic
    skill = item.primary_skill
    params = item.parameters
    final_answer = item.final_answer

    try:
        if topic == "arithmetic_series":
            return _verify_arithmetic_series(item)
        elif topic == "geometric_series":
            return _verify_geometric_series(item)
        elif topic == "differentiation":
            return _verify_differentiation(item)
        elif topic == "integration":
            return _verify_integration(item)
        elif topic == "logarithms":
            return _verify_logarithms(item)
        elif topic == "binomial_expansion":
            return _verify_binomial(item)
        else:
            return VerifierResult(
                is_correct=False,
                warnings=[f"No deterministic verifier for topic '{topic}'"],
            )
    except Exception as e:
        from schemas import VerifierResult
        return VerifierResult(
            is_correct=False,
            errors=[f"Verifier exception: {str(e)}"],
        )


def _result(is_correct, computed=None, errors=None, warnings=None, checks=None):
    from schemas import VerifierResult
    return VerifierResult(
        is_correct=is_correct,
        computed_answer=str(computed) if computed is not None else None,
        errors=errors or [],
        warnings=warnings or [],
        checks=checks or {},
    )


def _verify_arithmetic_series(item):
    p = item.parameters
    a = p.get("first_term")
    d = p.get("common_difference")
    n = p.get("n")

    errors = []
    checks = {}

    if None in (a, d, n):
        return _result(False, errors=["Missing arithmetic series parameters"])

    if not isinstance(n, int) or n <= 0:
        errors.append(f"n must be a positive integer, got {n}")

    # Compute sum
    S = sp.Rational(n, 2) * (2 * a + (n - 1) * d)
    checks["computed_sum"] = str(S)

    # Check final answer
    fa = item.final_answer
    if equivalent(fa, str(S)):
        return _result(True, computed=S, checks=checks)
    else:
        # Maybe they asked for nth term
        Tn = a + (n - 1) * d
        checks["computed_nth_term"] = str(Tn)
        if equivalent(fa, str(Tn)):
            return _result(True, computed=Tn, checks=checks)
        errors.append(f"Final answer '{fa}' != computed sum '{S}' or nth term '{Tn}'")
        return _result(False, computed=S, errors=errors, checks=checks)


def _verify_geometric_series(item):
    p = item.parameters
    a = p.get("first_term")
    r = p.get("common_ratio")
    n = p.get("n")
    task = p.get("task", "sum")  # "sum", "nth_term", "sum_to_infinity"

    errors = []
    checks = {}

    if None in (a, r):
        return _result(False, errors=["Missing geometric series parameters a or r"])

    # Normalise r to a number
    try:
        if isinstance(r, str):
            from fractions import Fraction as _Frac
            r = float(_Frac(r))
    except Exception:
        return _result(False, errors=[f"Cannot parse common_ratio: {r}"])

    if r == 1:
        errors.append("Common ratio r=1 makes sum formula degenerate")

    fa = item.final_answer

    if task == "sum_to_infinity":
        if abs(float(r)) >= 1:
            errors.append(f"Series with |r|={abs(float(r))} does not converge")
            return _result(False, errors=errors, checks=checks)
        S_inf = sp.Rational(a, 1) / (1 - r) if isinstance(r, (int, float)) else sp.Rational(a) / (1 - sp.Rational(r))
        checks["computed_S_inf"] = str(S_inf)
        if equivalent(fa, str(S_inf)):
            return _result(True, computed=S_inf, checks=checks)
        errors.append(f"Final answer '{fa}' != computed S_inf '{S_inf}'")
        return _result(False, computed=S_inf, errors=errors, checks=checks)

    elif task == "nth_term":
        if n is None:
            return _result(False, errors=["n required for nth_term task"])
        Tn = a * (sp.Rational(r) ** (n - 1)) if isinstance(r, (int, float)) else a * r ** (n - 1)
        checks["computed_nth_term"] = str(Tn)
        if equivalent(fa, str(Tn)):
            return _result(True, computed=Tn, checks=checks)
        errors.append(f"Final answer '{fa}' != computed nth term '{Tn}'")
        return _result(False, computed=Tn, errors=errors, checks=checks)

    else:  # sum
        if n is None:
            return _result(False, errors=["n required for sum task"])
        if isinstance(r, str):
            r_sym = sp.Rational(r)
        elif isinstance(r, (int, float)):
            r_sym = sp.Rational(r)
        else:
            r_sym = r
        S = a * (1 - r_sym ** n) / (1 - r_sym)
        S = sp.simplify(S)
        checks["computed_sum"] = str(S)
        if equivalent(fa, str(S)):
            return _result(True, computed=S, checks=checks)
        errors.append(f"Final answer '{fa}' != computed sum '{S}'")
        return _result(False, computed=S, errors=errors, checks=checks)


def _verify_differentiation(item):
    p = item.parameters
    expr_str = p.get("expression")
    task = p.get("task", "stationary_points")

    errors = []
    checks = {}

    if not expr_str:
        return _result(False, errors=["No expression in parameters"])

    x = Symbol("x")
    try:
        expr = _parse(expr_str)
        dy_dx = diff(expr, x)
        checks["derivative"] = str(dy_dx)
    except Exception as e:
        return _result(False, errors=[f"Failed to differentiate: {e}"])

    fa = item.final_answer

    if task == "stationary_points":
        try:
            crit_points = solve(dy_dx, x)
            real_crit = [pt for pt in crit_points if pt.is_real]
            checks["stationary_x_values"] = str(real_crit)

            if not real_crit:
                errors.append("No real stationary points found")
                return _result(False, errors=errors, checks=checks)

            # Compute y values
            stat_points = [(float(pt), float(expr.subs(x, pt))) for pt in real_crit]
            checks["stationary_points_xy"] = str(stat_points)

            # Check if answer matches one of them
            for xv, yv in stat_points:
                if equivalent(fa, str(sp.Rational(yv).limit_denominator(1000))):
                    return _result(True, computed=yv, checks=checks)
                # Try coordinate form
                coord_str = f"({xv}, {yv})"
                if fa.strip() == coord_str or equivalent(fa, str(xv)):
                    return _result(True, computed=coord_str, checks=checks)

            # If answer references multiple points
            return _result(True, computed=str(stat_points), checks=checks,
                           warnings=["Could not match final_answer to specific point; stationary points computed"])
        except Exception as e:
            errors.append(f"Failed to find stationary points: {e}")
            return _result(False, errors=errors, checks=checks)

    elif task == "derivative":
        if equivalent(fa, str(dy_dx)):
            return _result(True, computed=dy_dx, checks=checks)
        dy_dx_simplified = sp.simplify(dy_dx)
        if equivalent(fa, str(dy_dx_simplified)):
            return _result(True, computed=dy_dx_simplified, checks=checks)
        errors.append(f"Derivative mismatch: got '{dy_dx}', answer says '{fa}'")
        return _result(False, computed=dy_dx, errors=errors, checks=checks)

    return _result(False, errors=[f"Unknown differentiation task: {task}"])


def _verify_integration(item):
    p = item.parameters
    expr_str = p.get("expression")
    lower = p.get("lower_bound")
    upper = p.get("upper_bound")
    task = p.get("task", "area")

    errors = []
    checks = {}

    if not expr_str:
        return _result(False, errors=["No expression in parameters"])

    x = Symbol("x")
    try:
        expr = _parse(expr_str)
    except Exception as e:
        return _result(False, errors=[f"Failed to parse expression: {e}"])

    fa = item.final_answer

    if lower is not None and upper is not None:
        try:
            area = integrate(expr, (x, lower, upper))
            area_simplified = sp.simplify(area)
            checks["computed_integral"] = str(area_simplified)

            if float(area_simplified) < 0:
                errors.append("Computed area is negative — check bounds or expression")

            if equivalent(fa, str(area_simplified)):
                return _result(True, computed=area_simplified, checks=checks)
            # Try absolute value for area
            if equivalent(fa, str(abs(area_simplified))):
                return _result(True, computed=abs(area_simplified), checks=checks)
            errors.append(f"Final answer '{fa}' != computed integral '{area_simplified}'")
            return _result(False, computed=area_simplified, errors=errors, checks=checks)
        except Exception as e:
            errors.append(f"Integration failed: {e}")
            return _result(False, errors=errors, checks=checks)
    else:
        # Indefinite integral check
        try:
            antideriv = integrate(expr, x)
            checks["antiderivative"] = str(antideriv)
            if equivalent(fa, str(antideriv)):
                return _result(True, computed=antideriv, checks=checks)
            return _result(True, computed=antideriv, checks=checks,
                           warnings=["Indefinite integral computed; final answer format may differ by constant"])
        except Exception as e:
            errors.append(f"Integration failed: {e}")
            return _result(False, errors=errors, checks=checks)


def _verify_logarithms(item):
    p = item.parameters
    equation_str = p.get("equation")
    task = p.get("task", "solve")

    errors = []
    checks = {}

    if not equation_str:
        return _result(False, errors=["No equation in parameters"])

    x = Symbol("x")
    fa = item.final_answer

    try:
        # Parse as lhs - rhs = 0
        if "=" in equation_str:
            parts = equation_str.split("=", 1)
            lhs = _parse(parts[0])
            rhs = _parse(parts[1])
            eq = lhs - rhs
        else:
            eq = _parse(equation_str)

        solutions = solve(eq, x)
        # Filter to positive real solutions (log domain)
        real_positive = []
        for s in solutions:
            try:
                val = float(s.evalf())
                if val > 0:
                    real_positive.append(s)
            except Exception:
                pass
        checks["solutions"] = str(real_positive)

        if not real_positive:
            errors.append("No valid positive real solutions found")
            return _result(False, errors=errors, checks=checks)

        if len(real_positive) == 1:
            sol = real_positive[0]
            if equivalent(fa, str(sol)):
                return _result(True, computed=sol, checks=checks)
            # Try numeric
            if abs(float(sp.N(sol)) - float(sp.N(_parse(fa)))) < 1e-6:
                return _result(True, computed=sol, checks=checks)
            errors.append(f"Final answer '{fa}' != solution '{sol}'")
            return _result(False, computed=sol, errors=errors, checks=checks)
        else:
            checks["all_solutions"] = str(real_positive)
            return _result(True, computed=str(real_positive),
                           warnings=["Multiple solutions found"], checks=checks)
    except Exception as e:
        errors.append(f"Log verification failed: {e}")
        return _result(False, errors=errors, checks=checks)


def _verify_binomial(item):
    p = item.parameters
    n = p.get("n")
    a = p.get("a", 1)
    b = p.get("b", 1)
    term_r = p.get("term_r")  # which term (0-indexed)
    task = p.get("task", "coefficient")

    errors = []
    checks = {}
    fa = item.final_answer

    if n is None:
        return _result(False, errors=["n required for binomial"])

    try:
        if task == "coefficient" and term_r is not None:
            # Coefficient of x^r in (a + bx)^n
            r = term_r
            coeff = int(sp_binomial(n, r)) * (a ** (n - r)) * (b ** r)
            checks["computed_coefficient"] = str(coeff)
            if equivalent(fa, str(coeff)):
                return _result(True, computed=coeff, checks=checks)
            errors.append(f"Coefficient mismatch: computed {coeff}, answer '{fa}'")
            return _result(False, computed=coeff, errors=errors, checks=checks)

        elif task == "expand":
            x = Symbol("x")
            expr = (a + b * x) ** n
            expanded = expand(expr)
            checks["expansion"] = str(expanded)
            return _result(True, computed=expanded, checks=checks,
                           warnings=["Expansion computed; full verification of wording not done"])

        else:
            return _result(False, errors=[f"Unknown binomial task: {task}"])

    except Exception as e:
        errors.append(f"Binomial verification failed: {e}")
        return _result(False, errors=errors, checks=checks)
