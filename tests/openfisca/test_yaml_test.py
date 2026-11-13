"""
Tests of reading OpenFisca's tests and answering them with the family benefits model.
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction

import pytest

from law_as_code_benchmarks.catala.amounts import MonthlyBases
from law_as_code_benchmarks.catala.conclusions import ResourceBracket
from law_as_code_benchmarks.openfisca.exceptions import UnexpectedOpenFiscaVariable
from law_as_code_benchmarks.openfisca.yaml_test import (
    ErrorMargin,
    ExpectedOutput,
    OpenFiscaComputedTest,
    OpenFiscaTestFile,
    OpenFiscaVariable,
)

from .snippets import read_snippet

# %% reading


def test_a_test_is_read_with_its_month_margin_and_outputs() -> None:
    """
    The month is the period's first day, the margins and the expected values are exact.
    """
    test = read_snippet("shared_residence_with_wages.yaml")
    assert (
        test.identifier,
        test.month.isoformat(),
        test.margin,
        test.expected_outputs,
    ) == (
        f"{OpenFiscaTestFile.FAMILY_ALLOWANCES.value}:1",
        "2019-01-01",
        ErrorMargin(relative=Fraction(1, 100)),
        [
            ExpectedOutput(
                variable=OpenFiscaVariable.SHARED_RESIDENCE_COEFFICIENT,
                value=Fraction(5, 6),
            ),
            ExpectedOutput(
                variable=OpenFiscaVariable.AGE_SUPPLEMENTS, value=Fraction(0)
            ),
        ],
    )


def test_an_output_the_reader_does_not_map_is_refused() -> None:
    """
    A birth grant is no output of family allowances.
    """
    with pytest.raises(UnexpectedOpenFiscaVariable):
        read_snippet("unknown_output.yaml")


@pytest.mark.parametrize(
    "margin, computed, admitted",
    [
        (ErrorMargin(), Fraction(100), True),
        (ErrorMargin(), Fraction(10001, 100), False),
        (ErrorMargin(absolute=Fraction(2, 100)), Fraction(10002, 100), True),
        (ErrorMargin(absolute=Fraction(2, 100)), Fraction(10003, 100), False),
        (ErrorMargin(relative=Fraction(1, 100)), Fraction(99), True),
        (ErrorMargin(relative=Fraction(1, 100)), Fraction(9899, 100), False),
    ],
)
def test_a_margin_admits_what_is_within_it_of_the_expected_value(
    margin: ErrorMargin, computed: Fraction, admitted: bool
) -> None:
    """
    Without a margin the value must be exact; an absolute margin bounds the difference,
    a relative one the difference over the expected value, 100.
    """
    assert margin.admits(Fraction(100), computed) == admitted


# %% where the values come from


@pytest.mark.parametrize(
    "test_file, name, computed",
    [
        (OpenFiscaTestFile.FAMILY_ALLOWANCES, "Two children given by age", False),
        (
            OpenFiscaTestFile.FAMILY_ALLOWANCES,
            OpenFiscaComputedTest.SHARED_RESIDENCE.value,
            True,
        ),
        (OpenFiscaTestFile.APRIL_2020, "Two children given by age", True),
    ],
)
def test_the_values_of_the_tests_listed_and_of_april_2020_are_openfiscas(
    test_file: OpenFiscaTestFile, name: str, computed: bool
) -> None:
    """
    A test is taken to expect OpenFisca's own values where its name is listed or its
    whole file is.
    """
    test = dataclasses.replace(
        read_snippet("two_children_by_age.yaml", test_file), name=name
    )
    assert test.is_computed_by_openfisca == computed


# %% answering


def test_two_children_are_paid_the_second_childs_rate_in_june_2013() -> None:
    """
    32 % of the monthly base of April 2013, as the test expects.
    """
    test = read_snippet("two_children_by_age.yaml")
    assert test.computed_outputs() == {
        OpenFiscaVariable.FAMILY_ALLOWANCE: Fraction(
            (
                MonthlyBases.APRIL_2013.value.amount
                * ResourceBracket.FIRST.value.second_child
            ).cents,
            100,
        )
    }
    assert test.is_reproduced()


def test_a_test_expecting_another_amount_is_not_reproduced() -> None:
    """
    The same test expecting a cent more than its margin allows is not reproduced.
    """
    test = read_snippet("two_children_by_age.yaml")
    (output,) = test.expected_outputs
    wrong = dataclasses.replace(
        test,
        expected_outputs=[
            dataclasses.replace(output, value=output.value + Fraction(2, 100))
        ],
    )
    assert not wrong.is_reproduced()


def test_a_shared_residence_and_no_age_supplement_are_computed() -> None:
    """
    One child of three in shared residence leaves five sixths of the base allowance; no
    child is old enough for an age supplement.
    """
    test = read_snippet("shared_residence_with_wages.yaml")
    assert test.computed_outputs() == {
        OpenFiscaVariable.SHARED_RESIDENCE_COEFFICIENT: Fraction(5, 6),
        OpenFiscaVariable.AGE_SUPPLEMENTS: Fraction(0),
    }
