"""
Tests of the model of Catala's income tax and of its oracles.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from law_as_code_benchmarks.catala.income_tax.exceptions import UndistributableAmount
from law_as_code_benchmarks.catala.income_tax.oracles import (
    DeficitImputation,
    PastDeficit,
    ProportionalDistribution,
)
from law_as_code_benchmarks.catala.income_tax.parts import (
    AdultChildrenAbatementProvision,
    PartsCase,
    PartsOutput,
    TaxHouseholdDescription,
)
from law_as_code_benchmarks.catala.income_tax.wages import (
    ClaimedRealExpenses,
    DeclarantWagesCase,
    DeclarantWagesOutput,
    DeductionCeilingProvision,
    DeductionMinimumProvision,
    PensionAbatementMinimumProvision,
    UncappedPensionAbatement,
    WageDeclaration,
)
from law_as_code_benchmarks.catala.money import Money

# %% oracles


def test_a_distribution_evens_out_its_rounding_on_the_last_shares() -> None:
    """
    Ten euros over three equal bases round to three each, a euro short; the oracle turns
    the rounding of the last share it reaches once enough shares passed.
    """
    shares = ProportionalDistribution(
        amount=Money.from_euros(10), bases=[Money.from_euros(1)] * 3
    ).shares()
    assert shares == [Money.from_euros(3), Money.from_euros(3), Money.from_euros(4)]


@pytest.mark.parametrize(
    "amount, bases",
    [
        (Money(cents=1050), [Money.from_euros(1)]),
        (Money.from_euros(10), [Money.from_euros(-1), Money.from_euros(2)]),
        (Money.from_euros(10), [Money.zero, Money.zero]),
    ],
)
def test_a_distribution_the_oracle_asserts_against_is_refused(
    amount: Money, bases: list[Money]
) -> None:
    """
    An amount with cents, a negative base, or nothing to distribute over is refused.
    """
    with pytest.raises(UndistributableAmount):
        ProportionalDistribution(amount=amount, bases=bases).shares()


def test_income_is_imputed_on_the_oldest_deficits_first() -> None:
    """
    The oldest deficit is used up first, and what the income cannot cover remains.
    """
    imputation = DeficitImputation.from_income(
        Money.from_euros(1000),
        [
            PastDeficit(year=2020, amount=Money.from_euros(500)),
            PastDeficit(year=2019, amount=Money.from_euros(600)),
        ],
    )
    assert imputation.imputed_income == Money.zero
    assert [
        (deficit.year, deficit.amount) for deficit in imputation.remaining_deficits
    ] == [(2020, Money.from_euros(100))]


# %% parts


def test_a_married_couple_with_three_children_has_four_parts() -> None:
    """
    194: two parts, and one for each child from the third.
    """
    case = PartsCase(
        household=TaxHouseholdDescription(married=True, minor_unmarried_children=3),
        income_year=2022,
    )
    assert case.output(PartsOutput.PARTS) == Fraction(4)


def test_a_person_alone_who_raised_a_child_has_one_and_a_half_parts() -> None:
    """
    195 1: one and a half parts for box L.
    """
    case = PartsCase(
        household=TaxHouseholdDescription(single=True, alone_without_children=True),
        income_year=2023,
    )
    assert case.output(PartsOutput.PARTS) == Fraction(3, 2)


def test_an_adult_child_with_a_family_gives_an_abatement() -> None:
    """
    196 B: the abatement of the year for each adult child married or with a family.
    """
    case = PartsCase(
        household=TaxHouseholdDescription(
            widowed=True, married_adult_children_or_with_family=Fraction(1)
        ),
        income_year=2023,
    )
    assert (
        case.output(PartsOutput.ABATEMENT)
        == AdultChildrenAbatementProvision.abatement_by_year[2023]
    )


# %% wages


def declarant(**declared: object) -> DeclarantWagesCase:
    """:return: A declarant of 2022 declaring *declared*, the pension abatement uncapped."""
    return DeclarantWagesCase(
        declaration=WageDeclaration(**declared),
        income_year=2022,
        pension_abatement_cap=UncappedPensionAbatement(),
    )


def test_the_flat_deduction_is_the_minimum_at_least_but_the_wages_at_most() -> None:
    """
    83 3°: 10 % of 3,000 € is below the minimum, which a wage of 400 € caps.
    """
    minimum = DeductionMinimumProvision.amount_by_year[2022]
    deductions = [
        declarant(wages=Money.from_euros(wages)).output(
            DeclarantWagesOutput.PROFESSIONAL_EXPENSES
        )
        for wages in (3000, 400)
    ]
    assert deductions == [minimum, Money.from_euros(400)]


def test_the_flat_deduction_stops_at_its_ceiling() -> None:
    """
    83 3°: no more than the ceiling of the year.
    """
    case = declarant(wages=Money.from_euros(500_000))
    assert (
        case.output(DeclarantWagesOutput.PROFESSIONAL_EXPENSES)
        == (DeductionCeilingProvision.amount_by_year[2022])
    )


def test_real_expenses_replace_a_lower_flat_deduction() -> None:
    """
    83 3°: real expenses above the flat deduction are deducted instead.
    """
    case = declarant(
        wages=Money.from_euros(10_000),
        real_expenses=ClaimedRealExpenses(amount=Money.from_euros(2_000)),
    )
    assert case.output(DeclarantWagesOutput.PROFESSIONAL_EXPENSES) == Money.from_euros(
        2_000
    )


def test_a_small_pension_has_the_minimum_abatement() -> None:
    """
    158 5 a: 10 % of 3,000 € is below the minimum of the year.
    """
    case = declarant(pensions=Money.from_euros(3_000))
    assert (
        case.output(DeclarantWagesOutput.PENSION_ABATEMENT)
        == (PensionAbatementMinimumProvision.amount_by_year[2022])
    )
