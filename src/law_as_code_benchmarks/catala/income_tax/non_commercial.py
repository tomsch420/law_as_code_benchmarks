"""
Non-commercial profits (*bénéfices non commerciaux*, BNC) of articles 92 to 103 of the
Code général des impôts: of one declarant (Catala's ``BénéficesNonCommerciauxDéclarant``)
and of the tax household (``BénéficesNonCommerciauxFoyerFiscal``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from functools import cached_property

from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.catala.income_tax.categorical import (
    CapitalGains,
    QuotientDeficitImputation,
)
from law_as_code_benchmarks.catala.income_tax.exceptional_income import (
    ExceptionalIncome,
    IncomeKind,
    QuotientIncome,
)
from law_as_code_benchmarks.catala.income_tax.oracles import (
    DeficitImputation,
    PastDeficit,
    ProportionalDistribution,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import (
    CatalaValue,
    Reference,
    StructureLiteral,
)
from law_as_code_benchmarks.catala.scope_test import CatalaRecord, ScopeCase

# %% the declarations


@dataclass(eq=False)
class NonCommercialGeneral(CatalaRecord):
    """
    What a declarant declares of non-commercial profits, professional or not, Catala's
    ``DéclarationBénéficesNonCommerciauxGénéraux``; an empty box is nothing.
    """

    micro_taxable: Money = field(default_factory=lambda: Money.zero)
    """The receipts of the micro regime."""

    micro_short_term_gains: Money = field(default_factory=lambda: Money.zero)
    """Net short-term capital gains of the micro regime."""

    micro_short_term_losses: Money = field(default_factory=lambda: Money.zero)
    """Net short-term capital losses of the micro regime."""

    micro_long_term_gains: Money = field(default_factory=lambda: Money.zero)
    """Net long-term capital gains of the micro regime."""

    micro_long_term_losses: Money = field(default_factory=lambda: Money.zero)
    """Net long-term capital losses of the micro regime."""

    real_long_term_gains: Money = field(default_factory=lambda: Money.zero)
    """Net long-term capital gains of the real regime."""

    real_taxable: Money = field(default_factory=lambda: Money.zero)
    """The taxable profits of the real regime."""

    real_deficit: Money = field(default_factory=lambda: Money.zero)
    """The deficit of the real regime."""

    foreign_taxable_credited: Money = field(default_factory=lambda: Money.zero)
    """Taxable profits of foreign source whose tax is credited."""

    exceptional_income: list[ExceptionalIncome] = field(default_factory=list)
    """The exceptional or deferred income."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``DéclarationBénéficesNonCommerciauxGénéraux``."""
        return {
            "revenus_imposables_micro": "micro_taxable",
            "plus_values_nettes_court_terme_micro": "micro_short_term_gains",
            "moins_values_nettes_court_terme_micro": "micro_short_term_losses",
            "plus_values_nettes_long_terme_micro": "micro_long_term_gains",
            "moins_values_nettes_long_terme_micro": "micro_long_term_losses",
            "plus_values_nettes_long_terme_réel": "real_long_term_gains",
            "revenus_imposables": "real_taxable",
            "déficit_réel": "real_deficit",
            "revenus_imposables_source_étrangère_imputés": "foreign_taxable_credited",
            "revenus_exceptionnels_ou_différés": "exceptional_income",
        }

    @property
    def micro_exceptional_income(self) -> list[ExceptionalIncome]:
        """102 ter: the exceptional income of the micro regime, which the flat abatement also abates."""
        return [
            income
            for income in self.exceptional_income
            if income.category.kind == IncomeKind.MICRO_NON_COMMERCIAL
        ]

    @property
    def other_exceptional_income(self) -> list[ExceptionalIncome]:
        """The other exceptional income, which no abatement abates."""
        return [
            income
            for income in self.exceptional_income
            if income.category.kind != IncomeKind.MICRO_NON_COMMERCIAL
        ]

    @property
    def real_balance(self) -> Money:
        """The profits of the real regime, those of foreign source credited (23 B of the OECD model), less its deficit."""
        return self.real_taxable + self.foreign_taxable_credited - self.real_deficit


@dataclass(eq=False)
class NonCommercialProfessional(CatalaRecord):
    """The professional non-commercial profits, Catala's ``DéclarationBénéficesNonCommerciauxProfessionnels``."""

    general: NonCommercialGeneral = field(default_factory=NonCommercialGeneral)
    """What is declared as for every non-commercial profit."""

    inventor_software_income: Money = field(default_factory=lambda: Money.zero)
    """The taxable income of inventors and software (93 quater I)."""

    inventor_software_income_with_contributions: Money = field(
        default_factory=lambda: Money.zero
    )
    """That of it subject to social contributions."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``DéclarationBénéficesNonCommerciauxProfessionnels``."""
        return {
            "généraux": "general",
            "produits_inventeurs_logiciel_taxables": "inventor_software_income",
            "produits_inventeurs_logiciel_taxables_soumis_cotisations": "inventor_software_income_with_contributions",
        }


@dataclass(eq=False)
class NonCommercialNonProfessional(CatalaRecord):
    """The non-professional non-commercial profits, Catala's ``DéclarationBénéficesNonCommerciauxNonProfessionnels``."""

    general: NonCommercialGeneral = field(default_factory=NonCommercialGeneral)
    """What is declared as for every non-commercial profit."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The field of ``DéclarationBénéficesNonCommerciauxNonProfessionnels``."""
        return {"généraux": "general"}


@dataclass(eq=False)
class NonCommercialDeclaration(CatalaRecord):
    """What a declarant declares of non-commercial profits, Catala's ``DéclarationBénéficesNonCommerciaux``."""

    professional: NonCommercialProfessional = field(
        default_factory=NonCommercialProfessional
    )
    """The professional profits."""

    non_professional: NonCommercialNonProfessional = field(
        default_factory=NonCommercialNonProfessional
    )
    """The non-professional profits."""

    flat_levy_receipts: Money = field(default_factory=lambda: Money.zero)
    """The receipts of a micro-entrepreneur under the flat levy, exempt from contributions (151-0)."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``DéclarationBénéficesNonCommerciaux``."""
        return {
            "professionnels": "professional",
            "non_professionnels": "non_professional",
            "recettes_prélèvement_libératoire_éxonérées_cotisations": "flat_levy_receipts",
        }


# %% the declarant


class NonCommercialDeclarantOutput(StrEnum):
    """The outputs of ``BénéficesNonCommerciauxDéclarant``."""

    PROFESSIONAL_ABATEMENT = "abattement_forfaitaire_micro_professionnel"
    """The professional share of the flat abatement of the micro regime."""

    NON_PROFESSIONAL_ABATEMENT = "abattement_forfaitaire_micro_non_professionnel"
    """Its non-professional share."""

    PROFESSIONAL_QUOTIENT_INCOMES = "revenus_quotientés_professionnels"
    """The professional quotient incomes."""

    NON_PROFESSIONAL_QUOTIENT_INCOMES = "revenus_quotientés_non_professionnels"
    """The non-professional quotient incomes."""

    MICRO_ENTERPRISE_LEVY = "prélèvement_libératoire_auto_entreprise"
    """The flat levy of a micro-entrepreneur."""

    LONG_TERM_GAINS_LEVY = "prélèvement_libératoire_plus_values_long_terme"
    """The levy on long-term capital gains."""

    PROFESSIONAL_BALANCE = "solde_net_professionnel"
    """The net professional balance."""

    NON_PROFESSIONAL_BALANCE = "solde_net_non_professionnel"
    """The net non-professional balance."""

    FLAT_RATE_TAX = "impôt_taux_forfaitaire"
    """The tax at a flat rate on inventors' and software income."""


@dataclass(eq=False)
class NonCommercialDeclarantCase(ScopeCase):
    """The non-commercial profits of one declarant, Catala's ``BénéficesNonCommerciauxDéclarant``."""

    declaration: NonCommercialDeclaration
    """What the declarant declares."""

    income_year: int
    """The year of the income."""

    @classproperty
    def catala_scope(cls) -> str:
        """``BénéficesNonCommerciauxDéclarant``."""
        return "BénéficesNonCommerciauxDéclarant"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {"revenus": "declaration", "année_revenus": "income_year"}

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`NonCommercialDeclarantOutput`."""
        return NonCommercialDeclarantOutput

    @classproperty
    def micro_abatement_rate(cls) -> Fraction:
        """102 ter: 34 %."""
        return Fraction(34, 100)

    @classproperty
    def micro_abatement_minimum(cls) -> Money:
        """102 ter: 305 €."""
        return Money.from_euros(305)

    @classproperty
    def micro_enterprise_levy_rate(cls) -> Fraction:
        """151-0: 2.2 %."""
        return Fraction(22, 1000)

    @classproperty
    def flat_rate(cls) -> Fraction:
        """93 quater I: 10 %."""
        return Fraction(10, 100)

    @property
    def professional(self) -> NonCommercialGeneral:
        """What the declarant declares of professional profits."""
        return self.declaration.professional.general

    @property
    def non_professional(self) -> NonCommercialGeneral:
        """What the declarant declares of non-professional profits."""
        return self.declaration.non_professional.general

    @cached_property
    def micro_abatement(self) -> Money:
        """102 ter and 193: 34 % of the micro receipts and micro exceptional income, rounded to the euro, 305 € at least but the receipts at most."""
        basis = sum(
            (
                income.amount
                for general in (self.professional, self.non_professional)
                for income in general.micro_exceptional_income
            ),
            self.professional.micro_taxable + self.non_professional.micro_taxable,
        )
        abatement = (basis * self.micro_abatement_rate).rounded_to_units()
        return min(max(abatement, self.micro_abatement_minimum), basis)

    @cached_property
    def micro_abatement_shares(self) -> tuple[Money, Money, list[Money], list[Money]]:
        """
        102 ter and 163-0 A: the abatement shared in proportion between the professional
        and non-professional receipts and each micro exceptional income, as Catala's
        ``ProRataArrondiEuroBranchement`` shares it among its nine bases and lists.
        """
        professional = [
            income.amount for income in self.professional.micro_exceptional_income
        ]
        non_professional = [
            income.amount for income in self.non_professional.micro_exceptional_income
        ]
        shares = ProportionalDistribution(
            amount=self.micro_abatement,
            bases=[
                self.professional.micro_taxable,
                self.non_professional.micro_taxable,
                *[Money.zero] * 7,
                *professional,
                *non_professional,
            ],
        ).shares()
        return (
            shares[0],
            shares[1],
            shares[9 : 9 + len(professional)],
            shares[9 + len(professional) :],
        )

    def quotient_incomes(
        self, general: NonCommercialGeneral, micro_shares: list[Money]
    ) -> list[QuotientIncome]:
        """:return: 163-0 A: the micro exceptional incomes with their share of the abatement, then the others without deduction."""
        return [
            QuotientIncome.from_income(income, share, self.income_year)
            for income, share in zip(general.micro_exceptional_income, micro_shares)
        ] + [
            QuotientIncome.from_income(income, Money.zero, self.income_year)
            for income in general.other_exceptional_income
        ]

    def balance(self, general: NonCommercialGeneral, abatement: Money) -> Money:
        """:return: 13 and 102 ter: the real balance, the micro receipts less their abatement, and the short-term gains less losses."""
        return (
            general.real_balance
            + general.micro_taxable
            - abatement
            + CapitalGains(
                general.micro_short_term_gains, general.micro_short_term_losses
            ).short_term_balance
        )

    def output(self, variable: str) -> CatalaValue:
        (
            professional_abatement,
            non_professional_abatement,
            professional_shares,
            non_professional_shares,
        ) = self.micro_abatement_shares
        professional, non_professional = self.professional, self.non_professional
        match NonCommercialDeclarantOutput(variable):
            case NonCommercialDeclarantOutput.PROFESSIONAL_ABATEMENT:
                return professional_abatement
            case NonCommercialDeclarantOutput.NON_PROFESSIONAL_ABATEMENT:
                return non_professional_abatement
            case NonCommercialDeclarantOutput.PROFESSIONAL_QUOTIENT_INCOMES:
                return [
                    income.to_catala()
                    for income in self.quotient_incomes(
                        professional, professional_shares
                    )
                ]
            case NonCommercialDeclarantOutput.NON_PROFESSIONAL_QUOTIENT_INCOMES:
                return [
                    income.to_catala()
                    for income in self.quotient_incomes(
                        non_professional, non_professional_shares
                    )
                ]
            case NonCommercialDeclarantOutput.MICRO_ENTERPRISE_LEVY:
                return (
                    self.declaration.flat_levy_receipts
                    * self.micro_enterprise_levy_rate
                ).rounded_to_units()
            case NonCommercialDeclarantOutput.LONG_TERM_GAINS_LEVY:
                return (
                    CapitalGains(
                        professional.micro_long_term_gains
                        + non_professional.micro_long_term_gains,
                        professional.micro_long_term_losses
                        + non_professional.micro_long_term_losses,
                    ).long_term_levy
                    + CapitalGains(
                        non_professional.real_long_term_gains, Money.zero
                    ).long_term_levy
                )
            case NonCommercialDeclarantOutput.PROFESSIONAL_BALANCE:
                return self.balance(professional, professional_abatement)
            case NonCommercialDeclarantOutput.NON_PROFESSIONAL_BALANCE:
                return self.balance(non_professional, non_professional_abatement)
            case NonCommercialDeclarantOutput.FLAT_RATE_TAX:
                return (
                    self.declaration.professional.inventor_software_income
                    + self.declaration.professional.inventor_software_income_with_contributions
                ) * self.flat_rate

    def non_professional_quotient_incomes(self) -> list[QuotientIncome]:
        """:return: The non-professional quotient incomes."""
        return self.quotient_incomes(
            self.non_professional, self.micro_abatement_shares[3]
        )

    def to_catala(self) -> StructureLiteral:
        """:return: Every output of the scope, as Catala prints its result."""
        return StructureLiteral(
            structure=Reference(parts=(self.catala_scope,)),
            fields={
                output.value: self.output(output)
                for output in NonCommercialDeclarantOutput
            },
        )


# %% the tax household


class NonCommercialHouseholdOutput(StrEnum):
    """The outputs of ``BénéficesNonCommerciauxFoyerFiscal``."""

    DECLARANTS = "résultats_liquidation_bénéfices_non_commerciaux"
    """The result of each declaration."""

    IMPUTED_QUOTIENT_INCOMES = "revenus_non_professionnels_quotientés_imputés"
    """The non-professional quotient incomes, the deficit imputed on them."""

    GROSS_TOTAL_INCOME = "revenu_brut_global"
    """The gross total income."""

    NON_PROFESSIONAL_DEFICIT = "déficit_brut_global_non_professionnel"
    """The non-professional gross total deficit."""

    PROFESSIONAL_DEFICIT = "déficit_brut_global_professionnel"
    """The professional gross total deficit."""

    UPDATED_PAST_DEFICITS = (
        "déficits_réels_années_antérieures_non_professionnels_mis_à_jour"
    )
    """The non-professional deficits of past years left."""


@dataclass(eq=False)
class NonCommercialHouseholdCase(ScopeCase):
    """The non-commercial profits of the tax household, Catala's ``BénéficesNonCommerciauxFoyerFiscal``."""

    income_year: int
    """The year of the income."""

    declarations: list[NonCommercialDeclaration]
    """What each declarant declares."""

    past_non_professional_deficits: list[PastDeficit]
    """The non-professional deficits of the real regime of past years."""

    @classproperty
    def catala_scope(cls) -> str:
        """``BénéficesNonCommerciauxFoyerFiscal``."""
        return "BénéficesNonCommerciauxFoyerFiscal"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "année_revenus": "income_year",
            "revenus": "declarations",
            "déficits_réels_années_antérieures_non_professionnels": "past_non_professional_deficits",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`NonCommercialHouseholdOutput`."""
        return NonCommercialHouseholdOutput

    @classproperty
    def deficit_carry_forward_years(cls) -> int:
        """156 I 2°: the deficits of the six years before."""
        return 6

    @cached_property
    def declarants(self) -> list[NonCommercialDeclarantCase]:
        """Each declaration's result."""
        return [
            NonCommercialDeclarantCase(
                declaration=declaration, income_year=self.income_year
            )
            for declaration in self.declarations
        ]

    def total(self, output: NonCommercialDeclarantOutput) -> Money:
        """:return: The sum of *output* over the declarants."""
        return sum(
            (declarant.output(output) for declarant in self.declarants), Money.zero
        )

    @cached_property
    def quotient_imputation(self) -> QuotientDeficitImputation:
        """156: the non-professional deficit imputed on the non-professional quotient incomes."""
        return QuotientDeficitImputation(
            balance=self.total(NonCommercialDeclarantOutput.NON_PROFESSIONAL_BALANCE),
            quotient_incomes=[
                declarant.non_professional_quotient_incomes()
                for declarant in self.declarants
            ],
        )

    @cached_property
    def past_deficit_imputation(self) -> DeficitImputation:
        """156 I 2°: the balance left imputed on the deficits of the six years before, oldest first."""
        quotient = self.quotient_imputation
        return DeficitImputation.from_income(
            quotient.balance + quotient.imputed_deficit,
            [
                deficit
                for deficit in self.past_non_professional_deficits
                if deficit.year >= self.income_year - self.deficit_carry_forward_years
            ],
        )

    def output(self, variable: str) -> CatalaValue:
        professional = self.total(NonCommercialDeclarantOutput.PROFESSIONAL_BALANCE)
        non_professional = self.past_deficit_imputation.imputed_income
        match NonCommercialHouseholdOutput(variable):
            case NonCommercialHouseholdOutput.DECLARANTS:
                return [declarant.to_catala() for declarant in self.declarants]
            case NonCommercialHouseholdOutput.IMPUTED_QUOTIENT_INCOMES:
                return [
                    [income.to_catala() for income in incomes]
                    for incomes in self.quotient_imputation.imputed_incomes
                ]
            case NonCommercialHouseholdOutput.GROSS_TOTAL_INCOME:
                return max(non_professional, Money.zero) + max(professional, Money.zero)
            case NonCommercialHouseholdOutput.NON_PROFESSIONAL_DEFICIT:
                return Money.zero - min(non_professional, Money.zero)
            case NonCommercialHouseholdOutput.PROFESSIONAL_DEFICIT:
                return Money.zero - min(professional, Money.zero)
            case NonCommercialHouseholdOutput.UPDATED_PAST_DEFICITS:
                return [
                    deficit.to_catala()
                    for deficit in self.past_deficit_imputation.remaining_deficits
                ]
