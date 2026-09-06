"""Small helpers for writing the LaTeX that KaTeX renders in the browser."""

from __future__ import annotations

from fractions import Fraction


def tex(expression: str) -> str:
    """Wrap an expression in inline math delimiters."""
    return f"${expression}$"


def number(value: float | int | Fraction) -> str:
    """Format a number without a trailing ``.0``."""
    if isinstance(value, Fraction):
        return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def signed(value: float | int) -> str:
    """``+3`` / ``-3``, for appending a term to an expression."""
    return f"+ {number(value)}" if value >= 0 else f"- {number(abs(value))}"


def term(coefficient: int, variable: str = "x") -> str:
    """``3x``, ``-x``, ``x``; an empty string when the coefficient is 0."""
    if coefficient == 0:
        return "0"
    if coefficient == 1:
        return variable
    if coefficient == -1:
        return f"-{variable}"
    return f"{coefficient}{variable}"


def linear(a: int, b: int, variable: str = "x") -> str:
    """``3x + 4``, ``-x - 2``, ``5x``."""
    if a == 0:
        return number(b)
    if b == 0:
        return term(a, variable)
    return f"{term(a, variable)} {signed(b)}"


def fraction(numerator: int, denominator: int) -> str:
    """A reduced ``\\frac`` — or a plain integer when it divides evenly."""
    value = Fraction(numerator, denominator)
    if value.denominator == 1:
        return number(value.numerator)
    sign = "-" if value < 0 else ""
    return f"{sign}\\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def sum_terms(*parts: str) -> str:
    """Join formatted terms with proper signs: ``("3x", "-4y")`` -> ``"3x - 4y"``.

    Empty and ``"0"`` parts are dropped, so callers can pass optional terms.
    """
    kept = [part for part in parts if part not in ("", "0")]
    if not kept:
        return "0"

    result = kept[0]
    for part in kept[1:]:
        result += f" - {part[1:]}" if part.startswith("-") else f" + {part}"
    return result


def paren(value: float | int) -> str:
    """Wrap negatives in parentheses so ``2 - (-3)`` reads correctly."""
    text = number(value)
    return f"({text})" if text.startswith("-") else text
