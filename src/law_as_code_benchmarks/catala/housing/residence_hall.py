"""
The personal housing aids of a residence hall (*logement-foyer*): the minimum rent
equivalence of D832-26 (Catala's ``CalculÉquivalenceLoyerMinimale``), the parts of
D832-25 (``CalculNombrePartLogementFoyer``), the personalised aid of D832-24 to D832-27
(``CalculAidePersonnaliséeLogementFoyer``) and the allowance of D842-15 to D842-17.
"""

from __future__ import annotations

import datetime
from abc import ABC
from dataclasses import dataclass
from enum import Enum, StrEnum
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
    or_,
    variable,
)
from krrood.entity_query_language.predicate import symbolic_function
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from typing_extensions import Callable

from law_as_code_benchmarks.catala.domain import DatedValue, Territory
from law_as_code_benchmarks.catala.housing.domain import (
    HousingZone,
    ResidenceHallRentCategory,
    ResidenceHallType,
)
from law_as_code_benchmarks.catala.housing.household_tables import (
    ResidenceHallCeilings,
    ResidenceHallRentEquivalence,
    ZoneTables,
)
from law_as_code_benchmarks.catala.housing.rented import (
    AidFamilySituation,
    AidTreatment,
    Contribution,
    MoneyRounding,
    RentedAidProvision,
    SocialContributionProvision,
    TreatedAid,
    TreatmentProvision,
)
from law_as_code_benchmarks.catala.housing.rented_scales import (
    OverseasScale,
    OverseasScales,
    RentedHomeScale,
    RentedHomeScales,
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

# %% the minimum rent equivalence


@dataclass(frozen=True)
class IncomeBracket:
    """A bracket of the household's resources of D832-26, and the rate it is taken at."""

    lower: Money
    """Where the bracket starts."""

    upper: Money | None
    """Where it ends; None for the last."""

    rate: Fraction
    """The rate."""


class IncomeBracketScales(Enum):
    """The brackets of article 31, in force since October 2019."""

    ORDINARY = (
        IncomeBracket(Money(cents=0), Money(cents=194810), Fraction(4, 100)),
        IncomeBracket(Money(cents=194810), Money(cents=267871), Fraction(104, 1000)),
        IncomeBracket(Money(cents=267871), Money(cents=389618), Fraction(216, 1000)),
        IncomeBracket(Money(cents=389618), Money(cents=535744), Fraction(264, 1000)),
        IncomeBracket(Money(cents=535744), Money(cents=633129), Fraction(32, 100)),
        IncomeBracket(Money(cents=633129), None, Fraction(48, 100)),
    )
    """The brackets of an ordinary hall."""

    SECOND_CASE_OF_D832_25 = (
        IncomeBracket(Money(cents=0), Money(cents=142303), Fraction(0)),
        IncomeBracket(Money(cents=142303), Money(cents=204761), Fraction(24, 1000)),
        IncomeBracket(Money(cents=204761), Money(cents=262985), Fraction(208, 1000)),
        IncomeBracket(Money(cents=262985), Money(cents=409505), Fraction(232, 1000)),
        IncomeBracket(Money(cents=409505), None, Fraction(328, 1000)),
    )
    """The brackets of a hall of the 2° of D832-25, and of the allowances."""


@dataclass(frozen=True)
class BracketedAmount:
    """The resources taken bracket by bracket, the brackets multiplied by the parts, as D832-26 takes them."""

    @staticmethod
    @symbolic_function
    def yearly(
        brackets: tuple[IncomeBracket, ...], resources: Money, parts: Fraction
    ) -> Fraction:
        """:return: The sum over *brackets* of the resources within each, at its rate."""
        income = Fraction(resources.cents, 100)
        total = Fraction(0)
        for bracket in brackets:
            lower = Fraction(bracket.lower.cents, 100) * parts
            if income <= lower:
                continue
            if bracket.upper is None:
                total += (income - lower) * bracket.rate
                continue
            upper = Fraction(bracket.upper.cents, 100) * parts
            total += (min(income, upper) - lower) * bracket.rate
        return total

    @staticmethod
    @symbolic_function
    def monthly(yearly: Fraction, flat: Money, flat_share: Fraction) -> Money:
        """:return: *yearly* and *flat* times *flat_share*, over twelve months, as money."""
        return Money.from_exact_units(
            (yearly + Fraction(flat.cents, 100) * flat_share) / 12
        )


@dataclass(eq=False)
class MinimumRentEquivalence(CaseAmount):
    """D832-26: the minimum rent equivalence."""


class MinimumRentEquivalenceOutput(StrEnum):
    """The output of ``CalculÉquivalenceLoyerMinimale``."""

    AMOUNT = "montant"
    """The minimum rent equivalence."""


@dataclass(eq=False)
class MinimumRentEquivalenceCase(ScopeCase):
    """The inputs of the minimum rent equivalence, Catala's ``CalculÉquivalenceLoyerMinimale``."""

    assessment_date: datetime.date
    """The day the equivalence is computed for."""

    resources: Money
    """The household's resources, rounded."""

    second_case_of_d832_25: bool
    """Whether the hall is of the 2° of D832-25, or the allowances are computed."""

    parts: Fraction
    """The household's parts."""

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculÉquivalenceLoyerMinimale``."""
        return "CalculÉquivalenceLoyerMinimale"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "date_courante": "assessment_date",
            "ressources_ménage_arrondies": "resources",
            "condition_2_du_832_25": "second_case_of_d832_25",
            "n_nombre_parts_d832_25": "parts",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`MinimumRentEquivalenceOutput`."""
        return MinimumRentEquivalenceOutput

    def output(self, variable: str) -> CatalaValue:
        amount = self.sole_conclusion(MinimumRentEquivalenceProvision)
        return None if amount is None else amount.amount


@dataclass
class MinimumRentEquivalenceProvision(ScopeProvision):
    """
    D832-26 and article 31: the resources taken bracket by bracket, and a flat amount,
    over twelve months; the brackets and the flat amount of an ordinary hall multiplied
    by the parts, those of the 2° of D832-25 the brackets only.
    """

    @classproperty
    def first_day(cls) -> datetime.date:
        """Article 31 holds after October 1, 2019."""
        return datetime.date(2019, 10, 1)

    @classproperty
    def ordinary_flat_amount(cls) -> Money:
        """Article 31: 45.57 €."""
        return Money(cents=4557)

    @classproperty
    def second_case_flat_amount(cls) -> Money:
        """Article 31: 76.32 €."""
        return Money(cents=7632)

    def query(self) -> Query:
        case = variable(MinimumRentEquivalenceCase, domain=[self.case])
        return RuleChain(
            conclusion=deduced_variable(MinimumRentEquivalence),
            branches=[
                RuleBranch(
                    conditions=(
                        case.assessment_date > self.first_day,
                        case.second_case_of_d832_25 == True,
                    ),
                    inferred=self.inferred(
                        case,
                        IncomeBracketScales.SECOND_CASE_OF_D832_25.value,
                        self.second_case_flat_amount,
                        Fraction(1),
                    ),
                ),
                RuleBranch(
                    conditions=(case.assessment_date > self.first_day,),
                    inferred=self.inferred(
                        case,
                        IncomeBracketScales.ORDINARY.value,
                        self.ordinary_flat_amount,
                        case.parts,
                    ),
                ),
            ],
        ).query()

    @staticmethod
    def inferred(
        case: MinimumRentEquivalenceCase,
        brackets: tuple[IncomeBracket, ...],
        flat: Money,
        flat_share: Fraction,
    ) -> MinimumRentEquivalence:
        """:return: The inference of the equivalence over *brackets* and *flat*, over a variable of the case."""
        return inference(MinimumRentEquivalence)(
            case=case,
            amount=BracketedAmount.monthly(
                BracketedAmount.yearly(brackets, case.resources, case.parts),
                flat,
                flat_share,
            ),
        )


# %% the parts


@dataclass(frozen=True)
class PartsTable:
    """The parts of a person alone, a couple, and one to four dependants, and those added beyond four."""

    single: Fraction
    """Of a person alone."""

    couple: Fraction
    """Of a couple."""

    by_dependants: tuple[Fraction, ...]
    """Of one to four dependants."""

    each_further_dependant: Fraction
    """Added for each dependant beyond four."""

    @staticmethod
    @symbolic_function
    def base_parts(table: PartsTable, couple: bool, dependants: int) -> Fraction:
        """:return: The parts of *table* before any addition beyond four dependants."""
        if dependants == 0:
            return table.couple if couple else table.single
        return table.by_dependants[min(dependants, len(table.by_dependants)) - 1]


class PartsTables(Enum):
    """The parts of D832-11 and D832-25."""

    ORDINARY = PartsTable(
        single=Fraction(14, 10),
        couple=Fraction(18, 10),
        by_dependants=(
            Fraction(25, 10),
            Fraction(3),
            Fraction(37, 10),
            Fraction(43, 10),
        ),
        each_further_dependant=Fraction(1, 2),
    )
    """D832-11 and the 1° of D832-25."""

    SECOND_CASE_OF_D832_25 = PartsTable(
        single=Fraction(12, 10),
        couple=Fraction(15, 10),
        by_dependants=(
            Fraction(25, 10),
            Fraction(3),
            Fraction(37, 10),
            Fraction(43, 10),
        ),
        each_further_dependant=Fraction(1, 2),
    )
    """The 2° of D832-25."""


@dataclass(eq=False)
class HallParts(CaseFraction):
    """D832-25: the household's parts."""


class HallPartsOutput(StrEnum):
    """The output of ``CalculNombrePartLogementFoyer``."""

    PARTS = "n_nombre_parts_d832_25"
    """The parts."""


@dataclass(eq=False)
class HallPartsCase(ScopeCase):
    """The inputs of the parts of D832-25, Catala's ``CalculNombrePartLogementFoyer``."""

    assessment_date: datetime.date
    """The day the parts are computed for."""

    second_case_of_d832_25: bool
    """Whether the hall is of the 2° of D832-25."""

    dependant_count: int
    """How many persons are in the household's charge."""

    family_situation: AidFamilySituation
    """Whether the household is a person alone or a couple."""

    limits_dependant_parts: bool = False
    """D861-8: whether the parts added for dependants are limited, as overseas until April 2023."""

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculNombrePartLogementFoyer``."""
        return "CalculNombrePartLogementFoyer"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "date_courante": "assessment_date",
            "condition_2_du_832_25": "second_case_of_d832_25",
            "nombre_personnes_à_charge": "dependant_count",
            "situation_familiale_calcul_apl": "family_situation",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`HallPartsOutput`."""
        return HallPartsOutput

    def output(self, variable: str) -> CatalaValue:
        parts = self.sole_conclusion(HallPartsProvision)
        return None if parts is None else parts.fraction


@dataclass
class HallPartsProvision(ScopeProvision):
    """
    D832-25: the parts of the household, those of the 2° for its halls, and half a part
    for each dependant beyond four. D861-8 limits the addition to one part beyond six
    dependants overseas from September 2019 to April 4, 2023.
    """

    @classproperty
    def limitation_period(cls) -> tuple[datetime.date, datetime.date]:
        """D861-8: from September 1, 2019, until April 5, 2023, excluded."""
        return datetime.date(2019, 9, 1), datetime.date(2023, 4, 5)

    @classproperty
    def limited_addition(cls) -> Fraction:
        """D861-8: one part."""
        return Fraction(1)

    @classproperty
    def dependants_counted_before_limit(cls) -> int:
        """D861-8: six dependants."""
        return 6

    def query(self) -> Query:
        case = variable(HallPartsCase, domain=[self.case])
        couple = case.family_situation == AidFamilySituation.COUPLE
        first, last = self.limitation_period
        dependants: int = self.case.dependant_count
        addition = PartsTables.ORDINARY.value.each_further_dependant * max(
            dependants - len(PartsTables.ORDINARY.value.by_dependants), 0
        )
        branches = []
        for table_condition, table in (
            (
                (case.second_case_of_d832_25 == True,),
                PartsTables.SECOND_CASE_OF_D832_25,
            ),
            ((), PartsTables.ORDINARY),
        ):
            base = PartsTable.base_parts(table.value, couple, case.dependant_count)
            branches += [
                RuleBranch(
                    conditions=(
                        *table_condition,
                        case.limits_dependant_parts == True,
                        case.dependant_count > self.dependants_counted_before_limit,
                        case.assessment_date >= first,
                        case.assessment_date < last,
                    ),
                    inferred=inference(HallParts)(
                        case=case, fraction=base + self.limited_addition
                    ),
                ),
                RuleBranch(
                    conditions=table_condition,
                    inferred=inference(HallParts)(case=case, fraction=base + addition),
                ),
            ]
        return RuleChain(
            conclusion=deduced_variable(HallParts), branches=branches
        ).query()


# %% the personalised aid of a residence hall


class HallAidOutput(StrEnum):
    """The outputs of ``CalculAidePersonnaliséeLogementFoyer``."""

    MULTIPLIER = "coefficient_multiplicateur_d832_25"
    """The multiplier of D832-25."""

    COEFFICIENT_R = "coefficient_r_d832_25"
    """The coefficient R of D832-25."""

    PARTS = "n_nombre_parts_d832_25"
    """The parts."""

    ELIGIBLE_RENT_EQUIVALENCE = "équivalence_loyer_éligible"
    """The fee within the ceiling."""

    RENT_EQUIVALENCE_CEILING = "plafond_équivalence_loyer_éligible"
    """The ceiling of the rent equivalence."""

    MINIMUM_RENT_EQUIVALENCE = "équivalence_loyer_minimale"
    """The minimum rent equivalence."""

    COVERAGE = "coefficient_prise_en_charge_d832_25"
    """The coefficient of coverage."""

    INITIAL_AID = "aide_finale_formule_initiale"
    """The aid the formula gives."""

    AID_TREATMENT = "traitement_aide_finale"
    """The treatment of an aid, a function."""


@dataclass(eq=False)
class HallAidCase(ScopeCase):
    """The inputs of the personalised aid of a residence hall, Catala's ``CalculAidePersonnaliséeLogementFoyer``."""

    residence: Territory
    """Where the household lives."""

    young_workers_hostel: bool
    """Whether the hall is a hostel for young workers."""

    hall_type: ResidenceHallType
    """The kind of hall."""

    agreement_date: datetime.date
    """The day of the hall's agreement."""

    resources: Money
    """The household's resources, rounded."""

    dependant_count: int
    """How many persons are in the household's charge."""

    family_situation: AidFamilySituation
    """Whether the household is a person alone or a couple."""

    zone: HousingZone
    """The zone the hall is in."""

    assessment_date: datetime.date
    """The day the aid is computed for."""

    fee: Money
    """The monthly fee (*redevance*)."""

    stated_second_case: bool | None = None
    """Whether a calling scope states the hall of the 2° of D832-25; None where D832-25 decides."""

    limits_dependant_parts: bool = False
    """D861-8: whether a calling scope limits the parts added for dependants."""

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculAidePersonnaliséeLogementFoyer``."""
        return "CalculAidePersonnaliséeLogementFoyer"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "résidence": "residence",
            "logement_foyer_jeunes_travailleurs": "young_workers_hostel",
            "type_logement_foyer": "hall_type",
            "date_conventionnement": "agreement_date",
            "ressources_ménage_arrondies": "resources",
            "nombre_personnes_à_charge": "dependant_count",
            "situation_familiale_calcul_apl": "family_situation",
            "date_courante": "assessment_date",
            "redevance": "fee",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`HallAidOutput`."""
        return HallAidOutput

    @cached_property
    def second_case(self) -> bool:
        """Whether the hall is of the 2° of D832-25, as :class:`SecondCaseProvision` concludes."""
        return self.sole_conclusion(SecondCaseProvision).holds

    @cached_property
    def parts_case(self) -> HallPartsCase:
        """The parts of the household, Catala's subscope ``calcul_nombre_parts``."""
        return HallPartsCase(
            assessment_date=self.assessment_date,
            second_case_of_d832_25=self.second_case,
            dependant_count=self.dependant_count,
            family_situation=self.family_situation,
            limits_dependant_parts=self.limits_dependant_parts,
        )

    @cached_property
    def parts(self) -> Fraction:
        """The parts of the household."""
        return self.parts_case.output(HallPartsOutput.PARTS)

    @cached_property
    def minimum_rent_equivalence_case(self) -> MinimumRentEquivalenceCase:
        """The minimum rent equivalence, Catala's subscope ``calcul_équivalence_loyer_minimale``."""
        return MinimumRentEquivalenceCase(
            assessment_date=self.assessment_date,
            resources=self.resources,
            second_case_of_d832_25=self.second_case,
            parts=self.parts,
        )

    def treated_aid(self, aid: Money) -> Money | None:
        """:return: *aid* treated as ``traitement_aide_finale`` treats it; None where no rule does."""
        return AidTreatment(case=self, aid=aid).sole_amount(HallMinimumAidProvision)

    def output(self, variable: str) -> CatalaValue | Callable[[Money], Money | None]:
        match HallAidOutput(variable):
            case HallAidOutput.PARTS:
                return self.parts
            case HallAidOutput.MINIMUM_RENT_EQUIVALENCE:
                return self.minimum_rent_equivalence_case.output(
                    MinimumRentEquivalenceOutput.AMOUNT
                )
            case HallAidOutput.AID_TREATMENT:
                return self.treated_aid
            case HallAidOutput.COVERAGE:
                coverage = self.sole_conclusion(HallCoverageProvision)
                return None if coverage is None else coverage.fraction
        provision = {
            HallAidOutput.MULTIPLIER: HallMultiplierProvision,
            HallAidOutput.COEFFICIENT_R: CoefficientRProvision,
            HallAidOutput.ELIGIBLE_RENT_EQUIVALENCE: EligibleRentEquivalenceProvision,
            HallAidOutput.RENT_EQUIVALENCE_CEILING: RentEquivalenceCeilingProvision,
            HallAidOutput.INITIAL_AID: HallInitialAidProvision,
        }[HallAidOutput(variable)]
        amount = self.sole_conclusion(provision)
        return None if amount is None else amount.amount


@dataclass(eq=False)
class SecondCase(CaseCondition):
    """D832-25: the hall is of the 2°."""


@dataclass(eq=False)
class HallMultiplier(CaseAmount):
    """Article 30: the multiplier of D832-25."""


@dataclass(eq=False)
class CoefficientR(CaseAmount):
    """Article 30: the coefficient R of D832-25."""


@dataclass(eq=False)
class RentEquivalenceCeiling(CaseAmount):
    """Article 27: the ceiling of the rent equivalence."""


@dataclass(eq=False)
class EligibleRentEquivalence(CaseAmount):
    """D832-24: the fee within the ceiling."""


@dataclass(eq=False)
class HallCoverage(CaseFraction):
    """D832-25: the coefficient of coverage, rounded down to the hundredth, at most its maximum."""


@dataclass(eq=False)
class HallInitialAid(CaseAmount):
    """D832-24: the aid the formula gives."""


@dataclass
class HallAidProvision(ScopeProvision, ABC):
    """A provision of the personalised aid of a residence hall."""

    @classproperty
    def overseas_departments(cls) -> frozenset[Territory]:
        """The overseas departments of D861-21."""
        return frozenset(
            {
                Territory.GUADELOUPE,
                Territory.FRENCH_GUIANA,
                Territory.MARTINIQUE,
                Territory.REUNION,
                Territory.MAYOTTE,
            }
        )

    def sole(self, provision: type[ScopeProvision]) -> CaseAmount:
        """:return: A variable over the one conclusion *provision* draws about the case."""
        return variable(CaseAmount, domain=provision(case=self.case).conclusions)


@dataclass
class SecondCaseProvision(HallAidProvision):
    """
    D832-25 2°: a hostel for young workers agreed from September 30, 1990, or a social
    residence agreed from December 31, 1994; none overseas from April 5, 2023 (D861-21).
    A calling scope may state it.
    """

    @classproperty
    def first_hostel_agreement(cls) -> datetime.date:
        """September 30, 1990."""
        return datetime.date(1990, 9, 30)

    @classproperty
    def first_social_residence_agreement(cls) -> datetime.date:
        """December 31, 1994."""
        return datetime.date(1994, 12, 31)

    @classproperty
    def first_day_of_d861_21(cls) -> datetime.date:
        """April 5, 2023."""
        return datetime.date(2023, 4, 5)

    def query(self) -> Query:
        case = variable(HallAidCase, domain=[self.case])
        stated = self.case.stated_second_case
        branches = []
        if stated is not None:
            branches.append(
                RuleBranch(
                    conditions=(case.stated_second_case == stated,),
                    inferred=inference(SecondCase)(case=case, holds=stated),
                )
            )
        branches += [
            RuleBranch(
                conditions=(
                    case.assessment_date >= self.first_day_of_d861_21,
                    in_(case.residence, self.overseas_departments),
                ),
                inferred=inference(SecondCase)(case=case, holds=False),
            ),
            RuleBranch(
                conditions=(
                    or_(
                        and_(
                            case.young_workers_hostel == True,
                            case.agreement_date >= self.first_hostel_agreement,
                        ),
                        and_(
                            case.hall_type == ResidenceHallType.SOCIAL_RESIDENCE,
                            case.agreement_date
                            >= self.first_social_residence_agreement,
                        ),
                    ),
                ),
                inferred=inference(SecondCase)(case=case, holds=True),
            ),
            RuleBranch(
                conditions=(), inferred=inference(SecondCase)(case=case, holds=False)
            ),
        ]
        return RuleChain(
            conclusion=deduced_variable(SecondCase), branches=branches
        ).query()


@dataclass
class HallMultiplierProvision(HallAidProvision):
    """Article 30: 21,420.91 € for a hall of the 2° of D832-25, 13,393.40 € otherwise."""

    @classproperty
    def second_case_multiplier(cls) -> Money:
        """21,420.91 €."""
        return Money(cents=2142091)

    @classproperty
    def ordinary_multiplier(cls) -> Money:
        """13,393.40 €."""
        return Money(cents=1339340)

    def query(self) -> Query:
        case = variable(HallAidCase, domain=[self.case])
        multiplier = (
            self.second_case_multiplier
            if self.case.second_case
            else self.ordinary_multiplier
        )
        return an(entity(inference(HallMultiplier)(case=case, amount=multiplier)))


@dataclass
class CoefficientRProvision(HallAidProvision):
    """Article 30: the coefficient R, 1,217.26 €."""

    @classproperty
    def coefficient_r(cls) -> Money:
        """1,217.26 €."""
        return Money(cents=121726)

    def query(self) -> Query:
        case = variable(HallAidCase, domain=[self.case])
        return an(entity(inference(CoefficientR)(case=case, amount=self.coefficient_r)))


@dataclass
class RentEquivalenceCeilingProvision(HallAidProvision):
    """Article 27: the ceiling of the rent equivalence in force, by household and zone."""

    def query(self) -> Query:
        case = variable(HallAidCase, domain=[self.case])
        ceilings = variable(
            ResidenceHallCeilings, domain=list(ResidenceHallCeilings.versions())
        )
        return an(
            entity(
                inference(RentEquivalenceCeiling)(
                    case=case,
                    amount=ZoneTables.amount_for(
                        ceilings.zones,
                        case.zone,
                        case.family_situation == AidFamilySituation.COUPLE,
                        case.dependant_count,
                        Fraction(1),
                    ),
                )
            ).where(DatedValue.is_in_force(ceilings, case.assessment_date))
        )


@dataclass
class EligibleRentEquivalenceProvision(HallAidProvision):
    """D832-24: the fee, the ceiling where the fee reaches it."""

    def query(self) -> Query:
        case = variable(HallAidCase, domain=[self.case])
        ceiling = self.sole(RentEquivalenceCeilingProvision)
        return RuleChain(
            conclusion=deduced_variable(EligibleRentEquivalence),
            branches=[
                RuleBranch(
                    conditions=(case.fee >= ceiling.amount,),
                    inferred=inference(EligibleRentEquivalence)(
                        case=case, amount=ceiling.amount
                    ),
                ),
                RuleBranch(
                    conditions=(),
                    inferred=inference(EligibleRentEquivalence)(
                        case=case, amount=case.fee
                    ),
                ),
            ],
        ).query()


@dataclass(frozen=True)
class CoverageRounding:
    """Rounds a coefficient of coverage as D832-11 and D832-25 do."""

    @staticmethod
    @symbolic_function
    def rounded(coverage: Fraction, maximum: Fraction) -> Fraction:
        """:return: *coverage* rounded down to the hundredth, as Catala rounds it, *maximum* at most."""
        shifted = (coverage - Fraction(5, 1000)) * 100
        whole = (abs(shifted) + Fraction(1, 2)).__floor__()
        rounded = Fraction(whole if shifted >= 0 else -whole, 100)
        return min(rounded, maximum)


@dataclass
class HallCoverageProvision(HallAidProvision):
    """
    D832-25: 0.95 less the resources beyond R times the parts, over the multiplier times
    the parts; for a hall of the 2°, 0.90 less the resources over the multiplier times the
    parts. Rounded down to the hundredth, at most 0.95 or 0.90.
    """

    @classproperty
    def ordinary_maximum(cls) -> Fraction:
        """0.95."""
        return Fraction(95, 100)

    @classproperty
    def second_case_maximum(cls) -> Fraction:
        """0.90."""
        return Fraction(90, 100)

    def query(self) -> Query:
        case = variable(HallAidCase, domain=[self.case])
        multiplier = self.sole(HallMultiplierProvision)
        coefficient_r = self.sole(CoefficientRProvision)
        parts = self.case.parts
        if self.case.second_case:
            coverage = self.second_case_maximum - (
                case.resources / (multiplier.amount * parts)
            )
            maximum = self.second_case_maximum
        else:
            coverage = self.ordinary_maximum - (
                HallCoverageProvision.net_resources(
                    case.resources, coefficient_r.amount * parts
                )
                / (multiplier.amount * parts)
            )
            maximum = self.ordinary_maximum
        return an(
            entity(
                inference(HallCoverage)(
                    case=case, fraction=CoverageRounding.rounded(coverage, maximum)
                )
            )
        )

    @staticmethod
    @symbolic_function
    def net_resources(resources: Money, deduction: Money) -> Money:
        """:return: *resources* less *deduction*, none below zero."""
        net = resources - deduction
        return net if net >= Money.zero else Money.zero


@dataclass
class HallInitialAidProvision(HallAidProvision):
    """D832-24: the eligible rent equivalence less the minimum one, times the coverage; none below zero."""

    def query(self) -> Query:
        case = variable(HallAidCase, domain=[self.case])
        eligible = self.sole(EligibleRentEquivalenceProvision)
        coverage = variable(
            HallCoverage, domain=HallCoverageProvision(case=self.case).conclusions
        )
        minimum = self.case.output(HallAidOutput.MINIMUM_RENT_EQUIVALENCE)
        aid = (eligible.amount - minimum) * coverage.fraction
        return RuleChain(
            conclusion=deduced_variable(HallInitialAid),
            branches=[
                RuleBranch(
                    conditions=(aid < Money.zero,),
                    inferred=inference(HallInitialAid)(case=case, amount=Money.zero),
                ),
                RuleBranch(
                    conditions=(),
                    inferred=inference(HallInitialAid)(case=case, amount=aid),
                ),
            ],
        ).query()


# %% the treatment of the personalised aid of a residence hall


@dataclass(eq=False)
class HallTreatedAid(TreatedAid):
    """The personalised aid of a residence hall after a step of its treatment."""


@dataclass
class HallFlatReducedAidProvision(TreatmentProvision):
    """D832-24 and article 28: the aid less 5 €, none below zero."""

    @classproperty
    def flat_reduction(cls) -> Money:
        """Article 28: 5 €."""
        return Money.from_euros(5)

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        reduced = self.previous_amount(treatment) - self.flat_reduction
        return TreatmentChain.at_least_zero(treatment, reduced)


@dataclass
class HallNetExpenseAbatementProvision(TreatmentProvision):
    """
    D832-27 and article 32: the aid less the shortfall of the net expense, the eligible
    rent equivalence less the aid, below 26.68 €, or 15 € for a hall of the 2°.
    """

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`HallFlatReducedAidProvision`."""
        return HallFlatReducedAidProvision

    @classproperty
    def ordinary_minimum_expense(cls) -> Money:
        """26.68 €."""
        return Money(cents=2668)

    @classproperty
    def second_case_minimum_expense(cls) -> Money:
        """15 €."""
        return Money.from_euros(15)

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        case: HallAidCase = self.treatment.case
        aid = self.previous_amount(treatment)
        eligible = self.case_conclusion(EligibleRentEquivalenceProvision)
        minimum_expense = (
            self.second_case_minimum_expense
            if case.second_case
            else self.ordinary_minimum_expense
        )
        abatement = NetExpense.shortfall(eligible.amount - aid, minimum_expense)
        return TreatmentChain.at_least_zero(treatment, aid - abatement)


@dataclass(frozen=True)
class NetExpense:
    """The shortfall of a net expense below its minimum, which D832-17, D832-27, D842-11 and D842-17 take off the aid."""

    @staticmethod
    @symbolic_function
    def shortfall(expense: Money, minimum: Money) -> Money:
        """:return: How much *expense* falls short of *minimum*; nothing where it reaches it."""
        if expense <= minimum:
            return minimum - expense
        return Money.zero

    @staticmethod
    @symbolic_function
    def strict_shortfall(expense: Money, minimum: Money) -> Money:
        """:return: How much *expense* falls short of *minimum*, counted only strictly below it."""
        if expense < minimum:
            return minimum - expense
        return Money.zero


@dataclass(frozen=True)
class TreatmentChain:
    """The rule trees the steps of a treatment share."""

    @staticmethod
    def at_least_zero(treatment: AidTreatment, amount: Money) -> Query:
        """:return: The rule tree concluding *amount*, or zero where it is below zero."""
        return RuleChain(
            conclusion=deduced_variable(HallTreatedAid),
            branches=[
                RuleBranch(
                    conditions=(amount < Money.zero,),
                    inferred=inference(HallTreatedAid)(
                        treatment=treatment, amount=Money.zero
                    ),
                ),
                RuleBranch(
                    conditions=(),
                    inferred=inference(HallTreatedAid)(
                        treatment=treatment, amount=amount
                    ),
                ),
            ],
        ).query()

    @staticmethod
    def contribution_rounded(provision: TreatmentProvision) -> Query:
        """:return: The rule tree of the aid net of its contribution rounded down to the euro, the contribution added back."""
        treatment = variable(AidTreatment, domain=[provision.treatment])
        aid = provision.previous_amount(treatment)
        social = provision.case_conclusion(SocialContributionProvision)
        contribution = Contribution.amount(aid, social)
        net = MoneyRounding.rounded_to_units(aid - contribution - Money(cents=50))
        return TreatmentChain.at_least_zero(treatment, net + contribution)

    @staticmethod
    def at_least(provision: TreatmentProvision, least: Money) -> Query:
        """:return: The rule tree of the aid, none below *least*."""
        treatment = variable(AidTreatment, domain=[provision.treatment])
        aid = provision.previous_amount(treatment)
        return RuleChain(
            conclusion=deduced_variable(HallTreatedAid),
            branches=[
                RuleBranch(
                    conditions=(aid < least,),
                    inferred=inference(HallTreatedAid)(
                        treatment=treatment, amount=Money.zero
                    ),
                ),
                RuleBranch(
                    conditions=(),
                    inferred=inference(HallTreatedAid)(treatment=treatment, amount=aid),
                ),
            ],
        ).query()


@dataclass
class HallContributionRoundedAidProvision(TreatmentProvision):
    """D832-24: the aid net of its contribution, rounded down to the euro, the contribution added back."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`HallNetExpenseAbatementProvision`."""
        return HallNetExpenseAbatementProvision

    def query(self) -> Query:
        return TreatmentChain.contribution_rounded(self)


@dataclass
class HallMinimumAidProvision(TreatmentProvision):
    """D832-24 and article 29: no aid below 10 €."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`HallContributionRoundedAidProvision`."""
        return HallContributionRoundedAidProvision

    @classproperty
    def least_aid(cls) -> Money:
        """Article 29: 10 €."""
        return Money.from_euros(10)

    def query(self) -> Query:
        return TreatmentChain.at_least(self, self.least_aid)


# %% the allowance of a residence hall


class HallAllowanceOutput(StrEnum):
    """The outputs of ``CalculAllocationLogementFoyer``."""

    COVERAGE = "coefficient_prise_en_charge"
    """The coefficient of coverage."""

    RENT_EQUIVALENCE = "équivalence_loyer"
    """The rent equivalence."""

    FLAT_CHARGES = "montant_forfaitaire_charges"
    """The flat charges."""

    MINIMUM_RENT = "loyer_minimal"
    """The minimum rent."""

    INITIAL_AID = "aide_finale_formule_initiale"
    """The aid the formula gives."""

    AID_TREATMENT = "traitement_aide_finale"
    """The treatment of an aid, a function."""


@dataclass(eq=False)
class HallAllowanceCase(HallAidCase):
    """The inputs of the housing allowance of a residence hall, Catala's ``CalculAllocationLogementFoyer``."""

    rent_category: ResidenceHallRentCategory = ResidenceHallRentCategory.OTHER_PERSONS
    """The category of rent equivalence of D842-16."""

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculAllocationLogementFoyer``."""
        return "CalculAllocationLogementFoyer"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """Extends the inputs of the personalised aid with the category of D842-16."""
        return super().catala_names | {
            "catégorie_équivalence_loyer_d842_16": "rent_category"
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`HallAllowanceOutput`."""
        return HallAllowanceOutput

    @classproperty
    def limitation_period(cls) -> tuple[datetime.date, datetime.date]:
        """D861-8: overseas, from September 1, 2019, until April 5, 2023, excluded."""
        return HallPartsProvision.limitation_period

    @cached_property
    def personalised_aid(self) -> HallAidCase:
        """
        D842-15: the personalised aid with the same inputs, of a hall of the 2° of
        D832-25, the parts limited in the overseas departments until April 2023 (D861-8).
        """
        first, last = self.limitation_period
        return HallAidCase(
            residence=self.residence,
            young_workers_hostel=self.young_workers_hostel,
            hall_type=self.hall_type,
            agreement_date=self.agreement_date,
            resources=self.resources,
            dependant_count=self.dependant_count,
            family_situation=self.family_situation,
            zone=self.zone,
            assessment_date=self.assessment_date,
            fee=self.fee,
            stated_second_case=True,
            limits_dependant_parts=self.residence
            in HallAidProvision.overseas_departments
            and first <= self.assessment_date < last,
        )

    @cached_property
    def allowance_parts(self) -> Fraction:
        """D842-15: the parts of a hall of the 2° of D832-25, not limited."""
        return HallPartsCase(
            assessment_date=self.assessment_date,
            second_case_of_d832_25=True,
            dependant_count=self.dependant_count,
            family_situation=self.family_situation,
        ).output(HallPartsOutput.PARTS)

    @cached_property
    def minimum_rent(self) -> Money | None:
        """D842-15: the minimum rent equivalence of a hall of the 2°."""
        return MinimumRentEquivalenceCase(
            assessment_date=self.assessment_date,
            resources=self.resources,
            second_case_of_d832_25=True,
            parts=self.allowance_parts,
        ).output(MinimumRentEquivalenceOutput.AMOUNT)

    @cached_property
    def scale(self) -> RentedHomeScale | None:
        """The amounts of article 40, the flat charges of article 9, in force."""
        return DatedValue.value_in_force(RentedHomeScales, self.assessment_date)

    @cached_property
    def overseas_scale(self) -> OverseasScale | None:
        """The amounts of article 46 in force."""
        return DatedValue.value_in_force(OverseasScales, self.assessment_date)

    def treated_aid(self, aid: Money) -> Money | None:
        """:return: *aid* treated as ``traitement_aide_finale`` treats it; None where no rule does."""
        return AidTreatment(case=self, aid=aid).sole_amount(
            HallAllowanceMinimumAidProvision
        )

    def output(self, variable: str) -> CatalaValue | Callable[[Money], Money | None]:
        """Overrides :meth:`HallAidCase.output` with the outputs of the allowance."""
        match HallAllowanceOutput(variable):
            case HallAllowanceOutput.COVERAGE:
                return self.personalised_aid.output(HallAidOutput.COVERAGE)
            case HallAllowanceOutput.MINIMUM_RENT:
                return self.minimum_rent
            case HallAllowanceOutput.AID_TREATMENT:
                return self.treated_aid
        provision = {
            HallAllowanceOutput.RENT_EQUIVALENCE: RentEquivalenceProvision,
            HallAllowanceOutput.FLAT_CHARGES: HallFlatChargesProvision,
            HallAllowanceOutput.INITIAL_AID: HallAllowanceInitialAidProvision,
        }[HallAllowanceOutput(variable)]
        amount = self.sole_conclusion(provision)
        return None if amount is None else amount.amount


@dataclass(eq=False)
class RentEquivalence(CaseAmount):
    """Article 43: the rent equivalence of the resident's category."""


@dataclass(eq=False)
class HallFlatCharges(CaseAmount):
    """D842-15 and article 40: the flat charges."""


@dataclass(eq=False)
class HallAllowanceInitialAid(CaseAmount):
    """D842-15: the allowance the formula gives."""


@dataclass
class RentEquivalenceProvision(HallAidProvision):
    """Article 43: the rent equivalence of the resident's category, of a person alone or a couple."""

    def query(self) -> Query:
        case = variable(HallAllowanceCase, domain=[self.case])
        equivalence = variable(
            ResidenceHallRentEquivalence,
            domain=list(ResidenceHallRentEquivalence.versions()),
        )
        return RuleChain(
            conclusion=deduced_variable(RentEquivalence),
            branches=[
                RuleBranch(
                    conditions=(
                        DatedValue.is_in_force(equivalence, case.assessment_date),
                        equivalence.category == case.rent_category,
                        case.family_situation == AidFamilySituation.COUPLE,
                    ),
                    inferred=inference(RentEquivalence)(
                        case=case, amount=equivalence.couple
                    ),
                ),
                RuleBranch(
                    conditions=(
                        DatedValue.is_in_force(equivalence, case.assessment_date),
                        equivalence.category == case.rent_category,
                    ),
                    inferred=inference(RentEquivalence)(
                        case=case, amount=equivalence.single
                    ),
                ),
            ],
        ).query()


@dataclass
class HallFlatChargesProvision(HallAidProvision):
    """
    Article 40: the flat charges of article 9, and more for each dependant; article 46
    sets those of overseas, counting six dependants at most until 2022.
    """

    @property
    def conclusions(self) -> list[HallFlatCharges]:
        """Extends :meth:`Provision.conclusions`: none before the scales Catala's example states."""
        if self.case.scale is None:
            return []
        return super().conclusions

    def query(self) -> Query:
        case = variable(HallAllowanceCase, domain=[self.case])
        scale = self.case.scale
        overseas = self.case.overseas_scale
        dependants: int = self.case.dependant_count
        branches = []
        if overseas is not None:
            counted = (
                dependants
                if overseas.dependants_counted_at_most is None
                else min(dependants, overseas.dependants_counted_at_most)
            )
            branches.append(
                RuleBranch(
                    conditions=(
                        in_(case.residence, RentedAidProvision.overseas_territories),
                    ),
                    inferred=inference(HallFlatCharges)(
                        case=case,
                        amount=overseas.charges
                        + overseas.charges_per_dependant * counted,
                    ),
                )
            )
        branches.append(
            RuleBranch(
                conditions=(),
                inferred=inference(HallFlatCharges)(
                    case=case,
                    amount=scale.charges + scale.charges_per_dependant * dependants,
                ),
            )
        )
        return RuleChain(
            conclusion=deduced_variable(HallFlatCharges), branches=branches
        ).query()


@dataclass
class HallAllowanceInitialAidProvision(HallAidProvision):
    """D842-15: the rent equivalence and flat charges less the minimum rent, times the coverage."""

    def query(self) -> Query:
        case = variable(HallAllowanceCase, domain=[self.case])
        equivalence = self.sole(RentEquivalenceProvision)
        charges = self.sole(HallFlatChargesProvision)
        coverage = self.case.output(HallAllowanceOutput.COVERAGE)
        minimum = self.case.minimum_rent
        return an(
            entity(
                inference(HallAllowanceInitialAid)(
                    case=case,
                    amount=(equivalence.amount + charges.amount - minimum) * coverage,
                )
            )
        )


@dataclass
class HallAllowanceFlatReducedAidProvision(TreatmentProvision):
    """D842-15 and article 41: the allowance less 5 €, none below zero."""

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        reduced = (
            self.previous_amount(treatment) - HallFlatReducedAidProvision.flat_reduction
        )
        return TreatmentChain.at_least_zero(treatment, reduced)


@dataclass
class HallAllowanceNetExpenseProvision(TreatmentProvision):
    """
    D842-17 and article 44: the allowance less the shortfall of the net expense, the rent
    equivalence and flat charges less the allowance, below 15 €.
    """

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`HallAllowanceFlatReducedAidProvision`."""
        return HallAllowanceFlatReducedAidProvision

    @classproperty
    def minimum_net_expense(cls) -> Money:
        """Article 44: 15 €."""
        return Money.from_euros(15)

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        aid = self.previous_amount(treatment)
        equivalence = self.case_conclusion(RentEquivalenceProvision)
        charges = self.case_conclusion(HallFlatChargesProvision)
        abatement = NetExpense.strict_shortfall(
            equivalence.amount + charges.amount - aid, self.minimum_net_expense
        )
        return TreatmentChain.at_least_zero(treatment, aid - abatement)


@dataclass
class HallAllowanceFeeCapProvision(TreatmentProvision):
    """D842-15: the allowance, the fee at most."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`HallAllowanceNetExpenseProvision`."""
        return HallAllowanceNetExpenseProvision

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        aid = self.previous_amount(treatment)
        fee = treatment.case.fee
        return RuleChain(
            conclusion=deduced_variable(HallTreatedAid),
            branches=[
                RuleBranch(
                    conditions=(aid > fee,),
                    inferred=inference(HallTreatedAid)(treatment=treatment, amount=fee),
                ),
                RuleBranch(
                    conditions=(),
                    inferred=inference(HallTreatedAid)(treatment=treatment, amount=aid),
                ),
            ],
        ).query()


@dataclass
class HallAllowanceContributionRoundedProvision(TreatmentProvision):
    """D842-15: the allowance net of its contribution, rounded down to the euro, the contribution added back."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`HallAllowanceFeeCapProvision`."""
        return HallAllowanceFeeCapProvision

    def query(self) -> Query:
        return TreatmentChain.contribution_rounded(self)


@dataclass
class HallAllowanceSaintPierreProvision(TreatmentProvision):
    """Article 7 of décret n° 2021-1750: the allowance phased in in Saint-Pierre-et-Miquelon."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`HallAllowanceContributionRoundedProvision`."""
        return HallAllowanceContributionRoundedProvision

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        aid = self.previous_amount(treatment)
        return an(
            entity(
                inference(HallTreatedAid)(
                    treatment=treatment,
                    amount=SaintPierrePhaseIn.phased(
                        aid, treatment.case.residence, treatment.case.assessment_date
                    ),
                )
            )
        )


@dataclass(frozen=True)
class SaintPierrePhaseIn:
    """Article 7 of décret n° 2021-1750, Catala's ``montée_en_charge_saint_pierre_miquelon``."""

    @staticmethod
    @symbolic_function
    def phased(aid: Money, residence: Territory, day: datetime.date) -> Money:
        """:return: *aid* less an eighth for each year before 2026, in Saint-Pierre-et-Miquelon from 2022 to 2025."""
        if residence == Territory.SAINT_PIERRE_AND_MIQUELON and (
            datetime.date(2022, 1, 1) <= day <= datetime.date(2025, 12, 31)
        ):
            return aid * (1 - Fraction(2026 - day.year, 8))
        return aid


@dataclass
class HallAllowanceMinimumAidProvision(TreatmentProvision):
    """D842-15 and article 42: no allowance below 10 €."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`HallAllowanceSaintPierreProvision`."""
        return HallAllowanceSaintPierreProvision

    def query(self) -> Query:
        return TreatmentChain.at_least(self, HallMinimumAidProvision.least_aid)


# %% test files


class ResidenceHallTestFile(ScopeTestFile, StrEnum):
    """The test files of the aids of residence halls of Catala's ``aides_logement`` example."""

    PERSONALISED_AID = "tests_calcul_apl_logement_foyer.catala_fr"
    """Five households, four asking the personalised aid and one the allowance."""

    HOUSING_ALLOWANCE = "tests_calcul_al_logement_foyer.catala_fr"
    """One household asking the allowance."""

    @property
    def directory(self) -> Path:
        """:file:`aides_logement/tests`."""
        return CatalaDirectory.ROOT / "aides_logement" / "tests"

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """The personalised aid and the allowance of residence halls."""
        return [HallAidCase, HallAllowanceCase]
