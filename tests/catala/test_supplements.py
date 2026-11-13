"""
Tests of what family allowances add to their base: age supplements, the flat allowance
and the degressive supplements.
"""

from __future__ import annotations

import datetime

import pytest

from law_as_code_benchmarks.catala.amounts import MonthlyBases
from law_as_code_benchmarks.catala.conclusions import ResourceBracket
from law_as_code_benchmarks.catala.domain import (
    ChildCare,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.supplements import (
    AgeSupplementMinimumAgeProvision,
    AgeSupplementRightProvision,
    AllowanceDegressiveSupplementProvision,
    FamilyAllowanceProvision,
    FlatAllowanceRightProvision,
    InitialAgeSupplementProvision,
    PaidFlatAllowanceProvision,
    SharedAgeSupplementProvision,
)

from .families import child_born, children_born, household_of

# %% age supplements


@pytest.mark.parametrize(
    "birth_date, age",
    [
        (
            datetime.date(1997, 4, 30),
            AgeSupplementMinimumAgeProvision.minimum_age_before_2008,
        ),
        (datetime.date(1997, 5, 1), AgeSupplementMinimumAgeProvision.minimum_age),
    ],
)
def test_a_child_eleven_by_april_30_2008_keeps_the_earlier_minimum_age(
    birth_date: datetime.date, age: int
) -> None:
    """
    A child turning 11 on April 30, 2008, keeps the age set before the décret n°
    2008-409; one turning 11 a day later does not.
    """
    household = household_of([child_born(birth_date)])
    assert [
        conclusion.age
        for conclusion in AgeSupplementMinimumAgeProvision(
            household=household
        ).conclusions
    ] == [age]


def test_before_may_2008_a_child_gives_a_right_from_11_at_a_lower_rate_until_16() -> (
    None
):
    """
    On January 1, 2006, of three children aged 16, 14 and 6, the 16-year-old is paid 16
    % of the monthly base, the 14-year-old 9 %, and the 6-year-old nothing.
    """
    household = household_of(
        children_born(1990, 1992, 2000), datetime.date(2006, 1, 1), resources=Money.zero
    )
    base = MonthlyBases.JANUARY_2006.value.amount
    assert [
        conclusion.amount
        for conclusion in InitialAgeSupplementProvision(household=household).conclusions
    ] == [
        base * ResourceBracket.FIRST.value.age_supplement,
        base * InitialAgeSupplementProvision.rate_until_16_before_2008,
        Money.zero,
    ]


@pytest.mark.parametrize(
    "birth_date, age",
    [
        (datetime.date(2012, 2, 28), AgeSupplementMinimumAgeProvision.minimum_age),
        (
            AgeSupplementMinimumAgeProvision.first_birth_date_of_2026_reform,
            AgeSupplementMinimumAgeProvision.minimum_age_from_2026,
        ),
    ],
)
def test_from_march_2026_a_child_born_from_march_2012_gives_a_right_from_18(
    birth_date: datetime.date, age: int
) -> None:
    """
    On March 1, 2026, a child born on February 28, 2012, keeps the minimum age of 14;
    one born on March 1 has 18.
    """
    household = household_of(
        [child_born(birth_date)],
        AgeSupplementMinimumAgeProvision.first_day_of_2026_reform,
    )
    assert [
        conclusion.age
        for conclusion in AgeSupplementMinimumAgeProvision(
            household=household
        ).conclusions
    ] == [age]


def test_every_child_of_a_household_is_given_a_minimum_age_before_may_2008() -> None:
    """
    Before the décret n° 2008-409, each of two children has the minimum age of 11.
    """
    household = household_of(children_born(1995, 1997), datetime.date(2007, 1, 1))
    assert [
        conclusion.age
        for conclusion in AgeSupplementMinimumAgeProvision(
            household=household
        ).conclusions
    ] == [AgeSupplementMinimumAgeProvision.lower_supplement_age_before_2008] * 2


@pytest.mark.parametrize(
    "birth_years, rights",
    [
        ((2005, 2006), [False, True]),
        ((2005, 2006, 2010), [True, True, False]),
    ],
)
def test_every_child_but_the_oldest_gives_a_right_from_14_and_every_child_of_three(
    birth_years: tuple[int, ...], rights: list[bool]
) -> None:
    """
    On May 1, 2020, of two children aged 15 and 14 only the younger gives a right; with
    a third child, so does the oldest, but not the 10-year-old.
    """
    household = household_of(children_born(*birth_years))
    assert [
        conclusion.holds
        for conclusion in AgeSupplementRightProvision(household=household).conclusions
    ] == rights


def test_a_shared_residence_halves_the_age_supplement() -> None:
    """
    16 % of 414.40 € is 66.30 €, halved 33.15 €, for the younger of two children.
    """
    younger = child_born(
        datetime.date(2006, 1, 1), care=ChildCare.SHARED_RESIDENCE_SHARED_ALLOWANCE
    )
    household = household_of([child_born(datetime.date(2005, 1, 1)), younger])
    assert [
        conclusion.amount
        for conclusion in SharedAgeSupplementProvision(household=household).conclusions
        if conclusion.child is younger
    ] == [Money(cents=3315)]


# %% the flat allowance


@pytest.mark.parametrize(
    "birth_years_of_siblings, birth_date, holds",
    [
        ((2008, 2010), datetime.date(2000, 6, 1), True),
        ((2008, 2010), datetime.date(1999, 6, 1), True),
        ((2010,), datetime.date(2000, 6, 1), False),
    ],
)
def test_the_flat_allowance_is_due_for_a_child_near_the_age_limit_among_three(
    birth_years_of_siblings: tuple[int, ...], birth_date: datetime.date, holds: bool
) -> None:
    """
    A child turning 20 within a year gives a right in a household of three children, and
    so, as Catala reads it, does one who turned 20 before; not among two.
    """
    child = child_born(birth_date)
    household = household_of(children_born(*birth_years_of_siblings) + [child])
    assert [
        conclusion.holds
        for conclusion in FlatAllowanceRightProvision(household=household).conclusions
        if conclusion.child is child
    ] == [holds]


def test_the_flat_allowance_pays_the_brackets_rate_per_child() -> None:
    """
    20.234 % of 414.40 € is 83.85 € for the one child giving a right.
    """
    household = household_of(children_born(2000, 2008, 2010))
    assert [
        conclusion.amount
        for conclusion in PaidFlatAllowanceProvision(household=household).conclusions
    ] == [Money(cents=8385)]


# %% degressive supplements


def test_resources_just_above_a_ceiling_are_made_up_for_by_a_degressive_supplement() -> (
    None
):
    """
    Two children in 2020 and resources of 69,809 €, 500 € above the first ceiling:

    the second bracket pays 66.30 €, and a twelfth of 69,309 € plus twelve times 66.30 €
    less 69,809 € is 24.63 €.
    """
    household = household_of(children_born(2010, 2012), resources=Money(cents=6980900))
    assert [
        conclusion.amount
        for conclusion in AllowanceDegressiveSupplementProvision(
            household=household
        ).conclusions
    ] == [Money(cents=2463)]
    assert [
        conclusion.amount
        for conclusion in FamilyAllowanceProvision(household=household).conclusions
    ] == [Money(cents=6630 + 2463)]


# %% the amount paid


def test_a_household_without_children_is_paid_nothing() -> None:
    """
    A household with no child in its charge has no right to family allowances.
    """
    household = household_of([])
    assert [
        conclusion.amount
        for conclusion in FamilyAllowanceProvision(household=household).conclusions
    ] == [Money.zero]
