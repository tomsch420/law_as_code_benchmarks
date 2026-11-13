"""
The eligibility for the personal housing aids of the Code de la construction et de
l'habitation: the conditions common to every aid, those of the personalised housing aid
(*APL*) and those of the housing allowances (*AL*), Catala's
``ÉligibilitéAidesPersonnelleLogement``, ``ÉligibilitéAidePersonnaliséeLogement`` and ``ÉligibilitéAllocationLogement``.
"""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from fractions import Fraction
from functools import cached_property
from pathlib import Path

from krrood.entity_query_language.factories import (
    add,
    alternative,
    an,
    and_,
    deduced_variable,
    entity,
    exists,
    in_,
    inference,
    not_,
    or_,
    refinement,
    type_,
    variable,
)
from krrood.entity_query_language.predicate import symbolic_function
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.catala.conclusions import FamilyBenefitEntitlement
from law_as_code_benchmarks.catala.domain import (
    Child,
    DatedValue,
    Household,
    Period,
    SchoolingStage,
    Territory,
)
from law_as_code_benchmarks.catala.entitlement import (
    FamilyBenefitEntitlementProvision,
)
from law_as_code_benchmarks.catala.housing.domain import (
    AgreedPrivateLandlord,
    Applicant,
    BenefitReceived,
    ChildDependant,
    Dependant,
    DependentChild,
    FamilyRightHolder,
    FinancingAgreed,
    Foreign,
    HomeBuyer,
    HousingHousehold,
    Kinship,
    LeaseToOwnBuyer,
    LoanHolder,
    LoanType,
    Married,
    NotSublet,
    OtherDependant,
    OwnershipWorks,
    ResidenceHallResident,
    ResidenceHallType,
    SharedResidence,
    Single,
    SocialLandlord,
    Sublet,
    Tenant,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import CatalaDirectory, CatalaValue, Duration
from law_as_code_benchmarks.catala.scope_test import (
    CaseAmount,
    CaseCondition,
    CaseConclusion,
    ScopeCase,
    ScopeProvision,
    ScopeTestFile,
)

# %% calendar


@dataclass(frozen=True)
class Anniversary:
    """Adds a duration to a day as Catala adds one, refusing a day the calendar lacks."""

    @staticmethod
    @symbolic_function
    def date_after(day: datetime.date, duration: Duration) -> datetime.date:
        """:return: The day *duration* after *day*, as :meth:`Duration.date_after` finds it."""
        return duration.date_after(day)

    @staticmethod
    @symbolic_function
    def rounded_up_date_after(day: datetime.date, years: int) -> datetime.date:
        """
        :return: The day *years* after *day*, March 1 standing for a February 29 the
            year lacks, as Catala's ``date arrondi supérieur`` rounds it.
        """
        if (day.month, day.day) == (2, 29) and not (
            Anniversary.is_leap_year(day.year + years)
        ):
            return datetime.date(day.year + years, 3, 1)
        return day.replace(year=day.year + years)

    @staticmethod
    def is_leap_year(year: int) -> bool:
        """:return: Whether *year* has a February 29."""
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


# %% amounts in force


@dataclass(frozen=True)
class IndividualCeiling(DatedValue):
    """The individual ceiling of resources of the allowance for the elderly, of article L815-9 of the Code de la sécurité sociale."""

    amount: Money
    """The yearly ceiling."""


class IndividualCeilings(Enum):
    """The individual ceilings Catala's example states, revalued every January."""

    APRIL_2018 = IndividualCeiling(
        period=Period(datetime.date(2018, 4, 1), datetime.date(2018, 12, 31)),
        source="Article D815-1 du code de la sécurité sociale",
        amount=Money(cents=999840),
    )
    """From April 1, 2018."""

    JANUARY_2019 = IndividualCeiling(
        period=Period(datetime.date(2019, 1, 1), datetime.date(2019, 12, 31)),
        source="Article D815-1 du code de la sécurité sociale",
        amount=Money(cents=1041840),
    )
    """From January 1, 2019."""

    JANUARY_2020 = IndividualCeiling(
        period=Period(datetime.date(2020, 1, 1), datetime.date(2020, 12, 31)),
        source="Article D815-1 du code de la sécurité sociale",
        amount=Money(cents=1083840),
    )
    """From January 1, 2020."""

    JANUARY_2021 = IndividualCeiling(
        period=Period(datetime.date(2021, 1, 1), datetime.date(2021, 12, 31)),
        source="Circulaire de la CNAV 2021-1 du 11 janvier 2021",
        amount=Money(cents=1088175),
    )
    """From January 1, 2021."""

    JANUARY_2022 = IndividualCeiling(
        period=Period(datetime.date(2022, 1, 1), datetime.date(2022, 12, 31)),
        source="Circulaire de la CNAV 2022-3 du 11 janvier 2022",
        amount=Money(cents=1100144),
    )
    """From January 1, 2022."""

    JANUARY_2023 = IndividualCeiling(
        period=Period(datetime.date(2023, 1, 1)),
        source="Circulaire de la CNAV 2023-3 du 9 janvier 2023",
        amount=Money(cents=1153302),
    )
    """From January 1, 2023, open-ended as Catala's example leaves it."""


# %% the family benefits of the children


@dataclass(eq=False)
class HousingChild(Child):
    """A child in the household's charge, as the family benefits see them."""

    dependant: ChildDependant | None = None
    """The person in the household's charge the child is."""


# %% conclusions


@dataclass(eq=False)
class ChildAgeLimit(CaseConclusion):
    """The age limit of the right to family benefits that the housing aids set; None where R512-2's holds."""

    age: int | None = None
    """The age limit."""


@dataclass(eq=False)
class NationalityCondition(CaseCondition):
    """L822-2: the applicant's nationality allows the aid."""


@dataclass(eq=False)
class MainResidenceCondition(CaseCondition):
    """L821-2: the dwelling is the household's main residence."""


@dataclass(eq=False)
class OccupancyCondition(CaseCondition):
    """L822-2 and L822-3: the household occupies its dwelling in a way the aids cover."""


@dataclass(eq=False)
class SublettingCondition(CaseCondition):
    """L822-4: the dwelling is not let to third parties, or only as the article allows."""


@dataclass(eq=False)
class SurfaceCondition(CaseCondition):
    """R822-25: the dwelling is large enough for those living in it."""


@dataclass(eq=False)
class DwellingCondition(CaseCondition):
    """Every condition on the dwelling holds, none of L822-8 and L822-9 excluding it."""


@dataclass(eq=False)
class RetirementAge(CaseConclusion):
    """The age the applicant's right to a retirement pension opens at, of L161-17-2 of the Code de la sécurité sociale."""

    age: Duration = field(default_factory=Duration)
    """The age."""


@dataclass(eq=False)
class IndividualCeilingAmount(CaseAmount):
    """The individual ceiling of article L815-9 in force on the assessment date."""


@dataclass(eq=False)
class DependantCondition(CaseConclusion):
    """Whether a condition about one person in the household's charge holds."""

    dependant: Dependant | None = None
    """The person."""

    holds: bool = False
    """Whether the condition holds."""


@dataclass(eq=False)
class ElderlyAscendantCondition(DependantCondition):
    """R823-4 2°: the person is an ascendant of pension age with small resources."""


@dataclass(eq=False)
class CountedDependant(DependantCondition):
    """R823-4: the person counts as in the household's charge."""


@dataclass(eq=False)
class CountedDependants(CaseConclusion):
    """The persons R823-4 counts as in the household's charge."""

    dependants: list[Dependant] = field(default_factory=list)
    """The persons, in the household's order."""

    @property
    def shared_residence_coefficients(self) -> list[Fraction]:
        """The coefficient of each child counted who lives with each parent in turn, in order."""
        return [
            dependant.child.care_sharing.coefficient
            for dependant in self.dependants
            if isinstance(dependant, ChildDependant)
            and isinstance(dependant.child.care_sharing, SharedResidence)
        ]


@dataclass(eq=False)
class CommonEligibility(CaseCondition):
    """The household meets the conditions common to every personal housing aid."""


@dataclass(eq=False)
class LandlordCondition(CaseCondition):
    """L831-1: the dwelling is one the personalised housing aid covers."""


@dataclass(eq=False)
class LoanCondition(CaseCondition):
    """L831-2: the loan of a home bought does not exclude the personalised housing aid."""


@dataclass(eq=False)
class PersonalisedAidEligibility(CaseCondition):
    """The household is eligible for the personalised housing aid."""


@dataclass(eq=False)
class OwnershipCondition(CaseCondition):
    """R842-5: a home bought is one the housing allowances cover."""


@dataclass(eq=False)
class FamilyHousingAllowanceCondition(CaseCondition):
    """L841-1: the household is one the family housing allowance is paid to."""


class HousingAllowanceType(StrEnum):
    """The housing allowance a household is eligible for, each named as Catala's ``TypeÉligibilitéAllocationLogement``."""

    NOT_ELIGIBLE = "PasÉligible"
    """None."""

    FAMILY = "AllocationLogementFamiliale"
    """The family housing allowance."""

    SOCIAL = "AllocationLogementSociale"
    """The social housing allowance."""


@dataclass(eq=False)
class HousingAllowanceEligibility(CaseConclusion):
    """L841-2 and after: the housing allowance the household is eligible for."""

    allowance: HousingAllowanceType = HousingAllowanceType.NOT_ELIGIBLE
    """The allowance."""


# %% cases


class EligibilityOutput(StrEnum):
    """The outputs of the eligibility scopes."""

    ELIGIBILITY = "éligibilité"
    """Whether, or for which aid, the household is eligible."""

    DEPENDANT_COUNT = "nombre_personnes_à_charge_prises_en_compte"
    """How many persons count as in the household's charge."""

    SHARED_RESIDENCE_COEFFICIENTS = "coefficients_enfants_garde_alternée_pris_en_compte"
    """The coefficient of each child counted who lives with each parent in turn."""


@dataclass(eq=False)
class HousingEligibilityCase(ScopeCase, ABC):
    """A household, its applicant and the day the eligibility for a housing aid is assessed on."""

    household: HousingHousehold
    """The household."""

    applicant: Applicant
    """The applicant."""

    assessment_date: datetime.date
    """The day the eligibility is assessed on."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs every eligibility scope shares."""
        return {
            "ménage": "household",
            "demandeur": "applicant",
            "date_courante": "assessment_date",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`EligibilityOutput`."""
        return EligibilityOutput

    def family_benefits_household(self, age_limit: int | None) -> Household:
        """
        :return: The household as the family benefits see it, its children only, with
            *age_limit* in place of R512-2's where one is given.
        """
        return Household(
            assessment_date=self.assessment_date,
            residence=self.household.residence,
            children=[
                self.family_benefits_child(dependant)
                for dependant in self.household.dependants
                if isinstance(dependant, ChildDependant)
            ],
            stated_age_limit=age_limit,
        )

    @staticmethod
    def family_benefits_child(dependant: ChildDependant) -> HousingChild:
        """:return: The child of *dependant* as the family benefits see them."""
        child: DependentChild = dependant.child
        return HousingChild(
            identifier=child.identifier,
            birth_date=child.birth_date,
            monthly_pay=child.monthly_pay,
            has_opened_family_allowance=child.has_opened_family_allowance,
            stated_schooling_stage=child.schooling_stage,
            dependant=dependant,
        )


@dataclass(eq=False)
class CommonEligibilityCase(HousingEligibilityCase):
    """
    The conditions common to every personal housing aid, Catala's
    ``ÉligibilitéAidesPersonnelleLogement``, with the context variables a scope calling
    it may set.
    """

    main_residence_stated: bool = False
    """Whether the scope calling it states the main residence condition met, as R842-14 does."""

    surface_stated: bool = False
    """Whether the scope calling it states the surface condition met, as R842-14 does."""

    deferred_entry_into_force: datetime.date = datetime.date(2021, 1, 1)
    """R862-2: the day the code applies from in Saint-Barthélemy and Saint-Martin."""

    @classproperty
    def catala_scope(cls) -> str:
        """``ÉligibilitéAidesPersonnelleLogement``."""
        return "ÉligibilitéAidesPersonnelleLogement"

    @cached_property
    def family_benefits(self) -> Household:
        """The household as the family benefits of the subscope ``prestations_familiales`` see it."""
        age_limit = self.sole_conclusion(ChildAgeLimitProvision)
        return self.family_benefits_household(age_limit.age)

    def output(self, variable: str) -> CatalaValue:
        counted = self.sole_conclusion(CountedDependantsProvision)
        match EligibilityOutput(variable):
            case EligibilityOutput.ELIGIBILITY:
                return self.sole_conclusion(CommonEligibilityProvision).holds
            case EligibilityOutput.DEPENDANT_COUNT:
                return None if counted is None else len(counted.dependants)
            case EligibilityOutput.SHARED_RESIDENCE_COEFFICIENTS:
                return (
                    None if counted is None else counted.shared_residence_coefficients
                )


@dataclass(eq=False)
class CallingEligibilityCase(HousingEligibilityCase, ABC):
    """An eligibility scope calling the common conditions as its subscope ``éligibilité_commune``."""

    @property
    @abstractmethod
    def common(self) -> CommonEligibilityCase:
        """The common conditions, with the context variables the scope sets."""

    def common_output(self, variable: EligibilityOutput) -> CatalaValue:
        """:return: The output *variable* of the common conditions."""
        return self.common.output(variable)


@dataclass(eq=False)
class PersonalisedAidEligibilityCase(CallingEligibilityCase):
    """The eligibility for the personalised housing aid, Catala's ``ÉligibilitéAidePersonnaliséeLogement``."""

    @classproperty
    def catala_scope(cls) -> str:
        """``ÉligibilitéAidePersonnaliséeLogement``."""
        return "ÉligibilitéAidePersonnaliséeLogement"

    @classproperty
    def deferred_entry_into_force_for_buyers(cls) -> datetime.date:
        """R862-2: the day the code applies from in Saint-Barthélemy and Saint-Martin to a home bought."""
        return datetime.date(2021, 5, 1)

    @cached_property
    def common(self) -> CommonEligibilityCase:
        """The common conditions, R862-2 setting a later day for a home bought."""
        if isinstance(self.household.dwelling.occupancy, HomeBuyer):
            return CommonEligibilityCase(
                household=self.household,
                applicant=self.applicant,
                assessment_date=self.assessment_date,
                deferred_entry_into_force=self.deferred_entry_into_force_for_buyers,
            )
        return CommonEligibilityCase(
            household=self.household,
            applicant=self.applicant,
            assessment_date=self.assessment_date,
        )

    def output(self, variable: str) -> CatalaValue:
        if EligibilityOutput(variable) == EligibilityOutput.ELIGIBILITY:
            return self.sole_conclusion(PersonalisedAidEligibilityProvision).holds
        return self.common_output(EligibilityOutput(variable))


@dataclass(eq=False)
class HousingAllowanceEligibilityCase(CallingEligibilityCase):
    """The eligibility for the housing allowances, Catala's ``ÉligibilitéAllocationLogement``."""

    receives_personalised_aid: bool = False
    """Whether the household receives the personalised housing aid."""

    @classproperty
    def catala_scope(cls) -> str:
        """``ÉligibilitéAllocationLogement``."""
        return "ÉligibilitéAllocationLogement"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """Extends the shared inputs with whether the household receives the personalised aid."""
        return super().catala_names | {
            "bénéficie_aide_personnalisée_logement": "receives_personalised_aid"
        }

    @cached_property
    def common(self) -> CommonEligibilityCase:
        """
        The common conditions, R842-14 stating the main residence and surface conditions
        met in a residence hall built under the law of 1957.
        """
        occupancy = self.household.dwelling.occupancy
        stated = (
            isinstance(occupancy, ResidenceHallResident)
            and occupancy.hall.built_under_1957_law
        )
        return CommonEligibilityCase(
            household=self.household,
            applicant=self.applicant,
            assessment_date=self.assessment_date,
            main_residence_stated=stated,
            surface_stated=stated,
        )

    @cached_property
    def family_benefits(self) -> Household:
        """The household as the family benefits of the subscope ``prestations_familiales`` see it, R512-2's age limit holding."""
        return self.family_benefits_household(None)

    def output(self, variable: str) -> CatalaValue:
        if EligibilityOutput(variable) == EligibilityOutput.ELIGIBILITY:
            return self.sole_conclusion(HousingAllowanceEligibilityProvision).allowance
        return self.common_output(EligibilityOutput(variable))


# %% provisions


@dataclass
class HousingEligibilityProvision(ScopeProvision, ABC):
    """A provision of the eligibility for the housing aids."""

    @classproperty
    def overseas_departments(cls) -> frozenset[Territory]:
        """The overseas departments of L861-1: Guadeloupe, French Guiana, Martinique, La Réunion and Mayotte."""
        return frozenset(
            {
                Territory.GUADELOUPE,
                Territory.FRENCH_GUIANA,
                Territory.MARTINIQUE,
                Territory.REUNION,
                Territory.MAYOTTE,
            }
        )

    @classproperty
    def overseas_collectivities(cls) -> frozenset[Territory]:
        """The collectivities of L862-1: Saint-Barthélemy and Saint-Martin."""
        return frozenset({Territory.SAINT_BARTHELEMY, Territory.SAINT_MARTIN})

    @classproperty
    def first_day_of_r823_4(cls) -> datetime.date:
        """The first day R823-4 counts the persons in the household's charge from, as Catala's example states it."""
        return datetime.date(2019, 9, 1)

    @classproperty
    def first_day_of_2023_pension_reform(cls) -> datetime.date:
        """The first day of the version of R823-4 and of the pension ages of September 2023."""
        return datetime.date(2023, 9, 1)


# %% the common conditions


@dataclass
class ChildAgeLimitProvision(HousingEligibilityProvision):
    """
    R823-4: a child counts up to age 21 from September 2019; D861-9 sets 22 in the
    overseas departments, R862-2 in Saint-Barthélemy and Saint-Martin from the code's
    entry into force there.
    """

    @classproperty
    def age_limit(cls) -> int:
        """R823-4: 21."""
        return 21

    @classproperty
    def overseas_age_limit(cls) -> int:
        """D861-9 and R862-2: 22."""
        return 22

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        limit = deduced_variable(ChildAgeLimit)
        query = an(
            entity(limit).where(
                in_(case.household.residence, self.overseas_departments)
            )
        )
        with query:
            add(limit, inference(ChildAgeLimit)(case=case, age=self.overseas_age_limit))
            with alternative(
                in_(case.household.residence, self.overseas_collectivities),
                case.assessment_date >= case.deferred_entry_into_force,
            ):
                add(
                    limit,
                    inference(ChildAgeLimit)(case=case, age=self.overseas_age_limit),
                )
            with alternative(case.assessment_date >= self.first_day_of_r823_4):
                add(limit, inference(ChildAgeLimit)(case=case, age=self.age_limit))
            with alternative():
                add(limit, inference(ChildAgeLimit)(case=case, age=None))
        return query


@dataclass
class NationalityConditionProvision(HousingEligibilityProvision):
    """
    L822-2: a French applicant, or a foreigner meeting the conditions of L512-2 of the
    Code de la sécurité sociale; L861-5 asks in Mayotte a foreigner meeting article 4 of
    the ordinance of 2002, and excludes a French applicant, as Catala reads it.
    """

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        nationality = case.applicant.nationality
        foreign = type_(nationality) == Foreign
        condition = deduced_variable(NationalityCondition)
        query = an(
            entity(condition).where(case.household.residence == Territory.MAYOTTE)
        )
        with query:
            add(condition, self.inferred(case, False))
            with refinement(
                foreign, nationality.conditions.meets_mayotte_ordinance_article_4
            ):
                add(condition, self.inferred(case, True))
            with alternative(foreign, not_(nationality.conditions.meets_l512_2)):
                add(condition, self.inferred(case, False))
            with alternative():
                add(condition, self.inferred(case, True))
        return query

    @staticmethod
    def inferred(case: CommonEligibilityCase, holds: bool) -> NationalityCondition:
        """:return: The inference that the condition holds or not, over a variable of the case."""
        return inference(NationalityCondition)(case=case, holds=holds)


@dataclass
class MainResidenceConditionProvision(HousingEligibilityProvision):
    """L821-2: the dwelling is the household's main residence, or a calling scope states it so."""

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        condition = deduced_variable(MainResidenceCondition)
        query = an(
            entity(condition).where(
                or_(
                    case.main_residence_stated == True,
                    case.household.dwelling.main_residence == True,
                )
            )
        )
        with query:
            add(condition, inference(MainResidenceCondition)(case=case, holds=True))
            with alternative():
                add(
                    condition, inference(MainResidenceCondition)(case=case, holds=False)
                )
        return query


@dataclass
class OccupancyConditionProvision(HousingEligibilityProvision):
    """
    L822-2: a tenant, subtenant, resident of a residence hall or buyer under a lease-to-own
    contract, and a buyer whose home is their main residence. L822-3 excludes a tenant
    whose dwelling the applicant or their family owns or holds in usufruct, unless the
    shares held are below R822-1's thresholds.
    """

    @classproperty
    def ownership_threshold(cls) -> Fraction:
        """R822-1: the share of the ownership below which a family holding does not exclude the aid, 10 %."""
        return Fraction(10, 100)

    @classproperty
    def usufruct_threshold(cls) -> Fraction:
        """R822-1: the share of the usufruct below which a family holding does not exclude the aid, 10 %."""
        return Fraction(10, 100)

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        dwelling = case.household.dwelling
        family_owns = type_(dwelling.owner) == FamilyRightHolder
        family_holds_usufruct = type_(dwelling.usufructuary) == FamilyRightHolder
        condition = deduced_variable(OccupancyCondition)
        query = an(
            entity(condition).where(
                type_(dwelling.occupancy) == Tenant,
                or_(family_owns, family_holds_usufruct),
            )
        )
        with query:
            add(condition, inference(OccupancyCondition)(case=case, holds=False))
            with refinement(
                or_(not_(family_owns), dwelling.owner.share < self.ownership_threshold),
                or_(
                    not_(family_holds_usufruct),
                    dwelling.usufructuary.share < self.usufruct_threshold,
                ),
            ):
                add(condition, inference(OccupancyCondition)(case=case, holds=True))
            with alternative(
                type_(dwelling.occupancy) == HomeBuyer,
                dwelling.main_residence == False,
            ):
                add(condition, inference(OccupancyCondition)(case=case, holds=False))
            with alternative():
                add(condition, inference(OccupancyCondition)(case=case, holds=True))
        return query


@dataclass
class SublettingConditionProvision(HousingEligibilityProvision):
    """
    L822-4: a dwelling not let to third parties, or sublet to a person under 30 or as
    L442-1 allows.
    """

    @classproperty
    def subtenant_age(cls) -> int:
        """L822-4: the age a subtenant is to be under, 30."""
        return 30

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        subletting = case.household.dwelling.subletting
        condition = deduced_variable(SublettingCondition)
        query = an(
            entity(condition).where(
                or_(
                    type_(subletting) == NotSublet,
                    and_(
                        type_(subletting) == Sublet,
                        or_(
                            Anniversary.rounded_up_date_after(
                                subletting.occupant.birth_date, self.subtenant_age
                            )
                            > case.assessment_date,
                            subletting.occupant.complies_with_l442_1 == True,
                        ),
                    ),
                )
            )
        )
        with query:
            add(condition, inference(SublettingCondition)(case=case, holds=True))
            with alternative():
                add(condition, inference(SublettingCondition)(case=case, holds=False))
        return query


@dataclass
class SurfaceConditionProvision(HousingEligibilityProvision):
    """
    R822-25: 9 m² for a person alone, 16 for a couple, 9 more for each other person, 70
    at most for eight persons or more; R861-5 sets 9, 13 and 54 for nine in Mayotte.
    R844-4 asks a household of elderly or disabled persons of at most two 9 or 16 m².
    """

    @classproperty
    def surface_per_adult_count(cls) -> dict[int, int]:
        """R822-25: the surface for one adult, 9 m², and for two, 16."""
        return {1: 9, 2: 16}

    @classproperty
    def mayotte_surface_per_adult_count(cls) -> dict[int, int]:
        """R861-5: the surface for one adult, 9 m², and for two, 13."""
        return {1: 9, 2: 13}

    @classproperty
    def surface_per_other_person(cls) -> int:
        """R822-25 and R861-5: 9 m² for each other person."""
        return 9

    @classproperty
    def largest_surface_asked(cls) -> int:
        """R822-25: 70 m² at most."""
        return 70

    @classproperty
    def persons_for_largest_surface(cls) -> int:
        """R822-25: for eight persons or more."""
        return 8

    @classproperty
    def mayotte_largest_surface_asked(cls) -> int:
        """R861-5: 54 m² at most."""
        return 54

    @classproperty
    def mayotte_persons_for_largest_surface(cls) -> int:
        """R861-5: for nine persons or more."""
        return 9

    @classproperty
    def elderly_or_disabled_largest_household(cls) -> int:
        """R844-4: two persons at most."""
        return 2

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        household: HousingHousehold = self.case.household
        persons = (
            household.family_situation.adult_count
            + household.other_occupants
            + len(household.dependants)
        )
        others = household.other_occupants + len(household.dependants)
        surface = case.household.dwelling.surface_square_metres
        adults = household.family_situation.adult_count
        asked = (
            self.surface_per_adult_count[adults]
            + others * self.surface_per_other_person
        )
        if (
            asked >= self.largest_surface_asked
            and persons >= self.persons_for_largest_surface
        ):
            asked = self.largest_surface_asked
        mayotte_asked = (
            self.mayotte_surface_per_adult_count[adults]
            + others * self.surface_per_other_person
        )
        if (
            mayotte_asked >= self.mayotte_largest_surface_asked
            and persons >= self.mayotte_persons_for_largest_surface
        ):
            mayotte_asked = self.mayotte_largest_surface_asked
        elderly_asked = self.surface_per_adult_count[1 if persons == 1 else 2]
        elderly = case.household.elderly_or_disabled_r844_4 == True
        condition = deduced_variable(SurfaceCondition)
        query = an(entity(condition).where(case.surface_stated == True))
        with query:
            add(condition, self.inferred(case, True))
            with alternative(
                elderly, persons > self.elderly_or_disabled_largest_household
            ):
                add(condition, self.inferred(case, False))
            with alternative(elderly, surface >= elderly_asked):
                add(condition, self.inferred(case, True))
            with alternative(
                case.household.residence == Territory.MAYOTTE, surface >= mayotte_asked
            ):
                add(condition, self.inferred(case, True))
            with alternative(surface >= asked):
                add(condition, self.inferred(case, True))
            with alternative():
                add(condition, self.inferred(case, False))
        return query

    @staticmethod
    def inferred(case: CommonEligibilityCase, holds: bool) -> SurfaceCondition:
        """:return: The inference that the condition holds or not, over a variable of the case."""
        return inference(SurfaceCondition)(case=case, holds=holds)


@dataclass
class DwellingConditionProvision(HousingEligibilityProvision):
    """
    The conditions on the dwelling: main residence (L821-2), occupancy (L822-2), letting
    to third parties (L822-4) and surface (L822-10); L822-8 excludes an applicant
    attached to a parent liable to the real estate wealth tax, L822-9 an indecent dwelling.
    """

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        main_residence = self.condition(MainResidenceConditionProvision)
        occupancy = self.condition(OccupancyConditionProvision)
        subletting = self.condition(SublettingConditionProvision)
        surface = self.condition(SurfaceConditionProvision)
        condition = deduced_variable(DwellingCondition)
        query = an(
            entity(condition).where(
                or_(
                    case.household.attached_to_wealth_taxed_parent == True,
                    case.household.dwelling.decent == False,
                )
            )
        )
        with query:
            add(condition, inference(DwellingCondition)(case=case, holds=False))
            with alternative(
                main_residence.holds == True,
                occupancy.holds == True,
                subletting.holds == True,
                surface.holds == True,
            ):
                add(condition, inference(DwellingCondition)(case=case, holds=True))
            with alternative():
                add(condition, inference(DwellingCondition)(case=case, holds=False))
        return query

    def condition(self, provision: type[HousingEligibilityProvision]) -> CaseCondition:
        """:return: A variable over the one conclusion *provision* draws about the case."""
        return variable(CaseCondition, domain=provision(case=self.case).conclusions)


@dataclass
class RetirementAgeProvision(HousingEligibilityProvision):
    """
    L161-17-2 and D161-2-1-9 of the Code de la sécurité sociale: the age the applicant's
    right to a pension opens at, by birth date; 64 for those born from 1968 from
    September 2023.
    """

    @classproperty
    def ages_by_birth(cls) -> list[tuple[datetime.date, datetime.date, Duration]]:
        """D161-2-1-9: the first and last birth date of each age, and the age."""
        return [
            (datetime.date(1, 1, 1), datetime.date(1951, 6, 30), Duration(years=60)),
            (
                datetime.date(1951, 7, 1),
                datetime.date(1951, 12, 31),
                Duration(years=60, months=4),
            ),
            (
                datetime.date(1952, 1, 1),
                datetime.date(1952, 12, 31),
                Duration(years=60, months=9),
            ),
            (
                datetime.date(1953, 1, 1),
                datetime.date(1953, 12, 31),
                Duration(years=61, months=2),
            ),
            (
                datetime.date(1954, 1, 1),
                datetime.date(1954, 12, 31),
                Duration(years=61, months=7),
            ),
        ]

    @classproperty
    def ages_by_birth_from_2023(
        cls,
    ) -> list[tuple[datetime.date, datetime.date, Duration]]:
        """
        D161-2-1-9 from after September 1, 2023, for those born from 1955 to 1967, and
        L161-17-2 from that day, for those born from 1968, last.
        """
        return [
            (datetime.date(1955, 1, 1), datetime.date(1961, 8, 31), Duration(years=62)),
            (
                datetime.date(1961, 9, 1),
                datetime.date(1961, 12, 31),
                Duration(years=62, months=3),
            ),
            (
                datetime.date(1962, 1, 1),
                datetime.date(1962, 12, 31),
                Duration(years=62, months=6),
            ),
            (
                datetime.date(1963, 1, 1),
                datetime.date(1963, 12, 31),
                Duration(years=62, months=9),
            ),
            (
                datetime.date(1964, 1, 1),
                datetime.date(1964, 12, 31),
                Duration(years=63),
            ),
            (
                datetime.date(1965, 1, 1),
                datetime.date(1965, 12, 31),
                Duration(years=63, months=3),
            ),
            (
                datetime.date(1966, 1, 1),
                datetime.date(1966, 12, 31),
                Duration(years=63, months=6),
            ),
            (
                datetime.date(1967, 1, 1),
                datetime.date(1967, 12, 31),
                Duration(years=62, months=9),
            ),
            (
                datetime.date(1968, 1, 1),
                datetime.date(9999, 12, 31),
                Duration(years=64),
            ),
        ]

    @classproperty
    def first_birth_of_62(cls) -> datetime.date:
        """L161-17-2 before September 2023: January 1, 1955."""
        return datetime.date(1955, 1, 1)

    @classproperty
    def age_before_2023(cls) -> Duration:
        """L161-17-2 before September 2023: 62 for those born from 1955."""
        return Duration(years=62)

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        birth = case.applicant.birth_date
        reformed = case.assessment_date >= self.first_day_of_2023_pension_reform
        age = deduced_variable(RetirementAge)
        first, last, first_age = self.ages_by_birth[0]
        # D161-2-1-9 holds before the reform day and after it, not on it
        not_reform_day = case.assessment_date != self.first_day_of_2023_pension_reform
        after_reform_day = case.assessment_date > self.first_day_of_2023_pension_reform
        query = an(entity(age).where(not_reform_day, birth >= first, birth <= last))
        with query:
            add(age, inference(RetirementAge)(case=case, age=first_age))
            for first, last, value in self.ages_by_birth[1:]:
                with alternative(not_reform_day, birth >= first, birth <= last):
                    add(age, inference(RetirementAge)(case=case, age=value))
            *by_decree, (first, last, by_law) = self.ages_by_birth_from_2023
            with alternative(reformed, birth >= first, birth <= last):
                add(age, inference(RetirementAge)(case=case, age=by_law))
            for first, last, value in by_decree:
                with alternative(after_reform_day, birth >= first, birth <= last):
                    add(age, inference(RetirementAge)(case=case, age=value))
            with alternative(not_(reformed), birth >= self.first_birth_of_62):
                add(age, inference(RetirementAge)(case=case, age=self.age_before_2023))
        return query


@dataclass
class IndividualCeilingProvision(HousingEligibilityProvision):
    """L815-9 of the Code de la sécurité sociale: the individual ceiling in force on the assessment date."""

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        ceiling = variable(
            IndividualCeiling, domain=[member.value for member in IndividualCeilings]
        )
        return an(
            entity(
                inference(IndividualCeilingAmount)(case=case, amount=ceiling.amount)
            ).where(DatedValue.is_in_force(ceiling, case.assessment_date))
        )


@dataclass
class DependantProvision(HousingEligibilityProvision, ABC):
    """A provision concluding about each person in the household's charge."""

    @property
    def conclusions(self) -> list[DependantCondition]:
        """Extends :meth:`Provision.conclusions`: none for a household without persons in its charge."""
        # krrood raises on an else-if chain over an empty domain:
        # https://github.com/cram2/cognitive_robot_abstract_machine/issues/952
        if not self.case.household.dependants:
            return []
        return super().conclusions


@dataclass
class ElderlyAscendantConditionProvision(DependantProvision):
    """
    R823-4 2°, from September 2019: an ascendant whose resources are at most 125 % of
    the individual ceiling, of the age of L351-8 1° or over 65 holding an allowance for
    the elderly, or of pension age benefiting from L161-19, L351-8 or L643-3.
    """

    @classproperty
    def resources_share_of_ceiling(cls) -> Fraction:
        """R823-4: 125 % of the individual ceiling."""
        return Fraction(125, 100)

    @classproperty
    def old_age_allowance_age(cls) -> int:
        """R823-4: 65 years."""
        return 65

    @classproperty
    def years_after_pension_age_before_2023(cls) -> Duration:
        """L351-8 1° before September 2023: five years after the pension age."""
        return Duration(years=5)

    @classproperty
    def years_after_pension_age(cls) -> Duration:
        """L351-8 1° from September 2023: three years after the pension age."""
        return Duration(years=3)

    @classproperty
    def long_career_age(cls) -> Duration:
        """D351-1-14: the age of L351-1-5, 62 years."""
        return Duration(years=62)

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        dependant = variable(Dependant, domain=self.case.household.dependants)
        ceiling = variable(
            IndividualCeilingAmount,
            domain=IndividualCeilingProvision(case=self.case).conclusions,
        )
        retirement = self.sole_retirement_age()
        reformed = self.case.assessment_date >= self.first_day_of_2023_pension_reform
        full_rate_age = Duration(
            years=retirement.years
            + (
                self.years_after_pension_age
                if reformed
                else self.years_after_pension_age_before_2023
            ).years,
            months=retirement.months,
        )
        benefit_age = self.long_career_age if reformed else retirement
        person = dependant.person
        condition = deduced_variable(ElderlyAscendantCondition)
        query = an(
            entity(condition).where(
                case.assessment_date >= self.first_day_of_r823_4,
                type_(dependant) == OtherDependant,
                person.kinship == Kinship.ASCENDANT,
                person.resources <= ceiling.amount * self.resources_share_of_ceiling,
                or_(
                    Anniversary.date_after(person.birth_date, full_rate_age)
                    <= case.assessment_date,
                    and_(
                        person.old_age_allowance_holder == True,
                        Anniversary.rounded_up_date_after(
                            person.birth_date, self.old_age_allowance_age
                        )
                        <= case.assessment_date,
                    ),
                    and_(
                        Anniversary.date_after(person.birth_date, benefit_age)
                        <= case.assessment_date,
                        person.beneficiary_l161_19_l351_8_l643_3 == True,
                    ),
                ),
            )
        )
        with query:
            add(
                condition,
                inference(ElderlyAscendantCondition)(
                    case=case, dependant=dependant, holds=True
                ),
            )
            with alternative():
                add(
                    condition,
                    inference(ElderlyAscendantCondition)(
                        case=case, dependant=dependant, holds=False
                    ),
                )
        return query

    def sole_retirement_age(self) -> Duration:
        """:return: The applicant's pension age, which Catala's example takes for the ascendant's."""
        return self.case.sole_conclusion(RetirementAgeProvision).age


@dataclass
class CountedDependantProvision(DependantProvision):
    """
    R823-4, from September 2019: a child giving a right to family benefits up to the
    housing aids' age limit, an ascendant of 2°, a relative of 3° disabled at 80 % with
    resources within 125 % of the ceiling. L823-1 excepts a foreign child not meeting
    L512-2 but in Mayotte; L861-6 and L862-3 a studying child past schooling, under the limit.
    """

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        dependant = variable(Dependant, domain=self.case.household.dependants)
        entitlement = variable(
            FamilyBenefitEntitlement,
            domain=FamilyBenefitEntitlementProvision(
                household=self.case.family_benefits
            ).conclusions,
        )
        elderly = variable(
            ElderlyAscendantCondition,
            domain=ElderlyAscendantConditionProvision(case=self.case).conclusions,
        )
        ceiling = variable(
            IndividualCeilingAmount,
            domain=IndividualCeilingProvision(case=self.case).conclusions,
        )
        stated_age_limit = self.case.sole_conclusion(ChildAgeLimitProvision).age
        age_limit = (
            FamilyBenefitEntitlementProvision.age_limit
            if stated_age_limit is None
            else stated_age_limit
        )
        counted_from = case.assessment_date >= self.first_day_of_r823_4
        child = dependant.child
        is_child = type_(dependant) == ChildDependant
        person = dependant.person
        counted = deduced_variable(CountedDependant)
        query = an(
            entity(counted).where(
                is_child,
                case.household.residence != Territory.MAYOTTE,
                type_(child.nationality) == Foreign,
                child.nationality.conditions.meets_l512_2 == False,
            )
        )
        with query:
            add(counted, self.inferred(case, dependant, False))
            with alternative(
                is_child,
                or_(
                    in_(case.household.residence, self.overseas_departments),
                    in_(case.household.residence, self.overseas_collectivities),
                ),
                child.schooling_stage == SchoolingStage.AFTER,
                Anniversary.rounded_up_date_after(child.birth_date, age_limit)
                > case.assessment_date,
                child.studying_or_unable_to_work == True,
            ):
                add(counted, self.inferred(case, dependant, False))
            # the child's entitlement is joined with exists, the default otherwise firing
            # for every entitlement of another child (cram2/cognitive_robot_abstract_machine#970)
            with alternative(
                counted_from,
                is_child,
                exists(
                    entitlement,
                    and_(
                        entitlement.child.dependant == dependant,
                        entitlement.holds == True,
                    ),
                ),
            ):
                add(counted, self.inferred(case, dependant, True))
            with alternative(
                counted_from,
                type_(dependant) == OtherDependant,
                person.related_up_to_third_degree == True,
                person.disabled_or_restricted_from_work == True,
                person.resources
                <= ceiling.amount
                * ElderlyAscendantConditionProvision.resources_share_of_ceiling,
            ):
                add(counted, self.inferred(case, dependant, True))
            with alternative(
                counted_from,
                exists(
                    elderly,
                    and_(elderly.dependant == dependant, elderly.holds == True),
                ),
            ):
                add(counted, self.inferred(case, dependant, True))
            with alternative():
                add(counted, self.inferred(case, dependant, False))
        return query

    @staticmethod
    def inferred(
        case: CommonEligibilityCase, dependant: Dependant, holds: bool
    ) -> CountedDependant:
        """:return: The inference that the person counts or not, over variables of the case and person."""
        return inference(CountedDependant)(case=case, dependant=dependant, holds=holds)


@dataclass
class CountedDependantsProvision(HousingEligibilityProvision):
    """R823-4: the persons counted as in the household's charge, from September 2019."""

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        counted = variable(
            CountedDependant,
            domain=CountedDependantProvision(case=self.case).conclusions,
        )
        dependants = an(entity(counted.dependant).where(counted.holds == True))
        return an(
            entity(
                inference(CountedDependants)(case=case, dependants=dependants.tolist())
            ).where(case.assessment_date >= self.first_day_of_r823_4)
        )


@dataclass
class CommonEligibilityProvision(HousingEligibilityProvision):
    """
    The conditions common to every housing aid hold where those of nationality, of
    occupancy and of the dwelling do.
    """

    def query(self) -> Query:
        case = variable(CommonEligibilityCase, domain=[self.case])
        nationality = variable(
            NationalityCondition,
            domain=NationalityConditionProvision(case=self.case).conclusions,
        )
        occupancy = variable(
            OccupancyCondition,
            domain=OccupancyConditionProvision(case=self.case).conclusions,
        )
        dwelling = variable(
            DwellingCondition,
            domain=DwellingConditionProvision(case=self.case).conclusions,
        )
        eligibility = deduced_variable(CommonEligibility)
        query = an(
            entity(eligibility).where(
                nationality.holds == True,
                occupancy.holds == True,
                dwelling.holds == True,
            )
        )
        with query:
            add(eligibility, inference(CommonEligibility)(case=case, holds=True))
            with alternative():
                add(eligibility, inference(CommonEligibility)(case=case, holds=False))
        return query


# %% the personalised housing aid


@dataclass
class LandlordConditionProvision(HousingEligibilityProvision):
    """
    L831-1: a home bought with a loan of R832-5 or R832-7, a dwelling let by a social
    landlord or a private one under agreement, and a residence hall under agreement or
    meeting R832-21. R832-20 excludes a residence hall of no listed kind, R861-20 overseas
    from April 5, 2023 a hostel for young workers or migrants agreed before 1995.
    """

    @classproperty
    def first_day_of_r861_20(cls) -> datetime.date:
        """R861-20: April 5, 2023."""
        return datetime.date(2023, 4, 5)

    def query(self) -> Query:
        case = variable(PersonalisedAidEligibilityCase, domain=[self.case])
        occupancy = case.household.dwelling.occupancy
        hall = occupancy.hall
        overseas = in_(case.household.residence, self.overseas_departments)
        loan = occupancy.owner.loan
        landlord = occupancy.tenancy.landlord
        condition = deduced_variable(LandlordCondition)
        query = an(
            entity(condition).where(
                type_(occupancy) == ResidenceHallResident,
                or_(
                    hall.hall_type == ResidenceHallType.OTHER,
                    and_(
                        overseas,
                        case.assessment_date >= self.first_day_of_r861_20,
                        hall.hall_type
                        == ResidenceHallType.YOUNG_WORKERS_OR_MIGRANTS_BEFORE_1995,
                    ),
                ),
            )
        )
        with query:
            add(condition, self.inferred(case, False))
            with alternative(
                type_(occupancy) == ResidenceHallResident,
                or_(
                    hall.agreed_under_book_iii_title_v_chapter_iii == True,
                    hall.meets_r832_21 == True,
                    and_(overseas, hall.agreed_under_overseas_rules == True),
                ),
            ):
                add(condition, self.inferred(case, True))
            with alternative(
                type_(occupancy) == HomeBuyer,
                or_(
                    and_(
                        loan.holder == LoanHolder.APPLICANT,
                        in_(
                            loan.loan_type,
                            {LoanType.ARTICLE_D331_32, LoanType.ARTICLES_D331_63_64},
                        ),
                    ),
                    and_(
                        loan.holder == LoanHolder.SELLER_UNDER_LEASE_TO_OWN,
                        in_(
                            loan.loan_type,
                            {LoanType.ARTICLE_D331_59_8, LoanType.ARTICLE_D331_76_1},
                        ),
                    ),
                ),
            ):
                add(condition, self.inferred(case, True))
            with alternative(
                type_(occupancy) == Tenant,
                or_(
                    and_(
                        type_(landlord) == SocialLandlord,
                        landlord.agreement.agreed_under_book_iii_title_v_chapter_iii
                        == True,
                    ),
                    and_(
                        type_(landlord) == AgreedPrivateLandlord,
                        landlord.agreement.agreed_under_book_iii_title_ii_chapter_i_section_3
                        == True,
                    ),
                ),
            ):
                add(condition, self.inferred(case, True))
            # L831-1 6°, for a lease-to-own buyer, has no rule in Catala's example
            with alternative():
                add(condition, self.inferred(case, False))
        return query

    @staticmethod
    def inferred(
        case: PersonalisedAidEligibilityCase, holds: bool
    ) -> LandlordCondition:
        """:return: The inference that the condition holds or not, over a variable of the case."""
        return inference(LandlordCondition)(case=case, holds=holds)


@dataclass
class LoanConditionProvision(HousingEligibilityProvision):
    """
    L831-2: no personalised aid for a home bought with a loan signed from December 31,
    2017; but for an old home bought with a loan signed in 2018 or 2019 in a commune
    of imbalance, which Catala's example never finds.
    """

    @classproperty
    def first_excluded_signature(cls) -> datetime.date:
        """L831-2: December 31, 2017."""
        return datetime.date(2017, 12, 31)

    def query(self) -> Query:
        case = variable(PersonalisedAidEligibilityCase, domain=[self.case])
        occupancy = case.household.dwelling.occupancy
        condition = deduced_variable(LoanCondition)
        query = an(
            entity(condition).where(
                in_(type_(occupancy), {HomeBuyer, LeaseToOwnBuyer}),
                occupancy.owner.loan.signature_date >= self.first_excluded_signature,
            )
        )
        with query:
            # the commune of imbalance of L831-2 has no rule in Catala's example
            add(condition, inference(LoanCondition)(case=case, holds=False))
            with alternative():
                add(condition, inference(LoanCondition)(case=case, holds=True))
        return query


@dataclass
class PersonalisedAidEligibilityProvision(HousingEligibilityProvision):
    """
    L831-1 and L831-2: the dwelling and loan conditions and the common conditions; L860-3
    excludes Saint-Pierre-et-Miquelon from 2021.
    """

    @classproperty
    def first_day_of_l860_3(cls) -> datetime.date:
        """L860-3: January 1, 2021."""
        return datetime.date(2021, 1, 1)

    def query(self) -> Query:
        case = variable(PersonalisedAidEligibilityCase, domain=[self.case])
        landlord = variable(
            LandlordCondition,
            domain=LandlordConditionProvision(case=self.case).conclusions,
        )
        loan = variable(
            LoanCondition, domain=LoanConditionProvision(case=self.case).conclusions
        )
        common = variable(
            CommonEligibility,
            domain=CommonEligibilityProvision(case=self.case.common).conclusions,
        )
        eligibility = deduced_variable(PersonalisedAidEligibility)
        query = an(
            entity(eligibility).where(
                case.assessment_date >= self.first_day_of_l860_3,
                case.household.residence == Territory.SAINT_PIERRE_AND_MIQUELON,
            )
        )
        with query:
            add(eligibility, self.inferred(case, False))
            with alternative(
                landlord.holds == True, loan.holds == True, common.holds == True
            ):
                add(eligibility, self.inferred(case, True))
            with alternative():
                add(eligibility, self.inferred(case, False))
        return query

    @staticmethod
    def inferred(
        case: PersonalisedAidEligibilityCase, holds: bool
    ) -> PersonalisedAidEligibility:
        """:return: The inference that the household is eligible or not, over a variable of the case."""
        return inference(PersonalisedAidEligibility)(case=case, holds=holds)


# %% the housing allowances


@dataclass
class OwnershipConditionProvision(HousingEligibilityProvision):
    """
    R842-5: any dwelling but a home bought; a home bought where the applicant holds the
    loan and the works are none, for decency, listed in R321-15, or to enlarge the home
    or make it habitable.
    """

    def query(self) -> Query:
        case = variable(HousingAllowanceEligibilityCase, domain=[self.case])
        occupancy = case.household.dwelling.occupancy
        condition = deduced_variable(OwnershipCondition)
        query = an(
            entity(condition).where(
                type_(occupancy) == HomeBuyer,
                occupancy.owner.loan.holder == LoanHolder.APPLICANT,
                in_(
                    occupancy.owner.ownership_works,
                    {
                        OwnershipWorks.NO_WORKS,
                        OwnershipWorks.DECENCY,
                        OwnershipWorks.LISTED_IN_R321_15,
                        OwnershipWorks.ENLARGE_OR_MAKE_HABITABLE,
                    },
                ),
            )
        )
        with query:
            add(condition, inference(OwnershipCondition)(case=case, holds=True))
            with alternative(type_(occupancy) == HomeBuyer):
                add(condition, inference(OwnershipCondition)(case=case, holds=False))
            with alternative():
                add(condition, inference(OwnershipCondition)(case=case, holds=True))
        return query


@dataclass
class FamilyHousingAllowanceConditionProvision(HousingEligibilityProvision):
    """
    L841-1: a household receiving a family benefit (1°), with one entitled child (2°),
    married for five years at most without a child not entitled (3°), in charge of an
    ascendant of R823-4 2° (4°) or a disabled relative (5°), or alone expecting a child (6°).
    Overseas, L861-6 and L862-3 replace 1°, 2° and 6° by an entitled child or a farmer.
    """

    @classproperty
    def years_of_marriage(cls) -> Duration:
        """D841-1: the duration of L841-1 3°, five years."""
        return Duration(years=5)

    @classproperty
    def benefits_opening_allowance(cls) -> frozenset[BenefitReceived]:
        """L841-1 1°: the family allowances, the family supplement, the family support allowance and that for a disabled child."""
        return frozenset(BenefitReceived)

    def query(self) -> Query:
        case = variable(HousingAllowanceEligibilityCase, domain=[self.case])
        household = case.household
        dependant = variable(Dependant, domain=self.case.household.dependants)
        entitlements: list[FamilyBenefitEntitlement] = (
            FamilyBenefitEntitlementProvision(
                household=self.case.family_benefits
            ).conclusions
        )
        entitled = sum(entitlement.holds for entitlement in entitlements)
        not_entitled = len(entitlements) - entitled
        elderly = variable(
            ElderlyAscendantCondition,
            domain=ElderlyAscendantConditionProvision(
                case=self.case.common
            ).conclusions,
        )
        overseas = or_(
            in_(household.residence, self.overseas_departments),
            in_(household.residence, self.overseas_collectivities),
        )
        situation = household.family_situation
        received = variable(
            BenefitReceived, domain=self.case.household.benefits_received
        )
        condition = deduced_variable(FamilyHousingAllowanceCondition)
        query = an(
            entity(condition).where(
                not_(overseas),
                exists(
                    received,
                    in_(received, self.benefits_opening_allowance),
                ),
            )
        )
        with query:
            add(condition, self.inferred(case, True))
            with alternative(not_(overseas), entitled == 1):
                add(condition, self.inferred(case, True))
            with alternative(
                not_entitled == 0,
                type_(situation) == Married,
                case.assessment_date
                <= Anniversary.date_after(
                    situation.wedding_date, self.years_of_marriage
                ),
            ):
                add(condition, self.inferred(case, True))
            with alternative(exists(elderly, elderly.holds == True)):
                add(condition, self.inferred(case, True))
            with alternative(
                exists(
                    dependant,
                    and_(
                        type_(dependant) == OtherDependant,
                        dependant.person.related_up_to_third_degree == True,
                        dependant.person.disabled_or_restricted_from_work == True,
                    ),
                )
            ):
                add(condition, self.inferred(case, True))
            with alternative(
                not_(overseas),
                type_(situation) == Single,
                len(self.case.household.dependants) == 0,
                household.child_expected_after_fourth_month == True,
            ):
                add(condition, self.inferred(case, True))
            with alternative(overseas, entitled >= 1):
                add(condition, self.inferred(case, True))
            with alternative(overseas, case.applicant.non_salaried_farmer == True):
                add(condition, self.inferred(case, True))
            with alternative():
                add(condition, self.inferred(case, False))
        return query

    @staticmethod
    def inferred(
        case: HousingAllowanceEligibilityCase, holds: bool
    ) -> FamilyHousingAllowanceCondition:
        """:return: The inference that the condition holds or not, over a variable of the case."""
        return inference(FamilyHousingAllowanceCondition)(case=case, holds=holds)


@dataclass
class HousingAllowanceEligibilityProvision(HousingEligibilityProvision):
    """
    L841-2: none where the common conditions or R842-5 fail or the household receives the
    personalised aid; else the family allowance under L841-1, or the social one. L841-3
    gives the social one in a care unit; L841-4 and L861-6 none for a loan signed after
    2017, L861-8 none in Mayotte for an official whose interests lie elsewhere.
    """

    @classproperty
    def last_signature_allowed(cls) -> datetime.date:
        """L841-4: December 31, 2017."""
        return datetime.date(2017, 12, 31)

    @classproperty
    def last_overseas_signature_allowed(cls) -> datetime.date:
        """L861-6: December 31, 2019, for a financing agreed by December 31, 2018."""
        return datetime.date(2019, 12, 31)

    @classproperty
    def last_overseas_agreement(cls) -> datetime.date:
        """L861-6: December 31, 2018."""
        return datetime.date(2018, 12, 31)

    def query(self) -> Query:
        case = variable(HousingAllowanceEligibilityCase, domain=[self.case])
        common = variable(
            CommonEligibility,
            domain=CommonEligibilityProvision(case=self.case.common).conclusions,
        )
        ownership = variable(
            OwnershipCondition,
            domain=OwnershipConditionProvision(case=self.case).conclusions,
        )
        family = variable(
            FamilyHousingAllowanceCondition,
            domain=FamilyHousingAllowanceConditionProvision(case=self.case).conclusions,
        )
        occupancy = case.household.dwelling.occupancy
        loan = occupancy.owner.loan
        agreement = loan.overseas_financing_agreement
        buyer = type_(occupancy) == HomeBuyer
        eligibility = deduced_variable(HousingAllowanceEligibility)
        query = an(
            entity(eligibility).where(
                case.household.residence == Territory.MAYOTTE,
                case.applicant.official_with_interests_outside_mayotte == True,
            )
        )
        with query:
            add(eligibility, self.inferred(case, HousingAllowanceType.NOT_ELIGIBLE))
            with alternative(
                in_(case.household.residence, self.overseas_departments),
                buyer,
                or_(
                    loan.signature_date > self.last_signature_allowed,
                    and_(
                        loan.signature_date > self.last_overseas_signature_allowed,
                        type_(agreement) == FinancingAgreed,
                        agreement.agreement_date <= self.last_overseas_agreement,
                    ),
                ),
            ):
                add(
                    eligibility,
                    self.inferred(case, HousingAllowanceType.NOT_ELIGIBLE),
                )
            with alternative(buyer, loan.signature_date > self.last_signature_allowed):
                add(
                    eligibility,
                    self.inferred(case, HousingAllowanceType.NOT_ELIGIBLE),
                )
            with alternative(case.applicant.hosted_in_care_unit == True):
                add(eligibility, self.inferred(case, HousingAllowanceType.SOCIAL))
            with alternative(
                or_(
                    common.holds == False,
                    ownership.holds == False,
                    case.receives_personalised_aid == True,
                )
            ):
                add(
                    eligibility,
                    self.inferred(case, HousingAllowanceType.NOT_ELIGIBLE),
                )
            with alternative(family.holds == True):
                add(eligibility, self.inferred(case, HousingAllowanceType.FAMILY))
            with alternative():
                add(eligibility, self.inferred(case, HousingAllowanceType.SOCIAL))
        return query

    @staticmethod
    def inferred(
        case: HousingAllowanceEligibilityCase, allowance: HousingAllowanceType
    ) -> HousingAllowanceEligibility:
        """:return: The inference of the allowance, over a variable of the case."""
        return inference(HousingAllowanceEligibility)(case=case, allowance=allowance)


# %% test files


class EligibilityTestFile(ScopeTestFile, StrEnum):
    """The test file of the eligibility of Catala's ``aides_logement`` example."""

    ELIGIBILITY = "tests_eligibilite_apl.catala_fr"
    """Three households, one asking the personalised aid and two the allowances."""

    @property
    def directory(self) -> Path:
        """:file:`aides_logement/tests`."""
        return CatalaDirectory.ROOT / "aides_logement" / "tests"

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """The eligibility for the personalised aid and for the allowances."""
        return [PersonalisedAidEligibilityCase, HousingAllowanceEligibilityCase]
