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
    Business,
    CalendarYear,
    Death,
    DomesticServicePlace,
    EmployeeBenefit,
    EmployeeBenefitPlan,
    LaborKind,
    Marriage,
    Party,
    Payment,
    Place,
    Service,
    Termination,
)
from law_as_code_benchmarks.sara.employment_exclusions import (
    AdmittedAlienCondition,
    ExcludedAgriculturalLabor,
    ExcludedDomesticService,
    ForeignGovernmentExclusion,
    InternationalOrganizationExclusion,
    ServiceAbroadInclusion,
    ServiceForFamilyMemberTest,
    ServiceInUnitedStatesTest,
    StateExclusion,
    UnitedStatesGovernmentExclusion,
)
from law_as_code_benchmarks.sara.employment_tax_conclusions import (
    AgriculturalLaborPaidInKind,
    AgriculturalWorkday,
    AnnualWagesOfEmployee,
    DeathBenefitPlan,
    Employer,
    EmployerByAgriculturalWages,
    EmployerByCashPaid,
    EmployerByDaysOfAgriculturalLabor,
    EmployerByDaysOfEmployment,
    EmployerByWages,
    EmployerOfDomesticService,
    EmployerUnderGeneralRule,
    Employment,
    ExciseTax,
    PaymentAfterTermination,
    PaymentFromPlanForEmployees,
    PaymentInKindOutsideBusiness,
    PaymentToSurvivingSpouse,
    SicknessOrAccidentDisabilityPlan,
    TotalWages,
    Wages,
)
from law_as_code_benchmarks.sara.family_status import DependentTest
from law_as_code_benchmarks.sara.family_status_conclusions import Dependent
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
class DaysOfAgriculturalLaborEmployerTest(Provision[EmployerByDaysOfAgriculturalLabor]):
    """
    `§ 3306(a)(2)(B) <https://www.law.cornell.edu/uscode/text/26/3306#a_2_B>`__: a person who, on each of some 10 days in the calendar year or the
    year before, each in a different calendar week, employed 5 or more individuals in
    agricultural labor.
    """

    @classproperty
    def least_number_of_days(cls) -> int:
        """
        How many days, each in a different week, a person has to have employed them on.
        """
        return 10

    @classproperty
    def least_number_of_employees(cls) -> int:
        """
        How many individuals a person has to have employed on each of the days.
        """
        return 5

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EMPLOYER_BY_DAYS_OF_AGRICULTURAL_LABOR`.
        """
        return SaraPredicate.EMPLOYER_BY_DAYS_OF_AGRICULTURAL_LABOR

    @classproperty
    def year_position(cls) -> int | None:
        """
        The sixth argument.
        """
        return 5

    def query(self) -> Query:
        workday = variable(AgriculturalWorkday, domain=self.agricultural_workdays())
        year = variable(CalendarYear, domain=self.world.calendar_years)
        return an(
            entity(
                inference(EmployerByDaysOfAgriculturalLabor)(
                    party=workday.employer, year=year.number, workdays=workday
                )
            )
            .where(
                workday.workday >= year.opening_day_of_preceding_year,
                workday.workday <= year.closing_day,
            )
            .grouped_by(workday.employer, year.number)
            .having(
                count(workday.workday, distinct=True) >= self.least_number_of_days,
                count(workday.calendar_week(), distinct=True)
                >= self.least_number_of_days,
            )
        )

    def agricultural_workdays(self) -> list[AgriculturalWorkday]:
        """:return: The days a person employed enough individuals in agricultural labor on, among the days of employment the case states."""
        employment = variable(
            Employment,
            domain=[
                conclusion
                for conclusion in self.world.stated_conclusions
                if isinstance(conclusion, Employment) and conclusion.workday is not None
            ],
        )
        return (
            an(
                entity(
                    inference(AgriculturalWorkday)(
                        employer=employment.service.employer,
                        workday=employment.workday,
                        employees=employment.service.employee,
                    )
                )
                .where(in_(LaborKind.AGRICULTURAL_LABOR, employment.service.kinds))
                .grouped_by(employment.service.employer, employment.workday)
                .having(
                    count(employment.service.employee, distinct=True)
                    >= self.least_number_of_employees
                )
            )
        ).tolist()


@dataclass
class ExcludedAgriculturalLaborTest(Provision[ExcludedAgriculturalLabor]):
    """
    `§ 3306(c)(1) <https://www.law.cornell.edu/uscode/text/26/3306#c_1>`__: agricultural labor, unless performed for a person meeting
    `(1)(A)(i) <https://www.law.cornell.edu/uscode/text/26/3306#c_1_A_i>`__ or `(ii) <https://www.law.cornell.edu/uscode/text/26/3306#c_1_A_ii>`__ in the calendar year and not by an alien admitted to perform it.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EXCLUDED_AGRICULTURAL_LABOR`.
        """
        return SaraPredicate.EXCLUDED_AGRICULTURAL_LABOR

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        service = variable(Service, domain=self.world.services)
        year = variable(CalendarYear, domain=self.world.calendar_years)
        employer = variable(
            Employer,
            domain=EmployerByCashPaidTest(world=self.world).conclusions
            + DaysOfAgriculturalLaborEmployerTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(ExcludedAgriculturalLabor)(service=service, year=year.number)
            ).where(
                in_(LaborKind.AGRICULTURAL_LABOR, service.kinds),
                not_(
                    and_(
                        exists(
                            employer,
                            and_(
                                employer.party == service.employer,
                                employer.year == year.number,
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
        )


@dataclass
class ExcludedDomesticServiceTest(Provision[ExcludedDomesticService]):
    """
    `§ 3306(c)(2) <https://www.law.cornell.edu/uscode/text/26/3306#c_2>`__: domestic service in a private home, local college club or local
    chapter of a college fraternity or sorority, unless its employer paid cash
    remuneration of $1,000 or more for domestic service in the calendar year or the year
    before.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EXCLUDED_DOMESTIC_SERVICE`.
        """
        return SaraPredicate.EXCLUDED_DOMESTIC_SERVICE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        service = variable(Service, domain=self.world.services)
        place = variable(
            Place,
            domain=list(
                dict.fromkeys(
                    place for service in self.world.services for place in service.places
                )
            ),
        )
        year = variable(CalendarYear, domain=self.world.calendar_years)
        employer = variable(
            EmployerByCashPaid,
            domain=self.employers_by_cash_paid_for_domestic_service(),
        )
        return an(
            entity(
                inference(ExcludedDomesticService)(
                    service=service, place=place, year=year.number
                )
            ).where(
                in_(LaborKind.DOMESTIC_SERVICE, service.kinds),
                in_(place, service.places),
                in_(place.name, list(DomesticServicePlace)),
                not_(
                    exists(
                        employer,
                        and_(
                            employer.party == service.employer,
                            employer.year == year.number,
                        ),
                    )
                ),
            )
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
        agricultural_labor = variable(
            ExcludedAgriculturalLabor,
            domain=ExcludedAgriculturalLaborTest(world=self.world).conclusions,
        )
        domestic_service = variable(
            ExcludedDomesticService,
            domain=ExcludedDomesticServiceTest(world=self.world).conclusions,
        )
        return an(
            entity(inference(Employment)(service=service, year=service.end.year)).where(
                in_(service, self.services_included()),
                not_(in_(service, self.services_excluded_on_any_day())),
                not_(
                    exists(
                        agricultural_labor,
                        and_(
                            agricultural_labor.service == service,
                            agricultural_labor.year == service.end.year,
                        ),
                    )
                ),
                not_(
                    exists(
                        domestic_service,
                        and_(
                            domestic_service.service == service,
                            domestic_service.year == service.end.year,
                        ),
                    )
                ),
            )
        )

    def services_included(self) -> list[Service]:
        """:return: The services within the United States, and those `§ 3306(c)(B) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__ brings into employment though performed abroad."""
        return [
            conclusion.service
            for inclusion in (ServiceInUnitedStatesTest, ServiceAbroadInclusion)
            for conclusion in inclusion(world=self.world).conclusions
        ]

    def services_excluded_on_any_day(self) -> list[Service]:
        """:return: The services `§ 3306(c)(5) <https://www.law.cornell.edu/uscode/text/26/3306#c_5>`__, `(6) <https://www.law.cornell.edu/uscode/text/26/3306#c_6>`__, `(7) <https://www.law.cornell.edu/uscode/text/26/3306#c_7>`__, `(11) <https://www.law.cornell.edu/uscode/text/26/3306#c_11>`__ and `(16) <https://www.law.cornell.edu/uscode/text/26/3306#c_16>`__ exclude whatever the day."""
        return [
            conclusion.service
            for exclusion in (
                UnitedStatesGovernmentExclusion,
                StateExclusion,
                ForeignGovernmentExclusion,
                InternationalOrganizationExclusion,
            )
            for conclusion in exclusion(world=self.world).conclusions
        ] + [
            conclusion.service
            for conclusion in ServiceForFamilyMemberTest(world=self.world).conclusions
            if not conclusion.bounding_periods()
        ]


# %% wages


@dataclass
class SicknessOrAccidentDisabilityPlanTest(Provision[SicknessOrAccidentDisabilityPlan]):
    """
    `§ 3306(b)(2)(A) <https://www.law.cornell.edu/uscode/text/26/3306#b_2_A>`__: a plan making provision for employees in case of sickness or
    accident disability.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.SICKNESS_OR_ACCIDENT_DISABILITY_PLAN`.
        """
        return SaraPredicate.SICKNESS_OR_ACCIDENT_DISABILITY_PLAN

    def query(self) -> Query:
        plan = variable(EmployeeBenefitPlan, domain=self.world.benefit_plans)
        return an(
            entity(
                inference(SicknessOrAccidentDisabilityPlan)(benefit_plan=plan)
            ).where(
                plan.provides_any(
                    {EmployeeBenefit.SICKNESS, EmployeeBenefit.ACCIDENT_DISABILITY}
                )
            )
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


@dataclass
class PaymentInKindOutsideBusinessTest(Provision[PaymentInKindOutsideBusiness]):
    """
    `§ 3306(b)(7) <https://www.law.cornell.edu/uscode/text/26/3306#b_7>`__: remuneration paid in a medium other than cash for employment that is of
    another sort than the employer's trade or business.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.PAYMENT_IN_KIND_OUTSIDE_BUSINESS`.
        """
        return SaraPredicate.PAYMENT_IN_KIND_OUTSIDE_BUSINESS

    def query(self) -> Query:
        payment = variable(
            Payment,
            domain=[
                payment
                for payment in self.world.payments
                if payment.service is not None
            ],
        )
        business = variable(Business, domain=self.world.businesses)
        employment = variable(
            Employment, domain=EmploymentDefinition(world=self.world).conclusions
        )
        return an(
            entity(
                inference(PaymentInKindOutsideBusiness)(
                    payment=payment, service=payment.service, business=business
                )
            ).where(
                payment.is_in_other_medium_than_cash(),
                business.owner == payment.service.employer,
                business.type_description != None,
                Service.has_type_other_than(payment.service, business.type_description),
                exists(employment, employment.service == payment.service),
            )
        )


@dataclass
class PaymentAfterTerminationTest(Provision[PaymentAfterTermination]):
    """
    `§ 3306(b)(10)(A) <https://www.law.cornell.edu/uscode/text/26/3306#b_10_A>`__: a payment upon or after an employer ended an employment for the
    employee's death or disability.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.PAYMENT_AFTER_TERMINATION`.
        """
        return SaraPredicate.PAYMENT_AFTER_TERMINATION

    def query(self) -> Query:
        payment = variable(
            Payment,
            domain=[payment for payment in self.world.payments if payment.day],
        )
        termination = variable(Termination, domain=self.world.terminations)
        return an(
            entity(
                inference(PaymentAfterTermination)(
                    payment=payment, termination=termination
                )
            ).where(
                termination.ending_day() <= payment.day,
                termination.is_for_death_or_disability_of_employee(),
            )
        )


@dataclass
class PaymentFromPlanForEmployeesTest(Provision[PaymentFromPlanForEmployees]):
    """
    `§ 3306(b)(10)(B) <https://www.law.cornell.edu/uscode/text/26/3306#b_10_B>`__: a payment from a plan an employer established for its employees
    or their dependents.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.PAYMENT_FROM_PLAN_FOR_EMPLOYEES`.
        """
        return SaraPredicate.PAYMENT_FROM_PLAN_FOR_EMPLOYEES

    def query(self) -> Query:
        payment = variable(
            Payment,
            domain=[
                payment
                for payment in self.world.payments
                if payment.benefit_plan_drawn_on is not None
            ],
        )
        return an(
            entity(inference(PaymentFromPlanForEmployees)(payment=payment)).where(
                payment.benefit_plan_drawn_on.sponsor != None,
                payment.benefit_plan_drawn_on.provides_any(
                    {EmployeeBenefit.EMPLOYEES_OR_DEPENDENTS}
                ),
            )
        )


@dataclass
class AgriculturalLaborPaidInKindTest(Provision[AgriculturalLaborPaidInKind]):
    """
    `§ 3306(b)(11) <https://www.law.cornell.edu/uscode/text/26/3306#b_11>`__: remuneration for agricultural labor paid in a medium other than
    cash.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.AGRICULTURAL_LABOR_PAID_IN_KIND`.
        """
        return SaraPredicate.AGRICULTURAL_LABOR_PAID_IN_KIND

    def query(self) -> Query:
        payment = variable(
            Payment,
            domain=[
                payment
                for payment in self.world.payments
                if payment.service is not None
            ],
        )
        return an(
            entity(inference(AgriculturalLaborPaidInKind)(payment=payment)).where(
                in_(LaborKind.AGRICULTURAL_LABOR, payment.service.purposes),
                payment.service.employer == payment.payer,
                payment.service.employee == payment.recipient,
                payment.is_in_other_medium_than_cash(),
            )
        )


@dataclass
class PaymentToSurvivingSpouseTest(Provision[PaymentToSurvivingSpouse]):
    """
    `§ 3306(b)(15) <https://www.law.cornell.edu/uscode/text/26/3306#b_15>`__: a payment by an employer to the surviving spouse of an employee
    after the calendar year the employee died in.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.PAYMENT_TO_SURVIVING_SPOUSE`.
        """
        return SaraPredicate.PAYMENT_TO_SURVIVING_SPOUSE

    def query(self) -> Query:
        payment = variable(
            Payment,
            domain=[
                payment
                for payment in self.world.payments
                if payment.day and payment.payer is not None
            ],
        )
        employment = variable(
            Employment, domain=EmploymentDefinition(world=self.world).conclusions
        )
        death = variable(
            Death, domain=[death for death in self.world.deaths if death.day]
        )
        marriage = variable(Marriage, domain=self.world.marriages)
        return an(
            entity(
                inference(PaymentToSurvivingSpouse)(
                    payment=payment, employment=employment, death=death
                )
            ).where(
                employment.service.employer == payment.payer,
                employment.service.employee == death.person,
                death.day.year < payment.day.year,
                exists(
                    marriage,
                    and_(
                        in_(death.person, marriage.spouses),
                        in_(payment.recipient, marriage.spouses),
                        or_(
                            marriage.period.upper == None,
                            marriage.period.upper == death.day,
                        ),
                    ),
                ),
            )
        )


@dataclass
class WagesDefinition(Provision[Wages]):
    """
    `§ 3306(b) <https://www.law.cornell.edu/uscode/text/26/3306#b>`__: a payment for employment, up to the first $7,000 of it, that no paragraph
    of `§ 3306(b) <https://www.law.cornell.edu/uscode/text/26/3306#b>`__ excludes.
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
            domain=list(
                dict.fromkeys(
                    payee
                    for payment in self.world.payments
                    for payee in payment.payees()
                )
            ),
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
                not_(in_(payment, self.payments_excluded_whoever_receives_them())),
            )
        )

    def is_plan_payment_for_sickness_or_death(
        self, payment: Payment, payee: Party
    ) -> Query:
        """
        `§ 3306(b)(2)(A) <https://www.law.cornell.edu/uscode/text/26/3306#b_2_A>`__ and `(C) <https://www.law.cornell.edu/uscode/text/26/3306#b_2_C>`__: a payment by the employer into or from a plan making
        provision for the employee or their dependents in case of sickness, accident
        disability or death.
        """
        plan = variable(
            EmployeeBenefitPlan,
            domain=[
                conclusion.benefit_plan
                for test in (SicknessOrAccidentDisabilityPlanTest, DeathBenefitPlanTest)
                for conclusion in test(world=self.world).conclusions
            ],
        )
        return and_(
            payment.service.employer == payment.payer,
            self.is_employee_or_dependent(payment, payee),
            exists(
                plan,
                and_(
                    in_(plan, payment.benefit_plans()),
                    in_(payee, plan.beneficiaries),
                ),
            ),
        )

    def is_payment_upon_termination(self, payment: Payment, payee: Party) -> Query:
        """
        `§ 3306(b)(10) <https://www.law.cornell.edu/uscode/text/26/3306#b_10>`__: a payment by the employer to the employee or their dependents from a
        plan for its employees, upon or after it ended their employment for their death or
        disability.
        """
        after_termination = variable(
            PaymentAfterTermination,
            domain=PaymentAfterTerminationTest(world=self.world).conclusions,
        )
        from_plan = variable(
            PaymentFromPlanForEmployees,
            domain=PaymentFromPlanForEmployeesTest(world=self.world).conclusions,
        )
        return and_(
            self.is_employee_or_dependent(payment, payee),
            exists(
                after_termination,
                and_(
                    after_termination.payment == payment,
                    after_termination.termination.service == payment.service,
                    after_termination.termination.employer == payment.payer,
                ),
            ),
            exists(
                from_plan,
                and_(
                    from_plan.payment == payment,
                    payment.benefit_plan_drawn_on.sponsor == payment.payer,
                ),
            ),
        )

    def is_employee_or_dependent(self, payment: Payment, payee: Party) -> Query:
        """:return: Whether *payee* is the employee *payment* is paid for, or a dependent of theirs under `§ 152 <https://www.law.cornell.edu/uscode/text/26/152>`__."""
        dependent = variable(
            Dependent,
            domain=DependentTest(world=self.world).conclusions
            if self.world.benefit_plans
            else [],
        )
        return or_(
            payment.service.employee == payee,
            exists(
                dependent,
                and_(
                    dependent.individual == payee,
                    dependent.taxpayer == payment.service.employee,
                ),
            ),
        )

    def payments_excluded_whoever_receives_them(self) -> list[Payment]:
        """:return: The payments `§ 3306(b)(7) <https://www.law.cornell.edu/uscode/text/26/3306#b_7>`__, `(11) <https://www.law.cornell.edu/uscode/text/26/3306#b_11>`__ and `(15) <https://www.law.cornell.edu/uscode/text/26/3306#b_15>`__ exclude from wages."""
        return [
            conclusion.payment
            for exclusion in (
                PaymentInKindOutsideBusinessTest,
                AgriculturalLaborPaidInKindTest,
                PaymentToSurvivingSpouseTest,
            )
            for conclusion in exclusion(world=self.world).conclusions
        ]


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
class GeneralRuleEmployerTest(Provision[EmployerUnderGeneralRule]):
    """
    `§ 3306(a)(1) <https://www.law.cornell.edu/uscode/text/26/3306#a_1>`__: a person who is an employer for a calendar year by wages paid or by
    days of employment.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.EMPLOYER_UNDER_GENERAL_RULE`.
        """
        return SaraPredicate.EMPLOYER_UNDER_GENERAL_RULE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        employer = variable(
            Employer,
            domain=[
                conclusion
                for test in (WagesEmployerTest, DaysOfEmploymentEmployerTest)
                for conclusion in test(world=self.world).conclusions
            ],
        )
        return an(
            entity(
                inference(EmployerUnderGeneralRule)(
                    party=employer.party, year=employer.year
                )
            ).grouped_by(employer.party, employer.year)
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

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        employer = variable(
            Employer,
            domain=[
                conclusion
                for test in (
                    GeneralRuleEmployerTest,
                    AgriculturalWagesEmployerTest,
                    DaysOfAgriculturalLaborEmployerTest,
                    DomesticServiceEmployerTest,
                )
                for conclusion in test(world=self.world).conclusions
            ],
        )
        return an(
            entity(
                inference(Employer)(party=employer.party, year=employer.year)
            ).grouped_by(employer.party, employer.year)
        )


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
