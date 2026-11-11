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
    CalendarYear,
    Country,
    Death,
    Disability,
    ForeignGovernment,
    Hospital,
    HospitalStay,
    InternationalOrganization,
    Kinship,
    LaborKind,
    Marriage,
    Migration,
    Party,
    Payment,
    Place,
    Plan,
    PlanPurpose,
    Service,
    StateGovernment,
    Termination,
    UnitedStatesGovernment,
    World,
)
from law_as_code_benchmarks.sara.employment_tax_conclusions import (
    Employer,
    Employment,
    TotalWages,
    Wages,
)
from law_as_code_benchmarks.sara.exceptions import ConflictingFacts, MissingFact
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm, PrologText, Term
from law_as_code_benchmarks.sara.provision import SaraConclusion, SaraPredicate

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

    PAYMENT = "payment_"
    """A payment by its agent to its patient."""

    PLAN = "plan_"
    """That the event's name is that of a plan."""

    TERMINATION = "termination_"
    """Its agent ending its patient, a service."""

    DEATH = "death_"
    """The death of its agent."""

    DISABILITY = "disability_"
    """Its agent becoming disabled."""

    MARRIAGE = "marriage_"
    """A marriage between its agents."""

    SON = "son_"
    """That its agent is a son of its patient."""

    DAUGHTER = "daughter_"
    """That its agent is a daughter of its patient."""

    FATHER = "father_"
    """That its agent is the father of its patient."""

    MOTHER = "mother_"
    """That its agent is the mother of its patient."""


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

    AMOUNT = "amount_"
    """How much a payment is."""

    MEANS = "means_"
    """What a payment is paid in, or the plan it is paid from."""

    BENEFICIARY = "beneficiary_"
    """Whom a plan benefits."""

    REASON = "reason_"
    """Why an event happens."""


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

    PROVISION_IN_CASE_OF_SICKNESS = "make provisions for employees in case of sickness"
    """The purpose of a plan for employees in case of sickness."""

    PROVISION_IN_CASE_OF_ACCIDENT_DISABILITY = (
        "make provisions for employees in case of accident disability"
    )
    """The purpose of a plan for employees in case of accident disability."""

    PROVISION_IN_CASE_OF_DEATH = "make provisions for employees in case of death"
    """The purpose of a plan for employees in case of death."""

    PROVISION_FOR_EMPLOYEES_OR_DEPENDENTS = (
        "make provisions for employees or dependents"
    )
    """The purpose of a plan for employees or their dependents generally."""


class GovernmentAffix(StrEnum):
    """How SARA's names of governments begin or end."""

    STATE = "state of "
    """The beginning of the name of a State or one of its subdivisions."""

    GOVERNMENT = " government"
    """The ending of the name of a government."""


class StatedPredicate(StrEnum):
    """The predicates whose conclusions the domain model reads where a case states them as facts."""

    EMPLOYMENT = SaraPredicate.EMPLOYMENT.value
    """§ 3306(c): employment."""

    WAGES = SaraPredicate.WAGES.value
    """§ 3306(b): wages."""

    EMPLOYER = SaraPredicate.EMPLOYER.value
    """§ 3306(a): an employer for a year."""

    TOTAL_WAGES = SaraPredicate.TOTAL_WAGES.value
    """The total wages of an employer in a period."""


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

    stated: dict[SaraPredicate, list[CompoundTerm]] = field(
        default_factory=lambda: defaultdict(list)
    )
    """The conclusions of provisions the case states as facts, by predicate."""

    @classmethod
    def from_facts(cls, facts: list[CompoundTerm]) -> FactIndex:
        """:return: The index of *facts*; facts of functors the domain model does not read are left out."""
        index = cls()
        event_types = set(EventType)
        relations = set(Relation)
        stated_predicates = set(StatedPredicate)
        for fact in facts:
            if fact.functor in stated_predicates:
                index.stated[SaraPredicate(fact.functor)].append(fact)
            elif fact.functor in event_types and len(fact.arguments) == 1:
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

    services: dict[str, Service] = field(default_factory=dict)
    """The services read so far, by name, those only a stated conclusion names included."""

    plans: dict[str, Plan] = field(default_factory=dict)
    """The plans, by name."""

    payments: dict[str, Payment] = field(default_factory=dict)
    """The payments read so far, by name, those only a stated conclusion names included."""

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
        services = [
            self.service(event) for event in self.facts.typed[EventType.SERVICE]
        ]
        plans = [self.plan(event) for event in self.facts.typed[EventType.PLAN]]
        payments = [
            payment
            for event in self.facts.typed[EventType.PAYMENT]
            for payment in self.payments_of(event)
        ]
        stated_conclusions = self.stated_conclusions()
        return World(
            united_states=self.country(SaraName.UNITED_STATES.value),
            services=services,
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
            payments=payments,
            plans=plans,
            terminations=[
                self.termination(event)
                for event in self.facts.typed[EventType.TERMINATION]
            ],
            deaths=[self.death(event) for event in self.facts.typed[EventType.DEATH]],
            marriages=[
                self.marriage(event) for event in self.facts.typed[EventType.MARRIAGE]
            ],
            kinships=self.kinships(),
            stated_conclusions=stated_conclusions,
            calendar_years=self.calendar_years(
                [payment.day for payment in payments]
                + [
                    day
                    for service in self.services.values()
                    for day in (service.start, service.end)
                ]
                + [
                    conclusion.workday
                    for conclusion in stated_conclusions
                    if isinstance(conclusion, Employment)
                ]
            ),
        )

    @staticmethod
    def calendar_years(days: list[datetime.date | None]) -> list[CalendarYear]:
        """:return: The calendar years *days* fall in, and each year after one of them."""
        numbers = {day.year + offset for day in days if day for offset in (0, 1)}
        return [CalendarYear(number=number) for number in sorted(numbers)]

    def agents_of(self, event_type: EventType) -> list[Party]:
        """:return: The parties acting in the events of *event_type*."""
        return [
            self.party(agent)
            for event in self.facts.typed[event_type]
            for agent in self.facts.values(Relation.AGENT, event)
        ]

    def service(self, event: Term) -> Service:
        """:return: The service *event* is."""
        return self.service_by(
            event,
            employee=self.facts.required_value(Relation.AGENT, event),
            employer=self.facts.required_value(Relation.PATIENT, event),
        )

    def service_by(self, event: Term, employee: Term, employer: Term) -> Service:
        """:return: The service *event* is, by *employee* for *employer*, read once from its facts."""
        name = self.text(event)
        if name in self.services:
            return self.services[name]
        start = self.facts.value(Relation.START, event)
        end = self.facts.value(Relation.END, event)
        self.services[name] = Service(
            name=name,
            employee=self.party(employee),
            employer=self.party(employer),
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
            purposes=self.labor_kinds(self.facts.values(Relation.PURPOSE, event)),
        )
        return self.services[name]

    def plan(self, event: Term) -> Plan:
        """:return: The plan *event* names."""
        sponsor = self.facts.value(Relation.AGENT, event)
        purposes = {
            SaraName.PROVISION_IN_CASE_OF_SICKNESS.value: PlanPurpose.SICKNESS,
            SaraName.PROVISION_IN_CASE_OF_ACCIDENT_DISABILITY.value: PlanPurpose.ACCIDENT_DISABILITY,
            SaraName.PROVISION_IN_CASE_OF_DEATH.value: PlanPurpose.DEATH,
            SaraName.PROVISION_FOR_EMPLOYEES_OR_DEPENDENTS.value: PlanPurpose.EMPLOYEES_OR_DEPENDENTS,
        }
        plan = Plan(
            name=self.text(event),
            sponsor=None if sponsor is None else self.party(sponsor),
            purposes={
                purposes[self.text(purpose)]
                for purpose in self.facts.values(Relation.PURPOSE, event)
                if self.text(purpose) in purposes
            },
            beneficiaries=[
                self.party(beneficiary)
                for beneficiary in self.facts.values(Relation.BENEFICIARY, event)
            ],
        )
        self.plans[plan.name] = plan
        return plan

    def payments_of(self, event: Term) -> list[Payment]:
        """:return: The payments *event* is, one for each day it is made on; plans are read beforehand."""
        payer = self.facts.value(Relation.AGENT, event)
        recipient = self.facts.value(Relation.PATIENT, event)
        days = self.facts.values(Relation.START, event) or [None]
        means = self.facts.value(Relation.MEANS, event)
        services = [
            self.services[self.text(purpose)]
            for purpose in self.facts.values(Relation.PURPOSE, event)
            if self.text(purpose) in self.services
        ]
        payments = [
            Payment(
                name=self.text(event),
                payer=None if payer is None else self.party(payer),
                recipient=None
                if recipient is None
                else self.plans.get(self.text(recipient)) or self.party(recipient),
                amount=self.facts.required_value(Relation.AMOUNT, event),
                day=None if day is None else self.date(day),
                service=next(iter(services), None),
                medium=None
                if means is None or self.text(means) in self.plans
                else self.text(means),
                plan_drawn_on=None
                if means is None
                else self.plans.get(self.text(means)),
            )
            for day in days
        ]
        self.payments[self.text(event)] = payments[0]
        return payments

    def termination(self, event: Term) -> Termination:
        """:return: The termination *event* is; services are read beforehand."""
        day = self.facts.value(Relation.START, event)
        reasons = [
            self.text(reason) for reason in self.facts.values(Relation.REASON, event)
        ]
        return Termination(
            employer=self.party(self.facts.required_value(Relation.AGENT, event)),
            service=self.service(self.facts.required_value(Relation.PATIENT, event)),
            day=None if day is None else self.date(day),
            reasons=[
                self.death(reason)
                for reason in self.facts.typed[EventType.DEATH]
                if self.text(reason) in reasons
            ]
            + [
                Disability(
                    person=self.party(self.facts.required_value(Relation.AGENT, reason))
                )
                for reason in self.facts.typed[EventType.DISABILITY]
                if self.text(reason) in reasons
            ],
        )

    def death(self, event: Term) -> Death:
        """:return: The death *event* is."""
        day = self.facts.value(Relation.START, event)
        return Death(
            person=self.party(self.facts.required_value(Relation.AGENT, event)),
            day=None if day is None else self.date(day),
        )

    def marriage(self, event: Term) -> Marriage:
        """:return: The marriage *event* is."""
        start = self.facts.value(Relation.START, event)
        end = self.facts.value(Relation.END, event)
        return Marriage(
            spouses=[
                self.party(spouse)
                for spouse in self.facts.values(Relation.AGENT, event)
            ],
            start=None if start is None else self.date(start),
            end=None if end is None else self.date(end),
        )

    def kinships(self) -> list[Kinship]:
        """:return: The relations of parents to children, whether stated from the child's side or the parent's."""
        kinships = []
        for event_type, child_relation in (
            (EventType.SON, Relation.AGENT),
            (EventType.DAUGHTER, Relation.AGENT),
            (EventType.FATHER, Relation.PATIENT),
            (EventType.MOTHER, Relation.PATIENT),
        ):
            parent_relation = (
                Relation.PATIENT if child_relation == Relation.AGENT else Relation.AGENT
            )
            for event in self.facts.typed[event_type]:
                for parent in self.facts.values(parent_relation, event):
                    for child in self.facts.values(child_relation, event):
                        if self.party(parent) is not self.party(child):
                            kinships.append(
                                Kinship(
                                    parent=self.party(parent), child=self.party(child)
                                )
                            )
        return kinships

    def stated_conclusions(self) -> list[SaraConclusion]:
        """:return: The conclusions the case states as facts, each read into the domain model."""
        return (
            [
                Employment(
                    service=self.service_by(service, employee, employer),
                    workday=None if workday is None else self.date(workday),
                    year=year,
                )
                for service, employer, employee, workday, year in self.stated_arguments(
                    SaraPredicate.EMPLOYMENT
                )
            ]
            + [
                self.stated_wages(*arguments)
                for arguments in self.stated_arguments(SaraPredicate.WAGES)
            ]
            + [
                Employer(party=self.party(employer), year=year)
                for employer, year in self.stated_arguments(SaraPredicate.EMPLOYER)
            ]
            + [
                TotalWages(
                    employer=self.party(employer),
                    amount=amount,
                    first_day=self.date(first_day),
                    last_day=self.date(last_day),
                )
                for employer, amount, _, _, first_day, last_day in self.stated_arguments(
                    SaraPredicate.TOTAL_WAGES
                )
            ]
        )

    def stated_arguments(self, predicate: SaraPredicate) -> list[tuple[Term, ...]]:
        """:return: The arguments of each fact the case states of *predicate*."""
        return [fact.arguments for fact in self.facts.stated[predicate]]

    def stated_wages(
        self,
        amount: float,
        payment: Term,
        service: Term,
        payer: Term,
        payee: Term,
        employer: Term,
        employee: Term,
        medium: Term,
    ) -> Wages:
        """
        :return: The wages a stated fact of § 3306(b) states, in the program's order of
            arguments; a payment the case states no event of is taken to be made on the
            first day of its service.
        """
        stated_service = self.service_by(service, employee, employer)
        if payment is not None and self.text(payment) in self.payments:
            stated_payment = self.payments[self.text(payment)]
        else:
            stated_payment = Payment(
                name=None if payment is None else self.text(payment),
                payer=self.party(payer),
                recipient=self.party(payee),
                amount=amount,
                day=stated_service.start,
                service=stated_service,
                medium=None if medium is None else self.text(medium),
            )
        return Wages(
            amount=amount,
            payment=stated_payment,
            service=stated_service,
            payee=self.party(payee),
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
