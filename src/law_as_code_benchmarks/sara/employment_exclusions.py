"""
The services `§ 3306(c) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__ of the Internal Revenue Code excludes from *employment*, or
brings into it, as rules over the domain model.
"""

from __future__ import annotations

from dataclasses import dataclass

from krrood.entity_query_language.factories import (
    an,
    and_,
    entity,
    exists,
    in_,
    inference,
    not_,
    variable,
)
from krrood.entity_query_language.predicate import HasType
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.sara.case_reader import WorldReader
from law_as_code_benchmarks.sara.domain import (
    AmericanEmployer,
    ForeignGovernment,
    Hospital,
    HospitalStay,
    InternationalOrganization,
    LaborKind,
    Migration,
    Place,
    Service,
    StateGovernment,
    UnitedStatesGovernment,
)
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm, Term
from law_as_code_benchmarks.sara.provision import (
    Bindings,
    Provision,
    SaraConclusion,
    SaraPredicate,
)

# %% conclusions


@dataclass(eq=False)
class ExcludedService(SaraConclusion):
    """
    A service the statute excludes from employment.
    """

    service: Service
    """
    The service.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (self.service.name,)


@dataclass(eq=False)
class ExcludedServiceForEmployer(ExcludedService):
    """
    A service the statute excludes from employment because of whom it is performed for.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`ExcludedService.prolog_arguments` by the employer.
        """
        return self.service.name, self.service.employer.name


@dataclass(eq=False)
class ServiceOfHospitalPatient(ExcludedService):
    """
    A service for a hospital by one of its patients, during the patient's stay.
    """

    stay: HospitalStay
    """
    The patient's stay in the hospital.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`ExcludedService.prolog_arguments` by the hospital and the
        patient, the day left open.
        """
        return (
            self.service.name,
            self.service.employer.name,
            self.service.employee.name,
            None,
        )

    def unify(self, goal: CompoundTerm, bindings: Bindings) -> Bindings | None:
        """
        Extends :meth:`SaraConclusion.unify`: the goal must name a day of the stay.

        A goal naming no day has no answer, as in SARA.
        """
        *arguments, workday = goal.arguments
        workday = bindings.resolve(workday)
        if workday is None or not self.stay.includes(WorldReader.date(workday)):
            return None
        return super().unify(
            CompoundTerm(functor=goal.functor, arguments=(*arguments, None)), bindings
        )


@dataclass(eq=False)
class ServiceAbroad(SaraConclusion):
    """
    A service outside the United States by a citizen for an American employer.
    """

    service: Service
    """
    The service.
    """

    place: Place
    """
    Where it is performed, outside the United States.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.service.name,
            self.service.employer.name,
            self.service.employee.name,
            self.place.name,
        )


@dataclass(eq=False)
class LaborNotByAdmittedAlien(SaraConclusion):
    """
    A service that is not agricultural labor by an alien admitted to the United States
    to perform it.
    """

    service: Service
    """
    The service.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.service.name, self.service.employee.name


# %% exclusions by employer


@dataclass
class UnitedStatesGovernmentExclusion(Provision[ExcludedService]):
    """
    `§ 3306(c)(6) <https://www.law.cornell.edu/uscode/text/26/3306#c_6>`__: service performed in the employ of the United States Government.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.SERVICE_FOR_UNITED_STATES_GOVERNMENT`.
        """
        return SaraPredicate.SERVICE_FOR_UNITED_STATES_GOVERNMENT

    def query(self) -> Query:
        service = variable(Service, domain=self.world.services)
        return an(
            entity(inference(ExcludedService)(service=service)).where(
                HasType(variable=service.employer, types_=UnitedStatesGovernment)
            )
        )


@dataclass
class StateExclusion(Provision[ExcludedServiceForEmployer]):
    """
    `§ 3306(c)(7) <https://www.law.cornell.edu/uscode/text/26/3306#c_7>`__: service performed in the employ of a State, or a political subdivision
    of one.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.SERVICE_FOR_STATE`.
        """
        return SaraPredicate.SERVICE_FOR_STATE

    def query(self) -> Query:
        service = variable(Service, domain=self.world.services)
        return an(
            entity(inference(ExcludedServiceForEmployer)(service=service)).where(
                HasType(variable=service.employer, types_=StateGovernment)
            )
        )


@dataclass
class ForeignGovernmentExclusion(Provision[ExcludedServiceForEmployer]):
    """
    `§ 3306(c)(11) <https://www.law.cornell.edu/uscode/text/26/3306#c_11>`__: service performed in the employ of a foreign government.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.SERVICE_FOR_FOREIGN_GOVERNMENT`.
        """
        return SaraPredicate.SERVICE_FOR_FOREIGN_GOVERNMENT

    def query(self) -> Query:
        service = variable(Service, domain=self.world.services)
        return an(
            entity(inference(ExcludedServiceForEmployer)(service=service)).where(
                HasType(variable=service.employer, types_=ForeignGovernment)
            )
        )


@dataclass
class InternationalOrganizationExclusion(Provision[ExcludedServiceForEmployer]):
    """
    `§ 3306(c)(16) <https://www.law.cornell.edu/uscode/text/26/3306#c_16>`__: service performed in the employ of an international organization.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.SERVICE_FOR_INTERNATIONAL_ORGANIZATION`.
        """
        return SaraPredicate.SERVICE_FOR_INTERNATIONAL_ORGANIZATION

    def query(self) -> Query:
        service = variable(Service, domain=self.world.services)
        organization = variable(
            InternationalOrganization, domain=self.world.international_organizations
        )
        return an(
            entity(inference(ExcludedServiceForEmployer)(service=service)).where(
                service.employer == organization.role_taker
            )
        )


# %% exclusions by employee


@dataclass
class HospitalPatientExclusion(Provision[ServiceOfHospitalPatient]):
    """
    `§ 3306(c)(10)(B) <https://www.law.cornell.edu/uscode/text/26/3306#c_10_B>`__: service performed in the employ of a hospital by a patient of that
    hospital.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.SERVICE_BY_HOSPITAL_PATIENT`.
        """
        return SaraPredicate.SERVICE_BY_HOSPITAL_PATIENT

    def query(self) -> Query:
        service = variable(Service, domain=self.world.services)
        hospital = variable(Hospital, domain=self.world.hospitals)
        stay = variable(HospitalStay, domain=self.world.hospital_stays)
        return an(
            entity(
                inference(ServiceOfHospitalPatient)(service=service, stay=stay)
            ).where(
                service.employer == hospital.role_taker,
                stay.hospital == service.employer,
                stay.patient == service.employee,
            )
        )


@dataclass
class AdmittedAlienCondition(Provision[LaborNotByAdmittedAlien]):
    """
    `§ 3306(c)(1)(B) <https://www.law.cornell.edu/uscode/text/26/3306#c_1_B>`__: the condition that labor is not agricultural labor performed by an
    alien admitted to the United States to perform agricultural labor.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.LABOR_NOT_BY_ADMITTED_ALIEN`.
        """
        return SaraPredicate.LABOR_NOT_BY_ADMITTED_ALIEN

    def query(self) -> Query:
        service = variable(Service, domain=self.world.services)
        migration = variable(Migration, domain=self.world.migrations)
        united_states = self.world.united_states
        return an(
            entity(inference(LaborNotByAdmittedAlien)(service=service)).where(
                not_(
                    and_(
                        in_(LaborKind.AGRICULTURAL_LABOR, service.kinds),
                        service.employee.is_citizen_of_other_country_than(
                            united_states
                        ),
                        exists(
                            migration,
                            and_(
                                migration.migrant == service.employee,
                                migration.destination == united_states,
                                migration.purpose == LaborKind.AGRICULTURAL_LABOR,
                            ),
                        ),
                    )
                )
            )
        )


# %% inclusion of service abroad


@dataclass
class ServiceAbroadInclusion(Provision[ServiceAbroad]):
    """
    `§ 3306(c)(B) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__: service performed outside the United States by a citizen of the United
    States as an employee of an American employer.

    A place in no stated country is not taken to be abroad.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.SERVICE_ABROAD_FOR_AMERICAN_EMPLOYER`.
        """
        return SaraPredicate.SERVICE_ABROAD_FOR_AMERICAN_EMPLOYER

    def query(self) -> Query:
        service = variable(Service, domain=self.world.services)
        place = variable(
            Place,
            domain=[
                place for service in self.world.services for place in service.places
            ],
        )
        american_employer = variable(
            AmericanEmployer, domain=self.world.american_employers
        )
        united_states = self.world.united_states
        return an(
            entity(inference(ServiceAbroad)(service=service, place=place)).where(
                in_(place, service.places),
                place.country != None,
                place.country != united_states,
                exists(
                    american_employer, american_employer.role_taker == service.employer
                ),
                in_(united_states, service.employee.citizenships),
            )
        )
