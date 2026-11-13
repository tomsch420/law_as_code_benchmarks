"""
Tests of the amounts in force over the periods the family benefits are computed for.
"""

from __future__ import annotations

import datetime

import pytest

from law_as_code_benchmarks.catala.amounts import MinimumWages, MonthlyBases
from law_as_code_benchmarks.catala.domain import Territory

# %% one amount a month


def first_days_of_months(
    first: datetime.date, last: datetime.date
) -> list[datetime.date]:
    """:return: The first day of every month from *first*'s to *last*'s."""
    return [
        datetime.date(year, month, 1)
        for year in range(first.year, last.year + 1)
        for month in range(1, 13)
        if first <= datetime.date(year, month, 1) <= last
    ]


@pytest.mark.parametrize(
    "day", first_days_of_months(datetime.date(2006, 1, 1), datetime.date(2026, 12, 1))
)
def test_one_monthly_base_is_in_force_each_month_from_2006(day: datetime.date) -> None:
    """
    The monthly bases leave no month from 2006 to 2026 without one, and none with two.
    """
    assert len([base for base in MonthlyBases if base.value.period.contains(day)]) == 1


@pytest.mark.parametrize(
    "day", first_days_of_months(datetime.date(2005, 7, 1), datetime.date(2026, 12, 1))
)
def test_one_minimum_wage_is_in_force_outside_mayotte_each_month_from_july_2005(
    day: datetime.date,
) -> None:
    """
    The minimum wages leave no month from July 2005 to 2026 without one in metropolitan
    France, and none with two.
    """
    assert (
        len(
            [
                wage
                for wage in MinimumWages
                if wage.value.period.contains(day)
                and Territory.METROPOLITAN_FRANCE in wage.value.territories
            ]
        )
        == 1
    )
