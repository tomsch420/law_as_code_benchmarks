"""
Wages, salaries and pensions of articles 79 to 83, 158 and 163-0 A of the Code général
des impôts: of one declarant (Catala's ``TraitementsSalairesDéclarant``) and of the tax
household (``TraitementsSalairesFoyerFiscal``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from functools import cached_property

from krrood.entity_query_language.factories import (
    deduced_variable,
    inference,
    type_,
    variable,
)
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.catala.income_tax.exceptional_income import (
    AnnuityAge,
    ExceptionalIncome,
    IncomeKind,
    QuotientIncome,
)
from law_as_code_benchmarks.catala.income_tax.oracles import ProportionalDistribution
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.provision import RuleBranch, RuleChain
from law_as_code_benchmarks.catala.reader import (
    CatalaValue,
    Reference,
    StructureLiteral,
)
from law_as_code_benchmarks.catala.scope_test import (
    CaseAmount,
    CaseCondition,
    CatalaRecord,
    CatalaVariant,
    ScopeCase,
    ScopeProvision,
)

# %% the declarations


@dataclass(eq=False)
class RealExpenses(CatalaVariant):
    """Whether the declarant deducts their real expenses, Catala's ``FraisRéels``."""


@dataclass(eq=False)
class NoRealExpenses(RealExpenses):
    """The flat deduction, ``Non``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Non``."""
        return "Non"


@dataclass(eq=False)
class ClaimedRealExpenses(RealExpenses):
    """The real expenses, ``Oui``, of an amount."""

    amount: Money = field(default_factory=lambda: Money.zero)
    """The expenses."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Oui``."""
        return "Oui"

    @classproperty
    def content_field(cls) -> str:
        """The amount."""
        return "amount"


@dataclass(eq=False)
class WageDeclaration(CatalaRecord):
    """
    The wages and pensions one person declares, Catala's ``DéclarationTraitementsSalaires``,
    each field a box of the return; an empty box is nothing, as Catala's interface fills it.
    """

    childminder_income: Money = field(default_factory=lambda: Money.zero)
    """Box J: the income of a childminder (80 sexies)."""

    managing_partners_income: Money = field(default_factory=lambda: Money.zero)
    """The income of managing partners (62)."""

    civil_servants_copyright: Money = field(default_factory=lambda: Money.zero)
    """The copyright of civil servants and researchers (93 1 bis)."""

    exempt_overtime: Money = field(default_factory=lambda: Money.zero)
    """Exempt overtime and days off (81 quater)."""

    real_expenses: RealExpenses = field(default_factory=NoRealExpenses)
    """Whether the real expenses are deducted."""

    pensions: Money = field(default_factory=lambda: Money.zero)
    """Pensions, retirement pensions and annuities."""

    pension_capital_at_7_5_percent: Money = field(default_factory=lambda: Money.zero)
    """Pensions paid in capital, taxed at 7.5 % (163 bis)."""

    retirement_savings_capital: Money = field(default_factory=lambda: Money.zero)
    """Pensions paid in capital of retirement savings plans."""

    disability_pensions: Money = field(default_factory=lambda: Money.zero)
    """Disability pensions."""

    maintenance_received: Money = field(default_factory=lambda: Money.zero)
    """Maintenance payments received."""

    wages: Money = field(default_factory=lambda: Money.zero)
    """Wages and salaries."""

    exempt_tips: Money = field(default_factory=lambda: Money.zero)
    """Exempt tips (article 5 of the amending finance law of 2022)."""

    value_sharing_bonus: Money = field(default_factory=lambda: Money.zero)
    """The value sharing bonus declared exempt."""

    raised_bonus_threshold: bool = False
    """Whether the bonus's exemption threshold is raised."""

    unemployment_and_early_retirement: Money = field(default_factory=lambda: Money.zero)
    """Other taxable income of unemployment and early retirement."""

    excess_stock_option_discount: Money = field(default_factory=lambda: Money.zero)
    """The excess discount on stock options (80 bis)."""

    stock_option_gains: Money = field(default_factory=lambda: Money.zero)
    """The gains of exercising stock options (80 bis)."""

    insurance_agent_wages: Money = field(default_factory=lambda: Money.zero)
    """The taxable wages of insurance agents (93 1 ter)."""

    moral_damages_above_million: Money = field(default_factory=lambda: Money.zero)
    """The part of compensation for moral damages above a million (80)."""

    carried_interest: Money = field(default_factory=lambda: Money.zero)
    """Gains and distributions of carried interest (80 quindecies)."""

    carried_interest_with_contribution: Money = field(
        default_factory=lambda: Money.zero
    )
    """Those subject to the employee's contribution."""

    exceptional_income: list[ExceptionalIncome] = field(default_factory=list)
    """The exceptional or deferred income."""

    foreign_wages_with_tax_credit: Money = field(default_factory=lambda: Money.zero)
    """Foreign wages whose tax is credited."""

    foreign_pensions_with_tax_credit: Money = field(default_factory=lambda: Money.zero)
    """Foreign pensions whose tax is credited."""

    other_foreign_wages: Money = field(default_factory=lambda: Money.zero)
    """Other taxable wages of foreign source (204 C)."""

    other_foreign_pensions: Money = field(default_factory=lambda: Money.zero)
    """Other taxable pensions of foreign source (204 C)."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``DéclarationTraitementsSalaires``."""
        return {
            "revenu_assistants_maternels_familiaux": "childminder_income",
            "revenus_associés_gérants": "managing_partners_income",
            "droits_dauteurs_fonctionnaires_chercheurs": "civil_servants_copyright",
            "heures_supplémentaires_et_rtt_exonérées": "exempt_overtime",
            "frais_réels": "real_expenses",
            "pensions_retraites_rentes": "pensions",
            "pensions_retraites_en_capital_7_5pct": "pension_capital_at_7_5_percent",
            "pensions_en_capital_plans_épargne_retraite": "retirement_savings_capital",
            "pensions_invalidité": "disability_pensions",
            "pensions_alimentaires_perçues": "maintenance_received",
            "traitements_salaires": "wages",
            "pourboires_exonérés": "exempt_tips",
            "prime_partage_valeur_exonérée": "value_sharing_bonus",
            "majoration_seuil_exonération": "raised_bonus_threshold",
            "autres_revenus_imposables_chômage_préretraite": "unemployment_and_early_retirement",
            "rabais_excédentaire_options_sur_titres": "excess_stock_option_discount",
            "gains_de_levee_doptions": "stock_option_gains",
            "salaires_imposables_agent_assurance": "insurance_agent_wages",
            "indemnités_préjudice_moral_fraction_supérieure_million": "moral_damages_above_million",
            "gains_et_distributions_carried_interest": "carried_interest",
            "gains_et_distributions_carried_interest_soumis_contribution_salariale": "carried_interest_with_contribution",
            "revenus_exceptionnels_ou_différés": "exceptional_income",
            "salaires_étrangers_impôt_imputé": "foreign_wages_with_tax_credit",
            "pensions_étrangères_impôts_imputé": "foreign_pensions_with_tax_credit",
            "autre_salaires_imposables_source_étrangère": "other_foreign_wages",
            "autre_pensions_imposables_source_étrangère": "other_foreign_pensions",
        }

    def exceptional_amounts(self, kind: IncomeKind) -> list[Money]:
        """:return: The exceptional or deferred income of *kind*, in order."""
        return [
            income.amount
            for income in self.exceptional_income
            if income.category.kind == kind
        ]


@dataclass(eq=False)
class HouseholdWageDeclaration(CatalaRecord):
    """
    What the tax household declares besides each person's wages, Catala's
    ``DéclarationTraitementsSalairesFoyerFiscal``; an empty box is nothing.
    """

    annuities_under_50: Money = field(default_factory=lambda: Money.zero)
    """Life annuities begun under 50."""

    annuities_from_50_to_59: Money = field(default_factory=lambda: Money.zero)
    """Begun from 50 to 59."""

    annuities_from_60_to_69: Money = field(default_factory=lambda: Money.zero)
    """Begun from 60 to 69."""

    annuities_from_70: Money = field(default_factory=lambda: Money.zero)
    """Begun from 70."""

    foreign_annuities_under_50: Money = field(default_factory=lambda: Money.zero)
    """Foreign life annuities with tax credit, begun under 50."""

    foreign_annuities_from_50_to_59: Money = field(default_factory=lambda: Money.zero)
    """Begun from 50 to 59."""

    foreign_annuities_from_60_to_69: Money = field(default_factory=lambda: Money.zero)
    """Begun from 60 to 69."""

    foreign_annuities_from_70: Money = field(default_factory=lambda: Money.zero)
    """Begun from 70."""

    exceptional_income: list[ExceptionalIncome] = field(default_factory=list)
    """The household's exceptional or deferred income, life annuities."""

    free_shares_gain: Money = field(default_factory=lambda: Money.zero)
    """The taxable gain of acquiring free shares."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``DéclarationTraitementsSalairesFoyerFiscal``."""
        return {
            "rentes_percues_49moins_ans": "annuities_under_50",
            "rentes_percues_50_59ans": "annuities_from_50_to_59",
            "rentes_percues_60_69ans": "annuities_from_60_to_69",
            "rentes_percues_70plus_ans": "annuities_from_70",
            "rentes_étrangères_imputables_percues_49moins_ans": "foreign_annuities_under_50",
            "rentes_étrangères_imputables_percues_50_59ans": "foreign_annuities_from_50_to_59",
            "rentes_étrangères_imputables_percues_60_69ans": "foreign_annuities_from_60_to_69",
            "rentes_étrangères_imputables_percues_70plus_ans": "foreign_annuities_from_70",
            "revenus_exceptionnels_ou_différés": "exceptional_income",
            "acquisition_d_actions_gratuites_gain_imposable": "free_shares_gain",
        }


@dataclass(eq=False)
class PensionAbatementCap(CatalaVariant):
    """Whether the declarant's pension abatement is capped, Catala's ``SélecteurPlafondAbattementPensionsRetraitesRentes79``."""


@dataclass(eq=False)
class UncappedPensionAbatement(PensionAbatementCap):
    """Not capped, ``Déplafonné``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Déplafonné``."""
        return "Déplafonné"


@dataclass(eq=False)
class CappedPensionAbatement(PensionAbatementCap):
    """Capped, ``PlafondStandardOuProratisé``, at the household's ceiling or its share of it."""

    cap: Money = field(default_factory=lambda: Money.zero)
    """The cap."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``PlafondStandardOuProratisé``."""
        return "PlafondStandardOuProratisé"

    @classproperty
    def content_field(cls) -> str:
        """The cap."""
        return "cap"


class PensionKind(StrEnum):
    """The pensions of article 79, each named as Catala's ``TypePensionRetraiteRente``."""

    PENSIONS = "PensionsRetraitesRentes"
    """Pensions, retirement pensions and annuities."""

    CAPITAL_AT_7_5_PERCENT = "PensionEnCapital_7_5pct"
    """A pension in capital taxed at 7.5 %."""

    DISABILITY = "PensionInvalidité"
    """A disability pension."""

    RETIREMENT_SAVINGS_CAPITAL = "PensionEnCapitalPlansÉpargneRetraite"
    """A pension in capital of retirement savings plans."""

    MAINTENANCE = "PensionAlimentairePercue"
    """Maintenance received."""


@dataclass(frozen=True)
class Pension:
    """A pension of article 79, Catala's ``PensionRetraiteRente``."""

    amount: Money
    """The pension."""

    kind: PensionKind
    """What it is."""


# %% the declarant


class DeclarantWagesOutput(StrEnum):
    """The outputs of ``TraitementsSalairesDéclarant``."""

    PENSION_ABATEMENT = "abattement_pensions_retraites_rentes"
    """The abatement of pensions."""

    PROFESSIONAL_EXPENSES = "déduction_frais_professionnels_traitements_salaires"
    """The deduction of professional expenses."""

    OVERTIME_EXEMPTION = "exonérations_81_quater"
    """The exemption of 81 quater."""

    FLAT_LEVY = "prélèvement_libératoire"
    """The levy on pensions in capital."""

    TAXABLE_WAGES = "traitements_salaires_avec_déduction_frais_professionnels"
    """The wages the deduction is taken from."""

    GROSS_INCOME = "revenu_brut_déclarant_hors_quotient"
    """The declarant's gross income, the quotient incomes aside."""

    QUOTIENT_INCOMES = "revenus_quotientés"
    """The incomes taxed by the quotient."""


@dataclass(eq=False)
class DeclarantWagesCase(ScopeCase):
    """The wages and pensions of one declarant, Catala's ``TraitementsSalairesDéclarant``."""

    declaration: WageDeclaration
    """What the declarant declares."""

    income_year: int
    """The year of the income."""

    pension_abatement_cap: PensionAbatementCap
    """Whether the pension abatement is capped."""

    @classproperty
    def catala_scope(cls) -> str:
        """``TraitementsSalairesDéclarant``."""
        return "TraitementsSalairesDéclarant"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "revenus": "declaration",
            "année_revenus": "income_year",
            "selecteur_plafond_abattement_pensions_retraites_rentes": "pension_abatement_cap",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`DeclarantWagesOutput`."""
        return DeclarantWagesOutput

    def amount(self, provision: type[ScopeProvision]) -> Money | None:
        """:return: The amount *provision* concludes; None where it concludes none."""
        conclusion = self.sole_conclusion(provision)
        return None if conclusion is None else conclusion.amount

    @cached_property
    def overtime_exemption(self) -> Money | None:
        """81 quater: the exempt overtime and, from the amending law of 2022, tips, 7,500 € at most, from 2022."""
        return self.amount(OvertimeExemptionProvision)

    @cached_property
    def taxable_wages(self) -> Money | None:
        """
        The wages the deduction is taken from: the wages (1 A), with the income of 62,
        93 1 bis, 158 5 a and b, the overtime beyond the exemption (81 quater), the value
        sharing bonus beyond its exemption (loi n° 2022-1158), 80, 80 bis, 80 sexies,
        80 quindecies, 93 1 ter, the foreign wages credited and of 204 C.
        """
        if self.overtime_exemption is None:
            return None
        declaration = self.declaration
        bonus_cap = (
            ValueSharingBonus.raised_cap
            if declaration.raised_bonus_threshold
            else ValueSharingBonus.cap
        )
        return (
            declaration.wages
            + declaration.managing_partners_income
            + declaration.civil_servants_copyright
            + declaration.unemployment_and_early_retirement
            + declaration.exempt_overtime
            + declaration.exempt_tips
            - self.overtime_exemption
            + declaration.value_sharing_bonus
            - min(declaration.value_sharing_bonus, bonus_cap)
            + declaration.moral_damages_above_million
            + declaration.stock_option_gains
            + declaration.excess_stock_option_discount
            + declaration.childminder_income
            + declaration.carried_interest
            + declaration.carried_interest_with_contribution
            + declaration.insurance_agent_wages
            + declaration.foreign_wages_with_tax_credit
            + declaration.other_foreign_wages
        )

    @cached_property
    def flat_deduction(self) -> Money | None:
        """83 3°: 10 % of the wages, rounded to the euro (193), the minimum at least but the wages at most."""
        minimum = self.amount(DeductionMinimumProvision)
        if minimum is None or self.taxable_wages is None:
            return None
        deduction = (self.taxable_wages * WageDeduction.rate).rounded_to_units()
        if deduction >= minimum:
            return deduction
        return self.taxable_wages if minimum > self.taxable_wages else minimum

    @cached_property
    def uncapped_deduction(self) -> Money | None:
        """83 3°: the flat deduction and 10 % of the exceptional wages."""
        if self.flat_deduction is None:
            return None
        return self.flat_deduction + sum(
            (
                amount * WageDeduction.rate
                for amount in self.declaration.exceptional_amounts(IncomeKind.WAGES)
            ),
            Money.zero,
        )

    @cached_property
    def capped_deduction(self) -> Money | None:
        """83 3°: the deduction, the ceiling at most."""
        ceiling = self.amount(DeductionCeilingProvision)
        if ceiling is None or self.uncapped_deduction is None:
            return None
        return (
            ceiling if self.uncapped_deduction >= ceiling else self.uncapped_deduction
        )

    @cached_property
    def applied_real_expenses(self) -> Money | None:
        """83 3°: the real expenses, where they are declared and at least the capped deduction."""
        applies = self.sole_conclusion(RealExpensesProvision)
        if applies is None or not applies.holds:
            return None
        return self.declaration.real_expenses.amount

    @cached_property
    def total_deduction(self) -> Money | None:
        """83 3°: the real expenses where they apply, the capped deduction otherwise."""
        if self.capped_deduction is None:
            return None
        if self.applied_real_expenses is not None:
            return self.applied_real_expenses
        return self.capped_deduction

    @cached_property
    def pensions(self) -> list[Pension]:
        """Article 79, 23 B of the OECD model and 204 C: the pensions declared."""
        declaration = self.declaration
        return [
            Pension(declaration.pensions, PensionKind.PENSIONS),
            Pension(
                declaration.pension_capital_at_7_5_percent,
                PensionKind.CAPITAL_AT_7_5_PERCENT,
            ),
            Pension(
                declaration.retirement_savings_capital,
                PensionKind.RETIREMENT_SAVINGS_CAPITAL,
            ),
            Pension(declaration.disability_pensions, PensionKind.DISABILITY),
            Pension(declaration.maintenance_received, PensionKind.MAINTENANCE),
            Pension(declaration.foreign_pensions_with_tax_credit, PensionKind.PENSIONS),
            Pension(declaration.other_foreign_pensions, PensionKind.PENSIONS),
        ]

    def pension_abatement_of(self, pension: Money) -> Money | None:
        """:return: 158 5 a: 10 % of *pension*, rounded to the euro (193), the minimum at least but the pension at most."""
        minimum = self.amount(PensionAbatementMinimumProvision)
        if minimum is None:
            return None
        abatement = max((pension * PensionAbatement.rate).rounded_to_units(), minimum)
        return min(abatement, pension)

    @cached_property
    def uncapped_pension_abatement(self) -> Money | None:
        """158 5 a: the abatement of each pension that has one, and of each exceptional pension."""
        abated = [
            pension.amount
            for pension in self.pensions
            if PensionAbatement.applies_to(pension.kind)
        ] + self.declaration.exceptional_amounts(IncomeKind.PENSIONS)
        abatements = [self.pension_abatement_of(amount) for amount in abated]
        if None in abatements:
            return None
        return sum(abatements, Money.zero)

    @cached_property
    def capped_pension_abatement(self) -> Money | None:
        """158 5 a: the abatement, the household's ceiling or the declarant's share of it at most."""
        if self.uncapped_pension_abatement is None:
            return None
        cap = self.pension_abatement_cap
        if isinstance(cap, CappedPensionAbatement):
            return min(self.uncapped_pension_abatement, cap.cap)
        return self.uncapped_pension_abatement

    def quotient_deduction(self, income: ExceptionalIncome) -> Money:
        """
        :return: 163-0 A: the deduction of an exceptional income — of wages, the flat
            deduction prorated to the cap, or its share of the real expenses; of a pension,
            the abatement prorated to the cap — rounded to the euro (193).
        """
        amount = income.amount
        match income.category.kind:
            case IncomeKind.WAGES if self.applied_real_expenses is not None:
                wages = self.taxable_wages + sum(
                    self.declaration.exceptional_amounts(IncomeKind.WAGES), Money.zero
                )
                share = (
                    self.applied_real_expenses * (amount / wages)
                ).rounded_to_units()
                return min(share, amount).rounded_to_units()
            case IncomeKind.WAGES:
                return (
                    (amount * WageDeduction.rate)
                    * (self.capped_deduction / self.uncapped_deduction)
                ).rounded_to_units()
            case IncomeKind.PENSIONS:
                return (
                    self.pension_abatement_of(amount)
                    * (self.capped_pension_abatement / self.uncapped_pension_abatement)
                ).rounded_to_units()
        return Money.zero

    @cached_property
    def quotient_incomes(self) -> list[QuotientIncome]:
        """163-0 A: the exceptional or deferred incomes, each with its deduction."""
        return [
            QuotientIncome.from_income(
                income, self.quotient_deduction(income), self.income_year
            )
            for income in self.declaration.exceptional_income
        ]

    def quotient_deductions(self, kind: IncomeKind) -> Money:
        """:return: The deductions of the quotient incomes of *kind*."""
        return sum(
            (
                income.deduction
                for income in self.quotient_incomes
                if income.category.kind == kind
            ),
            Money.zero,
        )

    def output(self, variable: str) -> CatalaValue:
        if self.total_deduction is None or self.capped_pension_abatement is None:
            return None
        declaration = self.declaration
        pension_abatement = self.capped_pension_abatement - self.quotient_deductions(
            IncomeKind.PENSIONS
        )
        deduction = self.total_deduction - self.quotient_deductions(IncomeKind.WAGES)
        match DeclarantWagesOutput(variable):
            case DeclarantWagesOutput.PENSION_ABATEMENT:
                return pension_abatement
            case DeclarantWagesOutput.PROFESSIONAL_EXPENSES:
                return deduction
            case DeclarantWagesOutput.OVERTIME_EXEMPTION:
                return self.overtime_exemption
            case DeclarantWagesOutput.FLAT_LEVY:
                capital = declaration.pension_capital_at_7_5_percent
                return (capital - capital * PensionAbatement.rate) * FlatLevy.rate
            case DeclarantWagesOutput.TAXABLE_WAGES:
                return self.taxable_wages
            case DeclarantWagesOutput.GROSS_INCOME:
                return (
                    declaration.pensions
                    + declaration.maintenance_received
                    + declaration.disability_pensions
                    - pension_abatement
                    + declaration.retirement_savings_capital
                    + self.taxable_wages
                    - deduction
                )
            case DeclarantWagesOutput.QUOTIENT_INCOMES:
                return [income.to_catala() for income in self.quotient_incomes]

    def to_catala(self) -> StructureLiteral:
        """:return: Every output of the scope, as Catala prints its result."""
        return StructureLiteral(
            structure=Reference(parts=(self.catala_scope,)),
            fields={
                output.value: self.output(output) for output in DeclarantWagesOutput
            },
        )


# %% rates


@dataclass(frozen=True)
class WageDeduction:
    """The flat deduction of article 83 3°."""

    @classproperty
    def rate(cls) -> Fraction:
        """10 %."""
        return Fraction(10, 100)


@dataclass(frozen=True)
class PensionAbatement:
    """The abatement of pensions of article 158 5 a."""

    @classproperty
    def rate(cls) -> Fraction:
        """10 %."""
        return Fraction(10, 100)

    @staticmethod
    def applies_to(kind: PensionKind) -> bool:
        """:return: Whether 158 5 a abates a pension of *kind*: not one in capital of savings plans, nor one at 7.5 % (163 bis)."""
        return kind not in {
            PensionKind.RETIREMENT_SAVINGS_CAPITAL,
            PensionKind.CAPITAL_AT_7_5_PERCENT,
        }


@dataclass(frozen=True)
class FlatLevy:
    """The levy of 163 bis on pensions in capital."""

    @classproperty
    def rate(cls) -> Fraction:
        """7.5 %."""
        return Fraction(75, 1000)


@dataclass(frozen=True)
class ValueSharingBonus:
    """The exemption of the value sharing bonus of loi n° 2022-1158."""

    @classproperty
    def cap(cls) -> Money:
        """3,000 €."""
        return Money.from_euros(3000)

    @classproperty
    def raised_cap(cls) -> Money:
        """6,000 €."""
        return Money.from_euros(6000)


# %% provisions


@dataclass(eq=False)
class YearAmount(CaseAmount):
    """An amount the law sets for the year of the income."""


@dataclass(eq=False)
class RealExpensesApply(CaseCondition):
    """83 3°: the real expenses replace the flat deduction."""


@dataclass
class YearAmountProvision(ScopeProvision):
    """An amount the code sets for each year of income Catala's example states."""

    @classproperty
    def amount_by_year(cls) -> dict[int, Money]:
        """The amount, by year of income."""
        raise NotImplementedError

    def query(self) -> Query:
        case = variable(DeclarantWagesCase, domain=[self.case])
        return RuleChain(
            conclusion=deduced_variable(YearAmount),
            branches=[
                RuleBranch(
                    conditions=(case.income_year == year,),
                    inferred=inference(YearAmount)(case=case, amount=amount),
                )
                for year, amount in self.amount_by_year.items()
            ],
        ).query()


@dataclass
class DeductionCeilingProvision(YearAmountProvision):
    """83 3°: the ceiling of the deduction, 13,522 € for the income of 2022 and 14,171 € for 2023."""

    @classproperty
    def amount_by_year(cls) -> dict[int, Money]:
        """The ceiling, by year of income."""
        return {2022: Money.from_euros(13522), 2023: Money.from_euros(14171)}


@dataclass
class DeductionMinimumProvision(YearAmountProvision):
    """83 3°: the minimum deduction, 472 € for the income of 2022 and 495 € for 2023."""

    @classproperty
    def amount_by_year(cls) -> dict[int, Money]:
        """The minimum, by year of income."""
        return {2022: Money.from_euros(472), 2023: Money.from_euros(495)}


@dataclass
class PensionAbatementMinimumProvision(YearAmountProvision):
    """158 5 a: the minimum abatement, 422 € for the income of 2022 and 442 € for 2023."""

    @classproperty
    def amount_by_year(cls) -> dict[int, Money]:
        """The minimum, by year of income."""
        return {2022: Money.from_euros(422), 2023: Money.from_euros(442)}


@dataclass
class OvertimeExemptionProvision(ScopeProvision):
    """81 quater, from 2022: the overtime and days off, and the tips of article 5 of the amending law of 2022, 7,500 € at most."""

    @classproperty
    def cap(cls) -> Money:
        """7,500 €."""
        return Money.from_euros(7500)

    @classproperty
    def first_year(cls) -> int:
        """2022."""
        return 2022

    def query(self) -> Query:
        case = variable(DeclarantWagesCase, domain=[self.case])
        declaration: WageDeclaration = self.case.declaration
        basis = declaration.exempt_overtime + declaration.exempt_tips
        return RuleChain(
            conclusion=deduced_variable(YearAmount),
            branches=[
                RuleBranch(
                    conditions=(case.income_year >= self.first_year,),
                    inferred=inference(YearAmount)(
                        case=case, amount=min(basis, self.cap)
                    ),
                )
            ],
        ).query()


@dataclass
class RealExpensesProvision(ScopeProvision):
    """83 3°: the real expenses declared replace the deduction where they are not below the capped one."""

    def query(self) -> Query:
        case = variable(DeclarantWagesCase, domain=[self.case])
        expenses = case.declaration.real_expenses
        return RuleChain(
            conclusion=deduced_variable(RealExpensesApply),
            branches=[
                RuleBranch(
                    conditions=(
                        type_(expenses) == ClaimedRealExpenses,
                        expenses.amount >= self.case.capped_deduction,
                    ),
                    inferred=inference(RealExpensesApply)(case=case, holds=True),
                ),
                RuleBranch(
                    conditions=(),
                    inferred=inference(RealExpensesApply)(case=case, holds=False),
                ),
            ],
        ).query()


# %% the tax household


@dataclass(eq=False)
class SecondDeclaration(CatalaVariant):
    """Whether the household has a second declarant, Catala's ``DéclarationTraitementsSalaires2``."""


@dataclass(eq=False)
class NoSecondDeclaration(SecondDeclaration):
    """None, ``PasDeDéclaration``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``PasDeDéclaration``."""
        return "PasDeDéclaration"


@dataclass(eq=False)
class SecondDeclarant(SecondDeclaration):
    """A second declarant, ``Déclaration``, with their declaration."""

    declaration: WageDeclaration | None = None
    """What they declare."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Déclaration``."""
        return "Déclaration"

    @classproperty
    def content_field(cls) -> str:
        """The declaration."""
        return "declaration"


class HouseholdWagesOutput(StrEnum):
    """The outputs of ``TraitementsSalairesFoyerFiscal``."""

    DECLARANTS = "déclarations_avec_résultats_traitements_salaires"
    """The result of each declaration."""

    LIFE_ANNUITIES = "rentes_viagères_titre_onéreux"
    """The taxable part of life annuities."""

    GROSS_TOTAL_INCOME = "revenu_brut_global"
    """The gross total income."""

    GROSS_TOTAL_DEFICIT = "déficit_brut_global"
    """The gross total deficit."""

    QUOTIENT_INCOMES = "revenus_quotientés"
    """The household's incomes taxed by the quotient."""


@dataclass(eq=False)
class HouseholdWagesCase(ScopeCase):
    """The wages and pensions of the tax household, Catala's ``TraitementsSalairesFoyerFiscal``."""

    first_declarant: WageDeclaration
    """The first declarant's declaration."""

    second_declarant: SecondDeclaration
    """The second declarant's, if any."""

    dependants: list[WageDeclaration]
    """The declarations of the persons in the household's charge."""

    income_year: int
    """The year of the income."""

    household: HouseholdWageDeclaration
    """What the household declares besides."""

    @classproperty
    def catala_scope(cls) -> str:
        """``TraitementsSalairesFoyerFiscal``."""
        return "TraitementsSalairesFoyerFiscal"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "déclarant1": "first_declarant",
            "déclarant2": "second_declarant",
            "déclarations_personnes_à_charge": "dependants",
            "année_revenus": "income_year",
            "revenus": "household",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`HouseholdWagesOutput`."""
        return HouseholdWagesOutput

    @cached_property
    def declarations(self) -> list[WageDeclaration]:
        """The first declarant's, the second's if any, and the dependants' declarations."""
        second = (
            [self.second_declarant.declaration]
            if isinstance(self.second_declarant, SecondDeclarant)
            else []
        )
        return [self.first_declarant, *second, *self.dependants]

    @cached_property
    def pension_abatement_ceiling(self) -> Money | None:
        """158 5 a: the household's ceiling of the pension abatement."""
        ceiling = self.sole_conclusion(HouseholdPensionCeilingProvision)
        return None if ceiling is None else ceiling.amount

    @cached_property
    def declarants(self) -> list[DeclarantWagesCase] | None:
        """
        158 5 a: each declaration with the household's ceiling, or its share of it in
        proportion to the uncapped abatements where they reach the ceiling.
        """
        if self.pension_abatement_ceiling is None:
            return None
        uncapped = [
            DeclarantWagesCase(
                declaration=declaration,
                income_year=self.income_year,
                pension_abatement_cap=UncappedPensionAbatement(),
            ).output(DeclarantWagesOutput.PENSION_ABATEMENT)
            for declaration in self.declarations
        ]
        if None in uncapped:
            return None
        ceiling = self.pension_abatement_ceiling
        caps = (
            [ceiling] * len(uncapped)
            if sum(uncapped, Money.zero) < ceiling
            else ProportionalDistribution(amount=ceiling, bases=uncapped).shares()
        )
        return [
            DeclarantWagesCase(
                declaration=declaration,
                income_year=self.income_year,
                pension_abatement_cap=CappedPensionAbatement(cap=cap),
            )
            for declaration, cap in zip(self.declarations, caps)
        ]

    @cached_property
    def life_annuities(self) -> Money:
        """158 6 and 23 B of the OECD model: the taxable share of each life annuity, French and foreign."""
        household = self.household
        return sum(
            (
                LifeAnnuity.taxable(amount, age)
                for amount, age in (
                    (household.annuities_under_50, AnnuityAge.UNDER_50),
                    (household.annuities_from_50_to_59, AnnuityAge.FROM_50_TO_59),
                    (household.annuities_from_60_to_69, AnnuityAge.FROM_60_TO_69),
                    (household.annuities_from_70, AnnuityAge.FROM_70),
                    (household.foreign_annuities_under_50, AnnuityAge.UNDER_50),
                    (
                        household.foreign_annuities_from_50_to_59,
                        AnnuityAge.FROM_50_TO_59,
                    ),
                    (
                        household.foreign_annuities_from_60_to_69,
                        AnnuityAge.FROM_60_TO_69,
                    ),
                    (household.foreign_annuities_from_70, AnnuityAge.FROM_70),
                )
            ),
            Money.zero,
        )

    def output(self, variable: str) -> CatalaValue:
        if self.declarants is None:
            return None
        balance = (
            sum(
                (
                    declarant.output(DeclarantWagesOutput.GROSS_INCOME)
                    for declarant in self.declarants
                ),
                Money.zero,
            )
            + self.life_annuities
            + self.household.free_shares_gain
        )
        match HouseholdWagesOutput(variable):
            case HouseholdWagesOutput.DECLARANTS:
                return [declarant.to_catala() for declarant in self.declarants]
            case HouseholdWagesOutput.LIFE_ANNUITIES:
                return self.life_annuities
            case HouseholdWagesOutput.GROSS_TOTAL_INCOME:
                return max(balance, Money.zero)
            case HouseholdWagesOutput.GROSS_TOTAL_DEFICIT:
                return Money.zero - min(balance, Money.zero)
            case HouseholdWagesOutput.QUOTIENT_INCOMES:
                return [
                    QuotientIncome.from_income(
                        income,
                        LifeAnnuity.deduction(
                            income.amount, income.category.annuity_age
                        )
                        if income.category.kind == IncomeKind.LIFE_ANNUITY
                        else Money.zero,
                        self.income_year,
                    ).to_catala()
                    for income in self.household.exceptional_income
                ]


@dataclass(frozen=True)
class LifeAnnuity:
    """The taxable share of a life annuity of article 158 6, by the annuitant's age when it began."""

    @classproperty
    def taxable_share(cls) -> dict[AnnuityAge, Fraction]:
        """70 % under 50, 50 % from 50 to 59, 40 % from 60 to 69, 30 % from 70."""
        return {
            AnnuityAge.UNDER_50: Fraction(70, 100),
            AnnuityAge.FROM_50_TO_59: Fraction(50, 100),
            AnnuityAge.FROM_60_TO_69: Fraction(40, 100),
            AnnuityAge.FROM_70: Fraction(30, 100),
        }

    @classmethod
    def deduction(cls, amount: Money, age: AnnuityAge) -> Money:
        """:return: The part of *amount* not taxed."""
        return amount * (1 - cls.taxable_share[age])

    @classmethod
    def taxable(cls, amount: Money, age: AnnuityAge) -> Money:
        """:return: The part of *amount* taxed, the annuity less its deduction."""
        return amount - cls.deduction(amount, age)


@dataclass(eq=False)
class HouseholdPensionCeiling(CaseAmount):
    """158 5 a: the ceiling of the household's pension abatement."""


@dataclass
class HouseholdPensionCeilingProvision(ScopeProvision):
    """158 5 a: 4,123 € for the income of 2022, 4,321 € for 2023."""

    @classproperty
    def amount_by_year(cls) -> dict[int, Money]:
        """The ceiling, by year of income."""
        return {2022: Money.from_euros(4123), 2023: Money.from_euros(4321)}

    def query(self) -> Query:
        case = variable(HouseholdWagesCase, domain=[self.case])
        return RuleChain(
            conclusion=deduced_variable(HouseholdPensionCeiling),
            branches=[
                RuleBranch(
                    conditions=(case.income_year == year,),
                    inferred=inference(HouseholdPensionCeiling)(
                        case=case, amount=amount
                    ),
                )
                for year, amount in self.amount_by_year.items()
            ],
        ).query()
