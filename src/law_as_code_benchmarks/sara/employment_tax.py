"""
The employment tax as rules over the domain model: who is an *employer* (`§ 3306(a) <https://www.law.cornell.edu/uscode/text/26/3306#a>`__),
what is *wages* (`§ 3306(b) <https://www.law.cornell.edu/uscode/text/26/3306#b>`__) and *employment* (`§ 3306(c) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__), and the excise tax of `§ 3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__.

Days of employment are only those a case states, as SARA's program leaves the day open
wherever §§ `3306 <https://www.law.cornell.edu/uscode/text/26/3306>`__ and `3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__ ask about employment.
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
    EmployeeBenefitPlan,
    EmployeeBenefit,
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
    EmployerByCashPaid,
    EmployerOfDomesticService,
    Employment,
    ExciseTax,
    DeathBenefitPlan,
    TotalWages,
    Wages,
)
from law_as_code_benchmarks.sara.provision import Provision, SaraPredicate

# %% employment


@dataclass
class EmployerByCashPaidTest(Provision[EmployerByCashPaid]):
    """
    `§ 3306(c)(1)(A)(i) <https://www.law.cornell.edu/uscode/text/26/3306#c_1_A_i>`__: a person who, in the calendar year or the year before, paid
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
                inference(EmployerByCashPaid)(
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
    `§ 3306(c) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__: service within the United States, or abroad for an American
    employer, that no paragraph excludes, for the calendar year it ends in.

    `(5) <https://www.law.cornell.edu/uscode/text/26/3306#c_5>`__ for a spouse or a child under 21, `(10) <https://www.law.cornell.edu/uscode/text/26/3306#c_10>`__, `(13) <https://www.law.cornell.edu/uscode/text/26/3306#c_13>`__
    and `(21) <https://www.law.cornell.edu/uscode/text/26/3306#c_21>`__ need a day, which these rules never give, so they never apply.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EMPLOYMENT`.
        """
        return SaraPredicate.EMPLOYMENT

    def query(self) -> Query:
        service = variable(
            Service,
            domain=[service for service in self.world.services if service.end],
        )
        return an(
            entity(inference(Employment)(service=service, year=service.end.year)).where(
                or_(
                    service.places == [],
                    in_(self.world.united_states, service.countries()),
                    in_(service, self.services_abroad()),
                ),
                not_(in_(service, self.services_excluded_by_employer())),
                not_(self.is_excluded_agricultural_labor(service)),
                not_(self.is_excluded_domestic_service(service)),
                not_(self.is_service_for_child(service)),
            )
        )

    def services_abroad(self) -> list[Service]:
        """:return: The services `§ 3306(c)(B) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__ brings into employment though performed abroad."""
        return [
            conclusion.service
            for conclusion in ServiceAbroadInclusion(world=self.world).conclusions
        ]

    def services_excluded_by_employer(self) -> list[Service]:
        """:return: The services `§ 3306(c)(6) <https://www.law.cornell.edu/uscode/text/26/3306#c_6>`__, `(7) <https://www.law.cornell.edu/uscode/text/26/3306#c_7>`__, `(11) <https://www.law.cornell.edu/uscode/text/26/3306#c_11>`__ and `(16) <https://www.law.cornell.edu/uscode/text/26/3306#c_16>`__ exclude for whom they are performed for."""
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
        `§ 3306(c)(1) <https://www.law.cornell.edu/uscode/text/26/3306#c_1>`__: agricultural labor, unless performed for a person meeting
        `(1)(A)(i) <https://www.law.cornell.edu/uscode/text/26/3306#c_1_A_i>`__ in its year and not by an alien admitted to perform it.
        """
        employer = variable(
            EmployerByCashPaid,
            domain=EmployerByCashPaidTest(world=self.world).conclusions,
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

    def is_excluded_domestic_service(self, service: Service) -> Query:
        """
        `§ 3306(c)(2) <https://www.law.cornell.edu/uscode/text/26/3306#c_2>`__: domestic service in a private home, local college club or local
        chapter of a college fraternity or sorority, unless its employer paid cash
        remuneration of $1,000 or more for domestic service in its year or the year
        before.
        """
        employer = variable(
            EmployerByCashPaid,
            domain=self.employers_by_cash_paid_for_domestic_service(),
        )
        return and_(
            in_(LaborKind.DOMESTIC_SERVICE, service.kinds),
            service.is_performed_at_any(list(DomesticServicePlace)),
            not_(
                exists(
                    employer,
                    and_(
                        employer.party == service.employer,
                        employer.year == service.end.year,
                    ),
                )
            ),
        )

    def employers_by_cash_paid_for_domestic_service(
        self, threshold: float = 1_000
    ) -> list[EmployerByCashPaid]:
        """
        :param threshold: The least cash remuneration `§ 3306(c)(2) <https://www.law.cornell.edu/uscode/text/26/3306#c_2>`__ asks for.
        :return: The persons who paid at least *threshold* in cash for domestic service
            in a calendar year or the year before, for each such year.
        """
        payment = variable(Payment, domain=self.world.payments)
        year = variable(CalendarYear, domain=self.world.calendar_years)
        return an(
            entity(
                inference(EmployerByCashPaid)(
                    party=payment.payer, year=year.number, payments=payment
                )
            )
            .where(
                in_(LaborKind.DOMESTIC_SERVICE, payment.service.kinds),
                payment.is_in_cash(),
                payment.day >= year.opening_day_of_preceding_year,
                payment.day <= year.closing_day,
            )
            .grouped_by(payment.payer, year.number)
            .having(total(payment.amount, default=0) >= threshold)
        ).tolist()

    def is_service_for_child(self, service: Service) -> Query:
        """
        `§ 3306(c)(5)(A) <https://www.law.cornell.edu/uscode/text/26/3306#c_5_A>`__: service performed by an individual in the employ of their son
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
    `§ 3306(b) <https://www.law.cornell.edu/uscode/text/26/3306#b>`__: a payment for employment, up to the first $7,000 of it, that no paragraph
    of `§ 3306(b) <https://www.law.cornell.edu/uscode/text/26/3306#b>`__ excludes.

    Paragraphs `(2) <https://www.law.cornell.edu/uscode/text/26/3306#b_2>`__ and `(10) <https://www.law.cornell.edu/uscode/text/26/3306#b_10>`__ cover payments to the employee only, not to
    their dependents; `(7) <https://www.law.cornell.edu/uscode/text/26/3306#b_7>`__ is not modelled.
    """

    @classproperty
    def wage_base(cls) -> float:
        """
        `§ 3306(b)(1) <https://www.law.cornell.edu/uscode/text/26/3306#b_1>`__: the most of a payment that is wages.
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
        `§ 3306(b)(2)(A) <https://www.law.cornell.edu/uscode/text/26/3306#b_2_A>`__ and `(C) <https://www.law.cornell.edu/uscode/text/26/3306#b_2_C>`__: a payment by the employer into or from a plan making
        provision for the employee in case of sickness, accident disability or death.
        """
        plan = variable(EmployeeBenefitPlan, domain=self.world.benefit_plans)
        return and_(
            payment.service.employer == payment.payer,
            payment.service.employee == payee,
            exists(
                plan,
                and_(
                    in_(plan, payment.benefit_plans()),
                    in_(payee, plan.beneficiaries),
                    plan.provides_any(
                        {
                            EmployeeBenefit.SICKNESS,
                            EmployeeBenefit.ACCIDENT_DISABILITY,
                            EmployeeBenefit.DEATH,
                        }
                    ),
                ),
            ),
        )

    def is_payment_upon_termination(self, payment: Payment, payee: Party) -> Query:
        """
        `§ 3306(b)(10) <https://www.law.cornell.edu/uscode/text/26/3306#b_10>`__: a payment by the employer to the employee from a plan for its
        employees, upon or after it ended their service for their death or disability.
        """
        termination = variable(Termination, domain=self.world.terminations)
        return and_(
            payment.service.employer == payment.payer,
            payment.service.employee == payee,
            payment.benefit_plan_drawn_on.sponsor == payment.payer,
            payment.benefit_plan_drawn_on.provides_any(
                {EmployeeBenefit.EMPLOYEES_OR_DEPENDENTS}
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
        `§ 3306(b)(11) <https://www.law.cornell.edu/uscode/text/26/3306#b_11>`__: remuneration for agricultural labor paid in a medium other than
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
        `§ 3306(b)(15) <https://www.law.cornell.edu/uscode/text/26/3306#b_15>`__: a payment by the employer to the surviving spouse of the employee
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
                            or_(
                                marriage.period.end == None,
                                marriage.period.end == death.day,
                            ),
                        ),
                    ),
                ),
            ),
        )


@dataclass
class DeathBenefitPlanTest(Provision[DeathBenefitPlan]):
    """
    `§ 3306(b)(2)(C) <https://www.law.cornell.edu/uscode/text/26/3306#b_2_C>`__: a plan making provision for employees in case of death.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.DEATH_BENEFIT_PLAN`.
        """
        return SaraPredicate.DEATH_BENEFIT_PLAN

    def query(self) -> Query:
        plan = variable(EmployeeBenefitPlan, domain=self.world.benefit_plans)
        return an(
            entity(inference(DeathBenefitPlan)(benefit_plan=plan)).where(
                in_(EmployeeBenefit.DEATH, plan.benefits)
            )
        )


# %% employers


@dataclass
class WagesEmployerTest(Provision[EmployerByWages]):
    """
    `§ 3306(a)(1)(A) <https://www.law.cornell.edu/uscode/text/26/3306#a_1_A>`__: a person who, in the calendar year or the year before, paid wages
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
    `§ 3306(a)(1)(B) <https://www.law.cornell.edu/uscode/text/26/3306#a_1_B>`__: a person who, on each of some 10 days in the calendar year or the
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
    `§ 3306(a)(2)(A) <https://www.law.cornell.edu/uscode/text/26/3306#a_2_A>`__: a person who, in the calendar year or the year before, paid wages
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
    `§ 3306(a)(3) <https://www.law.cornell.edu/uscode/text/26/3306#a_3>`__: a person who, in the calendar year or the year before, paid wages in
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
    `§ 3306(a) <https://www.law.cornell.edu/uscode/text/26/3306#a>`__: a person who is an employer for a calendar year under any of its
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
    the wage base of `§ 3306(b)(1) <https://www.law.cornell.edu/uscode/text/26/3306#b_1>`__.
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
            ).grouped_by(
                annual_wages.employer,
                annual_wages.year.opening_day,
                annual_wages.year.closing_day,
            )
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
    `§ 3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__: the excise tax on an employer for a calendar year, 6 percent of the total
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
