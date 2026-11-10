"""
The circumstances SARA's cases describe, as a domain model: parties, the services they
perform for one another, where, and the roles and relations the employment-tax provisions
ask about.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum, auto

from krrood.patterns.role import Role
from krrood.symbol_graph.symbol_graph import Symbol

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
