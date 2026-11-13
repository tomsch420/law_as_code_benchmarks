"""
The personal housing aids of a home bought: the personalised aid of D832-10 to D832-18
(Catala's ``CalculAidePersonnaliséeLogementAccessionPropriété``) and the housing
allowance of D842-6 to D842-12 (``CalculAllocationLogementAccessionPropriété``).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from functools import cached_property
from pathlib import Path

from krrood.entity_query_language.factories import (
    an,
    and_,
    deduced_variable,
    entity,
    in_,
    inference,
    not_,
    or_,
    variable,
)
from krrood.entity_query_language.predicate import symbolic_function
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from typing_extensions import Callable

from law_as_code_benchmarks.catala.domain import DatedValue, Territory
from law_as_code_benchmarks.catala.housing.domain import (
    AcquisitionWorks,
    BuildingAge,
    HousingZone,
    ImprovedByOccupant,
    LoanType,
    NewBuilding,
    OldBuilding,
    OwnershipWorks,
    ResidenceHallType,
)
from law_as_code_benchmarks.catala.housing.household_tables import (
    AllowancePaymentCeiling,
    BuildingCondition,
    PersonalisedAidPaymentCeiling,
    ZoneTables,
)
from law_as_code_benchmarks.catala.housing.rented import (
    AidFamilySituation,
    AidTreatment,
    RentedAidProvision,
    TreatmentProvision,
)
from law_as_code_benchmarks.catala.housing.rented_scales import (
    OverseasScale,
    OverseasScales,
    RentedHomeScale,
    RentedHomeScales,
)
from law_as_code_benchmarks.catala.housing.residence_hall import (
    CoverageRounding,
    HallAidCase,
    HallAidOutput,
    HallAidProvision,
    HallFlatReducedAidProvision,
    HallMinimumAidProvision,
    MinimumRentEquivalenceCase,
    MinimumRentEquivalenceOutput,
    NetExpense,
    PartsTable,
    PartsTables,
    SaintPierrePhaseIn,
    TreatmentChain,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.provision import RuleBranch, RuleChain
from law_as_code_benchmarks.catala.reader import CatalaDirectory, CatalaValue
from law_as_code_benchmarks.catala.scope_test import (
    CaseAmount,
    CaseCondition,
    CaseFraction,
    ScopeCase,
    ScopeProvision,
    ScopeTestFile,
)

# %% shared


@dataclass(frozen=True)
class FrancConversion:
    """The conversion of francs to euros, of the decree of December 1998 Catala's example cites."""

    @classproperty
    def euros_per_franc(cls) -> Fraction:
        """1 / 6.55957."""
        return 1 / Fraction(655957, 100000)

    @classmethod
    def factor(cls, in_francs: bool) -> Fraction:
        """:return: The factor turning an amount in francs, or one in euros, into euros."""
        return cls.euros_per_franc if in_francs else Fraction(1)


@dataclass(frozen=True)
class OwnershipParts:
    """The parts of D832-11, Catala's ``CalculNombrePartsAccessionPropriété``."""

    @staticmethod
    def parts(couple: bool, dependants: int) -> Fraction:
        """:return: The parts of a couple or a person alone with *dependants*: the table of D832-11, and half a part beyond four dependants."""
        table: PartsTable = PartsTables.ORDINARY.value
        listed = len(table.by_dependants)
        return PartsTable.base_parts(
            table, couple, dependants
        ) + table.each_further_dependant * max(dependants - listed, 0)


@dataclass(eq=False)
class OwnershipCase(ScopeCase):
    """The inputs both aids of a home bought share."""

    monthly_repayment: Money
    """The loan's monthly repayment."""

    resources: Money
    """The household's resources, rounded."""

    dependant_count: int
    """How many persons are in the household's charge."""

    family_situation: AidFamilySituation
    """Whether the household is a person alone or a couple."""

    loan_signature_date: datetime.date
    """The day the loan was signed."""

    first_occupation_by_beneficiary: bool
    """Whether the beneficiary is the first to live in the home."""

    entry_date: datetime.date
    """The day the household moved in."""

    co_ownership: bool
    """Whether the home is in a co-owned building."""

    situation_r822_11_13_17: bool
    """Whether the household is in the situation of articles R822-11, R822-13 or R822-17."""

    zone: HousingZone
    """The zone the home is in."""

    assessment_date: datetime.date
    """The day the aid is computed for."""

    residence: Territory
    """Where the household lives."""

    @property
    def is_couple(self) -> bool:
        """Whether the household is a couple."""
        return self.family_situation == AidFamilySituation.COUPLE

    @cached_property
    def parts(self) -> Fraction:
        """D832-11: the household's parts."""
        return OwnershipParts.parts(self.is_couple, self.dependant_count)

    @cached_property
    def scale(self) -> RentedHomeScale | None:
        """The flat charges of articles 19, 24, 34 and 37, those of articles 9 and 16, in force."""
        return DatedValue.value_in_force(RentedHomeScales, self.assessment_date)

    @cached_property
    def overseas_scale(self) -> OverseasScale | None:
        """The amounts of article 46 in force."""
        return DatedValue.value_in_force(OverseasScales, self.assessment_date)


@dataclass
class OwnershipProvision(ScopeProvision):
    """A provision of an aid of a home bought."""

    @property
    def conclusions(self) -> list[CaseAmount]:
        """Extends :meth:`Provision.conclusions`: none before the scales Catala's example states."""
        if self.case.scale is None:
            return []
        return super().conclusions

    def sole(self, provision: type[ScopeProvision]) -> CaseAmount:
        """:return: A variable over the one conclusion *provision* draws about the case."""
        return variable(CaseAmount, domain=provision(case=self.case).conclusions)


# %% the personalised aid


class OwnershipAidOutput(StrEnum):
    """The outputs of ``CalculAidePersonnaliséeLogementAccessionPropriété``."""

    ELIGIBLE_REPAYMENT = "mensualité_éligible"
    """The repayment within the ceiling."""

    MINIMUM_REPAYMENT = "mensualité_minimale"
    """The minimum repayment."""

    COVERAGE = "coefficient_prise_en_charge_d832_10"
    """The coefficient of coverage."""

    INITIAL_AID = "aide_finale_formule_initiale"
    """The aid the formula gives."""

    AID_TREATMENT = "traitement_aide_finale"
    """The treatment of an aid, a function."""


@dataclass(eq=False)
class OwnershipAidCase(OwnershipCase):
    """The inputs of the personalised aid of a home bought, Catala's ``CalculAidePersonnaliséeLogementAccessionPropriété``."""

    acquisition_works: AcquisitionWorks
    """The works of D832-15."""

    loan_type: LoanType
    """The article defining the loan."""

    building_age: BuildingAge
    """Whether the home is new or old."""

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculAidePersonnaliséeLogementAccessionPropriété``."""
        return "CalculAidePersonnaliséeLogementAccessionPropriété"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "mensualité_principale": "monthly_repayment",
            "ressources_ménage_arrondies": "resources",
            "nombre_personnes_à_charge": "dependant_count",
            "situation_familiale_calcul_apl": "family_situation",
            "type_travaux_logement": "acquisition_works",
            "date_signature_prêt": "loan_signature_date",
            "local_habité_première_fois_bénéficiaire": "first_occupation_by_beneficiary",
            "date_entrée_logement": "entry_date",
            "copropriété": "co_ownership",
            "situation_r822_11_13_17": "situation_r822_11_13_17",
            "type_prêt": "loan_type",
            "ancienneté_logement": "building_age",
            "date_courante": "assessment_date",
            "résidence": "residence",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`OwnershipAidOutput`."""
        return OwnershipAidOutput

    def treated_aid(self, aid: Money) -> Money | None:
        """:return: *aid* treated as ``traitement_aide_finale`` treats it; None where no rule does."""
        return AidTreatment(case=self, aid=aid).sole_amount(
            OwnershipMinimumAidProvision
        )

    def output(self, variable: str) -> CatalaValue | Callable[[Money], Money | None]:
        match OwnershipAidOutput(variable):
            case OwnershipAidOutput.AID_TREATMENT:
                return self.treated_aid
            case OwnershipAidOutput.COVERAGE:
                coverage = self.sole_conclusion(OwnershipCoverageProvision)
                return None if coverage is None else coverage.fraction
        provision = {
            OwnershipAidOutput.ELIGIBLE_REPAYMENT: EligibleRepaymentProvision,
            OwnershipAidOutput.MINIMUM_REPAYMENT: MinimumRepaymentProvision,
            OwnershipAidOutput.INITIAL_AID: OwnershipInitialAidProvision,
        }[OwnershipAidOutput(variable)]
        amount = self.sole_conclusion(provision)
        return None if amount is None else amount.amount


@dataclass(eq=False)
class RepaymentCeiling(CaseAmount):
    """D832-10 3° and D832-14: the ceiling of the monthly repayment."""


@dataclass(eq=False)
class OwnershipFlatCharges(CaseAmount):
    """D832-10, articles 19 and 24: the flat charges."""


@dataclass(eq=False)
class EligibleRepayment(CaseAmount):
    """D832-10: the repayment within the ceiling."""


@dataclass(eq=False)
class MinimumRepayment(CaseAmount):
    """D832-15: the minimum repayment."""


@dataclass(eq=False)
class OwnershipCoverage(CaseFraction):
    """D832-11: the coefficient of coverage."""


@dataclass(eq=False)
class OwnershipInitialAid(CaseAmount):
    """D832-10: the aid the formula gives."""


@dataclass(frozen=True)
class PersonalisedAidCeilingLookup:
    """Finds the payment ceiling of articles 17 and 18 for a loan, as ``calcul_plafond_mensualité_d832_10_3`` does."""

    @staticmethod
    @symbolic_function
    def ceiling(case: OwnershipAidCase, day: datetime.date) -> Money | None:
        """
        :return: The ceiling of the row for a loan signed on *day*, the exception of
            article 18 first; None where no row holds.
        """
        rows = [
            row
            for row in PersonalisedAidPaymentCeiling.rows()
            if case.assessment_date >= row.assessed_from
            and row.covers_signature(day)
            and case.loan_type in row.loan_types
            and PersonalisedAidCeilingLookup.building_matches(
                row.building, case.building_age
            )
        ]
        rows.sort(key=lambda row: not row.is_exception)
        if not rows:
            return None
        row = rows[0]
        return ZoneTables.amount_for(
            row.zones,
            case.zone,
            case.is_couple,
            case.dependant_count,
            FrancConversion.factor(row.in_francs),
        )

    @staticmethod
    def building_matches(condition: BuildingCondition, age: BuildingAge) -> bool:
        """:return: Whether a row for *condition* holds for a home of *age*."""
        match condition:
            case BuildingCondition.NEW:
                return isinstance(age, NewBuilding)
            case BuildingCondition.OLD:
                return isinstance(age, OldBuilding)
            case BuildingCondition.OLD_IMPROVED:
                return (
                    isinstance(age, OldBuilding)
                    and age.improved_by_occupant == ImprovedByOccupant.YES
                )


@dataclass
class RepaymentCeilingProvision(OwnershipProvision):
    """
    D832-14: the ceiling of the loan's signature date; for the first occupant, the higher
    of those of the signature and of the entry. Article 24 takes 75 % of it in a co-owned
    building.
    """

    @classproperty
    def co_ownership_share(cls) -> Fraction:
        """Article 24: 75 %."""
        return Fraction(75, 100)

    @property
    def conclusions(self) -> list[RepaymentCeiling]:
        """Extends :meth:`OwnershipProvision.conclusions`: none where no row of articles 17 and 18 holds for the loan."""
        if (
            PersonalisedAidCeilingLookup.ceiling(
                self.case, self.case.loan_signature_date
            )
            is None
        ):
            return []
        return super().conclusions

    def query(self) -> Query:
        case = variable(OwnershipAidCase, domain=[self.case])
        signed = PersonalisedAidCeilingLookup.ceiling(case, case.loan_signature_date)
        entered = PersonalisedAidCeilingLookup.ceiling(case, case.entry_date)
        branches = []
        for co_owned, share in (
            ((case.co_ownership == True,), self.co_ownership_share),
            ((), Fraction(1)),
        ):
            branches += [
                RuleBranch(
                    conditions=(
                        *co_owned,
                        case.first_occupation_by_beneficiary == True,
                        signed < entered,
                    ),
                    inferred=inference(RepaymentCeiling)(
                        case=case, amount=entered * share
                    ),
                ),
                RuleBranch(
                    conditions=co_owned,
                    inferred=inference(RepaymentCeiling)(
                        case=case, amount=signed * share
                    ),
                ),
            ]
        return RuleChain(
            conclusion=deduced_variable(RepaymentCeiling), branches=branches
        ).query()


@dataclass
class OwnershipFlatChargesProvision(OwnershipProvision):
    """
    Article 19: the flat charges of article 9 and more for each dependant; article 24
    halves those of a person alone in a co-owned building.
    """

    def query(self) -> Query:
        case = variable(OwnershipAidCase, domain=[self.case])
        scale: RentedHomeScale = self.case.scale
        per_dependants = scale.charges_per_dependant * self.case.dependant_count
        return RuleChain(
            conclusion=deduced_variable(OwnershipFlatCharges),
            branches=[
                RuleBranch(
                    conditions=(
                        case.co_ownership == True,
                        case.family_situation == AidFamilySituation.SINGLE,
                    ),
                    inferred=inference(OwnershipFlatCharges)(
                        case=case, amount=scale.shared_charges_single + per_dependants
                    ),
                ),
                RuleBranch(
                    conditions=(),
                    inferred=inference(OwnershipFlatCharges)(
                        case=case, amount=scale.charges + per_dependants
                    ),
                ),
            ],
        ).query()


@dataclass
class EligibleRepaymentProvision(OwnershipProvision):
    """D832-10: the repayment, the ceiling where it is higher."""

    def query(self) -> Query:
        case = variable(OwnershipCase, domain=[self.case])
        ceiling = self.sole(self.ceiling_provision)
        return RuleChain(
            conclusion=deduced_variable(EligibleRepayment),
            branches=[
                RuleBranch(
                    conditions=(case.monthly_repayment > ceiling.amount,),
                    inferred=inference(EligibleRepayment)(
                        case=case, amount=ceiling.amount
                    ),
                ),
                RuleBranch(
                    conditions=(),
                    inferred=inference(EligibleRepayment)(
                        case=case, amount=case.monthly_repayment
                    ),
                ),
            ],
        ).query()

    @property
    def ceiling_provision(self) -> type[OwnershipProvision]:
        """The provision of the ceiling of the case's aid."""
        if isinstance(self.case, OwnershipAllowanceCase):
            return AllowanceRepaymentCeilingProvision
        return RepaymentCeilingProvision


@dataclass(frozen=True)
class RepaymentBrackets:
    """The minimum repayment of D832-15 1°: the resources at a lower rate up to a limit times the parts, at a higher one beyond."""

    @staticmethod
    @symbolic_function
    def monthly(
        resources: Money,
        limit: Money,
        parts: Fraction,
        lower_rate: Fraction,
        upper_rate: Fraction,
    ) -> Money:
        """:return: The yearly amount over twelve months, as money."""
        income = Fraction(resources.cents, 100)
        bound = Fraction(limit.cents, 100) * parts
        upper = (income - bound) * upper_rate if income >= bound else Fraction(0)
        lower = (income if income <= bound else bound) * lower_rate
        return Money.from_exact_units((upper + lower) / 12)


@dataclass
class MinimumRepaymentProvision(OwnershipProvision):
    """
    D832-15 and article 23: for a purchase with or without works, 20.80 % of the
    resources up to 5,600.85 € times the parts and 41.60 % beyond, over twelve months;
    for works on a home already bought, the minimum rent equivalence of D832-26.
    """

    @classproperty
    def bracket_limit(cls) -> Money:
        """Article 23: 5,600.85 €."""
        return Money(cents=560085)

    @classproperty
    def lower_rate(cls) -> Fraction:
        """Article 23: 20.80 %."""
        return Fraction(208, 1000)

    @classproperty
    def upper_rate(cls) -> Fraction:
        """Article 23: 41.60 %."""
        return Fraction(416, 1000)

    def query(self) -> Query:
        case = variable(OwnershipAidCase, domain=[self.case])
        equivalence = MinimumRentEquivalenceCase(
            assessment_date=self.case.assessment_date,
            resources=self.case.resources,
            second_case_of_d832_25=False,
            parts=self.case.parts,
        ).output(MinimumRentEquivalenceOutput.AMOUNT)
        branches = [
            RuleBranch(
                conditions=(
                    in_(
                        case.acquisition_works,
                        {
                            AcquisitionWorks.WORKS_FOR_ACQUISITION,
                            AcquisitionWorks.NO_WORKS,
                        },
                    ),
                ),
                inferred=inference(MinimumRepayment)(
                    case=case,
                    amount=RepaymentBrackets.monthly(
                        case.resources,
                        self.bracket_limit,
                        self.case.parts,
                        self.lower_rate,
                        self.upper_rate,
                    ),
                ),
            )
        ]
        if equivalence is not None:
            branches.append(
                RuleBranch(
                    conditions=(
                        case.acquisition_works
                        == AcquisitionWorks.WORKS_ON_ACQUIRED_HOME,
                    ),
                    inferred=inference(MinimumRepayment)(case=case, amount=equivalence),
                )
            )
        return RuleChain(
            conclusion=deduced_variable(MinimumRepayment), branches=branches
        ).query()


@dataclass
class OwnershipCoverageProvision(OwnershipProvision):
    """D832-11 and article 22: 0.95 less the resources over 22,111.33 € times the parts, rounded down to the hundredth, at most 0.95."""

    @classproperty
    def multiplier(cls) -> Money:
        """Article 22: 22,111.33 €."""
        return Money(cents=2211133)

    @classproperty
    def maximum(cls) -> Fraction:
        """0.95."""
        return Fraction(95, 100)

    def query(self) -> Query:
        case = variable(OwnershipAidCase, domain=[self.case])
        coverage = self.maximum - case.resources / (self.multiplier * self.case.parts)
        return an(
            entity(
                inference(OwnershipCoverage)(
                    case=case, fraction=CoverageRounding.rounded(coverage, self.maximum)
                )
            )
        )


@dataclass
class OwnershipInitialAidProvision(OwnershipProvision):
    """D832-10: the eligible repayment and flat charges less the minimum repayment, times the coverage; none below zero."""

    def query(self) -> Query:
        case = variable(OwnershipAidCase, domain=[self.case])
        repayment = self.sole(EligibleRepaymentProvision)
        charges = self.sole(OwnershipFlatChargesProvision)
        minimum = self.sole(MinimumRepaymentProvision)
        coverage = variable(
            OwnershipCoverage,
            domain=OwnershipCoverageProvision(case=self.case).conclusions,
        )
        aid = (repayment.amount + charges.amount - minimum.amount) * coverage.fraction
        return RuleChain(
            conclusion=deduced_variable(OwnershipInitialAid),
            branches=[
                RuleBranch(
                    conditions=(aid < Money.zero,),
                    inferred=inference(OwnershipInitialAid)(
                        case=case, amount=Money.zero
                    ),
                ),
                RuleBranch(
                    conditions=(),
                    inferred=inference(OwnershipInitialAid)(case=case, amount=aid),
                ),
            ],
        ).query()


@dataclass
class OwnershipNetExpenseAbatementProvision(TreatmentProvision):
    """
    D832-17, D832-18, articles 25 and 26: the aid less the shortfall of the net expense —
    the repayment, with the flat charges for a loan signed from June 30, 1999, less the
    aid — below the resources, at least 16.25 times the repayment, at a rate of the building.
    """

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`HallFlatReducedAidProvision`, the flat reduction of 5 € of article 20."""
        return HallFlatReducedAidProvision

    @classproperty
    def first_signature_with_charges(cls) -> datetime.date:
        """D832-17: June 30, 1999."""
        return datetime.date(1999, 6, 30)

    @classproperty
    def resources_multiple_of_repayment(cls) -> Fraction:
        """Article 26: 16.25."""
        return Fraction(1625, 100)

    @classproperty
    def last_signature_at_lower_rate(cls) -> datetime.date:
        """Article 25: October 1, 1998."""
        return datetime.date(1998, 10, 1)

    @classproperty
    def rates(cls) -> tuple[Fraction, Fraction, Fraction]:
        """Article 25: 2.26 % until then, 2.34 % after, 1.72 % for an old home its occupant improved."""
        return Fraction(226, 10000), Fraction(234, 10000), Fraction(172, 10000)

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        case: OwnershipAidCase = self.treatment.case
        aid = self.previous_amount(treatment)
        charges = self.case_conclusion(OwnershipFlatChargesProvision)
        repayment = treatment.case.monthly_repayment
        expense = (
            repayment + charges.amount - aid
            if case.loan_signature_date >= self.first_signature_with_charges
            else repayment - aid
        )
        floor = case.monthly_repayment * self.resources_multiple_of_repayment
        resources = (
            case.resources
            if case.situation_r822_11_13_17 or case.resources > floor
            else floor
        )
        before, after, improved = self.rates
        rate = (
            improved
            if isinstance(case.building_age, OldBuilding)
            and case.building_age.improved_by_occupant == ImprovedByOccupant.YES
            else (
                before
                if case.loan_signature_date <= self.last_signature_at_lower_rate
                else after
            )
        )
        abatement = NetExpense.shortfall(expense, resources * rate)
        return TreatmentChain.at_least_zero(treatment, aid - abatement)


@dataclass
class OwnershipContributionRoundedProvision(TreatmentProvision):
    """D832-10: the aid net of its contribution, rounded down to the euro, the contribution added back."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`OwnershipNetExpenseAbatementProvision`."""
        return OwnershipNetExpenseAbatementProvision

    def query(self) -> Query:
        return TreatmentChain.contribution_rounded(self)


@dataclass
class OwnershipMinimumAidProvision(TreatmentProvision):
    """D832-10 and article 21: no aid below 10 €."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`OwnershipContributionRoundedProvision`."""
        return OwnershipContributionRoundedProvision

    def query(self) -> Query:
        return TreatmentChain.at_least(self, HallMinimumAidProvision.least_aid)


# %% the housing allowance


class OwnershipAllowanceOutput(StrEnum):
    """The outputs of ``CalculAllocationLogementAccessionPropriété``."""

    ELIGIBLE_REPAYMENT = "mensualité_éligible"
    """The repayment within the ceiling."""

    MINIMUM_REPAYMENT = "mensualité_minimale"
    """The minimum repayment."""

    COVERAGE = "coefficient_prise_en_charge"
    """The coefficient of coverage."""

    INITIAL_AID = "aide_finale_formule_initiale"
    """The allowance the formula gives."""

    AID_TREATMENT = "traitement_aide_finale"
    """The treatment of an allowance, a function."""


@dataclass(eq=False)
class OwnershipAllowanceCase(OwnershipCase):
    """The inputs of the housing allowance of a home bought, Catala's ``CalculAllocationLogementAccessionPropriété``."""

    ownership_works: OwnershipWorks
    """The works of R842-5."""

    monthly_loan_charges: Money
    """The loan's monthly charges."""

    state_aided_social_scalable_housing: bool
    """Whether the home comes of operations of scalable social housing for State-aided ownership."""

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculAllocationLogementAccessionPropriété``."""
        return "CalculAllocationLogementAccessionPropriété"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "ressources_ménage_arrondies": "resources",
            "nombre_personnes_à_charge": "dependant_count",
            "situation_familiale_calcul_apl": "family_situation",
            "zone": "zone",
            "résidence": "residence",
            "date_courante": "assessment_date",
            "mensualité_principale": "monthly_repayment",
            "situation_r822_11_13_17": "situation_r822_11_13_17",
            "date_signature_prêt": "loan_signature_date",
            "type_travaux_logement": "ownership_works",
            "local_habité_première_fois_bénéficiaire": "first_occupation_by_beneficiary",
            "date_entrée_logement": "entry_date",
            "charges_mensuelles_prêt": "monthly_loan_charges",
            "copropriété": "co_ownership",
            "opérations_logement_évolutifs_sociaux_accession_propriété_aidée_État": "state_aided_social_scalable_housing",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`OwnershipAllowanceOutput`."""
        return OwnershipAllowanceOutput

    @cached_property
    def thresholded_resources(self) -> Money | None:
        """D842-12: the resources, raised to the threshold where they fall below it."""
        resources = self.sole_conclusion(ThresholdedResourcesProvision)
        return None if resources is None else resources.amount

    @cached_property
    def hall_coverage_case(self) -> HallAidCase:
        """
        D842-6: the personalised aid of a social residence of the 2° of D832-25, Catala's
        ``calcul_apl_logement_foyer``, the parts limited overseas until April 2023.
        """
        first, last = datetime.date(2019, 9, 1), datetime.date(2023, 4, 5)
        return HallAidCase(
            residence=self.residence,
            young_workers_hostel=False,
            hall_type=ResidenceHallType.SOCIAL_RESIDENCE,
            agreement_date=datetime.date(1970, 1, 1),
            resources=self.thresholded_resources,
            dependant_count=self.dependant_count,
            family_situation=self.family_situation,
            zone=self.zone,
            assessment_date=self.assessment_date,
            fee=Money.zero,
            stated_second_case=True,
            limits_dependant_parts=self.residence
            in HallAidProvision.overseas_departments
            and first <= self.assessment_date < last,
        )

    def treated_aid(self, aid: Money) -> Money | None:
        """:return: *aid* treated as ``traitement_aide_finale`` treats it; None where no rule does."""
        return AidTreatment(case=self, aid=aid).sole_amount(
            AllowanceOwnershipMinimumProvision
        )

    def output(self, variable: str) -> CatalaValue | Callable[[Money], Money | None]:
        match OwnershipAllowanceOutput(variable):
            case OwnershipAllowanceOutput.AID_TREATMENT:
                return self.treated_aid
            case OwnershipAllowanceOutput.COVERAGE:
                if self.thresholded_resources is None:
                    return None
                return self.hall_coverage_case.output(HallAidOutput.COVERAGE)
        provision = {
            OwnershipAllowanceOutput.ELIGIBLE_REPAYMENT: EligibleRepaymentProvision,
            OwnershipAllowanceOutput.MINIMUM_REPAYMENT: AllowanceMinimumRepaymentProvision,
            OwnershipAllowanceOutput.INITIAL_AID: AllowanceOwnershipInitialAidProvision,
        }[OwnershipAllowanceOutput(variable)]
        amount = self.sole_conclusion(provision)
        return None if amount is None else amount.amount


@dataclass(eq=False)
class ThresholdedResources(CaseAmount):
    """D842-12: the resources, raised to the threshold where they fall below it."""


@dataclass(eq=False)
class AllowanceRepaymentCeiling(CaseAmount):
    """D842-9 and article 33: the ceiling of the monthly repayment."""


@dataclass(eq=False)
class AllowanceOwnershipFlatCharges(CaseAmount):
    """D842-6, articles 34, 37 and 46: the flat charges."""


@dataclass(eq=False)
class AllowanceMinimumRepayment(CaseAmount):
    """D842-6: the minimum repayment, the minimum rent equivalence of the 2° of D832-25."""


@dataclass(eq=False)
class AllowanceOwnershipInitialAid(CaseAmount):
    """D842-6: the allowance the formula gives."""


@dataclass(eq=False)
class ThirdCaseOfD842_11(CaseCondition):
    """D842-11 3°: the minimum net expense is a share of the resources."""


@dataclass
class ThresholdedResourcesProvision(OwnershipProvision):
    """
    D842-12: for a loan signed from September 30, 1992 to September 30, 1994, or later
    with works that are none, for decency or enlarging, a threshold of 16.25 times the
    repayment; later with works listed in R321-15, 3,900 €. Resources at most the
    threshold are raised to it, rounded up to the hundred; not in R822-11, R822-13, R822-17.
    """

    @classproperty
    def first_period(cls) -> tuple[datetime.date, datetime.date]:
        """September 30, 1992, to September 30, 1994."""
        return datetime.date(1992, 9, 30), datetime.date(1994, 9, 30)

    @classproperty
    def repayment_multiple(cls) -> Fraction:
        """Article 39: 16.25."""
        return Fraction(1625, 100)

    @classproperty
    def listed_works_threshold(cls) -> Money:
        """Article 39: 3,900 €."""
        return Money.from_euros(3900)

    def query(self) -> Query:
        case = variable(OwnershipAllowanceCase, domain=[self.case])
        first, last = self.first_period
        ordinary_works = in_(
            case.ownership_works,
            {
                OwnershipWorks.NO_WORKS,
                OwnershipWorks.DECENCY,
                OwnershipWorks.ENLARGE_OR_MAKE_HABITABLE,
            },
        )
        branches = [
            RuleBranch(
                conditions=(case.situation_r822_11_13_17 == True,),
                inferred=inference(ThresholdedResources)(
                    case=case, amount=case.resources
                ),
            )
        ]
        for period, threshold in (
            (
                (
                    or_(
                        and_(
                            case.loan_signature_date >= first,
                            case.loan_signature_date <= last,
                        ),
                        and_(case.loan_signature_date > last, ordinary_works),
                    ),
                ),
                case.monthly_repayment * self.repayment_multiple,
            ),
            (
                (
                    case.loan_signature_date > last,
                    case.ownership_works == OwnershipWorks.LISTED_IN_R321_15,
                ),
                self.listed_works_threshold,
            ),
        ):
            branches += [
                RuleBranch(
                    conditions=(*period, case.resources <= threshold),
                    inferred=inference(ThresholdedResources)(
                        case=case, amount=ResourceThreshold.rounded_up(threshold)
                    ),
                ),
                RuleBranch(
                    conditions=period,
                    inferred=inference(ThresholdedResources)(
                        case=case, amount=case.resources
                    ),
                ),
            ]
        return RuleChain(
            conclusion=deduced_variable(ThresholdedResources), branches=branches
        ).query()


@dataclass(frozen=True)
class ResourceThreshold:
    """The threshold of D842-12 raised to the hundred, as Catala's example rounds it."""

    @staticmethod
    @symbolic_function
    def rounded_up(threshold: Money) -> Money:
        """:return: *threshold* and 49.99 €, at 1 %, rounded to the unit, times a hundred."""
        return (
            (threshold + Money(cents=4999)) * Fraction(1, 100)
        ).rounded_to_units() * 100


@dataclass(frozen=True)
class AllowanceCeilingLookup:
    """Finds the payment ceiling of article 33, as ``calcul_plafond_mensualité_d842_6`` does."""

    @staticmethod
    @symbolic_function
    def ceiling(
        case: OwnershipAllowanceCase, day: datetime.date, dependants: int
    ) -> Money | None:
        """:return: The ceiling of the row holding for *day*, for *dependants*; None where no row holds."""
        rows = [row for row in AllowancePaymentCeiling.rows() if row.covers(day)]
        if not rows:
            return None
        return ZoneTables.amount_for(
            rows[0].zones,
            case.zone,
            case.is_couple,
            dependants,
            FrancConversion.factor(rows[0].in_francs),
        )


@dataclass
class AllowanceRepaymentCeilingProvision(OwnershipProvision):
    """
    D842-9: the ceiling of the signature date, for the first occupant the higher of the
    signature's and the entry's. Article 37 takes 75 % of it in a co-owned building; article
    46 that of six dependants overseas until 2022.
    """

    @property
    def conclusions(self) -> list[AllowanceRepaymentCeiling]:
        """Extends :meth:`OwnershipProvision.conclusions`: none where no row of article 33 holds."""
        if self.ceiling_on(self.case.loan_signature_date) is None:
            return []
        return super().conclusions

    def ceiling_on(self, day: datetime.date) -> Money | None:
        """:return: The ceiling for *day*, with the reductions of articles 37 and 46."""
        case: OwnershipAllowanceCase = self.case
        overseas = case.overseas_scale
        dependants = case.dependant_count
        if (
            overseas is not None
            and overseas.dependants_counted_at_most is not None
            and case.residence in RentedAidProvision.overseas_territories
            and dependants >= overseas.dependants_counted_at_most
        ):
            dependants = overseas.dependants_counted_at_most
        ceiling = AllowanceCeilingLookup.ceiling(case, day, dependants)
        if ceiling is None:
            return None
        return (
            ceiling * RepaymentCeilingProvision.co_ownership_share
            if case.co_ownership
            else ceiling
        )

    def query(self) -> Query:
        case = variable(OwnershipAllowanceCase, domain=[self.case])
        signed = self.ceiling_on(self.case.loan_signature_date)
        entered = self.ceiling_on(self.case.entry_date)
        branches = []
        if entered is not None and entered > signed:
            branches.append(
                RuleBranch(
                    conditions=(case.first_occupation_by_beneficiary == True,),
                    inferred=inference(AllowanceRepaymentCeiling)(
                        case=case, amount=entered
                    ),
                )
            )
        branches.append(
            RuleBranch(
                conditions=(),
                inferred=inference(AllowanceRepaymentCeiling)(case=case, amount=signed),
            )
        )
        return RuleChain(
            conclusion=deduced_variable(AllowanceRepaymentCeiling), branches=branches
        ).query()


@dataclass
class AllowanceOwnershipFlatChargesProvision(OwnershipProvision):
    """
    Articles 34 and 37: the flat charges of article 9, halved for a person alone in a
    co-owned building, and more for each dependant; article 46 sets those of overseas,
    counting six dependants at most until 2022.
    """

    def query(self) -> Query:
        case = variable(OwnershipAllowanceCase, domain=[self.case])
        couple = case.family_situation == AidFamilySituation.COUPLE
        co_owned = case.co_ownership == True
        places = []
        overseas = self.case.overseas_scale
        if overseas is not None:
            places.append(
                (
                    (in_(case.residence, RentedAidProvision.overseas_territories),),
                    overseas,
                )
            )
        places.append(((), self.case.scale))
        branches = []
        for place, scale in places:
            dependants: int = self.case.dependant_count
            if isinstance(scale, OverseasScale) and scale.dependants_counted_at_most:
                dependants = min(dependants, scale.dependants_counted_at_most)
            per_dependants = scale.charges_per_dependant * dependants
            branches += [
                RuleBranch(
                    conditions=(*place, co_owned, not_(couple)),
                    inferred=inference(AllowanceOwnershipFlatCharges)(
                        case=case, amount=scale.shared_charges_single + per_dependants
                    ),
                ),
                RuleBranch(
                    conditions=place,
                    inferred=inference(AllowanceOwnershipFlatCharges)(
                        case=case, amount=scale.charges + per_dependants
                    ),
                ),
            ]
        return RuleChain(
            conclusion=deduced_variable(AllowanceOwnershipFlatCharges),
            branches=branches,
        ).query()


@dataclass
class AllowanceMinimumRepaymentProvision(OwnershipProvision):
    """D842-6: the minimum rent equivalence of the 2° of D832-25, on the parts of D832-11."""

    @cached_property
    def equivalence(self) -> Money | None:
        """The minimum rent equivalence; None where none is computed."""
        resources = self.case.thresholded_resources
        if resources is None:
            return None
        return MinimumRentEquivalenceCase(
            assessment_date=self.case.assessment_date,
            resources=resources,
            second_case_of_d832_25=True,
            parts=self.case.parts,
        ).output(MinimumRentEquivalenceOutput.AMOUNT)

    @property
    def conclusions(self) -> list[AllowanceMinimumRepayment]:
        """Extends :meth:`OwnershipProvision.conclusions`: none where no minimum rent equivalence is computed."""
        if self.equivalence is None:
            return []
        return super().conclusions

    def query(self) -> Query:
        case = variable(OwnershipAllowanceCase, domain=[self.case])
        return an(
            entity(
                inference(AllowanceMinimumRepayment)(case=case, amount=self.equivalence)
            )
        )


@dataclass
class AllowanceOwnershipInitialAidProvision(OwnershipProvision):
    """D842-6: the eligible repayment and flat charges less the minimum repayment, times the coverage."""

    def query(self) -> Query:
        case = variable(OwnershipAllowanceCase, domain=[self.case])
        repayment = self.sole(EligibleRepaymentProvision)
        charges = self.sole(AllowanceOwnershipFlatChargesProvision)
        minimum = self.sole(AllowanceMinimumRepaymentProvision)
        coverage = self.case.output(OwnershipAllowanceOutput.COVERAGE)
        return an(
            entity(
                inference(AllowanceOwnershipInitialAid)(
                    case=case,
                    amount=(repayment.amount + charges.amount - minimum.amount)
                    * coverage,
                )
            )
        )


@dataclass
class ThirdCaseOfD842_11Provision(OwnershipProvision):
    """
    D842-11 3°: works that are none, for decency or enlarging, a loan signed from July 1,
    1999; not overseas for operations of scalable social housing (D861-8 and D862-7).
    """

    @classproperty
    def first_signature(cls) -> datetime.date:
        """July 1, 1999."""
        return datetime.date(1999, 7, 1)

    @classproperty
    def first_day_of_exclusion(cls) -> datetime.date:
        """D861-8 and D862-7: from September 1, 2019."""
        return datetime.date(2019, 9, 1)

    def query(self) -> Query:
        case = variable(OwnershipAllowanceCase, domain=[self.case])
        return RuleChain(
            conclusion=deduced_variable(ThirdCaseOfD842_11),
            branches=[
                RuleBranch(
                    conditions=(
                        case.assessment_date >= self.first_day_of_exclusion,
                        in_(case.residence, RentedAidProvision.overseas_territories),
                        case.state_aided_social_scalable_housing == True,
                    ),
                    inferred=inference(ThirdCaseOfD842_11)(case=case, holds=False),
                ),
                RuleBranch(
                    conditions=(
                        in_(
                            case.ownership_works,
                            {
                                OwnershipWorks.NO_WORKS,
                                OwnershipWorks.DECENCY,
                                OwnershipWorks.ENLARGE_OR_MAKE_HABITABLE,
                            },
                        ),
                        case.loan_signature_date >= self.first_signature,
                    ),
                    inferred=inference(ThirdCaseOfD842_11)(case=case, holds=True),
                ),
                RuleBranch(
                    conditions=(),
                    inferred=inference(ThirdCaseOfD842_11)(case=case, holds=False),
                ),
            ],
        ).query()


@dataclass
class AllowanceOwnershipNetExpenseProvision(TreatmentProvision):
    """
    D842-11 and article 38: the allowance less the shortfall of the net expense — the
    loan's charges and the flat charges less the allowance — below 15 €, or 2.34 % of the
    resources in the 3° of D842-11.
    """

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`HallFlatReducedAidProvision`, the flat reduction of 5 € of article 35."""
        return HallFlatReducedAidProvision

    @classproperty
    def minimum_expense(cls) -> Money:
        """Article 38: 15 €."""
        return Money.from_euros(15)

    @classproperty
    def resources_share(cls) -> Fraction:
        """Article 38: 2.34 %."""
        return Fraction(234, 10000)

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        case: OwnershipAllowanceCase = self.treatment.case
        aid = self.previous_amount(treatment)
        charges = self.case_conclusion(AllowanceOwnershipFlatChargesProvision)
        third_case = case.sole_conclusion(ThirdCaseOfD842_11Provision).holds
        minimum = (
            case.thresholded_resources * self.resources_share
            if third_case
            else self.minimum_expense
        )
        abatement = NetExpense.strict_shortfall(
            treatment.case.monthly_loan_charges + charges.amount - aid, minimum
        )
        return TreatmentChain.at_least_zero(treatment, aid - abatement)


@dataclass
class AllowanceOwnershipContributionProvision(TreatmentProvision):
    """D842-6: the allowance net of its contribution, rounded down to the euro, the contribution added back."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`AllowanceOwnershipNetExpenseProvision`."""
        return AllowanceOwnershipNetExpenseProvision

    def query(self) -> Query:
        return TreatmentChain.contribution_rounded(self)


@dataclass
class AllowanceOwnershipSaintPierreProvision(TreatmentProvision):
    """Article 7 of décret n° 2021-1750: the allowance phased in in Saint-Pierre-et-Miquelon."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`AllowanceOwnershipContributionProvision`."""
        return AllowanceOwnershipContributionProvision

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        aid = self.previous_amount(treatment)
        return TreatmentChain.at_least_zero(
            treatment,
            SaintPierrePhaseIn.phased(
                aid, treatment.case.residence, treatment.case.assessment_date
            ),
        )


@dataclass
class AllowanceOwnershipMinimumProvision(TreatmentProvision):
    """D842-6 and article 36: no allowance below 10 €."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`AllowanceOwnershipSaintPierreProvision`."""
        return AllowanceOwnershipSaintPierreProvision

    def query(self) -> Query:
        return TreatmentChain.at_least(self, HallMinimumAidProvision.least_aid)


# %% test files


class OwnershipTestFile(ScopeTestFile, StrEnum):
    """The test files of the aids of homes bought of Catala's ``aides_logement`` example."""

    PERSONALISED_AID = "tests_calcul_apl_accession_propriete.catala_fr"
    """Four households asking the personalised aid."""

    HOUSING_ALLOWANCE = "tests_calcul_al_accession_propriete.catala_fr"
    """Two households asking the allowance, overseas."""

    @property
    def directory(self) -> Path:
        """:file:`aides_logement/tests`."""
        return CatalaDirectory.ROOT / "aides_logement" / "tests"

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """The personalised aid and the allowance of homes bought."""
        return [OwnershipAidCase, OwnershipAllowanceCase]
