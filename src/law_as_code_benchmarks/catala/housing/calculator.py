"""
The housing aid of a household, all aids together: the computation of the personalised
aid and of the allowance whatever the dwelling (Catala's ``CalculAidePersonnaliséeLogement``
and ``CalculAllocationLogement``, D823-9), the calculator choosing between them
(``CalculetteAidesAuLogement``, L841-2) and that of children in shared residence.
"""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from functools import cached_property
from pathlib import Path

from krrood.entity_query_language.factories import (
    deduced_variable,
    inference,
    variable,
)
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from typing_extensions import Callable

from law_as_code_benchmarks.catala.domain import Territory
from law_as_code_benchmarks.catala.housing.domain import (
    Applicant,
    ChildDependant,
    FamilySituation,
    HomeBuyer,
    HousingHousehold,
    HousingZone,
    LeaseToOwnBuyer,
    NotMoved,
    Occupancy,
    ResidenceHallResident,
    SharedResidence,
    SocialLandlord,
    Subtenant,
    Tenancy,
    Tenant,
)
from law_as_code_benchmarks.catala.housing.eligibility import (
    EligibilityOutput,
    HousingAllowanceEligibility,
    HousingAllowanceEligibilityCase,
    HousingAllowanceEligibilityProvision,
    HousingAllowanceType,
    PersonalisedAidEligibility,
    PersonalisedAidEligibilityCase,
    PersonalisedAidEligibilityProvision,
)
from law_as_code_benchmarks.catala.housing.ownership import (
    OwnershipAidCase,
    OwnershipAllowanceCase,
)
from law_as_code_benchmarks.catala.housing.rented import (
    AidFamilySituation,
    AidType,
    RentedAidCase,
    RentedAllowanceCase,
)
from law_as_code_benchmarks.catala.housing.residence_hall import (
    HallAidCase,
    HallAllowanceCase,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.provision import RuleBranch, RuleChain
from law_as_code_benchmarks.catala.reader import CatalaDirectory, CatalaValue
from law_as_code_benchmarks.catala.scope_test import (
    CaseCondition,
    ScopeCase,
    ScopeProvision,
    ScopeTestFile,
)

# %% the computation whatever the dwelling


class AidComputationOutput(StrEnum):
    """The outputs of ``CalculAidePersonnaliséeLogement`` and ``CalculAllocationLogement``."""

    INITIAL_AID = "aide_finale_formule_initiale"
    """The aid the formula gives."""

    AID_TREATMENT = "traitement_aide_finale"
    """The treatment of an aid, a function."""


@dataclass(eq=False)
class AidComputationCase(ScopeCase, ABC):
    """The inputs of the computation of an aid whatever the dwelling, which D823-9 sends to the computation of its sector."""

    occupancy: Occupancy
    """How the household occupies its dwelling."""

    resources: Money
    """The household's resources, before they are rounded."""

    family_situation: FamilySituation
    """The applicant's family situation."""

    dependant_count: int
    """How many persons are in the household's charge."""

    zone: HousingZone
    """The zone the dwelling is in."""

    assessment_date: datetime.date
    """The day the aid is computed for."""

    aid_type: AidType
    """The aid computed."""

    residence: Territory
    """Where the household lives."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "mode_occupation": "occupancy",
            "ressources_ménage": "resources",
            "situation_familiale": "family_situation",
            "nombre_personnes_à_charge": "dependant_count",
            "date_courante": "assessment_date",
            "type_aide": "aid_type",
            "résidence": "residence",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`AidComputationOutput`."""
        return AidComputationOutput

    @cached_property
    def rounded_resources(self) -> Money:
        """D823-17 4°: the resources rounded up to the hundred euros, as Catala's ``arrondi_centaine_supérieure`` rounds them."""
        return (
            (self.resources * Fraction(1, 100)) + Money(cents=49)
        ).rounded_to_units() * 100

    @property
    def situation_for_scales(self) -> AidFamilySituation:
        """Article 7: a person alone, or a couple."""
        if self.family_situation.adult_count == 1:
            return AidFamilySituation.SINGLE
        return AidFamilySituation.COUPLE

    @cached_property
    @abstractmethod
    def sector(self) -> ScopeCase | None:
        """The computation of the dwelling's sector; None where the aid is nothing whatever its amount."""

    def output(self, variable: str) -> CatalaValue | Callable[[Money], Money | None]:
        if self.sector is None:
            if AidComputationOutput(variable) == AidComputationOutput.INITIAL_AID:
                return Money.zero
            return NoAid.treated_aid
        return self.sector.output(variable)

    def rented_inputs(self, tenancy: Tenancy) -> dict[str, object]:
        """:return: The inputs of the computation of a rented home with *tenancy*."""
        landlord = tenancy.landlord
        return dict(
            rent=tenancy.rent,
            resources=self.rounded_resources,
            disability_aid_recipient=tenancy.disability_aid_recipient,
            assessment_date=self.assessment_date,
            dependant_count=self.dependant_count,
            family_situation=self.situation_for_scales,
            zone=self.zone,
            is_room=tenancy.is_room,
            paying_guests_elderly_or_disabled=tenancy.paying_guests_elderly_or_disabled,
            aid_type=self.aid_type,
            is_house_share=tenancy.is_house_share,
            solidarity_rent_reduction=landlord.agreement.solidarity_rent_reduction
            if isinstance(landlord, SocialLandlord)
            else Money.zero,
            furnished_d842_2=tenancy.furnished_d842_2,
            residence=self.residence,
        )

    def hall_inputs(self, resident: ResidenceHallResident) -> dict[str, object]:
        """:return: The inputs of the computation of a residence hall for *resident*."""
        hall = resident.hall
        return dict(
            residence=self.residence,
            young_workers_hostel=hall.young_workers_hostel,
            hall_type=hall.hall_type,
            agreement_date=hall.agreement_date,
            resources=self.rounded_resources,
            dependant_count=self.dependant_count,
            family_situation=self.situation_for_scales,
            zone=self.zone,
            assessment_date=self.assessment_date,
            fee=hall.fee,
        )

    def ownership_inputs(self, buyer: HomeBuyer | LeaseToOwnBuyer) -> dict[str, object]:
        """:return: The inputs both computations of a home bought share for *buyer*."""
        owner = buyer.owner
        return dict(
            monthly_repayment=owner.monthly_repayment,
            resources=self.rounded_resources,
            dependant_count=self.dependant_count,
            family_situation=self.situation_for_scales,
            loan_signature_date=owner.loan.signature_date,
            first_occupation_by_beneficiary=owner.first_occupation_by_beneficiary,
            entry_date=owner.entry_date,
            co_ownership=owner.co_ownership,
            situation_r822_11_13_17=owner.situation_r822_11_13_17,
            zone=self.zone,
            assessment_date=self.assessment_date,
            residence=self.residence,
        )


@dataclass(frozen=True)
class NoAid:
    """The treatment of an aid that is nothing, Catala's ``traitement_nul_tout_le_temps``."""

    @staticmethod
    def treated_aid(aid: Money) -> Money:
        """:return: Nothing, whatever *aid*."""
        return Money.zero


@dataclass(eq=False)
class PersonalisedAidComputationCase(AidComputationCase):
    """D823-9: the personalised aid of the dwelling's sector, Catala's ``CalculAidePersonnaliséeLogement``."""

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculAidePersonnaliséeLogement``."""
        return "CalculAidePersonnaliséeLogement"

    @cached_property
    def sector(self) -> ScopeCase | None:
        """D823-9: a rented home, a residence hall or a home bought."""
        occupancy = self.occupancy
        if isinstance(occupancy, (Tenant, Subtenant)):
            return RentedAidCase(**self.rented_inputs(occupancy.tenancy))
        if isinstance(occupancy, ResidenceHallResident):
            return HallAidCase(**self.hall_inputs(occupancy))
        owner = occupancy.owner
        return OwnershipAidCase(
            **self.ownership_inputs(occupancy),
            acquisition_works=owner.acquisition_works,
            loan_type=owner.loan.loan_type,
            building_age=owner.building_age,
        )


@dataclass(eq=False)
class AllowanceComputationCase(AidComputationCase):
    """
    D823-9: the allowance of the dwelling's sector, Catala's ``CalculAllocationLogement``;
    D863-7 computes that of a residence hall in Saint-Pierre-et-Miquelon as a rented home's.
    """

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculAllocationLogement``."""
        return "CalculAllocationLogement"

    @cached_property
    def sector(self) -> ScopeCase | None:
        """D823-9 and D863-7: a rented home, a residence hall or a home bought."""
        occupancy = self.occupancy
        saint_pierre = self.residence == Territory.SAINT_PIERRE_AND_MIQUELON
        if isinstance(occupancy, ResidenceHallResident) and saint_pierre:
            hall = occupancy.hall
            return RentedAllowanceCase(
                **self.rented_inputs(
                    Tenancy(
                        landlord=None,
                        rent=hall.fee,
                        disability_aid_recipient=hall.disability_aid_recipient,
                        is_room=hall.is_room,
                        is_house_share=hall.is_house_share,
                        paying_guests_elderly_or_disabled=False,
                        furnished_d842_2=hall.furnished_d842_2,
                        home_change=NotMoved(),
                    )
                ),
                home_change=NotMoved(),
            )
        if isinstance(occupancy, (Tenant, Subtenant)):
            return RentedAllowanceCase(
                **self.rented_inputs(occupancy.tenancy),
                home_change=occupancy.tenancy.home_change,
            )
        if isinstance(occupancy, ResidenceHallResident):
            return HallAllowanceCase(
                **self.hall_inputs(occupancy),
                rent_category=occupancy.hall.rent_equivalence_category,
            )
        owner = occupancy.owner
        return OwnershipAllowanceCase(
            **self.ownership_inputs(occupancy),
            ownership_works=owner.ownership_works,
            monthly_loan_charges=owner.monthly_loan_charges,
            state_aided_social_scalable_housing=owner.state_aided_social_scalable_housing,
        )


# %% the calculator


class CalculatorOutput(StrEnum):
    """The outputs of ``CalculetteAidesAuLogement``."""

    ELIGIBILITY = "éligibilité"
    """Whether the household is eligible for an aid."""

    INITIAL_AID = "aide_finale_formule_initiale"
    """The aid the formula gives."""

    AID_TREATMENT = "traitement_aide_finale"
    """The treatment of an aid, a function."""

    SHARED_RESIDENCE_COEFFICIENTS = "coefficients_enfants_garde_alternée_pris_en_compte"
    """The coefficient of each child counted who lives with each parent in turn."""


@dataclass(eq=False)
class CalculatorCase(ScopeCase):
    """The household asking a housing aid, whichever it gets, Catala's ``CalculetteAidesAuLogement``."""

    household: HousingHousehold
    """The household."""

    applicant: Applicant
    """The applicant."""

    assessment_date: datetime.date
    """The day the aid is computed for."""

    resources: Money
    """The household's resources taken into account."""

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculetteAidesAuLogement``."""
        return "CalculetteAidesAuLogement"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "ménage": "household",
            "demandeur": "applicant",
            "date_courante": "assessment_date",
            "ressources_ménage_prises_en_compte": "resources",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`CalculatorOutput`."""
        return CalculatorOutput

    @cached_property
    def personalised_aid_eligibility(self) -> PersonalisedAidEligibilityCase:
        """The eligibility for the personalised aid."""
        return PersonalisedAidEligibilityCase(
            household=self.household,
            applicant=self.applicant,
            assessment_date=self.assessment_date,
        )

    @cached_property
    def allowance_eligibility(self) -> HousingAllowanceEligibilityCase:
        """L841-2: the eligibility for the allowances, the household taken not to receive the personalised aid."""
        return HousingAllowanceEligibilityCase(
            household=self.household,
            applicant=self.applicant,
            assessment_date=self.assessment_date,
            receives_personalised_aid=False,
        )

    @cached_property
    def allowance_type(self) -> HousingAllowanceType:
        """The allowance the household is eligible for."""
        return self.allowance_eligibility.output(EligibilityOutput.ELIGIBILITY)

    @cached_property
    def personalised_aid(self) -> PersonalisedAidComputationCase:
        """The personalised aid, for the persons that eligibility counts."""
        return PersonalisedAidComputationCase(
            **self.computation_inputs(self.personalised_aid_eligibility),
            aid_type=AidType.PERSONALISED_AID,
        )

    @cached_property
    def allowance(self) -> AllowanceComputationCase:
        """The allowance, of its type, for the persons that eligibility counts; the social one where none is due."""
        return AllowanceComputationCase(
            **self.computation_inputs(self.allowance_eligibility),
            aid_type=AidType.FAMILY_ALLOWANCE
            if self.allowance_type == HousingAllowanceType.FAMILY
            else AidType.SOCIAL_ALLOWANCE,
        )

    def computation_inputs(
        self,
        eligibility: PersonalisedAidEligibilityCase | HousingAllowanceEligibilityCase,
    ) -> dict[str, object]:
        """:return: The inputs both computations share, the persons counted by *eligibility*."""
        return dict(
            occupancy=self.household.dwelling.occupancy,
            resources=self.resources,
            family_situation=self.household.family_situation,
            dependant_count=eligibility.output(EligibilityOutput.DEPENDANT_COUNT),
            zone=self.household.dwelling.zone,
            assessment_date=self.assessment_date,
            residence=self.household.residence,
        )

    @cached_property
    def eligible_aids(self) -> tuple[bool, bool]:
        """Whether the household is eligible for the personalised aid, and for an allowance."""
        eligibility = self.sole_conclusion(CalculatorEligibilityProvision)
        return eligibility.personalised_aid, eligibility.allowance

    def treated_aid(self, aid: Money) -> Money | None:
        """
        :return: *aid* treated as the aid the household is eligible for treats it, the
            higher where it is eligible for both; *aid* as it is where for none.
        """
        personalised, allowance = self.eligible_aids
        if not (personalised or allowance):
            return aid
        treated_personalised = self.personalised_aid.output(
            AidComputationOutput.AID_TREATMENT
        )(aid)
        treated_allowance = self.allowance.output(AidComputationOutput.AID_TREATMENT)(
            aid
        )
        if personalised and allowance:
            return max(treated_personalised, treated_allowance)
        return treated_personalised if personalised else treated_allowance

    def initial_aid(self) -> Money | None:
        """:return: The initial aid of the aid the household is eligible for, that whose treated aid is higher where both; nothing where none."""
        personalised, allowance = self.eligible_aids
        if not (personalised or allowance):
            return Money.zero
        initial_personalised = self.personalised_aid.output(
            AidComputationOutput.INITIAL_AID
        )
        initial_allowance = self.allowance.output(AidComputationOutput.INITIAL_AID)
        if personalised and allowance:
            treated_personalised = self.personalised_aid.output(
                AidComputationOutput.AID_TREATMENT
            )(initial_personalised)
            treated_allowance = self.allowance.output(
                AidComputationOutput.AID_TREATMENT
            )(initial_allowance)
            if treated_personalised > treated_allowance:
                return initial_personalised
            return initial_allowance
        return initial_personalised if personalised else initial_allowance

    def output(self, variable: str) -> CatalaValue | Callable[[Money], Money | None]:
        match CalculatorOutput(variable):
            case CalculatorOutput.ELIGIBILITY:
                return any(self.eligible_aids)
            case CalculatorOutput.INITIAL_AID:
                return self.initial_aid()
            case CalculatorOutput.AID_TREATMENT:
                return self.treated_aid
            case CalculatorOutput.SHARED_RESIDENCE_COEFFICIENTS:
                return self.personalised_aid_eligibility.output(
                    EligibilityOutput.SHARED_RESIDENCE_COEFFICIENTS
                )


@dataclass(eq=False)
class CalculatorEligibility(CaseCondition):
    """L841-2: the household is eligible for an aid; which ones it is eligible for."""

    personalised_aid: bool = False
    """Whether it is eligible for the personalised aid."""

    allowance: bool = False
    """Whether it is eligible for an allowance."""


@dataclass
class CalculatorEligibilityProvision(ScopeProvision):
    """L841-2: eligible for the personalised aid, or for an allowance of either kind."""

    def query(self) -> Query:
        case = variable(CalculatorCase, domain=[self.case])
        personalised = variable(
            PersonalisedAidEligibility,
            domain=PersonalisedAidEligibilityProvision(
                case=self.case.personalised_aid_eligibility
            ).conclusions,
        )
        allowance = variable(
            HousingAllowanceEligibility,
            domain=HousingAllowanceEligibilityProvision(
                case=self.case.allowance_eligibility
            ).conclusions,
        )
        allowance_due = allowance.allowance != HousingAllowanceType.NOT_ELIGIBLE
        return RuleChain(
            conclusion=deduced_variable(CalculatorEligibility),
            branches=[
                RuleBranch(
                    conditions=(personalised.holds == True, allowance_due),
                    inferred=self.inferred(case, True, True),
                ),
                RuleBranch(
                    conditions=(personalised.holds == True,),
                    inferred=self.inferred(case, True, False),
                ),
                RuleBranch(
                    conditions=(allowance_due,),
                    inferred=self.inferred(case, False, True),
                ),
                RuleBranch(conditions=(), inferred=self.inferred(case, False, False)),
            ],
        ).query()

    @staticmethod
    def inferred(
        case: CalculatorCase, personalised_aid: bool, allowance: bool
    ) -> CalculatorEligibility:
        """:return: The inference of the aids the household is eligible for, over a variable of the case."""
        return inference(CalculatorEligibility)(
            case=case,
            holds=personalised_aid or allowance,
            personalised_aid=personalised_aid,
            allowance=allowance,
        )


# %% the calculator with children in shared residence


class SharedResidenceCalculatorOutput(StrEnum):
    """The outputs of ``CalculetteAidesAuLogementGardeAlternée``."""

    ELIGIBILITY = "éligibilité"
    """Whether the household is eligible for an aid."""

    AID = "aide_finale"
    """The aid paid."""


@dataclass(eq=False)
class SharedResidenceCalculatorCase(CalculatorCase):
    """
    The household asking a housing aid with children in shared residence, Catala's
    ``CalculetteAidesAuLogementGardeAlternée``: the aid without those children, and their
    share of the difference those children make, as the Conseil d'État held (n° 398563).
    """

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculetteAidesAuLogementGardeAlternée``."""
        return "CalculetteAidesAuLogementGardeAlternée"

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`SharedResidenceCalculatorOutput`."""
        return SharedResidenceCalculatorOutput

    @cached_property
    def calculator(self) -> CalculatorCase:
        """The calculator with every person in the household's charge."""
        return CalculatorCase(
            household=self.household,
            applicant=self.applicant,
            assessment_date=self.assessment_date,
            resources=self.resources,
        )

    @cached_property
    def calculator_without_shared_children(self) -> CalculatorCase:
        """The calculator without the children in shared residence."""
        household = self.household
        return CalculatorCase(
            household=HousingHousehold(
                benefits_received=household.benefits_received,
                dwelling=household.dwelling,
                dependants=[
                    dependant
                    for dependant in household.dependants
                    if not (
                        isinstance(dependant, ChildDependant)
                        and isinstance(dependant.child.care_sharing, SharedResidence)
                    )
                ],
                other_occupants=household.other_occupants,
                family_situation=household.family_situation,
                attached_to_wealth_taxed_parent=household.attached_to_wealth_taxed_parent,
                child_expected_after_fourth_month=household.child_expected_after_fourth_month,
                elderly_or_disabled_r844_4=household.elderly_or_disabled_r844_4,
                residence=household.residence,
            ),
            applicant=self.applicant,
            assessment_date=self.assessment_date,
            resources=self.resources,
        )

    def output(self, variable: str) -> CatalaValue:
        """Overrides :meth:`CalculatorCase.output`: the eligibility of the calculator, and the aid shared as n° 398563 shares it."""
        if (
            SharedResidenceCalculatorOutput(variable)
            == SharedResidenceCalculatorOutput.ELIGIBILITY
        ):
            return self.calculator.output(CalculatorOutput.ELIGIBILITY)
        return SharedResidenceAid.paid(
            self.calculator, self.calculator_without_shared_children
        )


@dataclass(frozen=True)
class SharedResidenceAid:
    """The aid of the Conseil d'État's decision n° 398563, of 21 July 2017."""

    @staticmethod
    def paid(
        calculator: CalculatorCase, without_shared_children: CalculatorCase
    ) -> Money | None:
        """
        :return: The aid without the children in shared residence, and the difference
            they make times the mean of their coefficients, treated as the calculator treats it.
        """
        coefficients: list[Fraction] = calculator.output(
            CalculatorOutput.SHARED_RESIDENCE_COEFFICIENTS
        )
        without = without_shared_children.output(CalculatorOutput.INITIAL_AID)
        with_children = calculator.output(CalculatorOutput.INITIAL_AID)
        if None in (coefficients, without, with_children):
            return None
        added = (
            Money.zero
            if not coefficients
            else (with_children - without)
            * (sum(coefficients, Fraction(0)) / len(coefficients))
        )
        return calculator.output(CalculatorOutput.AID_TREATMENT)(without + added)


# %% test files


class CalculatorTestFile(ScopeTestFile, StrEnum):
    """The test file of the calculator of Catala's ``aides_logement`` example."""

    CALCULATOR = "tests_calculette_globale.catala_fr"
    """Two households, one with a child in shared residence, one in Saint-Pierre-et-Miquelon."""

    @property
    def directory(self) -> Path:
        """:file:`aides_logement/tests`."""
        return CatalaDirectory.ROOT / "aides_logement" / "tests"

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """The calculator with children in shared residence."""
        return [SharedResidenceCalculatorCase]
