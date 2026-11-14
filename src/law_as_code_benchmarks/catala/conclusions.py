"""
What the provisions of the family benefits conclude about a household or a child, one
class for each variable of Catala's scopes the computation needs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction

from law_as_code_benchmarks.law.provision import Conclusion
from law_as_code_benchmarks.catala.domain import (
    ChargeShare,
    Child,
    Household,
    SchoolingStage,
)
from law_as_code_benchmarks.catala.money import Money

# %% shapes shared by many conclusions


@dataclass(eq=False)
class HouseholdConclusion(Conclusion):
    """A conclusion about a household."""

    household: Household
    """The household."""


@dataclass(eq=False)
class HouseholdAmount(HouseholdConclusion):
    """An amount a provision gives a household."""

    amount: Money = field(default_factory=lambda: Money.zero)
    """The amount."""


@dataclass(eq=False)
class HouseholdCondition(HouseholdConclusion):
    """Whether a condition of a provision holds for a household, false where no rule says it does."""

    holds: bool = False
    """Whether the condition holds."""


@dataclass(eq=False)
class ChildConclusion(Conclusion):
    """A conclusion about a child in a household's charge."""

    child: Child
    """The child."""


@dataclass(eq=False)
class ChildAmount(ChildConclusion):
    """An amount a provision gives for a child."""

    amount: Money = field(default_factory=lambda: Money.zero)
    """The amount."""


@dataclass(eq=False)
class ChildCondition(ChildConclusion):
    """Whether a condition of a provision holds for a child, false where no rule says it does."""

    holds: bool = False
    """Whether the condition holds."""


# %% amounts in force


@dataclass(eq=False)
class MonthlyBaseAmount(HouseholdAmount):
    """The monthly base of family allowances in force on the household's assessment date."""


@dataclass(eq=False)
class HourlyMinimumWageAmount(HouseholdAmount):
    """The gross hourly minimum wage in force where and when the household is assessed."""


# %% entitlement to family benefits


@dataclass(eq=False)
class OverseasRegime(HouseholdCondition):
    """`L751-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031323778>`__: the household lives in an overseas department the special provisions apply in."""


@dataclass(eq=False)
class PayCeiling(HouseholdAmount):
    """`R512-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006750602>`__: the monthly pay a child past compulsory schooling may earn and still give a right to family benefits."""


@dataclass(eq=False)
class SchoolingStageOfChild(ChildConclusion):
    """`L131-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000038901859>`__ of the Code de l'éducation: where the child stands to compulsory schooling."""

    stage: SchoolingStage = SchoolingStage.DURING
    """The stage."""


@dataclass(eq=False)
class FamilyBenefitEntitlement(ChildCondition):
    """`L512-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000041979743>`__: the child gives a right to family benefits."""


@dataclass(eq=False)
class ConditionsBesidesAge(ChildCondition):
    """`L512-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000041979743>`__: the child meets every condition of the right to family benefits but its age."""


@dataclass(eq=False)
class EntitledChildren(HouseholdConclusion):
    """The children in the household's charge who give a right to family benefits."""

    children: list[Child] = field(default_factory=list)
    """The children, in the household's order."""

    @property
    def number_of_children(self) -> int:
        """How many children give a right to family benefits."""
        return len(self.children)


# %% the household's bracket


@dataclass(frozen=True)
class BracketRates:
    """The rates of the monthly base family allowances pay in one bracket of resources."""

    second_child: Fraction
    """The rate for the second child, by a) of the bracket's paragraph of D521-1."""

    later_child: Fraction
    """The rate for the third child and each one after, by b) of the bracket's paragraph of D521-1."""

    age_supplement: Fraction
    """The rate of the age supplement, by the bracket's paragraph of D521-1."""

    flat_allowance: Fraction
    """The rate of the flat allowance per child, by the bracket's paragraph of D521-2."""


class ResourceBracket(Enum):
    """
    The three brackets of `D521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680318>`__ and `D521-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680324>`__ by a household's
    resources, each worth the rates it pays.
    """

    FIRST = BracketRates(
        second_child=Fraction(32, 100),
        later_child=Fraction(41, 100),
        age_supplement=Fraction(16, 100),
        flat_allowance=Fraction("20.234") / 100,
    )
    """Resources up to the first ceiling."""

    SECOND = BracketRates(
        second_child=Fraction(16, 100),
        later_child=Fraction("20.5") / 100,
        age_supplement=Fraction(8, 100),
        flat_allowance=Fraction("10.117") / 100,
    )
    """Resources above the first ceiling, up to the second."""

    THIRD = BracketRates(
        second_child=Fraction(8, 100),
        later_child=Fraction("10.25") / 100,
        age_supplement=Fraction(4, 100),
        flat_allowance=Fraction("5.059") / 100,
    )
    """Resources above the second ceiling."""


@dataclass(eq=False)
class ApplicableResourceCeilings(HouseholdConclusion):
    """`D521-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044809227>`__: the two resource ceilings for the household, raised for every entitled child."""

    first_ceiling: Money = field(default_factory=lambda: Money.zero)
    """The ceiling of I."""

    second_ceiling: Money = field(default_factory=lambda: Money.zero)
    """The ceiling of II."""


@dataclass(eq=False)
class HouseholdBracket(HouseholdConclusion):
    """The bracket the household's resources fall in."""

    bracket: ResourceBracket = ResourceBracket.FIRST
    """The bracket."""


# %% the base allowance


@dataclass(eq=False)
class BaseAllowanceRight(HouseholdCondition):
    """`L521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000029963006>`__: the household has a right to family allowances."""


@dataclass(eq=False)
class FirstChildAmount(HouseholdAmount):
    """What family allowances pay for a first child, where they pay for one."""


@dataclass(eq=False)
class SecondChildAmount(HouseholdAmount):
    """What family allowances pay for a second child."""


@dataclass(eq=False)
class LaterChildrenAmount(HouseholdAmount):
    """What family allowances pay for the third child and every one after."""


@dataclass(eq=False)
class MayotteThirdChildAmount(HouseholdAmount):
    """3° of article 7 of the décret n°2002-423: what family allowances in Mayotte pay for a third child."""


@dataclass(eq=False)
class MayotteLaterChildrenAmount(HouseholdAmount):
    """4° of article 7 of the décret n°2002-423: what family allowances in Mayotte pay for the fourth child and every one after."""


@dataclass(eq=False)
class InitialBaseAmount(HouseholdAmount):
    """The family allowances for all of the household's entitled children, before a shared residence divides them."""


@dataclass(eq=False)
class ChargeShareOfChild(ChildConclusion):
    """`L521-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000039099826>`__: the share of the child that counts towards the household's allowances."""

    share: ChargeShare = ChargeShare.FULL
    """The share."""


@dataclass(eq=False)
class ChildrenRatio(HouseholdConclusion):
    """`R521-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006750610>`__: the average number of children over their total number."""

    ratio: Fraction = Fraction(0)
    """The ratio; zero where the household has no entitled child."""


@dataclass(eq=False)
class PaidBaseAllowance(HouseholdAmount):
    """The family allowances paid for the household's children, age supplements aside."""


# %% age supplements


@dataclass(eq=False)
class AgeSupplementMinimumAge(ChildConclusion):
    """`R521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000018735853>`__: the age from which the child gives a right to an age supplement."""

    age: int = 14
    """The age, in years."""


@dataclass(eq=False)
class AgeSupplementRight(ChildCondition):
    """`L521-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006743289>`__: the child gives a right to an age supplement."""


@dataclass(eq=False)
class InitialAgeSupplement(ChildAmount):
    """The age supplement for the child, before a shared residence halves it."""


@dataclass(eq=False)
class SharedAgeSupplement(ChildAmount):
    """`R521-4 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006750613>`__: the age supplement for the child, halved for a shared residence."""


@dataclass(eq=False)
class PaidAgeSupplements(HouseholdAmount):
    """The age supplements paid for the household's entitled children."""


# %% the flat allowance


@dataclass(eq=False)
class FlatAllowanceRight(ChildCondition):
    """`L521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000029963006>`__: the child gives a right to the flat allowance paid for a year once it reaches the age limit."""


@dataclass(eq=False)
class PaidFlatAllowance(HouseholdAmount):
    """`D521-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680324>`__: the flat allowances paid for the household's children."""


# %% degressive supplements


@dataclass(eq=False)
class DegressiveSupplementRight(HouseholdCondition):
    """`L521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000029963006>`__: the household has a right to the degressive supplements."""


@dataclass(eq=False)
class SupplementedAllowance(HouseholdAmount):
    """II of `D521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680318>`__: the base allowance and age supplements paid, which the degressive supplement makes up for."""


@dataclass(eq=False)
class AllowanceDegressiveSupplement(HouseholdAmount):
    """II of `D521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680318>`__: the degressive supplement to the base allowance and the age supplements."""


@dataclass(eq=False)
class FlatAllowanceDegressiveSupplement(HouseholdAmount):
    """II of `D521-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680324>`__: the degressive supplement to the flat allowance."""


# %% the amount paid


@dataclass(eq=False)
class FamilyAllowance(HouseholdAmount):
    """The family allowances paid to the household for the month."""
