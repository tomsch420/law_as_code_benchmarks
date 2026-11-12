"""
Tests of the employment tax of §§ `3306 <https://www.law.cornell.edu/uscode/text/26/3306>`__ and `3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__: employment, wages, employers and the
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
    EmployeeBenefitPlan,
    EmployeeBenefit,
    Service,
    World,
)
from law_as_code_benchmarks.sara.employment_exclusions import (
    ServiceForFamilyMemberTest,
)
from law_as_code_benchmarks.sara.employment_tax import (
    DaysOfEmploymentEmployerTest,
    EmployerDefinition,
    EmploymentDefinition,
    ExciseTaxOnEmployer,
    TotalWagesOfEmployer,
    WagesDefinition,
)
from law_as_code_benchmarks.sara.employment_tax_conclusions import (
    Employer,
    Employment,
    TotalWages,
)
from law_as_code_benchmarks.sara.family_status_conclusions import Dependent
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


@pytest.mark.parametrize(
    "identifier",
    [
        f"{predicate}_{suffix}"
        for predicate in (
            "s3306_a_1",
            "s3306_a_2_B",
            "s3306_b_2_A",
            "s3306_b_7",
            "s3306_b_10_A",
            "s3306_b_10_B",
            "s3306_b_11",
            "s3306_b_15",
            "s3306_c_A",
            "s3306_c_1",
            "s3306_c_2",
            "s3306_c_5",
            "s3306_c_10_A_i",
            "s3306_c_10_A_ii",
            "s3306_c_13",
            "s3306_c_21",
        )
        for suffix in ("pos", "neg")
    ],
)
def test_an_employment_tax_train_case_is_answered_as_its_test_goal_states(
    identifier: str, swipl: str
) -> None:
    """
    Each train case about a paragraph of `§ 3306 <https://www.law.cornell.edu/uscode/text/26/3306>`__ asked on its own is answered as its
    test goal states.
    """
    result = CaseResult.from_identifier(identifier, swipl)
    assert (result.is_modelled, result.is_correct) == (True, True)


# %% a world of one service


def world_of_one_service(
    payments: list[Payment] | None = None,
    benefit_plans: list[EmployeeBenefitPlan] | None = None,
    kinships: list[Kinship] | None = None,
) -> World:
    """:return: Bob working in 2017 for Alice, with *payments*, *benefit_plans* and *kinships*."""
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
    world.benefit_plans = benefit_plans or []
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
    `§ 3306(c)(5)(A) <https://www.law.cornell.edu/uscode/text/26/3306#c_5_A>`__: service in the employ of one's son or daughter is no employment.
    """
    world = world_of_one_service()
    service = world.services[0]
    world.kinships = [Kinship(parent=service.employee, child=service.employer)]
    assert EmploymentDefinition(world=world).conclusions == []


def test_domestic_service_in_a_private_home_with_little_cash_paid_is_not_employment() -> (
    None
):
    """
    `§ 3306(c)(2) <https://www.law.cornell.edu/uscode/text/26/3306#c_2>`__: domestic service in a private home in the United States, for which
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
    `§ 3306(b)(1) <https://www.law.cornell.edu/uscode/text/26/3306#b_1>`__: of a payment for employment, only the wage base is wages.
    """
    world = world_of_one_service()
    world.payments = [payment_for_work(world, WagesDefinition.wage_base + 2_000)]
    assert [wages.amount for wages in WagesDefinition(world=world).conclusions] == [
        WagesDefinition.wage_base
    ]


def test_each_payment_to_an_employee_is_wages_once() -> None:
    """
    Two payments to the same employee are two wages, not one for each pairing of the
    payment with an occurrence of the employee among the payees.
    """
    world = world_of_one_service()
    first, second = payment_for_work(world, 500), payment_for_work(world, 700)
    second.name = "second pay"
    world.payments = [first, second]
    assert sorted(
        wages.amount for wages in WagesDefinition(world=world).conclusions
    ) == sorted(payment.amount for payment in world.payments)


def test_a_payment_into_a_plan_for_death_of_the_employee_is_no_wages() -> None:
    """
    `§ 3306(b)(2)(C) <https://www.law.cornell.edu/uscode/text/26/3306#b_2_C>`__: a payment by the employer into a plan making provision for the
    employee in case of death is no wages.
    """
    world = world_of_one_service()
    service = world.services[0]
    plan = EmployeeBenefitPlan(
        name="life insurance",
        benefits={EmployeeBenefit.DEATH},
        beneficiaries=[service.employee],
    )
    payment = payment_for_work(world, 1_000)
    payment.recipient = plan
    world.benefit_plans = [plan]
    world.payments = [payment]
    assert WagesDefinition(world=world).conclusions == []


def test_a_payment_into_a_sickness_plan_for_a_dependent_of_the_employee_is_no_wages() -> (
    None
):
    """
    `§ 3306(b)(2)(A) <https://www.law.cornell.edu/uscode/text/26/3306#b_2_A>`__: a payment by the employer into a plan making provision for a
    dependent of the employee in case of sickness is no wages.
    """
    world = world_of_one_service()
    service = world.services[0]
    child = Party(name="carol")
    plan = EmployeeBenefitPlan(
        name="health insurance",
        benefits={EmployeeBenefit.SICKNESS},
        beneficiaries=[child],
    )
    payment = payment_for_work(world, 1_000)
    payment.recipient = plan
    world.benefit_plans = [plan]
    world.payments = [payment]
    world.stated_conclusions = [
        Dependent(individual=child, taxpayer=service.employee, year=2017)
    ]
    assert WagesDefinition(world=world).conclusions == []


# %% employment on a day


def test_service_for_ones_child_is_excluded_whatever_the_day() -> None:
    """
    `§ 3306(c)(5) <https://www.law.cornell.edu/uscode/text/26/3306#c_5>`__ excludes service for one's child on any day, so a goal leaving the
    day open has an answer.
    """
    world = world_of_one_service()
    service = world.services[0]
    world.kinships = [Kinship(parent=service.employee, child=service.employer)]
    assert ServiceForFamilyMemberTest(world=world).holds(
        CompoundTerm(
            functor=ServiceForFamilyMemberTest.predicate,
            arguments=("work", "alice", "bob", None),
        )
    )


# %% employers


def test_a_person_paying_enough_wages_is_an_employer_under_section_3306_a() -> None:
    """
    A goal of `§ 3306(a) <https://www.law.cornell.edu/uscode/text/26/3306#a>`__ itself, naming the employer and the year, holds for a person
    paying wages of $1,500 or more.
    """
    world = world_of_one_service()
    world.payments = [payment_for_work(world, 2_000)]
    world.calendar_years = [CalendarYear(number=2017)]
    assert EmployerDefinition(world=world).holds(
        CompoundTerm(functor=EmployerDefinition.predicate, arguments=("alice", 2017))
    )


def employment_on(service: Service, workday: datetime.date) -> Employment:
    """:return: The stated conclusion that *service* is employment on *workday*."""
    return Employment(service=service, workday=workday)


def test_days_in_one_calendar_week_count_as_one_week() -> None:
    """
    `§ 3306(a)(1)(B) <https://www.law.cornell.edu/uscode/text/26/3306#a_1_B>`__: days of employment from Monday to Sunday of one week count as one
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
    `§ 3306(a)(1)(B) <https://www.law.cornell.edu/uscode/text/26/3306#a_1_B>`__: employing someone on ten days, each in a different week, makes an
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
    `§ 3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__: the tax is rounded to whole dollars, half a dollar away from zero, as
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


def test_total_wages_run_over_the_calendar_year_they_are_paid_in() -> None:
    """
    The total wages an employer paid in a year run from January 1 to December 31 of it,
    each a day.
    """
    world = world_of_one_service()
    world.payments = [payment_for_work(world, 1_000)]
    world.calendar_years = [CalendarYear(number=2017)]
    [total_wages] = TotalWagesOfEmployer(world=world).conclusions
    assert (total_wages.first_day, total_wages.last_day) == (
        datetime.date(2017, 1, 1),
        datetime.date(2017, 12, 31),
    )


def test_a_stated_conclusion_holds_alongside_inferred_ones() -> None:
    """
    A conclusion a case states counts among the provision's conclusions as one its rule
    infers does.
    """
    world = world_of_one_service()
    stated = Employment(service=world.services[0], workday=datetime.date(2017, 3, 1))
    world.stated_conclusions = [stated]
    assert stated in EmploymentDefinition(world=world).conclusions
