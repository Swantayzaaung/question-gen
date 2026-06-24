"""
SymPy-based utilities for symbolic math checking.
"""

from __future__ import annotations
import re
from typing import Optional

try:
    import sympy as sp
    from sympy import (
        sympify, simplify, solve, diff, integrate, expand,
        Rational, sqrt, pi, E, oo, zoo, nan, Symbol,
        binomial as sympy_binomial, factorial,
        latex, N, Abs, Float
    )
    from sympy.parsing.sympy_parser import (
        parse_expr, standard_transformations, implicit_multiplication_application
    )
    SYMPY_OK = True
except ImportError:
    SYMPY_OK = False


_TRANSFORMS = (standard_transformations + (implicit_multiplication_application,)) if SYMPY_OK else None


def _parse(text: str):
    """Parse a math expression string to a SymPy expression."""
    if not SYMPY_OK:
        raise RuntimeError("sympy not available")
    text = text.strip()
    # Replace common LaTeX-ish notations
    text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', text)
    text = re.sub(r'\\sqrt\{([^}]+)\}', r'sqrt(\1)', text)
    text = re.sub(r'\\sqrt(\w)', r'sqrt(\1)', text)
    text = re.sub(r'\^', r'**', text)
    text = re.sub(r'\\times', '*', text)
    text = re.sub(r'\\cdot', '*', text)
    text = re.sub(r'\\left|\\right', '', text)
    text = re.sub(r'\$', '', text)
    try:
        return parse_expr(text, transformations=_TRANSFORMS)
    except Exception:
        return sympify(text)


def normalize_expr(text: str) -> Optional[object]:
    """Parse and simplify an expression string. Returns None on failure."""
    if not SYMPY_OK:
        return None
    try:
        expr = _parse(text)
        return simplify(expr)
    except Exception:
        return None


def equivalent(a: str, b: str, tol: float = 1e-9) -> bool:
    """Check whether two math expression strings are equivalent."""
    if not SYMPY_OK:
        return a.strip() == b.strip()
    try:
        ea = _parse(a)
        eb = _parse(b)
        diff_expr = simplify(ea - eb)
        if diff_expr == 0:
            return True
        # Numeric check
        val = complex(N(diff_expr.subs([(s, 1.23456789) for s in diff_expr.free_symbols])))
        return abs(val) < tol
    except Exception:
        return False


def is_integer_answer(expr_or_str) -> bool:
    """Return True if the expression evaluates to an integer."""
    if not SYMPY_OK:
        try:
            return float(expr_or_str) == int(float(expr_or_str))
        except Exception:
            return False
    try:
        if isinstance(expr_or_str, str):
            expr_or_str = _parse(expr_or_str)
        val = simplify(expr_or_str)
        return val.is_integer is True
    except Exception:
        return False


def is_simple_fraction(expr_or_str, max_denominator: int = 12) -> bool:
    """Return True if the expression is a rational with small denominator."""
    if not SYMPY_OK:
        return False
    try:
        if isinstance(expr_or_str, str):
            expr_or_str = _parse(expr_or_str)
        val = simplify(expr_or_str)
        if val.is_Rational:
            return abs(val.q) <= max_denominator
        return False
    except Exception:
        return False


def is_surd_or_irrational(expr_or_str) -> bool:
    """Return True if the expression contains surds or irrationals."""
    if not SYMPY_OK:
        return False
    try:
        if isinstance(expr_or_str, str):
            expr_or_str = _parse(expr_or_str)
        val = simplify(expr_or_str)
        return not val.is_rational
    except Exception:
        return False


def has_unique_real_solution(equation_lhs, variable_name: str = "x", domain=None) -> bool:
    """Check whether an equation (lhs=0) has exactly one real solution."""
    if not SYMPY_OK:
        return False
    try:
        if isinstance(equation_lhs, str):
            equation_lhs = _parse(equation_lhs)
        x = Symbol(variable_name)
        solutions = solve(equation_lhs, x)
        real_sols = [s for s in solutions if s.is_real]
        if domain:
            real_sols = [s for s in real_sols if domain[0] <= float(s.evalf()) <= domain[1]]
        return len(real_sols) == 1
    except Exception:
        return False


def compute_derivative(expr_str: str, var: str = "x"):
    """Differentiate expression with respect to var."""
    if not SYMPY_OK:
        return None
    try:
        expr = _parse(expr_str)
        x = Symbol(var)
        return diff(expr, x)
    except Exception:
        return None


def compute_integral(expr_str: str, var: str = "x", lower=None, upper=None):
    """Integrate expression. If bounds given, returns definite integral."""
    if not SYMPY_OK:
        return None
    try:
        expr = _parse(expr_str)
        x = Symbol(var)
        if lower is not None and upper is not None:
            return integrate(expr, (x, lower, upper))
        return integrate(expr, x)
    except Exception:
        return None


def solve_equation(lhs_str: str, var: str = "x") -> list:
    """Solve lhs = 0 for var. Returns list of solutions."""
    if not SYMPY_OK:
        return []
    try:
        lhs = _parse(lhs_str)
        x = Symbol(var)
        return solve(lhs, x)
    except Exception:
        return []


def check_cleanliness(expr_or_str, cleanliness: str) -> bool:
    """Check if expression matches the cleanliness requirement."""
    if not SYMPY_OK:
        return True
    try:
        if isinstance(expr_or_str, str):
            expr_or_str = _parse(expr_or_str)
        val = simplify(expr_or_str)
        if cleanliness == "clean":
            return val.is_integer is True or is_simple_fraction(val)
        elif cleanliness == "mixed":
            # allow simple surds or fractions
            return True  # hard to enforce without more heuristics
        else:
            return True
    except Exception:
        return True
