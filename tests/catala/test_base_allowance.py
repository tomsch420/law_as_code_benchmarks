"""
Tests of the base of family allowances: ceilings, brackets, the right to them and what
is paid for each child.
"""

from __future__ import annotations

import datetime

import pytest

from law_as_code_benchmarks.catala.base_allowance import (
    BaseAllowanceRightProvision,
    FirstChildAmountProvision,
    HouseholdBracketProvision,
    InitialBaseAmountProvision,
    PaidBaseAllowanceProvision,
    ResourceCeilingsProvision,
)
from law_as_code_benchmarks.catala.conclusions import ResourceBracket
from law_as_code_benchmarks.catala.domain import ChildCare, Money, Territory

from .families import child_born, children_born, household_of

# %% the household's bracket


@pytest.mark.parametrize(
    "assessment_date, ceilings",
    [
        (datetime.date(2020, 5, 1), (Money(cents=6930900), Money(cents=9238100))),
        (datetime.date(2022, 5, 1), (Money(cents=6714000), Money(cents=8949000))),
    ],
)
def test_the_ceilings_revalued_for_the_year_apply_and_the_articles_otherwise(
    assessment_date: datetime.date, ceilings: tuple[Money, Money]
) -> None:
    """
    For two children, 2020's revalued ceilings are 57,759 € and 80,831 € plus 5,775 €
    each; Catala revalues none for 2022, where D521-3's 55,950 € and 78,300 € plus 5,595
    € each apply.
    """
    household = household_of(children_born(2010, 2012), assessment_date)
    assert [
        (conclusion.first_ceiling, conclusion.second_ceiling)
        for conclusion in ResourceCeilingsProvision(household=household).conclusions
    ] == [ceilings]


@pytest.mark.parametrize(
    "resources, bracket",
    [
        (Money(cents=6930900), ResourceBracket.FIRST),
        (Money(cents=6930901), ResourceBracket.SECOND),
        (Money(cents=9238101), ResourceBracket.THIRD),
    ],
)
def test_the_bracket_is_set_by_the_ceilings_the_resources_reach(
    resources: Money, bracket: ResourceBracket
) -> None:
    """
    Resources up to a ceiling stay in its bracket; a cent more moves them up.
    """
    household = household_of(children_born(2010, 2012), resources=resources)
    assert [
        conclusion.bracket
        for conclusion in HouseholdBracketProvision(household=household).conclusions
    ] == [bracket]


# %% the right to family allowances


@pytest.mark.parametrize(
    "residence, birth_years, holds",
    [
        (Territory.METROPOLITAN_FRANCE, (2010,), False),
        (Territory.METROPOLITAN_FRANCE, (2010, 2012), True),
        (Territory.GUADELOUPE, (2010,), True),
        (Territory.MAYOTTE, (2010,), True),
    ],
)
def test_allowances_are_due_from_the_second_child_and_from_the_first_overseas_and_in_mayotte(
    residence: Territory, birth_years: tuple[int, ...], holds: bool
) -> None:
    """
    L521-1 asks for two children; L755-12 and the décret n°2002-423 for one.
    """
    household = household_of(children_born(*birth_years), residence=residence)
    assert [
        conclusion.holds
        for conclusion in BaseAllowanceRightProvision(household=household).conclusions
    ] == [holds]


# %% what is paid for each child by its rank


def test_four_children_are_paid_the_second_childs_rate_and_twice_the_later_childrens() -> (
    None
):
    """
    In the first bracket in 2020, 32 % of 414.40 € is 132.61 € and 41 % is 169.90 €.
    """
    household = household_of(children_born(2008, 2010, 2012, 2014))
    assert [
        conclusion.amount
        for conclusion in InitialBaseAmountProvision(household=household).conclusions
    ] == [Money(cents=13261 + 2 * 16990)]


def test_a_single_child_overseas_is_paid_the_single_child_rate() -> None:
    """
    D755-5 pays 5.88 % of 414.40 €, 24.37 €.
    """
    household = household_of(children_born(2010), residence=Territory.GUADELOUPE)
    assert [
        conclusion.amount
        for conclusion in InitialBaseAmountProvision(household=household).conclusions
    ] == [Money(cents=2437)]


@pytest.mark.parametrize(
    "assessment_date, had_child_before_2012, amount",
    [
        (datetime.date(2019, 6, 1), False, Money(cents=3499)),
        (datetime.date(2019, 6, 1), True, Money(cents=5728)),
        (datetime.date(2021, 6, 1), False, Money(cents=2439)),
    ],
)
def test_a_first_child_in_mayotte_is_paid_the_years_rate_or_the_fixed_amount(
    assessment_date: datetime.date, had_child_before_2012: bool, amount: Money
) -> None:
    """
    The annex's 8.47 % of 413.16 € in 2019, 57.28 € to a household with a child before
    2012, and article 7's 5.88 % of 414.81 € once the annex ends.
    """
    household = household_of(
        children_born(2010),
        assessment_date,
        residence=Territory.MAYOTTE,
        had_child_before_2012=had_child_before_2012,
    )
    assert [
        conclusion.amount
        for conclusion in FirstChildAmountProvision(household=household).conclusions
    ] == [amount]


# %% shared residences


def test_a_shared_residence_counts_the_child_for_half() -> None:
    """
    One of two children in a shared residence: 132.61 € times 1.5 over 2 is 99.46 €.
    """
    household = household_of(
        [
            child_born(datetime.date(2010, 1, 1)),
            child_born(
                datetime.date(2012, 1, 1),
                care=ChildCare.SHARED_RESIDENCE_SHARED_ALLOWANCE,
            ),
        ]
    )
    assert [
        conclusion.amount
        for conclusion in PaidBaseAllowanceProvision(household=household).conclusions
    ] == [Money(cents=9946)]
