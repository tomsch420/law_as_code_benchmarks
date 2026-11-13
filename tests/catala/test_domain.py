"""
Tests of the domain model of the family benefits: money, birthdays and households.
"""

from __future__ import annotations

import datetime
from fractions import Fraction

import pytest

from law_as_code_benchmarks.catala.domain import (
    Child,
    Household,
    Territory,
)
from law_as_code_benchmarks.catala.exceptions import AmbiguousBirthday
from law_as_code_benchmarks.catala.money import Money

# %% money


def test_money_times_a_rate_is_rounded_to_the_cent() -> None:
    """
    32 % of 414.40 € is 132.608 €, paid as 132.61 €.
    """
    assert Money(cents=41440) * Fraction(32, 100) == Money(cents=13261)


@pytest.mark.parametrize("cents", [1, -1])
def test_half_a_cent_is_rounded_away_from_zero(cents: int) -> None:
    """
    Half of one cent rounds to one cent, of either sign.
    """
    assert Money(cents=cents) * Fraction(1, 2) == Money(cents=cents)


@pytest.mark.parametrize(
    "cents, units", [(36898, 36900), (36849, 36800), (-50, -100), (49, 0)]
)
def test_money_is_rounded_to_whole_units_halves_away_from_zero(
    cents: int, units: int
) -> None:
    """
    Catala's ``arrondi`` rounds money to the nearest unit, halves away from zero.
    """
    assert Money(cents=cents).rounded_to_units() == Money(cents=units)


def test_money_leaves_an_operand_it_does_not_know_to_the_operand() -> None:
    """
    Money gives way to an operand that is neither money nor a number, as a symbolic one
    is.
    """
    assert Money(cents=1).__mul__("x") is NotImplemented
    assert Money(cents=1).__add__(1) is NotImplemented
    assert Money(cents=1).__sub__(1) is NotImplemented


def test_amounts_sum_from_zero() -> None:
    """
    :func:`sum` adds amounts, starting from the integer 0.
    """
    assert sum([Money(cents=150), Money(cents=250)]) == Money(cents=400)


# %% children


def test_a_birthday_falls_on_the_same_day_years_later() -> None:
    """
    A child born on March 3, 2004, turns 20 on March 3, 2024.
    """
    child = Child(
        identifier=1,
        birth_date=datetime.date(2004, 3, 3),
        monthly_pay=Money.zero,
        has_opened_family_allowance=True,
    )
    assert Child.birthday(child, 20) == datetime.date(2024, 3, 3)


def test_a_birthday_on_february_29_in_a_year_without_one_is_refused() -> None:
    """
    A child born on February 29, 2004, has no day in 2005 to turn 1 on.
    """
    child = Child(
        identifier=1,
        birth_date=datetime.date(2004, 2, 29),
        monthly_pay=Money.zero,
        has_opened_family_allowance=True,
    )
    with pytest.raises(AmbiguousBirthday):
        Child.birthday(child, 1)


# %% households


def test_the_oldest_child_is_the_first_born_on_the_earliest_day() -> None:
    """
    Of twins born before a younger sibling, the first named is the oldest.
    """
    younger, first_twin, second_twin = [
        Child(
            identifier=identifier,
            birth_date=birth_date,
            monthly_pay=Money.zero,
            has_opened_family_allowance=True,
        )
        for identifier, birth_date in [
            (1, datetime.date(2012, 1, 1)),
            (2, datetime.date(2010, 6, 1)),
            (3, datetime.date(2010, 6, 1)),
        ]
    ]
    household = Household(
        assessment_date=datetime.date(2020, 5, 1),
        residence=Territory.METROPOLITAN_FRANCE,
        children=[younger, first_twin, second_twin],
    )
    assert household.oldest_child is first_twin
