"""
Tests of reading the arithmetic OpenFisca's tests write values in.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from law_as_code_benchmarks.openfisca.arithmetic import ArithmeticReader

# %% reading


@pytest.mark.parametrize(
    "text, value",
    [
        ("1412.64 / 12", Fraction("1412.64") / 12),
        ("131.16 / (1 - 0.005)", Fraction("131.16") / Fraction("0.995")),
        (
            "231.31 / (1 - 0.005) + 48.97",
            Fraction("231.31") / Fraction("0.995") + Fraction("48.97"),
        ),
        (
            "63534 / 0.90 / 2 + 20 / 0.90 / 2",
            (Fraction(63534) / Fraction("0.9") + Fraction(20) / Fraction("0.9")) / 2,
        ),
        ("-2 * 3", Fraction(-6)),
        ("(296.53 * 0.8333)", Fraction("296.53") * Fraction("0.8333")),
    ],
)
def test_an_expression_evaluates_exactly_with_the_usual_precedence(
    text: str, value: Fraction
) -> None:
    """
    Division and multiplication bind tighter than addition and subtraction, parentheses
    tighter still, and decimals are read exactly.
    """
    assert ArithmeticReader().read(text) == value


@pytest.mark.parametrize(
    "number, value",
    [(0, Fraction(0)), (40000, Fraction(40000)), (0.8333, Fraction("0.8333"))],
)
def test_a_number_yaml_already_read_is_taken_as_written(
    number: int | float, value: Fraction
) -> None:
    """
    A float is read from its decimal writing, not its binary value.
    """
    assert ArithmeticReader().read(number) == value
