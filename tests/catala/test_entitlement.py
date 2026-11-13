"""
Tests of the right a child gives to family benefits.
"""

from __future__ import annotations

import datetime

import pytest

from law_as_code_benchmarks.catala.domain import (
    SchoolingStage,
    Territory,
)
from law_as_code_benchmarks.catala.entitlement import (
    EntitledChildrenProvision,
    FamilyBenefitEntitlementProvision,
    OverseasRegimeProvision,
    PayCeilingProvision,
    SchoolingStageProvision,
)
from law_as_code_benchmarks.catala.money import Money

from .families import child_born, household_of

# %% the overseas regime and the pay ceiling


@pytest.mark.parametrize(
    "residence, holds",
    [
        (Territory.GUADELOUPE, True),
        (Territory.MAYOTTE, False),
        (Territory.METROPOLITAN_FRANCE, False),
    ],
)
def test_the_overseas_regime_holds_in_the_departments_of_l751_1(
    residence: Territory, holds: bool
) -> None:
    """
    L751-1 names Guadeloupe among its departments, Mayotte not.
    """
    household = household_of([], residence=residence)
    assert [
        regime.holds
        for regime in OverseasRegimeProvision(household=household).conclusions
    ] == [holds]


@pytest.mark.parametrize(
    "residence, ceiling",
    [
        (Territory.METROPOLITAN_FRANCE, Money(cents=94302)),
        (Territory.MAYOTTE, Money(cents=71149)),
    ],
)
def test_the_pay_ceiling_is_169_hours_at_55_percent_of_the_minimum_wage(
    residence: Territory, ceiling: Money
) -> None:
    """
    In 2020, 55 % of 10.15 € is 5.58 €, times 169 is 943.02 €; of Mayotte's 7.66 €,
    4.21 €, times 169 is 711.49 €.
    """
    household = household_of([], residence=residence)
    assert [
        conclusion.amount
        for conclusion in PayCeilingProvision(household=household).conclusions
    ] == [ceiling]


# %% compulsory schooling


@pytest.mark.parametrize(
    "birth_date, stage",
    [
        (datetime.date(2017, 5, 1), SchoolingStage.BEFORE),
        (datetime.date(2017, 4, 30), SchoolingStage.DURING),
        (datetime.date(2004, 5, 1), SchoolingStage.DURING),
        (datetime.date(2004, 4, 30), SchoolingStage.AFTER),
    ],
)
def test_compulsory_schooling_runs_from_the_day_after_the_third_birthday_to_the_day_after_the_sixteenth(
    birth_date: datetime.date, stage: SchoolingStage
) -> None:
    """
    On May 1, 2020, a child turning 3 that day is before compulsory schooling, one who
    turned 3 the day before is in it, and so on at 16.
    """
    household = household_of([child_born(birth_date)])
    assert [
        conclusion.stage
        for conclusion in SchoolingStageProvision(household=household).conclusions
    ] == [stage]


def test_a_stated_schooling_stage_holds_over_the_birth_date() -> None:
    """
    A 13-year-old the case states past compulsory schooling is past it.
    """
    child = child_born(datetime.date(2007, 1, 1))
    child.stated_schooling_stage = SchoolingStage.AFTER
    household = household_of([child])
    assert [
        conclusion.stage
        for conclusion in SchoolingStageProvision(household=household).conclusions
    ] == [SchoolingStage.AFTER]


# %% the right to family benefits


@pytest.mark.parametrize(
    "birth_date, monthly_pay, entitled",
    [
        (datetime.date(2010, 1, 1), Money(cents=200000), True),
        (datetime.date(2003, 1, 1), Money(cents=94302), True),
        (datetime.date(2003, 1, 1), Money(cents=94303), False),
        (datetime.date(2000, 5, 2), Money(cents=0), True),
        (datetime.date(2000, 5, 1), Money(cents=0), False),
    ],
)
def test_a_child_is_entitled_through_compulsory_schooling_and_after_it_up_to_the_pay_ceiling_and_age_limit(
    birth_date: datetime.date, monthly_pay: Money, entitled: bool
) -> None:
    """
    On May 1, 2020, any pay keeps a 10-year-old entitled; after compulsory schooling,
    pay above 943.02 € ends it, and so does the twentieth birthday.
    """
    household = household_of([child_born(birth_date, monthly_pay)])
    assert [
        conclusion.holds
        for conclusion in FamilyBenefitEntitlementProvision(
            household=household
        ).conclusions
    ] == [entitled]


@pytest.mark.parametrize(
    "birth_date", [datetime.date(2010, 1, 1), datetime.date(2003, 1, 1)]
)
def test_housing_aid_in_the_childs_own_name_excepts_the_child_at_any_stage(
    birth_date: datetime.date,
) -> None:
    """
    L821-3 of the Code de la construction et de l'habitation excepts a child in
    compulsory schooling and one past it alike.
    """
    child = child_born(birth_date, receives_personal_housing_aid=True)
    household = household_of([child])
    assert [
        conclusion.holds
        for conclusion in FamilyBenefitEntitlementProvision(
            household=household
        ).conclusions
    ] == [False]


def test_only_entitled_children_are_counted() -> None:
    """
    A child earning above the pay ceiling is left out of the entitled children.
    """
    entitled = child_born(datetime.date(2010, 1, 1))
    earning = child_born(datetime.date(2003, 1, 1), Money(cents=110000))
    household = household_of([entitled, earning])
    assert [
        conclusion.children
        for conclusion in EntitledChildrenProvision(household=household).conclusions
    ] == [[entitled]]
