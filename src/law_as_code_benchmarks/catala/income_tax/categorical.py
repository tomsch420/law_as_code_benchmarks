"""
What the categories of profits share: the short-term capital gains of 39 quaterdecies
and the levy on long-term ones of 39 quindecies, and the imputation of a categorical
deficit on the quotient incomes of 156 (Catala's
``ImputationDéficitSurRevenusQuotientés``).
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.catala.income_tax.exceptional_income import QuotientIncome
from law_as_code_benchmarks.catala.income_tax.oracles import ProportionalDistribution
from law_as_code_benchmarks.catala.money import Money

# %% capital gains


@dataclass(frozen=True)
class CapitalGains:
    """
    Net capital gains and losses.
    """

    gains: Money
    """
    The net gains.
    """

    losses: Money
    """
    The net losses.
    """

    @classproperty
    def long_term_rate(cls) -> Fraction:
        """
        39 quindecies: 12.8 %.
        """
        return Fraction(128, 1000)

    @property
    def short_term_balance(self) -> Money:
        """
        39 quaterdecies: the gains less the losses.
        """
        return self.gains - self.losses

    @property
    def long_term_levy(self) -> Money:
        """
        39 quindecies and 193: 12.8 % of the gains beyond the losses, rounded to the
        euro.
        """
        return (
            max(self.gains - self.losses, Money.zero) * self.long_term_rate
        ).rounded_to_units()


# %% deficits on quotient incomes


@dataclass(frozen=True)
class QuotientDeficitImputation:
    """
    156: a categorical deficit imputed on the quotient incomes of the category, at most
    their net amounts, and shared between them in proportion, rounded to the euro.
    """

    balance: Money
    """
    The category's balance, a deficit where negative.
    """

    quotient_incomes: list[list[QuotientIncome]]
    """
    The quotient incomes of the category, by declarant.
    """

    @property
    def imputed_deficit(self) -> Money:
        """
        The deficit imputed: none for a profit, the net quotient incomes at most.
        """
        if self.balance >= Money.zero:
            return Money.zero
        basis = sum(
            (
                income.net_amount
                for incomes in self.quotient_incomes
                for income in incomes
            ),
            Money.zero,
        )
        return min(Money.zero - self.balance, basis)

    @property
    def imputed_incomes(self) -> list[list[QuotientIncome]]:
        """
        The quotient incomes, each less its share of the deficit.
        """
        shares = ProportionalDistribution.list_shares(
            self.imputed_deficit,
            [
                [income.net_amount for income in incomes]
                for incomes in self.quotient_incomes
            ],
        )
        return [
            [
                QuotientIncome(
                    net_amount=income.net_amount - share,
                    deduction=income.deduction,
                    coefficient=income.coefficient,
                    category=income.category,
                )
                for income, share in zip(incomes, declarant_shares)
            ]
            for incomes, declarant_shares in zip(self.quotient_incomes, shares)
        ]
