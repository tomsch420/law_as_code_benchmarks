"""
Taxable income as rules over the domain model: the totals of personal exemptions (`§ 151 <https://www.law.cornell.edu/uscode/text/26/151>`__),
the overall limitation on itemized deductions (`§ 68 <https://www.law.cornell.edu/uscode/text/26/68>`__) and taxable income with the standard
deduction (`§ 63 <https://www.law.cornell.edu/uscode/text/26/63>`__).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from krrood.entity_query_language.factories import (
    an,
    and_,
    entity,
    exists,
    inference,
    not_,
    or_,
    variable,
)
from krrood.entity_query_language.factories import sum as total
from krrood.entity_query_language.predicate import symbolic_function
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.sara.domain import (
    Birth,
    Blindness,
    BusinessTrustStatus,
    CalendarYear,
    ItemizedDeduction,
    NonresidentAlienStatus,
    Party,
)
from law_as_code_benchmarks.sara.family_status import (
    ApplicableAmountTest,
    DependentExemptionAmountTest,
    ExemptionAmountTest,
    ExemptionForDependentTest,
    ExemptionForSpouseTest,
    GrossIncomeOfParty,
    HeadOfHouseholdTest,
    JointFilingTest,
    MarriedIndividualTest,
    SurvivingSpouseTest,
)
from law_as_code_benchmarks.sara.family_status_conclusions import (
    AnnualDependency,
    ApplicableAmount,
    DependentExemptionAmount,
    ExemptionAmount,
    ExemptionForSpouse,
    GrossIncome,
    HeadOfHousehold,
    JointFiling,
    MarriedIndividual,
    SurvivingSpouse,
)
from law_as_code_benchmarks.sara.provision import (
    ConclusionType,
    Provision,
    SaraPredicate,
)
from law_as_code_benchmarks.sara.taxable_income_conclusions import (
    AdditionalAmountsForAgedOrBlind,
    AdditionalStandardDeduction,
    AgedCount,
    AgedOrBlindAmounts,
    AgedSpouse,
    AgedTaxpayer,
    AllowedExemptions,
    BasicAmountInOtherCases,
    BasicStandardDeduction,
    BlindCount,
    BlindSpouse,
    BlindTaxpayer,
    DependentBasicAmountLimit,
    DoubledBasicAmount,
    ExcessIncomeReduction,
    ExemptionDeductions,
    HeadOfHouseholdBasicAmount,
    HigherAdditionalAmount,
    IneligibleForStandardDeduction,
    ItemizedDeductionLimitation,
    ItemizedDeductionReduction,
    ItemizedDeductions,
    JointReturnDoubling,
    LimitedBasicStandardDeduction,
    LimitedItemizedDeductions,
    NonresidentAlienIndividual,
    PersonalExemptions,
    SpouseExemption,
    SpouseItemizing,
    StandardDeduction,
    StandardDeductionUnderGeneralRule,
    SurvivingSpouseDoubling,
    SuspendedLimitation,
    TaxableIncome,
    TaxableIncomeInGeneral,
    TaxableIncomeWithoutItemizing,
    TaxpayerAmount,
    TaxpayerConclusion,
    TaxpayerExemption,
    TaxpayerOrSpouseExemption,
    TemporaryBasicAmountForHeadOfHousehold,
    TemporaryBasicAmountInOtherCases,
    TrustOrPartnership,
)

# %% totals of personal exemptions


@dataclass
class TaxpayerOrSpouseExemptionTest(Provision[TaxpayerOrSpouseExemption]):
    """
    `§ 151(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__: an exemption of the exemption amount for every taxpayer, and an additional
    one for a spouse they are allowed an exemption for.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.TAXPAYER_OR_SPOUSE_EXEMPTION`.
        """
        return SaraPredicate.TAXPAYER_OR_SPOUSE_EXEMPTION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The last argument, of either arity.
        """
        return -1

    def query(self) -> Query:
        amount = variable(
            ExemptionAmount, domain=ExemptionAmountTest(world=self.world).conclusions
        )
        spouse = variable(
            ExemptionForSpouse,
            domain=ExemptionForSpouseTest(world=self.world).conclusions,
        )
        exemption = variable(
            TaxpayerOrSpouseExemption,
            domain=an(
                entity(
                    inference(TaxpayerExemption)(
                        taxpayer=amount.taxpayer, amount=amount.amount, year=amount.year
                    )
                )
            ).tolist()
            + an(
                entity(
                    inference(SpouseExemption)(
                        taxpayer=amount.taxpayer,
                        amount=amount.amount,
                        year=amount.year,
                        spouse=spouse.individual,
                    )
                ).where(spouse.taxpayer == amount.taxpayer, spouse.year == amount.year)
            ).tolist(),
        )
        return an(entity(exemption))


@dataclass
class PersonalExemptionsTest(Provision[PersonalExemptions]):
    """
    `§ 151 <https://www.law.cornell.edu/uscode/text/26/151>`__: the exemptions of `(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__ and `(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__ a taxpayer deducts, each person once, and those
    of their spouse where the two make a joint return.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.PERSONAL_EXEMPTIONS`.
        """
        return SaraPredicate.PERSONAL_EXEMPTIONS

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fifth argument.
        """
        return 4

    def query(self) -> Query:
        individual = self.individual_exemptions()
        exemptions = variable(PersonalExemptions, domain=individual)
        spouse_exemptions = variable(PersonalExemptions, domain=individual)
        filing = variable(
            JointFiling, domain=JointFilingTest(world=self.world).conclusions
        )
        other_filing = variable(
            JointFiling, domain=JointFilingTest(world=self.world).conclusions
        )
        combined = variable(
            PersonalExemptions,
            domain=an(
                entity(exemptions).where(
                    not_(
                        exists(
                            filing,
                            and_(
                                filing.individual == exemptions.taxpayer,
                                filing.year == exemptions.year,
                            ),
                        )
                    )
                )
            ).tolist()
            + an(
                entity(
                    inference(PersonalExemptions)(
                        taxpayer=exemptions.taxpayer,
                        total=exemptions.total + spouse_exemptions.total,
                        year=exemptions.year,
                        persons=exemptions.persons + spouse_exemptions.persons,
                        amounts=exemptions.amounts + spouse_exemptions.amounts,
                    )
                ).where(
                    other_filing.individual == exemptions.taxpayer,
                    other_filing.spouse == spouse_exemptions.taxpayer,
                    other_filing.year == exemptions.year,
                    spouse_exemptions.year == exemptions.year,
                )
            ).tolist(),
        )
        return an(entity(combined))

    def individual_exemptions(self) -> list[PersonalExemptions]:
        """:return: The exemptions each taxpayer deducts for each year by themself: theirs, then their spouse's and dependents', each person once."""
        exemptions = TaxpayerOrSpouseExemptionTest(world=self.world).conclusions
        spouse_exemptions = [
            exemption
            for exemption in exemptions
            if isinstance(exemption, SpouseExemption)
        ]
        dependent_exemptions = DependentExemptionAmountTest(
            world=self.world
        ).conclusions
        return [
            self.exemptions_of(own, spouse_exemptions, dependent_exemptions)
            for own in exemptions
            if isinstance(own, TaxpayerExemption)
        ]

    @staticmethod
    def exemptions_of(
        own: TaxpayerExemption,
        spouse_exemptions: list[SpouseExemption],
        dependent_exemptions: list[DependentExemptionAmount],
    ) -> PersonalExemptions:
        """:return: The taxpayer's own exemption, then each of their spouse and dependent exemptions of the year, each person and amount once."""
        pairs = [(own.taxpayer, own.amount)]
        for person, amount in [
            (exemption.spouse, exemption.amount)
            for exemption in spouse_exemptions
            if exemption.taxpayer is own.taxpayer and exemption.year == own.year
        ] + [
            (exemption.individual, exemption.amount)
            for exemption in dependent_exemptions
            if exemption.taxpayer is own.taxpayer and exemption.year == own.year
        ]:
            if not any(
                known is person and known_amount == amount
                for known, known_amount in pairs
            ):
                pairs.append((person, amount))
        return PersonalExemptions(
            taxpayer=own.taxpayer,
            total=sum(amount for _, amount in pairs),
            year=own.year,
            persons=[person for person, _ in pairs],
            amounts=[amount for _, amount in pairs],
        )


@dataclass
class AllowedExemptionsTest(Provision[AllowedExemptions]):
    """
    `§ 151(a) <https://www.law.cornell.edu/uscode/text/26/151#a>`__: the sum of the exemptions a taxpayer deducts, allowed as deductions.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.ALLOWED_EXEMPTIONS`.
        """
        return SaraPredicate.ALLOWED_EXEMPTIONS

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        exemptions = variable(
            PersonalExemptions,
            domain=[
                exemptions
                for exemptions in PersonalExemptionsTest(world=self.world).conclusions
                if exemptions.total is not None
            ],
        )
        return an(
            entity(
                inference(AllowedExemptions)(
                    taxpayer=exemptions.taxpayer,
                    year=exemptions.year,
                    amount=exemptions.total,
                )
            )
        )


# %% itemized deductions and their limitation


@dataclass
class ItemizedDeductionsTest(Provision[ItemizedDeductions]):
    """
    `§ 63(d) <https://www.law.cornell.edu/uscode/text/26/63#d>`__: the deductions a taxpayer claims in a calendar year, where they claim any.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.ITEMIZED_DEDUCTIONS`.
        """
        return SaraPredicate.ITEMIZED_DEDUCTIONS

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        deduction = variable(
            ItemizedDeduction,
            domain=[
                deduction
                for deduction in self.world.itemized_deductions
                if deduction.day is not None and deduction.amount is not None
            ],
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(ItemizedDeductions)(
                    taxpayer=deduction.claimant,
                    total=total(deduction.amount, default=0),
                    year=year.number,
                )
            )
            .where(deduction.day >= year.opening_day, deduction.day <= year.closing_day)
            .grouped_by(deduction.claimant, year.number)
        )


@dataclass
class ExemptionDeductionsTest(Provision[ExemptionDeductions]):
    """
    `§ 63(d)(2) <https://www.law.cornell.edu/uscode/text/26/63#d_2>`__: the deduction for personal exemptions, which is no itemized deduction.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.EXEMPTION_DEDUCTIONS`.
        """
        return SaraPredicate.EXEMPTION_DEDUCTIONS

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        exemptions = variable(
            PersonalExemptions,
            domain=PersonalExemptionsTest(world=self.world).conclusions,
        )
        return an(entity(inference(ExemptionDeductions)(exemptions=exemptions)))


@dataclass
class SuspendedLimitationTest(Provision[SuspendedLimitation]):
    """
    `§ 68(f) <https://www.law.cornell.edu/uscode/text/26/68#f>`__: taxable years beginning after 2017 and before 2026, which `§ 68 <https://www.law.cornell.edu/uscode/text/26/68>`__ does not
    apply to.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SUSPENDED_LIMITATION`.
        """
        return SaraPredicate.SUSPENDED_LIMITATION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The first argument.
        """
        return 0

    @classproperty
    def first_year(cls) -> int:
        """
        The first calendar year `§ 68 <https://www.law.cornell.edu/uscode/text/26/68>`__ does not apply to.
        """
        return 2018

    @classproperty
    def last_year(cls) -> int:
        """
        The last calendar year `§ 68 <https://www.law.cornell.edu/uscode/text/26/68>`__ does not apply to.
        """
        return 2025

    def query(self) -> Query:
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(inference(SuspendedLimitation)(year=year.number)).where(
                year.number >= self.first_year, year.number <= self.last_year
            )
        )


@dataclass
class ExcessIncomeReductionTest(Provision[ExcessIncomeReduction]):
    """
    `§ 68(a)(1) <https://www.law.cornell.edu/uscode/text/26/68#a_1>`__: 3 percent of the excess of a taxpayer's gross income over their applicable
    amount.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.EXCESS_INCOME_REDUCTION`.
        """
        return SaraPredicate.EXCESS_INCOME_REDUCTION

    @classproperty
    def percentage(cls) -> float:
        """
        The share of the excess.
        """
        return 3

    def query(self) -> Query:
        income = variable(
            GrossIncome, domain=GrossIncomeOfParty(world=self.world).conclusions
        )
        applicable_amount = variable(
            ApplicableAmount, domain=ApplicableAmountTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(ExcessIncomeReduction)(
                    gross_income=income.amount,
                    applicable_amount=applicable_amount.amount,
                    reduction=Provision.share_in_whole_dollars(
                        income.amount - applicable_amount.amount, self.percentage
                    ),
                )
            ).where(
                applicable_amount.taxpayer == income.person,
                applicable_amount.year == income.year,
            )
        )


@dataclass
class ItemizedDeductionReductionTest(Provision[ItemizedDeductionReduction]):
    """
    `§ 68(a)(2) <https://www.law.cornell.edu/uscode/text/26/68#a_2>`__: 80 percent of a taxpayer's itemized deductions.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.ITEMIZED_DEDUCTION_REDUCTION`.
        """
        return SaraPredicate.ITEMIZED_DEDUCTION_REDUCTION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    @classproperty
    def percentage(cls) -> float:
        """
        The share of the itemized deductions.
        """
        return 80

    def query(self) -> Query:
        deductions = variable(
            ItemizedDeductions,
            domain=ItemizedDeductionsTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(ItemizedDeductionReduction)(
                    itemized_deductions=deductions,
                    reduction=Provision.share_in_whole_dollars(
                        deductions.total, self.percentage
                    ),
                )
            )
        )


@dataclass
class ItemizedDeductionLimitationTest(Provision[ItemizedDeductionLimitation]):
    """
    `§ 68(a) <https://www.law.cornell.edu/uscode/text/26/68#a>`__: where a taxpayer's gross income exceeds their applicable amount, their itemized
    deductions are reduced by the lesser of `(1) <https://www.law.cornell.edu/uscode/text/26/68#a_1>`__ and `(2) <https://www.law.cornell.edu/uscode/text/26/68#a_2>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.ITEMIZED_DEDUCTION_LIMITATION`.
        """
        return SaraPredicate.ITEMIZED_DEDUCTION_LIMITATION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The sixth argument.
        """
        return 5

    def query(self) -> Query:
        limitation = variable(
            ItemizedDeductionLimitation,
            domain=self.limitations(excess_is_lesser=True)
            + self.limitations(excess_is_lesser=False),
        )
        return an(entity(limitation))

    def limitations(self, excess_is_lesser: bool) -> list[ItemizedDeductionLimitation]:
        """:return: The limitations where the reduction of `(1) <https://www.law.cornell.edu/uscode/text/26/68#a_1>`__ is the lesser, or where that of `(2) <https://www.law.cornell.edu/uscode/text/26/68#a_2>`__ is."""
        income = variable(
            GrossIncome, domain=GrossIncomeOfParty(world=self.world).conclusions
        )
        applicable_amount = variable(
            ApplicableAmount, domain=ApplicableAmountTest(world=self.world).conclusions
        )
        excess = variable(
            ExcessIncomeReduction,
            domain=ExcessIncomeReductionTest(world=self.world).conclusions,
        )
        reduction = variable(
            ItemizedDeductionReduction,
            domain=ItemizedDeductionReductionTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(ItemizedDeductionLimitation)(
                    taxpayer=income.person,
                    gross_income=income.amount,
                    applicable_amount=applicable_amount.amount,
                    itemized_total=reduction.itemized_deductions.total,
                    reduction=excess.reduction
                    if excess_is_lesser
                    else reduction.reduction,
                    year=income.year,
                )
            ).where(
                applicable_amount.taxpayer == income.person,
                applicable_amount.year == income.year,
                income.amount > applicable_amount.amount,
                excess.gross_income == income.amount,
                excess.applicable_amount == applicable_amount.amount,
                reduction.itemized_deductions.taxpayer == income.person,
                reduction.itemized_deductions.year == income.year,
                excess.reduction <= reduction.reduction
                if excess_is_lesser
                else excess.reduction > reduction.reduction,
            )
        ).tolist()


@dataclass
class LimitedItemizedDeductionsTest(Provision[LimitedItemizedDeductions]):
    """
    `§ 68 <https://www.law.cornell.edu/uscode/text/26/68>`__: a taxpayer's itemized deductions, less the reduction of `(a) <https://www.law.cornell.edu/uscode/text/26/68#a>`__ unless `(f) <https://www.law.cornell.edu/uscode/text/26/68#f>`__ suspends
    the limitation.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.LIMITED_ITEMIZED_DEDUCTIONS`.
        """
        return SaraPredicate.LIMITED_ITEMIZED_DEDUCTIONS

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        deductions = variable(
            ItemizedDeductions,
            domain=ItemizedDeductionsTest(world=self.world).conclusions,
        )
        limitation = variable(
            ItemizedDeductionLimitation,
            domain=ItemizedDeductionLimitationTest(world=self.world).conclusions,
        )
        other_limitation = variable(
            ItemizedDeductionLimitation,
            domain=ItemizedDeductionLimitationTest(world=self.world).conclusions,
        )
        suspended = variable(
            SuspendedLimitation,
            domain=SuspendedLimitationTest(world=self.world).conclusions,
        )
        other_suspended = variable(
            SuspendedLimitation,
            domain=SuspendedLimitationTest(world=self.world).conclusions,
        )
        limited = variable(
            LimitedItemizedDeductions,
            domain=an(
                entity(
                    inference(LimitedItemizedDeductions)(
                        taxpayer=deductions.taxpayer,
                        before=deductions.total,
                        after=deductions.total - limitation.reduction,
                        year=deductions.year,
                    )
                ).where(
                    not_(exists(suspended, suspended.year == deductions.year)),
                    limitation.taxpayer == deductions.taxpayer,
                    limitation.year == deductions.year,
                    limitation.itemized_total == deductions.total,
                )
            ).tolist()
            + an(
                entity(
                    inference(LimitedItemizedDeductions)(
                        taxpayer=deductions.taxpayer,
                        before=deductions.total,
                        after=deductions.total,
                        year=deductions.year,
                    )
                ).where(
                    or_(
                        exists(
                            other_suspended, other_suspended.year == deductions.year
                        ),
                        not_(
                            exists(
                                other_limitation,
                                and_(
                                    other_limitation.taxpayer == deductions.taxpayer,
                                    other_limitation.year == deductions.year,
                                    other_limitation.itemized_total == deductions.total,
                                ),
                            )
                        ),
                    )
                )
            ).tolist(),
        )
        return an(entity(limited))


# %% basic standard deduction


@dataclass
class TemporaryBasicAmountTest(Provision[ConclusionType], ABC):
    """
    `§ 63(c)(7) <https://www.law.cornell.edu/uscode/text/26/63#c_7>`__: an amount `(2) <https://www.law.cornell.edu/uscode/text/26/63#c_2>`__ takes for taxable years beginning after 2017 and
    before 2026.
    """

    @classproperty
    def year_position(cls) -> int | None:
        """
        The first argument.
        """
        return 0

    @classproperty
    def first_year(cls) -> int:
        """
        The first calendar year the amount is taken for.
        """
        return 2018

    @classproperty
    def last_year(cls) -> int:
        """
        The last calendar year the amount is taken for.
        """
        return 2025

    @classproperty
    @abstractmethod
    def amount(cls) -> float:
        """
        The amount.
        """

    def query(self) -> Query:
        conclusion_type = self.get_type_of_generic_parameter(parameter=ConclusionType)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(conclusion_type)(year=year.number, amount=self.amount)
            ).where(year.number >= self.first_year, year.number <= self.last_year)
        )


@dataclass
class TemporaryBasicAmountForHeadOfHouseholdTest(
    TemporaryBasicAmountTest[TemporaryBasicAmountForHeadOfHousehold]
):
    """
    `§ 63(c)(7)(i) <https://www.law.cornell.edu/uscode/text/26/63#c_7>`__: $18,000 in place of $4,400 for a head of household.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.TEMPORARY_BASIC_AMOUNT_FOR_HEAD_OF_HOUSEHOLD`.
        """
        return SaraPredicate.TEMPORARY_BASIC_AMOUNT_FOR_HEAD_OF_HOUSEHOLD

    @classproperty
    def amount(cls) -> float:
        """
        The amount.
        """
        return 18_000


@dataclass
class TemporaryBasicAmountInOtherCasesTest(
    TemporaryBasicAmountTest[TemporaryBasicAmountInOtherCases]
):
    """
    `§ 63(c)(7)(ii) <https://www.law.cornell.edu/uscode/text/26/63#c_7>`__: $12,000 in place of $3,000 in any other case.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.TEMPORARY_BASIC_AMOUNT_IN_OTHER_CASES`.
        """
        return SaraPredicate.TEMPORARY_BASIC_AMOUNT_IN_OTHER_CASES

    @classproperty
    def amount(cls) -> float:
        """
        The amount.
        """
        return 12_000


@dataclass
class BasicAmountInOtherCasesTest(Provision[BasicAmountInOtherCases]):
    """
    `§ 63(c)(2)(C) <https://www.law.cornell.edu/uscode/text/26/63#c_2_C>`__: $3,000, or the amount of `(7)(ii) <https://www.law.cornell.edu/uscode/text/26/63#c_7>`__ where it applies.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.BASIC_AMOUNT_IN_OTHER_CASES`.
        """
        return SaraPredicate.BASIC_AMOUNT_IN_OTHER_CASES

    @classproperty
    def year_position(cls) -> int | None:
        """
        The first argument.
        """
        return 0

    @classproperty
    def amount(cls) -> float:
        """
        The amount.
        """
        return 3_000

    def query(self) -> Query:
        temporary = variable(
            TemporaryBasicAmountInOtherCases,
            domain=TemporaryBasicAmountInOtherCasesTest(world=self.world).conclusions,
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        amount = variable(
            BasicAmountInOtherCases,
            domain=an(
                entity(
                    inference(BasicAmountInOtherCases)(
                        year=temporary.year, amount=temporary.amount
                    )
                )
            ).tolist()
            + an(
                entity(
                    inference(BasicAmountInOtherCases)(
                        year=year.number, amount=self.amount
                    )
                ).where(not_(exists(temporary, temporary.year == year.number)))
            ).tolist(),
        )
        return an(entity(amount))


@dataclass
class HeadOfHouseholdBasicAmountTest(Provision[HeadOfHouseholdBasicAmount]):
    """
    `§ 63(c)(2)(B) <https://www.law.cornell.edu/uscode/text/26/63#c_2_B>`__: $4,400 for a head of household, or the amount of `(7)(i) <https://www.law.cornell.edu/uscode/text/26/63#c_7>`__ where it
    applies.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HEAD_OF_HOUSEHOLD_BASIC_AMOUNT`.
        """
        return SaraPredicate.HEAD_OF_HOUSEHOLD_BASIC_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    @classproperty
    def amount(cls) -> float:
        """
        The amount.
        """
        return 4_400

    def query(self) -> Query:
        head = variable(
            HeadOfHousehold, domain=HeadOfHouseholdTest(world=self.world).conclusions
        )
        temporary = variable(
            TemporaryBasicAmountForHeadOfHousehold,
            domain=TemporaryBasicAmountForHeadOfHouseholdTest(
                world=self.world
            ).conclusions,
        )
        other_temporary = variable(
            TemporaryBasicAmountForHeadOfHousehold,
            domain=TemporaryBasicAmountForHeadOfHouseholdTest(
                world=self.world
            ).conclusions,
        )
        amount = variable(
            HeadOfHouseholdBasicAmount,
            domain=an(
                entity(
                    inference(HeadOfHouseholdBasicAmount)(
                        taxpayer=head.taxpayer, year=head.year, amount=temporary.amount
                    )
                ).where(temporary.year == head.year)
            ).tolist()
            + an(
                entity(
                    inference(HeadOfHouseholdBasicAmount)(
                        taxpayer=head.taxpayer, year=head.year, amount=self.amount
                    )
                ).where(
                    not_(exists(other_temporary, other_temporary.year == head.year))
                )
            ).tolist(),
        )
        return an(entity(amount))


@dataclass
class JointReturnDoublingTest(Provision[JointReturnDoubling]):
    """
    `§ 63(c)(2)(A)(i) <https://www.law.cornell.edu/uscode/text/26/63#c_2_A_i>`__: a married taxpayer making a joint return with their spouse.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.JOINT_RETURN_DOUBLING`.
        """
        return SaraPredicate.JOINT_RETURN_DOUBLING

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        filing = variable(
            JointFiling, domain=JointFilingTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(JointReturnDoubling)(
                    taxpayer=filing.individual,
                    year=filing.year,
                    joint_return=filing.joint_return,
                )
            )
        )


@dataclass
class SurvivingSpouseDoublingTest(Provision[SurvivingSpouseDoubling]):
    """
    `§ 63(c)(2)(A)(ii) <https://www.law.cornell.edu/uscode/text/26/63#c_2_A_ii>`__: a surviving spouse under `§ 2(a) <https://www.law.cornell.edu/uscode/text/26/2#a>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SURVIVING_SPOUSE_DOUBLING`.
        """
        return SaraPredicate.SURVIVING_SPOUSE_DOUBLING

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        survivor = variable(
            SurvivingSpouse, domain=SurvivingSpouseTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(SurvivingSpouseDoubling)(
                    taxpayer=survivor.taxpayer, year=survivor.year
                )
            )
        )


@dataclass
class DoubledBasicAmountTest(Provision[DoubledBasicAmount]):
    """
    `§ 63(c)(2)(A) <https://www.law.cornell.edu/uscode/text/26/63#c_2_A>`__: 200 percent of the amount of `(C) <https://www.law.cornell.edu/uscode/text/26/63#c_2_C>`__ for a joint return `(i) <https://www.law.cornell.edu/uscode/text/26/63#c_2_A_i>`__ or a
    surviving spouse `(ii) <https://www.law.cornell.edu/uscode/text/26/63#c_2_A_ii>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.DOUBLED_BASIC_AMOUNT`.
        """
        return SaraPredicate.DOUBLED_BASIC_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    @classproperty
    def multiplier(cls) -> float:
        """
        The multiple of the amount of `(C) <https://www.law.cornell.edu/uscode/text/26/63#c_2_C>`__.
        """
        return 2

    def query(self) -> Query:
        doubling = variable(
            TaxpayerConclusion,
            domain=JointReturnDoublingTest(world=self.world).conclusions
            + SurvivingSpouseDoublingTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(DoubledBasicAmount)(
                    taxpayer=doubling.taxpayer,
                    year=doubling.year,
                    amount=self.multiplier,
                )
            )
        )


@dataclass
class BasicStandardDeductionTest(Provision[BasicStandardDeduction]):
    """
    `§ 63(c)(2) <https://www.law.cornell.edu/uscode/text/26/63#c_2>`__: the doubled amount of `(A) <https://www.law.cornell.edu/uscode/text/26/63#c_2_A>`__ for a taxpayer who is no head of household,
    that of `(B) <https://www.law.cornell.edu/uscode/text/26/63#c_2_B>`__ for one not under `(A) <https://www.law.cornell.edu/uscode/text/26/63#c_2_A>`__, and that of `(C) <https://www.law.cornell.edu/uscode/text/26/63#c_2_C>`__ otherwise.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.BASIC_STANDARD_DEDUCTION`.
        """
        return SaraPredicate.BASIC_STANDARD_DEDUCTION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        taxpayer = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        other_cases = variable(
            BasicAmountInOtherCases,
            domain=BasicAmountInOtherCasesTest(world=self.world).conclusions,
        )
        amount = variable(
            BasicStandardDeduction,
            domain=an(
                entity(
                    inference(BasicStandardDeduction)(
                        taxpayer=taxpayer,
                        year=year.number,
                        amount=DoubledBasicAmountTest.multiplier * other_cases.amount,
                    )
                ).where(
                    other_cases.year == year.number,
                    self.is_doubled(taxpayer, year),
                    not_(self.is_head_of_household(taxpayer, year)),
                )
            ).tolist()
            + self.head_of_household_amounts()
            + an(
                entity(
                    inference(BasicStandardDeduction)(
                        taxpayer=taxpayer, year=year.number, amount=other_cases.amount
                    )
                ).where(
                    other_cases.year == year.number,
                    not_(self.is_doubled(taxpayer, year)),
                    not_(self.is_head_of_household(taxpayer, year)),
                )
            ).tolist(),
        )
        return an(entity(amount))

    def head_of_household_amounts(self) -> list[BasicStandardDeduction]:
        """:return: The amount of `(B) <https://www.law.cornell.edu/uscode/text/26/63#c_2_B>`__ of each head of household not under `(A) <https://www.law.cornell.edu/uscode/text/26/63#c_2_A>`__."""
        head = variable(
            HeadOfHouseholdBasicAmount,
            domain=HeadOfHouseholdBasicAmountTest(world=self.world).conclusions,
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(BasicStandardDeduction)(
                    taxpayer=head.taxpayer, year=head.year, amount=head.amount
                )
            ).where(
                year.number == head.year, not_(self.is_doubled(head.taxpayer, year))
            )
        ).tolist()

    def is_doubled(self, taxpayer: Party, year: CalendarYear) -> Query:
        """:return: Whether *taxpayer*'s basic standard deduction for *year* falls under `(A) <https://www.law.cornell.edu/uscode/text/26/63#c_2_A>`__."""
        doubled = variable(
            DoubledBasicAmount,
            domain=DoubledBasicAmountTest(world=self.world).conclusions,
        )
        return exists(
            doubled, and_(doubled.taxpayer == taxpayer, doubled.year == year.number)
        )

    def is_head_of_household(self, taxpayer: Party, year: CalendarYear) -> Query:
        """:return: Whether *taxpayer*'s basic standard deduction for *year* falls under `(B) <https://www.law.cornell.edu/uscode/text/26/63#c_2_B>`__."""
        head = variable(
            HeadOfHouseholdBasicAmount,
            domain=HeadOfHouseholdBasicAmountTest(world=self.world).conclusions,
        )
        return exists(head, and_(head.taxpayer == taxpayer, head.year == year.number))


@dataclass
class DependentBasicAmountLimitTest(Provision[DependentBasicAmountLimit]):
    """
    `§ 63(c)(5) <https://www.law.cornell.edu/uscode/text/26/63#c_5>`__: for an individual another taxpayer is allowed an exemption for, the greater
    of $500 and $250 plus their gross income, which SARA takes for their earned income.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.DEPENDENT_BASIC_AMOUNT_LIMIT`.
        """
        return SaraPredicate.DEPENDENT_BASIC_AMOUNT_LIMIT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        exemption = variable(
            AnnualDependency,
            domain=ExemptionForSpouseTest(world=self.world).conclusions
            + ExemptionForDependentTest(world=self.world).conclusions,
        )
        income = variable(
            GrossIncome, domain=GrossIncomeOfParty(world=self.world).conclusions
        )
        return an(
            entity(
                inference(DependentBasicAmountLimit)(
                    taxpayer=exemption.individual,
                    other_taxpayer=exemption.taxpayer,
                    gross_income=income.amount,
                    year=exemption.year,
                    amount=DependentBasicAmountLimitTest.limit(self, income.amount),
                )
            ).where(
                income.person == exemption.individual, income.year == exemption.year
            )
        )

    @symbolic_function
    def limit(
        self, gross_income: float, least: float = 500, addition: float = 250
    ) -> float:
        """
        :param least: The least limit, `(A) <https://www.law.cornell.edu/uscode/text/26/63#c_5_A>`__.
        :param addition: The amount `(B) <https://www.law.cornell.edu/uscode/text/26/63#c_5_B>`__ adds to the earned income.
        :return: The greater of *least* and *addition* plus *gross_income*.
        """
        return max(least, addition + gross_income)


@dataclass
class LimitedBasicStandardDeductionTest(Provision[LimitedBasicStandardDeduction]):
    """
    `§ 63(c)(1)(A) <https://www.law.cornell.edu/uscode/text/26/63#c_1_A>`__: the basic standard deduction of `(2) <https://www.law.cornell.edu/uscode/text/26/63#c_2>`__, at most the limit of `(5) <https://www.law.cornell.edu/uscode/text/26/63#c_5>`__ where it
    applies.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.LIMITED_BASIC_STANDARD_DEDUCTION`.
        """
        return SaraPredicate.LIMITED_BASIC_STANDARD_DEDUCTION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        basic = variable(
            BasicStandardDeduction,
            domain=BasicStandardDeductionTest(world=self.world).conclusions,
        )
        limit = variable(
            DependentBasicAmountLimit,
            domain=DependentBasicAmountLimitTest(world=self.world).conclusions,
        )
        other_limit = variable(
            DependentBasicAmountLimit,
            domain=DependentBasicAmountLimitTest(world=self.world).conclusions,
        )
        amount = variable(
            LimitedBasicStandardDeduction,
            domain=an(
                entity(
                    inference(LimitedBasicStandardDeduction)(
                        taxpayer=basic.taxpayer,
                        year=basic.year,
                        amount=LimitedBasicStandardDeductionTest.lesser(
                            self, basic.amount, limit.amount
                        ),
                    )
                ).where(limit.taxpayer == basic.taxpayer, limit.year == basic.year)
            ).tolist()
            + an(
                entity(
                    inference(LimitedBasicStandardDeduction)(
                        taxpayer=basic.taxpayer, year=basic.year, amount=basic.amount
                    )
                ).where(
                    not_(
                        exists(
                            other_limit,
                            and_(
                                other_limit.taxpayer == basic.taxpayer,
                                other_limit.year == basic.year,
                            ),
                        )
                    )
                )
            ).tolist(),
        )
        return an(entity(amount))

    @symbolic_function
    def lesser(self, amount: float, limit: float) -> float:
        """:return: *amount*, at most *limit*."""
        return min(amount, limit)


# %% additional amounts for the aged and blind


@dataclass
class AgedTaxpayerTest(Provision[AgedTaxpayer]):
    """
    `§ 63(f)(1)(A) <https://www.law.cornell.edu/uscode/text/26/63#f_1_A>`__: a taxpayer who has attained age 65 before the close of the year, as
    SARA counts.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.AGED_TAXPAYER`.
        """
        return SaraPredicate.AGED_TAXPAYER

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    @classproperty
    def age(cls) -> int:
        """
        The age in years.
        """
        return 65

    def query(self) -> Query:
        birth = variable(Birth, domain=self.world.births)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(AgedTaxpayer)(taxpayer=birth.person, year=year.number)
            ).where(
                CalendarYear.days_lived_by_close(year, birth.day)
                >= CalendarYear.days_of_years_after_close(year, self.age)
            )
        )


@dataclass
class BlindTaxpayerTest(Provision[BlindTaxpayer]):
    """
    `§ 63(f)(2)(A) <https://www.law.cornell.edu/uscode/text/26/63#f_2_A>`__: a taxpayer who is blind at the close of the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.BLIND_TAXPAYER`.
        """
        return SaraPredicate.BLIND_TAXPAYER

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        blindness = variable(Blindness, domain=self.world.blindnesses)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(BlindTaxpayer)(taxpayer=blindness.person, year=year.number)
            ).where(blindness.start <= year.closing_day)
        )


@dataclass
class SpouseConditionTest(Provision[ConclusionType], ABC):
    """
    A married taxpayer allowed an exemption under `§ 151(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__ for their spouse, of whom a condition of
    their own holds for the year.
    """

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    @abstractmethod
    def spouse_conclusions(self) -> list[TaxpayerConclusion]:
        """:return: The conclusions about each party themself, of which those about the spouse decide."""

    def query(self) -> Query:
        conclusion_type = self.get_type_of_generic_parameter(parameter=ConclusionType)
        married = variable(
            MarriedIndividual,
            domain=MarriedIndividualTest(world=self.world).conclusions,
        )
        spouse = variable(TaxpayerConclusion, domain=self.spouse_conclusions())
        exemption = variable(
            ExemptionForSpouse,
            domain=ExemptionForSpouseTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(conclusion_type)(
                    taxpayer=married.person, year=married.year, spouse=married.spouse
                )
            ).where(
                spouse.taxpayer == married.spouse,
                spouse.year == married.year,
                exists(
                    exemption,
                    and_(
                        exemption.taxpayer == married.person,
                        exemption.individual == married.spouse,
                        exemption.year == married.year,
                    ),
                ),
            )
        )


@dataclass
class AgedSpouseTest(SpouseConditionTest[AgedSpouse]):
    """
    `§ 63(f)(1)(B) <https://www.law.cornell.edu/uscode/text/26/63#f_1_B>`__: a taxpayer whose spouse, for whom an exemption is allowable to them, has
    attained age 65 before the close of the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.AGED_SPOUSE`.
        """
        return SaraPredicate.AGED_SPOUSE

    def spouse_conclusions(self) -> list[TaxpayerConclusion]:
        return AgedTaxpayerTest(world=self.world).conclusions


@dataclass
class BlindSpouseTest(SpouseConditionTest[BlindSpouse]):
    """
    `§ 63(f)(2)(B) <https://www.law.cornell.edu/uscode/text/26/63#f_2_B>`__: a taxpayer whose spouse, for whom an exemption is allowable to them, is
    blind at the close of the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.BLIND_SPOUSE`.
        """
        return SaraPredicate.BLIND_SPOUSE

    def spouse_conclusions(self) -> list[TaxpayerConclusion]:
        return BlindTaxpayerTest(world=self.world).conclusions


@dataclass
class EntitlementCountTest(Provision[ConclusionType], ABC):
    """
    How many additional amounts of `§ 63(f) <https://www.law.cornell.edu/uscode/text/26/63#f>`__ a taxpayer is entitled to for themself and their spouse.
    """

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    @classproperty
    def count_for_spouse(cls) -> float:
        """
        How much the spouse's entitlement counts.
        """
        return 1

    @abstractmethod
    def taxpayer_entitlements(self) -> list[TaxpayerConclusion]:
        """:return: The entitlements of each taxpayer for themself."""

    @abstractmethod
    def spouse_entitlements(self) -> list[TaxpayerConclusion]:
        """:return: The entitlements of each taxpayer for their spouse."""

    def query(self) -> Query:
        count = variable(
            TaxpayerAmount,
            domain=[
                conclusion
                for for_taxpayer in (True, False)
                for for_spouse in (True, False)
                for conclusion in self.counts(for_taxpayer, for_spouse)
            ],
        )
        return an(entity(count))

    def counts(self, for_taxpayer: bool, for_spouse: bool) -> list[TaxpayerAmount]:
        """:return: The count of each taxpayer entitled, or not, for themself and for their spouse."""
        conclusion_type = self.get_type_of_generic_parameter(parameter=ConclusionType)
        taxpayer = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        own = variable(TaxpayerConclusion, domain=self.taxpayer_entitlements())
        spouse = variable(TaxpayerConclusion, domain=self.spouse_entitlements())
        is_entitled = exists(
            own, and_(own.taxpayer == taxpayer, own.year == year.number)
        )
        is_entitled_for_spouse = exists(
            spouse, and_(spouse.taxpayer == taxpayer, spouse.year == year.number)
        )
        return an(
            entity(
                inference(conclusion_type)(
                    taxpayer=taxpayer,
                    year=year.number,
                    amount=for_taxpayer + for_spouse * self.count_for_spouse,
                )
            ).where(
                is_entitled if for_taxpayer else not_(is_entitled),
                is_entitled_for_spouse if for_spouse else not_(is_entitled_for_spouse),
            )
        ).tolist()


@dataclass
class AgedCountTest(EntitlementCountTest[AgedCount]):
    """
    `§ 63(f)(1) <https://www.law.cornell.edu/uscode/text/26/63#f_1>`__: an additional amount for the taxpayer's age `(A) <https://www.law.cornell.edu/uscode/text/26/63#f_1_A>`__ and one for their spouse's
    `(B) <https://www.law.cornell.edu/uscode/text/26/63#f_1_B>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.AGED_COUNT`.
        """
        return SaraPredicate.AGED_COUNT

    def taxpayer_entitlements(self) -> list[TaxpayerConclusion]:
        return AgedTaxpayerTest(world=self.world).conclusions

    def spouse_entitlements(self) -> list[TaxpayerConclusion]:
        return AgedSpouseTest(world=self.world).conclusions


@dataclass
class BlindCountTest(EntitlementCountTest[BlindCount]):
    """
    `§ 63(f)(2) <https://www.law.cornell.edu/uscode/text/26/63#f_2>`__: an additional amount for the taxpayer's blindness `(A) <https://www.law.cornell.edu/uscode/text/26/63#f_2_A>`__ and one for their
    spouse's `(B) <https://www.law.cornell.edu/uscode/text/26/63#f_2_B>`__, which SARA's program counts as 600 amounts.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.BLIND_COUNT`.
        """
        return SaraPredicate.BLIND_COUNT

    @classproperty
    def count_for_spouse(cls) -> float:
        """
        How much SARA's program counts the spouse's entitlement.
        """
        return 600

    def taxpayer_entitlements(self) -> list[TaxpayerConclusion]:
        return BlindTaxpayerTest(world=self.world).conclusions

    def spouse_entitlements(self) -> list[TaxpayerConclusion]:
        return BlindSpouseTest(world=self.world).conclusions


@dataclass
class HigherAdditionalAmountTest(Provision[HigherAdditionalAmount]):
    """
    `§ 63(f)(3) <https://www.law.cornell.edu/uscode/text/26/63#f_3>`__: $750 in place of $600 for an individual not married and no surviving spouse.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HIGHER_ADDITIONAL_AMOUNT`.
        """
        return SaraPredicate.HIGHER_ADDITIONAL_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    @classproperty
    def amount(cls) -> float:
        """
        The higher amount.
        """
        return 750

    def query(self) -> Query:
        taxpayer = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        married = variable(
            MarriedIndividual,
            domain=MarriedIndividualTest(world=self.world).conclusions,
        )
        survivor = variable(
            SurvivingSpouse, domain=SurvivingSpouseTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(HigherAdditionalAmount)(
                    taxpayer=taxpayer, year=year.number, amount=self.amount
                )
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
            )
        )


@dataclass
class AgedOrBlindAmountsTest(Provision[AgedOrBlindAmounts]):
    """
    `§ 63(f) <https://www.law.cornell.edu/uscode/text/26/63#f>`__: $600 for each additional amount of `(1) <https://www.law.cornell.edu/uscode/text/26/63#f_1>`__ and `(2) <https://www.law.cornell.edu/uscode/text/26/63#f_2>`__, or the amount of `(3) <https://www.law.cornell.edu/uscode/text/26/63#f_3>`__
    where it applies.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.AGED_OR_BLIND_AMOUNTS`.
        """
        return SaraPredicate.AGED_OR_BLIND_AMOUNTS

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    @classproperty
    def amount(cls) -> float:
        """
        The amount of each additional amount.
        """
        return 600

    def query(self) -> Query:
        aged = variable(AgedCount, domain=AgedCountTest(world=self.world).conclusions)
        blind = variable(
            BlindCount, domain=BlindCountTest(world=self.world).conclusions
        )
        higher = variable(
            HigherAdditionalAmount,
            domain=HigherAdditionalAmountTest(world=self.world).conclusions,
        )
        other_higher = variable(
            HigherAdditionalAmount,
            domain=HigherAdditionalAmountTest(world=self.world).conclusions,
        )
        amounts = variable(
            AgedOrBlindAmounts,
            domain=an(
                entity(
                    inference(AgedOrBlindAmounts)(
                        taxpayer=aged.taxpayer,
                        year=aged.year,
                        amount=(aged.amount + blind.amount) * higher.amount,
                    )
                ).where(
                    blind.taxpayer == aged.taxpayer,
                    blind.year == aged.year,
                    higher.taxpayer == aged.taxpayer,
                    higher.year == aged.year,
                )
            ).tolist()
            + an(
                entity(
                    inference(AgedOrBlindAmounts)(
                        taxpayer=aged.taxpayer,
                        year=aged.year,
                        amount=(aged.amount + blind.amount) * self.amount,
                    )
                ).where(
                    blind.taxpayer == aged.taxpayer,
                    blind.year == aged.year,
                    not_(
                        exists(
                            other_higher,
                            and_(
                                other_higher.taxpayer == aged.taxpayer,
                                other_higher.year == aged.year,
                            ),
                        )
                    ),
                )
            ).tolist(),
        )
        return an(entity(amounts))


@dataclass
class AdditionalAmountsForAgedOrBlindTest(Provision[AdditionalAmountsForAgedOrBlind]):
    """
    `§ 63(c)(3) <https://www.law.cornell.edu/uscode/text/26/63#c_3>`__: the additional standard deduction, the amounts of `(f) <https://www.law.cornell.edu/uscode/text/26/63#f>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.ADDITIONAL_AMOUNTS_FOR_AGED_OR_BLIND`.
        """
        return SaraPredicate.ADDITIONAL_AMOUNTS_FOR_AGED_OR_BLIND

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        amounts = variable(
            AgedOrBlindAmounts,
            domain=AgedOrBlindAmountsTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(AdditionalAmountsForAgedOrBlind)(
                    taxpayer=amounts.taxpayer, year=amounts.year, amount=amounts.amount
                )
            )
        )


@dataclass
class AdditionalStandardDeductionTest(Provision[AdditionalStandardDeduction]):
    """
    `§ 63(c)(1)(B) <https://www.law.cornell.edu/uscode/text/26/63#c_1_B>`__: the additional standard deduction of `(3) <https://www.law.cornell.edu/uscode/text/26/63#c_3>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.ADDITIONAL_STANDARD_DEDUCTION`.
        """
        return SaraPredicate.ADDITIONAL_STANDARD_DEDUCTION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        amounts = variable(
            AdditionalAmountsForAgedOrBlind,
            domain=AdditionalAmountsForAgedOrBlindTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(AdditionalStandardDeduction)(
                    taxpayer=amounts.taxpayer, year=amounts.year, amount=amounts.amount
                )
            )
        )


# %% individuals not eligible for the standard deduction


@dataclass
class SpouseItemizingTest(Provision[SpouseItemizing]):
    """
    `§ 63(c)(6)(A) <https://www.law.cornell.edu/uscode/text/26/63#c_6_A>`__: a married individual filing separately where either spouse itemizes
    a deduction in the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SPOUSE_ITEMIZING`.
        """
        return SaraPredicate.SPOUSE_ITEMIZING

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        married = variable(
            MarriedIndividual,
            domain=MarriedIndividualTest(world=self.world).separate_filers(),
        )
        deduction = variable(
            ItemizedDeduction,
            domain=[
                deduction
                for deduction in self.world.itemized_deductions
                if deduction.day is not None
            ],
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(SpouseItemizing)(
                    taxpayer=married.person,
                    year=married.year,
                    spouse=married.spouse,
                    deduction=deduction,
                )
            ).where(
                year.number == married.year,
                or_(
                    deduction.claimant == married.person,
                    deduction.claimant == married.spouse,
                ),
                deduction.day >= year.opening_day,
                deduction.day <= year.closing_day,
            )
        )


@dataclass
class NonresidentAlienIndividualTest(Provision[NonresidentAlienIndividual]):
    """
    `§ 63(c)(6)(B) <https://www.law.cornell.edu/uscode/text/26/63#c_6_B>`__: a nonresident alien individual at some time during the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.NONRESIDENT_ALIEN_INDIVIDUAL`.
        """
        return SaraPredicate.NONRESIDENT_ALIEN_INDIVIDUAL

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        status = variable(
            NonresidentAlienStatus, domain=self.world.nonresident_alien_statuses
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(NonresidentAlienIndividual)(
                    taxpayer=status.person, year=year.number
                )
            ).where(
                or_(
                    status.period.first_day == None,
                    status.period.first_day <= year.closing_day,
                ),
                or_(
                    status.period.last_day == None,
                    status.period.last_day >= year.opening_day,
                ),
            )
        )


@dataclass
class TrustOrPartnershipTest(Provision[TrustOrPartnership]):
    """
    `§ 63(c)(6)(D) <https://www.law.cornell.edu/uscode/text/26/63#c_6_D>`__: an estate, trust, common trust fund or partnership at some time during
    the year; SARA's cases state business trusts.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.TRUST_OR_PARTNERSHIP`.
        """
        return SaraPredicate.TRUST_OR_PARTNERSHIP

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        status = variable(
            BusinessTrustStatus, domain=self.world.business_trust_statuses
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(TrustOrPartnership)(taxpayer=status.party, year=year.number)
            ).where(
                or_(
                    status.period.first_day == None,
                    status.period.first_day <= year.closing_day,
                ),
                or_(
                    status.period.last_day == None,
                    status.period.last_day >= year.opening_day,
                ),
            )
        )


@dataclass
class IneligibleForStandardDeductionTest(Provision[IneligibleForStandardDeduction]):
    """
    `§ 63(c)(6) <https://www.law.cornell.edu/uscode/text/26/63#c_6>`__: a zero standard deduction for the individuals of `(A) <https://www.law.cornell.edu/uscode/text/26/63#c_6_A>`__, `(B) <https://www.law.cornell.edu/uscode/text/26/63#c_6_B>`__ and `(D) <https://www.law.cornell.edu/uscode/text/26/63#c_6_D>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.INELIGIBLE_FOR_STANDARD_DEDUCTION`.
        """
        return SaraPredicate.INELIGIBLE_FOR_STANDARD_DEDUCTION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        ineligible = variable(
            TaxpayerConclusion,
            domain=SpouseItemizingTest(world=self.world).conclusions
            + NonresidentAlienIndividualTest(world=self.world).conclusions
            + TrustOrPartnershipTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(IneligibleForStandardDeduction)(
                    taxpayer=ineligible.taxpayer, year=ineligible.year, amount=0
                )
            )
        )


# %% standard deduction


@dataclass
class StandardDeductionUnderGeneralRuleTest(
    Provision[StandardDeductionUnderGeneralRule]
):
    """
    `§ 63(c)(1) <https://www.law.cornell.edu/uscode/text/26/63#c_1>`__: zero under `(6) <https://www.law.cornell.edu/uscode/text/26/63#c_6>`__, else the basic standard deduction `(A) <https://www.law.cornell.edu/uscode/text/26/63#c_1_A>`__ plus the
    additional standard deduction `(B) <https://www.law.cornell.edu/uscode/text/26/63#c_1_B>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.STANDARD_DEDUCTION_UNDER_GENERAL_RULE`.
        """
        return SaraPredicate.STANDARD_DEDUCTION_UNDER_GENERAL_RULE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        ineligible = variable(
            IneligibleForStandardDeduction,
            domain=IneligibleForStandardDeductionTest(world=self.world).conclusions,
        )
        other_ineligible = variable(
            IneligibleForStandardDeduction,
            domain=IneligibleForStandardDeductionTest(world=self.world).conclusions,
        )
        basic = variable(
            LimitedBasicStandardDeduction,
            domain=LimitedBasicStandardDeductionTest(world=self.world).conclusions,
        )
        additional = variable(
            AdditionalStandardDeduction,
            domain=AdditionalStandardDeductionTest(world=self.world).conclusions,
        )
        deduction = variable(
            StandardDeductionUnderGeneralRule,
            domain=an(
                entity(
                    inference(StandardDeductionUnderGeneralRule)(
                        taxpayer=ineligible.taxpayer,
                        year=ineligible.year,
                        amount=ineligible.amount,
                    )
                )
            ).tolist()
            + an(
                entity(
                    inference(StandardDeductionUnderGeneralRule)(
                        taxpayer=basic.taxpayer,
                        year=basic.year,
                        amount=basic.amount + additional.amount,
                    )
                ).where(
                    additional.taxpayer == basic.taxpayer,
                    additional.year == basic.year,
                    not_(
                        exists(
                            other_ineligible,
                            and_(
                                other_ineligible.taxpayer == basic.taxpayer,
                                other_ineligible.year == basic.year,
                            ),
                        )
                    ),
                )
            ).tolist(),
        )
        return an(entity(deduction))


@dataclass
class StandardDeductionTest(Provision[StandardDeduction]):
    """
    `§ 63(c) <https://www.law.cornell.edu/uscode/text/26/63#c>`__: the standard deduction of `(1) <https://www.law.cornell.edu/uscode/text/26/63#c_1>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.STANDARD_DEDUCTION`.
        """
        return SaraPredicate.STANDARD_DEDUCTION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        deduction = variable(
            StandardDeductionUnderGeneralRule,
            domain=StandardDeductionUnderGeneralRuleTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(StandardDeduction)(
                    taxpayer=deduction.taxpayer,
                    year=deduction.year,
                    amount=deduction.amount,
                )
            )
        )


# %% taxable income


@dataclass
class TaxableIncomeWithoutItemizingTest(Provision[TaxableIncomeWithoutItemizing]):
    """
    `§ 63(b) <https://www.law.cornell.edu/uscode/text/26/63#b>`__: for a taxpayer itemizing no deductions, gross income less the standard
    deduction `(1) <https://www.law.cornell.edu/uscode/text/26/63#b_1>`__ and the personal exemptions `(2) <https://www.law.cornell.edu/uscode/text/26/63#b_2>`__, at least zero.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.TAXABLE_INCOME_WITHOUT_ITEMIZING`.
        """
        return SaraPredicate.TAXABLE_INCOME_WITHOUT_ITEMIZING

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        income = variable(
            GrossIncome, domain=GrossIncomeOfParty(world=self.world).conclusions
        )
        deduction = variable(
            StandardDeduction,
            domain=StandardDeductionTest(world=self.world).conclusions,
        )
        exemptions = variable(
            PersonalExemptions,
            domain=[
                exemptions
                for exemptions in PersonalExemptionsTest(world=self.world).conclusions
                if exemptions.total is not None
            ],
        )
        itemized = variable(
            ItemizedDeductions,
            domain=ItemizedDeductionsTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(TaxableIncomeWithoutItemizing)(
                    taxpayer=income.person,
                    year=income.year,
                    amount=TaxableIncomeTest.at_least_zero(
                        self, income.amount - deduction.amount - exemptions.total
                    ),
                    gross_income=income.amount,
                )
            ).where(
                deduction.taxpayer == income.person,
                deduction.year == income.year,
                exemptions.taxpayer == income.person,
                exemptions.year == income.year,
                not_(
                    exists(
                        itemized,
                        and_(
                            itemized.taxpayer == income.person,
                            itemized.year == income.year,
                        ),
                    )
                ),
            )
        )


@dataclass
class TaxableIncomeInGeneralTest(Provision[TaxableIncomeInGeneral]):
    """
    `§ 63(a) <https://www.law.cornell.edu/uscode/text/26/63#a>`__: gross income less the itemized deductions, limited by `§ 68 <https://www.law.cornell.edu/uscode/text/26/68>`__, and the
    personal exemptions, at least zero.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.TAXABLE_INCOME_IN_GENERAL`.
        """
        return SaraPredicate.TAXABLE_INCOME_IN_GENERAL

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        income = variable(
            GrossIncome, domain=GrossIncomeOfParty(world=self.world).conclusions
        )
        itemized = variable(
            ItemizedDeductions,
            domain=ItemizedDeductionsTest(world=self.world).conclusions,
        )
        limited = variable(
            LimitedItemizedDeductions,
            domain=LimitedItemizedDeductionsTest(world=self.world).conclusions,
        )
        exemptions = variable(
            PersonalExemptions,
            domain=[
                exemptions
                for exemptions in PersonalExemptionsTest(world=self.world).conclusions
                if exemptions.total is not None
            ],
        )
        return an(
            entity(
                inference(TaxableIncomeInGeneral)(
                    taxpayer=income.person,
                    year=income.year,
                    amount=TaxableIncomeTest.at_least_zero(
                        self, income.amount - limited.after - exemptions.total
                    ),
                    gross_income=income.amount,
                    deductions=limited.after + exemptions.total,
                )
            ).where(
                itemized.taxpayer == income.person,
                itemized.year == income.year,
                limited.taxpayer == income.person,
                limited.year == income.year,
                limited.before == itemized.total,
                exemptions.taxpayer == income.person,
                exemptions.year == income.year,
            )
        )


@dataclass
class TaxableIncomeTest(Provision[TaxableIncome]):
    """
    `§ 63 <https://www.law.cornell.edu/uscode/text/26/63>`__: the taxable income of `(b) <https://www.law.cornell.edu/uscode/text/26/63#b>`__ for a taxpayer it applies to, else that of `(a) <https://www.law.cornell.edu/uscode/text/26/63#a>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.TAXABLE_INCOME`.
        """
        return SaraPredicate.TAXABLE_INCOME

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        without_itemizing = variable(
            TaxableIncomeWithoutItemizing,
            domain=TaxableIncomeWithoutItemizingTest(world=self.world).conclusions,
        )
        other_without_itemizing = variable(
            TaxableIncomeWithoutItemizing,
            domain=TaxableIncomeWithoutItemizingTest(world=self.world).conclusions,
        )
        in_general = variable(
            TaxableIncomeInGeneral,
            domain=TaxableIncomeInGeneralTest(world=self.world).conclusions,
        )
        income = variable(
            TaxableIncome,
            domain=an(
                entity(
                    inference(TaxableIncome)(
                        taxpayer=without_itemizing.taxpayer,
                        year=without_itemizing.year,
                        amount=without_itemizing.amount,
                    )
                )
            ).tolist()
            + an(
                entity(
                    inference(TaxableIncome)(
                        taxpayer=in_general.taxpayer,
                        year=in_general.year,
                        amount=in_general.amount,
                    )
                ).where(
                    not_(
                        exists(
                            other_without_itemizing,
                            and_(
                                other_without_itemizing.taxpayer == in_general.taxpayer,
                                other_without_itemizing.year == in_general.year,
                            ),
                        )
                    )
                )
            ).tolist(),
        )
        return an(entity(income))

    @symbolic_function
    def at_least_zero(self, amount: float) -> float:
        """:return: *amount*, at least zero."""
        return max(amount, 0)
