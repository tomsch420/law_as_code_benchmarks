"""
Reads the facts of a SARA case into the domain model.

SARA states a case in Prolog facts about events: a fact such as ``service_(alice_employed)``
types an event, and facts such as ``agent_(alice_employed, bob)`` relate it to its participants.
This module is the only one that knows that vocabulary and SARA's naming conventions.
"""

from __future__ import annotations

import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum

from law_as_code_benchmarks.sara.domain import (
    AmericanEmployer,
    Country,
    ForeignGovernment,
    Hospital,
    HospitalStay,
    InternationalOrganization,
    LaborKind,
    Migration,
    Party,
    Place,
    Service,
    StateGovernment,
    UnitedStatesGovernment,
    World,
)
from law_as_code_benchmarks.sara.exceptions import ConflictingFacts, MissingFact
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm, PrologText, Term

# %% SARA's vocabulary


class EventType(StrEnum):
    """The functors SARA types an event with, among those the domain model reads."""

    SERVICE = "service_"
    """A service an employee performs for an employer."""

    HOSPITAL = "hospital_"
    """That its agent runs a hospital."""

    MEDICAL_PATIENT = "medical_patient_"
    """A stay of its agent as a patient of its patient, a hospital."""

    MIGRATION = "migration_"
    """An admission of its agent to its destination."""

    CITIZENSHIP = "citizenship_"
    """That its agent is a citizen of its patient, a country."""

    INTERNATIONAL_ORGANIZATION = "international_organization_"
    """That its agent is an international organization."""

    AMERICAN_EMPLOYER = "american_employer_"
    """That its agent is an American employer."""


class Relation(StrEnum):
    """The functors SARA relates an event to a value with, among those the domain model reads."""

    AGENT = "agent_"
    """Who or what acts in the event."""

    PATIENT = "patient_"
    """Who or what the event is done to."""

    START = "start_"
    """The day the event begins."""

    END = "end_"
    """The day the event ends."""

    LOCATION = "location_"
    """Where the event takes place."""

    PURPOSE = "purpose_"
    """What the event is for."""

    TYPE = "type_"
    """What sort of service the event is."""

    DESTINATION = "destination_"
    """Where a migration leads."""

    COUNTRY = "country_"
    """The country a place lies in; its first argument is the place, not an event."""


class SaraName(StrEnum):
    """The names SARA gives the things the domain model knows by kind rather than by name."""

    UNITED_STATES = "usa"
    """The United States."""

    UNITED_STATES_GOVERNMENT = "united states government"
    """The Government of the United States."""

    AGRICULTURAL_LABOR = "agricultural labor"
    """Agricultural labor, as the purpose or type of a service or a migration."""

    DOMESTIC_SERVICE = "domestic service"
    """Domestic service, as the purpose or type of a service."""


class GovernmentAffix(StrEnum):
    """How SARA's names of governments begin or end."""

    STATE = "state of "
    """The beginning of the name of a State or one of its subdivisions."""

    GOVERNMENT = " government"
    """The ending of the name of a government."""


# %% the facts of a case, indexed


@dataclass
class FactIndex:
    """A case's facts, indexed by what they type and relate."""

    typed: dict[EventType, list[Term]] = field(
        default_factory=lambda: defaultdict(list)
    )
    """The events each typing functor types, in the order the case states them."""

    related: dict[tuple[Relation, Term], list[Term]] = field(
        default_factory=lambda: defaultdict(list)
    )
    """The values each relation relates an event to, by relation and event."""

    @classmethod
    def from_facts(cls, facts: list[CompoundTerm]) -> FactIndex:
        """:return: The index of *facts*; facts of functors the domain model does not read are left out."""
        index = cls()
        event_types = set(EventType)
        relations = set(Relation)
        for fact in facts:
            if fact.functor in event_types and len(fact.arguments) == 1:
                index.typed[EventType(fact.functor)].append(fact.arguments[0])
            elif fact.functor in relations and len(fact.arguments) == 2:
                index.related[(Relation(fact.functor), fact.arguments[0])].append(
                    fact.arguments[1]
                )
        return index

    def values(self, relation: Relation, event: Term) -> list[Term]:
        """:return: The values *relation* relates *event* to."""
        return self.related.get((relation, event), [])

    def value(self, relation: Relation, event: Term) -> Term:
        """
        :return: The one value *relation* relates *event* to; None if it relates it to none.
        :raises ConflictingFacts: If it relates it to more than one.
        """
        values = self.values(relation, event)
        if len(values) > 1:
            raise ConflictingFacts(event=event, functor=relation.value)
        return values[0] if values else None

    def required_value(self, relation: Relation, event: Term) -> Term:
        """
        :return: The one value *relation* relates *event* to.
        :raises MissingFact: If it relates it to none.
        """
        value = self.value(relation, event)
        if value is None:
            raise MissingFact(event=event, functor=relation.value)
        return value


# %% reading the domain model


@dataclass
class WorldReader:
    """Builds the domain model of one case, each party, place and country once."""

    facts: FactIndex
    """The case's facts."""

    countries: dict[str, Country] = field(default_factory=dict)
    """The countries read so far, by name."""

    parties: dict[str, Party] = field(default_factory=dict)
    """The parties read so far, by name."""

    places: dict[str, Place] = field(default_factory=dict)
    """The places read so far, by name."""

    @classmethod
    def from_facts(cls, facts: list[CompoundTerm]) -> WorldReader:
        """:return: A reader of the case stating *facts*."""
        return cls(facts=FactIndex.from_facts(facts))

    def read(self) -> World:
        """:return: The circumstances the case's facts describe."""
        for citizenship in self.facts.typed[EventType.CITIZENSHIP]:
            self.party(
                self.facts.required_value(Relation.AGENT, citizenship)
            ).citizenships.append(
                self.country(self.facts.required_value(Relation.PATIENT, citizenship))
            )
        return World(
            united_states=self.country(SaraName.UNITED_STATES.value),
            services=[
                self.service(event) for event in self.facts.typed[EventType.SERVICE]
            ],
            hospitals=[
                Hospital(role_taker=party)
                for party in self.agents_of(EventType.HOSPITAL)
            ],
            hospital_stays=[
                self.hospital_stay(event)
                for event in self.facts.typed[EventType.MEDICAL_PATIENT]
            ],
            international_organizations=[
                InternationalOrganization(role_taker=party)
                for party in self.agents_of(EventType.INTERNATIONAL_ORGANIZATION)
            ],
            american_employers=[
                AmericanEmployer(role_taker=party)
                for party in self.agents_of(EventType.AMERICAN_EMPLOYER)
            ],
            migrations=[
                self.migration(event) for event in self.facts.typed[EventType.MIGRATION]
            ],
        )

    def agents_of(self, event_type: EventType) -> list[Party]:
        """:return: The parties acting in the events of *event_type*."""
        return [
            self.party(agent)
            for event in self.facts.typed[event_type]
            for agent in self.facts.values(Relation.AGENT, event)
        ]

    def service(self, event: Term) -> Service:
        """:return: The service *event* is."""
        start = self.facts.value(Relation.START, event)
        end = self.facts.value(Relation.END, event)
        return Service(
            name=self.text(event),
            employee=self.party(self.facts.required_value(Relation.AGENT, event)),
            employer=self.party(self.facts.required_value(Relation.PATIENT, event)),
            start=None if start is None else self.date(start),
            end=None if end is None else self.date(end),
            places=[
                self.place(location)
                for location in self.facts.values(Relation.LOCATION, event)
            ],
            kinds=self.labor_kinds(
                self.facts.values(Relation.PURPOSE, event)
                + self.facts.values(Relation.TYPE, event)
            ),
        )

    def hospital_stay(self, event: Term) -> HospitalStay:
        """:return: The hospital stay *event* is."""
        end = self.facts.value(Relation.END, event)
        return HospitalStay(
            patient=self.party(self.facts.required_value(Relation.AGENT, event)),
            hospital=self.party(self.facts.required_value(Relation.PATIENT, event)),
            start=self.date(self.facts.required_value(Relation.START, event)),
            end=None if end is None else self.date(end),
        )

    def migration(self, event: Term) -> Migration:
        """:return: The migration *event* is."""
        purposes = self.labor_kinds(self.facts.values(Relation.PURPOSE, event))
        return Migration(
            migrant=self.party(self.facts.required_value(Relation.AGENT, event)),
            destination=self.country(
                self.facts.required_value(Relation.DESTINATION, event)
            ),
            purpose=next(iter(purposes), None),
        )

    def party(self, term: Term) -> Party:
        """:return: The party named *term*, a government where SARA's name says so."""
        name = self.text(term)
        if name not in self.parties:
            self.parties[name] = self.party_class(name)(name=name)
        return self.parties[name]

    @staticmethod
    def party_class(name: str) -> type[Party]:
        """:return: The class of the party named *name*, read off SARA's naming of governments."""
        if name == SaraName.UNITED_STATES_GOVERNMENT:
            return UnitedStatesGovernment
        if name.startswith(GovernmentAffix.STATE):
            return StateGovernment
        if name.endswith(GovernmentAffix.GOVERNMENT):
            return ForeignGovernment
        return Party

    def place(self, term: Term) -> Place:
        """:return: The place named *term*, in the country the case puts it in, or itself the United States."""
        name = self.text(term)
        if name not in self.places:
            country = self.facts.value(Relation.COUNTRY, term)
            if country is not None:
                self.places[name] = Place(name=name, country=self.country(country))
            elif name == SaraName.UNITED_STATES:
                self.places[name] = Place(name=name, country=self.country(name))
            else:
                self.places[name] = Place(name=name)
        return self.places[name]

    def country(self, term: Term) -> Country:
        """:return: The country named *term*."""
        name = self.text(term)
        if name not in self.countries:
            self.countries[name] = Country(name=name)
        return self.countries[name]

    def labor_kinds(self, terms: list[Term]) -> set[LaborKind]:
        """:return: The kinds of work *terms* name, among those the provisions treat apart."""
        kinds = {
            SaraName.AGRICULTURAL_LABOR.value: LaborKind.AGRICULTURAL_LABOR,
            SaraName.DOMESTIC_SERVICE.value: LaborKind.DOMESTIC_SERVICE,
        }
        return {kinds[self.text(term)] for term in terms if self.text(term) in kinds}

    @staticmethod
    def text(term: Term) -> str:
        """:return: The characters of an atom or a string."""
        return term.value if isinstance(term, PrologText) else str(term)

    @staticmethod
    def date(term: Term) -> datetime.date:
        """:return: The day a ``YYYY-MM-DD`` string names, an overflowing day carried into the next month as Prolog does."""
        year, month, day = (int(part) for part in WorldReader.text(term).split("-"))
        return datetime.date(year, month, 1) + datetime.timedelta(days=day - 1)
