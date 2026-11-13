"""
Sections 121 and 132 of the United States Internal Revenue Code, as Catala's ``us_tax_code``
example states them: the exclusion of gain from the sale of a principal residence, and
the qualified employee discount.
"""

from __future__ import annotations

import datetime
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
    exists,
    inference,
    not_,
    variable,
)
from krrood.entity_query_language.factories import max as maximum
from krrood.entity_query_language.predicate import symbolic_function
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from krrood.symbol_graph.symbol_graph import Symbol
from typing_extensions import Self

from law_as_code_benchmarks.catala.assessment import CatalaConclusion
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import (
    CatalaDirectory,
    CatalaValue,
    ConstructorWithContent,
    Duration,
    StructureLiteral,
)
from law_as_code_benchmarks.catala.scope_test import (
    CaseAmount,
    CaseCondition,
    CaseFraction,
    CatalaRecord,
    ScopeCase,
    ScopeProvision,
    ScopeTestFile,
)

# %% section 132: the qualified employee discount


class DiscountType(StrEnum):
    """What an employee discount is on, each named as Catala's ``DiscountType`` constructor."""

    PROPERTY = "Property"
    """Property."""

    SERVICES = "Services"
    """Services."""


class EmployeeDiscountOutput(StrEnum):
    """The outputs of Catala's ``QualifiedEmployeeDiscount`` scope."""

    EMPLOYEE_DISCOUNT = "employee_discount"
    """The discount the employee gets."""

    GROSS_PROFIT_PERCENTAGE = "gross_profit_percentage"
    """The employer's gross profit percentage."""

    QUALIFIED_EMPLOYEE_DISCOUNT = "qualified_employee_discount"
    """The part of the discount that is qualified."""


@dataclass(eq=False)
class EmployeeDiscountCase(ScopeCase):
    """An employee discount, Catala's ``QualifiedEmployeeDiscount`` scope of § 132(c)."""

    customer_price: Money = field(default_factory=lambda: Money.zero)
    """The price at which the employer offers the item to customers."""

    employee_price: Money = field(default_factory=lambda: Money.zero)
    """The price the employee pays."""

    aggregate_cost: Money = field(default_factory=lambda: Money.zero)
    """The aggregate cost of the property sold; nothing for services, as Catala sets."""

    discount_type: DiscountType = DiscountType.PROPERTY
    """What the discount is on."""

    @classproperty
    def catala_scope(cls) -> str:
        """``QualifiedEmployeeDiscount``."""
        return "QualifiedEmployeeDiscount"

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`EmployeeDiscountOutput`."""
        return EmployeeDiscountOutput

    def output(self, variable: str) -> CatalaValue:
        match EmployeeDiscountOutput(variable):
            case EmployeeDiscountOutput.EMPLOYEE_DISCOUNT:
                return self.sole_conclusion(EmployeeDiscountProvision).amount
            case EmployeeDiscountOutput.GROSS_PROFIT_PERCENTAGE:
                return self.sole_conclusion(GrossProfitPercentageProvision).fraction
            case EmployeeDiscountOutput.QUALIFIED_EMPLOYEE_DISCOUNT:
                return self.sole_conclusion(QualifiedEmployeeDiscountProvision).amount


@dataclass(eq=False)
class EmployeeDiscount(CaseAmount):
    """§ 132(c)(3): the amount by which the employee's price is below the customer price."""


@dataclass(eq=False)
class GrossProfitPercentage(CaseFraction):
    """§ 132(c)(2): the share of the customer price above the aggregate cost of property."""


@dataclass(eq=False)
class QualifiedEmployeeDiscount(CaseAmount):
    """§ 132(c)(1): the part of the employee discount excluded from gross income."""


@dataclass
class EmployeeDiscountProvision(ScopeProvision[EmployeeDiscount]):
    """§ 132(c)(3): the customer price less the employee's price."""

    def query(self) -> Query:
        case = variable(EmployeeDiscountCase, domain=[self.case])
        return an(
            entity(
                inference(EmployeeDiscount)(
                    case=case, amount=case.customer_price - case.employee_price
                )
            )
        )


@dataclass
class GrossProfitPercentageProvision(ScopeProvision[GrossProfitPercentage]):
    """
    § 132(c)(2): for property, the customer price less the aggregate cost, over the
    customer price; nothing for services, which Catala sets as they need none.
    """

    def query(self) -> Query:
        case = variable(EmployeeDiscountCase, domain=[self.case])
        percentage = deduced_variable(GrossProfitPercentage)
        query = an(
            entity(percentage).where(case.discount_type == DiscountType.PROPERTY)
        )
        with query:
            add(
                percentage,
                inference(GrossProfitPercentage)(
                    case=case,
                    fraction=(case.customer_price - case.aggregate_cost)
                    / case.customer_price,
                ),
            )
            with alternative():
                add(
                    percentage,
                    inference(GrossProfitPercentage)(case=case, fraction=Fraction(0)),
                )
        return query


@dataclass
class QualifiedEmployeeDiscountProvision(ScopeProvision[QualifiedEmployeeDiscount]):
    """
    § 132(c)(1): the employee discount, up to the gross profit percentage of the
    customer price for property (A), and up to 20 % of it for services (B).
    """

    @classproperty
    def services_share(cls) -> Fraction:
        """(B): the share of the customer price a discount on services may reach, 20 %."""
        return Fraction(20, 100)

    def query(self) -> Query:
        case = variable(EmployeeDiscountCase, domain=[self.case])
        discount = variable(
            EmployeeDiscount,
            domain=EmployeeDiscountProvision(case=self.case).conclusions,
        )
        percentage = variable(
            GrossProfitPercentage,
            domain=GrossProfitPercentageProvision(case=self.case).conclusions,
        )
        property_limit = case.customer_price * percentage.fraction
        services_limit = case.customer_price * self.services_share
        qualified = deduced_variable(QualifiedEmployeeDiscount)
        query = an(
            entity(qualified).where(
                case.discount_type == DiscountType.PROPERTY,
                discount.amount > property_limit,
            )
        )
        with query:
            add(
                qualified,
                inference(QualifiedEmployeeDiscount)(case=case, amount=property_limit),
            )
            with alternative(case.discount_type == DiscountType.PROPERTY):
                add(
                    qualified,
                    inference(QualifiedEmployeeDiscount)(
                        case=case, amount=discount.amount
                    ),
                )
            with alternative(discount.amount > services_limit):
                add(
                    qualified,
                    inference(QualifiedEmployeeDiscount)(
                        case=case, amount=services_limit
                    ),
                )
            with alternative():
                add(
                    qualified,
                    inference(QualifiedEmployeeDiscount)(
                        case=case, amount=discount.amount
                    ),
                )
        return query


# %% section 121: the sale of a principal residence


@dataclass
class Period(CatalaRecord):
    """A period of days, Catala's ``Period``."""

    begin: datetime.date
    """The first day."""

    end: datetime.date
    """The day it ends."""


class OtherSaleConstructor(StrEnum):
    """The constructors of Catala's ``OtherSection121aSale``."""

    NO_OTHER_SALE = "NoOtherSaleWhereSection121aApplied"
    """No other sale § 121(a) applied to."""

    MOST_RECENT_SALE = "MostRecentSaleWhereSection121aApplied"
    """The most recent other sale § 121(a) applied to, with its date."""


@dataclass
class PersonalData(CatalaRecord):
    """What § 121 asks of one taxpayer, Catala's ``PersonalData``."""

    property_ownage: list[Period] = field(default_factory=list)
    """The periods the taxpayer owned the property."""

    property_usage_as_principal_residence: list[Period] = field(default_factory=list)
    """The periods the taxpayer used the property as their principal residence."""

    previous_exclusion_sale_date: datetime.date | None = None
    """The date of the most recent other sale § 121(a) applied to; None where there was none."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The field Catala's ``other_section_121a_sale`` maps onto."""
        return {"other_section_121a_sale": "previous_exclusion_sale_date"}

    @classmethod
    def from_catala(cls, values: dict[str, CatalaValue]) -> Self:
        """
        Extends :meth:`CatalaRecord.from_catala` by reading Catala's
        ``OtherSection121aSale`` as the date of the sale, or None.
        """
        return super().from_catala(cls.resolve_previous_sale_date(values))

    @staticmethod
    def resolve_previous_sale_date(
        values: dict[str, CatalaValue],
    ) -> dict[str, CatalaValue]:
        """:return: *values*, an ``OtherSection121aSale`` among them replaced by the date of the sale it names, or None."""
        other_sale = values.get("other_section_121a_sale")
        if other_sale is None:
            return values
        date = None
        if isinstance(other_sale, ConstructorWithContent):
            sale: StructureLiteral = other_sale.content
            date = sale.fields["date_of_sale_or_exchange"]
        return {**values, "other_section_121a_sale": date}


@dataclass(eq=False)
class Seller(Symbol):
    """A taxpayer selling or exchanging a property, as § 121 considers them on their own."""

    personal_data: PersonalData
    """What § 121 asks of the taxpayer."""

    sale_date: datetime.date
    """The date of the sale or exchange."""

    gain: Money
    """The gain from the sale or exchange."""

    @staticmethod
    @symbolic_function
    def days_in_last_five_years(seller: Seller, periods: list[Period]) -> int:
        """
        :return: The days of *periods* in the five years before the sale, as Catala
            counts them: a period beginning within them counts in full, one ending
            before them not at all, and one across their start from that start on.
        """
        days = 0
        for period in periods:
            if seller.sale_date <= Duration(years=5).date_after(period.begin):
                days += (period.end - period.begin).days
            elif seller.sale_date < Duration(years=5).date_after(period.end):
                days += (
                    Duration(years=5).date_after(period.end) - seller.sale_date
                ).days
        return days


@dataclass(eq=False)
class SaleOfResidenceCase(ScopeCase, ABC):
    """A sale or exchange of a property § 121 may exclude the gain of."""

    date_of_sale_or_exchange: datetime.date = datetime.date.min
    """The date of the sale or exchange."""

    gain_from_sale_or_exchange_of_property: Money = field(
        default_factory=lambda: Money.zero
    )
    """The gain from it."""

    @property
    @abstractmethod
    def sellers(self) -> list[Seller]:
        """The taxpayers § 121 considers on their own, in Catala's order."""


class SellerOutput(StrEnum):
    """The outputs of Catala's ``Section121SinglePerson`` scope."""

    REQUIREMENTS_MET = "requirements_met"
    """Whether the requirements of § 121(a) are met."""

    OWNERSHIP_MET = "requirements_ownership_met"
    """Whether the ownership requirement is met."""

    USAGE_MET = "requirements_usage_met"
    """Whether the use requirement is met."""

    GAIN_CAP = "gain_cap"
    """The limitation of § 121(b)(1)."""

    UNCAPPED_EXCLUSION = "income_excluded_from_gross_income_uncapped"
    """The gain excluded, before the limitation."""

    EXCLUSION = "income_excluded_from_gross_income"
    """The gain excluded."""

    RECENT_EXCLUSION = "section_121_b_3_applies"
    """Whether § 121(b)(3) excludes the sale."""


@dataclass(eq=False)
class SinglePersonCase(SaleOfResidenceCase):
    """One taxpayer's sale, Catala's ``Section121SinglePerson`` scope."""

    property_ownage: list[Period] = field(default_factory=list)
    """The periods the taxpayer owned the property."""

    property_usage_as_principal_residence: list[Period] = field(default_factory=list)
    """The periods the taxpayer used it as their principal residence."""

    previous_exclusion_sale_date: datetime.date | None = None
    """The date of the most recent other sale § 121(a) applied to; None where there was none."""

    seller: Seller = field(init=False)
    """The taxpayer."""

    def __post_init__(self) -> None:
        """Makes the taxpayer of the case's inputs a seller."""
        self.seller = Seller(
            personal_data=PersonalData(
                property_ownage=self.property_ownage,
                property_usage_as_principal_residence=self.property_usage_as_principal_residence,
                previous_exclusion_sale_date=self.previous_exclusion_sale_date,
            ),
            sale_date=self.date_of_sale_or_exchange,
            gain=self.gain_from_sale_or_exchange_of_property,
        )

    @classproperty
    def catala_scope(cls) -> str:
        """``Section121SinglePerson``."""
        return "Section121SinglePerson"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The input Catala's ``other_section_121a_sale`` maps onto."""
        return PersonalData.catala_names

    @classmethod
    def from_catala(cls, values: dict[str, CatalaValue]) -> Self:
        """Extends :meth:`CatalaRecord.from_catala` as :meth:`PersonalData.from_catala` does."""
        return super().from_catala(PersonalData.resolve_previous_sale_date(values))

    @property
    def sellers(self) -> list[Seller]:
        return [self.seller]

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`SellerOutput`."""
        return SellerOutput

    def output(self, variable: str) -> CatalaValue:
        if SellerOutput(variable) == SellerOutput.GAIN_CAP:
            return SellerExclusionProvision.gain_cap
        provision = {
            SellerOutput.REQUIREMENTS_MET: ExclusionRequirementsProvision,
            SellerOutput.OWNERSHIP_MET: OwnershipRequirementProvision,
            SellerOutput.USAGE_MET: UseRequirementProvision,
            SellerOutput.RECENT_EXCLUSION: RecentExclusionProvision,
            SellerOutput.UNCAPPED_EXCLUSION: UncappedExclusionProvision,
            SellerOutput.EXCLUSION: SellerExclusionProvision,
        }
        return self.sole_conclusion(provision[SellerOutput(variable)]).answer()


class ReturnConstructor(StrEnum):
    """The constructors of Catala's ``ReturnType``."""

    SINGLE_RETURN = "SingleReturn"
    """A single return."""

    JOINT_RETURN = "JointReturn"
    """A joint return of spouses."""

    SURVIVING_SPOUSE_RETURN = "SingleReturnSurvivingSpouse"
    """A single return of a surviving spouse."""


@dataclass(frozen=True)
class TaxReturn:
    """The return a sale is reported on, and the two taxpayers § 121 considers for it."""

    kind: ReturnConstructor
    """The kind of return."""

    first_person: PersonalData
    """The first taxpayer: the one filing a single return, or the first spouse."""

    second_person: PersonalData
    """The second taxpayer: the same one again on a single return, or the second spouse."""

    @classmethod
    def from_catala(cls, return_type: ConstructorWithContent) -> TaxReturn:
        """:return: The return Catala's ``ReturnType`` constructor states, each person as Catala's ``Section121TwoPersons`` picks them."""
        kind = ReturnConstructor(return_type.constructor.last_part)
        content: StructureLiteral = return_type.content
        match kind:
            case ReturnConstructor.JOINT_RETURN:
                persons = [content.fields["person1"], content.fields["person2"]]
            case ReturnConstructor.SURVIVING_SPOUSE_RETURN:
                persons = [content.fields["return"]] * 2
            case _:
                persons = [content] * 2
        first, second = [PersonalData.from_catala(person.fields) for person in persons]
        return cls(kind=kind, first_person=first, second_person=second)


class TwoPersonsOutput(StrEnum):
    """The outputs of Catala's ``Section121TwoPersons`` scope."""

    JOINT_LIMITATION = "section_121_b_2_A_condition"
    """Whether § 121(b)(2)(A) raises the limitation for a joint return."""

    FIRST_GAIN_CAP = "gain_cap_person_1"
    """The limitation of the first taxpayer on their own."""

    SECOND_GAIN_CAP = "gain_cap_person_2"
    """The limitation of the second taxpayer on their own."""

    UNCAPPED_EXCLUSION = "income_excluded_from_gross_income_uncapped"
    """The gain excluded, before the limitation."""

    EXCLUSION = "income_excluded_from_gross_income"
    """The gain excluded."""


@dataclass(eq=False)
class TwoPersonsCase(SaleOfResidenceCase):
    """A sale reported on a return of one taxpayer or two, Catala's ``Section121TwoPersons`` scope."""

    return_type: TaxReturn | None = None
    """The return the sale is reported on."""

    return_date: datetime.date | None = None
    """The date of the return, which no provision modelled asks for."""

    first_seller: Seller = field(init=False)
    """The first taxpayer."""

    second_seller: Seller = field(init=False)
    """The second taxpayer."""

    def __post_init__(self) -> None:
        """Makes each taxpayer of the return a seller."""
        self.first_seller, self.second_seller = [
            Seller(
                personal_data=person,
                sale_date=self.date_of_sale_or_exchange,
                gain=self.gain_from_sale_or_exchange_of_property,
            )
            for person in (
                self.return_type.first_person,
                self.return_type.second_person,
            )
        ]

    @classproperty
    def catala_scope(cls) -> str:
        """``Section121TwoPersons``."""
        return "Section121TwoPersons"

    @classmethod
    def from_catala(cls, values: dict[str, CatalaValue]) -> Self:
        """Extends :meth:`CatalaRecord.from_catala` by reading Catala's ``ReturnType`` as a :class:`TaxReturn`."""
        return super().from_catala(
            {**values, "return_type": TaxReturn.from_catala(values["return_type"])}
        )

    @property
    def sellers(self) -> list[Seller]:
        return [self.first_seller, self.second_seller]

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`TwoPersonsOutput`."""
        return TwoPersonsOutput

    def output(self, variable: str) -> CatalaValue:
        match TwoPersonsOutput(variable):
            case TwoPersonsOutput.JOINT_LIMITATION:
                return self.sole_conclusion(JointLimitationProvision).holds
            case TwoPersonsOutput.FIRST_GAIN_CAP | TwoPersonsOutput.SECOND_GAIN_CAP:
                return SellerExclusionProvision.gain_cap
            case TwoPersonsOutput.UNCAPPED_EXCLUSION:
                return self.sole_conclusion(ReturnUncappedExclusionProvision).amount
            case TwoPersonsOutput.EXCLUSION:
                return self.sole_conclusion(ReturnExclusionProvision).amount


# %% section 121: conclusions


@dataclass(eq=False)
class SellerConclusion(CatalaConclusion, ABC):
    """A conclusion of § 121 about one taxpayer."""

    seller: Seller
    """The taxpayer."""

    @abstractmethod
    def answer(self) -> CatalaValue:
        """:return: The value the conclusion gives the output of Catala's ``Section121SinglePerson`` scope."""


@dataclass(eq=False)
class SellerCondition(SellerConclusion):
    """Whether a condition of § 121 holds for a taxpayer, false where no rule says it does."""

    holds: bool = False
    """Whether it holds."""

    def answer(self) -> CatalaValue:
        return self.holds


@dataclass(eq=False)
class SellerAmount(SellerConclusion):
    """An amount § 121 gives a taxpayer."""

    amount: Money = field(default_factory=lambda: Money.zero)
    """The amount."""

    def answer(self) -> CatalaValue:
        return self.amount


@dataclass(eq=False)
class OwnershipRequirement(SellerCondition):
    """§ 121(a): the taxpayer owned the property for 2 of the 5 years before the sale."""


@dataclass(eq=False)
class UseRequirement(SellerCondition):
    """§ 121(a): the taxpayer used the property as their principal residence for 2 of the 5 years."""


@dataclass(eq=False)
class ExclusionRequirements(SellerCondition):
    """§ 121(a): the taxpayer meets both requirements."""


@dataclass(eq=False)
class RecentExclusion(SellerCondition):
    """§ 121(b)(3): § 121(a) applied to another sale by the taxpayer in the 2 years before."""


@dataclass(eq=False)
class UncappedExclusion(SellerAmount):
    """§ 121(a): the gain excluded for the taxpayer, before the limitation."""


@dataclass(eq=False)
class SellerExclusion(SellerAmount):
    """§ 121(b)(1): the gain excluded for the taxpayer, up to the limitation."""


@dataclass(eq=False)
class JointLimitation(CaseCondition):
    """§ 121(b)(2)(A): the limitation is doubled for a joint return."""


@dataclass(eq=False)
class ReturnGainCap(CaseAmount):
    """The limitation for the return: § 121(b)(1)'s, or § 121(b)(2)(A)'s."""


@dataclass(eq=False)
class ReturnUncappedExclusion(CaseAmount):
    """The larger of the two taxpayers' gains excluded before the limitation."""


@dataclass(eq=False)
class ReturnExclusion(CaseAmount):
    """The gain excluded for the return, up to its limitation."""


# %% section 121: provisions


@dataclass
class OwnershipRequirementProvision(ScopeProvision[OwnershipRequirement]):
    """
    § 121(a): the periods of ownership in the 5 years before the sale aggregate 2 years
    or more, 730 days by regulation 1.121-1(c)(1).
    """

    @classproperty
    def minimum_days(cls) -> int:
        """Two years, 730 days."""
        return 730

    def query(self) -> Query:
        seller = variable(Seller, domain=self.case.sellers)
        requirement = deduced_variable(OwnershipRequirement)
        query = an(
            entity(requirement).where(
                Seller.days_in_last_five_years(
                    seller, seller.personal_data.property_ownage
                )
                >= self.minimum_days
            )
        )
        with query:
            add(requirement, inference(OwnershipRequirement)(seller=seller, holds=True))
            with alternative():
                add(
                    requirement,
                    inference(OwnershipRequirement)(seller=seller, holds=False),
                )
        return query


@dataclass
class UseRequirementProvision(ScopeProvision[UseRequirement]):
    """
    § 121(a): the periods of use as principal residence in the 5 years before the sale
    aggregate 730 days or more, whether or not they overlap the periods of ownership.
    """

    def query(self) -> Query:
        seller = variable(Seller, domain=self.case.sellers)
        requirement = deduced_variable(UseRequirement)
        query = an(
            entity(requirement).where(
                Seller.days_in_last_five_years(
                    seller, seller.personal_data.property_usage_as_principal_residence
                )
                >= OwnershipRequirementProvision.minimum_days
            )
        )
        with query:
            add(requirement, inference(UseRequirement)(seller=seller, holds=True))
            with alternative():
                add(requirement, inference(UseRequirement)(seller=seller, holds=False))
        return query


@dataclass
class ExclusionRequirementsProvision(ScopeProvision[ExclusionRequirements]):
    """§ 121(a): the taxpayer meets the ownership and the use requirement."""

    def query(self) -> Query:
        ownership = variable(
            OwnershipRequirement,
            domain=OwnershipRequirementProvision(case=self.case).conclusions,
        )
        use = variable(
            UseRequirement, domain=UseRequirementProvision(case=self.case).conclusions
        )
        requirements = deduced_variable(ExclusionRequirements)
        query = an(
            entity(requirements).where(
                use.seller == ownership.seller,
                ownership.holds == True,
                use.holds == True,
            )
        )
        with query:
            add(
                requirements,
                inference(ExclusionRequirements)(seller=ownership.seller, holds=True),
            )
            with alternative(use.seller == ownership.seller):
                add(
                    requirements,
                    inference(ExclusionRequirements)(
                        seller=ownership.seller, holds=False
                    ),
                )
        return query


@dataclass
class RecentExclusionProvision(ScopeProvision[RecentExclusion]):
    """§ 121(b)(3): another sale of the taxpayer § 121(a) applied to lies within 2 years before this one."""

    def query(self) -> Query:
        seller = variable(Seller, domain=self.case.sellers)
        recent = deduced_variable(RecentExclusion)
        query = an(
            entity(recent).where(
                seller.personal_data.previous_exclusion_sale_date != None,
                seller.sale_date
                <= RecentExclusionProvision.two_years_after(
                    seller.personal_data.previous_exclusion_sale_date
                ),
            )
        )
        with query:
            add(recent, inference(RecentExclusion)(seller=seller, holds=True))
            with alternative():
                add(recent, inference(RecentExclusion)(seller=seller, holds=False))
        return query

    @staticmethod
    @symbolic_function
    def two_years_after(day: datetime.date) -> datetime.date:
        """:return: The day two years after *day*."""
        return Duration(years=2).date_after(day)


@dataclass
class UncappedExclusionProvision(ScopeProvision[UncappedExclusion]):
    """§ 121(a): the whole gain where the requirements are met; nothing where § 121(b)(3) excludes the sale."""

    def query(self) -> Query:
        requirements = variable(
            ExclusionRequirements,
            domain=ExclusionRequirementsProvision(case=self.case).conclusions,
        )
        recent = variable(
            RecentExclusion, domain=RecentExclusionProvision(case=self.case).conclusions
        )
        seller = requirements.seller
        exclusion = deduced_variable(UncappedExclusion)
        query = an(
            entity(exclusion).where(recent.seller == seller, recent.holds == True)
        )
        with query:
            add(
                exclusion,
                inference(UncappedExclusion)(seller=seller, amount=Money.zero),
            )
            with alternative(recent.seller == seller, requirements.holds == True):
                add(
                    exclusion,
                    inference(UncappedExclusion)(seller=seller, amount=seller.gain),
                )
            with alternative(recent.seller == seller):
                add(
                    exclusion,
                    inference(UncappedExclusion)(seller=seller, amount=Money.zero),
                )
        return query


@dataclass
class SellerExclusionProvision(ScopeProvision[SellerExclusion]):
    """§ 121(b)(1): the gain excluded may not exceed $250,000."""

    @classproperty
    def gain_cap(cls) -> Money:
        """$250,000."""
        return Money.from_euros(250_000)

    def query(self) -> Query:
        uncapped = variable(
            UncappedExclusion,
            domain=UncappedExclusionProvision(case=self.case).conclusions,
        )
        exclusion = deduced_variable(SellerExclusion)
        query = an(entity(exclusion).where(uncapped.amount >= self.gain_cap))
        with query:
            add(
                exclusion,
                inference(SellerExclusion)(
                    seller=uncapped.seller, amount=self.gain_cap
                ),
            )
            with alternative():
                add(
                    exclusion,
                    inference(SellerExclusion)(
                        seller=uncapped.seller, amount=uncapped.amount
                    ),
                )
        return query


@dataclass
class JointLimitationProvision(ScopeProvision[JointLimitation]):
    """
    § 121(b)(2)(A): on a joint return, where either spouse meets the ownership
    requirement, both meet the use requirement and § 121(b)(3) excludes neither.
    """

    def query(self) -> Query:
        case = variable(TwoPersonsCase, domain=[self.case])
        ownership = variable(
            OwnershipRequirement,
            domain=OwnershipRequirementProvision(case=self.case).conclusions,
        )
        use = variable(
            UseRequirement, domain=UseRequirementProvision(case=self.case).conclusions
        )
        recent = variable(
            RecentExclusion, domain=RecentExclusionProvision(case=self.case).conclusions
        )
        limitation = deduced_variable(JointLimitation)
        query = an(
            entity(limitation).where(
                case.return_type.kind == ReturnConstructor.JOINT_RETURN,
                exists(ownership, ownership.holds == True),
                not_(exists(use, use.holds == False)),
                not_(exists(recent, recent.holds == True)),
            )
        )
        with query:
            add(limitation, inference(JointLimitation)(case=case, holds=True))
            with alternative():
                add(limitation, inference(JointLimitation)(case=case, holds=False))
        return query


@dataclass
class ReturnGainCapProvision(ScopeProvision[ReturnGainCap]):
    """§ 121(b)(2)(A) substitutes $500,000 for § 121(b)(1)'s $250,000."""

    @classproperty
    def joint_gain_cap(cls) -> Money:
        """$500,000."""
        return Money.from_euros(500_000)

    def query(self) -> Query:
        limitation = variable(
            JointLimitation, domain=JointLimitationProvision(case=self.case).conclusions
        )
        cap = deduced_variable(ReturnGainCap)
        query = an(entity(cap).where(limitation.holds == True))
        with query:
            add(
                cap,
                inference(ReturnGainCap)(
                    case=limitation.case, amount=self.joint_gain_cap
                ),
            )
            with alternative():
                add(
                    cap,
                    inference(ReturnGainCap)(
                        case=limitation.case, amount=SellerExclusionProvision.gain_cap
                    ),
                )
        return query


@dataclass
class ReturnUncappedExclusionProvision(ScopeProvision[ReturnUncappedExclusion]):
    """The larger of the gains § 121(a) excludes for either taxpayer on their own."""

    def query(self) -> Query:
        uncapped = variable(
            UncappedExclusion,
            domain=UncappedExclusionProvision(case=self.case).conclusions,
        )
        largest = an(entity(maximum(uncapped.amount))).first()
        case = variable(TwoPersonsCase, domain=[self.case])
        return an(entity(inference(ReturnUncappedExclusion)(case=case, amount=largest)))


@dataclass
class ReturnExclusionProvision(ScopeProvision[ReturnExclusion]):
    """§ 121(b): the gain excluded for the return may not exceed its limitation."""

    def query(self) -> Query:
        uncapped = variable(
            ReturnUncappedExclusion,
            domain=ReturnUncappedExclusionProvision(case=self.case).conclusions,
        )
        cap = variable(
            ReturnGainCap, domain=ReturnGainCapProvision(case=self.case).conclusions
        )
        exclusion = deduced_variable(ReturnExclusion)
        query = an(entity(exclusion).where(uncapped.amount >= cap.amount))
        with query:
            add(exclusion, inference(ReturnExclusion)(case=cap.case, amount=cap.amount))
            with alternative():
                add(
                    exclusion,
                    inference(ReturnExclusion)(case=cap.case, amount=uncapped.amount),
                )
        return query


# %% test files


class UnitedStatesTaxCodeTestFile(ScopeTestFile, StrEnum):
    """The test files of Catala's ``us_tax_code`` example."""

    SECTION_121 = "test_section_121.catala_en"
    """The tests of § 121."""

    SECTION_132 = "test_section_132.catala_en"
    """The tests of § 132."""

    @property
    def directory(self) -> Path:
        """:file:`us_tax_code/tests`."""
        return CatalaDirectory.ROOT / "us_tax_code" / "tests"

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """The scopes of the section the file tests."""
        match self:
            case UnitedStatesTaxCodeTestFile.SECTION_121:
                return [SinglePersonCase, TwoPersonsCase]
            case UnitedStatesTaxCodeTestFile.SECTION_132:
                return [EmployeeDiscountCase]
