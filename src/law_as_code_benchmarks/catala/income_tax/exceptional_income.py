"""
The exceptional or deferred income of article 163-0 A of the Code général des impôts,
taxed by the quotient, which every category of income declares alike.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from krrood.ormatic.utils import classproperty
from typing_extensions import Self

from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import (
    CatalaValue,
    ConstructorWithContent,
    Reference,
    StructureLiteral,
)
from law_as_code_benchmarks.catala.scope_test import CatalaRecord, CatalaVariant

# %% exceptional and deferred income


class IncomeKind(StrEnum):
    """The categories of exceptional or deferred income, each named as Catala's ``CatégorieRevenuExceptionnelOuDifféré``."""

    WAGES = "TraitementsSalaires"
    """Wages and salaries."""

    LIFE_ANNUITY = "RenteViagèreOnéreux"
    """A life annuity acquired for consideration."""

    PENSIONS = "PensionsRetraitesRentes"
    """Pensions, retirement pensions and annuities."""

    NON_COMMERCIAL = "BénéficesNonCommerciaux"
    """Non-commercial profits."""

    MICRO_NON_COMMERCIAL = "MicroBénéficesNonCommerciaux"
    """Non-commercial profits of the micro regime."""

    COMMERCIAL = "BénéficesIndustrielsCommerciaux"
    """Industrial and commercial profits."""

    FURNISHED_LETTING = "BénéficesIndustrielsCommerciauxLocationMeublées"
    """Industrial and commercial profits of furnished letting."""

    MICRO_GOODS = "MicroBénéficesIndustrielsCommerciauxMarchandises"
    """Micro profits of selling goods."""

    MICRO_SERVICES = "MicroBénéficesIndustrielsCommerciauxServices"
    """Micro profits of services."""

    MICRO_FURNISHED_LETTING = (
        "MicroBénéficesIndustrielsCommerciauxLocationsMeubléesGénéral"
    )
    """Micro profits of furnished letting."""

    MICRO_CLASSIFIED_LETTING = (
        "MicroBénéficesIndustrielsCommerciauxLocationsMeubléesHôtesClassées"
    )
    """Micro profits of classified guest letting."""

    MICRO_RURAL_LETTING = (
        "MicroBénéficesIndustrielsCommerciauxLocationsMeubléesRuralesSpéciales"
    )
    """Micro profits of special rural letting."""


class AnnuityAge(StrEnum):
    """The age the annuitant was when a life annuity began, each named as Catala's ``CatégorieRenteViagèreOnéreux``."""

    UNDER_50 = "RenteViagèreOnéreuxMoins49Ans"
    """Under 50."""

    FROM_50_TO_59 = "RenteViagèreOnéreuxEntre50Et59Ans"
    """From 50 to 59."""

    FROM_60_TO_69 = "RenteViagèreOnéreuxEntre60Et69Ans"
    """From 60 to 69."""

    FROM_70 = "RenteViagèreOnéreuxPlus70Ans"
    """From 70."""


@dataclass(eq=False)
class IncomeCategory(CatalaVariant):
    """The category of an exceptional or deferred income, with the age of a life annuity."""

    kind: IncomeKind = IncomeKind.WAGES
    """The category."""

    annuity_age: AnnuityAge | None = None
    """The age of a life annuity; None for any other category."""

    @classmethod
    def from_constructor(cls, value: ConstructorWithContent | Reference) -> Self:
        """Overrides :meth:`CatalaVariant.from_constructor`: every constructor maps onto this class, a life annuity's age kept."""
        if isinstance(value, ConstructorWithContent):
            return cls(
                kind=IncomeKind(value.constructor.last_part),
                annuity_age=AnnuityAge(value.content.last_part),
            )
        return cls(kind=IncomeKind(value.last_part))

    def to_catala(self) -> CatalaValue:
        """:return: The category as Catala prints it."""
        if self.annuity_age is None:
            return Reference(parts=(self.kind.value,))
        return ConstructorWithContent(
            constructor=Reference(parts=(self.kind.value,)),
            content=Reference(parts=(self.annuity_age.value,)),
        )


class IncomeRegime(StrEnum):
    """The regime of an exceptional or deferred income, each named as Catala's ``RégimeRevenuExceptionnelOuDifféré``."""

    ARTICLE_163_0_A = "Article163_0_A"
    """Article 163-0 A."""

    ARTICLE_163_0_A_BIS = "Article163_0_A_bis"
    """Article 163-0 A bis."""


@dataclass(eq=False)
class IncomeTerm(CatalaVariant):
    """Whether an income is exceptional or deferred, Catala's ``ÉchéanceRevenuExceptionnelOuDifféré``."""


@dataclass(eq=False)
class ExceptionalIncomeTerm(IncomeTerm):
    """An exceptional income, ``RevenuExceptionnel``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``RevenuExceptionnel``."""
        return "RevenuExceptionnel"


@dataclass(eq=False)
class DeferredIncomeTerm(IncomeTerm):
    """A deferred income, ``RevenuDifféréÉchéanceNormale``, with the year it was normally due."""

    due_year: int = 0
    """The year it was normally due."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``RevenuDifféréÉchéanceNormale``."""
        return "RevenuDifféréÉchéanceNormale"

    @classproperty
    def content_field(cls) -> str:
        """The year due."""
        return "due_year"


@dataclass(eq=False)
class ExceptionalIncome(CatalaRecord):
    """An exceptional or deferred income, Catala's ``RevenuExceptionnelOuDifféré``."""

    amount: Money
    """The income."""

    regime: IncomeRegime
    """Its regime."""

    term: IncomeTerm
    """Whether it is exceptional or deferred."""

    category: IncomeCategory
    """Its category."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``RevenuExceptionnelOuDifféré``."""
        return {
            "valeur": "amount",
            "régime": "regime",
            "échéance": "term",
            "catégorie": "category",
        }


@dataclass(frozen=True)
class QuotientIncome:
    """An income taxed by the quotient of 163-0 A, Catala's ``RevenuQuotienté``."""

    net_amount: Money
    """The income less its deduction."""

    deduction: Money
    """The deduction."""

    coefficient: int
    """The coefficient of the quotient."""

    category: IncomeCategory
    """Its category."""

    @classmethod
    def from_income(
        cls, income: ExceptionalIncome, deduction: Money, year: int
    ) -> Self:
        """
        :return: *income* with *deduction*, as ``CalculRevenuQuotienté`` computes it: a
            coefficient of 4 for an exceptional income; for a deferred one, the years since
            it was due and one more, but under 163-0 A bis.
        """
        term = income.term
        if isinstance(term, DeferredIncomeTerm):
            shift = 0 if income.regime == IncomeRegime.ARTICLE_163_0_A_BIS else 1
            coefficient = year - term.due_year + shift
        else:
            coefficient = 4
        return cls(
            net_amount=income.amount - deduction,
            deduction=deduction,
            coefficient=coefficient,
            category=income.category,
        )

    def to_catala(self) -> StructureLiteral:
        """:return: The income as Catala prints it."""
        return StructureLiteral(
            structure=Reference(parts=("RevenuQuotienté",)),
            fields={
                "valeur_nette": self.net_amount,
                "déduction": self.deduction,
                "coefficient": self.coefficient,
                "catégorie": self.category.to_catala(),
            },
        )
