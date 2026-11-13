"""
Industrial and commercial profits (*bénéfices industriels et commerciaux*, BIC) of
articles 34 to 50-0 of the Code général des impôts: of one declarant (Catala's
``BénéficesIndustrielsCommerciauxDéclarant``) and of the tax household
(``BénéficesIndustrielsCommerciauxFoyerFiscal``).
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
class CommercialGeneral(CatalaRecord):
    """
    What a declarant declares of industrial and commercial profits, professional or not,
    Catala's ``DéclarationBénéficesIndustrielsCommerciauxGénéraux``; an empty box is nothing.
    """

    patent_licence_income: Money = field(default_factory=lambda: Money.zero)
    """The income of licensing patents (219)."""

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

    micro_goods: Money = field(default_factory=lambda: Money.zero)
    """The receipts of selling goods of the micro regime."""

    micro_services: Money = field(default_factory=lambda: Money.zero)
    """The receipts of services of the micro regime."""

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
        """The fields of ``DéclarationBénéficesIndustrielsCommerciauxGénéraux``."""
        return {
            "revenus_concession_brevets": "patent_licence_income",
            "plus_values_nettes_court_terme_micro": "micro_short_term_gains",
            "moins_values_nettes_court_terme_micro": "micro_short_term_losses",
            "plus_values_nettes_long_terme_micro": "micro_long_term_gains",
            "moins_values_nettes_long_terme_micro": "micro_long_term_losses",
            "plus_values_nettes_long_terme_réel": "real_long_term_gains",
            "revenus_imposables_micro_marchandises": "micro_goods",
            "revenus_imposables_micro_services": "micro_services",
            "revenus_imposables_réel": "real_taxable",
            "déficit_réel": "real_deficit",
            "revenus_imposables_réel_source_étrangère_imputés": "foreign_taxable_credited",
            "revenus_exceptionnels_ou_différés": "exceptional_income",
        }

    def exceptional_of(self, kinds: frozenset[IncomeKind]) -> list[ExceptionalIncome]:
        """:return: The exceptional income of *kinds*, in order."""
        return [
            income
            for income in self.exceptional_income
            if income.category.kind in kinds
        ]

    def exceptional_besides(
        self, kinds: frozenset[IncomeKind]
    ) -> list[ExceptionalIncome]:
        """:return: The exceptional income of no kind of *kinds*, in order."""
        return [
            income
            for income in self.exceptional_income
            if income.category.kind not in kinds
        ]

    @property
    def real_balance(self) -> Money:
        """The profits of the real regime, those of foreign source credited (23 B of the OECD model), less its deficit."""
        return self.real_taxable + self.foreign_taxable_credited - self.real_deficit


@dataclass(eq=False)
class CommercialNonProfessional(CatalaRecord):
    """The non-professional industrial and commercial profits, Catala's ``DéclarationBénéficesIndustrielsCommerciauxNonProfessionnels``."""

    general: CommercialGeneral = field(default_factory=CommercialGeneral)
    """What is declared as for every such profit."""

    furnished_micro_general: Money = field(default_factory=lambda: Money.zero)
    """Furnished lettings of the micro regime."""

    furnished_micro_classified: Money = field(default_factory=lambda: Money.zero)
    """Classified furnished tourist lettings and guest rooms of the micro regime."""

    furnished_micro_rural: Money = field(default_factory=lambda: Money.zero)
    """Classified lettings in special rural areas of the micro regime."""

    furnished_micro_general_with_contributions: Money = field(
        default_factory=lambda: Money.zero
    )
    """Furnished lettings of the micro regime subject to contributions."""

    furnished_micro_classified_with_contributions: Money = field(
        default_factory=lambda: Money.zero
    )
    """Classified ones subject to contributions."""

    furnished_micro_rural_with_contributions: Money = field(
        default_factory=lambda: Money.zero
    )
    """Rural ones subject to contributions."""

    furnished_real_general: Money = field(default_factory=lambda: Money.zero)
    """Furnished lettings of the real regime."""

    furnished_real_foreign: Money = field(default_factory=lambda: Money.zero)
    """Furnished lettings of the real regime of foreign source."""

    furnished_real_with_contributions: Money = field(default_factory=lambda: Money.zero)
    """Furnished lettings of the real regime subject to contributions."""

    furnished_deficit_general: Money = field(default_factory=lambda: Money.zero)
    """The deficit of furnished lettings."""

    furnished_deficit_with_contributions: Money = field(
        default_factory=lambda: Money.zero
    )
    """The deficit of furnished lettings subject to contributions."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``DéclarationBénéficesIndustrielsCommerciauxNonProfessionnels``."""
        return {
            "généraux": "general",
            "locations_meublées_micro_général": "furnished_micro_general",
            "locations_meublées_micro_hôtes_classées": "furnished_micro_classified",
            "locations_meublées_micro_classées_rurales_spéciales": "furnished_micro_rural",
            "locations_meublées_micro_cotisations_général": "furnished_micro_general_with_contributions",
            "locations_meublées_micro_cotisations_hôtes_classées": "furnished_micro_classified_with_contributions",
            "locations_meublées_micro_cotisations_classées_rurales_spéciales": "furnished_micro_rural_with_contributions",
            "locations_meublées_réel_général": "furnished_real_general",
            "locations_meublées_réel_source_étrangère": "furnished_real_foreign",
            "locations_meublées_réel_cotisations": "furnished_real_with_contributions",
            "locations_meublées_déficit_général": "furnished_deficit_general",
            "locations_meublées_déficit_cotisations": "furnished_deficit_with_contributions",
        }

    @property
    def furnished_micro_goods_like(self) -> Money:
        """The classified and rural furnished lettings, abated as goods are."""
        return (
            self.furnished_micro_classified
            + self.furnished_micro_rural
            + self.furnished_micro_classified_with_contributions
            + self.furnished_micro_rural_with_contributions
        )

    @property
    def furnished_micro_services_like(self) -> Money:
        """The other furnished lettings of the micro regime, abated as services are."""
        return (
            self.furnished_micro_general
            + self.furnished_micro_general_with_contributions
        )

    @property
    def furnished_micro_rural_total(self) -> Money:
        """The rural furnished lettings, which have a special abatement besides."""
        return (
            self.furnished_micro_rural + self.furnished_micro_rural_with_contributions
        )


@dataclass(eq=False)
class CommercialDeclaration(CatalaRecord):
    """What a declarant declares of industrial and commercial profits, Catala's ``DéclarationBénéficesIndustrielsCommerciaux``."""

    professional: CommercialGeneral = field(default_factory=CommercialGeneral)
    """The professional profits."""

    non_professional: CommercialNonProfessional = field(
        default_factory=CommercialNonProfessional
    )
    """The non-professional profits."""

    flat_levy_goods_turnover: Money = field(default_factory=lambda: Money.zero)
    """The turnover of selling goods of a micro-entrepreneur under the flat levy."""

    flat_levy_services_turnover: Money = field(default_factory=lambda: Money.zero)
    """The turnover of services of a micro-entrepreneur under the flat levy."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``DéclarationBénéficesIndustrielsCommerciaux``."""
        return {
            "professionnels": "professional",
            "non_professionnels": "non_professional",
            "chiffre_affaires_prélèvement_libératoire_marchandises_éxonéré_cotisations": "flat_levy_goods_turnover",
            "chiffre_affaires_prélèvement_libératoire_services_éxonéré_cotisations": "flat_levy_services_turnover",
        }


# %% the micro abatements


class MicroAbatementKind(StrEnum):
    """The abatements of the micro regime of article 50-0."""

    GOODS = "marchandises"
    """Of selling goods, 71 %."""

    SERVICES = "services"
    """Of services, 50 %."""

    RURAL = "rurales_spéciales"
    """Special of rural furnished lettings, 21 %."""

    @property
    def rate(self) -> Fraction:
        """The share of the receipts abated."""
        match self:
            case MicroAbatementKind.GOODS:
                return Fraction(71, 100)
            case MicroAbatementKind.SERVICES:
                return Fraction(50, 100)
            case MicroAbatementKind.RURAL:
                return Fraction(21, 100)


@dataclass(frozen=True)
class MicroAbatement:
    """An abatement of the micro regime, the receipts it abates in proportion as nine bases and lists."""

    kind: MicroAbatementKind
    """Which abatement."""

    bases: list[Money]
    """The bases the abatement is shared over, three at most."""

    lists: list[list[Money]]
    """The lists of exceptional incomes it is shared over besides."""

    @property
    def basis(self) -> Money:
        """The receipts abated, every base and exceptional income."""
        return sum(self.bases, Money.zero) + sum(
            (amount for amounts in self.lists for amount in amounts), Money.zero
        )

    @property
    def rounded(self) -> Money:
        """50-0 and 193: the rate of the receipts, rounded to the euro."""
        return (self.basis * self.kind.rate).rounded_to_units()

    def shares(self, amount: Money) -> tuple[list[Money], list[list[Money]]]:
        """:return: *amount* shared in proportion over the bases and the lists, as ``ProRataArrondiEuroBranchement`` shares it."""
        padded = self.bases + [Money.zero] * (9 - len(self.bases))
        flat = ProportionalDistribution(
            amount=amount,
            bases=padded + [base for amounts in self.lists for base in amounts],
        ).shares()
        lists, start = [], 9
        for amounts in self.lists:
            lists.append(flat[start : start + len(amounts)])
            start += len(amounts)
        return flat[: len(self.bases)], lists


# %% the declarant


class CommercialDeclarantOutput(StrEnum):
    """The outputs of ``BénéficesIndustrielsCommerciauxDéclarant``."""

    RURAL_SPECIAL_ABATEMENT = (
        "abattement_spécial_micro_location_meublées_rurales_spéciales"
    )
    """The special abatement of rural furnished lettings."""

    PROFESSIONAL_GOODS_ABATEMENT = (
        "abattement_forfaitaire_micro_professionnel_marchandises"
    )
    """The abatement of professional goods."""

    NON_PROFESSIONAL_GOODS_ABATEMENT = (
        "abattement_forfaitaire_micro_non_professionnel_marchandises"
    )
    """The abatement of non-professional goods."""

    FURNISHED_GOODS_ABATEMENT = (
        "abattement_forfaitaire_micro_non_professionnel_marchandises_locations_meublées"
    )
    """The goods abatement of classified and rural furnished lettings."""

    PROFESSIONAL_SERVICES_ABATEMENT = (
        "abattement_forfaitaire_micro_professionnel_services"
    )
    """The abatement of professional services."""

    NON_PROFESSIONAL_SERVICES_ABATEMENT = (
        "abattement_forfaitaire_micro_non_professionnel_services"
    )
    """The abatement of non-professional services."""

    FURNISHED_SERVICES_ABATEMENT = (
        "abattement_forfaitaire_micro_non_professionnel_services_locations_meublées"
    )
    """The services abatement of other furnished lettings."""

    PROFESSIONAL_QUOTIENT_INCOMES = "revenus_quotientés_professionnels"
    """The professional quotient incomes."""

    NON_PROFESSIONAL_QUOTIENT_INCOMES = "revenus_quotientés_non_professionnels"
    """The non-professional quotient incomes."""

    PROFESSIONAL_BALANCE = "solde_net_professionnel"
    """The net professional balance."""

    NON_PROFESSIONAL_BALANCE = "solde_net_non_professionnel_hors_locations_meublées"
    """The net non-professional balance, furnished lettings aside."""

    FURNISHED_BALANCE = "solde_net_non_professionnel_locations_meublées"
    """The net balance of furnished lettings."""

    MICRO_ENTERPRISE_LEVY = "prélèvement_libératoire_auto_entreprise"
    """The flat levy of a micro-entrepreneur."""

    LONG_TERM_GAINS_LEVY = "prélèvement_libératoire_plus_values_long_terme"
    """The levy on long-term capital gains."""

    PATENT_LEVY = "prélèvement_libératoire_revenus_concession_brevets"
    """The levy on the income of licensing patents."""


@dataclass(eq=False)
class CommercialDeclarantCase(ScopeCase):
    """The industrial and commercial profits of one declarant, Catala's ``BénéficesIndustrielsCommerciauxDéclarant``."""

    declaration: CommercialDeclaration
    """What the declarant declares."""

    income_year: int
    """The year of the income."""

    @classproperty
    def catala_scope(cls) -> str:
        """``BénéficesIndustrielsCommerciauxDéclarant``."""
        return "BénéficesIndustrielsCommerciauxDéclarant"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {"revenus": "declaration", "année_revenus": "income_year"}

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`CommercialDeclarantOutput`."""
        return CommercialDeclarantOutput

    @classproperty
    def minimum_abatement(cls) -> Money:
        """50-0: 305 €."""
        return Money.from_euros(305)

    @classproperty
    def goods_levy_rate(cls) -> Fraction:
        """151-0: 1 % of the turnover of goods."""
        return Fraction(1, 100)

    @classproperty
    def services_levy_rate(cls) -> Fraction:
        """151-0: 1.7 % of the turnover of services."""
        return Fraction(17, 1000)

    @classproperty
    def patent_levy_rate(cls) -> Fraction:
        """219: 10 %."""
        return Fraction(10, 100)

    @property
    def professional(self) -> CommercialGeneral:
        """What the declarant declares of professional profits."""
        return self.declaration.professional

    @property
    def non_professional(self) -> CommercialNonProfessional:
        """What the declarant declares of non-professional profits."""
        return self.declaration.non_professional

    @cached_property
    def abatements(self) -> dict[MicroAbatementKind, MicroAbatement]:
        """50-0: the abatements of goods, services and rural furnished lettings, and what each is shared over."""
        professional, non_professional = self.professional, self.non_professional
        general = non_professional.general
        return {
            MicroAbatementKind.GOODS: MicroAbatement(
                kind=MicroAbatementKind.GOODS,
                bases=[
                    professional.micro_goods,
                    non_professional.furnished_micro_goods_like,
                    general.micro_goods,
                ],
                lists=[
                    [
                        income.amount
                        for income in professional.exceptional_of(
                            Categories.professional_goods
                        )
                    ],
                    [
                        income.amount
                        for income in general.exceptional_of(
                            Categories.non_professional_goods
                        )
                    ],
                    [
                        income.amount
                        for income in general.exceptional_of(Categories.rural)
                    ],
                ],
            ),
            MicroAbatementKind.SERVICES: MicroAbatement(
                kind=MicroAbatementKind.SERVICES,
                bases=[
                    professional.micro_services,
                    non_professional.furnished_micro_services_like,
                    general.micro_services,
                ],
                lists=[
                    [
                        income.amount
                        for income in professional.exceptional_of(
                            Categories.professional_services
                        )
                    ],
                    [
                        income.amount
                        for income in general.exceptional_of(
                            Categories.non_professional_services
                        )
                    ],
                ],
            ),
            MicroAbatementKind.RURAL: MicroAbatement(
                kind=MicroAbatementKind.RURAL,
                bases=[non_professional.furnished_micro_rural_total],
                lists=[
                    [
                        income.amount
                        for income in general.exceptional_of(Categories.rural)
                    ]
                ],
            ),
        }

    @cached_property
    def floored_totals(self) -> dict[MicroAbatementKind, Money]:
        """50-0: the rounded abatements, their total 305 € at least but the total at most, shared back in proportion."""
        rounded = [self.abatements[kind].rounded for kind in MicroAbatementKind]
        total = sum(rounded, Money.zero)
        floored = min(max(total, self.minimum_abatement), total)
        shares = ProportionalDistribution(
            amount=floored, bases=rounded + [Money.zero] * 6
        ).shares()
        return dict(zip(MicroAbatementKind, shares))

    @cached_property
    def shares(self) -> dict[MicroAbatementKind, tuple[list[Money], list[list[Money]]]]:
        """163-0 A and 50-0: each floored abatement shared over its bases and lists."""
        return {
            kind: self.abatements[kind].shares(self.floored_totals[kind])
            for kind in MicroAbatementKind
        }

    def quotient_incomes(
        self,
        groups: list[tuple[list[ExceptionalIncome], list[Money]]],
        others: list[ExceptionalIncome],
    ) -> list[QuotientIncome]:
        """:return: 163-0 A: the incomes of *groups* with their deductions, then *others* without."""
        return [
            QuotientIncome.from_income(income, deduction, self.income_year)
            for incomes, deductions in groups
            for income, deduction in zip(incomes, deductions)
        ] + [
            QuotientIncome.from_income(income, Money.zero, self.income_year)
            for income in others
        ]

    @cached_property
    def professional_quotient_incomes(self) -> list[QuotientIncome]:
        """The professional quotient incomes: services, goods, then the others."""
        professional = self.professional
        return self.quotient_incomes(
            [
                (
                    professional.exceptional_of(Categories.professional_services),
                    self.shares[MicroAbatementKind.SERVICES][1][0],
                ),
                (
                    professional.exceptional_of(Categories.professional_goods),
                    self.shares[MicroAbatementKind.GOODS][1][0],
                ),
            ],
            professional.exceptional_besides(Categories.professional_abated),
        )

    @cached_property
    def non_professional_quotient_incomes(self) -> list[QuotientIncome]:
        """The non-professional quotient incomes: services, goods, rural lettings with both their abatements, then the others."""
        general = self.non_professional.general
        rural_deductions = [
            goods + special
            for goods, special in zip(
                self.shares[MicroAbatementKind.GOODS][1][2],
                self.shares[MicroAbatementKind.RURAL][1][0],
            )
        ]
        return self.quotient_incomes(
            [
                (
                    general.exceptional_of(Categories.non_professional_services),
                    self.shares[MicroAbatementKind.SERVICES][1][1],
                ),
                (
                    general.exceptional_of(Categories.non_professional_goods),
                    self.shares[MicroAbatementKind.GOODS][1][1],
                ),
                (general.exceptional_of(Categories.rural), rural_deductions),
            ],
            general.exceptional_besides(Categories.non_professional_abated),
        )

    def output(self, variable: str) -> CatalaValue:
        goods, _ = self.shares[MicroAbatementKind.GOODS]
        services, _ = self.shares[MicroAbatementKind.SERVICES]
        (rural,), _ = self.shares[MicroAbatementKind.RURAL]
        professional, non_professional = self.professional, self.non_professional
        general = non_professional.general
        match CommercialDeclarantOutput(variable):
            case CommercialDeclarantOutput.RURAL_SPECIAL_ABATEMENT:
                return rural
            case CommercialDeclarantOutput.PROFESSIONAL_GOODS_ABATEMENT:
                return goods[0]
            case CommercialDeclarantOutput.FURNISHED_GOODS_ABATEMENT:
                return goods[1]
            case CommercialDeclarantOutput.NON_PROFESSIONAL_GOODS_ABATEMENT:
                return goods[2]
            case CommercialDeclarantOutput.PROFESSIONAL_SERVICES_ABATEMENT:
                return services[0]
            case CommercialDeclarantOutput.FURNISHED_SERVICES_ABATEMENT:
                return services[1]
            case CommercialDeclarantOutput.NON_PROFESSIONAL_SERVICES_ABATEMENT:
                return services[2]
            case CommercialDeclarantOutput.PROFESSIONAL_QUOTIENT_INCOMES:
                return [
                    income.to_catala() for income in self.professional_quotient_incomes
                ]
            case CommercialDeclarantOutput.NON_PROFESSIONAL_QUOTIENT_INCOMES:
                return [
                    income.to_catala()
                    for income in self.non_professional_quotient_incomes
                ]
            case CommercialDeclarantOutput.PROFESSIONAL_BALANCE:
                return (
                    professional.real_balance
                    + professional.micro_goods
                    - goods[0]
                    + professional.micro_services
                    - services[0]
                    + CapitalGains(
                        professional.micro_short_term_gains,
                        professional.micro_short_term_losses,
                    ).short_term_balance
                )
            case CommercialDeclarantOutput.NON_PROFESSIONAL_BALANCE:
                return (
                    general.real_balance
                    + general.micro_goods
                    - goods[2]
                    + general.micro_services
                    - services[2]
                    + CapitalGains(
                        general.micro_short_term_gains, general.micro_short_term_losses
                    ).short_term_balance
                )
            case CommercialDeclarantOutput.FURNISHED_BALANCE:
                return (
                    non_professional.furnished_real_general
                    + non_professional.furnished_real_with_contributions
                    + non_professional.furnished_real_foreign
                    - non_professional.furnished_deficit_general
                    - non_professional.furnished_deficit_with_contributions
                    + non_professional.furnished_micro_goods_like
                    - goods[1]
                    - rural
                    + non_professional.furnished_micro_services_like
                    - services[1]
                )
            case CommercialDeclarantOutput.MICRO_ENTERPRISE_LEVY:
                return (
                    self.declaration.flat_levy_goods_turnover * self.goods_levy_rate
                    + self.declaration.flat_levy_services_turnover
                    * self.services_levy_rate
                ).rounded_to_units()
            case CommercialDeclarantOutput.LONG_TERM_GAINS_LEVY:
                return (
                    CapitalGains(
                        professional.micro_long_term_gains
                        + general.micro_long_term_gains,
                        professional.micro_long_term_losses
                        + general.micro_long_term_losses,
                    ).long_term_levy
                    + CapitalGains(
                        general.real_long_term_gains
                        + professional.real_long_term_gains,
                        Money.zero,
                    ).long_term_levy
                )
            case CommercialDeclarantOutput.PATENT_LEVY:
                return (
                    professional.patent_licence_income + general.patent_licence_income
                ) * self.patent_levy_rate

    def to_catala(self) -> StructureLiteral:
        """:return: Every output of the scope, as Catala prints its result."""
        return StructureLiteral(
            structure=Reference(parts=(self.catala_scope,)),
            fields={
                output.value: self.output(output)
                for output in CommercialDeclarantOutput
            },
        )


@dataclass(frozen=True)
class Categories:
    """The categories of exceptional income each micro abatement of 50-0 abates."""

    @classproperty
    def professional_goods(cls) -> frozenset[IncomeKind]:
        """Professional micro goods."""
        return frozenset({IncomeKind.MICRO_GOODS})

    @classproperty
    def professional_services(cls) -> frozenset[IncomeKind]:
        """Professional micro services."""
        return frozenset({IncomeKind.MICRO_SERVICES})

    @classproperty
    def professional_abated(cls) -> frozenset[IncomeKind]:
        """Every professional category abated."""
        return cls.professional_goods | cls.professional_services

    @classproperty
    def non_professional_goods(cls) -> frozenset[IncomeKind]:
        """Non-professional micro goods and classified furnished lettings."""
        return frozenset({IncomeKind.MICRO_GOODS, IncomeKind.MICRO_CLASSIFIED_LETTING})

    @classproperty
    def non_professional_services(cls) -> frozenset[IncomeKind]:
        """Non-professional micro services and furnished lettings."""
        return frozenset(
            {IncomeKind.MICRO_SERVICES, IncomeKind.MICRO_FURNISHED_LETTING}
        )

    @classproperty
    def rural(cls) -> frozenset[IncomeKind]:
        """Rural furnished lettings."""
        return frozenset({IncomeKind.MICRO_RURAL_LETTING})

    @classproperty
    def non_professional_abated(cls) -> frozenset[IncomeKind]:
        """Every non-professional category abated."""
        return cls.non_professional_goods | cls.non_professional_services | cls.rural

    @classproperty
    def non_professional_besides_furnished(cls) -> frozenset[IncomeKind]:
        """156: the quotient incomes a non-professional deficit besides furnished lettings is imputed on."""
        return frozenset(
            {IncomeKind.COMMERCIAL, IncomeKind.MICRO_GOODS, IncomeKind.MICRO_SERVICES}
        )

    @classproperty
    def furnished(cls) -> frozenset[IncomeKind]:
        """156: the quotient incomes a deficit of furnished lettings is imputed on."""
        return frozenset(
            {
                IncomeKind.FURNISHED_LETTING,
                IncomeKind.MICRO_FURNISHED_LETTING,
                IncomeKind.MICRO_CLASSIFIED_LETTING,
                IncomeKind.MICRO_RURAL_LETTING,
            }
        )


# %% the tax household


class CommercialHouseholdOutput(StrEnum):
    """The outputs of ``BénéficesIndustrielsCommerciauxFoyerFiscal``."""

    DECLARANTS = "résultats_liquidation_bénéfices_industriels_commerciaux"
    """The result of each declaration."""

    IMPUTED_QUOTIENT_INCOMES = "revenus_non_professionnels_quotientés_imputés"
    """The non-professional quotient incomes, the deficits imputed on them."""

    GROSS_TOTAL_INCOME = "revenu_brut_global"
    """The gross total income."""

    NON_PROFESSIONAL_DEFICIT = (
        "déficit_brut_global_non_professionnel_hors_locations_meublées"
    )
    """The non-professional gross total deficit, furnished lettings aside."""

    PROFESSIONAL_DEFICIT = "déficit_brut_global_professionnel"
    """The professional gross total deficit."""

    FURNISHED_DEFICIT = "déficit_brut_global_non_professionnel_locations_meublées"
    """The gross total deficit of furnished lettings."""

    UPDATED_PAST_DEFICITS = (
        "déficits_réels_années_antérieures_non_professionnels_mis_à_jour"
    )
    """The non-professional deficits of past years left."""

    UPDATED_PAST_FURNISHED_DEFICITS = "déficits_réels_années_antérieures_non_professionnels_locations_meublées_mis_à_jour"
    """The deficits of furnished lettings of past years left."""


@dataclass(eq=False)
class CommercialHouseholdCase(ScopeCase):
    """The industrial and commercial profits of the tax household, Catala's ``BénéficesIndustrielsCommerciauxFoyerFiscal``."""

    income_year: int
    """The year of the income."""

    declarations: list[CommercialDeclaration]
    """What each declarant declares."""

    past_non_professional_deficits: list[PastDeficit]
    """The non-professional deficits of the real regime of past years."""

    past_furnished_deficits: list[PastDeficit]
    """The deficits of furnished lettings of past years."""

    @classproperty
    def catala_scope(cls) -> str:
        """``BénéficesIndustrielsCommerciauxFoyerFiscal``."""
        return "BénéficesIndustrielsCommerciauxFoyerFiscal"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "année_revenus": "income_year",
            "revenus": "declarations",
            "déficits_réels_années_antérieures_non_professionnels": "past_non_professional_deficits",
            "déficits_réels_années_antérieures_non_professionnels_locations_meublées": "past_furnished_deficits",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`CommercialHouseholdOutput`."""
        return CommercialHouseholdOutput

    @classproperty
    def carry_forward_years(cls) -> int:
        """156 I 1°: the deficits of the six years before."""
        return 6

    @classproperty
    def furnished_carry_forward_years(cls) -> int:
        """156 I 1° ter: the deficits of furnished lettings of the ten years before."""
        return 10

    @cached_property
    def declarants(self) -> list[CommercialDeclarantCase]:
        """Each declaration's result."""
        return [
            CommercialDeclarantCase(
                declaration=declaration, income_year=self.income_year
            )
            for declaration in self.declarations
        ]

    def total(self, output: CommercialDeclarantOutput) -> Money:
        """:return: The sum of *output* over the declarants."""
        return sum(
            (declarant.output(output) for declarant in self.declarants), Money.zero
        )

    def quotient_imputation(
        self, output: CommercialDeclarantOutput, kinds: frozenset[IncomeKind]
    ) -> QuotientDeficitImputation:
        """:return: 156: the deficit of *output* imputed on the non-professional quotient incomes of *kinds*."""
        return QuotientDeficitImputation(
            balance=self.total(output),
            quotient_incomes=[
                [
                    income
                    for income in declarant.non_professional_quotient_incomes
                    if income.category.kind in kinds
                ]
                for declarant in self.declarants
            ],
        )

    @cached_property
    def non_professional_imputation(self) -> QuotientDeficitImputation:
        """The non-professional deficit besides furnished lettings on its quotient incomes."""
        return self.quotient_imputation(
            CommercialDeclarantOutput.NON_PROFESSIONAL_BALANCE,
            Categories.non_professional_besides_furnished,
        )

    @cached_property
    def furnished_imputation(self) -> QuotientDeficitImputation:
        """The deficit of furnished lettings on its quotient incomes."""
        return self.quotient_imputation(
            CommercialDeclarantOutput.FURNISHED_BALANCE, Categories.furnished
        )

    def past_imputation(
        self,
        imputation: QuotientDeficitImputation,
        deficits: list[PastDeficit],
        years: int,
    ) -> DeficitImputation:
        """:return: 156: the balance left after *imputation* imputed on the *deficits* of the *years* before, oldest first."""
        return DeficitImputation.from_income(
            imputation.balance + imputation.imputed_deficit,
            [
                deficit
                for deficit in deficits
                if deficit.year >= self.income_year - years
            ],
        )

    def output(self, variable: str) -> CatalaValue:
        professional = self.total(CommercialDeclarantOutput.PROFESSIONAL_BALANCE)
        non_professional = self.past_imputation(
            self.non_professional_imputation,
            self.past_non_professional_deficits,
            self.carry_forward_years,
        )
        furnished = self.past_imputation(
            self.furnished_imputation,
            self.past_furnished_deficits,
            self.furnished_carry_forward_years,
        )
        match CommercialHouseholdOutput(variable):
            case CommercialHouseholdOutput.DECLARANTS:
                return [declarant.to_catala() for declarant in self.declarants]
            case CommercialHouseholdOutput.IMPUTED_QUOTIENT_INCOMES:
                return [
                    [income.to_catala() for income in incomes]
                    for imputation in (
                        self.non_professional_imputation,
                        self.furnished_imputation,
                    )
                    for incomes in imputation.imputed_incomes
                ]
            case CommercialHouseholdOutput.GROSS_TOTAL_INCOME:
                return (
                    max(professional, Money.zero)
                    + max(non_professional.imputed_income, Money.zero)
                    + max(furnished.imputed_income, Money.zero)
                )
            case CommercialHouseholdOutput.NON_PROFESSIONAL_DEFICIT:
                return Money.zero - min(non_professional.imputed_income, Money.zero)
            case CommercialHouseholdOutput.PROFESSIONAL_DEFICIT:
                return Money.zero - min(professional, Money.zero)
            case CommercialHouseholdOutput.FURNISHED_DEFICIT:
                return Money.zero - min(furnished.imputed_income, Money.zero)
            case CommercialHouseholdOutput.UPDATED_PAST_DEFICITS:
                return [
                    deficit.to_catala()
                    for deficit in non_professional.remaining_deficits
                ]
            case CommercialHouseholdOutput.UPDATED_PAST_FURNISHED_DEFICITS:
                return [deficit.to_catala() for deficit in furnished.remaining_deficits]
