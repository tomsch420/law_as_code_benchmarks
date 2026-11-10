"""
The services § 3306(c) of the Internal Revenue Code excludes from *employment*, or brings
into it, as SARA's Prolog program states them.

Each rule follows the program's clause, its quirks included, so that it answers each goal
as the program does; a quirk the statute's text would not lead a reader to expect is noted.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from krrood.entity_query_language.factories import (
    an,
    and_,
    entity,
    exists,
    in_,
    inference,
    not_,
    or_,
    variable,
)
from krrood.entity_query_language.predicate import length
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from krrood.symbol_graph.symbol_graph import Symbol

from law_as_code_benchmarks.sara.prolog_term import PrologText, Term
from law_as_code_benchmarks.sara.provision import (
    Provision,
    SaraConclusion,
    SaraPredicate,
)
from law_as_code_benchmarks.sara.text_predicates import BeginsWith, EndsWith
from law_as_code_benchmarks.sara.world import Event, EventKind, SaraDate

# %% names the program compares with


class StatedName(StrEnum):
    """The names SARA's program compares a case's terms with, each a Prolog string there."""

    UNITED_STATES_GOVERNMENT = "united states government"
    """The employer § 3306(c)(6) names."""

    UNITED_STATES = "usa"
    """The country, as a citizenship, a destination or a place."""

    AGRICULTURAL_LABOR = "agricultural labor"
    """The purpose or type of agricultural labor."""

    def term(self) -> PrologText:
        """:return: The name as the Prolog string the program writes it as."""
        return PrologText(self.value)


class NameAffix(StrEnum):
    """The beginnings and endings of names SARA's program recognizes an employer by."""

    STATE = "state of "
    """How the name of a State, or of one of its subdivisions, begins."""

    GOVERNMENT = " government"
    """How the name of a government ends."""


# %% conclusions


@dataclass(eq=False)
class ExcludedService(SaraConclusion):
    """A service the statute excludes from employment."""

    service: Term
    """The service."""

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (self.service,)


@dataclass(eq=False)
class ExcludedServiceForEmployer(ExcludedService):
    """A service the statute excludes from employment because of whom it is performed for."""

    employer: Term
    """Whom it is performed for."""

    def prolog_arguments(self) -> tuple[Term, ...]:
        """Extends :meth:`ExcludedService.prolog_arguments` by the employer."""
        return self.service, self.employer


@dataclass(eq=False)
class ServiceOfHospitalPatient(ExcludedServiceForEmployer):
    """A service for a hospital by one of its patients, on a day of the patient's stay."""

    employee: Term
    """The patient performing it."""

    workday: Term
    """The day it is performed on, as the goal states it."""

    def prolog_arguments(self) -> tuple[Term, ...]:
        """Extends :meth:`ExcludedServiceForEmployer.prolog_arguments` by the patient and the day."""
        return self.service, self.employer, self.employee, self.workday


@dataclass(eq=False)
class ServiceAbroad(SaraConclusion):
    """A service outside the United States by a citizen for an American employer."""

    service: Term
    """The service."""

    employer: Term
    """The American employer."""

    employee: Term
    """The citizen performing it."""

    location: Term
    """The place outside the United States; None where the program leaves it unbound."""

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.service, self.employer, self.employee, self.location


@dataclass(eq=False)
class NoAdmittedAlienLabor(SaraConclusion):
    """That no agricultural labor of a service is performed by an alien admitted to perform it."""

    service: Term
    """The service, as the goal states it; None where it leaves it open."""

    employee: Term
    """Who performs it, as the goal states it; None where it leaves it open."""

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.service, self.employee


@dataclass(eq=False)
class Place(Symbol):
    """A place a service may be performed at, with the countries the case puts it in."""

    name: Term
    """The place; None for the place the program leaves unbound."""

    countries: list[Term]
    """The countries the case puts it in."""


# %% exclusions by employer


@dataclass
class UnitedStatesGovernmentExclusion(Provision[ExcludedService]):
    """
    § 3306(c)(6): service performed in the employ of the United States Government. The
    program reads it of any event, whether or not the case types it as a service.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """The predicate of :attr:`SaraPredicate.SERVICE_FOR_UNITED_STATES_GOVERNMENT`."""
        return SaraPredicate.SERVICE_FOR_UNITED_STATES_GOVERNMENT

    def query(self) -> Query:
        service = variable(Event, domain=list(self.world.events.values()))
        employer = variable(object, domain=self.world.participants())
        return an(
            entity(inference(ExcludedService)(service=service.identifier)).where(
                in_(employer, service.patients),
                employer == StatedName.UNITED_STATES_GOVERNMENT.term(),
            )
        )


@dataclass
class StateExclusion(Provision[ExcludedServiceForEmployer]):
    """
    § 3306(c)(7): service performed in the employ of a State, or a subdivision of one,
    which the program recognizes by a name beginning with *state of*.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """The predicate of :attr:`SaraPredicate.SERVICE_FOR_STATE`."""
        return SaraPredicate.SERVICE_FOR_STATE

    def query(self) -> Query:
        service = variable(Event, domain=list(self.world.events.values()))
        employer = variable(object, domain=self.world.participants())
        return an(
            entity(
                inference(ExcludedServiceForEmployer)(
                    service=service.identifier, employer=employer
                )
            ).where(
                in_(employer, service.patients),
                BeginsWith(employer, NameAffix.STATE.value),
            )
        )


@dataclass
class ForeignGovernmentExclusion(Provision[ExcludedServiceForEmployer]):
    """
    § 3306(c)(11): service performed in the employ of a foreign government, which the
    program recognizes by a name ending in *government* other than the United States'.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """The predicate of :attr:`SaraPredicate.SERVICE_FOR_FOREIGN_GOVERNMENT`."""
        return SaraPredicate.SERVICE_FOR_FOREIGN_GOVERNMENT

    def query(self) -> Query:
        service = variable(Event, domain=self.world.events_of(EventKind.SERVICE))
        employer = variable(object, domain=self.world.participants())
        return an(
            entity(
                inference(ExcludedServiceForEmployer)(
                    service=service.identifier, employer=employer
                )
            ).where(
                in_(employer, service.patients),
                EndsWith(employer, NameAffix.GOVERNMENT.value),
                employer != StatedName.UNITED_STATES_GOVERNMENT.term(),
            )
        )


@dataclass
class InternationalOrganizationExclusion(Provision[ExcludedServiceForEmployer]):
    """§ 3306(c)(16): service performed in the employ of an international organization."""

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """The predicate of :attr:`SaraPredicate.SERVICE_FOR_INTERNATIONAL_ORGANIZATION`."""
        return SaraPredicate.SERVICE_FOR_INTERNATIONAL_ORGANIZATION

    def query(self) -> Query:
        service = variable(Event, domain=self.world.events_of(EventKind.SERVICE))
        organization = variable(
            Event, domain=self.world.events_of(EventKind.INTERNATIONAL_ORGANIZATION)
        )
        employer = variable(object, domain=self.world.participants())
        return an(
            entity(
                inference(ExcludedServiceForEmployer)(
                    service=service.identifier, employer=employer
                )
            ).where(
                in_(employer, service.patients),
                in_(employer, organization.agents),
            )
        )


# %% exclusions by employee


@dataclass
class HospitalPatientExclusion(Provision[ServiceOfHospitalPatient]):
    """
    § 3306(c)(10)(B): service performed in the employ of a hospital by a patient of that
    hospital, on the day the goal names. A goal naming no day has no solution, as in the program.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """The predicate of :attr:`SaraPredicate.SERVICE_BY_HOSPITAL_PATIENT`."""
        return SaraPredicate.SERVICE_BY_HOSPITAL_PATIENT

    def query(self) -> Query:
        workday = self.goal.arguments[3]
        services = [] if workday is None else self.world.events_of(EventKind.SERVICE)
        service = variable(Event, domain=services)
        hospital = variable(Event, domain=self.world.events_of(EventKind.HOSPITAL))
        stay = variable(Event, domain=self.world.events_of(EventKind.MEDICAL_PATIENT))
        employer = variable(object, domain=self.world.participants())
        employee = variable(object, domain=self.world.participants())
        return an(
            entity(
                inference(ServiceOfHospitalPatient)(
                    service=service.identifier,
                    employer=employer,
                    employee=employee,
                    workday=workday,
                )
            ).where(
                in_(employer, service.patients),
                in_(employee, service.agents),
                in_(employer, hospital.agents),
                in_(employee, stay.agents),
                in_(employer, stay.patients),
                stay.is_ongoing_on(SaraDate.from_term(workday)),
            )
        )


@dataclass
class AdmittedAlienCondition(Provision[NoAdmittedAlienLabor]):
    """
    § 3306(c)(1)(B): the labor is not agricultural labor performed by an alien admitted to the
    United States to perform it. It holds where no service and employee the goal admits are such
    labor by an alien whose migration to the United States was for agricultural labor.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """The predicate of :attr:`SaraPredicate.LABOR_NOT_BY_ADMITTED_ALIEN`."""
        return SaraPredicate.LABOR_NOT_BY_ADMITTED_ALIEN

    def query(self) -> Query:
        asked_service, asked_employee = self.goal.arguments
        service = variable(Event, domain=self.services_asked(asked_service))
        employee = variable(
            object,
            domain=self.world.participants()
            if asked_employee is None
            else [asked_employee],
        )
        citizenship = variable(
            Event, domain=self.world.events_of(EventKind.CITIZENSHIP)
        )
        migration = variable(Event, domain=self.world.events_of(EventKind.MIGRATION))
        country = variable(object, domain=self.world.participants())
        agricultural_labor = StatedName.AGRICULTURAL_LABOR.term()
        united_states = StatedName.UNITED_STATES.term()
        admitted_alien_labor = and_(
            or_(
                in_(agricultural_labor, service.types),
                in_(agricultural_labor, service.purposes),
            ),
            in_(employee, citizenship.agents),
            exists(
                country,
                and_(in_(country, citizenship.patients), country != united_states),
            ),
            in_(employee, migration.agents),
            in_(united_states, migration.destinations),
            in_(agricultural_labor, migration.purposes),
        )
        return an(
            entity(
                inference(NoAdmittedAlienLabor)(
                    service=asked_service, employee=asked_employee
                )
            ).where(
                not_(
                    exists(
                        service,
                        exists(
                            employee,
                            exists(
                                citizenship, exists(migration, admitted_alien_labor)
                            ),
                        ),
                    )
                )
            )
        )

    def services_asked(self, asked_service: Term) -> list[Event]:
        """:return: The events the goal's service can be: the one it names, or any if it names none."""
        if asked_service is None:
            return list(self.world.events.values())
        event = self.world.find(asked_service)
        return [] if event is None else [event]


# %% inclusion of service abroad


@dataclass
class ServiceAbroadInclusion(Provision[ServiceAbroad]):
    """
    § 3306(c)(B): service performed outside the United States, other than in a contiguous country
    the United States has an unemployment compensation agreement with, by a citizen of the United
    States as an employee of an American employer.

    .. note:: The program does not tie the place to the service: an unbound place is any place
        the case puts in a country other than the United States, or, where the case puts no
        place in a country, stays unbound and passes.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """The predicate of :attr:`SaraPredicate.SERVICE_ABROAD_FOR_AMERICAN_EMPLOYER`."""
        return SaraPredicate.SERVICE_ABROAD_FOR_AMERICAN_EMPLOYER

    def query(self) -> Query:
        service = variable(Event, domain=list(self.world.events.values()))
        employer = variable(object, domain=self.world.participants())
        employee = variable(object, domain=self.world.participants())
        place = variable(Place, domain=self.places(self.goal.arguments[3]))
        country = variable(
            object,
            domain=[
                value
                for event in self.world.events.values()
                for value in event.countries
            ],
        )
        agreement = variable(
            Event,
            domain=self.world.events_of(EventKind.UNEMPLOYMENT_COMPENSATION_AGREEMENT),
        )
        american_employer = variable(
            Event, domain=self.world.events_of(EventKind.AMERICAN_EMPLOYER)
        )
        citizenship = variable(
            Event, domain=self.world.events_of(EventKind.CITIZENSHIP)
        )
        united_states = StatedName.UNITED_STATES.term()
        return an(
            entity(
                inference(ServiceAbroad)(
                    service=service.identifier,
                    employer=employer,
                    employee=employee,
                    location=place.name,
                )
            ).where(
                in_(employee, service.agents),
                in_(employer, service.patients),
                or_(
                    exists(
                        country,
                        and_(in_(country, place.countries), country != united_states),
                    ),
                    and_(length(place.countries) == 0, place.name != united_states),
                ),
                not_(
                    exists(
                        agreement,
                        and_(
                            in_(united_states, agreement.agents),
                            or_(place.name == None, in_(place.name, agreement.agents)),
                        ),
                    )
                ),
                exists(american_employer, in_(employer, american_employer.agents)),
                exists(
                    citizenship,
                    and_(
                        in_(employee, citizenship.agents),
                        in_(united_states, citizenship.patients),
                    ),
                ),
            )
        )

    def places(self, asked_location: Term) -> list[Place]:
        """
        :param asked_location: The place the goal names; None if it names none.
        :return: The places the program tries: the one named, else every place the case puts in a
            country, else the unbound place.
        """
        if asked_location is not None:
            event = self.world.find(asked_location)
            return [
                Place(
                    name=asked_location,
                    countries=[] if event is None else list(event.countries),
                )
            ]
        places = [
            Place(name=event.identifier, countries=list(event.countries))
            for event in self.world.events.values()
            if event.countries
        ]
        return places or [Place(name=None, countries=[])]
