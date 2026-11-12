"""
The circumstances SARA's cases describe, as a domain model: parties, the services they
perform for one another, where, what is paid for them, their families and homes, and
the roles, relations and events the provisions ask about.
"""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, StrEnum, auto

from krrood.entity_query_language.predicate import symbolic_function
from krrood.patterns.role import Role
from krrood.symbol_graph.symbol_graph import Symbol
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from law_as_code_benchmarks.sara.provision import SaraConclusion

# %% periods


@dataclass(frozen=True)
class Period:
    """The days something lasts, from its first to its last, either of which a case may leave open."""

    start: datetime.date | None = None
    """The first day; None where the case does not say."""

    end: datetime.date | None = None
    """The last day; None where it goes on."""

    @symbolic_function
    def intersect(self, other: Period) -> Period:
        """:return: The period from the later stated start of the two to the earlier stated end."""
        starts = [start for start in (self.start, other.start) if start is not None]
        ends = [end for end in (self.end, other.end) if end is not None]
        return Period(
            start=max(starts) if starts else None, end=min(ends) if ends else None
        )

    def includes(self, day: datetime.date) -> bool:
        """:return: Whether *day* falls within the period, an open start or end bounding nothing."""
        return (self.start is None or self.start <= day) and (
            self.end is None or day <= self.end
        )


# %% places


@dataclass(eq=False)
class Country(Symbol):
    """A country."""

    name: str
    """The country's name."""


@dataclass(eq=False)
class Place(Symbol):
    """A place work is done at."""

    name: str
    """The place's name."""

    country: Country | None = None
    """The country it lies in; None where the case does not say."""


# %% parties


@dataclass(eq=False)
class Party(Symbol):
    """A person or an organization that works, employs, pays or is paid."""

    name: str
    """The party's name."""

    citizenships: list[Country] = field(default_factory=list)
    """The countries the party is a citizen of."""

    def is_citizen_of_other_country_than(self, country: Country) -> bool:
        """:return: Whether the party is a citizen of a country other than *country*, whether or not also of it."""
        return any(citizenship is not country for citizenship in self.citizenships)


@dataclass(eq=False)
class Government(Party):
    """The government of a country or of a part of one."""


@dataclass(eq=False)
class UnitedStatesGovernment(Government):
    """The Government of the United States."""


@dataclass(eq=False)
class StateGovernment(Government):
    """The government of a State, or of a political subdivision of one."""


@dataclass(eq=False)
class ForeignGovernment(Government):
    """The government of a country other than the United States."""


@dataclass(eq=False)
class Hospital(Role[Party]):
    """A party running a hospital."""


@dataclass(eq=False)
class InternationalOrganization(Role[Party]):
    """A party that is an international organization."""


@dataclass(eq=False)
class AmericanEmployer(Role[Party]):
    """A party that is an American employer."""


# %% work


class LaborKind(Enum):
    """The kinds of work the employment-tax provisions treat apart."""

    AGRICULTURAL_LABOR = auto()
    """Agricultural labor."""

    DOMESTIC_SERVICE = auto()
    """Domestic service."""


@dataclass(eq=False)
class Service(Symbol):
    """Work an employee performs for an employer."""

    name: str
    """The name the case gives the service."""

    employee: Party
    """Who performs it."""

    employer: Party
    """Whom it is performed for."""

    start: datetime.date | None = None
    """The first day of it; None where the case does not say."""

    end: datetime.date | None = None
    """The last day of it; None where it goes on."""

    places: list[Place] = field(default_factory=list)
    """Where it is performed."""

    kinds: set[LaborKind] = field(default_factory=set)
    """The kinds of work it is, among those the provisions treat apart."""

    purposes: set[LaborKind] = field(default_factory=set)
    """The kinds of work among :attr:`kinds` the case states as its purpose rather than its type."""

    def countries(self) -> list[Country | None]:
        """:return: The country of each place it is performed at, None for a place in no stated country."""
        return [place.country for place in self.places]

    def is_performed_at_any(self, place_names: list[str]) -> bool:
        """:return: Whether it is performed at a place of one of *place_names*."""
        return any(place.name in place_names for place in self.places)


class DomesticServicePlace(StrEnum):
    """The places `§ 3306(c)(2) <https://www.law.cornell.edu/uscode/text/26/3306#c_2>`__ treats domestic service at apart, each named as SARA names it."""

    PRIVATE_HOME = "private home"
    """A private home."""

    LOCAL_COLLEGE_CLUB = "local college club"
    """A local college club."""

    LOCAL_CHAPTER_OF_COLLEGE_FRATERNITY = "local chapter of a college fraternity"
    """A local chapter of a college fraternity."""

    LOCAL_CHAPTER_OF_COLLEGE_SORORITY = "local chapter of a college sorority"
    """A local chapter of a college sorority."""


@dataclass(eq=False)
class HospitalStay(Symbol):
    """A party's stay as a patient of a hospital."""

    patient: Party
    """The patient."""

    hospital: Party
    """The party running the hospital."""

    start: datetime.date
    """The first day of the stay."""

    end: datetime.date | None = None
    """The last day of the stay; None where it goes on."""

    def includes(self, day: datetime.date) -> bool:
        """:return: Whether *day* falls within the stay, its first and last day included."""
        return self.start <= day and (self.end is None or day <= self.end)


@dataclass(eq=False)
class Migration(Symbol):
    """A party's admission to a country."""

    migrant: Party
    """Who migrates."""

    destination: Country
    """The country admitted to."""

    purpose: LaborKind | None = None
    """The work admitted for; None where it is not among the kinds the provisions treat apart."""


# %% payments


class Revenue(ABC):
    """Money a party receives, which counts towards their gross income."""

    @abstractmethod
    def earner(self) -> Party | None:
        """:return: Who receives the money; None where it goes to no party."""

    @abstractmethod
    def received_amount(self) -> float:
        """:return: How much is received."""

    @abstractmethod
    def received_day(self) -> datetime.date | None:
        """:return: The day it is received; None where the case does not say."""


class EmployeeBenefit(Enum):
    """The benefits an employee benefit plan provides, among those `§ 3306(b) <https://www.law.cornell.edu/uscode/text/26/3306#b>`__ treats apart."""

    SICKNESS = auto()
    """Provision for employees in case of sickness."""

    ACCIDENT_DISABILITY = auto()
    """Provision for employees in case of accident disability."""

    DEATH = auto()
    """Provision for employees in case of death."""

    EMPLOYEES_OR_DEPENDENTS = auto()
    """Provision for employees or their dependents generally."""


@dataclass(eq=False)
class EmployeeBenefitPlan(Symbol):
    """A plan or fund an employer establishes for its employees or their dependents, and pays into or from."""

    name: str
    """The plan's name."""

    sponsor: Party | None = None
    """Who established it; None where the case does not say."""

    benefits: set[EmployeeBenefit] = field(default_factory=set)
    """The benefits it provides, among those `§ 3306(b) <https://www.law.cornell.edu/uscode/text/26/3306#b>`__ treats apart."""

    beneficiaries: list[Party] = field(default_factory=list)
    """Whom it benefits."""

    def provides_any(self, benefits: set[EmployeeBenefit]) -> bool:
        """:return: Whether it provides one of *benefits*."""
        return not self.benefits.isdisjoint(benefits)


class PaymentMedium(StrEnum):
    """The media of payment the provisions treat apart."""

    CASH = "cash"
    """Cash."""


@dataclass(eq=False)
class Household(Symbol):
    """A home, which its residents live in and someone maintains."""

    name: str
    """The household's name."""


@dataclass(eq=False)
class Payment(Symbol, Revenue):
    """A payment from one party to another party or into a plan."""

    name: str | None
    """The name the case gives the payment; None where it leaves the payment unnamed."""

    payer: Party | None
    """Who pays; None where the case does not say."""

    recipient: Party | EmployeeBenefitPlan | None
    """Who or what is paid; None where the case does not say."""

    amount: float
    """How much is paid."""

    day: datetime.date | None = None
    """The day it is paid; None where the case does not say."""

    service: Service | None = None
    """The service it is paid for; None where it is not paid for a service."""

    medium: str | None = None
    """What it is paid in, such as ``cash``; None where the case does not say."""

    benefit_plan_drawn_on: EmployeeBenefitPlan | None = None
    """The plan it is paid from; None where it is not paid from a plan."""

    household_maintained: Household | None = None
    """The household whose upkeep it pays for; None where it pays for none."""

    def earner(self) -> Party | None:
        return self.recipient if isinstance(self.recipient, Party) else None

    def received_amount(self) -> float:
        return self.amount

    def received_day(self) -> datetime.date | None:
        return self.day

    def amount_up_to(self, limit: float) -> float:
        """:return: The amount, counted up to *limit*."""
        return min(limit, self.amount)

    def benefit_plans(self) -> list[EmployeeBenefitPlan]:
        """:return: The plans it is paid into or from."""
        return [
            plan
            for plan in (self.recipient, self.benefit_plan_drawn_on)
            if isinstance(plan, EmployeeBenefitPlan)
        ]

    def payees(self) -> list[Party]:
        """:return: Who receives the payment: its recipient, or the beneficiaries of the plan paid into."""
        if isinstance(self.recipient, EmployeeBenefitPlan):
            return self.recipient.beneficiaries
        return [] if self.recipient is None else [self.recipient]

    def is_in_cash(self) -> bool:
        """:return: Whether it is paid in cash, which it is taken to be where the case names no medium."""
        return self.medium is None or self.medium == PaymentMedium.CASH

    def is_in_other_medium_than_cash(self) -> bool:
        """:return: Whether the case names a medium it is paid in other than cash."""
        return self.medium is not None and self.medium != PaymentMedium.CASH


# %% events of life and work


@dataclass(eq=False)
class Death(Symbol):
    """A party's death."""

    person: Party
    """Who dies."""

    day: datetime.date | None = None
    """The day of the death; None where the case does not say."""


@dataclass(eq=False)
class Disability(Symbol):
    """A party becoming disabled."""

    person: Party
    """Who becomes disabled."""


@dataclass(eq=False)
class Termination(Symbol):
    """An employer ending an employee's service."""

    employer: Party
    """Who ends the service."""

    service: Service
    """The service ended."""

    day: datetime.date | None = None
    """The day it ends; None where the case gives no day of its own."""

    reasons: list[Death | Disability] = field(default_factory=list)
    """Why the service is ended."""

    def is_for_death_or_disability_of(self, person: Party) -> bool:
        """:return: Whether one of its reasons is the death or disability of *person*."""
        return any(reason.person is person for reason in self.reasons)

    def ending_day(self) -> datetime.date | None:
        """:return: The day the termination takes effect: its own day, else the last day of the service."""
        return self.day if self.day is not None else self.service.end


@dataclass(eq=False)
class Income(Symbol, Revenue):
    """Money a party earns other than by a payment the case states."""

    earning_party: Party
    """Who earns it."""

    amount: float
    """How much is earned."""

    day: datetime.date | None = None
    """The day it is earned; None where the case does not say."""

    def earner(self) -> Party | None:
        return self.earning_party

    def received_amount(self) -> float:
        return self.amount

    def received_day(self) -> datetime.date | None:
        return self.day


# %% families and homes


@dataclass(eq=False)
class Birth(Symbol):
    """A party's birth."""

    person: Party
    """Who is born."""

    day: datetime.date
    """The day of the birth."""


@dataclass(eq=False)
class Marriage(Symbol):
    """A marriage between two parties."""

    name: str
    """The name the case gives the marriage."""

    spouses: list[Party]
    """The spouses."""

    period: Period = field(default_factory=Period)
    """The days it lasts."""

    def is_between(self, person: Party, other_person: Party) -> bool:
        """:return: Whether *person* and *other_person*, two different parties, are its spouses."""
        return (
            person is not other_person
            and person in self.spouses
            and other_person in self.spouses
        )


class SeparationDecree(StrEnum):
    """The decrees `§ 7703(a)(2) <https://www.law.cornell.edu/uscode/text/26/7703#a_2>`__ legally separates spouses by, each named as SARA names it."""

    DIVORCE = "decree of divorce"
    """A decree of divorce."""

    SEPARATE_MAINTENANCE = "decree of separate maintenance"
    """A decree of separate maintenance."""


@dataclass(eq=False)
class LegalSeparation(Symbol):
    """The legal separation of spouses under a decree."""

    name: str
    """The name the case gives the separation."""

    marriage: Marriage
    """The marriage whose spouses are separated."""

    decree: SeparationDecree
    """The decree they are separated by."""

    day: datetime.date
    """The day it takes effect."""


@dataclass(eq=False)
class Kinship(Symbol):
    """That one party is a child of another."""

    parent: Party
    """The parent."""

    child: Party
    """The child."""

    period: Period = field(default_factory=Period)
    """The days the relation lasts."""


@dataclass(eq=False)
class Siblinghood(Symbol):
    """That two parties are brothers or sisters."""

    siblings: list[Party]
    """The siblings."""

    period: Period = field(default_factory=Period)
    """The days the relation lasts."""


@dataclass(eq=False)
class Residence(Symbol):
    """Parties living in a household."""

    name: str
    """The name the case gives the residence."""

    residents: list[Party]
    """Who lives there."""

    household: Household
    """Where they live."""

    period: Period = field(default_factory=Period)
    """The days they live there."""


@dataclass(eq=False)
class JointReturn(Symbol):
    """A single return of income taxes, made jointly by spouses."""

    name: str
    """The name the case gives the return."""

    filers: list[Party]
    """Who makes it."""

    period: Period = field(default_factory=Period)
    """The taxable period it is made for."""


@dataclass(eq=False)
class NonresidentAlienStatus(Symbol):
    """That a party is a nonresident alien."""

    person: Party
    """The nonresident alien."""

    period: Period = field(default_factory=Period)
    """The days they are one."""


# %% calendar years


@dataclass(eq=False)
class CalendarYear(Symbol):
    """A calendar year, with the days the employer provisions count from and to."""

    number: int
    """The year's number, such as 2017."""

    opening_day: datetime.date = field(init=False)
    """January 1 of the year."""

    closing_day: datetime.date = field(init=False)
    """December 31 of the year."""

    opening_day_of_preceding_year: datetime.date = field(init=False)
    """January 1 of the year before."""

    opening_day_of_following_year: datetime.date = field(init=False)
    """January 1 of the year after."""

    closing_day_of_preceding_year: datetime.date = field(init=False)
    """December 31 of the year before."""

    opening_day_of_year_before_preceding: datetime.date = field(init=False)
    """January 1 of the year two years before."""

    opening_day_of_last_six_months: datetime.date = field(init=False)
    """July 2, the first day SARA counts in the last 6 months of the year, which end on January 1 of the next."""

    half_length: float = field(init=False)
    """Half the number of days from its first to its last day, which SARA compares half a year with."""

    def __post_init__(self) -> None:
        """Sets the days the year and the years around it open and close on, and its half length."""
        self.opening_day = datetime.date(self.number, 1, 1)
        self.closing_day = datetime.date(self.number, 12, 31)
        self.opening_day_of_preceding_year = datetime.date(self.number - 1, 1, 1)
        self.opening_day_of_following_year = datetime.date(self.number + 1, 1, 1)
        self.closing_day_of_preceding_year = datetime.date(self.number - 1, 12, 31)
        self.opening_day_of_year_before_preceding = datetime.date(self.number - 2, 1, 1)
        self.opening_day_of_last_six_months = datetime.date(self.number, 7, 2)
        self.half_length = (self.closing_day - self.opening_day).days / 2

    @symbolic_function
    def days_within(self, period: Period) -> int:
        """
        :return: The number of days from the first to the last day the year shares with
            *period*, an open start or end bounded by the year; negative where they share none.
        """
        shared = Period(start=self.opening_day, end=self.closing_day).intersect(period)
        return (shared.end - shared.start).days

    @symbolic_function
    def days_spanned(self, period: Period) -> int:
        """:return: The number of days from the first to the last day of *period*, an open start or end taken as the year's."""
        start = self.opening_day if period.start is None else period.start
        end = self.closing_day if period.end is None else period.end
        return (end - start).days

    @symbolic_function
    def counts_younger_than_25(self, birth_day: datetime.date) -> bool:
        """:return: Whether someone born on *birth_day* is less than 25 years old at the close of the year, as SARA counts."""
        close_25_years_later = datetime.date(self.number + 25, 12, 31)
        return (self.closing_day - birth_day).days <= (
            close_25_years_later - self.closing_day
        ).days


# %% the circumstances of a case


@dataclass
class World:
    """Everything a case states that the modelled provisions ask about."""

    united_states: Country
    """The United States, as the case's places and citizenships refer to it."""

    parties: list[Party] = field(default_factory=list)
    """Every party the case names."""

    services: list[Service] = field(default_factory=list)
    """The services performed."""

    hospitals: list[Hospital] = field(default_factory=list)
    """The parties running a hospital."""

    hospital_stays: list[HospitalStay] = field(default_factory=list)
    """The stays of patients in hospitals."""

    international_organizations: list[InternationalOrganization] = field(
        default_factory=list
    )
    """The parties that are international organizations."""

    american_employers: list[AmericanEmployer] = field(default_factory=list)
    """The parties that are American employers."""

    migrations: list[Migration] = field(default_factory=list)
    """The admissions of parties to countries."""

    payments: list[Payment] = field(default_factory=list)
    """The payments made."""

    benefit_plans: list[EmployeeBenefitPlan] = field(default_factory=list)
    """The plans of employers."""

    terminations: list[Termination] = field(default_factory=list)
    """The terminations of services."""

    deaths: list[Death] = field(default_factory=list)
    """The deaths of parties."""

    marriages: list[Marriage] = field(default_factory=list)
    """The marriages between parties."""

    legal_separations: list[LegalSeparation] = field(default_factory=list)
    """The legal separations of spouses."""

    kinships: list[Kinship] = field(default_factory=list)
    """The relations of parents to their children."""

    siblinghoods: list[Siblinghood] = field(default_factory=list)
    """The relations of brothers and sisters."""

    births: list[Birth] = field(default_factory=list)
    """The births of parties."""

    residences: list[Residence] = field(default_factory=list)
    """Who lives in which household, and when."""

    incomes: list[Income] = field(default_factory=list)
    """The incomes earned other than by stated payments."""

    joint_returns: list[JointReturn] = field(default_factory=list)
    """The joint returns made."""

    nonresident_alien_statuses: list[NonresidentAlienStatus] = field(
        default_factory=list
    )
    """When parties are nonresident aliens."""

    stated_conclusions: list[SaraConclusion] = field(default_factory=list)
    """The conclusions of provisions the case states itself instead of the circumstances behind them."""

    calendar_years: list[CalendarYear] = field(default_factory=list)
    """The calendar years the case's days fall in, and each year after one of them."""

    @symbolic_function
    def lifetime(self, person: Party) -> Period:
        """:return: The days up to *person*'s death, open where the case states no day of it."""
        days = [
            death.day for death in self.deaths if death.person is person and death.day
        ]
        return Period(end=days[0] if days else None)

    def households(self) -> list[Household]:
        """:return: The households parties reside in, each once."""
        return list(dict.fromkeys(residence.household for residence in self.residences))

    def include_calendar_year(self, number: int) -> None:
        """Adds the calendar year numbered *number* to :attr:`calendar_years`, unless it is among them."""
        if any(year.number == number for year in self.calendar_years):
            return
        self.calendar_years.append(CalendarYear(number=number))
        self.calendar_years.sort(key=lambda year: year.number)
