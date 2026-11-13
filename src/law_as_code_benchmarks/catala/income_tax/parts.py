"""
The parts of the family quotient of articles 194 to 196 B of the Code général des
impôts, Catala's ``NombreDeParts``, and the abatement of 196 B for adult children.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction

from krrood.entity_query_language.factories import (
    an,
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

from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.provision import RuleBranch, RuleChain
from law_as_code_benchmarks.catala.reader import CatalaValue
from law_as_code_benchmarks.catala.scope_test import (
    CaseAmount,
    CaseCondition,
    CaseConclusion,
    CaseFraction,
    CatalaRecord,
    ScopeCase,
    ScopeProvision,
)

# %% the tax household


class TaxFamilySituation(StrEnum):
    """The family situation of the tax household, each named as Catala's ``SituationFamiliale``."""

    MARRIED = "Mariées"
    """Married."""

    CIVIL_PARTNERS = "Pacsées"
    """Partners of a civil solidarity pact."""

    DIVORCED_OR_SEPARATED = "DivorcéeSéparées"
    """Divorced or separated."""

    SINGLE = "Célibataire"
    """Single."""

    WIDOWED = "Veuve"
    """Widowed."""


@dataclass(eq=False)
class TaxHouseholdDescription(CatalaRecord):
    """What the return states of the tax household, Catala's ``DescriptionFoyerFiscal``, each field a box of the form."""

    minor_unmarried_children: int = 0
    """Box F: the minor unmarried children in the household's charge."""

    disabled_minor_unmarried_children: int = 0
    """Box G: those of them who are disabled."""

    shared_residence_children: int = 0
    """Box H: the children in shared residence."""

    disabled_shared_residence_children: int = 0
    """Box I: those of them who are disabled."""

    other_disabled_persons: int = 0
    """Box R: other disabled persons living under the household's roof."""

    single_adult_children_without_children: int = 0
    """The single adult children without children attached to the household."""

    married_adult_children_or_with_family: Fraction = Fraction(0)
    """The adult children who are married or have a family, attached to the household."""

    married: bool = False
    """Box M."""

    single: bool = False
    """Box C."""

    civil_partners: bool = False
    """Box O."""

    divorced_or_separated: bool = False
    """Box D."""

    widowed: bool = False
    """Box V."""

    single_parent: bool = False
    """Box T: a parent raising their children alone."""

    alone_without_children: bool = False
    """Box L: single, divorced or widowed, without children, who raised a child."""

    disability_card: bool = False
    """Box P: the declarant holds a disability card of 40 % at least."""

    spouse_disability_card: bool = False
    """Box F: the spouse holds one."""

    war_pensioner_alone: bool = False
    """Box W: a single or widowed war pensioner."""

    war_pensioner_in_couple: bool = False
    """Box S: a married or partnered war pensioner."""

    war_widow: bool = False
    """Box G: the widow of a war pensioner."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``DescriptionFoyerFiscal``."""
        return {
            "nombre_enfants_à_charge_mineurs_et_non_mariés": "minor_unmarried_children",
            "nombre_enfants_à_charge_mineurs_et_non_mariés_invalides": "disabled_minor_unmarried_children",
            "nombre_enfants_à_charge_résidence_alternée": "shared_residence_children",
            "nombre_enfants_à_charge_résidence_alternée_invalides": "disabled_shared_residence_children",
            "nombre_autres_personnes_invalides_vivant_sous_toit": "other_disabled_persons",
            "nombre_enfants_majeurs_célibataires_sans_enfant": "single_adult_children_without_children",
            "nombre_enfants_majeurs_mariés_ou_chargés_famille": "married_adult_children_or_with_family",
            "mariées": "married",
            "célibataire": "single",
            "pacsées": "civil_partners",
            "divorcée_séparées": "divorced_or_separated",
            "veuve": "widowed",
            "parent_isolé": "single_parent",
            "célibataire_divorcé_veuf_sans_enfant": "alone_without_children",
            "titulaire_carte_invalidité_CMI_invalidité_40_pourcent": "disability_card",
            "conjoint_titulaire_carte_invalidité_CMI_invalidité_40_pourcent": "spouse_disability_card",
            "pensionné_guerre_célibataire_veuf": "war_pensioner_alone",
            "pensionné_guerre_marié_pacsé": "war_pensioner_in_couple",
            "pensionné_veuve_de_guerre": "war_widow",
        }


# %% the case


class PartsOutput(StrEnum):
    """The outputs of ``NombreDeParts``."""

    PARTS = "nombre_de_parts"
    """The parts."""

    ABATEMENT = "abattement"
    """The abatement for adult children."""


@dataclass(eq=False)
class PartsCase(ScopeCase):
    """The inputs of the parts, Catala's ``NombreDeParts``."""

    household: TaxHouseholdDescription
    """What the return states of the household."""

    income_year: int
    """The year of the income taxed."""

    @classproperty
    def catala_scope(cls) -> str:
        """``NombreDeParts``."""
        return "NombreDeParts"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {"foyer_fiscal": "household", "année_revenus": "income_year"}

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`PartsOutput`."""
        return PartsOutput

    def output(self, variable: str) -> CatalaValue:
        if PartsOutput(variable) == PartsOutput.ABATEMENT:
            abatement = self.sole_conclusion(AdultChildrenAbatementProvision)
            return None if abatement is None else abatement.amount
        parts = self.sole_conclusion(AdultChildrenPartsProvision)
        return None if parts is None else parts.fraction


# %% conclusions


@dataclass(eq=False)
class FamilySituationConclusion(CaseConclusion):
    """The family situation the boxes of the return state."""

    situation: TaxFamilySituation = TaxFamilySituation.SINGLE
    """The situation."""


@dataclass(eq=False)
class FirstCaseOf195(CaseCondition):
    """195 1: the half part of a person alone who raised a child, or holds a disability card or a war pension."""


@dataclass(eq=False)
class Parts(CaseFraction):
    """The parts after one article of 194 to 196 B."""


@dataclass(eq=False)
class AdultChildrenAbatement(CaseAmount):
    """196 B: the abatement for adult children married or with a family."""


# %% provisions


@dataclass
class PartsProvision(ScopeProvision, ABC):
    """A provision of the parts."""

    @classproperty
    def alone(cls) -> frozenset[TaxFamilySituation]:
        """The situations of a person alone: single, divorced or separated, widowed."""
        return frozenset(
            {
                TaxFamilySituation.SINGLE,
                TaxFamilySituation.DIVORCED_OR_SEPARATED,
                TaxFamilySituation.WIDOWED,
            }
        )

    @classproperty
    def couple(cls) -> frozenset[TaxFamilySituation]:
        """The situations of a couple: married or partnered."""
        return frozenset(
            {TaxFamilySituation.MARRIED, TaxFamilySituation.CIVIL_PARTNERS}
        )

    def situation(self) -> FamilySituationConclusion:
        """:return: A variable over the household's family situation."""
        return variable(
            FamilySituationConclusion,
            domain=FamilySituationProvision(case=self.case).conclusions,
        )

    def previous_parts(self, provision: type[PartsProvision]) -> Parts:
        """:return: A variable over the parts *provision* concludes."""
        return variable(Parts, domain=provision(case=self.case).conclusions)


@dataclass
class FamilySituationProvision(PartsProvision):
    """The family situation of the box ticked: M, C, O, D, and V otherwise."""

    def query(self) -> Query:
        case = variable(PartsCase, domain=[self.case])
        household = case.household
        branches = [
            RuleBranch(
                conditions=(ticked == True,),
                inferred=inference(FamilySituationConclusion)(
                    case=case, situation=situation
                ),
            )
            for ticked, situation in (
                (household.married, TaxFamilySituation.MARRIED),
                (household.single, TaxFamilySituation.SINGLE),
                (household.civil_partners, TaxFamilySituation.CIVIL_PARTNERS),
                (
                    household.divorced_or_separated,
                    TaxFamilySituation.DIVORCED_OR_SEPARATED,
                ),
            )
        ]
        branches.append(
            RuleBranch(
                conditions=(),
                inferred=inference(FamilySituationConclusion)(
                    case=case, situation=TaxFamilySituation.WIDOWED
                ),
            )
        )
        return RuleChain(
            conclusion=deduced_variable(FamilySituationConclusion), branches=branches
        ).query()


@dataclass
class BasePartsProvision(PartsProvision):
    """194, from 2017: one part, two for a couple, and more for the minor unmarried children."""

    @classproperty
    def first_year(cls) -> int:
        """2017."""
        return 2017

    def query(self) -> Query:
        case = variable(PartsCase, domain=[self.case])
        situation = self.situation()
        return an(
            entity(
                inference(Parts)(
                    case=case,
                    fraction=FamilyQuotient.base_parts(
                        situation.situation, case.household.minor_unmarried_children
                    ),
                )
            ).where(case.income_year >= self.first_year)
        )


@dataclass(frozen=True)
class FamilyQuotient:
    """The tables of article 194."""

    @staticmethod
    @symbolic_function
    def base_parts(situation: TaxFamilySituation, children: int) -> Fraction:
        """:return: The parts of 194 for *situation* and *children* minor unmarried children."""
        alone = situation in {
            TaxFamilySituation.SINGLE,
            TaxFamilySituation.DIVORCED_OR_SEPARATED,
        }
        if children == 0:
            return Fraction(1) if situation in PartsProvision.alone else Fraction(2)
        if children == 1:
            return Fraction(3, 2) if alone else Fraction(5, 2)
        if children == 2:
            return Fraction(2) if alone else Fraction(3)
        return Fraction(children) if alone else Fraction(children + 1)

    @staticmethod
    @symbolic_function
    def shared_residence_parts(children: int, shared: int) -> Fraction:
        """:return: The parts 194 adds for *shared* children in shared residence, with *children* in the household's charge."""
        if children == 0:
            if shared <= 2:
                return Fraction(1, 4) * shared
            return Fraction(1, 2) + Fraction(1, 2) * (shared - 2)
        if children == 1:
            if shared <= 1:
                return Fraction(1, 4) * shared
            return Fraction(1, 4) + Fraction(1, 2) * (shared - 1)
        return Fraction(1, 2) * shared

    @staticmethod
    @symbolic_function
    def single_parent_parts(
        single_parent: bool, children: int, shared: int
    ) -> Fraction:
        """:return: The parts 194 adds for a parent raising their children alone."""
        if not single_parent:
            return Fraction(0)
        if children >= 1:
            return Fraction(1, 2)
        if shared == 1:
            return Fraction(1, 4)
        if shared >= 2:
            return Fraction(1, 2)
        return Fraction(0)


@dataclass
class SharedResidencePartsProvision(PartsProvision):
    """194: a quarter part for each of the first children in shared residence, a half beyond."""

    def query(self) -> Query:
        case = variable(PartsCase, domain=[self.case])
        previous = self.previous_parts(BasePartsProvision)
        household = case.household
        return an(
            entity(
                inference(Parts)(
                    case=case,
                    fraction=previous.fraction
                    + FamilyQuotient.shared_residence_parts(
                        household.minor_unmarried_children,
                        household.shared_residence_children,
                    ),
                )
            )
        )


@dataclass
class FirstCaseOf195Provision(PartsProvision):
    """
    195 1, from 2021: box L, a war widow, a disability card, or box W; not for a couple
    where one of them holds a disability card.
    """

    @classproperty
    def first_year(cls) -> int:
        """2021."""
        return 2021

    def query(self) -> Query:
        case = variable(PartsCase, domain=[self.case])
        situation = self.situation()
        household = case.household
        recent = case.income_year >= self.first_year
        return RuleChain(
            conclusion=deduced_variable(FirstCaseOf195),
            branches=[
                RuleBranch(
                    conditions=(
                        recent,
                        in_(situation.situation, self.couple),
                        or_(
                            household.disability_card == True,
                            household.spouse_disability_card == True,
                        ),
                    ),
                    inferred=inference(FirstCaseOf195)(case=case, holds=False),
                ),
                RuleBranch(
                    conditions=(
                        recent,
                        or_(
                            household.alone_without_children == True,
                            household.war_widow == True,
                            household.disability_card == True,
                            household.war_pensioner_alone == True,
                        ),
                    ),
                    inferred=inference(FirstCaseOf195)(case=case, holds=True),
                ),
                RuleBranch(
                    conditions=(),
                    inferred=inference(FirstCaseOf195)(case=case, holds=False),
                ),
            ],
        ).query()


@dataclass
class SingleParentPartsProvision(PartsProvision):
    """
    194: half a part for a parent alone with a child in their charge, a quarter or a half
    with children in shared residence only. 195 1 gives a person alone without children
    one and a half parts from 2021.
    """

    def query(self) -> Query:
        case = variable(PartsCase, domain=[self.case])
        previous = self.previous_parts(SharedResidencePartsProvision)
        situation = self.situation()
        first_case = variable(
            FirstCaseOf195, domain=FirstCaseOf195Provision(case=self.case).conclusions
        )
        household = case.household
        return RuleChain(
            conclusion=deduced_variable(Parts),
            branches=[
                RuleBranch(
                    conditions=(
                        case.income_year >= FirstCaseOf195Provision.first_year,
                        in_(situation.situation, self.alone),
                        household.minor_unmarried_children == 0,
                        household.shared_residence_children == 0,
                        first_case.holds == True,
                    ),
                    inferred=inference(Parts)(case=case, fraction=Fraction(3, 2)),
                ),
                RuleBranch(
                    conditions=(),
                    inferred=inference(Parts)(
                        case=case,
                        fraction=previous.fraction
                        + FamilyQuotient.single_parent_parts(
                            household.single_parent,
                            household.minor_unmarried_children,
                            household.shared_residence_children,
                        ),
                    ),
                ),
            ],
        ).query()


@dataclass
class IncreasedPartsProvision(PartsProvision, ABC):
    """A provision of 195 adding parts to those of the provision before it, from 2021."""

    @classproperty
    @abstractmethod
    def previous_provision(cls) -> type[PartsProvision]:
        """The provision whose parts this one adds to."""

    @staticmethod
    @abstractmethod
    def added_parts(
        situation: TaxFamilySituation, household: TaxHouseholdDescription
    ) -> Fraction:
        """:return: The parts added for *situation* and *household*, a symbolic function."""

    def query(self) -> Query:
        case = variable(PartsCase, domain=[self.case])
        previous = self.previous_parts(self.previous_provision)
        situation = self.situation()
        return an(
            entity(
                inference(Parts)(
                    case=case,
                    fraction=previous.fraction
                    + self.added_parts(situation.situation, case.household),
                )
            ).where(case.income_year >= FirstCaseOf195Provision.first_year)
        )


@dataclass
class DisabledChildrenPartsProvision(IncreasedPartsProvision):
    """195 2 and 196 A bis: half a part for each disabled child or person under the roof, a quarter in shared residence."""

    @classproperty
    def previous_provision(cls) -> type[PartsProvision]:
        """:class:`SingleParentPartsProvision`."""
        return SingleParentPartsProvision

    @staticmethod
    @symbolic_function
    def added_parts(
        situation: TaxFamilySituation, household: TaxHouseholdDescription
    ) -> Fraction:
        return (
            Fraction(1, 2)
            * (
                household.disabled_minor_unmarried_children
                + household.other_disabled_persons
            )
            + Fraction(1, 4) * household.disabled_shared_residence_children
        )


@dataclass
class DisabledSpousePartsProvision(IncreasedPartsProvision):
    """195 3: half a part for a couple of whom one holds a disability card."""

    @classproperty
    def previous_provision(cls) -> type[PartsProvision]:
        """:class:`DisabledChildrenPartsProvision`."""
        return DisabledChildrenPartsProvision

    @staticmethod
    @symbolic_function
    def added_parts(
        situation: TaxFamilySituation, household: TaxHouseholdDescription
    ) -> Fraction:
        holds = situation in PartsProvision.couple and (
            household.disability_card or household.spouse_disability_card
        )
        return Fraction(1, 2) if holds else Fraction(0)


@dataclass
class BothDisabledPartsProvision(IncreasedPartsProvision):
    """195 4: half a part more for a couple of whom both hold a disability card."""

    @classproperty
    def previous_provision(cls) -> type[PartsProvision]:
        """:class:`DisabledSpousePartsProvision`."""
        return DisabledSpousePartsProvision

    @staticmethod
    @symbolic_function
    def added_parts(
        situation: TaxFamilySituation, household: TaxHouseholdDescription
    ) -> Fraction:
        holds = situation in PartsProvision.couple and (
            household.disability_card and household.spouse_disability_card
        )
        return Fraction(1, 2) if holds else Fraction(0)


@dataclass
class DisabledParentPartsProvision(IncreasedPartsProvision):
    """195 5: half a part for a person alone with a child, who is a war widow or holds a disability card."""

    @classproperty
    def previous_provision(cls) -> type[PartsProvision]:
        """:class:`BothDisabledPartsProvision`."""
        return BothDisabledPartsProvision

    @staticmethod
    @symbolic_function
    def added_parts(
        situation: TaxFamilySituation, household: TaxHouseholdDescription
    ) -> Fraction:
        holds = (
            situation in PartsProvision.alone
            and household.shared_residence_children + household.minor_unmarried_children
            >= 1
            and (household.war_widow or household.disability_card)
        )
        return Fraction(1, 2) if holds else Fraction(0)


@dataclass
class WarPensionerPartsProvision(IncreasedPartsProvision):
    """195 6: half a part for a married or partnered war pensioner."""

    @classproperty
    def previous_provision(cls) -> type[PartsProvision]:
        """:class:`DisabledParentPartsProvision`."""
        return DisabledParentPartsProvision

    @staticmethod
    @symbolic_function
    def added_parts(
        situation: TaxFamilySituation, household: TaxHouseholdDescription
    ) -> Fraction:
        return Fraction(1, 2) if household.war_pensioner_in_couple else Fraction(0)


@dataclass
class AdultChildrenPartsProvision(PartsProvision):
    """196 B, for the income of 2022 and 2023: half a part for each single adult child without children."""

    @classproperty
    def years(cls) -> frozenset[int]:
        """The years Catala's example states 196 B for, 2022 and 2023."""
        return frozenset({2022, 2023})

    def query(self) -> Query:
        case = variable(PartsCase, domain=[self.case])
        previous = self.previous_parts(WarPensionerPartsProvision)
        return an(
            entity(
                inference(Parts)(
                    case=case,
                    fraction=previous.fraction
                    + Fraction(1, 2)
                    * case.household.single_adult_children_without_children,
                )
            ).where(in_(case.income_year, self.years))
        )


@dataclass
class AdultChildrenAbatementProvision(PartsProvision):
    """196 B: 6,368 € for each adult child married or with a family for the income of 2022, 6,674 € for 2023."""

    @classproperty
    def abatement_by_year(cls) -> dict[int, Money]:
        """The abatement for one child, by year of the income."""
        return {2022: Money.from_euros(6368), 2023: Money.from_euros(6674)}

    def query(self) -> Query:
        case = variable(PartsCase, domain=[self.case])
        branches = [
            RuleBranch(
                conditions=(case.income_year == year,),
                inferred=inference(AdultChildrenAbatement)(
                    case=case,
                    amount=abatement
                    * case.household.married_adult_children_or_with_family,
                ),
            )
            for year, abatement in self.abatement_by_year.items()
        ]
        return RuleChain(
            conclusion=deduced_variable(AdultChildrenAbatement), branches=branches
        ).query()
