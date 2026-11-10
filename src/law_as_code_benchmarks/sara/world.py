"""
What a SARA case states, as objects: its events, typed by facts such as
``marriage_(alice_and_bob)`` and related to their participants by role facts such as
``agent_(alice_and_bob, alice)``, and the statutes' conclusions it states outright.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import StrEnum

from krrood.symbol_graph.symbol_graph import Symbol

from law_as_code_benchmarks.sara.exceptions import AmbiguousRole
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm, PrologText, Term

# %% vocabulary


class EventKind(StrEnum):
    """The kinds SARA types an event or thing with, each the functor of its typing fact."""

    AMERICAN_EMPLOYER = "american_employer_"
    """Typed by ``american_employer_(Event)``: american employer."""
    ATTENDING_CLASSES = "attending_classes_"
    """Typed by ``attending_classes_(Event)``: attending classes."""
    BIRTH = "birth_"
    """Typed by ``birth_(Event)``: birth."""
    BLINDNESS = "blindness_"
    """Typed by ``blindness_(Event)``: blindness."""
    BROTHER = "brother_"
    """Typed by ``brother_(Event)``: brother."""
    BUSINESS = "business_"
    """Typed by ``business_(Event)``: business."""
    BUSINESS_TRUST = "business_trust_"
    """Typed by ``business_trust_(Event)``: business trust."""
    CITIZENSHIP = "citizenship_"
    """Typed by ``citizenship_(Event)``: citizenship."""
    DAUGHTER = "daughter_"
    """Typed by ``daughter_(Event)``: daughter."""
    DEATH = "death_"
    """Typed by ``death_(Event)``: death."""
    DEDUCTION = "deduction_"
    """Typed by ``deduction_(Event)``: deduction."""
    DISABILITY = "disability_"
    """Typed by ``disability_(Event)``: disability."""
    EDUCATIONAL_INSTITUTION = "educational_institution_"
    """Typed by ``educational_institution_(Event)``: educational institution."""
    ENROLLMENT = "enrollment_"
    """Typed by ``enrollment_(Event)``: enrollment."""
    FATHER = "father_"
    """Typed by ``father_(Event)``: father."""
    HOSPITAL = "hospital_"
    """Typed by ``hospital_(Event)``: hospital."""
    INCARCERATION = "incarceration_"
    """Typed by ``incarceration_(Event)``: incarceration."""
    INCOME = "income_"
    """Typed by ``income_(Event)``: income."""
    INTERNATIONAL_ORGANIZATION = "international_organization_"
    """Typed by ``international_organization_(Event)``: international organization."""
    JOINT_RETURN = "joint_return_"
    """Typed by ``joint_return_(Event)``: joint return."""
    LEGAL_SEPARATION = "legal_separation_"
    """Typed by ``legal_separation_(Event)``: legal separation."""
    MARRIAGE = "marriage_"
    """Typed by ``marriage_(Event)``: marriage."""
    MEDICAL_INSTITUTION = "medical_institution_"
    """Typed by ``medical_institution_(Event)``: medical institution."""
    MEDICAL_PATIENT = "medical_patient_"
    """Typed by ``medical_patient_(Event)``: medical patient."""
    MIGRATION = "migration_"
    """Typed by ``migration_(Event)``: migration."""
    MOTHER = "mother_"
    """Typed by ``mother_(Event)``: mother."""
    NONRESIDENT_ALIEN = "nonresident_alien_"
    """Typed by ``nonresident_alien_(Event)``: nonresident alien."""
    NURSES_TRAINING_SCHOOL = "nurses_training_school_"
    """Typed by ``nurses_training_school_(Event)``: nurses training school."""
    PAYMENT = "payment_"
    """Typed by ``payment_(Event)``: payment."""
    PENAL_INSTITUTION = "penal_institution_"
    """Typed by ``penal_institution_(Event)``: penal institution."""
    PLAN = "plan_"
    """Typed by ``plan_(Event)``: plan."""
    RESIDENCE = "residence_"
    """Typed by ``residence_(Event)``: residence."""
    RETIREMENT = "retirement_"
    """Typed by ``retirement_(Event)``: retirement."""
    SERVICE = "service_"
    """Typed by ``service_(Event)``: service."""
    SIBLING = "sibling_"
    """Typed by ``sibling_(Event)``: sibling."""
    SISTER = "sister_"
    """Typed by ``sister_(Event)``: sister."""
    SON = "son_"
    """Typed by ``son_(Event)``: son."""
    TERMINATION = "termination_"
    """Typed by ``termination_(Event)``: termination."""
    UNEMPLOYMENT_COMPENSATION_AGREEMENT = "unemployment_compensation_agreement_"
    """Typed by ``unemployment_compensation_agreement_(Event)``: unemployment compensation agreement."""


class EventRole(StrEnum):
    """The roles SARA relates an event or thing to a value with, each the functor of its fact."""

    AGENT = "agent_"
    """Who or what acts in an event."""
    PATIENT = "patient_"
    """Who or what an event is done to."""
    START = "start_"
    """The day an event begins."""
    END = "end_"
    """The day an event ends."""
    AMOUNT = "amount_"
    """The sum of money an event is for."""
    PURPOSE = "purpose_"
    """What an event is for."""
    LOCATION = "location_"
    """Where an event takes place."""
    MEANS = "means_"
    """How a payment is made."""
    TYPE = "type_"
    """What sort of service or business an event is."""
    REASON = "reason_"
    """The event another happens because of."""
    BENEFICIARY = "beneficiary_"
    """Who a plan pays out to."""
    DESTINATION = "destination_"
    """Where a migration leads."""
    COUNTRY = "country_"
    """The country a place lies in."""


# %% events


@dataclass(eq=False)
class Event(Symbol):
    """
    An event or thing a case's facts describe: a marriage, a payment, a plan, a place.
    Every role holds the values the case relates it to, in the order the case states them.
    """

    identifier: Term
    """The atom, or for a place sometimes the string, naming it in the facts."""

    kinds: set[EventKind] = field(default_factory=set)
    """What the case types it as."""

    agents: list[Term] = field(default_factory=list)
    """Who or what acts in it."""

    patients: list[Term] = field(default_factory=list)
    """Who or what it is done to."""

    starts: list[Term] = field(default_factory=list)
    """The days, as ``YYYY-MM-DD`` strings, it begins on."""

    ends: list[Term] = field(default_factory=list)
    """The days, as ``YYYY-MM-DD`` strings, it ends on."""

    amounts: list[Term] = field(default_factory=list)
    """The sums of money it is for, in dollars."""

    purposes: list[Term] = field(default_factory=list)
    """What it is for."""

    locations: list[Term] = field(default_factory=list)
    """Where it takes place."""

    means: list[Term] = field(default_factory=list)
    """How it is paid: in cash, in kind, or out of a plan."""

    types: list[Term] = field(default_factory=list)
    """What sort of service or business it is."""

    reasons: list[Term] = field(default_factory=list)
    """The events it happens because of."""

    beneficiaries: list[Term] = field(default_factory=list)
    """Who a plan pays out to."""

    destinations: list[Term] = field(default_factory=list)
    """Where a migration leads."""

    countries: list[Term] = field(default_factory=list)
    """The countries a place lies in."""

    def is_a(self, kind: EventKind) -> bool:
        """:return: Whether the case types this event as *kind*."""
        return kind in self.kinds

    def start(self) -> datetime.date | None:
        """
        :return: The day it begins on; None if the case states none.
        :raises AmbiguousRole: If the case states more than one.
        """
        return self.only_day(self.starts, EventRole.START)

    def end(self) -> datetime.date | None:
        """
        :return: The day it ends on; None if the case states none.
        :raises AmbiguousRole: If the case states more than one.
        """
        return self.only_day(self.ends, EventRole.END)

    def amount(self) -> int | float | None:
        """
        :return: The sum it is for; None if the case states none.
        :raises AmbiguousRole: If the case states more than one.
        """
        if len(self.amounts) > 1:
            raise AmbiguousRole(identifier=self.identifier, role=EventRole.AMOUNT)
        return self.amounts[0] if self.amounts else None

    def is_ongoing_on(self, day: datetime.date) -> bool:
        """
        :param day: A day.
        :return: Whether it has begun by *day* and not ended before it; one with no start has not begun.
        """
        start = self.start()
        end = self.end()
        return start is not None and start <= day and (end is None or day <= end)

    def only_day(self, days: list[Term], role: EventRole) -> datetime.date | None:
        """
        :param days: The values of a role holding days.
        :param role: That role.
        :return: The one day it holds; None if it holds none.
        :raises AmbiguousRole: If it holds more than one.
        """
        if len(days) > 1:
            raise AmbiguousRole(identifier=self.identifier, role=role)
        return SaraDate.from_term(days[0]) if days else None


@dataclass(frozen=True)
class SaraDate:
    """The days SARA writes as ``YYYY-MM-DD`` strings."""

    @staticmethod
    def from_term(term: Term) -> datetime.date:
        """
        :param term: A day as SARA writes it.
        :return: That day.
        """
        text = term.value if isinstance(term, PrologText) else str(term)
        year, month, day = (int(part) for part in text.split("-"))
        return datetime.date(year, month, 1) + datetime.timedelta(days=day - 1)


# %% the world of a case


@dataclass
class World:
    """Everything a case states: its events and the statutes' conclusions it states outright."""

    events: dict[Term, Event] = field(default_factory=dict)
    """The events and things, by identifier."""

    stated_conclusions: list[CompoundTerm] = field(default_factory=list)
    """The facts of the statutes' own predicates the case states, such as ``s151_b_applies(alice,2015)``."""

    @classmethod
    def from_facts(cls, facts: list[CompoundTerm]) -> World:
        """
        :param facts: A case's ground facts.
        :return: The world they describe.
        """
        world = cls()
        kinds = set(EventKind)
        roles = {role.value: role for role in EventRole}
        for fact in facts:
            if fact.functor in kinds and len(fact.arguments) == 1:
                world.event(fact.arguments[0]).kinds.add(EventKind(fact.functor))
            elif fact.functor in roles and len(fact.arguments) == 2:
                world.add_role(
                    roles[fact.functor], fact.arguments[0], fact.arguments[1]
                )
            else:
                world.stated_conclusions.append(fact)
        return world

    def event(self, identifier: Term) -> Event:
        """:return: The event named *identifier*, created if the world holds none yet."""
        key = self.key(identifier)
        if key not in self.events:
            self.events[key] = Event(identifier=identifier)
        return self.events[key]

    def add_role(self, role: EventRole, identifier: Term, value: Term) -> None:
        """Relate the event named *identifier* to *value* in *role*, unless it already is."""
        values = self.role_values(self.event(identifier), role)
        if value not in values:
            values.append(value)

    @staticmethod
    def role_values(event: Event, role: EventRole) -> list[Term]:
        """:return: The list holding *event*'s values in *role*."""
        match role:
            case EventRole.AGENT:
                return event.agents
            case EventRole.PATIENT:
                return event.patients
            case EventRole.START:
                return event.starts
            case EventRole.END:
                return event.ends
            case EventRole.AMOUNT:
                return event.amounts
            case EventRole.PURPOSE:
                return event.purposes
            case EventRole.LOCATION:
                return event.locations
            case EventRole.MEANS:
                return event.means
            case EventRole.TYPE:
                return event.types
            case EventRole.REASON:
                return event.reasons
            case EventRole.BENEFICIARY:
                return event.beneficiaries
            case EventRole.DESTINATION:
                return event.destinations
            case EventRole.COUNTRY:
                return event.countries

    @staticmethod
    def key(identifier: Term) -> Term:
        """:return: *identifier* as a dictionary key; a list is not hashable, so it becomes a tuple."""
        return tuple(identifier) if isinstance(identifier, list) else identifier

    def events_of(self, kind: EventKind) -> list[Event]:
        """:return: The events the case types as *kind*."""
        return [event for event in self.events.values() if event.is_a(kind)]

    def participants(self) -> list[Term]:
        """:return: Every agent and patient of the case's events, each once, in the order the case states them."""
        values = [
            value
            for event in self.events.values()
            for value in event.agents + event.patients
        ]
        return list(dict.fromkeys(self.key(value) for value in values))

    def find(self, identifier: Term) -> Event | None:
        """:return: The event named *identifier*; None if the case describes none."""
        return self.events.get(self.key(identifier))
