"""
What §§ `3306 <https://www.law.cornell.edu/uscode/text/26/3306>`__ and `3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__ of the Internal Revenue Code conclude: employment, wages,
employers and the excise tax on them.
"""

from __future__ import annotations

import datetime
from abc import ABC
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from krrood.symbol_graph.symbol_graph import Symbol

from law_as_code_benchmarks.sara.domain import (
    Business,
    CalendarYear,
    Death,
    EmployeeBenefitPlan,
    Party,
    Payment,
    Service,
    Termination,
)
from law_as_code_benchmarks.sara.prolog_term import Term
from law_as_code_benchmarks.sara.provision import SaraConclusion

# %% employment and wages


@dataclass(eq=False)
class Employment(SaraConclusion):
    """
    A service that is employment under `§ 3306(c) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__.
    """

    service: Service
    """
    The service.
    """

    workday: datetime.date | None = None
    """
    The day it is employment on; None where it is for no day in particular.
    """

    year: int | None = None
    """
    The calendar year it is employment in; None where it is for no year in particular.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.service.name,
            self.service.employer.name,
            self.service.employee.name,
            None if self.workday is None else self.workday.isoformat(),
            self.year,
        )

    def calendar_week(self) -> tuple[int, int] | None:
        """:return: The year and number of the calendar week, Monday to Sunday, of its day; None without a day."""
        if self.workday is None:
            return None
        year, week, _ = self.workday.isocalendar()
        return year, week


@dataclass(eq=False)
class Wages(SaraConclusion):
    """
    A payment, or the part of one, that is wages under `§ 3306(b) <https://www.law.cornell.edu/uscode/text/26/3306#b>`__.
    """

    amount: float
    """
    How much of the payment is wages.
    """

    payment: Payment
    """
    The payment.
    """

    service: Service
    """
    The employment it is paid for.
    """

    payee: Party
    """
    Who receives it.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.amount,
            self.payment.name,
            self.service.name,
            self.payment.payer.name,
            self.payee.name,
            self.service.employer.name,
            self.service.employee.name,
            self.payment.medium,
        )


@dataclass(eq=False)
class BenefitPlanConclusion(SaraConclusion, ABC):
    """
    A conclusion about a plan an employer establishes for its employees.
    """

    benefit_plan: EmployeeBenefitPlan
    """
    The plan.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (self.benefit_plan.name,)


@dataclass(eq=False)
class DeathBenefitPlan(BenefitPlanConclusion):
    """
    A plan making provision for employees in case of death.
    """


@dataclass(eq=False)
class SicknessOrAccidentDisabilityPlan(BenefitPlanConclusion):
    """
    A plan making provision for employees in case of sickness or accident disability.
    """


# %% payments that are no wages


@dataclass(eq=False)
class PaymentInKindOutsideBusiness(SaraConclusion):
    """
    A payment in a medium other than cash for employment outside the employer's trade or
    business.
    """

    payment: Payment
    """
    The payment.
    """

    service: Service
    """
    The employment it is paid for.
    """

    business: Business
    """
    The employer's trade or business, which the employment is of another sort than.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.payment.name,
            self.service.name,
            self.service.employer.name,
            self.service.employee.name,
            self.payment.medium,
            self.business.type_description,
        )


@dataclass(eq=False)
class PaymentAfterTermination(SaraConclusion):
    """
    A payment upon or after an employer ended an employment for the employee's death or
    disability.
    """

    payment: Payment
    """
    The payment.
    """

    termination: Termination
    """
    The termination.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.payment.name,
            self.termination.service.name,
            self.termination.service.employee.name,
            self.termination.employer.name,
            None,
            None,
        )


@dataclass(eq=False)
class PaymentFromPlanForEmployees(SaraConclusion):
    """
    A payment from a plan its payer established for employees or their dependents.
    """

    payment: Payment
    """
    The payment.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.payment.benefit_plan_drawn_on.sponsor.name,
            self.payment.name,
            self.payment.benefit_plan_drawn_on.name,
        )


@dataclass(eq=False)
class AgriculturalLaborPaidInKind(SaraConclusion):
    """
    A payment for agricultural labor in a medium other than cash.
    """

    payment: Payment
    """
    The payment.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.payment.name, self.payment.service.name, self.payment.medium


@dataclass(eq=False)
class PaymentToSurvivingSpouse(SaraConclusion):
    """
    A payment by an employer to the surviving spouse of an employee after the calendar
    year the employee died in.
    """

    payment: Payment
    """
    The payment.
    """

    employment: Employment
    """
    The deceased's employment by the payer.
    """

    death: Death
    """
    The employee's death.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.payment.name,
            self.payment.payer.name,
            self.payment.recipient.name,
            self.death.person.name,
            self.death.day.year,
        )


# %% employers


@dataclass(eq=False)
class Employer(SaraConclusion):
    """
    A person who is an employer for a calendar year under `§ 3306(a) <https://www.law.cornell.edu/uscode/text/26/3306#a>`__.
    """

    party: Party
    """
    The employer.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.party.name, self.year


@dataclass(eq=False)
class EmployerByWagesPaid(Employer, ABC):
    """
    An employer for having paid enough wages in the year or the year before.
    """

    wages: list[Wages] = field(default_factory=list)
    """
    The wages counted.
    """

    def total_wages(self) -> float:
        """:return: The sum of the wages counted."""
        return sum(wages.amount for wages in self.wages)

    def service_names(self) -> list[str]:
        """:return: The name of the service each of the wages counted is paid for."""
        return [wages.service.name for wages in self.wages]


@dataclass(eq=False)
class EmployerByWages(EmployerByWagesPaid):
    """
    An employer for having paid wages of $1,500 or more, agricultural labor and domestic
    service aside.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`Employer.prolog_arguments` by the total wages.
        """
        return self.party.name, self.year, self.total_wages()


@dataclass(eq=False)
class EmployerByAgriculturalWages(EmployerByWagesPaid):
    """
    An employer for having paid wages of $20,000 or more for agricultural labor.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`Employer.prolog_arguments` by the total wages and the services.
        """
        return self.party.name, self.year, self.total_wages(), self.service_names()


@dataclass(eq=False)
class EmployerOfDomesticService(EmployerByWagesPaid):
    """
    An employer for having paid $1,000 or more in cash wages for domestic service.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Orders the arguments as `§ 3306(a)(3) <https://www.law.cornell.edu/uscode/text/26/3306#a_3>`__ does, the services and the total wages
        inserted.
        """
        return self.party.name, self.service_names(), self.total_wages(), self.year


@dataclass(eq=False)
class EmployerByCashPaid(Employer):
    """
    A person who paid enough cash for a kind of labor in the calendar year or the year
    before.
    """

    payments: list[Payment] = field(default_factory=list)
    """
    The payments counted.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Orders the arguments as `§ 3306(c)(1)(A)(i) <https://www.law.cornell.edu/uscode/text/26/3306#c_1_A_i>`__ does, the remuneration, recipients
        and services inserted.
        """
        return (
            self.party.name,
            sum(payment.amount for payment in self.payments),
            [payment.recipient.name for payment in self.payments],
            [payment.service.name for payment in self.payments],
            self.year,
        )


@dataclass(eq=False)
class EmployerByDaysOfEmployment(Employer):
    """
    An employer for having employed someone on enough days, each in a different week.
    """

    workdays: list[datetime.date] = field(default_factory=list)
    """
    The days of employment counted.
    """

    employees: list[Party] = field(default_factory=list)
    """
    Who was employed on them, one for each day.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Orders the arguments as `§ 3306(a)(1)(B) <https://www.law.cornell.edu/uscode/text/26/3306#a_1_B>`__ does, the days and employees inserted.
        """
        return (
            self.party.name,
            [workday.isoformat() for workday in self.workdays],
            [employee.name for employee in self.employees],
            self.year,
        )


@dataclass(eq=False)
class EmployerUnderGeneralRule(Employer):
    """
    An employer under `§ 3306(a)(1) <https://www.law.cornell.edu/uscode/text/26/3306#a_1>`__, by wages paid or by days of employment.
    """


@dataclass(eq=False)
class AgriculturalWorkday(Symbol):
    """
    A day a person employed 5 or more individuals in agricultural labor on.
    """

    employer: Party
    """
    The person employing them.
    """

    workday: datetime.date
    """
    The day.
    """

    employees: list[Party] = field(default_factory=list)
    """
    The individuals employed on it.
    """

    def calendar_week(self) -> tuple[int, int]:
        """:return: The year and number of the calendar week, Monday to Sunday, of the day."""
        year, week, _ = self.workday.isocalendar()
        return year, week


@dataclass(eq=False)
class EmployerByDaysOfAgriculturalLabor(Employer):
    """
    An employer for having employed 5 or more individuals in agricultural labor on
    enough days, each in a different week.
    """

    workdays: list[AgriculturalWorkday] = field(default_factory=list)
    """
    The days counted.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Orders the arguments as `§ 3306(a)(2)(B) <https://www.law.cornell.edu/uscode/text/26/3306#a_2_B>`__ does, the days, services, employees and
        weeks inserted; the services are left open.
        """
        return (
            self.party.name,
            [workday.workday.isoformat() for workday in self.workdays],
            None,
            [[employee.name for employee in day.employees] for day in self.workdays],
            sorted({workday.calendar_week() for workday in self.workdays}),
            self.year,
        )


# %% the excise tax


@dataclass(eq=False)
class AnnualWagesOfEmployee(Symbol):
    """
    The wages an employer paid one employee in a calendar year.
    """

    employer: Party
    """
    The employer.
    """

    employee: Party
    """
    The employee.
    """

    year: CalendarYear
    """
    The calendar year.
    """

    amount: float
    """
    The wages.
    """

    def amount_up_to(self, limit: float) -> float:
        """:return: The wages, counted up to *limit*."""
        return min(limit, self.amount)


@dataclass(eq=False)
class TotalWages(SaraConclusion):
    """
    The wages an employer paid from one day to another, each employee's capped by
    `§ 3306(b)(1) <https://www.law.cornell.edu/uscode/text/26/3306#b_1>`__.
    """

    employer: Party
    """
    The employer.
    """

    amount: float
    """
    The total.
    """

    first_day: datetime.date
    """
    The first day of the period.
    """

    last_day: datetime.date
    """
    The last day of the period.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.employer.name,
            self.amount,
            None,
            None,
            self.first_day.isoformat(),
            self.last_day.isoformat(),
        )

    def spans_a_calendar_year(self) -> bool:
        """:return: Whether the period runs from January 1 to December 31 of one year."""
        return (
            self.first_day.year == self.last_day.year
            and (self.first_day.month, self.first_day.day) == (1, 1)
            and (self.last_day.month, self.last_day.day) == (12, 31)
        )

    def share_in_whole_dollars(self, rate: float) -> int:
        """:return: *rate* of the total, rounded to whole dollars, halves away from zero as Prolog's ``round``."""
        return int(Decimal(str(rate * self.amount)).quantize(Decimal(1), ROUND_HALF_UP))


@dataclass(eq=False)
class ExciseTax(SaraConclusion):
    """
    The excise tax `§ 3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__ imposes on an employer for a calendar year.
    """

    employer: Party
    """
    The employer.
    """

    year: int
    """
    The calendar year.
    """

    wages: float
    """
    The total wages it is imposed on.
    """

    amount: int
    """
    The tax, in whole dollars.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.employer.name, self.year, self.wages, None, None, self.amount
