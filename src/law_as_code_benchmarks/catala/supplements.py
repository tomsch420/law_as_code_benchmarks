"""
What family allowances add to their base: the age supplements of `L521-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006743289>`__, the flat
allowance of `L521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000029963006>`__, the degressive supplements of `D521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680318>`__ and `D521-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680324>`__,
and the amount paid in all.
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
    variable,
)
from krrood.entity_query_language.factories import sum as total
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.catala.base_allowance import (
    BaseAllowanceRightProvision,
    ChargeShareProvision,
    HouseholdBracketProvision,
    PaidBaseAllowanceProvision,
    ResourceCeilingsProvision,
)
from law_as_code_benchmarks.catala.conclusions import (
    AgeSupplementMinimumAge,
    AgeSupplementRight,
    AllowanceDegressiveSupplement,
    ApplicableResourceCeilings,
    BaseAllowanceRight,
    ChargeShareOfChild,
    ConditionsBesidesAge,
    DegressiveSupplementRight,
    EntitledChildren,
    FamilyAllowance,
    FlatAllowanceDegressiveSupplement,
    FlatAllowanceRight,
    HouseholdAmount,
    HouseholdBracket,
    InitialAgeSupplement,
    MonthlyBaseAmount,
    OverseasRegime,
    PaidAgeSupplements,
    PaidBaseAllowance,
    PaidFlatAllowance,
    SharedAgeSupplement,
    SupplementedAllowance,
)
from law_as_code_benchmarks.catala.domain import (
    Child,
    Household,
)
from law_as_code_benchmarks.catala.entitlement import (
    ConditionsBesidesAgeProvision,
    EntitledChildrenProvision,
    FamilyBenefitEntitlementProvision,
    MonthlyBaseProvision,
    OverseasRegimeProvision,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.provision import (
    ChildProvision,
    FamilyBenefitsProvision,
)
from law_as_code_benchmarks.law.provision import ConclusionType

# %% age supplements


@dataclass
class AgeSupplementMinimumAgeProvision(ChildProvision[AgeSupplementMinimumAge]):
    """
    `R521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000018735853>`__: a child gives a right to an age supplement from age 14; before the
    décret n° 2008-409, from age 11. A child whose eleventh birthday came by April 30,
    2008, keeps the age of 16 the article set for the higher supplement before it. From
    March 1, 2026, the décret n° 2026-138 sets 18 for a child born from March 1, 2012.
    """

    @classproperty
    def minimum_age(cls) -> int:
        """
        The age the article sets, 14.
        """
        return 14

    @classproperty
    def minimum_age_before_2008(cls) -> int:
        """
        The age of the higher supplement before the décret n° 2008-409, 16, which a
        child eleven by April 30, 2008, keeps as its minimum age.
        """
        return 16

    @classproperty
    def lower_supplement_age_before_2008(cls) -> int:
        """
        The age of the lower supplement before the décret n° 2008-409, 11.
        """
        return 11

    @classproperty
    def last_eleventh_birthday_before_2008(cls) -> datetime.date:
        """
        The last day of the article's version before the décret n° 2008-409, and so the
        last day an eleventh birthday keeps its age of 16, April 30, 2008.
        """
        return datetime.date(2008, 4, 30)

    @classproperty
    def minimum_age_from_2026(cls) -> int:
        """
        The age the décret n° 2026-138 sets, 18.
        """
        return 18

    @classproperty
    def first_day_of_2026_reform(cls) -> datetime.date:
        """
        The day the décret n° 2026-138 takes effect, March 1, 2026.
        """
        return datetime.date(2026, 3, 1)

    @classproperty
    def first_birth_date_of_2026_reform(cls) -> datetime.date:
        """
        The first birth date the décret n° 2026-138 applies to, March 1, 2012.
        """
        return datetime.date(2012, 3, 1)

    def query(self) -> Query:
        household = variable(Household, domain=[self.household])
        child = variable(Child, domain=self.household.children)
        day = household.assessment_date
        age = deduced_variable(AgeSupplementMinimumAge)
        # A condition on the child comes first, true for every child born: otherwise
        # only the first child is concluded (cram2/cognitive_robot_abstract_machine#964).
        query = an(
            entity(age).where(
                child.birth_date <= day,
                day <= self.last_eleventh_birthday_before_2008,
            )
        )
        with query:
            add(
                age,
                inference(AgeSupplementMinimumAge)(
                    child=child, age=self.lower_supplement_age_before_2008
                ),
            )
            with alternative(
                Child.birthday(child, self.lower_supplement_age_before_2008)
                <= self.last_eleventh_birthday_before_2008
            ):
                add(
                    age,
                    inference(AgeSupplementMinimumAge)(
                        child=child, age=self.minimum_age_before_2008
                    ),
                )
            with alternative(
                day >= self.first_day_of_2026_reform,
                child.birth_date >= self.first_birth_date_of_2026_reform,
            ):
                add(
                    age,
                    inference(AgeSupplementMinimumAge)(
                        child=child, age=self.minimum_age_from_2026
                    ),
                )
            with alternative():
                add(
                    age,
                    inference(AgeSupplementMinimumAge)(
                        child=child, age=self.minimum_age
                    ),
                )
        return query


@dataclass
class AgeSupplementRightProvision(ChildProvision[AgeSupplementRight]):
    """
    `L521-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006743289>`__: every child but the oldest gives a right to an age supplement from
    the minimum age; every child does in a household with at least the number of
    entitled children of `R521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000018735853>`__.
    """

    @classproperty
    def number_of_children_for_every_child(cls) -> int:
        """`R521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000018735853>`__: the entitled children from which every child gives a right, three."""
        return 3

    def query(self) -> Query:
        minimum = variable(
            AgeSupplementMinimumAge,
            domain=AgeSupplementMinimumAgeProvision(
                household=self.household
            ).conclusions,
        )
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        household = children.household
        reached = (
            Child.birthday(minimum.child, minimum.age) <= household.assessment_date
        )
        right = deduced_variable(AgeSupplementRight)
        query = an(
            entity(right).where(
                reached,
                children.number_of_children >= self.number_of_children_for_every_child,
            )
        )
        with query:
            add(right, inference(AgeSupplementRight)(child=minimum.child, holds=True))
            with alternative(minimum.child != household.oldest_child, reached):
                add(
                    right,
                    inference(AgeSupplementRight)(child=minimum.child, holds=True),
                )
            with alternative():
                add(
                    right,
                    inference(AgeSupplementRight)(child=minimum.child, holds=False),
                )
        return query


@dataclass
class InitialAgeSupplementProvision(ChildProvision[InitialAgeSupplement]):
    """
    `D521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680318>`__: the rate of the household's bracket for a child giving a right to
    an age supplement, nothing for another; before the décret n° 2008-409, a lower rate
    until age 16. `D755-5 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006738575>`__ sets a single child overseas its own rates, from age 11 and from
    age 16.
    """

    @classproperty
    def rate_until_16_before_2008(cls) -> Fraction:
        """
        The rate until age 16 before the décret n° 2008-409, 9 %.
        """
        return Fraction(9, 100)

    @classproperty
    def single_child_rate_from_11(cls) -> Fraction:
        """
        The rate for a single child overseas from age 11, 3.69 %.
        """
        return Fraction("3.69") / 100

    @classproperty
    def single_child_rate_from_16(cls) -> Fraction:
        """
        The rate for a single child overseas from age 16, 5.67 %.
        """
        return Fraction("5.67") / 100

    def query(self) -> Query:
        right = variable(
            AgeSupplementRight,
            domain=AgeSupplementRightProvision(household=self.household).conclusions,
        )
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        overseas = variable(
            OverseasRegime,
            domain=OverseasRegimeProvision(household=self.household).conclusions,
        )
        base = variable(
            MonthlyBaseAmount,
            domain=MonthlyBaseProvision(household=self.household).conclusions,
        )
        bracket = variable(
            HouseholdBracket,
            domain=HouseholdBracketProvision(household=self.household).conclusions,
        )
        day = children.household.assessment_date
        supplement = deduced_variable(InitialAgeSupplement)
        query = an(
            entity(supplement).where(
                right.holds == True,
                overseas.holds == True,
                children.number_of_children == 1,
                Child.birthday(right.child, 11) <= day,
                Child.birthday(right.child, 16) > day,
            )
        )
        with query:
            add(
                supplement,
                inference(InitialAgeSupplement)(
                    child=right.child,
                    amount=base.amount * self.single_child_rate_from_11,
                ),
            )
            with alternative(
                right.holds == True,
                overseas.holds == True,
                children.number_of_children == 1,
                Child.birthday(right.child, 16) <= day,
            ):
                add(
                    supplement,
                    inference(InitialAgeSupplement)(
                        child=right.child,
                        amount=base.amount * self.single_child_rate_from_16,
                    ),
                )
            with alternative(
                right.holds == True,
                day
                <= AgeSupplementMinimumAgeProvision.last_eleventh_birthday_before_2008,
                Child.birthday(
                    right.child,
                    AgeSupplementMinimumAgeProvision.minimum_age_before_2008,
                )
                > day,
            ):
                add(
                    supplement,
                    inference(InitialAgeSupplement)(
                        child=right.child,
                        amount=base.amount * self.rate_until_16_before_2008,
                    ),
                )
            with alternative(right.holds == True):
                add(
                    supplement,
                    inference(InitialAgeSupplement)(
                        child=right.child,
                        amount=base.amount * bracket.bracket.value.age_supplement,
                    ),
                )
            with alternative():
                add(
                    supplement,
                    inference(InitialAgeSupplement)(
                        child=right.child, amount=Money.zero
                    ),
                )
        return query


@dataclass
class SharedAgeSupplementProvision(ChildProvision[SharedAgeSupplement]):
    """
    `R521-4 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006750613>`__: the age supplement times the child's share, halved for a shared
    residence.
    """

    def query(self) -> Query:
        initial = variable(
            InitialAgeSupplement,
            domain=InitialAgeSupplementProvision(household=self.household).conclusions,
        )
        share = variable(
            ChargeShareOfChild,
            domain=ChargeShareProvision(household=self.household).conclusions,
        )
        return an(
            entity(
                inference(SharedAgeSupplement)(
                    child=initial.child, amount=initial.amount * share.share.value
                )
            ).where(share.child == initial.child)
        )


@dataclass
class PaidAgeSupplementsProvision(FamilyBenefitsProvision[PaidAgeSupplements]):
    """
    The age supplements of the entitled children, where the household has a right to
    family allowances.
    """

    def query(self) -> Query:
        right = variable(
            BaseAllowanceRight,
            domain=BaseAllowanceRightProvision(household=self.household).conclusions,
        )
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        supplement = variable(
            SharedAgeSupplement,
            domain=SharedAgeSupplementProvision(household=self.household).conclusions,
        )
        supplements = an(
            entity(total(supplement.amount, default=Money.zero)).where(
                in_(supplement.child, children.children)
            )
        )
        paid = deduced_variable(PaidAgeSupplements)
        query = an(entity(paid).where(right.holds == True))
        with query:
            add(
                paid,
                inference(PaidAgeSupplements)(
                    household=right.household, amount=supplements.first()
                ),
            )
            with alternative():
                add(
                    paid,
                    inference(PaidAgeSupplements)(
                        household=right.household, amount=Money.zero
                    ),
                )
        return query


# %% the flat allowance


@dataclass
class FlatAllowanceRightProvision(ChildProvision[FlatAllowanceRight]):
    """
    `L521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000029963006>`__: with the children of `D521-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680324>`__ in the household's charge, a child who
    gave a right to family allowances and meets every condition but its age gives a
    right to the flat allowance within a year of the age limit, and, as Catala reads
    it, after. `L755-12 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000029962999>`__ excepts a single entitled child overseas.
    """

    @classproperty
    def minimum_number_of_children(cls) -> int:
        """III of `D521-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680324>`__: the children in the household's charge from which the allowance is paid, three."""
        return 3

    @classproperty
    def days_before_age_limit(cls) -> int:
        """
        The days before the birthday at the age limit within which the allowance is
        paid, 365.
        """
        return 365

    def query(self) -> Query:
        conditions = variable(
            ConditionsBesidesAge,
            domain=ConditionsBesidesAgeProvision(household=self.household).conclusions,
        )
        children = variable(
            EntitledChildren,
            domain=EntitledChildrenProvision(household=self.household).conclusions,
        )
        overseas = variable(
            OverseasRegime,
            domain=OverseasRegimeProvision(household=self.household).conclusions,
        )
        household = children.household
        child = conditions.child
        right = deduced_variable(FlatAllowanceRight)
        query = an(
            entity(right).where(
                overseas.holds == True, children.number_of_children == 1
            )
        )
        with query:
            add(right, inference(FlatAllowanceRight)(child=child, holds=False))
            # The child's own conditions come first: the else is lost otherwise
            # (cram2/cognitive_robot_abstract_machine#948).
            with alternative(
                conditions.holds == True,
                child.has_opened_family_allowance == True,
                Household.days_until(
                    household,
                    Child.birthday(child, FamilyBenefitEntitlementProvision.age_limit),
                )
                < self.days_before_age_limit,
                household.number_of_children >= self.minimum_number_of_children,
            ):
                add(right, inference(FlatAllowanceRight)(child=child, holds=True))
            with alternative():
                add(right, inference(FlatAllowanceRight)(child=child, holds=False))
        return query


@dataclass
class PaidFlatAllowanceProvision(FamilyBenefitsProvision[PaidFlatAllowance]):
    """
    `D521-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680324>`__: the rate of the household's bracket for every child giving a right
    to the flat allowance.
    """

    def query(self) -> Query:
        right = variable(
            FlatAllowanceRight,
            domain=FlatAllowanceRightProvision(household=self.household).conclusions,
        )
        base = variable(
            MonthlyBaseAmount,
            domain=MonthlyBaseProvision(household=self.household).conclusions,
        )
        bracket = variable(
            HouseholdBracket,
            domain=HouseholdBracketProvision(household=self.household).conclusions,
        )
        children = an(entity(right.child).where(right.holds == True)).tolist()
        return an(
            entity(
                inference(PaidFlatAllowance)(
                    household=base.household,
                    amount=(base.amount * bracket.bracket.value.flat_allowance)
                    * len(children),
                )
            )
        )


# %% degressive supplements


@dataclass
class DegressiveSupplementRightProvision(
    FamilyBenefitsProvision[DegressiveSupplementRight]
):
    """
    `L521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000029963006>`__: a household has a right to the degressive supplements.
    `L755-12 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000029962999>`__ excepts a household with a single entitled child overseas.
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
        right = deduced_variable(DegressiveSupplementRight)
        query = an(
            entity(right).where(
                overseas.holds == True, children.number_of_children == 1
            )
        )
        with query:
            add(
                right,
                inference(DegressiveSupplementRight)(
                    household=children.household, holds=False
                ),
            )
            with alternative():
                add(
                    right,
                    inference(DegressiveSupplementRight)(
                        household=children.household, holds=True
                    ),
                )
        return query


@dataclass
class SupplementedAllowanceProvision(FamilyBenefitsProvision[SupplementedAllowance]):
    """
    II of `D521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680318>`__: the monthly allowance its degressive supplement makes up for,
    the base allowance and the age supplements paid.
    """

    def query(self) -> Query:
        base = variable(
            PaidBaseAllowance,
            domain=PaidBaseAllowanceProvision(household=self.household).conclusions,
        )
        supplements = variable(
            PaidAgeSupplements,
            domain=PaidAgeSupplementsProvision(household=self.household).conclusions,
        )
        return an(
            entity(
                inference(SupplementedAllowance)(
                    household=base.household, amount=base.amount + supplements.amount
                )
            )
        )


@dataclass
class DegressiveSupplementProvision(FamilyBenefitsProvision[ConclusionType]):
    """
    A degressive supplement: where a household's resources exceed a ceiling by less than
    twelve times a monthly allowance, a twelfth of what the ceiling plus those twelve
    allowances exceed the resources by; none before the modulation by resources began.
    """

    @classproperty
    def months(cls) -> int:
        """
        The months of a year, twelve.
        """
        return 12

    def supplement(
        self,
        allowance: HouseholdAmount,
        ceilings: ApplicableResourceCeilings,
        *conditions: object,
    ) -> Query:
        """
        :param allowance: A variable over the monthly allowance supplemented.
        :param ceilings: A variable over the household's ceilings.
        :param conditions: The conditions of the right to the supplement.
        :return: The query concluding the supplement, nothing where no ceiling is
            exceeded by less than twelve allowances or a condition fails.
        """
        conclusion_type = self.get_type_of_generic_parameter(parameter=ConclusionType)
        household = ceilings.household
        yearly = allowance.amount * self.months
        supplement = deduced_variable(conclusion_type)
        modulated = (
            household.assessment_date
            >= HouseholdBracketProvision.first_day_of_modulation
        )
        query = an(
            entity(supplement).where(
                *conditions,
                modulated,
                household.resources > ceilings.first_ceiling,
                household.resources <= ceilings.first_ceiling + yearly,
            )
        )
        with query:
            add(
                supplement,
                inference(conclusion_type)(
                    household=household,
                    amount=(ceilings.first_ceiling + yearly - household.resources)
                    * Fraction(1, self.months),
                ),
            )
            with alternative(
                *conditions,
                modulated,
                household.resources > ceilings.second_ceiling,
                household.resources <= ceilings.second_ceiling + yearly,
            ):
                add(
                    supplement,
                    inference(conclusion_type)(
                        household=household,
                        amount=(ceilings.second_ceiling + yearly - household.resources)
                        * Fraction(1, self.months),
                    ),
                )
            with alternative():
                add(
                    supplement,
                    inference(conclusion_type)(household=household, amount=Money.zero),
                )
        return query


@dataclass
class AllowanceDegressiveSupplementProvision(
    DegressiveSupplementProvision[AllowanceDegressiveSupplement]
):
    """
    II of `D521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680318>`__: the degressive supplement to the base allowance and the age
    supplements paid, where the household has a right to it.
    """

    def query(self) -> Query:
        right = variable(
            DegressiveSupplementRight,
            domain=DegressiveSupplementRightProvision(
                household=self.household
            ).conclusions,
        )
        allowance = variable(
            SupplementedAllowance,
            domain=SupplementedAllowanceProvision(household=self.household).conclusions,
        )
        ceilings = variable(
            ApplicableResourceCeilings,
            domain=ResourceCeilingsProvision(household=self.household).conclusions,
        )
        return self.supplement(allowance, ceilings, right.holds == True)


@dataclass
class FlatAllowanceDegressiveSupplementProvision(
    DegressiveSupplementProvision[FlatAllowanceDegressiveSupplement]
):
    """
    II of `D521-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680324>`__: the degressive supplement to the flat allowance.

    .. note:: Catala pays it without the right of :class:`DegressiveSupplementRightProvision`,
        which it checks for the supplement of II of `D521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000030680318>`__ only.
    """

    def query(self) -> Query:
        allowance = variable(
            PaidFlatAllowance,
            domain=PaidFlatAllowanceProvision(household=self.household).conclusions,
        )
        ceilings = variable(
            ApplicableResourceCeilings,
            domain=ResourceCeilingsProvision(household=self.household).conclusions,
        )
        return self.supplement(allowance, ceilings)


# %% the amount paid


@dataclass
class FamilyAllowanceProvision(FamilyBenefitsProvision[FamilyAllowance]):
    """
    The family allowances paid for the month: the base allowance, the age supplements,
    the flat allowance and both degressive supplements, where the household has a right
    to family allowances; nothing otherwise.
    """

    def query(self) -> Query:
        right = variable(
            BaseAllowanceRight,
            domain=BaseAllowanceRightProvision(household=self.household).conclusions,
        )
        base = variable(
            PaidBaseAllowance,
            domain=PaidBaseAllowanceProvision(household=self.household).conclusions,
        )
        supplements = variable(
            PaidAgeSupplements,
            domain=PaidAgeSupplementsProvision(household=self.household).conclusions,
        )
        flat = variable(
            PaidFlatAllowance,
            domain=PaidFlatAllowanceProvision(household=self.household).conclusions,
        )
        allowance_supplement = variable(
            AllowanceDegressiveSupplement,
            domain=AllowanceDegressiveSupplementProvision(
                household=self.household
            ).conclusions,
        )
        flat_supplement = variable(
            FlatAllowanceDegressiveSupplement,
            domain=FlatAllowanceDegressiveSupplementProvision(
                household=self.household
            ).conclusions,
        )
        allowance = deduced_variable(FamilyAllowance)
        query = an(entity(allowance).where(right.holds == True))
        with query:
            add(
                allowance,
                inference(FamilyAllowance)(
                    household=right.household,
                    amount=base.amount
                    + supplements.amount
                    + flat.amount
                    + allowance_supplement.amount
                    + flat_supplement.amount,
                ),
            )
            with alternative():
                add(
                    allowance,
                    inference(FamilyAllowance)(
                        household=right.household, amount=Money.zero
                    ),
                )
        return query
