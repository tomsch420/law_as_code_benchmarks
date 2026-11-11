"""
What §§ `63 <https://www.law.cornell.edu/uscode/text/26/63>`__, `68 <https://www.law.cornell.edu/uscode/text/26/68>`__ and the totals of `151 <https://www.law.cornell.edu/uscode/text/26/151>`__ of the Internal Revenue Code conclude: taxable income, the
standard deduction, itemized deductions and their limitation, and the personal
exemptions a taxpayer deducts.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass

from law_as_code_benchmarks.sara.domain import ItemizedDeduction, JointReturn, Party
from law_as_code_benchmarks.sara.prolog_term import Term
from law_as_code_benchmarks.sara.provision import SaraConclusion

# %% shapes shared by many conclusions


@dataclass(eq=False)
class TaxpayerConclusion(SaraConclusion, ABC):
    """
    A conclusion about a taxpayer for a calendar year.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.year


@dataclass(eq=False)
class TaxpayerAmount(TaxpayerConclusion, ABC):
    """
    An amount a provision gives a taxpayer for a calendar year, the year before the
    amount.
    """

    amount: float = 0
    """
    The amount.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`TaxpayerConclusion.prolog_arguments` by the amount.
        """
        return self.taxpayer.name, self.year, self.amount


@dataclass(eq=False)
class TaxpayerAmountBeforeYear(TaxpayerAmount, ABC):
    """
    An amount a provision gives a taxpayer for a calendar year, the amount before the
    year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Orders the arguments of :meth:`TaxpayerAmount.prolog_arguments` with the amount
        before the year.
        """
        return self.taxpayer.name, self.amount, self.year


@dataclass(eq=False)
class TaxpayerAndSpouse(TaxpayerConclusion, ABC):
    """
    A conclusion about a taxpayer and their spouse for a calendar year.
    """

    spouse: Party | None = None
    """
    The spouse.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`TaxpayerConclusion.prolog_arguments` by the spouse, after the
        taxpayer.
        """
        return self.taxpayer.name, self.spouse.name, self.year


@dataclass(eq=False)
class YearAmount(SaraConclusion, ABC):
    """
    An amount a provision gives for a calendar year, whoever the taxpayer.
    """

    year: int
    """
    The calendar year.
    """

    amount: float
    """
    The amount.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.year, self.amount


# %% personal exemptions


@dataclass(eq=False)
class PersonalExemptions(SaraConclusion):
    """
    `§ 151 <https://www.law.cornell.edu/uscode/text/26/151>`__: the exemptions a taxpayer deducts for a calendar year, for themself, their
    spouse and their dependents, and those of a spouse they make a joint return with.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    total: float | None
    """
    The sum of the exemptions; None where the case states the exemptions without it.
    """

    year: int
    """
    The calendar year.
    """

    persons: list[Party | None] | None = None
    """
    The person of each exemption, None for one the case states without them; None where
    it states the total alone.
    """

    amounts: list[float] | None = None
    """
    The amount of each exemption; None where the case states the total alone.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.taxpayer.name,
            self.total,
            None
            if self.persons is None
            else [self.name_of(person) for person in self.persons],
            self.amounts,
            self.year,
        )


@dataclass(eq=False)
class AllowedExemptions(TaxpayerAmountBeforeYear):
    """
    `§ 151(a) <https://www.law.cornell.edu/uscode/text/26/151#a>`__: the sum of the exemptions a taxpayer deducts.
    """


@dataclass(eq=False)
class TaxpayerOrSpouseExemption(SaraConclusion, ABC):
    """
    `§ 151(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__: an exemption of the exemption amount, for the taxpayer or their spouse.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    amount: float
    """
    The exemption amount.
    """

    year: int
    """
    The calendar year.
    """


@dataclass(eq=False)
class TaxpayerExemption(TaxpayerOrSpouseExemption):
    """
    `§ 151(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__: the exemption for the taxpayer.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.amount, self.year


@dataclass(eq=False)
class SpouseExemption(TaxpayerOrSpouseExemption):
    """
    `§ 151(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__: the additional exemption for the taxpayer's spouse.
    """

    spouse: Party | None = None
    """
    The spouse.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.spouse.name, self.amount, self.year


@dataclass(eq=False)
class ExemptionDeductions(SaraConclusion):
    """
    `§ 63(d)(2) <https://www.law.cornell.edu/uscode/text/26/63#d_2>`__: the exemptions of `§ 151 <https://www.law.cornell.edu/uscode/text/26/151>`__, which are no itemized deductions.
    """

    exemptions: PersonalExemptions
    """
    The exemptions.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.exemptions.taxpayer.name,
            self.exemptions.amounts,
            self.exemptions.year,
        )


# %% itemized deductions and their limitation


@dataclass(eq=False)
class ItemizedDeductions(SaraConclusion):
    """
    `§ 63(d) <https://www.law.cornell.edu/uscode/text/26/63#d>`__: the sum of the itemized deductions a taxpayer claims for a calendar year.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    total: float
    """
    The sum of the deductions.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        # the list of deductions is left open; no case asks for it
        return (
            self.taxpayer.name,
            None,
            self.total,
            self.year,
        )


@dataclass(eq=False)
class ItemizedDeductionReduction(SaraConclusion):
    """
    `§ 68(a)(2) <https://www.law.cornell.edu/uscode/text/26/68#a_2>`__: 80 percent of the itemized deductions, rounded to whole dollars.
    """

    itemized_deductions: ItemizedDeductions
    """
    The itemized deductions.
    """

    reduction: int
    """
    The reduction.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.itemized_deductions.taxpayer.name,
            self.itemized_deductions.total,
            self.reduction,
            self.itemized_deductions.year,
        )


@dataclass(eq=False)
class ExcessIncomeReduction(SaraConclusion):
    """
    `§ 68(a)(1) <https://www.law.cornell.edu/uscode/text/26/68#a_1>`__: 3 percent of the excess of gross income over the applicable amount,
    rounded to whole dollars.
    """

    gross_income: float
    """
    The gross income, which SARA takes for the adjusted gross income.
    """

    applicable_amount: float
    """
    The applicable amount.
    """

    reduction: int
    """
    The reduction.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.gross_income, self.applicable_amount, self.reduction


@dataclass(eq=False)
class ItemizedDeductionLimitation(SaraConclusion):
    """
    `§ 68(a) <https://www.law.cornell.edu/uscode/text/26/68#a>`__: the reduction of a taxpayer's itemized deductions where their gross income
    exceeds the applicable amount, the lesser of `(1) <https://www.law.cornell.edu/uscode/text/26/68#a_1>`__ and `(2) <https://www.law.cornell.edu/uscode/text/26/68#a_2>`__.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    gross_income: float
    """
    Their gross income.
    """

    applicable_amount: float
    """
    Their applicable amount.
    """

    itemized_total: float
    """
    Their itemized deductions.
    """

    reduction: int
    """
    The reduction.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.taxpayer.name,
            self.gross_income,
            self.applicable_amount,
            self.itemized_total,
            self.reduction,
            self.year,
        )


@dataclass(eq=False)
class LimitedItemizedDeductions(SaraConclusion):
    """
    `§ 68 <https://www.law.cornell.edu/uscode/text/26/68>`__: a taxpayer's itemized deductions after the overall limitation.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    before: float
    """
    The itemized deductions before the limitation.
    """

    after: float
    """
    The itemized deductions after it.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.before, self.after, self.year


@dataclass(eq=False)
class SuspendedLimitation(SaraConclusion):
    """
    `§ 68(f) <https://www.law.cornell.edu/uscode/text/26/68#f>`__: that `§ 68 <https://www.law.cornell.edu/uscode/text/26/68>`__ does not apply to the calendar year.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (self.year,)


# %% standard deduction


@dataclass(eq=False)
class TemporaryBasicAmountForHeadOfHousehold(YearAmount):
    """
    `§ 63(c)(7)(i) <https://www.law.cornell.edu/uscode/text/26/63#c_7>`__: the basic standard deduction of a head of household for 2018 through 2025.
    """


@dataclass(eq=False)
class TemporaryBasicAmountInOtherCases(YearAmount):
    """
    `§ 63(c)(7)(ii) <https://www.law.cornell.edu/uscode/text/26/63#c_7>`__: the basic standard deduction in other cases for 2018 through 2025.
    """


@dataclass(eq=False)
class BasicAmountInOtherCases(YearAmount):
    """
    `§ 63(c)(2)(C) <https://www.law.cornell.edu/uscode/text/26/63#c_2_C>`__: the basic standard deduction in any case not otherwise provided for.
    """


@dataclass(eq=False)
class HeadOfHouseholdBasicAmount(TaxpayerAmount):
    """
    `§ 63(c)(2)(B) <https://www.law.cornell.edu/uscode/text/26/63#c_2_B>`__: the basic standard deduction of a head of household.
    """


@dataclass(eq=False)
class JointReturnDoubling(TaxpayerConclusion):
    """
    `§ 63(c)(2)(A)(i) <https://www.law.cornell.edu/uscode/text/26/63#c_2_A_i>`__: a taxpayer making a joint return, whose basic standard deduction is doubled.
    """

    joint_return: JointReturn | None = None
    """
    The joint return.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`TaxpayerConclusion.prolog_arguments` by the joint return, after
        the taxpayer.
        """
        return (
            self.taxpayer.name,
            None if self.joint_return is None else self.joint_return.name,
            self.year,
        )


@dataclass(eq=False)
class SurvivingSpouseDoubling(TaxpayerConclusion):
    """
    `§ 63(c)(2)(A)(ii) <https://www.law.cornell.edu/uscode/text/26/63#c_2_A_ii>`__: a surviving spouse, whose basic standard deduction is doubled.
    """


@dataclass(eq=False)
class DoubledBasicAmount(TaxpayerAmount):
    """
    `§ 63(c)(2)(A) <https://www.law.cornell.edu/uscode/text/26/63#c_2_A>`__: that the taxpayer's basic standard deduction is the amount of `(C) <https://www.law.cornell.edu/uscode/text/26/63#c_2_C>`__
    times this multiplier.
    """


@dataclass(eq=False)
class BasicStandardDeduction(TaxpayerAmount):
    """
    `§ 63(c)(2) <https://www.law.cornell.edu/uscode/text/26/63#c_2>`__: a taxpayer's basic standard deduction.
    """


@dataclass(eq=False)
class DependentBasicAmountLimit(SaraConclusion):
    """
    `§ 63(c)(5) <https://www.law.cornell.edu/uscode/text/26/63#c_5>`__: the most a dependent's basic standard deduction may be, the greater of
    $500 and $250 plus their gross income.
    """

    taxpayer: Party
    """
    The dependent.
    """

    other_taxpayer: Party
    """
    The taxpayer allowed an exemption for them.
    """

    gross_income: float
    """
    The dependent's gross income, which SARA takes for their earned income.
    """

    year: int
    """
    The calendar year.
    """

    amount: float
    """
    The limit.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.taxpayer.name,
            self.other_taxpayer.name,
            self.gross_income,
            self.year,
            self.amount,
        )


@dataclass(eq=False)
class LimitedBasicStandardDeduction(TaxpayerAmount):
    """
    `§ 63(c)(1)(A) <https://www.law.cornell.edu/uscode/text/26/63#c_1_A>`__: a taxpayer's basic standard deduction, limited by `(5) <https://www.law.cornell.edu/uscode/text/26/63#c_5>`__.
    """


@dataclass(eq=False)
class AdditionalStandardDeduction(TaxpayerAmount):
    """
    `§ 63(c)(1)(B) <https://www.law.cornell.edu/uscode/text/26/63#c_1_B>`__: a taxpayer's additional standard deduction.
    """


@dataclass(eq=False)
class AdditionalAmountsForAgedOrBlind(TaxpayerAmountBeforeYear):
    """
    `§ 63(c)(3) <https://www.law.cornell.edu/uscode/text/26/63#c_3>`__: the additional standard deduction, the sum of the amounts of `(f) <https://www.law.cornell.edu/uscode/text/26/63#f>`__.
    """


@dataclass(eq=False)
class AgedOrBlindAmounts(TaxpayerAmountBeforeYear):
    """
    `§ 63(f) <https://www.law.cornell.edu/uscode/text/26/63#f>`__: the additional amounts a taxpayer is entitled to for age or blindness.
    """


@dataclass(eq=False)
class StandardDeductionUnderGeneralRule(TaxpayerAmount):
    """
    `§ 63(c)(1) <https://www.law.cornell.edu/uscode/text/26/63#c_1>`__: a taxpayer's standard deduction.
    """


@dataclass(eq=False)
class StandardDeduction(TaxpayerAmount):
    """
    `§ 63(c) <https://www.law.cornell.edu/uscode/text/26/63#c>`__: a taxpayer's standard deduction.
    """


@dataclass(eq=False)
class IneligibleForStandardDeduction(TaxpayerAmount):
    """
    `§ 63(c)(6) <https://www.law.cornell.edu/uscode/text/26/63#c_6>`__: a taxpayer whose standard deduction is zero.
    """


@dataclass(eq=False)
class SpouseItemizing(TaxpayerAndSpouse):
    """
    `§ 63(c)(6)(A) <https://www.law.cornell.edu/uscode/text/26/63#c_6_A>`__: a married taxpayer filing separately where either spouse itemizes.
    """

    deduction: ItemizedDeduction | None = None
    """
    An itemized deduction of either spouse in the year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`TaxpayerAndSpouse.prolog_arguments` by the deduction, after the
        spouse.
        """
        return self.taxpayer.name, self.spouse.name, self.deduction.name, self.year


@dataclass(eq=False)
class NonresidentAlienIndividual(TaxpayerConclusion):
    """
    `§ 63(c)(6)(B) <https://www.law.cornell.edu/uscode/text/26/63#c_6_B>`__: a taxpayer who is a nonresident alien during the year.
    """


@dataclass(eq=False)
class TrustOrPartnership(TaxpayerConclusion):
    """
    `§ 63(c)(6)(D) <https://www.law.cornell.edu/uscode/text/26/63#c_6_D>`__: a taxpayer that is an estate, trust, common trust fund or
    partnership during the year.
    """


@dataclass(eq=False)
class AgedTaxpayer(TaxpayerConclusion):
    """
    `§ 63(f)(1)(A) <https://www.law.cornell.edu/uscode/text/26/63#f_1_A>`__: a taxpayer who is 65 before the close of the year.
    """


@dataclass(eq=False)
class AgedSpouse(TaxpayerAndSpouse):
    """
    `§ 63(f)(1)(B) <https://www.law.cornell.edu/uscode/text/26/63#f_1_B>`__: a taxpayer whose spouse, for whom they are allowed an exemption, is 65
    before the close of the year.
    """


@dataclass(eq=False)
class BlindTaxpayer(TaxpayerConclusion):
    """
    `§ 63(f)(2)(A) <https://www.law.cornell.edu/uscode/text/26/63#f_2_A>`__: a taxpayer who is blind at the close of the year.
    """


@dataclass(eq=False)
class BlindSpouse(TaxpayerAndSpouse):
    """
    `§ 63(f)(2)(B) <https://www.law.cornell.edu/uscode/text/26/63#f_2_B>`__: a taxpayer whose spouse, for whom they are allowed an exemption, is
    blind at the close of the year.
    """


@dataclass(eq=False)
class AgedCount(TaxpayerAmount):
    """
    `§ 63(f)(1) <https://www.law.cornell.edu/uscode/text/26/63#f_1>`__: how many additional amounts for age the taxpayer is entitled to.
    """


@dataclass(eq=False)
class BlindCount(TaxpayerAmount):
    """
    `§ 63(f)(2) <https://www.law.cornell.edu/uscode/text/26/63#f_2>`__: how many additional amounts for blindness the taxpayer is entitled to, the
    spouse's counted as 600 as in SARA's program.
    """


@dataclass(eq=False)
class HigherAdditionalAmount(TaxpayerAmount):
    """
    `§ 63(f)(3) <https://www.law.cornell.edu/uscode/text/26/63#f_3>`__: the higher additional amount of an unmarried individual, no surviving spouse.
    """


# %% taxable income


@dataclass(eq=False)
class TaxableIncome(TaxpayerAmount):
    """
    `§ 63 <https://www.law.cornell.edu/uscode/text/26/63>`__: a taxpayer's taxable income, at least zero.
    """


@dataclass(eq=False)
class TaxableIncomeWithoutItemizing(TaxpayerAmount):
    """
    `§ 63(b) <https://www.law.cornell.edu/uscode/text/26/63#b>`__: the taxable income of a taxpayer who does not itemize: gross income less the
    standard deduction and the exemptions.
    """

    gross_income: float = 0
    """
    Their gross income, which SARA takes for the adjusted gross income.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`TaxpayerAmount.prolog_arguments` by the gross income.
        """
        return self.taxpayer.name, self.year, self.amount, self.gross_income


@dataclass(eq=False)
class TaxableIncomeInGeneral(TaxpayerAmount):
    """
    `§ 63(a) <https://www.law.cornell.edu/uscode/text/26/63#a>`__: gross income less the limited itemized deductions and the exemptions.
    """

    gross_income: float = 0
    """
    The gross income.
    """

    deductions: float = 0
    """
    The deductions subtracted.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`TaxpayerAmount.prolog_arguments` by the gross income and the
        deductions.
        """
        return (
            self.taxpayer.name,
            self.year,
            self.amount,
            self.gross_income,
            self.deductions,
        )
