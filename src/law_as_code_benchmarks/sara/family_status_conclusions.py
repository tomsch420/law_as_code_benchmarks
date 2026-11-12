"""
What §§ `7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__, `152 <https://www.law.cornell.edu/uscode/text/26/152>`__, `151 <https://www.law.cornell.edu/uscode/text/26/151>`__, `2 <https://www.law.cornell.edu/uscode/text/26/2>`__ and `68(b) <https://www.law.cornell.edu/uscode/text/26/68#b>`__ of the Internal Revenue Code conclude: marital status,
dependents, personal exemptions, surviving spouses, heads of household and the
applicable amount, and the kinship and gross income SARA's program defines them by.
"""

from __future__ import annotations

import datetime
from abc import ABC
from dataclasses import dataclass, field

from krrood.entity_query_language.predicate import symbolic_function
from krrood.symbol_graph.symbol_graph import Symbol

from law_as_code_benchmarks.sara.domain import (
    CalendarYear,
    Household,
    JointReturn,
    LegalSeparation,
    Marriage,
    Party,
    Period,
)
from law_as_code_benchmarks.sara.prolog_term import Term
from law_as_code_benchmarks.sara.provision import SaraConclusion

# %% kinship


@dataclass(eq=False)
class Relationship(SaraConclusion):
    """
    That one party bears a relation of kinship to another, for the days it lasts.
    """

    relative: Party
    """
    The party bearing the relation.
    """

    person: Party
    """
    The party it is borne to.
    """

    period: Period = field(default_factory=Period)
    """
    The days it lasts.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.relative.name,
            self.person.name,
            self.day_text(self.period.start),
            self.day_text(self.period.end),
        )


@dataclass(eq=False)
class ChildRelationship(Relationship):
    """
    That the relative is a child of the person.
    """


@dataclass(eq=False)
class DescendantRelationship(Relationship):
    """
    That the relative is a descendant of the person, for the days of the last
    generation's relation.
    """


@dataclass(eq=False)
class SiblingRelationship(Relationship):
    """
    That the relative is a brother or sister of the person.
    """


@dataclass(eq=False)
class StepsiblingRelationship(Relationship):
    """
    That a parent of the relative married a parent of the person.
    """


@dataclass(eq=False)
class SiblingInLawRelationship(Relationship):
    """
    That one of the two married a brother or sister of the other.
    """


@dataclass(eq=False)
class ChildInLawRelationship(Relationship):
    """
    That the relative married a child of the person.
    """


@dataclass(eq=False)
class ParentInLawRelationship(Relationship):
    """
    That the relative married a parent of the person, as SARA's program defines a
    parent-in-law.
    """


@dataclass(eq=False)
class StepparentRelationship(Relationship):
    """
    That the relative married a parent of the person, the marriage's start stated.
    """


# %% gross income


@dataclass(eq=False)
class IndividualGrossIncome(Symbol):
    """
    The income a party receives in a calendar year, their spouse's aside.
    """

    person: Party
    """
    Who receives it.
    """

    year: CalendarYear
    """
    The calendar year.
    """

    amount: float
    """
    How much is received.
    """


@dataclass(eq=False)
class GrossIncome(SaraConclusion):
    """
    A party's gross income for a calendar year, their spouse's included where they make
    a joint return.
    """

    person: Party
    """
    Whose gross income it is.
    """

    year: int
    """
    The calendar year.
    """

    amount: float
    """
    The gross income.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.person.name, self.year, self.amount


# %% marital status


@dataclass(eq=False)
class MaritalConclusion(SaraConclusion, ABC):
    """
    A conclusion about a party and their spouse in a marriage, for a calendar year.
    """

    person: Party
    """
    The party.
    """

    spouse: Party
    """
    Their spouse.
    """

    marriage: Marriage
    """
    The marriage.
    """

    year: int
    """
    The calendar year.
    """


@dataclass(eq=False)
class MarriedIndividual(MaritalConclusion):
    """
    `§ 7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__: that the party is married for the year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.person.name, self.spouse.name, self.marriage.name, self.year


@dataclass(eq=False)
class MarriedUnderGeneralRule(MarriedIndividual):
    """
    `§ 7703(a) <https://www.law.cornell.edu/uscode/text/26/7703#a>`__: that the party is married for the year, individuals living apart not set aside.
    """


@dataclass(eq=False)
class MarriedAtDetermination(MaritalConclusion):
    """
    `§ 7703(a)(1) <https://www.law.cornell.edu/uscode/text/26/7703#a_1>`__: that the party is married at the close of the year, or at their spouse's death in it.
    """

    spouse_death_day: datetime.date | None = None
    """
    The day the spouse died in the year; None where they did not.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.person.name,
            self.spouse.name,
            self.marriage.name,
            self.day_text(self.spouse_death_day),
            self.year,
        )


@dataclass(eq=False)
class LegallySeparatedIndividual(MaritalConclusion):
    """
    `§ 7703(a)(2) <https://www.law.cornell.edu/uscode/text/26/7703#a_2>`__: that the party is legally separated from their spouse by the close of the year.
    """

    separation: LegalSeparation | None = None
    """
    The separation.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.person.name,
            self.spouse.name,
            self.marriage.name,
            self.separation.name,
            self.year,
        )


@dataclass(eq=False)
class IndividualLivingApart(SaraConclusion):
    """
    `§ 7703(b) <https://www.law.cornell.edu/uscode/text/26/7703#b>`__: that a married party living apart from their spouse is not considered married for the year.
    """

    person: Party
    """
    The party.
    """

    spouse: Party
    """
    Their spouse.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.person.name, self.spouse.name, self.year


@dataclass(eq=False)
class HouseholdConclusion(SaraConclusion, ABC):
    """
    A conclusion about a party and a household, for a calendar year.
    """

    person: Party
    """
    The party.
    """

    household: Household
    """
    The household.
    """

    year: int
    """
    The calendar year.
    """


@dataclass(eq=False)
class HomeOfChild(HouseholdConclusion):
    """
    `§ 7703(b)(1) <https://www.law.cornell.edu/uscode/text/26/7703#b_1>`__: that a party filing separately keeps as their home the household of a qualifying child for half the year.
    """

    child: Party | None = None
    """
    The child.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.person.name, self.household.name, self.child.name, self.year


@dataclass(eq=False)
class HouseholdMaintenance(HouseholdConclusion):
    """
    `§ 7703(b)(2) <https://www.law.cornell.edu/uscode/text/26/7703#b_2>`__: that the party furnishes at least half the cost of maintaining the household in the year.
    """

    cost: float = 0
    """
    The cost of maintaining the household in the year, whoever furnishes it.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.person.name, self.household.name, self.cost, self.year


@dataclass(eq=False)
class MaintenanceCost(Symbol):
    """
    What someone pays in a calendar year for maintaining a household.
    """

    household: Household
    """
    The household.
    """

    year: int
    """
    The calendar year.
    """

    amount: float
    """
    How much is paid.
    """

    payer: Party | None = None
    """
    Who pays; None for the cost whoever pays it.
    """

    @symbolic_function
    def is_at_least_half_of(self, cost: MaintenanceCost) -> bool:
        """:return: Whether the amount is at least half of *cost*'s, which is more than nothing."""
        return cost.amount > 0 and 2 * self.amount >= cost.amount


@dataclass(eq=False)
class AbsentSpouse(HouseholdConclusion):
    """
    `§ 7703(b)(3) <https://www.law.cornell.edu/uscode/text/26/7703#b_3>`__: that the party's spouse is no member of the household in the last 6 months of the year.
    """

    spouse: Party | None = None
    """
    The spouse.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.person.name, self.spouse.name, self.household.name, self.year


# %% dependents


@dataclass(eq=False)
class DependencyConclusion(SaraConclusion, ABC):
    """
    A conclusion about an individual with respect to a taxpayer.
    """

    individual: Party
    """
    The individual.
    """

    taxpayer: Party
    """
    The taxpayer.
    """


@dataclass(eq=False)
class AnnualDependency(DependencyConclusion):
    """
    A conclusion about an individual with respect to a taxpayer for a calendar year.
    """

    year: int = 0
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.individual.name, self.taxpayer.name, self.year


@dataclass(eq=False)
class Dependent(AnnualDependency):
    """
    `§ 152 <https://www.law.cornell.edu/uscode/text/26/152>`__: that the individual is a dependent of the taxpayer.
    """


@dataclass(eq=False)
class DependentCandidate(AnnualDependency):
    """
    That the individual is a dependent of the taxpayer under `§ 152(a) <https://www.law.cornell.edu/uscode/text/26/152#a>`__ and not married filing jointly, `§ 152(b)(1) <https://www.law.cornell.edu/uscode/text/26/152#b_1>`__ aside.
    """


@dataclass(eq=False)
class QualifyingChildDependent(AnnualDependency):
    """
    `§ 152(a)(1) <https://www.law.cornell.edu/uscode/text/26/152#a_1>`__: that the individual is a dependent of the taxpayer as a qualifying child.
    """


@dataclass(eq=False)
class DependencyException(AnnualDependency):
    """
    `§ 152(b) <https://www.law.cornell.edu/uscode/text/26/152#b>`__: that the taxpayer can have no dependents, or the individual can be no dependent.
    """


@dataclass(eq=False)
class QualifyingChild(AnnualDependency):
    """
    `§ 152(c) <https://www.law.cornell.edu/uscode/text/26/152#c>`__: that the individual is a qualifying child of the taxpayer.
    """


@dataclass(eq=False)
class QualifyingChildUnderGeneralRule(AnnualDependency):
    """
    `§ 152(c)(1) <https://www.law.cornell.edu/uscode/text/26/152#c_1>`__: that the individual is a qualifying child of the taxpayer.
    """


@dataclass(eq=False)
class AgeRequirement(AnnualDependency):
    """
    `§ 152(c)(3) <https://www.law.cornell.edu/uscode/text/26/152#c_3>`__: that the individual is younger than the taxpayer and less than 25 years old.
    """


@dataclass(eq=False)
class AgeRequirementOfQualifyingChild(AnnualDependency):
    """
    `§ 152(c)(1)(C) <https://www.law.cornell.edu/uscode/text/26/152#c_1_C>`__: that the individual meets the age requirements of `§ 152(c)(3) <https://www.law.cornell.edu/uscode/text/26/152#c_3>`__.
    """


@dataclass(eq=False)
class DependentOfOtherTaxpayer(SaraConclusion):
    """
    `§ 152(b)(1) <https://www.law.cornell.edu/uscode/text/26/152#b_1>`__: that a taxpayer, being a dependent of another, is treated as having no dependents.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    other_taxpayer: Party
    """
    Whose dependent they are.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.other_taxpayer.name, self.year


@dataclass(eq=False)
class JointFiling(SaraConclusion):
    """
    `§ 152(b)(2) <https://www.law.cornell.edu/uscode/text/26/152#b_2>`__: that a married individual made a joint return with their spouse for the year.
    """

    individual: Party
    """
    The individual.
    """

    spouse: Party
    """
    Their spouse.
    """

    year: int
    """
    The calendar year.
    """

    joint_return: JointReturn | None = None
    """
    The joint return; None where the case states the conclusion without it.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.individual.name,
            None if self.joint_return is None else self.joint_return.name,
            self.spouse.name,
            self.year,
        )


@dataclass(eq=False)
class NoJointReturn(SaraConclusion):
    """
    `§ 152(c)(1)(E) <https://www.law.cornell.edu/uscode/text/26/152#c_1_E>`__: that the individual made no joint return with a spouse for the year.
    """

    individual: Party
    """
    The individual.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.individual.name, None, self.year


@dataclass(eq=False)
class IndividualYearConclusion(SaraConclusion, ABC):
    """
    A conclusion about an individual for a calendar year.
    """

    individual: Party
    """
    The individual.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.individual.name, self.year


@dataclass(eq=False)
class NoGrossIncome(IndividualYearConclusion):
    """
    `§ 152(d)(1)(B) <https://www.law.cornell.edu/uscode/text/26/152#d_1_B>`__: that the individual has no gross income for the year.
    """


@dataclass(eq=False)
class NoQualifyingChild(IndividualYearConclusion):
    """
    `§ 152(d)(1)(D) <https://www.law.cornell.edu/uscode/text/26/152#d_1_D>`__: that the individual is no qualifying child of any taxpayer for the year.
    """


@dataclass(eq=False)
class RelationshipToTaxpayer(DependencyConclusion):
    """
    That the individual bears a relationship to the taxpayer, for the days it lasts.
    """

    period: Period = field(default_factory=Period)
    """
    The days the relationship lasts.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.individual.name,
            self.taxpayer.name,
            self.day_text(self.period.start),
            self.day_text(self.period.end),
        )


@dataclass(eq=False)
class QualifyingChildRelationship(RelationshipToTaxpayer):
    """
    `§ 152(c)(2) <https://www.law.cornell.edu/uscode/text/26/152#c_2>`__: a relationship a qualifying child bears.
    """


@dataclass(eq=False)
class QualifyingChildRelationshipUntilDeath(RelationshipToTaxpayer):
    """
    `§ 152(c)(1)(A) <https://www.law.cornell.edu/uscode/text/26/152#c_1_A>`__: a relationship of `§ 152(c)(2) <https://www.law.cornell.edu/uscode/text/26/152#c_2>`__, ending at the death of either party.
    """


@dataclass(eq=False)
class AncestorRelationship(RelationshipToTaxpayer):
    """
    `§ 152(d)(2)(C) <https://www.law.cornell.edu/uscode/text/26/152#d_2_C>`__: that the individual is the father or mother of the taxpayer, or an ancestor of either.
    """


@dataclass(eq=False)
class ChildOrDescendantRelationship(RelationshipToTaxpayer):
    """
    `§ 152(d)(2)(A) <https://www.law.cornell.edu/uscode/text/26/152#d_2_A>`__: that the individual is a child of the taxpayer or a descendant of a child.
    """


@dataclass(eq=False)
class SiblingOrStepsiblingRelationship(RelationshipToTaxpayer):
    """
    `§ 152(d)(2)(B) <https://www.law.cornell.edu/uscode/text/26/152#d_2_B>`__: that the individual is a brother, sister, stepbrother or stepsister of the taxpayer.
    """


@dataclass(eq=False)
class StepparentOfTaxpayerRelationship(RelationshipToTaxpayer):
    """
    `§ 152(d)(2)(D) <https://www.law.cornell.edu/uscode/text/26/152#d_2_D>`__: that the individual is a stepfather or stepmother of the taxpayer.
    """


@dataclass(eq=False)
class InLawRelationship(RelationshipToTaxpayer):
    """
    `§ 152(d)(2)(G) <https://www.law.cornell.edu/uscode/text/26/152#d_2_G>`__: that the individual is a son-, daughter-, father-, mother-, brother- or sister-in-law of the taxpayer.
    """


@dataclass(eq=False)
class RelationshipThroughRelative(RelationshipToTaxpayer):
    """
    That the individual bears a relationship to the taxpayer through a relative of
    either.
    """

    relative: Party | None = None
    """
    The relative.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`RelationshipToTaxpayer.prolog_arguments` by the relative, after
        the taxpayer.
        """
        return (
            self.individual.name,
            self.taxpayer.name,
            self.relative.name,
            self.day_text(self.period.start),
            self.day_text(self.period.end),
        )


@dataclass(eq=False)
class ChildOrDescendantOfChildRelationship(RelationshipThroughRelative):
    """
    `§ 152(c)(2)(A) <https://www.law.cornell.edu/uscode/text/26/152#c_2_A>`__: that the individual is a child of the taxpayer, the relative, or a descendant of the relative.
    """


@dataclass(eq=False)
class SiblingOrDescendantOfSiblingRelationship(RelationshipThroughRelative):
    """
    `§ 152(c)(2)(B) <https://www.law.cornell.edu/uscode/text/26/152#c_2_B>`__: that the individual is a brother, sister, stepbrother or stepsister of the taxpayer, the relative, or a descendant of the relative.
    """


@dataclass(eq=False)
class NephewOrNieceRelationship(RelationshipThroughRelative):
    """
    `§ 152(d)(2)(E) <https://www.law.cornell.edu/uscode/text/26/152#d_2_E>`__: that the individual is a son or daughter of the relative, a brother or sister of the taxpayer.
    """


@dataclass(eq=False)
class UncleOrAuntRelationship(RelationshipThroughRelative):
    """
    `§ 152(d)(2)(F) <https://www.law.cornell.edu/uscode/text/26/152#d_2_F>`__: that the individual is a brother or sister of the relative, a parent of the taxpayer.
    """


@dataclass(eq=False)
class AnnualRelationship(RelationshipToTaxpayer):
    """
    That the individual bears a relationship to the taxpayer for a calendar year, for
    the days it lasts.
    """

    year: int = 0
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`RelationshipToTaxpayer.prolog_arguments` by the year, after the
        taxpayer.
        """
        return (
            self.individual.name,
            self.taxpayer.name,
            self.year,
            self.day_text(self.period.start),
            self.day_text(self.period.end),
        )


@dataclass(eq=False)
class DependentUnderDefinition(AnnualRelationship):
    """
    `§ 152(a) <https://www.law.cornell.edu/uscode/text/26/152#a>`__: that the individual is a qualifying child or a qualifying relative of the taxpayer.
    """


@dataclass(eq=False)
class QualifyingRelativeDependent(AnnualRelationship):
    """
    `§ 152(a)(2) <https://www.law.cornell.edu/uscode/text/26/152#a_2>`__: that the individual is a dependent of the taxpayer as a qualifying relative.
    """


@dataclass(eq=False)
class QualifyingRelative(AnnualRelationship):
    """
    `§ 152(d) <https://www.law.cornell.edu/uscode/text/26/152#d>`__: that the individual is a qualifying relative of the taxpayer.
    """


@dataclass(eq=False)
class QualifyingRelativeUnderGeneralRule(AnnualRelationship):
    """
    `§ 152(d)(1) <https://www.law.cornell.edu/uscode/text/26/152#d_1>`__: that the individual is a qualifying relative of the taxpayer.
    """


@dataclass(eq=False)
class QualifyingRelativeRelationshipUntilDeath(AnnualRelationship):
    """
    `§ 152(d)(1)(A) <https://www.law.cornell.edu/uscode/text/26/152#d_1_A>`__: a relationship of `§ 152(d)(2) <https://www.law.cornell.edu/uscode/text/26/152#d_2>`__, ending at the death of either party.
    """


@dataclass(eq=False)
class QualifyingRelativeRelationship(AnnualRelationship):
    """
    `§ 152(d)(2) <https://www.law.cornell.edu/uscode/text/26/152#d_2>`__: a relationship a qualifying relative bears.
    """


@dataclass(eq=False)
class HouseholdMemberRelationship(AnnualRelationship):
    """
    `§ 152(d)(2)(H) <https://www.law.cornell.edu/uscode/text/26/152#d_2_H>`__: that the individual, never the taxpayer's spouse in the year, shares the taxpayer's home all year.
    """

    household: Household | None = None
    """
    The home they share.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`AnnualRelationship.prolog_arguments` by the household, after the
        year.
        """
        return (
            self.individual.name,
            self.taxpayer.name,
            self.year,
            None if self.household is None else self.household.name,
            self.day_text(self.period.start),
            self.day_text(self.period.end),
        )


@dataclass(eq=False)
class SharedAbode(RelationshipToTaxpayer):
    """
    `§ 152(c)(1)(B) <https://www.law.cornell.edu/uscode/text/26/152#c_1_B>`__: that the individual shares the taxpayer's principal place of abode for over half the year, within the days of their relationship.
    """

    household: Household | None = None
    """
    The abode.
    """

    year: int = 0
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Orders the arguments as `§ 152(c)(1)(B) <https://www.law.cornell.edu/uscode/text/26/152#c_1_B>`__ does: the abode after the individual, the year last.
        """
        return (
            self.individual.name,
            self.household.name,
            self.taxpayer.name,
            self.day_text(self.period.start),
            self.day_text(self.period.end),
            self.year,
        )


# %% personal exemptions


@dataclass(eq=False)
class ExemptionForDependent(AnnualDependency):
    """
    `§ 151(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__: that the taxpayer is allowed an exemption for the individual, their dependent.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Orders the arguments as `§ 151(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__ does, the taxpayer first.
        """
        return self.taxpayer.name, self.individual.name, self.year


@dataclass(eq=False)
class ExemptionForSpouse(AnnualDependency):
    """
    `§ 151(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__: that the taxpayer is allowed an exemption for the individual, their spouse.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Orders the arguments as `§ 151(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__ does, the taxpayer first.
        """
        return self.taxpayer.name, self.individual.name, self.year


@dataclass(eq=False)
class DependentExemptionAmount(SaraConclusion):
    """
    `§ 151(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__: the exemption amount the taxpayer deducts for a dependent.
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

    individual: Party | None = None
    """
    The dependent; None where the case states the conclusion without them.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.taxpayer.name,
            None if self.individual is None else self.individual.name,
            self.amount,
            self.year,
        )


@dataclass(eq=False)
class ExemptionAmount(SaraConclusion):
    """
    `§ 151(d) <https://www.law.cornell.edu/uscode/text/26/151#d>`__: the exemption amount of a taxpayer for a calendar year.
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

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.amount, self.year


@dataclass(eq=False)
class GeneralExemptionAmount(SaraConclusion):
    """
    `§ 151(d)(1) <https://www.law.cornell.edu/uscode/text/26/151#d_1>`__: the exemption amount, except as otherwise provided.
    """

    amount: float
    """
    The exemption amount.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (self.amount,)


@dataclass(eq=False)
class DisallowedExemptionAmount(SaraConclusion):
    """
    `§ 151(d)(2) <https://www.law.cornell.edu/uscode/text/26/151#d_2>`__: a zero exemption amount for an individual another taxpayer may deduct an exemption for.
    """

    individual: Party
    """
    The individual.
    """

    other_taxpayer: Party
    """
    The taxpayer allowed the exemption for them.
    """

    year: int
    """
    The calendar year.
    """

    amount: float = 0
    """
    The exemption amount.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.individual.name, self.other_taxpayer.name, self.amount, self.year


@dataclass(eq=False)
class SuspendedExemptionAmount(SaraConclusion):
    """
    `§ 151(d)(5) <https://www.law.cornell.edu/uscode/text/26/151#d_5>`__: a zero exemption amount for the years 2018 through 2025.
    """

    year: int
    """
    The calendar year.
    """

    amount: float = 0
    """
    The exemption amount.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.amount, self.year


@dataclass(eq=False)
class ApplicablePercentage(SaraConclusion):
    """
    `§ 151(d)(3)(B) <https://www.law.cornell.edu/uscode/text/26/151#d_3_B>`__: the percentage the exemption amount of a taxpayer is reduced by.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    year: int
    """
    The calendar year.
    """

    percentage: int
    """
    The applicable percentage.
    """

    gross_income: float
    """
    The taxpayer's gross income, which SARA takes for their adjusted gross income.
    """

    applicable_amount: float
    """
    The applicable amount of `§ 68(b) <https://www.law.cornell.edu/uscode/text/26/68#b>`__.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.percentage,
            self.taxpayer.name,
            self.gross_income,
            self.year,
            self.applicable_amount,
        )


@dataclass(eq=False)
class ReducedExemptionAmount(SaraConclusion):
    """
    `§ 151(d)(3)(A) <https://www.law.cornell.edu/uscode/text/26/151#d_3_A>`__: the exemption amount of a taxpayer whose gross income exceeds the applicable amount, reduced by the applicable percentage.
    """

    percentage: ApplicablePercentage
    """
    The applicable percentage, with the income and applicable amount it is computed
    from.
    """

    exemption_amount_before: float
    """
    The exemption amount before the reduction.
    """

    amount: float
    """
    The reduced exemption amount.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.percentage.taxpayer.name,
            self.percentage.gross_income,
            self.percentage.applicable_amount,
            self.percentage.percentage,
            self.exemption_amount_before,
            self.amount,
            self.percentage.year,
        )


@dataclass(eq=False)
class PhasedOutExemptionAmount(SaraConclusion):
    """
    `§ 151(d)(3) <https://www.law.cornell.edu/uscode/text/26/151#d_3>`__: the exemption amount of a taxpayer after the phaseout.
    """

    reduction: ReducedExemptionAmount
    """
    The reduction of `§ 151(d)(3)(A) <https://www.law.cornell.edu/uscode/text/26/151#d_3_A>`__.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.reduction.percentage.taxpayer.name,
            self.reduction.exemption_amount_before,
            self.reduction.amount,
            self.reduction.percentage.year,
        )


@dataclass(eq=False)
class ApplicableAmount(SaraConclusion):
    """
    `§ 68(b) <https://www.law.cornell.edu/uscode/text/26/68#b>`__: the applicable amount of a taxpayer for a calendar year.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    amount: float
    """
    The applicable amount.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.amount, self.year


@dataclass(eq=False)
class JointReturnOrSurvivorApplicableAmount(SaraConclusion):
    """
    `§ 68(b)(1)(A) <https://www.law.cornell.edu/uscode/text/26/68#b_1_A>`__: the applicable amount for a joint return or a surviving spouse.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    amount: float
    """
    The applicable amount.
    """

    year: int
    """
    The calendar year.
    """

    joint_return: JointReturn | None = None
    """
    The joint return; None for a surviving spouse.
    """

    surviving_spouse: Party | None = None
    """
    The surviving spouse, the taxpayer; None for a joint return.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.taxpayer.name,
            None if self.joint_return is None else self.joint_return.name,
            None if self.surviving_spouse is None else self.surviving_spouse.name,
            self.amount,
            self.year,
        )


@dataclass(eq=False)
class HeadOfHouseholdApplicableAmount(ApplicableAmount):
    """
    `§ 68(b)(1)(B) <https://www.law.cornell.edu/uscode/text/26/68#b_1_B>`__: the applicable amount for a head of household.
    """


@dataclass(eq=False)
class UnmarriedApplicableAmount(ApplicableAmount):
    """
    `§ 68(b)(1)(C) <https://www.law.cornell.edu/uscode/text/26/68#b_1_C>`__: the applicable amount for an individual not married, no surviving
    spouse and no head of household.
    """


@dataclass(eq=False)
class SeparateReturnApplicableAmount(ApplicableAmount):
    """
    `§ 68(b)(1)(D) <https://www.law.cornell.edu/uscode/text/26/68#b_1_D>`__: the applicable amount for a married individual filing separately.
    """


# %% surviving spouse and head of household


@dataclass(eq=False)
class SurvivingSpouse(SaraConclusion):
    """
    `§ 2(a) <https://www.law.cornell.edu/uscode/text/26/2#a>`__: that a taxpayer is a surviving spouse for a calendar year.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    year: int
    """
    The calendar year.
    """

    spouse: Party | None = None
    """
    The spouse who died; None where the case states the conclusion without them.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.name_of(self.spouse), self.year


@dataclass(eq=False)
class DeceasedSpouse(SaraConclusion):
    """
    `§ 2(a)(1)(A) <https://www.law.cornell.edu/uscode/text/26/2#a_1_A>`__: that a taxpayer's spouse died during either of the two years before the calendar year.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    spouse: Party
    """
    The spouse who died.
    """

    marriage: Marriage
    """
    Their marriage.
    """

    year_of_death: int
    """
    The calendar year the spouse died in.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.taxpayer.name,
            self.spouse.name,
            self.marriage.name,
            self.year_of_death,
            self.year,
        )


@dataclass(eq=False)
class SurvivingSpouseUnderGeneralRule(SaraConclusion):
    """
    `§ 2(a)(1) <https://www.law.cornell.edu/uscode/text/26/2#a_1>`__: a taxpayer whose spouse died in the two years before, keeping a home for a dependent child.
    """

    deceased_spouse: DeceasedSpouse
    """
    The death of the spouse, under `§ 2(a)(1)(A) <https://www.law.cornell.edu/uscode/text/26/2#a_1_A>`__.
    """

    home: HomeForDependent
    """
    The home kept, under `§ 2(a)(1)(B) <https://www.law.cornell.edu/uscode/text/26/2#a_1_B>`__.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.deceased_spouse.taxpayer.name,
            self.deceased_spouse.spouse.name,
            self.deceased_spouse.marriage.name,
            self.home.household.name,
            self.home.individual.name,
            self.year,
        )

    @property
    def year(self) -> int:
        """
        The calendar year.
        """
        return self.deceased_spouse.year


@dataclass(eq=False)
class HomeForDependent(SaraConclusion):
    """
    A taxpayer maintaining a household as the principal place of abode of an individual
    for the calendar year.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    household: Household
    """
    The household.
    """

    individual: Party
    """
    The individual.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.household.name, self.individual.name, self.year


@dataclass(eq=False)
class HomeForDependentChild(HomeForDependent):
    """
    `§ 2(a)(1)(B) <https://www.law.cornell.edu/uscode/text/26/2#a_1_B>`__: a home kept all year for a son, stepson, daughter or stepdaughter the taxpayer may deduct an exemption for.
    """


@dataclass(eq=False)
class HeadOfHouseholdHome(HomeForDependent):
    """
    `§ 2(b)(1) <https://www.law.cornell.edu/uscode/text/26/2#b_1>`__: an unmarried taxpayer, no surviving spouse, keeping a home for a qualifying individual.
    """


@dataclass(eq=False)
class HomeForQualifyingIndividual(HomeForDependent):
    """
    `§ 2(b)(1)(A) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A>`__: a home kept for over half the year for a qualifying child or a dependent.
    """


@dataclass(eq=False)
class HomeForParent(HomeForDependent):
    """
    `§ 2(b)(1)(B) <https://www.law.cornell.edu/uscode/text/26/2#b_1_B>`__: a home kept all year for a father or mother the taxpayer may deduct an exemption for.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        """
        Extends :meth:`HomeForDependent.prolog_arguments` by the exemption amount, left
        open since it depends on head-of-household status itself.
        """
        return (
            self.taxpayer.name,
            self.household.name,
            self.individual.name,
            None,
            self.year,
        )


@dataclass(eq=False)
class RemarriedTaxpayer(SaraConclusion):
    """
    `§ 2(a)(2)(A) <https://www.law.cornell.edu/uscode/text/26/2#a_2_A>`__: that a taxpayer remarried before the close of the calendar year.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    remarriage: Marriage
    """
    The later marriage.
    """

    previous_marriage: Marriage
    """
    The earlier marriage.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.taxpayer.name,
            self.remarriage.name,
            self.previous_marriage.name,
            self.day_text(self.remarriage.period.start),
            self.year,
        )


@dataclass(eq=False)
class SpousesWithoutNonresidentAlien(SaraConclusion):
    """
    `§ 2(a)(2)(B) <https://www.law.cornell.edu/uscode/text/26/2#a_2_B>`__: that neither spouse is a nonresident alien during the year, so a joint return could have been made.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    spouse: Party
    """
    The spouse.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.spouse.name, self.year


@dataclass(eq=False)
class HeadOfHousehold(SaraConclusion):
    """
    `§ 2(b) <https://www.law.cornell.edu/uscode/text/26/2#b>`__: that a taxpayer is a head of household for a calendar year, by reason of an individual.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    year: int
    """
    The calendar year.
    """

    individual: Party | None = None
    """
    The individual; None where the case states the conclusion without them.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.name_of(self.individual), self.year


@dataclass(eq=False)
class QualifyingChildOfHousehold(HeadOfHousehold):
    """
    `§ 2(b)(1)(A)(i) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_i>`__: a qualifying child, not married filing jointly.
    """


@dataclass(eq=False)
class DependentOfHousehold(HeadOfHousehold):
    """
    `§ 2(b)(1)(A)(ii) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_ii>`__: a dependent the taxpayer may deduct an exemption for.
    """


@dataclass(eq=False)
class HouseholdMemberDependent(HeadOfHousehold):
    """
    `§ 2(b)(3)(B) <https://www.law.cornell.edu/uscode/text/26/2#b_3_B>`__: an individual who would be no dependent but for `§ 152(d)(2)(H) <https://www.law.cornell.edu/uscode/text/26/152#d_2_H>`__.
    """


@dataclass(eq=False)
class HeadOfHouseholdLimitation(HeadOfHousehold):
    """
    `§ 2(b)(3) <https://www.law.cornell.edu/uscode/text/26/2#b_3>`__: that the taxpayer is no head of household by reason of the individual.
    """


@dataclass(eq=False)
class MarriedChild(IndividualYearConclusion):
    """
    `§ 2(b)(1)(A)(i)(I) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_i_I>`__: that a child is married at the close of the year.
    """


@dataclass(eq=False)
class ChildFilingJointly(AnnualDependency):
    """
    `§ 2(b)(1)(A)(i)(II) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_i_II>`__: that a child is no dependent by reason of `§ 152(b)(2) <https://www.law.cornell.edu/uscode/text/26/152#b_2>`__, the taxpayer in the spouse's place, as SARA's program asks it.
    """


@dataclass(eq=False)
class SeparatedForHeadOfHousehold(SaraConclusion):
    """
    `§ 2(b)(2)(A) <https://www.law.cornell.edu/uscode/text/26/2#b_2_A>`__: that a taxpayer legally separated from their spouse is not considered married.
    """

    separation: LegalSeparation
    """
    The separation.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    spouse: Party
    """
    The spouse.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return (
            self.taxpayer.name,
            self.spouse.name,
            self.separation.name,
            self.separation.marriage.name,
            self.year,
        )


@dataclass(eq=False)
class NonresidentAlienSpouse(SaraConclusion):
    """
    `§ 2(b)(2)(B) <https://www.law.cornell.edu/uscode/text/26/2#b_2_B>`__: that a taxpayer whose spouse is a nonresident alien in the year is considered not married.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    spouse: Party
    """
    The spouse.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.spouse.name, self.year


@dataclass(eq=False)
class SpouseDeceasedInYear(SaraConclusion):
    """
    `§ 2(b)(2)(C) <https://www.law.cornell.edu/uscode/text/26/2#b_2_C>`__: that a taxpayer whose spouse died in the year is considered married at its close.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    marriage: Marriage
    """
    Their marriage.
    """

    spouse: Party
    """
    The spouse who died.
    """

    year: int
    """
    The calendar year.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.marriage.name, self.spouse.name, self.year


@dataclass(eq=False)
class NonresidentAlienTaxpayer(SaraConclusion):
    """
    `§ 2(b)(3)(A) <https://www.law.cornell.edu/uscode/text/26/2#b_3_A>`__: that a taxpayer is a nonresident alien at some time during the year.
    """

    taxpayer: Party
    """
    The taxpayer.
    """

    year: int
    """
    The calendar year.
    """

    day: datetime.date
    """
    A day of the year they are one: January 1 where their status has no start, else
    December 31.
    """

    def prolog_arguments(self) -> tuple[Term, ...]:
        return self.taxpayer.name, self.year, self.day_text(self.day)
