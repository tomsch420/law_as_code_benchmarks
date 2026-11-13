"""
The right a child gives to family benefits (*prestations familiales*): the amounts in
force, the overseas regime of
`L751-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031323778>`__, the pay ceiling of `R512-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006750602>`__,
compulsory schooling and the conditions of `L512-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000041979743>`__.
"""

from __future__ import annotations

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
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.catala.amounts import (
    HourlyMinimumWage,
    MinimumWages,
    MonthlyBase,
    MonthlyBases,
)
from law_as_code_benchmarks.catala.conclusions import (
    ConditionsBesidesAge,
    EntitledChildren,
    FamilyBenefitEntitlement,
    HourlyMinimumWageAmount,
    MonthlyBaseAmount,
    OverseasRegime,
    PayCeiling,
    SchoolingStageOfChild,
)
from law_as_code_benchmarks.catala.domain import (
    Child,
    DatedValue,
    Household,
    SchoolingStage,
    Territory,
)
from law_as_code_benchmarks.catala.provision import Provision

# %% amounts in force


@dataclass
class MonthlyBaseProvision(Provision[MonthlyBaseAmount]):
    """
    `L551-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031688371>`__: the monthly base of family allowances in force on the
    household's assessment date; none before April 1, 2019, which Catala leaves out.
    """

    def query(self) -> Query:
        household = variable(Household, domain=[self.household])
        base = variable(MonthlyBase, domain=[member.value for member in MonthlyBases])
        return an(
            entity(
                inference(MonthlyBaseAmount)(household=household, amount=base.amount)
            ).where(DatedValue.is_in_force(base, household.assessment_date))
        )


@dataclass
class MinimumWageProvision(Provision[HourlyMinimumWageAmount]):
    """
    The gross hourly minimum wage in force where the household lives on its assessment
    date; none before 2019, which Catala leaves out.
    """

    def query(self) -> Query:
        household = variable(Household, domain=[self.household])
        wage = variable(
            HourlyMinimumWage, domain=[member.value for member in MinimumWages]
        )
        return an(
            entity(
                inference(HourlyMinimumWageAmount)(
                    household=household, amount=wage.amount
                )
            ).where(
                DatedValue.is_in_force(wage, household.assessment_date),
                in_(household.residence, wage.territories),
            )
        )


# %% the overseas regime and the pay ceiling


@dataclass
class OverseasRegimeProvision(Provision[OverseasRegime]):
    """
    `L751-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031323778>`__: the special provisions apply in Guadeloupe, French Guiana,
    Martinique, La Réunion, Saint-Barthélemy and Saint-Martin, not in Mayotte.
    """

    @classproperty
    def territories(cls) -> frozenset[Territory]:
        """
        The territories the special provisions apply in.
        """
        return frozenset(
            {
                Territory.GUADELOUPE,
                Territory.FRENCH_GUIANA,
                Territory.MARTINIQUE,
                Territory.REUNION,
                Territory.SAINT_BARTHELEMY,
                Territory.SAINT_MARTIN,
            }
        )

    def query(self) -> Query:
        household = variable(Household, domain=[self.household])
        regime = deduced_variable(OverseasRegime)
        query = an(entity(regime).where(in_(household.residence, self.territories)))
        with query:
            add(regime, inference(OverseasRegime)(household=household, holds=True))
            with alternative():
                add(regime, inference(OverseasRegime)(household=household, holds=False))
        return query


@dataclass
class PayCeilingProvision(Provision[PayCeiling]):
    """
    `R512-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006750602>`__: 55 % of the gross hourly minimum wage times 169. `R755-0-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006752633>`__
    sets the same in the overseas departments, the minimum wage in force there being
    the one :class:`MinimumWageProvision` finds.
    """

    @classproperty
    def share_of_minimum_wage(cls) -> Fraction:
        """
        The share of the hourly minimum wage, 55 %.
        """
        return Fraction(55, 100)

    @classproperty
    def hours(cls) -> Fraction:
        """
        The hours the share is multiplied by, 169.
        """
        return Fraction(169)

    def query(self) -> Query:
        wage = variable(
            HourlyMinimumWageAmount,
            domain=MinimumWageProvision(household=self.household).conclusions,
        )
        return an(
            entity(
                inference(PayCeiling)(
                    household=wage.household,
                    amount=(wage.amount * self.share_of_minimum_wage) * self.hours,
                )
            )
        )


# %% compulsory schooling


@dataclass
class SchoolingStageProvision(Provision[SchoolingStageOfChild]):
    """
    `L131-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000038901859>`__ of the Code de l'éducation: schooling is compulsory from age 3
    to age 16. A child is before it until the day after their third birthday and during
    it until the day after their sixteenth, as Catala reads the article; where the case
    states the stage, the stated one holds.
    """

    @classproperty
    def starting_age(cls) -> int:
        """
        The age compulsory schooling starts at.
        """
        return 3

    @classproperty
    def ending_age(cls) -> int:
        """
        The age compulsory schooling ends at.
        """
        return 16

    def query(self) -> Query:
        household = variable(Household, domain=[self.household])
        child = variable(Child, domain=self.household.children)
        stage = deduced_variable(SchoolingStageOfChild)
        query = an(entity(stage).where(child.stated_schooling_stage != None))
        with query:
            add(
                stage,
                inference(SchoolingStageOfChild)(
                    child=child, stage=child.stated_schooling_stage
                ),
            )
            with alternative(
                Child.birthday(child, self.starting_age) >= household.assessment_date
            ):
                add(
                    stage,
                    inference(SchoolingStageOfChild)(
                        child=child, stage=SchoolingStage.BEFORE
                    ),
                )
            with alternative(
                Child.birthday(child, self.ending_age) >= household.assessment_date
            ):
                add(
                    stage,
                    inference(SchoolingStageOfChild)(
                        child=child, stage=SchoolingStage.DURING
                    ),
                )
            with alternative():
                add(
                    stage,
                    inference(SchoolingStageOfChild)(
                        child=child, stage=SchoolingStage.AFTER
                    ),
                )
        return query


# %% the right to family benefits


@dataclass
class FamilyBenefitEntitlementProvision(Provision[FamilyBenefitEntitlement]):
    """
    `L512-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000041979743>`__: a child gives a right to family benefits until compulsory
    schooling ends (1°), and after it, up to the age limit of `R512-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006750602>`__, while their
    pay does not exceed the pay ceiling (2°). `L821-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000038814972>`__ of the Code de la construction
    et de l'habitation excepts a child receiving housing aid in their own name.
    """

    @classproperty
    def age_limit(cls) -> int:
        """`R512-2 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006750602>`__: the age limit of 2°, 20 years."""
        return 20

    def query(self) -> Query:
        household = variable(Household, domain=[self.household])
        stage = variable(
            SchoolingStageOfChild,
            domain=SchoolingStageProvision(household=self.household).conclusions,
        )
        ceiling = variable(
            PayCeiling, domain=PayCeilingProvision(household=self.household).conclusions
        )
        entitlement = deduced_variable(FamilyBenefitEntitlement)
        query = an(
            entity(entitlement).where(
                in_(stage.stage, {SchoolingStage.BEFORE, SchoolingStage.DURING})
            )
        )
        with query:
            add(
                entitlement,
                inference(FamilyBenefitEntitlement)(child=stage.child, holds=True),
            )
            with alternative(
                stage.stage == SchoolingStage.AFTER,
                stage.child.monthly_pay <= ceiling.amount,
                Child.birthday(stage.child, self.age_limit) > household.assessment_date,
            ):
                add(
                    entitlement,
                    inference(FamilyBenefitEntitlement)(child=stage.child, holds=True),
                )
                with refinement(stage.child.receives_personal_housing_aid == True):
                    add(
                        entitlement,
                        inference(FamilyBenefitEntitlement)(
                            child=stage.child, holds=False
                        ),
                    )
            with alternative():
                add(
                    entitlement,
                    inference(FamilyBenefitEntitlement)(child=stage.child, holds=False),
                )
            with refinement(stage.child.receives_personal_housing_aid == True):
                add(
                    entitlement,
                    inference(FamilyBenefitEntitlement)(child=stage.child, holds=False),
                )
        return query


@dataclass
class ConditionsBesidesAgeProvision(Provision[ConditionsBesidesAge]):
    """
    `L512-3 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000041979743>`__: a child, at whatever stage of compulsory schooling, meets the
    conditions of the right to family benefits but its age where their pay does not
    exceed the pay ceiling.
    """

    def query(self) -> Query:
        child = variable(Child, domain=self.household.children)
        ceiling = variable(
            PayCeiling, domain=PayCeilingProvision(household=self.household).conclusions
        )
        conditions = deduced_variable(ConditionsBesidesAge)
        query = an(entity(conditions).where(child.monthly_pay <= ceiling.amount))
        with query:
            add(conditions, inference(ConditionsBesidesAge)(child=child, holds=True))
            with alternative():
                add(
                    conditions,
                    inference(ConditionsBesidesAge)(child=child, holds=False),
                )
        return query


@dataclass
class EntitledChildrenProvision(Provision[EntitledChildren]):
    """
    The children in the household's charge who give a right to family benefits, the
    children `L521-1 <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000029963006>`__ and the provisions after it count.
    """

    def query(self) -> Query:
        household = variable(Household, domain=[self.household])
        entitlement = variable(
            FamilyBenefitEntitlement,
            domain=FamilyBenefitEntitlementProvision(
                household=self.household
            ).conclusions,
        )
        children = an(entity(entitlement.child).where(entitlement.holds == True))
        return an(
            entity(
                inference(EntitledChildren)(
                    household=household, children=children.tolist()
                )
            )
        )
