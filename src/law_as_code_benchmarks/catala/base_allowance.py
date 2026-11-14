"""
The base of family allowances (*allocations familiales*): the household's bracket by
its resources, the right of `L521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000029963006>`__, what is paid for each child by its rank, in
metropolitan France, overseas and in Mayotte, and its division for shared residences.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from fractions import Fraction

from krrood.entity_query_language.factories import (
    add,
    alternative,
    an,
    deduced_variable,
    entity,
    in_,
    inference,
    refinement,
    variable,
)
from krrood.entity_query_language.factories import sum as total
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.catala.amounts import (
    MayotteRates,
    MayotteRateSchedule,
    ResourceCeilingRevaluations,
    ResourceCeilings,
)
from law_as_code_benchmarks.catala.conclusions import (
    ApplicableResourceCeilings,
    BaseAllowanceRight,
    ChargeShareOfChild,
    ChildrenRatio,
    EntitledChildren,
    FirstChildAmount,
    HouseholdBracket,
    InitialBaseAmount,
    LaterChildrenAmount,
    MayotteLaterChildrenAmount,
    MayotteThirdChildAmount,
    MonthlyBaseAmount,
    OverseasRegime,
    PaidBaseAllowance,
    ResourceBracket,
    SecondChildAmount,
)
from law_as_code_benchmarks.catala.domain import (
    ChargeShare,
    Child,
    ChildCare,
    DatedValue,
    Household,
    Territory,
)
from law_as_code_benchmarks.catala.entitlement import (
    EntitledChildrenProvision,
    MonthlyBaseProvision,
    OverseasRegimeProvision,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.provision import (
    ChildProvision,
    FamilyBenefitsProvision,
)
from law_as_code_benchmarks.law.period import Period

# %% the household's bracket


@dataclass
class ResourceCeilingsProvision(FamilyBenefitsProvision[ApplicableResourceCeilings]):
    """
    `D521-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044809227>`__: the two ceilings, each raised for every child giving a right to
    family benefits; the ceilings revalued for the assessment date's year where
    Catala states them, else those of the article.
    """

    @classproperty
    def article_ceilings(cls) -> ResourceCeilings:
        """
        The ceilings I and II of the article set, and their raise per child.
        """
        return ResourceCeilings(
            period=Period(lower=datetime.date.min),
            source="Code de la sécurité sociale, D521-3 (LEGIARTI000044809227)",
            first_ceiling=Money.from_euros(55950),
            second_ceiling=Money.from_euros(78300),
            raise_per_child=Money.from_euros(5595),
        )

    def query(self) -> Query:
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        revalued = variable(
            ResourceCeilings,
            domain=self.values_in_force(
                [member.value for member in ResourceCeilingRevaluations]
            ),
        )
        article = variable(ResourceCeilings, domain=[self.article_ceilings])
        ceilings = deduced_variable(ApplicableResourceCeilings)
        day = children.household.assessment_date
        query = an(entity(ceilings).where(DatedValue.is_in_force(article, day)))
        with query:
            add(
                ceilings,
                inference(ApplicableResourceCeilings)(
                    household=children.household,
                    first_ceiling=article.first_ceiling
                    + article.raise_per_child * children.number_of_children,
                    second_ceiling=article.second_ceiling
                    + article.raise_per_child * children.number_of_children,
                ),
            )
            with refinement(DatedValue.is_in_force(revalued, day)):
                add(
                    ceilings,
                    inference(ApplicableResourceCeilings)(
                        household=children.household,
                        first_ceiling=revalued.first_ceiling
                        + revalued.raise_per_child * children.number_of_children,
                        second_ceiling=revalued.second_ceiling
                        + revalued.raise_per_child * children.number_of_children,
                    ),
                )
        return query


@dataclass
class HouseholdBracketProvision(FamilyBenefitsProvision[HouseholdBracket]):
    """
    The bracket of `D521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680318>`__ and `D521-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680324>`__: the first up to the first ceiling, the
    second up to the second, the third above it. Before the modulation by resources
    began, every household is in the first.
    """

    @classproperty
    def first_day_of_modulation(cls) -> datetime.date:
        """
        The day article 85 of the loi n° 2014-1554 began modulating family allowances by
        resources, July 1, 2015.
        """
        return datetime.date(2015, 7, 1)

    def query(self) -> Query:
        ceilings = variable(
            ApplicableResourceCeilings,
            domain=ResourceCeilingsProvision(household=self.household).conclusions,
        )
        bracket = deduced_variable(HouseholdBracket)
        query = an(
            entity(bracket).where(
                ceilings.household.assessment_date < self.first_day_of_modulation
            )
        )
        with query:
            add(
                bracket,
                inference(HouseholdBracket)(
                    household=ceilings.household, bracket=ResourceBracket.FIRST
                ),
            )
            with alternative(ceilings.household.resources <= ceilings.first_ceiling):
                add(
                    bracket,
                    inference(HouseholdBracket)(
                        household=ceilings.household, bracket=ResourceBracket.FIRST
                    ),
                )
            with alternative(ceilings.household.resources <= ceilings.second_ceiling):
                add(
                    bracket,
                    inference(HouseholdBracket)(
                        household=ceilings.household, bracket=ResourceBracket.SECOND
                    ),
                )
            with alternative():
                add(
                    bracket,
                    inference(HouseholdBracket)(
                        household=ceilings.household, bracket=ResourceBracket.THIRD
                    ),
                )
        return query


# %% the right to family allowances


@dataclass
class BaseAllowanceRightProvision(FamilyBenefitsProvision[BaseAllowanceRight]):
    """
    `L521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000029963006>`__: family allowances are due from the second child. `L755-12 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000029962999>`__
    excepts the overseas departments, and article 7 of the décret n°2002-423 Mayotte,
    where they are due from the first.
    """

    @classproperty
    def minimum_number_of_children(cls) -> int:
        """
        The children from which allowances are due, two.
        """
        return 2

    def query(self) -> Query:
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        overseas = variable(
            OverseasRegime,
            domain=OverseasRegimeProvision(household=self.household).conclusions,
        )
        right = deduced_variable(BaseAllowanceRight)
        query = an(
            entity(right).where(
                overseas.holds == True, children.number_of_children >= 1
            )
        )
        with query:
            add(
                right,
                inference(BaseAllowanceRight)(household=children.household, holds=True),
            )
            with alternative(
                children.household.residence == Territory.MAYOTTE,
                children.number_of_children >= 1,
            ):
                add(
                    right,
                    inference(BaseAllowanceRight)(
                        household=children.household, holds=True
                    ),
                )
            with alternative(
                children.number_of_children >= self.minimum_number_of_children
            ):
                add(
                    right,
                    inference(BaseAllowanceRight)(
                        household=children.household, holds=True
                    ),
                )
            with alternative():
                add(
                    right,
                    inference(BaseAllowanceRight)(
                        household=children.household, holds=False
                    ),
                )
        return query


# %% what is paid for each child by its rank


@dataclass
class RankRates:
    """
    The rates of the monthly base the provisions paying for a child by its rank share.
    """

    @classproperty
    def single_child_rate(cls) -> Fraction:
        """II of `D755-5 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006738575>`__ and 1° of article 7 of the décret n°2002-423: the rate for a single child, 5.88 %."""
        return Fraction("5.88") / 100

    @classproperty
    def mayotte_second_child_rate(cls) -> Fraction:
        """
        2° of article 7 of the décret n°2002-423: the rate for a second child in
        Mayotte, 32 %.
        """
        return Fraction(32, 100)

    @classproperty
    def mayotte_third_child_rate(cls) -> Fraction:
        """
        3° of article 7 of the décret n°2002-423: the rate for a third child in Mayotte,
        16 %.
        """
        return Fraction(16, 100)

    @classproperty
    def mayotte_later_child_rate(cls) -> Fraction:
        """
        4° of article 7 of the décret n°2002-423: the rate for each child from the
        fourth in Mayotte, 4.63 %.
        """
        return Fraction("4.63") / 100

    @classproperty
    def amount_for_child_before_2012(cls) -> Money:
        """
        The annex to the décret n°2002-423: what is paid for a single child in Mayotte
        to a household that had a child in its charge before 2012.
        """
        return Money(cents=5728)


@dataclass
class FirstChildAmountProvision(FamilyBenefitsProvision[FirstChildAmount], RankRates):
    """
    Nothing by default.

    `D755-5 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006738575>`__ pays a single child overseas the single-child rate. In Mayotte, article 7 of the décret n°2002-423 pays any first child that rate, its
    annex the rate of the assessment year until 2020, and a fixed amount to a household
    that had a child in its charge before 2012.
    """

    def query(self) -> Query:
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        base = variable(
            MonthlyBaseAmount,
            domain=MonthlyBaseProvision(household=self.household).conclusions,
        )
        overseas = variable(
            OverseasRegime,
            domain=OverseasRegimeProvision(household=self.household).conclusions,
        )
        rates = variable(
            MayotteRates,
            domain=self.values_in_force(
                [member.value for member in MayotteRateSchedule]
            ),
        )
        household = children.household
        amount = deduced_variable(FirstChildAmount)
        query = an(
            entity(amount).where(
                household.residence == Territory.MAYOTTE,
                household.had_child_before_2012 == True,
                children.number_of_children > 0,
            )
        )
        with query:
            add(
                amount,
                inference(FirstChildAmount)(
                    household=household, amount=self.amount_for_child_before_2012
                ),
            )
            with alternative(
                household.residence == Territory.MAYOTTE,
                household.had_child_before_2012 == False,
                DatedValue.is_in_force(rates, household.assessment_date),
                children.number_of_children > 0,
            ):
                add(
                    amount,
                    inference(FirstChildAmount)(
                        household=household, amount=base.amount * rates.first_child
                    ),
                )
            with alternative(
                household.residence == Territory.MAYOTTE,
                children.number_of_children > 0,
            ):
                add(
                    amount,
                    inference(FirstChildAmount)(
                        household=household,
                        amount=base.amount * self.single_child_rate,
                    ),
                )
            with alternative(overseas.holds == True, children.number_of_children == 1):
                add(
                    amount,
                    inference(FirstChildAmount)(
                        household=household,
                        amount=base.amount * self.single_child_rate,
                    ),
                )
            with alternative():
                add(
                    amount,
                    inference(FirstChildAmount)(household=household, amount=Money.zero),
                )
        return query


@dataclass
class SecondChildAmountProvision(FamilyBenefitsProvision[SecondChildAmount], RankRates):
    """
    `D521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680318>`__: the rate of the household's bracket for a second child. In Mayotte,
    article 7 of the décret n°2002-423 pays a second child its own rate, and its annex
    the rate of the assessment year until 2020.
    """

    def query(self) -> Query:
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        base = variable(
            MonthlyBaseAmount,
            domain=MonthlyBaseProvision(household=self.household).conclusions,
        )
        bracket = variable(
            HouseholdBracket,
            domain=HouseholdBracketProvision(household=self.household).conclusions,
        )
        rates = variable(
            MayotteRates,
            domain=self.values_in_force(
                [member.value for member in MayotteRateSchedule]
            ),
        )
        household = children.household
        amount = deduced_variable(SecondChildAmount)
        query = an(
            entity(amount).where(
                household.residence == Territory.MAYOTTE,
                DatedValue.is_in_force(rates, household.assessment_date),
                children.number_of_children > 1,
            )
        )
        with query:
            add(
                amount,
                inference(SecondChildAmount)(
                    household=household, amount=base.amount * rates.second_child
                ),
            )
            with alternative(
                household.residence == Territory.MAYOTTE,
                children.number_of_children > 1,
            ):
                add(
                    amount,
                    inference(SecondChildAmount)(
                        household=household,
                        amount=base.amount * self.mayotte_second_child_rate,
                    ),
                )
            with alternative(children.number_of_children > 1):
                add(
                    amount,
                    inference(SecondChildAmount)(
                        household=household,
                        amount=base.amount * bracket.bracket.value.second_child,
                    ),
                )
            with alternative():
                add(
                    amount,
                    inference(SecondChildAmount)(
                        household=household, amount=Money.zero
                    ),
                )
        return query


@dataclass
class LaterChildrenAmountProvision(FamilyBenefitsProvision[LaterChildrenAmount]):
    """
    `D521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680318>`__: the rate of the household's bracket for the third child and each
    one after.
    """

    def query(self) -> Query:
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        base = variable(
            MonthlyBaseAmount,
            domain=MonthlyBaseProvision(household=self.household).conclusions,
        )
        bracket = variable(
            HouseholdBracket,
            domain=HouseholdBracketProvision(household=self.household).conclusions,
        )
        amount = deduced_variable(LaterChildrenAmount)
        query = an(entity(amount).where(children.number_of_children > 2))
        with query:
            add(
                amount,
                inference(LaterChildrenAmount)(
                    household=children.household,
                    amount=(base.amount * bracket.bracket.value.later_child)
                    * (children.number_of_children - 2),
                ),
            )
            with alternative():
                add(
                    amount,
                    inference(LaterChildrenAmount)(
                        household=children.household, amount=Money.zero
                    ),
                )
        return query


@dataclass
class MayotteThirdChildAmountProvision(
    FamilyBenefitsProvision[MayotteThirdChildAmount], RankRates
):
    """
    3° of article 7 of the décret n°2002-423: the third child's rate in Mayotte, and the
    rate of the assessment year until 2020 by its annex.
    """

    def query(self) -> Query:
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        base = variable(
            MonthlyBaseAmount,
            domain=MonthlyBaseProvision(household=self.household).conclusions,
        )
        rates = variable(
            MayotteRates,
            domain=self.values_in_force(
                [member.value for member in MayotteRateSchedule]
            ),
        )
        household = children.household
        amount = deduced_variable(MayotteThirdChildAmount)
        query = an(
            entity(amount).where(
                DatedValue.is_in_force(rates, household.assessment_date),
                children.number_of_children > 2,
            )
        )
        with query:
            add(
                amount,
                inference(MayotteThirdChildAmount)(
                    household=household, amount=base.amount * rates.third_child
                ),
            )
            with alternative(children.number_of_children > 2):
                add(
                    amount,
                    inference(MayotteThirdChildAmount)(
                        household=household,
                        amount=base.amount * self.mayotte_third_child_rate,
                    ),
                )
            with alternative():
                add(
                    amount,
                    inference(MayotteThirdChildAmount)(
                        household=household, amount=Money.zero
                    ),
                )
        return query


@dataclass
class MayotteLaterChildrenAmountProvision(
    FamilyBenefitsProvision[MayotteLaterChildrenAmount], RankRates
):
    """
    4° of article 7 of the décret n°2002-423: the rate for the fourth child in Mayotte
    and each one after.
    """

    def query(self) -> Query:
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        base = variable(
            MonthlyBaseAmount,
            domain=MonthlyBaseProvision(household=self.household).conclusions,
        )
        amount = deduced_variable(MayotteLaterChildrenAmount)
        query = an(entity(amount).where(children.number_of_children > 3))
        with query:
            add(
                amount,
                inference(MayotteLaterChildrenAmount)(
                    household=children.household,
                    amount=(base.amount * self.mayotte_later_child_rate)
                    * (children.number_of_children - 3),
                ),
            )
            with alternative():
                add(
                    amount,
                    inference(MayotteLaterChildrenAmount)(
                        household=children.household, amount=Money.zero
                    ),
                )
        return query


@dataclass
class InitialBaseAmountProvision(FamilyBenefitsProvision[InitialBaseAmount]):
    """
    `D521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680318>`__: what is paid for the second child and for those after it.
    `D755-5 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006738575>`__ pays a single child overseas what is paid for a first child, and
    article 7 of the décret n°2002-423 adds up all four ranks in Mayotte.
    """

    def query(self) -> Query:
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        overseas = variable(
            OverseasRegime,
            domain=OverseasRegimeProvision(household=self.household).conclusions,
        )
        first = variable(
            FirstChildAmount,
            domain=FirstChildAmountProvision(household=self.household).conclusions,
        )
        second = variable(
            SecondChildAmount,
            domain=SecondChildAmountProvision(household=self.household).conclusions,
        )
        later = variable(
            LaterChildrenAmount,
            domain=LaterChildrenAmountProvision(household=self.household).conclusions,
        )
        mayotte_third = variable(
            MayotteThirdChildAmount,
            domain=MayotteThirdChildAmountProvision(
                household=self.household
            ).conclusions,
        )
        mayotte_later = variable(
            MayotteLaterChildrenAmount,
            domain=MayotteLaterChildrenAmountProvision(
                household=self.household
            ).conclusions,
        )
        household = children.household
        amount = deduced_variable(InitialBaseAmount)
        query = an(entity(amount).where(household.residence == Territory.MAYOTTE))
        with query:
            add(
                amount,
                inference(InitialBaseAmount)(
                    household=household,
                    amount=first.amount
                    + second.amount
                    + mayotte_third.amount
                    + mayotte_later.amount,
                ),
            )
            with alternative(overseas.holds == True, children.number_of_children == 1):
                add(
                    amount,
                    inference(InitialBaseAmount)(
                        household=household, amount=first.amount
                    ),
                )
            with alternative():
                add(
                    amount,
                    inference(InitialBaseAmount)(
                        household=household, amount=second.amount + later.amount
                    ),
                )
        return query


# %% shared residences


@dataclass
class ChargeShareProvision(ChildProvision[ChargeShareOfChild]):
    """
    `L521-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000039099826>`__: a child counts in full for the household taking care of them, or the
    parent the two named for a shared residence; for half where the parents share the
    allowances, which they may since the décret n° 2007-550; and for nothing where child
    welfare receives the child's part.
    """

    @classproperty
    def first_day_of_sharing(cls) -> datetime.date:
        """
        The day the décret n° 2007-550 let parents share the allowances of a child in
        shared residence, May 1, 2007.
        """
        return datetime.date(2007, 5, 1)

    @classproperty
    def full_care(cls) -> frozenset[ChildCare]:
        """
        The kinds of care a child counts in full for.
        """
        return frozenset(
            {
                ChildCare.EFFECTIVE_AND_PERMANENT,
                ChildCare.SHARED_RESIDENCE_SINGLE_RECIPIENT,
                ChildCare.SOCIAL_SERVICES_PAID_TO_FAMILY,
            }
        )

    def query(self) -> Query:
        household = variable(Household, domain=[self.household])
        child = variable(Child, domain=self.household.children)
        share = deduced_variable(ChargeShareOfChild)
        query = an(entity(share).where(in_(child.care, self.full_care)))
        with query:
            add(
                share,
                inference(ChargeShareOfChild)(child=child, share=ChargeShare.FULL),
            )
            with alternative(
                child.care == ChildCare.SHARED_RESIDENCE_SHARED_ALLOWANCE,
                household.assessment_date < self.first_day_of_sharing,
            ):
                add(
                    share,
                    inference(ChargeShareOfChild)(child=child, share=ChargeShare.FULL),
                )
            with alternative(child.care == ChildCare.SHARED_RESIDENCE_SHARED_ALLOWANCE):
                add(
                    share,
                    inference(ChargeShareOfChild)(child=child, share=ChargeShare.HALF),
                )
            with alternative(child.care == ChildCare.SOCIAL_SERVICES_PAID_TO_SERVICES):
                add(
                    share,
                    inference(ChargeShareOfChild)(child=child, share=ChargeShare.NONE),
                )
        return query


@dataclass
class ChildrenRatioProvision(FamilyBenefitsProvision[ChildrenRatio]):
    """
    `R521-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006750610>`__: the average number of entitled children, each counting for its share,
    over their total number; zero without entitled children.
    """

    def query(self) -> Query:
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        share = variable(
            ChargeShareOfChild,
            domain=ChargeShareProvision(household=self.household).conclusions,
        )
        average = an(
            entity(total(share.share.value, default=Fraction(0))).where(
                in_(share.child, children.children)
            )
        )
        ratio = deduced_variable(ChildrenRatio)
        query = an(entity(ratio).where(children.number_of_children > 0))
        with query:
            add(
                ratio,
                inference(ChildrenRatio)(
                    household=children.household,
                    ratio=average.first() / children.number_of_children,
                ),
            )
            with alternative():
                add(
                    ratio,
                    inference(ChildrenRatio)(
                        household=children.household, ratio=Fraction(0)
                    ),
                )
        return query


@dataclass
class PaidBaseAllowanceProvision(FamilyBenefitsProvision[PaidBaseAllowance]):
    """
    `R521-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006750610>`__: the allowances for all entitled children times the ratio of their
    average number to their total, where the household has a right to them.
    """

    def query(self) -> Query:
        right = variable(
            BaseAllowanceRight,
            domain=BaseAllowanceRightProvision(household=self.household).conclusions,
        )
        initial = variable(
            InitialBaseAmount,
            domain=InitialBaseAmountProvision(household=self.household).conclusions,
        )
        ratio = variable(
            ChildrenRatio,
            domain=ChildrenRatioProvision(household=self.household).conclusions,
        )
        paid = deduced_variable(PaidBaseAllowance)
        query = an(entity(paid).where(right.holds == True))
        with query:
            add(
                paid,
                inference(PaidBaseAllowance)(
                    household=right.household, amount=initial.amount * ratio.ratio
                ),
            )
            with alternative():
                add(
                    paid,
                    inference(PaidBaseAllowance)(
                        household=right.household, amount=Money.zero
                    ),
                )
        return query
