"""
Tests of rounding halves away from zero.
"""

from __future__ import annotations

from fractions import Fraction

from law_as_code_benchmarks.law.rounding import Rounding

# %% halves


def test_a_positive_half_rounds_up() -> None:
    """2.5 rounds to 3."""
    assert Rounding.round_half_away_from_zero(Fraction(5, 2)) == 3


def test_a_negative_half_rounds_down() -> None:
    """-2.5 rounds to -3, away from zero."""
    assert Rounding.round_half_away_from_zero(Fraction(-5, 2)) == -3


def test_less_than_a_half_rounds_towards_zero() -> None:
    """2.49 rounds to 2."""
    assert Rounding.round_half_away_from_zero(Fraction(249, 100)) == 2


# %% decimal places


def test_rounding_to_decimal_places_keeps_them() -> None:
    """0.125 rounds to 0.13 at two decimal places."""
    assert Rounding.round_half_away_from_zero(Fraction(125, 1000), 2) == Fraction(
        13, 100
    )
