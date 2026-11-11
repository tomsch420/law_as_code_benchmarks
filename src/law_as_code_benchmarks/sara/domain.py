"""
The circumstances SARA's cases describe, as a domain model: parties, the services they
perform for one another, where, what is paid for them, and the roles, relations and
events the employment-tax provisions ask about.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum, StrEnum, auto

from krrood.patterns.role import Role
from krrood.symbol_graph.symbol_graph import Symbol
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from law_as_code_benchmarks.sara.provision import SaraConclusion

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
    """The places § 3306(c)(2) treats domestic service at apart, each named as SARA names it."""

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


class PlanPurpose(Enum):
    """The provisions a plan of an employer makes, among those § 3306(b) treats apart."""

    SICKNESS = auto()
    """Provision for employees in case of sickness."""

    ACCIDENT_DISABILITY = auto()
    """Provision for employees in case of accident disability."""

    DEATH = auto()
    """Provision for employees in case of death."""

    EMPLOYEES_OR_DEPENDENTS = auto()
    """Provision for employees or their dependents generally."""


@dataclass(eq=False)
class Plan(Symbol):
    """A plan or fund an employer pays into, or pays from, for the benefit of others."""

    name: str
    """The plan's name."""

    sponsor: Party | None = None
    """Who established it; None where the case does not say."""

    purposes: set[PlanPurpose] = field(default_factory=set)
    """The provisions it makes, among those § 3306(b) treats apart."""

    beneficiaries: list[Party] = field(default_factory=list)
    """Whom it benefits."""

    def makes_any_provision(self, purposes: set[PlanPurpose]) -> bool:
        """:return: Whether it makes one of the provisions *purposes* name."""
        return not self.purposes.isdisjoint(purposes)


class Medium(StrEnum):
    """The media of payment the provisions treat apart."""

    CASH = "cash"
    """Cash."""


@dataclass(eq=False)
class Payment(Symbol):
    """A payment from one party to another party or into a plan."""

    name: str | None
    """The name the case gives the payment; None where it leaves the payment unnamed."""

    payer: Party | None
    """Who pays; None where the case does not say."""

    recipient: Party | Plan | None
    """Who or what is paid; None where the case does not say."""

    amount: float
    """How much is paid."""

    day: datetime.date | None = None
    """The day it is paid; None where the case does not say."""

    service: Service | None = None
    """The service it is paid for; None where it is not paid for a service."""

    medium: str | None = None
    """What it is paid in, such as ``cash``; None where the case does not say."""

    plan_drawn_on: Plan | None = None
    """The plan it is paid from; None where it is not paid from a plan."""

    def amount_up_to(self, limit: float) -> float:
        """:return: The amount, counted up to *limit*."""
        return min(limit, self.amount)

    def plans(self) -> list[Plan]:
        """:return: The plans it is paid into or from."""
        return [
            plan
            for plan in (self.recipient, self.plan_drawn_on)
            if isinstance(plan, Plan)
        ]

    def payees(self) -> list[Party]:
        """:return: Who receives the payment: its recipient, or the beneficiaries of the plan paid into."""
        if isinstance(self.recipient, Plan):
            return self.recipient.beneficiaries
        return [] if self.recipient is None else [self.recipient]

    def is_in_cash(self) -> bool:
        """:return: Whether it is paid in cash, which it is taken to be where the case names no medium."""
        return self.medium is None or self.medium == Medium.CASH

    def is_in_other_medium_than_cash(self) -> bool:
        """:return: Whether the case names a medium it is paid in other than cash."""
        return self.medium is not None and self.medium != Medium.CASH


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
class Marriage(Symbol):
    """A marriage between two parties."""

    spouses: list[Party]
    """The spouses."""

    start: datetime.date | None = None
    """The first day of it; None where the case does not say."""

    end: datetime.date | None = None
    """The last day of it; None where it goes on."""


@dataclass(eq=False)
class Kinship(Symbol):
    """That one party is a child of another."""

    parent: Party
    """The parent."""

    child: Party
    """The child."""


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

    def __post_init__(self) -> None:
        """Sets the days the year opens and closes on, and the day the year before opens on."""
        self.opening_day = datetime.date(self.number, 1, 1)
        self.closing_day = datetime.date(self.number, 12, 31)
        self.opening_day_of_preceding_year = datetime.date(self.number - 1, 1, 1)


# %% the circumstances of a case


@dataclass
class World:
    """Everything a case states that the modelled provisions ask about."""

    united_states: Country
    """The United States, as the case's places and citizenships refer to it."""

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

    plans: list[Plan] = field(default_factory=list)
    """The plans of employers."""

    terminations: list[Termination] = field(default_factory=list)
    """The terminations of services."""

    deaths: list[Death] = field(default_factory=list)
    """The deaths of parties."""

    marriages: list[Marriage] = field(default_factory=list)
    """The marriages between parties."""

    kinships: list[Kinship] = field(default_factory=list)
    """The relations of parents to their children."""

    stated_conclusions: list[SaraConclusion] = field(default_factory=list)
    """The conclusions of provisions the case states itself instead of the circumstances behind them."""

    calendar_years: list[CalendarYear] = field(default_factory=list)
    """The calendar years the case's days fall in, and each year after one of them."""
