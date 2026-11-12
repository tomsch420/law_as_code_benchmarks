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
    Birth,
    Blindness,
    Business,
    BusinessTrustStatus,
    ClassAttendance,
    Death,
    Disability,
    EducationalInstitution,
    Enrollment,
    ForeignGovernment,
    Hospital,
    HospitalStay,
    Household,
    Incarceration,
    Income,
    InternationalOrganization,
    ItemizedDeduction,
    JointReturn,
    Kinship,
    LaborKind,
    LegalSeparation,
    Marriage,
    Migration,
    NonresidentAlienStatus,
    NursesTrainingSchool,
    Party,
    Payment,
    PenalInstitution,
    Period,
    Place,
    Residence,
    SeparationDecree,
    Siblinghood,
    EmployeeBenefitPlan,
    EmployeeBenefit,
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
from law_as_code_benchmarks.sara.family_status_conclusions import (
    AgeRequirement,
    ApplicableAmount,
    DependentExemptionAmount,
    ExemptionForDependent,
    ExemptionForSpouse,
    HeadOfHousehold,
    HouseholdMemberRelationship,
    JointFiling,
    MarriedIndividual,
    QualifyingChild,
    QualifyingChildRelationship,
    QualifyingChildUnderGeneralRule,
    SurvivingSpouse,
)
from law_as_code_benchmarks.sara.exceptions import ConflictingFacts, MissingFact
from law_as_code_benchmarks.sara.taxable_income_conclusions import (
    AdditionalAmountsForAgedOrBlind,
    AgedSpouse,
    AgedTaxpayer,
    BasicStandardDeduction,
    ItemizedDeductions,
    PersonalExemptions,
    StandardDeduction,
    StandardDeductionUnderGeneralRule,
    TaxableIncome,
    TaxpayerExemption,
)
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

    BROTHER = "brother_"
    """That its agents and patients are brothers or sisters."""

    SISTER = "sister_"
    """That its agents and patients are brothers or sisters."""

    BIRTH = "birth_"
    """The birth of its agent."""

    LEGAL_SEPARATION = "legal_separation_"
    """The legal separation of the spouses of its patient, a marriage, under its agent, a decree."""

    RESIDENCE = "residence_"
    """Its agents living in its patient, a household."""

    INCOME = "income_"
    """Income its agent earns."""

    JOINT_RETURN = "joint_return_"
    """A joint return its agents make."""

    NONRESIDENT_ALIEN = "nonresident_alien_"
    """That its agent is a nonresident alien."""

    DEDUCTION = "deduction_"
    """An itemized deduction its agent claims."""

    BLINDNESS = "blindness_"
    """That its agent is blind."""

    BUSINESS_TRUST = "business_trust_"
    """That its agent is a business trust."""

    EDUCATIONAL_INSTITUTION = "educational_institution_"
    """That its agent is a school, college or university."""

    NURSES_TRAINING_SCHOOL = "nurses_training_school_"
    """That its agent is a nurses' training school."""

    PENAL_INSTITUTION = "penal_institution_"
    """That its agent is a penal institution."""

    ENROLLMENT = "enrollment_"
    """The enrollment of its agent as a student at its patient."""

    ATTENDING_CLASSES = "attending_classes_"
    """Its agent attending classes at its location."""

    INCARCERATION = "incarceration_"
    """The confinement of its agent in its patient."""

    BUSINESS = "business_"
    """A trade or business its agent carries on."""


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

    EMPLOYMENT = SaraPredicate.EMPLOYMENT
    """`§ 3306(c) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__: employment."""

    WAGES = SaraPredicate.WAGES
    """`§ 3306(b) <https://www.law.cornell.edu/uscode/text/26/3306#b>`__: wages."""

    EMPLOYER = SaraPredicate.EMPLOYER
    """`§ 3306(a) <https://www.law.cornell.edu/uscode/text/26/3306#a>`__: an employer for a year."""

    TOTAL_WAGES = SaraPredicate.TOTAL_WAGES
    """The total wages of an employer in a period."""

    MARRIED = SaraPredicate.MARRIED
    """`§ 7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__: an individual married for a year."""

    JOINT_FILING = SaraPredicate.JOINT_FILING
    """`§ 152(b)(2) <https://www.law.cornell.edu/uscode/text/26/152#b_2>`__: an individual who made a joint return with their spouse."""

    QUALIFYING_CHILD = SaraPredicate.QUALIFYING_CHILD
    """`§ 152(c) <https://www.law.cornell.edu/uscode/text/26/152#c>`__: a qualifying child."""

    QUALIFYING_CHILD_UNDER_GENERAL_RULE = (
        SaraPredicate.QUALIFYING_CHILD_UNDER_GENERAL_RULE
    )
    """`§ 152(c)(1) <https://www.law.cornell.edu/uscode/text/26/152#c_1>`__: a qualifying child."""

    QUALIFYING_CHILD_RELATIONSHIP = SaraPredicate.QUALIFYING_CHILD_RELATIONSHIP
    """`§ 152(c)(2) <https://www.law.cornell.edu/uscode/text/26/152#c_2>`__: a relationship of a qualifying child."""

    AGE_REQUIREMENT = SaraPredicate.AGE_REQUIREMENT
    """`§ 152(c)(3) <https://www.law.cornell.edu/uscode/text/26/152#c_3>`__: the age requirements of a qualifying child."""

    EXEMPTION_FOR_DEPENDENT = SaraPredicate.EXEMPTION_FOR_DEPENDENT
    """`§ 151(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__: an exemption for a dependent."""

    EXEMPTION_FOR_SPOUSE = SaraPredicate.EXEMPTION_FOR_SPOUSE
    """`§ 151(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__: an exemption for a spouse."""

    DEPENDENT_EXEMPTION_AMOUNT = SaraPredicate.DEPENDENT_EXEMPTION_AMOUNT
    """`§ 151(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__: the exemption amount for a dependent."""

    APPLICABLE_AMOUNT = SaraPredicate.APPLICABLE_AMOUNT
    """`§ 68(b) <https://www.law.cornell.edu/uscode/text/26/68#b>`__: the applicable amount."""

    SURVIVING_SPOUSE = SaraPredicate.SURVIVING_SPOUSE
    """`§ 2(a) <https://www.law.cornell.edu/uscode/text/26/2#a>`__: a surviving spouse."""

    HEAD_OF_HOUSEHOLD = SaraPredicate.HEAD_OF_HOUSEHOLD
    """`§ 2(b) <https://www.law.cornell.edu/uscode/text/26/2#b>`__: a head of household."""

    TAXABLE_INCOME = SaraPredicate.TAXABLE_INCOME
    """`§ 63 <https://www.law.cornell.edu/uscode/text/26/63>`__: taxable income."""

    STANDARD_DEDUCTION_UNDER_GENERAL_RULE = (
        SaraPredicate.STANDARD_DEDUCTION_UNDER_GENERAL_RULE
    )
    """`§ 63(c)(1) <https://www.law.cornell.edu/uscode/text/26/63#c_1>`__: the standard deduction."""

    ITEMIZED_DEDUCTIONS = SaraPredicate.ITEMIZED_DEDUCTIONS
    """`§ 63(d) <https://www.law.cornell.edu/uscode/text/26/63#d>`__: itemized deductions."""

    PERSONAL_EXEMPTIONS = SaraPredicate.PERSONAL_EXEMPTIONS
    """`§ 151 <https://www.law.cornell.edu/uscode/text/26/151>`__: the exemptions a taxpayer deducts."""

    TAXPAYER_OR_SPOUSE_EXEMPTION = SaraPredicate.TAXPAYER_OR_SPOUSE_EXEMPTION
    """`§ 151(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__: the exemption for the taxpayer."""

    HOUSEHOLD_MEMBER = SaraPredicate.HOUSEHOLD_MEMBER
    """`§ 152(d)(2)(H) <https://www.law.cornell.edu/uscode/text/26/152#d_2_H>`__: a member of the taxpayer's household."""

    STANDARD_DEDUCTION = SaraPredicate.STANDARD_DEDUCTION
    """`§ 63(c) <https://www.law.cornell.edu/uscode/text/26/63#c>`__: the standard deduction."""

    BASIC_STANDARD_DEDUCTION = SaraPredicate.BASIC_STANDARD_DEDUCTION
    """`§ 63(c)(2) <https://www.law.cornell.edu/uscode/text/26/63#c_2>`__: the basic standard deduction."""

    ADDITIONAL_AMOUNTS_FOR_AGED_OR_BLIND = (
        SaraPredicate.ADDITIONAL_AMOUNTS_FOR_AGED_OR_BLIND
    )
    """`§ 63(c)(3) <https://www.law.cornell.edu/uscode/text/26/63#c_3>`__: the additional standard deduction."""

    AGED_TAXPAYER = SaraPredicate.AGED_TAXPAYER
    """`§ 63(f)(1)(A) <https://www.law.cornell.edu/uscode/text/26/63#f_1_A>`__: a taxpayer aged 65."""

    AGED_SPOUSE = SaraPredicate.AGED_SPOUSE
    """`§ 63(f)(1)(B) <https://www.law.cornell.edu/uscode/text/26/63#f_1_B>`__: a spouse aged 65."""


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
        """:return: The values *relation* relates *event* to, those it relates every event to included."""
        values = self.related.get((relation, event), [])
        if event is None:
            return values
        return values + self.related.get((relation, None), [])

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

    services_of_other_parties: dict[tuple[str, str, str], Service] = field(
        default_factory=dict
    )
    """The services a stated conclusion names by the name of a service of other parties, by name, employee and employer."""

    benefit_plans: dict[str, EmployeeBenefitPlan] = field(default_factory=dict)
    """The plans, by name."""

    payments: dict[str, Payment] = field(default_factory=dict)
    """The payments read so far, by name, those only a stated conclusion names included."""

    households: dict[str, Household] = field(default_factory=dict)
    """The households read so far, by name."""

    residences: dict[str, Residence] = field(default_factory=dict)
    """The residences, by name."""

    marriages: dict[str, Marriage] = field(default_factory=dict)
    """The marriages, by name."""

    joint_returns: dict[str, JointReturn] = field(default_factory=dict)
    """The joint returns, by name."""

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
        benefit_plans = [
            self.benefit_plan(event) for event in self.facts.typed[EventType.PLAN]
        ]
        residences = [
            self.residence(event) for event in self.facts.typed[EventType.RESIDENCE]
        ]
        marriages = [
            marriage
            for event in self.facts.typed[EventType.MARRIAGE]
            for marriage in self.marriages_of(event)
        ]
        payments = [
            payment
            for event in self.facts.typed[EventType.PAYMENT]
            for payment in self.payments_of(event)
        ]
        joint_returns = [
            self.joint_return(event)
            for event in self.facts.typed[EventType.JOINT_RETURN]
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
            educational_institutions=[
                EducationalInstitution(role_taker=party)
                for party in self.agents_of(EventType.EDUCATIONAL_INSTITUTION)
            ],
            nurses_training_schools=[
                NursesTrainingSchool(role_taker=party)
                for party in self.agents_of(EventType.NURSES_TRAINING_SCHOOL)
            ],
            penal_institutions=[
                PenalInstitution(role_taker=party)
                for party in self.agents_of(EventType.PENAL_INSTITUTION)
            ],
            enrollments=[
                Enrollment(
                    student=self.party(
                        self.facts.required_value(Relation.AGENT, event)
                    ),
                    institution=self.party(
                        self.facts.required_value(Relation.PATIENT, event)
                    ),
                    period=self.period(event),
                )
                for event in self.facts.typed[EventType.ENROLLMENT]
            ],
            class_attendances=[
                ClassAttendance(
                    student=self.party(
                        self.facts.required_value(Relation.AGENT, event)
                    ),
                    institution=self.party(
                        self.facts.required_value(Relation.LOCATION, event)
                    ),
                    period=self.period(event),
                )
                for event in self.facts.typed[EventType.ATTENDING_CLASSES]
            ],
            incarcerations=[
                Incarceration(
                    inmate=self.party(self.facts.required_value(Relation.AGENT, event)),
                    institution=self.party(
                        self.facts.required_value(Relation.PATIENT, event)
                    ),
                    period=self.period(event),
                )
                for event in self.facts.typed[EventType.INCARCERATION]
            ],
            businesses=[
                Business(
                    owner=self.party(self.facts.required_value(Relation.AGENT, event)),
                    type_description=next(
                        (
                            self.text(type_description)
                            for type_description in self.facts.values(
                                Relation.TYPE, event
                            )
                        ),
                        None,
                    ),
                )
                for event in self.facts.typed[EventType.BUSINESS]
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
            benefit_plans=benefit_plans,
            terminations=[
                self.termination(event)
                for event in self.facts.typed[EventType.TERMINATION]
            ],
            deaths=[self.death(event) for event in self.facts.typed[EventType.DEATH]],
            marriages=marriages,
            legal_separations=[
                self.legal_separation(event)
                for event in self.facts.typed[EventType.LEGAL_SEPARATION]
            ],
            kinships=self.kinships(),
            siblinghoods=[
                self.siblinghood(event)
                for event_type in (EventType.BROTHER, EventType.SISTER)
                for event in self.facts.typed[event_type]
            ],
            births=[self.birth(event) for event in self.facts.typed[EventType.BIRTH]],
            residences=residences,
            incomes=[
                income
                for event in self.facts.typed[EventType.INCOME]
                for income in self.incomes_of(event)
            ],
            joint_returns=joint_returns,
            itemized_deductions=[
                deduction
                for event in self.facts.typed[EventType.DEDUCTION]
                for deduction in self.itemized_deductions_of(event)
            ],
            blindnesses=[
                Blindness(
                    person=self.party(self.facts.required_value(Relation.AGENT, event)),
                    start=self.date(self.facts.required_value(Relation.START, event)),
                )
                for event in self.facts.typed[EventType.BLINDNESS]
            ],
            business_trust_statuses=[
                BusinessTrustStatus(
                    party=self.party(self.facts.required_value(Relation.AGENT, event)),
                    period=self.period(event),
                )
                for event in self.facts.typed[EventType.BUSINESS_TRUST]
            ],
            nonresident_alien_statuses=[
                NonresidentAlienStatus(
                    person=self.party(self.facts.required_value(Relation.AGENT, event)),
                    period=self.period(event),
                )
                for event in self.facts.typed[EventType.NONRESIDENT_ALIEN]
            ],
            stated_conclusions=stated_conclusions,
            parties=list(self.parties.values()),
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
        """
        :return: The service *event* is, by *employee* for *employer*, read once from its
            facts; a name stated for several employees or employers names a service for each.
        """
        name = self.text(event)
        if name not in self.services:
            self.services[name] = self.new_service(event, employee, employer)
        service = self.services[name]
        if service.employee is self.party(employee) and service.employer is self.party(
            employer
        ):
            return service
        key = (name, self.text(employee), self.text(employer))
        if key not in self.services_of_other_parties:
            self.services_of_other_parties[key] = self.new_service(
                event, employee, employer
            )
        return self.services_of_other_parties[key]

    def new_service(self, event: Term, employee: Term, employer: Term) -> Service:
        """:return: The service *event* is, by *employee* for *employer*, as its facts describe it."""
        name = self.text(event)
        start = self.facts.value(Relation.START, event)
        end = self.facts.value(Relation.END, event)
        return Service(
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
            type_descriptions=[
                self.text(type_description)
                for type_description in self.facts.values(Relation.TYPE, event)
            ],
        )

    def benefit_plan(self, event: Term) -> EmployeeBenefitPlan:
        """:return: The plan *event* names."""
        sponsor = self.facts.value(Relation.AGENT, event)
        benefits = {
            SaraName.PROVISION_IN_CASE_OF_SICKNESS: EmployeeBenefit.SICKNESS,
            SaraName.PROVISION_IN_CASE_OF_ACCIDENT_DISABILITY: EmployeeBenefit.ACCIDENT_DISABILITY,
            SaraName.PROVISION_IN_CASE_OF_DEATH: EmployeeBenefit.DEATH,
            SaraName.PROVISION_FOR_EMPLOYEES_OR_DEPENDENTS: EmployeeBenefit.EMPLOYEES_OR_DEPENDENTS,
        }
        plan = EmployeeBenefitPlan(
            name=self.text(event),
            sponsor=None if sponsor is None else self.party(sponsor),
            benefits={
                benefits[self.text(purpose)]
                for purpose in self.facts.values(Relation.PURPOSE, event)
                if self.text(purpose) in benefits
            },
            beneficiaries=[
                self.party(beneficiary)
                for beneficiary in self.facts.values(Relation.BENEFICIARY, event)
            ],
        )
        self.benefit_plans[plan.name] = plan
        return plan

    def payments_of(self, event: Term) -> list[Payment]:
        """:return: The payments *event* is, one for each day and amount the case states of it; plans and residences are read beforehand."""
        payer = self.facts.value(Relation.AGENT, event)
        recipient = self.facts.value(Relation.PATIENT, event)
        days = self.facts.values(Relation.START, event) or [None]
        means = self.facts.value(Relation.MEANS, event)
        services = [
            self.services[self.text(purpose)]
            for purpose in self.facts.values(Relation.PURPOSE, event)
            if self.text(purpose) in self.services
        ]
        households = [
            self.household_of(self.text(purpose))
            for purpose in self.facts.values(Relation.PURPOSE, event)
            if self.household_of(self.text(purpose)) is not None
        ]
        payments = [
            Payment(
                name=self.text(event),
                payer=None if payer is None else self.party(payer),
                recipient=None
                if recipient is None
                else self.benefit_plans.get(self.text(recipient))
                or self.party(recipient),
                amount=amount,
                day=None if day is None else self.date(day),
                service=next(iter(services), None),
                medium=None
                if means is None or self.text(means) in self.benefit_plans
                else self.text(means),
                benefit_plan_drawn_on=None
                if means is None
                else self.benefit_plans.get(self.text(means)),
                household_maintained=next(iter(households), None),
            )
            for day in days
            for amount in self.facts.values(Relation.AMOUNT, event)
        ]
        if payments:
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

    def marriages_of(self, event: Term) -> list[Marriage]:
        """:return: The marriage *event* is, once for each start the case states of it."""
        end = self.facts.value(Relation.END, event)
        marriages = [
            Marriage(
                name=self.text(event),
                spouses=[
                    self.party(spouse)
                    for spouse in self.facts.values(Relation.AGENT, event)
                ],
                period=Period(
                    start=None if start is None else self.date(start),
                    end=None if end is None else self.date(end),
                ),
            )
            for start in self.facts.values(Relation.START, event) or [None]
        ]
        self.marriages[marriages[0].name] = marriages[0]
        return marriages

    def legal_separation(self, event: Term) -> LegalSeparation:
        """:return: The legal separation *event* is; marriages are read beforehand."""
        return LegalSeparation(
            name=self.text(event),
            marriage=self.marriages[
                self.text(self.facts.required_value(Relation.PATIENT, event))
            ],
            decree=SeparationDecree(
                self.text(self.facts.required_value(Relation.AGENT, event))
            ),
            day=self.date(self.facts.required_value(Relation.START, event)),
        )

    def siblinghood(self, event: Term) -> Siblinghood:
        """:return: The relation of brothers or sisters *event* is."""
        return Siblinghood(
            siblings=[
                self.party(sibling)
                for relation in (Relation.AGENT, Relation.PATIENT)
                for sibling in self.facts.values(relation, event)
            ],
            period=self.period(event),
        )

    def birth(self, event: Term) -> Birth:
        """:return: The birth *event* is."""
        return Birth(
            person=self.party(self.facts.required_value(Relation.AGENT, event)),
            day=self.date(self.facts.required_value(Relation.START, event)),
        )

    def residence(self, event: Term) -> Residence:
        """:return: The residence *event* is."""
        household = self.text(self.facts.required_value(Relation.PATIENT, event))
        if household not in self.households:
            self.households[household] = Household(name=household)
        residence = Residence(
            name=self.text(event),
            residents=[
                self.party(resident)
                for resident in self.facts.values(Relation.AGENT, event)
            ],
            household=self.households[household],
            period=self.period(event),
        )
        self.residences[residence.name] = residence
        return residence

    def household_of(self, name: str) -> Household | None:
        """:return: The household named *name*, or that of the residence named *name*; None if neither is read."""
        if name in self.residences:
            return self.residences[name].household
        return self.households.get(name)

    def incomes_of(self, event: Term) -> list[Income]:
        """:return: The income *event* is, once for each amount the case states of it."""
        day = self.facts.value(Relation.START, event)
        return [
            Income(
                earning_party=self.party(
                    self.facts.required_value(Relation.AGENT, event)
                ),
                amount=amount,
                day=None if day is None else self.date(day),
            )
            for amount in self.facts.values(Relation.AMOUNT, event)
        ]

    def itemized_deductions_of(self, event: Term) -> list[ItemizedDeduction]:
        """:return: The itemized deduction *event* is, once for each amount the case states of it, or once without one."""
        day = self.facts.value(Relation.START, event)
        return [
            ItemizedDeduction(
                name=self.text(event),
                claimant=self.party(self.facts.required_value(Relation.AGENT, event)),
                amount=amount,
                day=None if day is None else self.date(day),
            )
            for amount in self.facts.values(Relation.AMOUNT, event) or [None]
        ]

    def joint_return(self, event: Term) -> JointReturn:
        """:return: The joint return *event* is."""
        self.joint_returns[self.text(event)] = JointReturn(
            name=self.text(event),
            filers=[
                self.party(filer) for filer in self.facts.values(Relation.AGENT, event)
            ],
            period=self.period(event),
        )
        return self.joint_returns[self.text(event)]

    def period(self, event: Term) -> Period:
        """:return: The days from the start to the end the case states of *event*, either left open where it states none."""
        start = self.facts.value(Relation.START, event)
        end = self.facts.value(Relation.END, event)
        return Period(
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
                                    parent=self.party(parent),
                                    child=self.party(child),
                                    period=self.period(event),
                                )
                            )
        return kinships

    def stated_conclusions(self) -> list[SaraConclusion]:
        """:return: The conclusions the case states as facts, each read into the domain model."""
        return (
            self.stated_employment_tax_conclusions()
            + self.stated_family_conclusions()
            + self.stated_taxable_income_conclusions()
        )

    def stated_employment_tax_conclusions(self) -> list[SaraConclusion]:
        """:return: The conclusions of §§ `3306 <https://www.law.cornell.edu/uscode/text/26/3306>`__ and `3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__ the case states as facts."""
        return (
            [
                Employment(
                    service=self.service_by(service, employee, employer),
                    workday=None if workday is None else self.date(workday),
                    year=year,
                )
                for service, employer, employee, workday, year in self.stated_arguments(
                    SaraPredicate.EMPLOYMENT, 5
                )
            ]
            + [
                self.stated_wages(*arguments)
                for arguments in self.stated_arguments(SaraPredicate.WAGES, 8)
            ]
            + [
                Employer(party=self.party(employer), year=year)
                for employer, year in self.stated_arguments(SaraPredicate.EMPLOYER, 2)
            ]
            + [
                TotalWages(
                    employer=self.party(employer),
                    amount=amount,
                    first_day=self.date(first_day),
                    last_day=self.date(last_day),
                )
                for employer, amount, _, _, first_day, last_day in self.stated_arguments(
                    SaraPredicate.TOTAL_WAGES, 6
                )
            ]
        )

    def stated_family_conclusions(self) -> list[SaraConclusion]:
        """:return: The conclusions of §§ `7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__, `152 <https://www.law.cornell.edu/uscode/text/26/152>`__, `151 <https://www.law.cornell.edu/uscode/text/26/151>`__, `2 <https://www.law.cornell.edu/uscode/text/26/2>`__ and `68(b) <https://www.law.cornell.edu/uscode/text/26/68#b>`__ the case states as facts; marriages and joint returns are read beforehand."""
        return (
            [
                MarriedIndividual(
                    person=self.party(person),
                    spouse=self.party(spouse),
                    marriage=self.marriages.get(self.text(marriage))
                    or Marriage(
                        name=self.text(marriage),
                        spouses=[self.party(person), self.party(spouse)],
                    ),
                    year=year,
                )
                for person, spouse, marriage, year in self.stated_arguments(
                    SaraPredicate.MARRIED, 4
                )
            ]
            + [
                JointFiling(
                    individual=self.party(individual),
                    spouse=self.party(spouse),
                    year=year,
                    joint_return=None
                    if joint_return is None
                    else self.joint_returns.get(self.text(joint_return)),
                )
                for individual, joint_return, spouse, year in self.stated_arguments(
                    SaraPredicate.JOINT_FILING, 4
                )
            ]
            + [
                conclusion_type(
                    individual=self.party(individual),
                    taxpayer=self.party(taxpayer),
                    year=year,
                )
                for predicate, conclusion_type in (
                    (SaraPredicate.QUALIFYING_CHILD, QualifyingChild),
                    (
                        SaraPredicate.QUALIFYING_CHILD_UNDER_GENERAL_RULE,
                        QualifyingChildUnderGeneralRule,
                    ),
                    (SaraPredicate.AGE_REQUIREMENT, AgeRequirement),
                )
                for individual, taxpayer, year in self.stated_arguments(predicate, 3)
            ]
            + [
                conclusion_type(
                    individual=self.party(individual),
                    taxpayer=self.party(taxpayer),
                    year=year,
                )
                for predicate, conclusion_type in (
                    (SaraPredicate.EXEMPTION_FOR_DEPENDENT, ExemptionForDependent),
                    (SaraPredicate.EXEMPTION_FOR_SPOUSE, ExemptionForSpouse),
                )
                for taxpayer, individual, year in self.stated_arguments(predicate, 3)
            ]
            + [
                QualifyingChildRelationship(
                    individual=self.party(individual),
                    taxpayer=self.party(taxpayer),
                    period=Period(
                        start=None if start is None else self.date(start),
                        end=None if end is None else self.date(end),
                    ),
                )
                for individual, taxpayer, start, end in self.stated_arguments(
                    SaraPredicate.QUALIFYING_CHILD_RELATIONSHIP, 4
                )
            ]
            + [
                DependentExemptionAmount(
                    taxpayer=self.party(taxpayer),
                    amount=amount,
                    year=year,
                    individual=None if individual is None else self.party(individual),
                )
                for taxpayer, individual, amount, year in self.stated_arguments(
                    SaraPredicate.DEPENDENT_EXEMPTION_AMOUNT, 4
                )
            ]
            + [
                ApplicableAmount(
                    taxpayer=self.party(taxpayer), amount=amount, year=year
                )
                for taxpayer, amount, year in self.stated_arguments(
                    SaraPredicate.APPLICABLE_AMOUNT, 3
                )
            ]
            + [
                SurvivingSpouse(
                    taxpayer=self.party(taxpayer),
                    year=year,
                    spouse=self.optional_party(spouse),
                )
                for taxpayer, spouse, year in self.stated_arguments(
                    SaraPredicate.SURVIVING_SPOUSE, 3
                )
            ]
            + [
                HouseholdMemberRelationship(
                    individual=self.party(individual),
                    taxpayer=self.party(taxpayer),
                    year=year,
                    household=None
                    if household is None
                    else self.households.get(self.text(household)),
                    period=Period(
                        start=None if start is None else self.date(start),
                        end=None if end is None else self.date(end),
                    ),
                )
                for individual, taxpayer, year, household, start, end in (
                    self.stated_arguments(SaraPredicate.HOUSEHOLD_MEMBER, 6)
                )
            ]
            + [
                HeadOfHousehold(
                    taxpayer=self.party(taxpayer),
                    year=year,
                    individual=self.optional_party(individual),
                )
                for taxpayer, individual, year in self.stated_arguments(
                    SaraPredicate.HEAD_OF_HOUSEHOLD, 3
                )
            ]
        )

    def stated_taxable_income_conclusions(self) -> list[SaraConclusion]:
        """:return: The conclusions of §§ `63 <https://www.law.cornell.edu/uscode/text/26/63>`__ and `151 <https://www.law.cornell.edu/uscode/text/26/151>`__ the case states as facts."""
        return (
            [
                conclusion_type(taxpayer=self.party(taxpayer), year=year, amount=amount)
                for predicate, conclusion_type in (
                    (SaraPredicate.TAXABLE_INCOME, TaxableIncome),
                    (SaraPredicate.STANDARD_DEDUCTION, StandardDeduction),
                    (
                        SaraPredicate.STANDARD_DEDUCTION_UNDER_GENERAL_RULE,
                        StandardDeductionUnderGeneralRule,
                    ),
                    (SaraPredicate.BASIC_STANDARD_DEDUCTION, BasicStandardDeduction),
                )
                for taxpayer, year, amount in self.stated_arguments(predicate, 3)
            ]
            + [
                AdditionalAmountsForAgedOrBlind(
                    taxpayer=self.party(taxpayer), year=year, amount=amount
                )
                for taxpayer, amount, year in self.stated_arguments(
                    SaraPredicate.ADDITIONAL_AMOUNTS_FOR_AGED_OR_BLIND, 3
                )
            ]
            + [
                TaxpayerExemption(
                    taxpayer=self.party(taxpayer), amount=amount, year=year
                )
                for taxpayer, amount, year in self.stated_arguments(
                    SaraPredicate.TAXPAYER_OR_SPOUSE_EXEMPTION, 3
                )
            ]
            + [
                AgedTaxpayer(taxpayer=self.party(taxpayer), year=year)
                for taxpayer, year in self.stated_arguments(
                    SaraPredicate.AGED_TAXPAYER, 2
                )
            ]
            + [
                AgedSpouse(
                    taxpayer=self.party(taxpayer), year=year, spouse=self.party(spouse)
                )
                for taxpayer, spouse, year in self.stated_arguments(
                    SaraPredicate.AGED_SPOUSE, 3
                )
            ]
            + [
                ItemizedDeductions(
                    taxpayer=self.party(taxpayer), total=total, year=year
                )
                for taxpayer, _, total, year in self.stated_arguments(
                    SaraPredicate.ITEMIZED_DEDUCTIONS, 4
                )
            ]
            + [
                PersonalExemptions(
                    taxpayer=self.party(taxpayer),
                    total=total,
                    year=year,
                    persons=None
                    if persons is None
                    else [self.party(person) for person in persons],
                    amounts=amounts,
                )
                for taxpayer, total, persons, amounts, year in self.stated_arguments(
                    SaraPredicate.PERSONAL_EXEMPTIONS, 5
                )
            ]
        )

    def optional_party(self, term: Term) -> Party | None:
        """:return: The party named *term*; None for an argument a stated fact leaves open."""
        return None if term is None else self.party(term)

    def stated_arguments(
        self, predicate: SaraPredicate, arity: int
    ) -> list[tuple[Term, ...]]:
        """:return: The arguments of each fact of *arity* arguments the case states of *predicate*; facts of another arity are not the program's."""
        return [
            fact.arguments
            for fact in self.facts.stated[predicate]
            if len(fact.arguments) == arity
        ]

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
        :return: The wages a stated fact of `§ 3306(b) <https://www.law.cornell.edu/uscode/text/26/3306#b>`__ states, in the program's order of
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
