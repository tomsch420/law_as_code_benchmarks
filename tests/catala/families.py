"""
Children and households the tests of the family benefits share.
"""

from __future__ import annotations

import datetime

from law_as_code_benchmarks.catala.domain import (
    Child,
    ChildCare,
    Household,
    Money,
    Territory,
)

# %% children


def child_born(
    birth_date: datetime.date,
    monthly_pay: Money = Money(cents=0),
    care: ChildCare = ChildCare.EFFECTIVE_AND_PERMANENT,
    receives_personal_housing_aid: bool = False,
) -> Child:
    """:return: A child born on *birth_date* who already gave a right to family allowances, numbered by the birth date."""
    return Child(
        identifier=birth_date.toordinal(),
        birth_date=birth_date,
        monthly_pay=monthly_pay,
        has_opened_family_allowance=True,
        care=care,
        receives_personal_housing_aid=receives_personal_housing_aid,
    )


def children_born(*years: int) -> list[Child]:
    """:return: A child born on January 1 of each of *years*."""
    return [child_born(datetime.date(year, 1, 1)) for year in years]


# %% households


def household_of(
    children: list[Child],
    assessment_date: datetime.date = datetime.date(2020, 5, 1),
    residence: Territory = Territory.METROPOLITAN_FRANCE,
    resources: Money = Money(cents=3000000),
    had_child_before_2012: bool = False,
) -> Household:
    """:return: A household of *children*, by default assessed on May 1, 2020, in metropolitan France with 30,000 € of resources."""
    return Household(
        assessment_date=assessment_date,
        residence=residence,
        children=children,
        resources=resources,
        had_child_before_2012=had_child_before_2012,
    )
