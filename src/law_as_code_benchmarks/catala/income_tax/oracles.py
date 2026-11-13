"""
The external functions of Catala's ``impot_revenu`` example, which its module
``Oracles`` declares and its OCaml implementation computes: the imputation of past
deficits, oldest first, and the distribution of an amount in proportion, rounded to the euro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction

from krrood.ormatic.utils import classproperty
from typing_extensions import Self

from law_as_code_benchmarks.catala.income_tax.exceptions import UndistributableAmount
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import (
    CatalaValue,
    Reference,
    StructureLiteral,
)
from law_as_code_benchmarks.catala.scope_test import (
    CatalaRecord,
    ScopeCase,
)
from law_as_code_benchmarks.law.rounding import Rounding

# %% past deficits


@dataclass(eq=False)
class PastDeficit(CatalaRecord):
    """A deficit of a past year still to be imputed, Catala's ``Oracles.DéficitAntérieur``."""

    year: int
    """The year of the deficit."""

    amount: Money
    """What remains of it."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``DéficitAntérieur``."""
        return {"année": "year", "valeur": "amount"}

    def to_catala(self) -> StructureLiteral:
        """:return: The deficit as Catala prints it."""
        return StructureLiteral(
            structure=Reference(parts=("DéficitAntérieur",)),
            fields={"année": self.year, "valeur": self.amount},
        )


@dataclass(frozen=True)
class DeficitImputation:
    """The income left and the deficits remaining once the income is imputed on the oldest deficits first."""

    imputed_income: Money
    """The income left after the imputation."""

    remaining_deficits: list[PastDeficit] = field(default_factory=list)
    """The deficits left, oldest first."""

    @classmethod
    def from_income(cls, income: Money, deficits: list[PastDeficit]) -> Self:
        """:return: *income* imputed on *deficits*, oldest first, as ``imputation_aux_déficits_les_plus_anciens`` does."""
        remaining = sorted(deficits, key=lambda deficit: deficit.year)
        while remaining:
            oldest, *rest = remaining
            if oldest.amount > income:
                return cls(
                    imputed_income=Money.zero,
                    remaining_deficits=[
                        PastDeficit(year=oldest.year, amount=oldest.amount - income),
                        *rest,
                    ],
                )
            income = income - oldest.amount
            remaining = rest
        return cls(imputed_income=income)


class DeficitImputationOutput(StrEnum):
    """The outputs of ``ImputationAuxDéficitsLesPlusAnciens``."""

    IMPUTED_INCOME = "revenu_imputé"
    """The income left."""

    REMAINING_DEFICITS = "déficits_antérieurs_restants"
    """The deficits left."""


@dataclass(eq=False)
class DeficitImputationCase(ScopeCase):
    """The inputs of the imputation on past deficits, Catala's ``ImputationAuxDéficitsLesPlusAnciens``."""

    declared_income: Money
    """The income declared."""

    past_deficits: list[PastDeficit]
    """The deficits of past years still to be imputed."""

    @classproperty
    def catala_scope(cls) -> str:
        """``ImputationAuxDéficitsLesPlusAnciens``."""
        return "ImputationAuxDéficitsLesPlusAnciens"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "revenu_déclaré": "declared_income",
            "déficits_antérieurs": "past_deficits",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`DeficitImputationOutput`."""
        return DeficitImputationOutput

    def output(self, variable: str) -> CatalaValue:
        imputation = DeficitImputation.from_income(
            self.declared_income, self.past_deficits
        )
        match DeficitImputationOutput(variable):
            case DeficitImputationOutput.IMPUTED_INCOME:
                return imputation.imputed_income
            case DeficitImputationOutput.REMAINING_DEFICITS:
                return [
                    deficit.to_catala() for deficit in imputation.remaining_deficits
                ]


# %% distributing in proportion


class RoundingDirection(StrEnum):
    """How a share was rounded to the euro."""

    UP = "Haut"
    """Up."""

    DOWN = "Bas"
    """Down."""

    NONE = "Nul"
    """Not at all, the share being whole."""


@dataclass(frozen=True)
class RoundedShare:
    """A share rounded to the euro, and how it was rounded."""

    amount: Money
    """The share rounded."""

    direction: RoundingDirection
    """How it was rounded."""


@dataclass(frozen=True)
class ProportionalDistribution:
    """
    An amount of whole euros distributed in proportion to bases, each share rounded to
    the euro and the rounding differences evened out, as ``prorata_arrondi_euro`` does.
    """

    amount: Money
    """The amount distributed."""

    bases: list[Money]
    """The bases of the proportion."""

    def shares(self) -> list[Money]:
        """
        :return: The shares, in the order of the bases.
        :raises UndistributableAmount: Where a base is negative, every base is nothing
            while the amount is something, or the amount has cents.
        """
        self.check()
        rounded = self.rounded_shares()
        ups = sum(share.direction == RoundingDirection.UP for share in rounded)
        downs = sum(share.direction == RoundingDirection.DOWN for share in rounded)
        delta = (
            sum((share.amount for share in rounded), Money.zero) - self.amount
        ).cents // 100
        since_last_flip = 1
        shares = []
        for share in rounded:
            flip, waited = self.flip_for(
                share.direction, delta, ups, downs, since_last_flip
            )
            ups -= share.direction == RoundingDirection.UP
            downs -= share.direction == RoundingDirection.DOWN
            shares.append(share.amount + Money.from_euros(flip))
            delta += flip
            since_last_flip = 1 if flip else since_last_flip + waited
        return shares

    @staticmethod
    def flip_for(
        direction: RoundingDirection,
        delta: int,
        ups_left: int,
        downs_left: int,
        since_last_flip: int,
    ) -> tuple[int, int]:
        """
        :return: The euro a share's rounding is turned by, and whether the wait since the
            last turn grows: a share rounded the way the remaining difference runs is
            turned once enough shares passed for those left to even the rest out.
        """
        if delta == 0:
            return 0, 1
        if delta < 0 and direction == RoundingDirection.DOWN:
            return (1, 0) if -delta * since_last_flip > downs_left else (0, 1)
        if delta > 0 and direction == RoundingDirection.UP:
            return (-1, 0) if delta * since_last_flip > ups_left else (0, 1)
        return 0, 0

    @classmethod
    def list_shares(cls, amount: Money, bases: list[list[Money]]) -> list[list[Money]]:
        """:return: *amount* distributed over every base of *bases* at once, the shares split back into the lists, as ``prorata_arrondi_euro_listes`` does."""
        shares = cls(
            amount=amount, bases=[base for row in bases for base in row]
        ).shares()
        split, start = [], 0
        for row in bases:
            split.append(shares[start : start + len(row)])
            start += len(row)
        return split

    def check(self) -> None:
        """
        :raises UndistributableAmount: Where the oracle's assertions fail.
        """
        if any(base < Money.zero for base in self.bases):
            raise UndistributableAmount(amount=self.amount, bases=self.bases)
        if self.amount != Money.zero and all(base == Money.zero for base in self.bases):
            raise UndistributableAmount(amount=self.amount, bases=self.bases)
        if self.amount.rounded_to_units() != self.amount:
            raise UndistributableAmount(amount=self.amount, bases=self.bases)

    def rounded_shares(self) -> list[RoundedShare]:
        """:return: Each base's exact share of the amount, rounded to the euro, halves away from zero."""
        total = sum((base for base in self.bases), Money.zero)
        rounded = []
        for base in self.bases:
            exact = (
                Fraction(0)
                if total == Money.zero
                else Fraction(self.amount.cents, 100) * (base / total)
            )
            whole = int(Rounding.round_half_away_from_zero(exact))
            direction = (
                RoundingDirection.NONE
                if whole == exact
                else RoundingDirection.UP
                if whole > exact
                else RoundingDirection.DOWN
            )
            rounded.append(
                RoundedShare(amount=Money.from_euros(whole), direction=direction)
            )
        return rounded


class ProportionalDistributionOutput(StrEnum):
    """The output of the scope ``ProRataArrondiEuro`` the tests of the prorata declare."""

    SHARES = "valeurs_proratisées"
    """The shares."""


@dataclass(eq=False)
class ProportionalDistributionCase(ScopeCase):
    """The inputs of the scope ``ProRataArrondiEuro`` the tests of the prorata declare, which calls ``prorata_arrondi_euro``."""

    amount: Money
    """The amount distributed."""

    bases: list[Money]
    """The bases of the proportion."""

    @classproperty
    def catala_scope(cls) -> str:
        """``ProRataArrondiEuro``."""
        return "ProRataArrondiEuro"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {"montant_à_distribuer": "amount", "bases_prorata": "bases"}

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`ProportionalDistributionOutput`."""
        return ProportionalDistributionOutput

    def output(self, variable: str) -> CatalaValue:
        return ProportionalDistribution(amount=self.amount, bases=self.bases).shares()
