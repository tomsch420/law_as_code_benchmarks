"""
The income tax of `§ 1 <https://www.law.cornell.edu/uscode/text/26/1>`__ as rules over the domain model: its four rate schedules, the
tax on a taxpayer by their filing status, and the tax a person owes in all.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum, StrEnum
from numbers import Real

from krrood.entity_query_language.factories import (
    an,
    and_,
    entity,
    exists,
    inference,
    not_,
    variable,
)
from krrood.entity_query_language.predicate import symbolic_function
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from typing_extensions import Hashable

from law_as_code_benchmarks.sara.domain import CalendarYear, Party, World
from law_as_code_benchmarks.sara.employment_tax import ExciseTaxOnEmployer
from law_as_code_benchmarks.sara.employment_tax_conclusions import ExciseTax
from law_as_code_benchmarks.sara.family_status import (
    HeadOfHouseholdTest,
    JointFilingTest,
    MarriedIndividualTest,
    SurvivingSpouseTest,
)
from law_as_code_benchmarks.sara.family_status_conclusions import (
    HeadOfHousehold,
    JointFiling,
    MarriedIndividual,
    SurvivingSpouse,
)
from law_as_code_benchmarks.sara.income_tax_conclusions import (
    BracketTax,
    HeadOfHouseholdIncomeTax,
    IncomeTax,
    JointReturnIncomeTax,
    JointReturnOrSurvivorIncomeTax,
    SeparateReturnIncomeTax,
    SurvivorIncomeTax,
    TaxOwed,
    TotalIncomeTax,
    UnmarriedIncomeTax,
)
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm
from law_as_code_benchmarks.sara.provision import (
    ConclusionType,
    Provision,
    SaraPredicate,
)
from law_as_code_benchmarks.sara.taxable_income import TaxableIncomeTest
from law_as_code_benchmarks.sara.taxable_income_conclusions import TaxableIncome

# %% rate schedules


class TaxSchedule(StrEnum):
    """The rate schedules of `§ 1 <https://www.law.cornell.edu/uscode/text/26/1>`__, each named by its subsection."""

    JOINT_RETURN_OR_SURVIVOR = "a"
    """`§ 1(a) <https://www.law.cornell.edu/uscode/text/26/1#a>`__: married individuals making joint returns, and surviving spouses."""

    HEAD_OF_HOUSEHOLD = "b"
    """`§ 1(b) <https://www.law.cornell.edu/uscode/text/26/1#b>`__: heads of households."""

    UNMARRIED = "c"
    """`§ 1(c) <https://www.law.cornell.edu/uscode/text/26/1#c>`__: unmarried individuals, other than surviving spouses and heads of households."""

    SEPARATE_RETURN = "d"
    """`§ 1(d) <https://www.law.cornell.edu/uscode/text/26/1#d>`__: married individuals filing separate returns."""

    @symbolic_function
    def tax_on(self, taxable_income: float) -> int:
        """:return: The tax the schedule imposes on *taxable_income*, by the bracket it falls in."""
        for bracket in TaxBracket:
            if bracket.value.schedule == self and bracket.value.includes(
                taxable_income
            ):
                return bracket.value.tax_on(taxable_income)
        raise ValueError(taxable_income)


@dataclass(frozen=True)
class RateBracket:
    """A bracket of a rate schedule: a base amount plus a rate of the taxable income over its lower bound."""

    schedule: TaxSchedule
    """The schedule it belongs to."""

    numeral: str
    """Its clause in the schedule, such as ``iii``."""

    lower: float | None
    """The taxable income it is over; None for the first bracket."""

    upper: float | None
    """The most taxable income it covers; None for the last bracket."""

    base: float
    """The tax on its lower bound."""

    rate: float
    """The rate on the taxable income over its lower bound."""

    def includes(self, taxable_income: float) -> bool:
        """:return: Whether *taxable_income* is over the lower bound and not over the upper."""
        return (self.lower is None or self.lower < taxable_income) and (
            self.upper is None or taxable_income <= self.upper
        )

    def tax_on(self, taxable_income: float) -> int:
        """:return: The base plus the rate on *taxable_income* over the lower bound, rounded halves away from zero as Prolog's ``round``."""
        tax = self.base + (taxable_income - (self.lower or 0)) * self.rate
        return int(Decimal(tax).quantize(Decimal(1), ROUND_HALF_UP))


class TaxBracket(Enum):
    """The brackets of the rate schedules of `§ 1 <https://www.law.cornell.edu/uscode/text/26/1>`__."""

    JOINT_RETURN_OR_SURVIVOR_I = RateBracket(
        schedule=TaxSchedule.JOINT_RETURN_OR_SURVIVOR,
        numeral="i",
        lower=None,
        upper=36_900,
        base=0,
        rate=0.15,
    )
    """`§ 1(a)(i) <https://www.law.cornell.edu/uscode/text/26/1#a>`__."""

    JOINT_RETURN_OR_SURVIVOR_II = RateBracket(
        schedule=TaxSchedule.JOINT_RETURN_OR_SURVIVOR,
        numeral="ii",
        lower=36_900,
        upper=89_150,
        base=5_535,
        rate=0.28,
    )
    """`§ 1(a)(ii) <https://www.law.cornell.edu/uscode/text/26/1#a>`__."""

    JOINT_RETURN_OR_SURVIVOR_III = RateBracket(
        schedule=TaxSchedule.JOINT_RETURN_OR_SURVIVOR,
        numeral="iii",
        lower=89_150,
        upper=140_000,
        base=20_165,
        rate=0.31,
    )
    """`§ 1(a)(iii) <https://www.law.cornell.edu/uscode/text/26/1#a>`__."""

    JOINT_RETURN_OR_SURVIVOR_IV = RateBracket(
        schedule=TaxSchedule.JOINT_RETURN_OR_SURVIVOR,
        numeral="iv",
        lower=140_000,
        upper=250_000,
        base=35928.5,
        rate=0.36,
    )
    """`§ 1(a)(iv) <https://www.law.cornell.edu/uscode/text/26/1#a>`__."""

    JOINT_RETURN_OR_SURVIVOR_V = RateBracket(
        schedule=TaxSchedule.JOINT_RETURN_OR_SURVIVOR,
        numeral="v",
        lower=250_000,
        upper=None,
        base=75528.5,
        rate=0.396,
    )
    """`§ 1(a)(v) <https://www.law.cornell.edu/uscode/text/26/1#a>`__."""

    HEAD_OF_HOUSEHOLD_I = RateBracket(
        schedule=TaxSchedule.HEAD_OF_HOUSEHOLD,
        numeral="i",
        lower=None,
        upper=29_600,
        base=0,
        rate=0.15,
    )
    """`§ 1(b)(i) <https://www.law.cornell.edu/uscode/text/26/1#b>`__."""

    HEAD_OF_HOUSEHOLD_II = RateBracket(
        schedule=TaxSchedule.HEAD_OF_HOUSEHOLD,
        numeral="ii",
        lower=29_600,
        upper=76_400,
        base=4_440,
        rate=0.28,
    )
    """`§ 1(b)(ii) <https://www.law.cornell.edu/uscode/text/26/1#b>`__."""

    HEAD_OF_HOUSEHOLD_III = RateBracket(
        schedule=TaxSchedule.HEAD_OF_HOUSEHOLD,
        numeral="iii",
        lower=76_400,
        upper=127_500,
        base=17_544,
        rate=0.31,
    )
    """`§ 1(b)(iii) <https://www.law.cornell.edu/uscode/text/26/1#b>`__."""

    HEAD_OF_HOUSEHOLD_IV = RateBracket(
        schedule=TaxSchedule.HEAD_OF_HOUSEHOLD,
        numeral="iv",
        lower=127_500,
        upper=250_000,
        base=33_385,
        rate=0.36,
    )
    """`§ 1(b)(iv) <https://www.law.cornell.edu/uscode/text/26/1#b>`__."""

    HEAD_OF_HOUSEHOLD_V = RateBracket(
        schedule=TaxSchedule.HEAD_OF_HOUSEHOLD,
        numeral="v",
        lower=250_000,
        upper=None,
        base=77_485,
        rate=0.396,
    )
    """`§ 1(b)(v) <https://www.law.cornell.edu/uscode/text/26/1#b>`__."""

    UNMARRIED_I = RateBracket(
        schedule=TaxSchedule.UNMARRIED,
        numeral="i",
        lower=None,
        upper=22_100,
        base=0,
        rate=0.15,
    )
    """`§ 1(c)(i) <https://www.law.cornell.edu/uscode/text/26/1#c>`__."""

    UNMARRIED_II = RateBracket(
        schedule=TaxSchedule.UNMARRIED,
        numeral="ii",
        lower=22_100,
        upper=53_500,
        base=3_315,
        rate=0.28,
    )
    """`§ 1(c)(ii) <https://www.law.cornell.edu/uscode/text/26/1#c>`__."""

    UNMARRIED_III = RateBracket(
        schedule=TaxSchedule.UNMARRIED,
        numeral="iii",
        lower=53_500,
        upper=115_000,
        base=12_107,
        rate=0.31,
    )
    """`§ 1(c)(iii) <https://www.law.cornell.edu/uscode/text/26/1#c>`__."""

    UNMARRIED_IV = RateBracket(
        schedule=TaxSchedule.UNMARRIED,
        numeral="iv",
        lower=115_000,
        upper=250_000,
        base=31_172,
        rate=0.36,
    )
    """`§ 1(c)(iv) <https://www.law.cornell.edu/uscode/text/26/1#c>`__."""

    UNMARRIED_V = RateBracket(
        schedule=TaxSchedule.UNMARRIED,
        numeral="v",
        lower=250_000,
        upper=None,
        base=79_772,
        rate=0.396,
    )
    """`§ 1(c)(v) <https://www.law.cornell.edu/uscode/text/26/1#c>`__."""

    SEPARATE_RETURN_I = RateBracket(
        schedule=TaxSchedule.SEPARATE_RETURN,
        numeral="i",
        lower=None,
        upper=18_450,
        base=0,
        rate=0.15,
    )
    """`§ 1(d)(i) <https://www.law.cornell.edu/uscode/text/26/1#d>`__."""

    SEPARATE_RETURN_II = RateBracket(
        schedule=TaxSchedule.SEPARATE_RETURN,
        numeral="ii",
        lower=18_450,
        upper=44_575,
        base=2767.5,
        rate=0.28,
    )
    """`§ 1(d)(ii) <https://www.law.cornell.edu/uscode/text/26/1#d>`__."""

    SEPARATE_RETURN_III = RateBracket(
        schedule=TaxSchedule.SEPARATE_RETURN,
        numeral="iii",
        lower=44_575,
        upper=70_000,
        base=10082.5,
        rate=0.31,
    )
    """`§ 1(d)(iii) <https://www.law.cornell.edu/uscode/text/26/1#d>`__."""

    SEPARATE_RETURN_IV = RateBracket(
        schedule=TaxSchedule.SEPARATE_RETURN,
        numeral="iv",
        lower=70_000,
        upper=125_000,
        base=17964.25,
        rate=0.36,
    )
    """`§ 1(d)(iv) <https://www.law.cornell.edu/uscode/text/26/1#d>`__."""

    SEPARATE_RETURN_V = RateBracket(
        schedule=TaxSchedule.SEPARATE_RETURN,
        numeral="v",
        lower=125_000,
        upper=None,
        base=37764.25,
        rate=0.396,
    )
    """`§ 1(d)(v) <https://www.law.cornell.edu/uscode/text/26/1#d>`__."""


# %% the tax of one bracket


@dataclass
class BracketTaxTest(Provision[BracketTax], ABC):
    """
    The tax a bracket of a rate schedule imposes on each taxable income a goal names
    that falls within it.
    """

    taxable_incomes: list[Real] = field(default_factory=list)
    """The taxable incomes the goal names."""

    @classproperty
    @abstractmethod
    def bracket(cls) -> TaxBracket:
        """
        The bracket.
        """

    @classmethod
    def from_goal(cls, goal: CompoundTerm, world: World) -> Provision:
        """
        Extends :meth:`Provision.from_goal` by the taxable income *goal* names.
        """
        taxable_income = goal.arguments[0]
        return cls(
            world=world,
            taxable_incomes=[taxable_income]
            if isinstance(taxable_income, Real)
            else [],
        )

    def drawn_conclusions_key(self) -> Hashable:
        """
        Extends :meth:`Provision.drawn_conclusions_key` by the taxable incomes asked about.
        """
        return type(self), tuple(self.taxable_incomes)

    def query(self) -> Query:
        taxable_income = variable(Real, domain=self.taxable_incomes)
        return an(
            entity(
                inference(BracketTax)(
                    taxable_income=taxable_income,
                    tax=BracketTaxTest.tax_in_bracket(self, taxable_income),
                )
            ).where(BracketTaxTest.is_in_bracket(self, taxable_income))
        )

    @symbolic_function
    def is_in_bracket(self, taxable_income: Real) -> bool:
        """:return: Whether *taxable_income* falls within the bracket."""
        return self.bracket.value.includes(taxable_income)

    @symbolic_function
    def tax_in_bracket(self, taxable_income: Real) -> int:
        """:return: The tax the bracket imposes on *taxable_income*."""
        return self.bracket.value.tax_on(taxable_income)


@dataclass
class JointReturnOrSurvivorBracketITest(BracketTaxTest):
    """
    `§ 1(a)(i) <https://www.law.cornell.edu/uscode/text/26/1#a>`__: bracket (i) of the rate schedule of a married individual making a joint return or a surviving spouse.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.JOINT_RETURN_OR_SURVIVOR_BRACKET_I`.
        """
        return SaraPredicate.JOINT_RETURN_OR_SURVIVOR_BRACKET_I

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.JOINT_RETURN_OR_SURVIVOR_I`.
        """
        return TaxBracket.JOINT_RETURN_OR_SURVIVOR_I


@dataclass
class JointReturnOrSurvivorBracketIITest(BracketTaxTest):
    """
    `§ 1(a)(ii) <https://www.law.cornell.edu/uscode/text/26/1#a>`__: bracket (ii) of the rate schedule of a married individual making a joint return or a surviving spouse.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.JOINT_RETURN_OR_SURVIVOR_BRACKET_II`.
        """
        return SaraPredicate.JOINT_RETURN_OR_SURVIVOR_BRACKET_II

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.JOINT_RETURN_OR_SURVIVOR_II`.
        """
        return TaxBracket.JOINT_RETURN_OR_SURVIVOR_II


@dataclass
class JointReturnOrSurvivorBracketIIITest(BracketTaxTest):
    """
    `§ 1(a)(iii) <https://www.law.cornell.edu/uscode/text/26/1#a>`__: bracket (iii) of the rate schedule of a married individual making a joint return or a surviving spouse.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.JOINT_RETURN_OR_SURVIVOR_BRACKET_III`.
        """
        return SaraPredicate.JOINT_RETURN_OR_SURVIVOR_BRACKET_III

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.JOINT_RETURN_OR_SURVIVOR_III`.
        """
        return TaxBracket.JOINT_RETURN_OR_SURVIVOR_III


@dataclass
class JointReturnOrSurvivorBracketIVTest(BracketTaxTest):
    """
    `§ 1(a)(iv) <https://www.law.cornell.edu/uscode/text/26/1#a>`__: bracket (iv) of the rate schedule of a married individual making a joint return or a surviving spouse.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.JOINT_RETURN_OR_SURVIVOR_BRACKET_IV`.
        """
        return SaraPredicate.JOINT_RETURN_OR_SURVIVOR_BRACKET_IV

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.JOINT_RETURN_OR_SURVIVOR_IV`.
        """
        return TaxBracket.JOINT_RETURN_OR_SURVIVOR_IV


@dataclass
class JointReturnOrSurvivorBracketVTest(BracketTaxTest):
    """
    `§ 1(a)(v) <https://www.law.cornell.edu/uscode/text/26/1#a>`__: bracket (v) of the rate schedule of a married individual making a joint return or a surviving spouse.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.JOINT_RETURN_OR_SURVIVOR_BRACKET_V`.
        """
        return SaraPredicate.JOINT_RETURN_OR_SURVIVOR_BRACKET_V

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.JOINT_RETURN_OR_SURVIVOR_V`.
        """
        return TaxBracket.JOINT_RETURN_OR_SURVIVOR_V


@dataclass
class HeadOfHouseholdBracketITest(BracketTaxTest):
    """
    `§ 1(b)(i) <https://www.law.cornell.edu/uscode/text/26/1#b>`__: bracket (i) of the rate schedule of a head of household.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HEAD_OF_HOUSEHOLD_BRACKET_I`.
        """
        return SaraPredicate.HEAD_OF_HOUSEHOLD_BRACKET_I

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.HEAD_OF_HOUSEHOLD_I`.
        """
        return TaxBracket.HEAD_OF_HOUSEHOLD_I


@dataclass
class HeadOfHouseholdBracketIITest(BracketTaxTest):
    """
    `§ 1(b)(ii) <https://www.law.cornell.edu/uscode/text/26/1#b>`__: bracket (ii) of the rate schedule of a head of household.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HEAD_OF_HOUSEHOLD_BRACKET_II`.
        """
        return SaraPredicate.HEAD_OF_HOUSEHOLD_BRACKET_II

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.HEAD_OF_HOUSEHOLD_II`.
        """
        return TaxBracket.HEAD_OF_HOUSEHOLD_II


@dataclass
class HeadOfHouseholdBracketIIITest(BracketTaxTest):
    """
    `§ 1(b)(iii) <https://www.law.cornell.edu/uscode/text/26/1#b>`__: bracket (iii) of the rate schedule of a head of household.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HEAD_OF_HOUSEHOLD_BRACKET_III`.
        """
        return SaraPredicate.HEAD_OF_HOUSEHOLD_BRACKET_III

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.HEAD_OF_HOUSEHOLD_III`.
        """
        return TaxBracket.HEAD_OF_HOUSEHOLD_III


@dataclass
class HeadOfHouseholdBracketIVTest(BracketTaxTest):
    """
    `§ 1(b)(iv) <https://www.law.cornell.edu/uscode/text/26/1#b>`__: bracket (iv) of the rate schedule of a head of household.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HEAD_OF_HOUSEHOLD_BRACKET_IV`.
        """
        return SaraPredicate.HEAD_OF_HOUSEHOLD_BRACKET_IV

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.HEAD_OF_HOUSEHOLD_IV`.
        """
        return TaxBracket.HEAD_OF_HOUSEHOLD_IV


@dataclass
class HeadOfHouseholdBracketVTest(BracketTaxTest):
    """
    `§ 1(b)(v) <https://www.law.cornell.edu/uscode/text/26/1#b>`__: bracket (v) of the rate schedule of a head of household.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HEAD_OF_HOUSEHOLD_BRACKET_V`.
        """
        return SaraPredicate.HEAD_OF_HOUSEHOLD_BRACKET_V

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.HEAD_OF_HOUSEHOLD_V`.
        """
        return TaxBracket.HEAD_OF_HOUSEHOLD_V


@dataclass
class UnmarriedBracketITest(BracketTaxTest):
    """
    `§ 1(c)(i) <https://www.law.cornell.edu/uscode/text/26/1#c>`__: bracket (i) of the rate schedule of an unmarried individual.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.UNMARRIED_BRACKET_I`.
        """
        return SaraPredicate.UNMARRIED_BRACKET_I

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.UNMARRIED_I`.
        """
        return TaxBracket.UNMARRIED_I


@dataclass
class UnmarriedBracketIITest(BracketTaxTest):
    """
    `§ 1(c)(ii) <https://www.law.cornell.edu/uscode/text/26/1#c>`__: bracket (ii) of the rate schedule of an unmarried individual.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.UNMARRIED_BRACKET_II`.
        """
        return SaraPredicate.UNMARRIED_BRACKET_II

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.UNMARRIED_II`.
        """
        return TaxBracket.UNMARRIED_II


@dataclass
class UnmarriedBracketIIITest(BracketTaxTest):
    """
    `§ 1(c)(iii) <https://www.law.cornell.edu/uscode/text/26/1#c>`__: bracket (iii) of the rate schedule of an unmarried individual.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.UNMARRIED_BRACKET_III`.
        """
        return SaraPredicate.UNMARRIED_BRACKET_III

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.UNMARRIED_III`.
        """
        return TaxBracket.UNMARRIED_III


@dataclass
class UnmarriedBracketIVTest(BracketTaxTest):
    """
    `§ 1(c)(iv) <https://www.law.cornell.edu/uscode/text/26/1#c>`__: bracket (iv) of the rate schedule of an unmarried individual.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.UNMARRIED_BRACKET_IV`.
        """
        return SaraPredicate.UNMARRIED_BRACKET_IV

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.UNMARRIED_IV`.
        """
        return TaxBracket.UNMARRIED_IV


@dataclass
class UnmarriedBracketVTest(BracketTaxTest):
    """
    `§ 1(c)(v) <https://www.law.cornell.edu/uscode/text/26/1#c>`__: bracket (v) of the rate schedule of an unmarried individual.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.UNMARRIED_BRACKET_V`.
        """
        return SaraPredicate.UNMARRIED_BRACKET_V

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.UNMARRIED_V`.
        """
        return TaxBracket.UNMARRIED_V


@dataclass
class SeparateReturnBracketITest(BracketTaxTest):
    """
    `§ 1(d)(i) <https://www.law.cornell.edu/uscode/text/26/1#d>`__: bracket (i) of the rate schedule of a married individual filing separately.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SEPARATE_RETURN_BRACKET_I`.
        """
        return SaraPredicate.SEPARATE_RETURN_BRACKET_I

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.SEPARATE_RETURN_I`.
        """
        return TaxBracket.SEPARATE_RETURN_I


@dataclass
class SeparateReturnBracketIITest(BracketTaxTest):
    """
    `§ 1(d)(ii) <https://www.law.cornell.edu/uscode/text/26/1#d>`__: bracket (ii) of the rate schedule of a married individual filing separately.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SEPARATE_RETURN_BRACKET_II`.
        """
        return SaraPredicate.SEPARATE_RETURN_BRACKET_II

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.SEPARATE_RETURN_II`.
        """
        return TaxBracket.SEPARATE_RETURN_II


@dataclass
class SeparateReturnBracketIIITest(BracketTaxTest):
    """
    `§ 1(d)(iii) <https://www.law.cornell.edu/uscode/text/26/1#d>`__: bracket (iii) of the rate schedule of a married individual filing separately.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SEPARATE_RETURN_BRACKET_III`.
        """
        return SaraPredicate.SEPARATE_RETURN_BRACKET_III

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.SEPARATE_RETURN_III`.
        """
        return TaxBracket.SEPARATE_RETURN_III


@dataclass
class SeparateReturnBracketIVTest(BracketTaxTest):
    """
    `§ 1(d)(iv) <https://www.law.cornell.edu/uscode/text/26/1#d>`__: bracket (iv) of the rate schedule of a married individual filing separately.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SEPARATE_RETURN_BRACKET_IV`.
        """
        return SaraPredicate.SEPARATE_RETURN_BRACKET_IV

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.SEPARATE_RETURN_IV`.
        """
        return TaxBracket.SEPARATE_RETURN_IV


@dataclass
class SeparateReturnBracketVTest(BracketTaxTest):
    """
    `§ 1(d)(v) <https://www.law.cornell.edu/uscode/text/26/1#d>`__: bracket (v) of the rate schedule of a married individual filing separately.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SEPARATE_RETURN_BRACKET_V`.
        """
        return SaraPredicate.SEPARATE_RETURN_BRACKET_V

    @classproperty
    def bracket(cls) -> TaxBracket:
        """
        :attr:`TaxBracket.SEPARATE_RETURN_V`.
        """
        return TaxBracket.SEPARATE_RETURN_V


# %% income tax by filing status


@dataclass
class JointReturnIncomeTaxTest(Provision[JointReturnIncomeTax]):
    """
    `§ 1(a)(1) <https://www.law.cornell.edu/uscode/text/26/1#a_1>`__: the tax of schedule `(a) <https://www.law.cornell.edu/uscode/text/26/1#a>`__ on a married individual making a joint return
    with their spouse.

    SARA's program excludes nonresident aliens by an event it names ``someone_is_nra``,
    which no case states, so the exclusion is left out.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.JOINT_RETURN_INCOME_TAX`.
        """
        return SaraPredicate.JOINT_RETURN_INCOME_TAX

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        filing = variable(
            JointFiling, domain=JointFilingTest(world=self.world).conclusions
        )
        income = variable(
            TaxableIncome, domain=TaxableIncomeTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(JointReturnIncomeTax)(
                    taxpayer=income.taxpayer,
                    year=income.year,
                    taxable_income=income.amount,
                    tax=TaxSchedule.tax_on(
                        TaxSchedule.JOINT_RETURN_OR_SURVIVOR, income.amount
                    ),
                    joint_return=filing.joint_return,
                    spouse=filing.spouse,
                )
            ).where(filing.individual == income.taxpayer, filing.year == income.year)
        )


@dataclass
class ScheduleIncomeTaxTest(Provision[ConclusionType], ABC):
    """
    The tax of a rate schedule on the taxable income of each taxpayer of a filing status.
    """

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    @classproperty
    @abstractmethod
    def schedule(cls) -> TaxSchedule:
        """
        The rate schedule.
        """

    @abstractmethod
    def taxpayers(self) -> list[TaxpayerOfYear]:
        """:return: The taxpayers of the filing status, each with the year they have it in."""

    def query(self) -> Query:
        conclusion_type = self.get_type_of_generic_parameter(parameter=ConclusionType)
        taxpayer = variable(TaxpayerOfYear, domain=self.taxpayers())
        income = variable(
            TaxableIncome, domain=TaxableIncomeTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(conclusion_type)(
                    taxpayer=income.taxpayer,
                    year=income.year,
                    taxable_income=income.amount,
                    tax=TaxSchedule.tax_on(self.schedule, income.amount),
                )
            ).where(taxpayer.taxpayer == income.taxpayer, taxpayer.year == income.year)
        )


@dataclass(frozen=True)
class TaxpayerOfYear:
    """A taxpayer with a filing status in a calendar year."""

    taxpayer: Party
    """The taxpayer."""

    year: int
    """The calendar year."""


@dataclass
class SurvivorIncomeTaxTest(ScheduleIncomeTaxTest[SurvivorIncomeTax]):
    """
    `§ 1(a)(2) <https://www.law.cornell.edu/uscode/text/26/1#a_2>`__: the tax of schedule `(a) <https://www.law.cornell.edu/uscode/text/26/1#a>`__ on a surviving spouse.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SURVIVOR_INCOME_TAX`.
        """
        return SaraPredicate.SURVIVOR_INCOME_TAX

    @classproperty
    def schedule(cls) -> TaxSchedule:
        """
        :attr:`TaxSchedule.JOINT_RETURN_OR_SURVIVOR`.
        """
        return TaxSchedule.JOINT_RETURN_OR_SURVIVOR

    def taxpayers(self) -> list[TaxpayerOfYear]:
        return [
            TaxpayerOfYear(taxpayer=survivor.taxpayer, year=survivor.year)
            for survivor in SurvivingSpouseTest(world=self.world).conclusions
        ]


@dataclass
class HeadOfHouseholdIncomeTaxTest(ScheduleIncomeTaxTest[HeadOfHouseholdIncomeTax]):
    """
    `§ 1(b) <https://www.law.cornell.edu/uscode/text/26/1#b>`__: the tax of schedule `(b) <https://www.law.cornell.edu/uscode/text/26/1#b>`__ on a head of household.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HEAD_OF_HOUSEHOLD_INCOME_TAX`.
        """
        return SaraPredicate.HEAD_OF_HOUSEHOLD_INCOME_TAX

    @classproperty
    def schedule(cls) -> TaxSchedule:
        """
        :attr:`TaxSchedule.HEAD_OF_HOUSEHOLD`.
        """
        return TaxSchedule.HEAD_OF_HOUSEHOLD

    def taxpayers(self) -> list[TaxpayerOfYear]:
        return [
            TaxpayerOfYear(taxpayer=head.taxpayer, year=head.year)
            for head in HeadOfHouseholdTest(world=self.world).conclusions
        ]


@dataclass
class UnmarriedIncomeTaxTest(ScheduleIncomeTaxTest[UnmarriedIncomeTax]):
    """
    `§ 1(c) <https://www.law.cornell.edu/uscode/text/26/1#c>`__: the tax of schedule `(c) <https://www.law.cornell.edu/uscode/text/26/1#c>`__ on an individual not married, no surviving spouse
    and no head of household.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.UNMARRIED_INCOME_TAX`.
        """
        return SaraPredicate.UNMARRIED_INCOME_TAX

    @classproperty
    def schedule(cls) -> TaxSchedule:
        """
        :attr:`TaxSchedule.UNMARRIED`.
        """
        return TaxSchedule.UNMARRIED

    def taxpayers(self) -> list[TaxpayerOfYear]:
        taxpayer = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.calendar_years)
        married = variable(
            MarriedIndividual,
            domain=MarriedIndividualTest(world=self.world).conclusions,
        )
        survivor = variable(
            SurvivingSpouse, domain=SurvivingSpouseTest(world=self.world).conclusions
        )
        head = variable(
            HeadOfHousehold, domain=HeadOfHouseholdTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(TaxpayerOfYear)(taxpayer=taxpayer, year=year.number)
            ).where(
                not_(
                    exists(
                        married,
                        and_(married.person == taxpayer, married.year == year.number),
                    )
                ),
                not_(
                    exists(
                        survivor,
                        and_(
                            survivor.taxpayer == taxpayer, survivor.year == year.number
                        ),
                    )
                ),
                not_(
                    exists(
                        head, and_(head.taxpayer == taxpayer, head.year == year.number)
                    )
                ),
            )
        ).tolist()


@dataclass
class SeparateReturnIncomeTaxTest(Provision[SeparateReturnIncomeTax]):
    """
    `§ 1(d) <https://www.law.cornell.edu/uscode/text/26/1#d>`__: the tax of schedule `(d) <https://www.law.cornell.edu/uscode/text/26/1#d>`__ on a married individual making no joint return
    with their spouse.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SEPARATE_RETURN_INCOME_TAX`.
        """
        return SaraPredicate.SEPARATE_RETURN_INCOME_TAX

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        married = variable(
            MarriedIndividual,
            domain=MarriedIndividualTest(world=self.world).separate_filers(),
        )
        income = variable(
            TaxableIncome, domain=TaxableIncomeTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(SeparateReturnIncomeTax)(
                    taxpayer=income.taxpayer,
                    year=income.year,
                    taxable_income=income.amount,
                    tax=TaxSchedule.tax_on(TaxSchedule.SEPARATE_RETURN, income.amount),
                    spouse=married.spouse,
                )
            ).where(married.person == income.taxpayer, married.year == income.year)
        )


@dataclass
class IncomeTaxUnionTest(Provision[ConclusionType], ABC):
    """
    The income tax of any of several provisions, as one conclusion of this provision's kind.
    """

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    @abstractmethod
    def taxes(self) -> list[IncomeTax]:
        """:return: The income taxes of the provisions united."""

    def query(self) -> Query:
        conclusion_type = self.get_type_of_generic_parameter(parameter=ConclusionType)
        tax = variable(IncomeTax, domain=self.taxes())
        return an(
            entity(
                inference(conclusion_type)(
                    taxpayer=tax.taxpayer,
                    year=tax.year,
                    taxable_income=tax.taxable_income,
                    tax=tax.tax,
                )
            )
        )


@dataclass
class JointReturnOrSurvivorIncomeTaxTest(
    IncomeTaxUnionTest[JointReturnOrSurvivorIncomeTax]
):
    """
    `§ 1(a) <https://www.law.cornell.edu/uscode/text/26/1#a>`__: the tax on a married individual making a joint return `(1) <https://www.law.cornell.edu/uscode/text/26/1#a_1>`__ or a surviving spouse
    `(2) <https://www.law.cornell.edu/uscode/text/26/1#a_2>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.JOINT_RETURN_OR_SURVIVOR_INCOME_TAX`.
        """
        return SaraPredicate.JOINT_RETURN_OR_SURVIVOR_INCOME_TAX

    def taxes(self) -> list[IncomeTax]:
        return (
            JointReturnIncomeTaxTest(world=self.world).conclusions
            + SurvivorIncomeTaxTest(world=self.world).conclusions
        )


@dataclass
class IncomeTaxTest(IncomeTaxUnionTest[TotalIncomeTax]):
    """
    `§ 1 <https://www.law.cornell.edu/uscode/text/26/1>`__: the tax of any of `(a) <https://www.law.cornell.edu/uscode/text/26/1#a>`__ to `(d) <https://www.law.cornell.edu/uscode/text/26/1#d>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.INCOME_TAX`.
        """
        return SaraPredicate.INCOME_TAX

    def taxes(self) -> list[IncomeTax]:
        return [
            tax
            for test in (
                JointReturnOrSurvivorIncomeTaxTest,
                HeadOfHouseholdIncomeTaxTest,
                UnmarriedIncomeTaxTest,
                SeparateReturnIncomeTaxTest,
            )
            for tax in test(world=self.world).conclusions
        ]


# %% tax owed


@dataclass
class TaxOwedTest(Provision[TaxOwed]):
    """
    SARA's ``tax``: the income tax of `§ 1 <https://www.law.cornell.edu/uscode/text/26/1>`__ plus the employment tax of `§ 3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__, each
    zero where it does not apply.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.TAX_OWED`.
        """
        return SaraPredicate.TAX_OWED

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        taxed = variable(
            TaxOwed,
            domain=[
                tax
                for owes_income_tax in (True, False)
                for owes_employment_tax in (True, False)
                for tax in self.taxes_owed(owes_income_tax, owes_employment_tax)
            ],
        )
        return an(entity(taxed))

    def taxes_owed(
        self, owes_income_tax: bool, owes_employment_tax: bool
    ) -> list[TaxOwed]:
        """:return: The tax of each person who owes, or does not owe, income tax and employment tax."""
        person = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.calendar_years)
        income_tax = variable(
            TotalIncomeTax, domain=IncomeTaxTest(world=self.world).conclusions
        )
        employment_tax = variable(
            ExciseTax, domain=ExciseTaxOnEmployer(world=self.world).conclusions
        )
        owes_income = and_(
            income_tax.taxpayer == person, income_tax.year == year.number
        )
        owes_employment = and_(
            employment_tax.employer == person, employment_tax.year == year.number
        )
        conditions = [
            owes_income if owes_income_tax else not_(exists(income_tax, owes_income)),
            owes_employment
            if owes_employment_tax
            else not_(exists(employment_tax, owes_employment)),
        ]
        return an(
            entity(
                inference(TaxOwed)(
                    person=person,
                    year=year.number,
                    amount=(income_tax.tax if owes_income_tax else 0)
                    + (employment_tax.amount if owes_employment_tax else 0),
                )
            ).where(*conditions)
        ).tolist()
