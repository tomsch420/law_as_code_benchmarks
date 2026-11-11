"""
Tests of the employment tax of §§ 3306 and 3301: employment, wages, employers and the
excise tax on them.
"""

from __future__ import annotations

import datetime

import pytest

from law_as_code_benchmarks.sara.domain import (
    CalendarYear,
    Country,
    DomesticServicePlace,
    Kinship,
    LaborKind,
    Party,
    Payment,
    Place,
    Plan,
    PlanPurpose,
    Service,
    World,
)
from law_as_code_benchmarks.sara.employment_tax import (
    DaysOfEmploymentEmployerTest,
    EmploymentDefinition,
    ExciseTaxOnEmployer,
    WagesDefinition,
)
from law_as_code_benchmarks.sara.employment_tax_conclusions import (
    Employer,
    Employment,
    TotalWages,
)
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm
from law_as_code_benchmarks.sara.scoring import CaseResult

# %% SARA's cases


@pytest.mark.parametrize(
    "identifier",
    [
        f"{predicate}_{suffix}"
        for predicate in ("s3306_a_1_B", "s3306_a_3", "s3306_b_2_C", "s3301")
        for suffix in ("pos", "neg")
    ],
)
def test_an_employment_tax_case_is_answered_as_its_test_goal_states(
    identifier: str, swipl: str
) -> None:
    """
    Each test case about the employment tax is answered as its test goal states.
    """
    result = CaseResult.from_identifier(identifier, swipl)
    assert (result.is_modelled, result.is_correct) == (True, True)


# %% a world of one service


def world_of_one_service(
    payments: list[Payment] | None = None,
    plans: list[Plan] | None = None,
    kinships: list[Kinship] | None = None,
) -> World:
    """:return: Bob working in 2017 for Alice, with *payments*, *plans* and *kinships*."""
    world = World(united_states=Country(name="usa"))
    world.services = [
        Service(
            name="work",
            employee=Party(name="bob"),
            employer=Party(name="alice"),
            start=datetime.date(2017, 1, 1),
            end=datetime.date(2017, 12, 31),
        )
    ]
    world.payments = payments or []
    world.plans = plans or []
    world.kinships = kinships or []
    return world


def payment_for_work(world: World, amount: float) -> Payment:
    """:return: Alice paying Bob *amount* for his work in *world*, on the last day of 2017."""
    service = world.services[0]
    return Payment(
        name="pay",
        payer=service.employer,
        recipient=service.employee,
        amount=amount,
        day=datetime.date(2017, 12, 31),
        service=service,
    )


# %% employment


def test_service_for_ones_child_is_not_employment() -> None:
    """
    § 3306(c)(5)(A): service in the employ of one's son or daughter is no employment.
    """
    world = world_of_one_service()
    service = world.services[0]
    world.kinships = [Kinship(parent=service.employee, child=service.employer)]
    assert EmploymentDefinition(world=world).conclusions == []


def test_domestic_service_in_a_private_home_with_little_cash_paid_is_not_employment() -> (
    None
):
    """
    § 3306(c)(2): domestic service in a private home in the United States, for which
    less than $1,000 in cash was paid, is no employment.
    """
    world = world_of_one_service()
    service = world.services[0]
    service.kinds = {LaborKind.DOMESTIC_SERVICE}
    service.places = [
        Place(name=DomesticServicePlace.PRIVATE_HOME),
        Place(name="usa", country=world.united_states),
    ]
    world.payments = [payment_for_work(world, 300)]
    world.calendar_years = [CalendarYear(number=2017)]
    assert EmploymentDefinition(world=world).conclusions == []


# %% wages


def test_wages_are_counted_up_to_the_wage_base() -> None:
    """
    § 3306(b)(1): of a payment for employment, only the wage base is wages.
    """
    world = world_of_one_service()
    world.payments = [payment_for_work(world, WagesDefinition.wage_base + 2_000)]
    assert [wages.amount for wages in WagesDefinition(world=world).conclusions] == [
        WagesDefinition.wage_base
    ]


def test_a_payment_into_a_plan_for_death_of_the_employee_is_no_wages() -> None:
    """
    § 3306(b)(2)(C): a payment by the employer into a plan making provision for the
    employee in case of death is no wages.
    """
    world = world_of_one_service()
    service = world.services[0]
    plan = Plan(
        name="life insurance",
        purposes={PlanPurpose.DEATH},
        beneficiaries=[service.employee],
    )
    payment = payment_for_work(world, 1_000)
    payment.recipient = plan
    world.plans = [plan]
    world.payments = [payment]
    assert WagesDefinition(world=world).conclusions == []


# %% employers


def employment_on(service: Service, workday: datetime.date) -> Employment:
    """:return: The stated conclusion that *service* is employment on *workday*."""
    return Employment(service=service, workday=workday)


def test_days_in_one_calendar_week_count_as_one_week() -> None:
    """
    § 3306(a)(1)(B): days of employment from Monday to Sunday of one week count as one
    week, though ten days in all.
    """
    world = world_of_one_service()
    service = world.services[0]
    monday = datetime.date(2017, 1, 2)
    workdays = [monday + datetime.timedelta(weeks=week) for week in range(9)]
    workdays.append(monday + datetime.timedelta(weeks=8, days=6))
    world.stated_conclusions = [employment_on(service, day) for day in workdays]
    world.calendar_years = [CalendarYear(number=2017)]
    assert DaysOfEmploymentEmployerTest(world=world).conclusions == []


def test_ten_days_in_ten_calendar_weeks_make_an_employer() -> None:
    """
    § 3306(a)(1)(B): employing someone on ten days, each in a different week, makes an
    employer.
    """
    world = world_of_one_service()
    service = world.services[0]
    sunday = datetime.date(2017, 1, 1)
    world.stated_conclusions = [
        employment_on(service, sunday + datetime.timedelta(weeks=week))
        for week in range(DaysOfEmploymentEmployerTest.least_number_of_days)
    ]
    world.calendar_years = [CalendarYear(number=2017)]
    goal = CompoundTerm(
        functor=DaysOfEmploymentEmployerTest.predicate,
        arguments=(service.employer.name, None, None, 2017),
    )
    assert DaysOfEmploymentEmployerTest(world=world).holds(goal)


# %% the excise tax


def test_the_excise_tax_rounds_half_a_dollar_up() -> None:
    """
    § 3301: the tax is rounded to whole dollars, half a dollar away from zero, as
    Prolog's ``round`` does.
    """
    world = world_of_one_service()
    alice = world.services[0].employer
    wages = 0.5 / ExciseTaxOnEmployer.rate
    world.stated_conclusions = [
        Employer(party=alice, year=2017),
        TotalWages(
            employer=alice,
            amount=wages,
            first_day=datetime.date(2017, 1, 1),
            last_day=datetime.date(2017, 12, 31),
        ),
    ]
    assert [tax.amount for tax in ExciseTaxOnEmployer(world=world).conclusions] == [1]


def test_a_stated_conclusion_holds_alongside_inferred_ones() -> None:
    """
    A conclusion a case states counts among the provision's conclusions as one its rule
    infers does.
    """
    world = world_of_one_service()
    stated = Employment(service=world.services[0], workday=datetime.date(2017, 3, 1))
    world.stated_conclusions = [stated]
    assert stated in EmploymentDefinition(world=world).conclusions
