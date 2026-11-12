"""
What `§ 1 <https://www.law.cornell.edu/uscode/text/26/1>`__ of the Internal Revenue Code concludes, the income tax on taxable income, and
the tax a person owes in all.
"""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Real

from law_as_code_benchmarks.sara.domain import JointReturn, Party
from law_as_code_benchmarks.sara.prolog_term import Term
from law_as_code_benchmarks.sara.provision import SaraConclusion

# %% rate brackets


@dataclass(eq=False)
class BracketTax(SaraConclusion):
    """
    The tax a bracket of a rate schedule imposes on a taxable income within it.
    """

    taxable_income: Real
    """
    The taxable income.
    """

    tax: int
    """
    The tax, in whole dollars.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxable_income, self.tax


# %% income tax


@dataclass(eq=False)
class IncomeTax(SaraConclusion):
    """
    The income tax `§ 1 <https://www.law.cornell.edu/uscode/text/26/1>`__ imposes on a taxpayer's taxable income for a calendar year.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    year: int
    """
    The calendar year.
    """

    taxable_income: float
    """
    The taxable income of `§ 63 <https://www.law.cornell.edu/uscode/text/26/63>`__.
    """

    tax: int
    """
    The tax, in whole dollars.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.year, self.taxable_income, self.tax


@dataclass(eq=False)
class JointReturnOrSurvivorIncomeTax(IncomeTax):
    """
    `§ 1(a) <https://www.law.cornell.edu/uscode/text/26/1#a>`__: the tax on a married individual making a joint return or a surviving spouse.
    """


@dataclass(eq=False)
class SurvivorIncomeTax(IncomeTax):
    """
    `§ 1(a)(2) <https://www.law.cornell.edu/uscode/text/26/1#a_2>`__: the tax on a surviving spouse.
    """


@dataclass(eq=False)
class HeadOfHouseholdIncomeTax(IncomeTax):
    """
    `§ 1(b) <https://www.law.cornell.edu/uscode/text/26/1#b>`__: the tax on a head of household.
    """


@dataclass(eq=False)
class UnmarriedIncomeTax(IncomeTax):
    """
    `§ 1(c) <https://www.law.cornell.edu/uscode/text/26/1#c>`__: the tax on an individual not married, no surviving spouse and no head of
    household.
    """


@dataclass(eq=False)
class TotalIncomeTax(IncomeTax):
    """
    `§ 1 <https://www.law.cornell.edu/uscode/text/26/1>`__: the tax on a taxpayer under any of `(a) <https://www.law.cornell.edu/uscode/text/26/1#a>`__ to `(d) <https://www.law.cornell.edu/uscode/text/26/1#d>`__.
    """


@dataclass(eq=False)
class JointReturnIncomeTax(IncomeTax):
    """
    `§ 1(a)(1) <https://www.law.cornell.edu/uscode/text/26/1#a_1>`__: the tax on a married individual making a joint return with their spouse.
    """

    joint_return: JointReturn | None = None
    """
    The joint return.
    """

    spouse: Party | None = None
    """
    The spouse.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`IncomeTax.prolog_arguments` by the joint return and the spouse,
        after the taxpayer.
        """
        return (
            self.taxpayer.name,
            None if self.joint_return is None else self.joint_return.name,
            self.name_of(self.spouse),
            self.year,
            self.taxable_income,
            self.tax,
        )


@dataclass(eq=False)
class SeparateReturnIncomeTax(IncomeTax):
    """
    `§ 1(d) <https://www.law.cornell.edu/uscode/text/26/1#d>`__: the tax on a married individual making no joint return with their spouse.
    """

    spouse: Party | None = None
    """
    The spouse.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`IncomeTax.prolog_arguments` by the spouse, after the taxpayer.
        """
        return (
            self.taxpayer.name,
            self.name_of(self.spouse),
            self.year,
            self.taxable_income,
            self.tax,
        )


# %% tax owed


@dataclass(eq=False)
class TaxOwed(SaraConclusion):
    """
    SARA's ``tax``: the income tax of `§ 1 <https://www.law.cornell.edu/uscode/text/26/1>`__ plus the employment tax of `§ 3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__ a person owes
    for a calendar year, each zero where it does not apply.
    """

    person: Party
    """
    Who owes it.
    """

    year: int
    """
    The calendar year.
    """

    amount: float
    """
    The tax.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.person.name, self.year, self.amount
