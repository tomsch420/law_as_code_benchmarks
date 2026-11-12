"""
Tests of reading the tests of Catala's family benefits example.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from law_as_code_benchmarks.catala.case import (
    AmountPaidAssertion,
    CatalaTest,
    CatalaTestFile,
    EntitlementAssertion,
)
from law_as_code_benchmarks.catala.domain import (
    ChildCare,
    Money,
    SchoolingStage,
    Territory,
)
from law_as_code_benchmarks.catala.exceptions import UnexpectedCatalaStatement

# %% reading a test file


def read_test_file(file_name: str) -> list[CatalaTest]:
    """:return: The tests of :file:`test_files/{file_name}`."""
    return CatalaTest.from_text(
        CatalaTestFile.FAMILY_ALLOWANCES,
        (Path(__file__).parent / "test_files" / file_name).read_text(),
    )


def test_a_child_structure_and_the_household_definitions_are_read() -> None:
    """
    A child written as ``EnfantEntrée`` and the household's inputs read as the domain
    model, money with thousands separated by spaces and decimals by a comma.
    """
    (test,) = read_test_file("mayotte_child.catala_fr")
    (child,) = test.household.children
    assert (child.identifier, child.birth_date, child.monthly_pay, child.care) == (
        1,
        datetime.date(2007, 1, 1),
        Money(cents=125050),
        ChildCare.SHARED_RESIDENCE_SHARED_ALLOWANCE,
    )
    assert (
        test.household.assessment_date,
        test.household.residence,
        test.household.resources,
        test.household.had_child_before_2012,
    ) == (datetime.date(2020, 5, 1), Territory.MAYOTTE, Money(cents=3000000), True)


def test_an_amount_assertion_is_read() -> None:
    """
    ``assertion f.i_montant_versé = 57,28€`` reads as the amount paid.
    """
    (test,) = read_test_file("mayotte_child.catala_fr")
    assert test.assertions == [AmountPaidAssertion(expected_amount=Money(cents=5728))]


def test_entitlement_assertions_and_stated_schooling_stages_are_read() -> None:
    """
    A test without children of its own asks about every child of the data scope, whose
    stated stage of compulsory schooling is kept, and ``non`` negates an assertion.
    """
    (test,) = read_test_file("stated_schooling.catala_fr")
    first, second = test.household.children
    assert [child.stated_schooling_stage for child in (first, second)] == [
        SchoolingStage.DURING,
        SchoolingStage.AFTER,
    ]
    assert test.assertions == [
        EntitlementAssertion(child=first, expected_entitlement=True),
        EntitlementAssertion(child=second, expected_entitlement=False),
    ]


def test_an_assertion_the_reader_cannot_apply_is_refused() -> None:
    """
    An assertion about a variable no score compares is refused, not left out.
    """
    with pytest.raises(UnexpectedCatalaStatement):
        read_test_file("unknown_assertion.catala_fr")


# %% the example's files


def test_the_example_holds_sixteen_test_scopes() -> None:
    """
    The amounts file holds 14 test scopes and each entitlement file one.
    """
    assert {
        test_file: len(CatalaTest.from_file(test_file)) for test_file in CatalaTestFile
    } == {
        CatalaTestFile.FAMILY_ALLOWANCES: 14,
        CatalaTestFile.FAMILY_ALLOWANCES_ENTITLEMENT: 1,
        CatalaTestFile.FAMILY_BENEFITS_ENTITLEMENT: 1,
    }
