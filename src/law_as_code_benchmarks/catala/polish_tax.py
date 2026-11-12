"""
The rates of the Polish tax on civil-law transactions (*podatek od czynności
cywilnoprawnych*) of article 7, paragraph 1, as Catala's ``polish_taxes`` example
states them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from pathlib import Path

from krrood.entity_query_language.factories import (
    add,
    alternative,
    an,
    deduced_variable,
    entity,
    in_,
    inference,
    variable,
)
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import CatalaDirectory, CatalaValue
from law_as_code_benchmarks.catala.scope_test import (
    CaseAmount,
    CaseFraction,
    ScopeCase,
    ScopeProvision,
    ScopeTestFile,
)

# %% transactions


class TransactionKind(StrEnum):
    """The transactions article 7, paragraph 1 sets a rate for, each named as Catala's scope for it."""

    SALE = "UmowaSprzedaży"
    """1) A contract of sale."""

    EXCHANGE_OR_DONATION = "UmowaZamianyLubDarowizny"
    """2) A contract of exchange, life annuity, division of an inheritance or of co-ownership, or a donation."""

    PAID_USUFRUCT = "OdpłatneUżytkowanie"
    """3) A contract establishing a paid usufruct or a paid easement."""

    LOAN_OR_IRREGULAR_DEPOSIT = "PożyczkaLubDepozytNieprawidłowy"
    """4) A loan or an irregular deposit."""

    MORTGAGE = "Hipoteka"
    """7) The establishment of a mortgage."""

    PARTNERSHIP_AGREEMENT = "UmowaSpółki"
    """9) A partnership agreement."""


class TransactionOutput(StrEnum):
    """The outputs of the scopes of article 7."""

    TAX = "podatek"
    """The tax owed."""


@dataclass(eq=False)
class TransactionCase(ScopeCase, ABC):
    """A civil-law transaction, one of the scopes of article 7, paragraph 1."""

    amount: Money = field(default_factory=lambda: Money.zero)
    """The amount the tax is levied on."""

    other_property_rights: bool = False
    """Whether a sale or transfer is of other property rights than those of a)."""

    undetermined_claim: bool = False
    """Whether a mortgage secures a claim of undetermined amount."""

    @classproperty
    @abstractmethod
    def transaction_kind(cls) -> TransactionKind:
        """The kind of transaction."""

    @classproperty
    def catala_scope(cls) -> str:
        """The scope of the kind of transaction."""
        return cls.transaction_kind.value

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scopes of article 7."""
        return {
            "kwota": "amount",
            "inne_prawa_majątkowe": "other_property_rights",
            "wysokość_nieustalona": "undetermined_claim",
        }

    def output(self, variable: str) -> CatalaValue:
        match TransactionOutput(variable):
            case TransactionOutput.TAX:
                return self.sole_conclusion(TaxProvision).amount


@dataclass(eq=False)
class SaleCase(TransactionCase):
    """1) A contract of sale."""

    @classproperty
    def transaction_kind(cls) -> TransactionKind:
        """:attr:`TransactionKind.SALE`."""
        return TransactionKind.SALE


@dataclass(eq=False)
class ExchangeOrDonationCase(TransactionCase):
    """2) A contract of exchange or a donation, among others."""

    @classproperty
    def transaction_kind(cls) -> TransactionKind:
        """:attr:`TransactionKind.EXCHANGE_OR_DONATION`."""
        return TransactionKind.EXCHANGE_OR_DONATION


@dataclass(eq=False)
class PaidUsufructCase(TransactionCase):
    """3) A paid usufruct or easement."""

    @classproperty
    def transaction_kind(cls) -> TransactionKind:
        """:attr:`TransactionKind.PAID_USUFRUCT`."""
        return TransactionKind.PAID_USUFRUCT


@dataclass(eq=False)
class LoanOrIrregularDepositCase(TransactionCase):
    """4) A loan or an irregular deposit."""

    @classproperty
    def transaction_kind(cls) -> TransactionKind:
        """:attr:`TransactionKind.LOAN_OR_IRREGULAR_DEPOSIT`."""
        return TransactionKind.LOAN_OR_IRREGULAR_DEPOSIT


@dataclass(eq=False)
class MortgageCase(TransactionCase):
    """7) The establishment of a mortgage."""

    @classproperty
    def transaction_kind(cls) -> TransactionKind:
        """:attr:`TransactionKind.MORTGAGE`."""
        return TransactionKind.MORTGAGE


@dataclass(eq=False)
class PartnershipAgreementCase(TransactionCase):
    """9) A partnership agreement."""

    @classproperty
    def transaction_kind(cls) -> TransactionKind:
        """:attr:`TransactionKind.PARTNERSHIP_AGREEMENT`."""
        return TransactionKind.PARTNERSHIP_AGREEMENT


# %% conclusions


@dataclass(eq=False)
class TaxRate(CaseFraction):
    """Article 7, paragraph 1: the rate of the tax on the transaction."""


@dataclass(eq=False)
class Tax(CaseAmount):
    """The tax owed on the transaction."""


# %% provisions


@dataclass
class TaxRateProvision(ScopeProvision[TaxRate]):
    """
    Article 7, paragraph 1: 2 % on a sale (1a) or a transfer (2a), 1 % where it is of
    other property rights (1b, 2b); 1 % on a paid usufruct (3), 0.5 % on a loan or
    irregular deposit (4) and on a partnership agreement (9), 0.1 % on a mortgage (7a).
    """

    def query(self) -> Query:
        case = variable(type(self.case), domain=[self.case])
        transfers = {TransactionKind.SALE, TransactionKind.EXCHANGE_OR_DONATION}
        rate = deduced_variable(TaxRate)
        query = an(
            entity(rate).where(
                in_(case.transaction_kind, transfers),
                case.other_property_rights == True,
            )
        )
        with query:
            add(rate, inference(TaxRate)(case=case, fraction=Fraction(1, 100)))
            with alternative(in_(case.transaction_kind, transfers)):
                add(rate, inference(TaxRate)(case=case, fraction=Fraction(2, 100)))
            with alternative(case.transaction_kind == TransactionKind.PAID_USUFRUCT):
                add(rate, inference(TaxRate)(case=case, fraction=Fraction(1, 100)))
            with alternative(
                in_(
                    case.transaction_kind,
                    {
                        TransactionKind.LOAN_OR_IRREGULAR_DEPOSIT,
                        TransactionKind.PARTNERSHIP_AGREEMENT,
                    },
                )
            ):
                add(rate, inference(TaxRate)(case=case, fraction=Fraction(5, 1000)))
            with alternative(case.transaction_kind == TransactionKind.MORTGAGE):
                add(rate, inference(TaxRate)(case=case, fraction=Fraction(1, 1000)))
        return query


@dataclass
class TaxProvision(ScopeProvision[Tax]):
    """
    The amount times the rate; 7b) sets 19 zł on a mortgage securing a claim of
    undetermined amount.
    """

    @classproperty
    def undetermined_mortgage_tax(cls) -> Money:
        """The tax on a mortgage securing a claim of undetermined amount, 19 zł."""
        return Money.from_euros(19)

    def query(self) -> Query:
        rate = variable(TaxRate, domain=TaxRateProvision(case=self.case).conclusions)
        case = variable(type(self.case), domain=[self.case])
        tax = deduced_variable(Tax)
        query = an(
            entity(tax).where(
                case.transaction_kind == TransactionKind.MORTGAGE,
                case.undetermined_claim == True,
            )
        )
        with query:
            add(tax, inference(Tax)(case=case, amount=self.undetermined_mortgage_tax))
            with alternative():
                add(tax, inference(Tax)(case=case, amount=case.amount * rate.fraction))
        return query


# %% test files


class PolishTaxTestFile(ScopeTestFile, StrEnum):
    """The test files of Catala's ``polish_taxes`` example, each named after the point of article 7, paragraph 1 it tests."""

    SALE = "test_a7_u1_p1.catala_pl"
    """Point 1."""

    EXCHANGE_OR_DONATION = "test_a7_u1_p2.catala_pl"
    """Point 2."""

    PAID_USUFRUCT = "test_a7_u1_p3.catala_pl"
    """Point 3."""

    LOAN_OR_IRREGULAR_DEPOSIT = "test_a7_u1_p4.catala_pl"
    """Point 4."""

    MORTGAGE = "test_a7_u1_p7.catala_pl"
    """Point 7, which tests a loan, as the example's file does."""

    PARTNERSHIP_AGREEMENT = "test_a7_u1_p9.catala_pl"
    """Point 9."""

    @property
    def directory(self) -> Path:
        """:file:`polish_taxes/tests`."""
        return CatalaDirectory.ROOT / "polish_taxes" / "tests"

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """Every kind of transaction."""
        return [
            SaleCase,
            ExchangeOrDonationCase,
            PaidUsufructCase,
            LoanOrIrregularDepositCase,
            MortgageCase,
            PartnershipAgreementCase,
        ]
