"""
Tests of the models of Catala's small examples, on cases the examples' own tests leave
out.
"""

from __future__ import annotations

import datetime
from fractions import Fraction

import pytest

from law_as_code_benchmarks.catala.inheritance import (
    Child,
    ReservedPortionCase,
    ReservedPortionOutput,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.nsw_gaming import (
    GamingOutput,
    SocialHousie,
    SocialHousieCase,
)
from law_as_code_benchmarks.catala.polish_tax import (
    MortgageCase,
    TaxProvision,
    TransactionOutput,
)
from law_as_code_benchmarks.catala.us_tax_code import (
    DiscountType,
    EmployeeDiscountCase,
    EmployeeDiscountOutput,
    Period,
    SellerOutput,
    SinglePersonCase,
)

# %% inheritance


@pytest.mark.parametrize(
    "is_represented, share", [(True, Fraction(1, 2)), (False, Fraction(1, 4))]
)
def test_a_child_renouncing_the_succession_counts_only_where_represented(
    is_represented: bool, share: Fraction
) -> None:
    """
    Article 913: a represented child who renounced counts, reserving half for one child;
    one who is not leaves no child, and article 914-1 reserves a quarter for the
    surviving spouse.
    """
    child = Child(
        identifier=0,
        renounced_succession=True,
        is_represented=is_represented,
        must_return_gift=False,
    )
    case = ReservedPortionCase(
        total_estate=Money.from_euros(100_000),
        children=[child],
        surviving_spouse_not_divorced=True,
    )
    assert case.output(ReservedPortionOutput.RESERVED_SHARE) == share


# %% Polish tax


def test_a_mortgage_securing_an_undetermined_claim_is_taxed_19_zloty() -> None:
    """
    Article 7, paragraph 1, 7b): 19 zł whatever the amount.
    """
    case = MortgageCase(amount=Money.from_euros(50_000), undetermined_claim=True)
    assert case.output(TransactionOutput.TAX) == TaxProvision.undetermined_mortgage_tax


def test_a_mortgage_securing_an_existing_claim_is_taxed_a_tenth_of_a_percent() -> None:
    """
    Article 7, paragraph 1, 7a): 0.1 % of 50,000 zł is 50 zł.
    """
    case = MortgageCase(amount=Money.from_euros(50_000))
    assert case.output(TransactionOutput.TAX) == Money.from_euros(50)


# %% US tax code


def test_a_discount_on_services_is_qualified_up_to_a_fifth_of_the_customer_price() -> (
    None
):
    """
    § 132(c)(1)(B): a $100 discount on a $1,000 service is qualified in full.
    """
    case = EmployeeDiscountCase(
        customer_price=Money.from_euros(1000),
        employee_price=Money.from_euros(900),
        discount_type=DiscountType.SERVICES,
    )
    assert case.output(EmployeeDiscountOutput.QUALIFIED_EMPLOYEE_DISCOUNT) == (
        Money.from_euros(100)
    )


def test_another_exclusion_within_two_years_excludes_the_sale() -> None:
    """
    § 121(b)(3): a taxpayer meeting the requirements, who sold another residence under §
    121(a) a year before, has nothing excluded.
    """
    four_years = [
        Period(begin=datetime.date(2017, 1, 1), end=datetime.date(2021, 1, 1))
    ]
    case = SinglePersonCase(
        date_of_sale_or_exchange=datetime.date(2021, 1, 1),
        gain_from_sale_or_exchange_of_property=Money.from_euros(100_000),
        property_ownage=four_years,
        property_usage_as_principal_residence=four_years,
        previous_exclusion_sale_date=datetime.date(2020, 1, 1),
    )
    assert (
        case.output(SellerOutput.REQUIREMENTS_MET),
        case.output(SellerOutput.RECENT_EXCLUSION),
        case.output(SellerOutput.EXCLUSION),
    ) == (True, True, Money.zero)


# %% NSW community gaming


@pytest.mark.parametrize(
    "jackpot_prize_value, permitted",
    [(Money.from_euros(200), True), (Money.from_euros(201), False)],
)
def test_social_housie_is_permitted_with_a_jackpot_of_200_dollars_at_most(
    jackpot_prize_value: Money, permitted: bool
) -> None:
    """
    Clause 5(3)(d), which no test of the example covers: a jackpot of $200 is allowed,
    one dollar more is not.
    """
    case = SocialHousieCase(
        social_housie=SocialHousie(
            social_purposes_only=True,
            prize_value_per_session=Money.from_euros(40),
            on_licensed_premises=False,
            jackpot_prize_value=jackpot_prize_value,
            investment_returned=True,
        )
    )
    assert case.output(GamingOutput.AUTHORIZED) == permitted
