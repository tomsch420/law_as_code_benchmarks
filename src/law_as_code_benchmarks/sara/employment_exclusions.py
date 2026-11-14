"""
The services `§ 3306(c) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__ of the Internal Revenue Code excludes from *employment*, or
brings into it, as rules over the domain model.
"""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass

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
from krrood.entity_query_language.predicate import HasType
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.sara.case_reader import WorldReader
from law_as_code_benchmarks.law.period import Period
from law_as_code_benchmarks.sara.domain import (
    AmericanEmployer,
    Birth,
    ClassAttendance,
    EducationalInstitution,
    Enrollment,
    ForeignGovernment,
    Hospital,
    HospitalStay,
    Incarceration,
    InternationalOrganization,
    Kinship,
    LaborKind,
    Marriage,
    Migration,
    Party,
    Place,
    Service,
    StateGovernment,
    UnitedStatesGovernment,
)
from law_as_code_benchmarks.sara.family_status import MarriedIndividualTest
from law_as_code_benchmarks.sara.family_status_conclusions import MarriedIndividual
from law_as_code_benchmarks.sara.prolog_term import Term
from law_as_code_benchmarks.sara.provision import (
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
class ExcludedAgriculturalLabor(ExcludedService):
    """
    Agricultural labor the statute excludes from employment in a calendar year.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.service.name, self.year


@dataclass(eq=False)
class ExcludedDomesticService(ExcludedService):
    """
    Domestic service at a private home, college club or chapter that the statute
    excludes from employment in a calendar year.
    """

    place: Place
    """
    Where it is performed.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.service.name, self.place.name, self.year


@dataclass(eq=False)
class DayBoundConclusion(SaraConclusion, ABC):
    """
    A conclusion that holds on the days of some periods only; its last argument is the
    day, which the conclusion leaves open.
    """

    @abstractmethod
    def bounding_periods(self) -> list[Period]:
        """:return: The periods every day the conclusion holds on falls within."""

    def agrees_with_argument(self, position: int, asked: Term) -> bool:
        """
        Extends :meth:`SaraConclusion.agrees_with_argument`: the day must fall within
        every period of :meth:`bounding_periods`.

        A goal naming no day has an answer only where no period bounds the day, as in
        SARA.
        """
        if position < len(self.prolog_arguments()) - 1:
            return super().agrees_with_argument(position, asked)
        periods = self.bounding_periods()
        if asked is None:
            return not periods
        day = WorldReader.date(asked)
        return all(period.contains(day) for period in periods)


@dataclass(eq=False)
class ExcludedServiceOnDay(ExcludedService, DayBoundConclusion, ABC):
    """
    A service the statute excludes from employment on the days of some periods only.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`ExcludedService.prolog_arguments` by the employer and the
        employee, the day left open.
        """
        return (
            self.service.name,
            self.service.employer.name,
            self.service.employee.name,
            None,
        )


@dataclass(eq=False)
class ServiceOfHospitalPatient(ExcludedServiceOnDay):
    """
    A service for a hospital by one of its patients, during the patient's stay.
    """

    stay: HospitalStay
    """
    The patient's stay in the hospital.
    """

    def bounding_periods(self) -> list[Period]:
        return [Period(lower=self.stay.start, upper=self.stay.end)]


@dataclass(eq=False)
class StudentAtSchool(DayBoundConclusion):
    """
    A student enrolled at an institution and regularly attending classes at it.
    """

    enrollment: Enrollment
    """
    The student's enrollment.
    """

    attendance: ClassAttendance
    """
    The student's attendance at classes at the same institution.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.enrollment.student.name, self.enrollment.institution.name, None

    def bounding_periods(self) -> list[Period]:
        return [self.enrollment.period, self.attendance.period]


@dataclass(eq=False)
class MarriedStudent(DayBoundConclusion):
    """
    A student married under `§ 7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__, in the year of the day and on it.

    SARA's program asks this as ``s3306_c_10_A_ii(Spouse, Student, Day)`` but checks
    that its first argument is the student; the arguments follow the program.
    """

    student: StudentAtSchool
    """
    The student.
    """

    marriage: MarriedIndividual
    """
    The student's marriage, its spouse being the student.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.marriage.spouse.name, self.marriage.person.name, None

    def bounding_periods(self) -> list[Period]:
        return self.student.bounding_periods() + [
            self.marriage.marriage.period,
            Period(
                lower=datetime.date(self.marriage.year, 1, 1),
                upper=datetime.date(self.marriage.year, 12, 31),
            ),
        ]


@dataclass(eq=False)
class ServiceOfStudent(ExcludedServiceOnDay):
    """
    A service for a school, college or university by a student of it, or by a married
    student whose spouse is a student of it.
    """

    student: StudentAtSchool
    """
    The student of the institution served.
    """

    married_student: MarriedStudent | None = None
    """
    The employee, married to :attr:`student`; None where the employee is the student.
    """

    def bounding_periods(self) -> list[Period]:
        if self.married_student is None:
            return self.student.bounding_periods()
        return self.student.bounding_periods() + self.married_student.bounding_periods()


@dataclass(eq=False)
class ServiceOfStudentNurse(ExcludedServiceOnDay):
    """
    A service for a hospital or nurses' training school by a student nurse.
    """

    student: StudentAtSchool
    """
    The employee, a student of a nurses' training school.
    """

    def bounding_periods(self) -> list[Period]:
        return self.student.bounding_periods()


@dataclass(eq=False)
class ServiceOfInmate(ExcludedServiceOnDay):
    """
    A service by an inmate of a penal institution, during their confinement.
    """

    incarceration: Incarceration
    """
    The employee's confinement.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Orders the arguments as `§ 3306(c)(21) <https://www.law.cornell.edu/uscode/text/26/3306#c_21>`__ does: the service, the employee, the
        penal institution and the day, left open.
        """
        return (
            self.service.name,
            self.service.employee.name,
            self.incarceration.institution.name,
            None,
        )

    def bounding_periods(self) -> list[Period]:
        return [self.incarceration.period]


@dataclass(eq=False)
class ServiceForFamilyMember(ExcludedServiceOnDay):
    """
    A service for one's child or spouse, or by a child under 21 for a parent.
    """

    kinship: Kinship | None = None
    """
    The relation of parent and child between employer and employee; None for spouses.
    """

    marriage: Marriage | None = None
    """
    The marriage of employer and employee; None for parent and child.
    """

    birth: Birth | None = None
    """
    The birth of the employee, a child of the employer; None where the employee is not
    the child.
    """

    def bounding_periods(self) -> list[Period]:
        if self.marriage is not None:
            return [self.marriage.period]
        if self.birth is not None:
            return [self.birth.period_under_age_21()]
        return []


@dataclass(eq=False)
class ServiceInUnitedStates(SaraConclusion):
    """
    A service performed within the United States.
    """

    service: Service
    """
    The service.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.service.name, self.service.employer.name, self.service.employee.name


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


# %% services brought into employment


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


@dataclass
class ServiceInUnitedStatesTest(Provision[ServiceInUnitedStates]):
    """
    `§ 3306(c)(A) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__: service performed within the United States, which a service at no
    stated place is taken to be.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.SERVICE_IN_UNITED_STATES`.
        """
        return SaraPredicate.SERVICE_IN_UNITED_STATES

    def query(self) -> Query:
        service = variable(Service, domain=self.world.services)
        return an(
            entity(inference(ServiceInUnitedStates)(service=service)).where(
                or_(
                    service.places == [],
                    in_(self.world.united_states, service.countries()),
                )
            )
        )


# %% exclusions by employee on a day


@dataclass
class StudentAtSchoolTest(Provision[StudentAtSchool]):
    """
    `§ 3306(c)(10)(A)(i) <https://www.law.cornell.edu/uscode/text/26/3306#c_10_A_i>`__: a student enrolled and regularly attending classes at an
    institution.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.STUDENT_AT_SCHOOL`.
        """
        return SaraPredicate.STUDENT_AT_SCHOOL

    def query(self) -> Query:
        enrollment = variable(Enrollment, domain=self.world.enrollments)
        attendance = variable(ClassAttendance, domain=self.world.class_attendances)
        return an(
            entity(
                inference(StudentAtSchool)(enrollment=enrollment, attendance=attendance)
            ).where(
                attendance.student == enrollment.student,
                attendance.institution == enrollment.institution,
            )
        )


@dataclass
class MarriedStudentTest(Provision[MarriedStudent]):
    """
    `§ 3306(c)(10)(A)(ii) <https://www.law.cornell.edu/uscode/text/26/3306#c_10_A_ii>`__ as SARA's program reads it: a student married under
    `§ 7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.MARRIED_STUDENT`.
        """
        return SaraPredicate.MARRIED_STUDENT

    def query(self) -> Query:
        student = variable(
            StudentAtSchool, domain=StudentAtSchoolTest(world=self.world).conclusions
        )
        marriage = variable(
            MarriedIndividual,
            domain=MarriedIndividualTest(world=self.world).conclusions,
        )
        return an(
            entity(inference(MarriedStudent)(student=student, marriage=marriage)).where(
                marriage.spouse == student.enrollment.student
            )
        )


@dataclass
class ServiceOfStudentTest(Provision[ServiceOfStudent]):
    """
    `§ 3306(c)(10)(A) <https://www.law.cornell.edu/uscode/text/26/3306#c_10_A>`__: service for a school, college or university by a student
    of it, or by the spouse of one, as SARA's program reads the spouse.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.SERVICE_OF_STUDENT`.
        """
        return SaraPredicate.SERVICE_OF_STUDENT

    def query(self) -> Query:
        service_of_student = variable(
            ServiceOfStudent,
            domain=self.services_of_students() + self.services_of_married_students(),
        )
        return an(entity(service_of_student))

    def services_of_students(self) -> list[ServiceOfStudent]:
        """:return: The services for an educational institution by a student of it."""
        service = variable(Service, domain=self.world.services)
        student = variable(
            StudentAtSchool, domain=StudentAtSchoolTest(world=self.world).conclusions
        )
        return (
            an(
                entity(
                    inference(ServiceOfStudent)(service=service, student=student)
                ).where(
                    in_(service.employer, self.educational_institutions()),
                    student.enrollment.institution == service.employer,
                    student.enrollment.student == service.employee,
                )
            )
        ).tolist()

    def services_of_married_students(self) -> list[ServiceOfStudent]:
        """:return: The services for an educational institution by a married student whose spouse is a student of it."""
        service = variable(Service, domain=self.world.services)
        student = variable(
            StudentAtSchool, domain=StudentAtSchoolTest(world=self.world).conclusions
        )
        married_student = variable(
            MarriedStudent, domain=MarriedStudentTest(world=self.world).conclusions
        )
        return (
            an(
                entity(
                    inference(ServiceOfStudent)(
                        service=service,
                        student=student,
                        married_student=married_student,
                    )
                ).where(
                    in_(service.employer, self.educational_institutions()),
                    student.enrollment.institution == service.employer,
                    married_student.marriage.spouse == service.employee,
                    married_student.marriage.person == student.enrollment.student,
                )
            )
        ).tolist()

    def educational_institutions(self) -> list[Party]:
        """:return: The parties that are schools, colleges or universities."""
        return [
            institution.role_taker
            for institution in self.world.educational_institutions
        ]


@dataclass
class ServiceOfStudentNurseTest(Provision[ServiceOfStudentNurse]):
    """
    `§ 3306(c)(13) <https://www.law.cornell.edu/uscode/text/26/3306#c_13>`__: service for a hospital or nurses' training school by a student
    enrolled and regularly attending classes at a nurses' training school.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.SERVICE_OF_STUDENT_NURSE`.
        """
        return SaraPredicate.SERVICE_OF_STUDENT_NURSE

    def query(self) -> Query:
        service = variable(Service, domain=self.world.services)
        student = variable(
            StudentAtSchool, domain=StudentAtSchoolTest(world=self.world).conclusions
        )
        nurses_training_schools = [
            school.role_taker for school in self.world.nurses_training_schools
        ]
        return an(
            entity(
                inference(ServiceOfStudentNurse)(service=service, student=student)
            ).where(
                in_(
                    service.employer,
                    nurses_training_schools
                    + [hospital.role_taker for hospital in self.world.hospitals],
                ),
                student.enrollment.student == service.employee,
                in_(student.enrollment.institution, nurses_training_schools),
            )
        )


@dataclass
class ServiceOfInmateTest(Provision[ServiceOfInmate]):
    """
    `§ 3306(c)(21) <https://www.law.cornell.edu/uscode/text/26/3306#c_21>`__: service by an inmate of a penal institution.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.SERVICE_OF_INMATE`.
        """
        return SaraPredicate.SERVICE_OF_INMATE

    def query(self) -> Query:
        service = variable(Service, domain=self.world.services)
        incarceration = variable(Incarceration, domain=self.world.incarcerations)
        return an(
            entity(
                inference(ServiceOfInmate)(service=service, incarceration=incarceration)
            ).where(
                incarceration.inmate == service.employee,
                in_(
                    incarceration.institution,
                    [
                        institution.role_taker
                        for institution in self.world.penal_institutions
                    ],
                ),
            )
        )


@dataclass
class ServiceForFamilyMemberTest(Provision[ServiceForFamilyMember]):
    """
    `§ 3306(c)(5) <https://www.law.cornell.edu/uscode/text/26/3306#c_5>`__: service by an individual for their son, daughter or spouse, and by
    a child under 21 for their father or mother.

    A marriage counts from the start the case states of it, as in SARA's program.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        The predicate of :attr:`SaraPredicate.SERVICE_FOR_FAMILY_MEMBER`.
        """
        return SaraPredicate.SERVICE_FOR_FAMILY_MEMBER

    def query(self) -> Query:
        service_for_family_member = variable(
            ServiceForFamilyMember,
            domain=self.services_for_children()
            + self.services_for_spouses()
            + self.services_of_young_children(),
        )
        return an(entity(service_for_family_member))

    def services_for_children(self) -> list[ServiceForFamilyMember]:
        """:return: The services by an individual for their son or daughter."""
        service = variable(Service, domain=self.world.services)
        kinship = variable(Kinship, domain=self.world.kinships)
        return (
            an(
                entity(
                    inference(ServiceForFamilyMember)(service=service, kinship=kinship)
                ).where(
                    kinship.parent == service.employee,
                    kinship.child == service.employer,
                )
            )
        ).tolist()

    def services_for_spouses(self) -> list[ServiceForFamilyMember]:
        """:return: The services by an individual for their spouse, during a marriage with a stated start."""
        service = variable(Service, domain=self.world.services)
        marriage = variable(Marriage, domain=self.world.marriages)
        return (
            an(
                entity(
                    inference(ServiceForFamilyMember)(
                        service=service, marriage=marriage
                    )
                ).where(
                    service.employer != service.employee,
                    in_(service.employer, marriage.spouses),
                    in_(service.employee, marriage.spouses),
                    marriage.period.lower != None,
                )
            )
        ).tolist()

    def services_of_young_children(self) -> list[ServiceForFamilyMember]:
        """:return: The services by a child for their father or mother, before the child turns 21."""
        service = variable(Service, domain=self.world.services)
        kinship = variable(Kinship, domain=self.world.kinships)
        birth = variable(Birth, domain=self.world.births)
        return (
            an(
                entity(
                    inference(ServiceForFamilyMember)(
                        service=service, kinship=kinship, birth=birth
                    )
                ).where(
                    kinship.parent == service.employer,
                    kinship.child == service.employee,
                    birth.person == service.employee,
                )
            )
        ).tolist()
