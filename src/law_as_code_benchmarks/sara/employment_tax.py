"""
The employment tax as rules over the domain model: who is an *employer* (§ 3306(a)),
what is *wages* (§ 3306(b)) and *employment* (§ 3306(c)), and the excise tax of § 3301.

Days of employment are only those a case states, as SARA's program leaves the day open
wherever §§ 3306 and 3301 ask about employment.
"""

from __future__ import annotations

from dataclasses import dataclass

from krrood.entity_query_language.factories import (
    an,
    and_,
    count,
    entity,
    exists,
    in_,
    inference,
    not_,
    or_,
    variable,
)
from krrood.entity_query_language.factories import sum as total
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.sara.domain import (
    CalendarYear,
    Death,
    DomesticServicePlace,
    Kinship,
    LaborKind,
    Marriage,
    Party,
    Payment,
    Plan,
    PlanPurpose,
    Service,
    Termination,
)
from law_as_code_benchmarks.sara.employment_exclusions import (
    AdmittedAlienCondition,
    ForeignGovernmentExclusion,
    InternationalOrganizationExclusion,
    ServiceAbroadInclusion,
    StateExclusion,
    UnitedStatesGovernmentExclusion,
)
from law_as_code_benchmarks.sara.employment_tax_conclusions import (
    AnnualWagesOfEmployee,
    Employer,
    EmployerByAgriculturalWages,
    EmployerByDaysOfEmployment,
    EmployerByWages,
    EmployerOfAgriculturalLabor,
    EmployerOfDomesticService,
    Employment,
    ExciseTax,
    PlanForDeath,
    TotalWages,
    Wages,
)
from law_as_code_benchmarks.sara.provision import Provision, SaraPredicate

# %% employment


@dataclass
class EmployerOfAgriculturalLaborTest(Provision[EmployerOfAgriculturalLabor]):
    """
    § 3306(c)(1)(A)(i): a person who, in the calendar year or the year before, paid
    $20,000 or more in cash to individuals employed in agricultural labor.
    """

    @classproperty
    def threshold(cls) -> float:
        """
        The least cash a person has to have paid.
        """
        return 20_000

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EMPLOYER_OF_AGRICULTURAL_LABOR`.
        """
        return SaraPredicate.EMPLOYER_OF_AGRICULTURAL_LABOR

    def query(self) -> Query:
        payment = variable(Payment, domain=self.world.payments)
        year = variable(CalendarYear, domain=self.world.calendar_years)
        return an(
            entity(
                inference(EmployerOfAgriculturalLabor)(
                    party=payment.payer, year=year.number, payments=payment
                )
            )
            .where(
                in_(LaborKind.AGRICULTURAL_LABOR, payment.service.kinds),
                payment.service.employer == payment.payer,
                payment.service.employee == payment.recipient,
                payment.is_in_cash(),
                payment.day >= year.opening_day_of_preceding_year,
                payment.day <= year.closing_day,
            )
            .grouped_by(payment.payer, year.number)
            .having(total(payment.amount, default=0) >= self.threshold)
        )


@dataclass
class EmploymentDefinition(Provision[Employment]):
    """
    § 3306(c): service within the United States, or abroad for an American employer,
    that no paragraph of § 3306(c) excludes, for the calendar year it ends in.

    The paragraphs that exclude service on a given day, (5) for a spouse or a child
    under 21, (10), (13) and (21), never apply, as these rules give no day.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EMPLOYMENT`.
        """
        return SaraPredicate.EMPLOYMENT

    def query(self) -> Query:
        located_services = self.located_services()
        service = variable(Service, domain=located_services)
        return an(
            entity(inference(Employment)(service=service, year=service.end.year)).where(
                not_(in_(service, self.services_excluded_by_employer())),
                not_(self.is_excluded_agricultural_labor(service)),
                not_(in_(service, self.excluded_domestic_services(located_services))),
                not_(self.is_service_for_child(service)),
            )
        )

    def located_services(self) -> list[Service]:
        """
        :return: The services ending in a stated year that are performed within the
            United States, as one at no stated place is taken to be, or abroad under §
            3306(c)(B).
        """
        service = variable(
            Service,
            domain=[service for service in self.world.services if service.end],
        )
        return an(
            entity(service).where(
                or_(
                    service.places == [],
                    in_(self.world.united_states, service.countries()),
                    in_(service, self.services_abroad()),
                )
            )
        ).tolist()

    def services_abroad(self) -> list[Service]:
        """:return: The services § 3306(c)(B) brings into employment though performed abroad."""
        return [
            conclusion.service
            for conclusion in ServiceAbroadInclusion(world=self.world).conclusions
        ]

    def services_excluded_by_employer(self) -> list[Service]:
        """:return: The services § 3306(c)(6), (7), (11) and (16) exclude for whom they are performed for."""
        return [
            conclusion.service
            for exclusion in (
                UnitedStatesGovernmentExclusion,
                StateExclusion,
                ForeignGovernmentExclusion,
                InternationalOrganizationExclusion,
            )
            for conclusion in exclusion(world=self.world).conclusions
        ]

    def is_excluded_agricultural_labor(self, service: Service) -> Query:
        """
        § 3306(c)(1): agricultural labor, unless performed for a person meeting
        (1)(A)(i) in its year and not by an alien admitted to perform it.
        """
        employer = variable(
            EmployerOfAgriculturalLabor,
            domain=EmployerOfAgriculturalLaborTest(world=self.world).conclusions,
        )
        return and_(
            in_(LaborKind.AGRICULTURAL_LABOR, service.kinds),
            not_(
                and_(
                    exists(
                        employer,
                        and_(
                            employer.party == service.employer,
                            employer.year == service.end.year,
                        ),
                    ),
                    in_(
                        service,
                        [
                            conclusion.service
                            for conclusion in AdmittedAlienCondition(
                                world=self.world
                            ).conclusions
                        ],
                    ),
                )
            ),
        )

    def excluded_domestic_services(
        self, located_services: list[Service]
    ) -> list[Service]:
        """
        § 3306(c)(2): domestic service in a private home, local college club or local
        chapter of a college fraternity or sorority, unless performed for an employer
        under § 3306(a)(3) in its year.

        :param located_services: The services to look among.
        :return: The services excluded.
        """
        service = variable(Service, domain=located_services)
        domestic_services = an(
            entity(service).where(
                in_(LaborKind.DOMESTIC_SERVICE, service.kinds),
                service.is_performed_at_any(list(DomesticServicePlace)),
            )
        ).tolist()
        if not domestic_services:
            return []
        domestic_service = variable(Service, domain=domestic_services)
        employer = variable(
            EmployerOfDomesticService,
            domain=DomesticServiceEmployerTest(world=self.world).conclusions,
        )
        return an(
            entity(domestic_service).where(
                not_(
                    exists(
                        employer,
                        and_(
                            employer.party == domestic_service.employer,
                            employer.year == domestic_service.end.year,
                        ),
                    )
                )
            )
        ).tolist()

    def is_service_for_child(self, service: Service) -> Query:
        """
        § 3306(c)(5)(A): service performed by an individual in the employ of their son
        or daughter.
        """
        kinship = variable(Kinship, domain=self.world.kinships)
        return exists(
            kinship,
            and_(kinship.parent == service.employee, kinship.child == service.employer),
        )


# %% wages


@dataclass
class WagesDefinition(Provision[Wages]):
    """
    § 3306(b): a payment for employment, up to the first $7,000 of it, that no paragraph
    of § 3306(b) excludes.

    Paragraphs (2) and (10) cover payments to the employee only, not to their
    dependents; (7) is not modelled.
    """

    @classproperty
    def wage_base(cls) -> float:
        """
        § 3306(b)(1): the most of a payment that is wages.
        """
        return 7_000

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.WAGES`.
        """
        return SaraPredicate.WAGES

    def query(self) -> Query:
        payment = variable(
            Payment,
            domain=[
                payment
                for payment in self.world.payments
                if payment.service is not None and payment.service.end
            ],
        )
        payee = variable(
            Party,
            domain=[
                payee for payment in self.world.payments for payee in payment.payees()
            ],
        )
        employment = variable(
            Employment, domain=EmploymentDefinition(world=self.world).conclusions
        )
        return an(
            entity(
                inference(Wages)(
                    amount=payment.amount_up_to(self.wage_base),
                    payment=payment,
                    service=payment.service,
                    payee=payee,
                )
            ).where(
                in_(payee, payment.payees()),
                exists(
                    employment,
                    and_(
                        employment.service == payment.service,
                        or_(
                            employment.year == None,
                            employment.year == payment.service.end.year,
                        ),
                    ),
                ),
                not_(self.is_plan_payment_for_sickness_or_death(payment, payee)),
                not_(self.is_payment_upon_termination(payment, payee)),
                not_(self.is_agricultural_labor_paid_in_kind(payment)),
                not_(self.is_payment_to_survivor(payment, payee)),
            )
        )

    def is_plan_payment_for_sickness_or_death(
        self, payment: Payment, payee: Party
    ) -> Query:
        """
        § 3306(b)(2)(A) and (C): a payment by the employer into or from a plan making
        provision for the employee in case of sickness, accident disability or death.
        """
        plan = variable(Plan, domain=self.world.plans)
        return and_(
            payment.service.employer == payment.payer,
            payment.service.employee == payee,
            exists(
                plan,
                and_(
                    in_(plan, payment.plans()),
                    in_(payee, plan.beneficiaries),
                    plan.makes_any_provision(
                        {
                            PlanPurpose.SICKNESS,
                            PlanPurpose.ACCIDENT_DISABILITY,
                            PlanPurpose.DEATH,
                        }
                    ),
                ),
            ),
        )

    def is_payment_upon_termination(self, payment: Payment, payee: Party) -> Query:
        """
        § 3306(b)(10): a payment by the employer to the employee from a plan for its
        employees, upon or after it ended their service for their death or disability.
        """
        termination = variable(Termination, domain=self.world.terminations)
        return and_(
            payment.service.employer == payment.payer,
            payment.service.employee == payee,
            payment.plan_drawn_on.sponsor == payment.payer,
            payment.plan_drawn_on.makes_any_provision(
                {PlanPurpose.EMPLOYEES_OR_DEPENDENTS}
            ),
            exists(
                termination,
                and_(
                    termination.service == payment.service,
                    termination.employer == payment.payer,
                    termination.ending_day() <= payment.day,
                    termination.is_for_death_or_disability_of(payee),
                ),
            ),
        )

    def is_agricultural_labor_paid_in_kind(self, payment: Payment) -> Query:
        """
        § 3306(b)(11): remuneration for agricultural labor paid in a medium other than
        cash.
        """
        return and_(
            in_(LaborKind.AGRICULTURAL_LABOR, payment.service.purposes),
            payment.service.employer == payment.payer,
            payment.service.employee == payment.recipient,
            payment.is_in_other_medium_than_cash(),
        )

    def is_payment_to_survivor(self, payment: Payment, payee: Party) -> Query:
        """
        § 3306(b)(15): a payment by the employer to the surviving spouse of the employee
        after the calendar year the employee died in.
        """
        death = variable(Death, domain=self.world.deaths)
        marriage = variable(Marriage, domain=self.world.marriages)
        return and_(
            payment.service.employer == payment.payer,
            exists(
                death,
                and_(
                    death.person == payment.service.employee,
                    death.day.year < payment.day.year,
                    exists(
                        marriage,
                        and_(
                            in_(death.person, marriage.spouses),
                            in_(payee, marriage.spouses),
                            or_(marriage.end == None, marriage.end == death.day),
                        ),
                    ),
                ),
            ),
        )


@dataclass
class PlanForDeathTest(Provision[PlanForDeath]):
    """
    § 3306(b)(2)(C): a plan making provision for employees in case of death.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.PLAN_FOR_DEATH`.
        """
        return SaraPredicate.PLAN_FOR_DEATH

    def query(self) -> Query:
        plan = variable(Plan, domain=self.world.plans)
        return an(
            entity(inference(PlanForDeath)(plan=plan)).where(
                in_(PlanPurpose.DEATH, plan.purposes)
            )
        )


# %% employers


@dataclass
class WagesEmployerTest(Provision[EmployerByWages]):
    """
    § 3306(a)(1)(A): a person who, in the calendar year or the year before, paid wages
    of $1,500 or more, those for agricultural labor and domestic service aside.
    """

    @classproperty
    def threshold(cls) -> float:
        """
        The least wages a person has to have paid.
        """
        return 1_500

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EMPLOYER_BY_WAGES`.
        """
        return SaraPredicate.EMPLOYER_BY_WAGES

    def query(self) -> Query:
        wages = variable(Wages, domain=WagesDefinition(world=self.world).conclusions)
        year = variable(CalendarYear, domain=self.world.calendar_years)
        return an(
            entity(
                inference(EmployerByWages)(
                    party=wages.payment.payer, year=year.number, wages=wages
                )
            )
            .where(
                not_(in_(LaborKind.AGRICULTURAL_LABOR, wages.service.purposes)),
                not_(in_(LaborKind.DOMESTIC_SERVICE, wages.service.purposes)),
                wages.payment.day >= year.opening_day_of_preceding_year,
                wages.payment.day <= year.closing_day,
            )
            .grouped_by(wages.payment.payer, year.number)
            .having(total(wages.amount, default=0) >= self.threshold)
        )


@dataclass
class DaysOfEmploymentEmployerTest(Provision[EmployerByDaysOfEmployment]):
    """
    § 3306(a)(1)(B): a person who, on each of some 10 days in the calendar year or the
    year before, each in a different calendar week, employed someone in employment other
    than agricultural labor and domestic service.
    """

    @classproperty
    def least_number_of_days(cls) -> int:
        """
        How many days, each in a different week, a person has to have employed someone
        on.
        """
        return 10

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EMPLOYER_BY_DAYS_OF_EMPLOYMENT`.
        """
        return SaraPredicate.EMPLOYER_BY_DAYS_OF_EMPLOYMENT

    def query(self) -> Query:
        employment = variable(
            Employment,
            domain=[
                employment
                for employment in EmploymentDefinition(world=self.world).conclusions
                if employment.workday is not None
            ],
        )
        year = variable(CalendarYear, domain=self.world.calendar_years)
        return an(
            entity(
                inference(EmployerByDaysOfEmployment)(
                    party=employment.service.employer,
                    year=year.number,
                    workdays=employment.workday,
                    employees=employment.service.employee,
                )
            )
            .where(
                not_(in_(LaborKind.AGRICULTURAL_LABOR, employment.service.kinds)),
                not_(in_(LaborKind.DOMESTIC_SERVICE, employment.service.kinds)),
                employment.workday >= year.opening_day_of_preceding_year,
                employment.workday <= year.closing_day,
            )
            .grouped_by(employment.service.employer, year.number)
            .having(
                count(employment.workday, distinct=True) >= self.least_number_of_days,
                count(employment.calendar_week(), distinct=True)
                >= self.least_number_of_days,
            )
        )


@dataclass
class AgriculturalWagesEmployerTest(Provision[EmployerByAgriculturalWages]):
    """
    § 3306(a)(2)(A): a person who, in the calendar year or the year before, paid wages
    of $20,000 or more for agricultural labor.
    """

    @classproperty
    def threshold(cls) -> float:
        """
        The least wages a person has to have paid.
        """
        return 20_000

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EMPLOYER_BY_AGRICULTURAL_WAGES`.
        """
        return SaraPredicate.EMPLOYER_BY_AGRICULTURAL_WAGES

    def query(self) -> Query:
        wages = variable(Wages, domain=WagesDefinition(world=self.world).conclusions)
        year = variable(CalendarYear, domain=self.world.calendar_years)
        return an(
            entity(
                inference(EmployerByAgriculturalWages)(
                    party=wages.payment.payer, year=year.number, wages=wages
                )
            )
            .where(
                in_(LaborKind.AGRICULTURAL_LABOR, wages.service.purposes),
                wages.payment.day >= year.opening_day_of_preceding_year,
                wages.payment.day <= year.closing_day,
            )
            .grouped_by(wages.payment.payer, year.number)
            .having(total(wages.amount, default=0) >= self.threshold)
        )


@dataclass
class DomesticServiceEmployerTest(Provision[EmployerOfDomesticService]):
    """
    § 3306(a)(3): a person who, in the calendar year or the year before, paid wages in
    cash of $1,000 or more for domestic service.
    """

    @classproperty
    def threshold(cls) -> float:
        """
        The least cash wages a person has to have paid.
        """
        return 1_000

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EMPLOYER_OF_DOMESTIC_SERVICE`.
        """
        return SaraPredicate.EMPLOYER_OF_DOMESTIC_SERVICE

    def query(self) -> Query:
        wages = variable(Wages, domain=WagesDefinition(world=self.world).conclusions)
        year = variable(CalendarYear, domain=self.world.calendar_years)
        return an(
            entity(
                inference(EmployerOfDomesticService)(
                    party=wages.payment.payer, year=year.number, wages=wages
                )
            )
            .where(
                in_(LaborKind.DOMESTIC_SERVICE, wages.service.purposes),
                wages.payment.is_in_cash(),
                wages.payment.day >= year.opening_day_of_preceding_year,
                wages.payment.day <= year.closing_day,
            )
            .grouped_by(wages.payment.payer, year.number)
            .having(total(wages.amount, default=0) >= self.threshold)
        )


@dataclass
class EmployerDefinition(Provision[Employer]):
    """
    § 3306(a): a person who is an employer for a calendar year under any of its
    paragraphs.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EMPLOYER`.
        """
        return SaraPredicate.EMPLOYER

    def query(self) -> Query:
        employer = variable(
            Employer,
            domain=[
                conclusion
                for test in (
                    WagesEmployerTest,
                    DaysOfEmploymentEmployerTest,
                    AgriculturalWagesEmployerTest,
                    DomesticServiceEmployerTest,
                )
                for conclusion in test(world=self.world).conclusions
            ],
        )
        return an(entity(employer))


# %% the excise tax


@dataclass
class TotalWagesOfEmployer(Provision[TotalWages]):
    """
    The wages an employer paid in a calendar year, those to each employee counted up to
    the wage base of § 3306(b)(1).
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.TOTAL_WAGES`.
        """
        return SaraPredicate.TOTAL_WAGES

    def query(self) -> Query:
        annual_wages = variable(AnnualWagesOfEmployee, domain=self.annual_wages())
        return an(
            entity(
                inference(TotalWages)(
                    employer=annual_wages.employer,
                    amount=total(
                        annual_wages.amount_up_to(WagesDefinition.wage_base), default=0
                    ),
                    first_day=annual_wages.year.opening_day,
                    last_day=annual_wages.year.closing_day,
                )
            ).grouped_by(annual_wages.employer, annual_wages.year)
        )

    def annual_wages(self) -> list[AnnualWagesOfEmployee]:
        """:return: The wages each employer paid each employee in each calendar year."""
        wages = variable(Wages, domain=WagesDefinition(world=self.world).conclusions)
        year = variable(CalendarYear, domain=self.world.calendar_years)
        return (
            an(
                entity(
                    inference(AnnualWagesOfEmployee)(
                        employer=wages.payment.payer,
                        employee=wages.payee,
                        year=year,
                        amount=total(wages.amount, default=0),
                    )
                )
                .where(
                    wages.payment.payer == wages.service.employer,
                    wages.payment.day >= year.opening_day,
                    wages.payment.day <= year.closing_day,
                )
                .grouped_by(wages.payment.payer, wages.payee, year)
            )
        ).tolist()


@dataclass
class ExciseTaxOnEmployer(Provision[ExciseTax]):
    """
    § 3301: the excise tax on an employer for a calendar year, 6 percent of the total
    wages it paid in it.
    """

    @classproperty
    def rate(cls) -> float:
        """
        The share of the total wages the tax is.
        """
        return 0.06

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EXCISE_TAX`.
        """
        return SaraPredicate.EXCISE_TAX

    def query(self) -> Query:
        employer = variable(
            Employer, domain=EmployerDefinition(world=self.world).conclusions
        )
        total_wages = variable(
            TotalWages, domain=TotalWagesOfEmployer(world=self.world).conclusions
        )
        return an(
            entity(
                inference(ExciseTax)(
                    employer=employer.party,
                    year=employer.year,
                    wages=total_wages.amount,
                    amount=total_wages.share_in_whole_dollars(self.rate),
                )
            ).where(
                total_wages.employer == employer.party,
                total_wages.first_day.year == employer.year,
                total_wages.spans_a_calendar_year(),
            )
        )
