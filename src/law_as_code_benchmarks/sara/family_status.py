"""
Family status as rules over the domain model: §§ `7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__, `152 <https://www.law.cornell.edu/uscode/text/26/152>`__, `151 <https://www.law.cornell.edu/uscode/text/26/151>`__, `2 <https://www.law.cornell.edu/uscode/text/26/2>`__ and `68(b) <https://www.law.cornell.edu/uscode/text/26/68#b>`__, with
the kinship and gross income SARA defines them by.

A provision asks another only what that one decides without asking it back, which
breaks the mutual recursion of SARA's program.
"""

from __future__ import annotations

import math
from abc import ABC
from dataclasses import dataclass

from krrood.entity_query_language.factories import (
    an,
    and_,
    entity,
    exists,
    in_,
    inference,
    not_,
    or_,
    variable,
)
from krrood.entity_query_language.factories import sum as total
from krrood.entity_query_language.query.query import Query
from krrood.entity_query_language.predicate import symbolic_function
from krrood.ormatic.utils import classproperty
from typing_extensions import TypeVar

from law_as_code_benchmarks.sara.domain import (
    Birth,
    CalendarYear,
    Death,
    Household,
    JointReturn,
    Kinship,
    LegalSeparation,
    Marriage,
    NonresidentAlienStatus,
    Party,
    Payment,
    Period,
    Residence,
    Revenue,
    Siblinghood,
    World,
)
from law_as_code_benchmarks.sara.family_status_conclusions import (
    AnnualDependency,
    AbsentSpouse,
    AgeRequirement,
    AgeRequirementOfQualifyingChild,
    AncestorRelationship,
    ApplicableAmount,
    ApplicablePercentage,
    HeadOfHouseholdApplicableAmount,
    JointReturnOrSurvivorApplicableAmount,
    SeparateReturnApplicableAmount,
    UnmarriedApplicableAmount,
    ChildFilingJointly,
    ChildInLawRelationship,
    ChildOrDescendantOfChildRelationship,
    ChildOrDescendantRelationship,
    ChildRelationship,
    DeceasedSpouse,
    Dependent,
    DependencyException,
    DependentCandidate,
    DependentExemptionAmount,
    DependentOfHousehold,
    DependentOfOtherTaxpayer,
    DependentUnderDefinition,
    DescendantRelationship,
    DisallowedExemptionAmount,
    ExemptionAmount,
    ExemptionForDependent,
    ExemptionForSpouse,
    GeneralExemptionAmount,
    GrossIncome,
    HeadOfHousehold,
    HeadOfHouseholdHome,
    HeadOfHouseholdLimitation,
    HomeForDependent,
    HomeForDependentChild,
    HomeForParent,
    HomeForQualifyingIndividual,
    HomeOfChild,
    HouseholdMaintenance,
    HouseholdMemberDependent,
    HouseholdMemberRelationship,
    IndividualGrossIncome,
    IndividualLivingApart,
    InLawRelationship,
    JointFiling,
    LegallySeparatedIndividual,
    MaintenanceCost,
    MarriedAtDetermination,
    MarriedChild,
    MarriedIndividual,
    MarriedUnderGeneralRule,
    NephewOrNieceRelationship,
    NoGrossIncome,
    NoJointReturn,
    NonresidentAlienSpouse,
    NonresidentAlienTaxpayer,
    NoQualifyingChild,
    ParentInLawRelationship,
    PhasedOutExemptionAmount,
    QualifyingChild,
    QualifyingChildDependent,
    QualifyingChildOfHousehold,
    QualifyingChildRelationship,
    QualifyingChildRelationshipUntilDeath,
    QualifyingChildUnderGeneralRule,
    QualifyingRelative,
    QualifyingRelativeDependent,
    QualifyingRelativeRelationship,
    QualifyingRelativeRelationshipUntilDeath,
    QualifyingRelativeUnderGeneralRule,
    ReducedExemptionAmount,
    Relationship,
    RelationshipToTaxpayer,
    RemarriedTaxpayer,
    SeparatedForHeadOfHousehold,
    SharedAbode,
    SiblingInLawRelationship,
    SiblingOrDescendantOfSiblingRelationship,
    SiblingOrStepsiblingRelationship,
    SiblingRelationship,
    SpouseDeceasedInYear,
    SpousesWithoutNonresidentAlien,
    StepparentOfTaxpayerRelationship,
    StepparentRelationship,
    StepsiblingRelationship,
    SurvivingSpouse,
    SurvivingSpouseUnderGeneralRule,
    SuspendedExemptionAmount,
    UncleOrAuntRelationship,
)
from law_as_code_benchmarks.sara.provision import (
    Provision,
    SaraConclusion,
    SaraPredicate,
)

# %% kinship


@dataclass
class ChildRelation(Provision[ChildRelationship]):
    """
    SARA's ``is_child_of``: a party stated to be a son or daughter of another, or the
    other stated to be their father or mother.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.CHILD`.
        """
        return SaraPredicate.CHILD

    def query(self) -> Query:
        kinship = variable(Kinship, domain=self.world.kinships)
        return an(
            entity(
                inference(ChildRelationship)(
                    relative=kinship.child, person=kinship.parent, period=kinship.period
                )
            )
        )


@dataclass
class DescendantRelation(Provision[DescendantRelationship]):
    """
    SARA's ``is_descendent_of``: a child of a party, or a descendant of a child, for the
    days the descendant is a child of their own parent.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.DESCENDANT`.
        """
        return SaraPredicate.DESCENDANT

    def query(self) -> Query:
        descent = variable(DescendantRelationship, domain=self.descents())
        return an(entity(descent))

    def descents(self) -> list[DescendantRelationship]:
        """
        :return: Each pair of a descendant and an ancestor once, from the children up.

        krrood queries do not recurse, so the generations are joined here.
        """
        children = ChildRelation(world=self.world).conclusions
        descents = [
            DescendantRelationship(
                relative=child.relative, person=child.person, period=child.period
            )
            for child in children
        ]
        generation = descents
        while generation:
            generation = [
                DescendantRelationship(
                    relative=descent.relative,
                    person=child.person,
                    period=descent.period,
                )
                for descent in generation
                for child in children
                if descent.person is child.relative
                and not any(
                    known.relative is descent.relative and known.person is child.person
                    for known in descents
                )
            ]
            descents = descents + generation
        return descents


@dataclass
class SiblingRelation(Provision[SiblingRelationship]):
    """
    SARA's ``is_sibling_of``: two different parties of one relation of brothers or
    sisters.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SIBLING`.
        """
        return SaraPredicate.SIBLING

    def query(self) -> Query:
        siblinghood = variable(Siblinghood, domain=self.world.siblinghoods)
        relative = variable(Party, domain=self.world.parties)
        person = variable(Party, domain=self.world.parties)
        return an(
            entity(
                inference(SiblingRelationship)(
                    relative=relative, person=person, period=siblinghood.period
                )
            ).where(
                in_(relative, siblinghood.siblings),
                in_(person, siblinghood.siblings),
                relative != person,
            )
        )


@dataclass
class StepsiblingRelation(Provision[StepsiblingRelationship]):
    """
    SARA's ``is_stepsibling_of``: two different parties, a parent of each married to a
    parent of the other, for the days all three relations last.

    As in SARA, the two parents may be one, married to anyone.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.STEPSIBLING`.
        """
        return SaraPredicate.STEPSIBLING

    def query(self) -> Query:
        children = ChildRelation(world=self.world).conclusions
        child = variable(ChildRelationship, domain=children)
        other_child = variable(ChildRelationship, domain=children)
        marriage = variable(Marriage, domain=self.world.marriages)
        return an(
            entity(
                inference(StepsiblingRelationship)(
                    relative=child.relative,
                    person=other_child.relative,
                    period=Period.intersect(
                        Period.intersect(other_child.period, child.period),
                        marriage.period,
                    ),
                )
            ).where(
                in_(other_child.person, marriage.spouses),
                in_(child.person, marriage.spouses),
                child.relative != other_child.relative,
            )
        )


@dataclass
class ChildInLawRelation(Provision[ChildInLawRelationship]):
    """
    SARA's ``is_child_in_law_of``: a party married to a child of another, for the days
    both relations last.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.CHILD_IN_LAW`.
        """
        return SaraPredicate.CHILD_IN_LAW

    def query(self) -> Query:
        child = variable(
            ChildRelationship, domain=ChildRelation(world=self.world).conclusions
        )
        marriage = variable(Marriage, domain=self.world.marriages)
        relative = variable(Party, domain=self.world.parties)
        return an(
            entity(
                inference(ChildInLawRelationship)(
                    relative=relative,
                    person=child.person,
                    period=Period.intersect(marriage.period, child.period),
                )
            ).where(
                in_(child.relative, marriage.spouses),
                in_(relative, marriage.spouses),
                relative != child.person,
            )
        )


RelationshipType = TypeVar("RelationshipType", bound=Relationship)


@dataclass
class MarriageToParentRelation(Provision[RelationshipType], ABC):
    """
    A party married to a parent of another, for the days both relations last.
    """

    def query(self) -> Query:
        conclusion_type = self.get_type_of_generic_parameter(parameter=RelationshipType)
        child = variable(
            ChildRelationship, domain=ChildRelation(world=self.world).conclusions
        )
        marriage = variable(Marriage, domain=self.marriages())
        relative = variable(Party, domain=self.world.parties)
        return an(
            entity(
                inference(conclusion_type)(
                    relative=relative,
                    person=child.relative,
                    period=Period.intersect(marriage.period, child.period),
                )
            ).where(
                in_(child.person, marriage.spouses),
                in_(relative, marriage.spouses),
                relative != child.relative,
            )
        )

    def marriages(self) -> list[Marriage]:
        """:return: The marriages the relation may come of."""
        return self.world.marriages


@dataclass
class ParentInLawRelation(MarriageToParentRelation[ParentInLawRelationship]):
    """
    SARA's ``is_parent_in_law_of``: a party married to a parent of another, as SARA's
    program defines a parent-in-law.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.PARENT_IN_LAW`.
        """
        return SaraPredicate.PARENT_IN_LAW


@dataclass
class StepparentRelation(MarriageToParentRelation[StepparentRelationship]):
    """
    SARA's ``is_stepparent_of``: a party married to a parent of another, the marriage's
    start stated.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.STEPPARENT`.
        """
        return SaraPredicate.STEPPARENT

    def marriages(self) -> list[Marriage]:
        """
        Restricts :meth:`MarriageToParentRelation.marriages` to those whose start the
        case states.
        """
        return [
            marriage
            for marriage in self.world.marriages
            if marriage.period.start is not None
        ]


@dataclass
class SiblingInLawRelation(Provision[SiblingInLawRelationship]):
    """
    SARA's ``is_sibling_in_law_of``: two different parties, one married to a brother or
    sister of the other, for the days both relations last.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SIBLING_IN_LAW`.
        """
        return SaraPredicate.SIBLING_IN_LAW

    def query(self) -> Query:
        sibling = variable(
            SiblingRelationship, domain=SiblingRelation(world=self.world).conclusions
        )
        marriage = variable(Marriage, domain=self.world.marriages)
        married = variable(Party, domain=self.world.parties)
        relative = variable(Party, domain=self.world.parties)
        person = variable(Party, domain=self.world.parties)
        return an(
            entity(
                inference(SiblingInLawRelationship)(
                    relative=relative,
                    person=person,
                    period=Period.intersect(marriage.period, sibling.period),
                )
            ).where(
                in_(sibling.person, marriage.spouses),
                in_(married, marriage.spouses),
                married != sibling.relative,
                or_(
                    and_(relative == married, person == sibling.relative),
                    and_(person == married, relative == sibling.relative),
                ),
            )
        )


# %% gross income


@dataclass
class GrossIncomeOfParty(Provision[GrossIncome]):
    """
    SARA's ``gross_income``: the payments a party receives and the income they earn in a
    calendar year, their spouse's added where the two make a joint return for it.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.GROSS_INCOME`.
        """
        return SaraPredicate.GROSS_INCOME

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        individual = self.individual_gross_incomes()
        gross_income = variable(
            GrossIncome,
            domain=self.separate_gross_incomes(individual)
            + self.joint_gross_incomes(individual),
        )
        return an(entity(gross_income))

    def individual_gross_incomes(self) -> list[IndividualGrossIncome]:
        """:return: What each party receives in each calendar year, nothing where they receive nothing."""
        received = self.received_incomes()
        return received + [
            IndividualGrossIncome(person=person, year=year, amount=0)
            for person in self.world.parties
            for year in self.world.years_in_question()
            if not any(
                income.person is person and income.year is year for income in received
            )
        ]

    def received_incomes(self) -> list[IndividualGrossIncome]:
        """:return: What each party receives in each calendar year they receive anything in."""
        revenue = variable(Revenue, domain=[*self.world.incomes, *self.world.payments])
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return (
            an(
                entity(
                    inference(IndividualGrossIncome)(
                        person=revenue.earner(),
                        year=year,
                        amount=total(revenue.received_amount(), default=0),
                    )
                )
                .where(
                    revenue.earner() != None,
                    revenue.received_day() != None,
                    revenue.received_day() >= year.opening_day,
                    revenue.received_day() <= year.closing_day,
                )
                .grouped_by(revenue.earner(), year)
            )
        ).tolist()

    def separate_gross_incomes(
        self, individual: list[IndividualGrossIncome]
    ) -> list[GrossIncome]:
        """:return: The gross income of each party of *individual* making no joint return for its year."""
        income = variable(IndividualGrossIncome, domain=individual)
        filing = variable(
            JointFiling, domain=JointFilingTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(GrossIncome)(
                    person=income.person, year=income.year.number, amount=income.amount
                )
            ).where(
                not_(
                    exists(
                        filing,
                        and_(
                            filing.individual == income.person,
                            filing.year == income.year.number,
                        ),
                    )
                )
            )
        ).tolist()

    def joint_gross_incomes(
        self, individual: list[IndividualGrossIncome]
    ) -> list[GrossIncome]:
        """:return: The gross income of each party making a joint return, theirs and their spouse's of *individual*."""
        income = variable(IndividualGrossIncome, domain=individual)
        filing = variable(JointFiling, domain=self.joint_filings())
        return an(
            entity(
                inference(GrossIncome)(
                    person=filing.individual,
                    year=filing.year,
                    amount=total(income.amount, default=0),
                )
            )
            .where(
                or_(income.person == filing.individual, income.person == filing.spouse),
                income.year.number == filing.year,
            )
            .grouped_by(filing.individual, filing.spouse, filing.year)
        ).tolist()

    def joint_filings(self) -> list[JointFiling]:
        """:return: The joint filings, one for each individual, spouse and year, however many returns state it."""
        filings = {}
        for filing in JointFilingTest(world=self.world).conclusions:
            filings.setdefault((filing.individual, filing.spouse, filing.year), filing)
        return list(filings.values())


# %% marital status


@dataclass
class MarriedAtDeterminationTest(Provision[MarriedAtDetermination]):
    """
    `§ 7703(a)(1) <https://www.law.cornell.edu/uscode/text/26/7703#a_1>`__: an individual married at the close of the year, or, where their spouse
    died in it, at the death.

    A marriage without a start is taken to start on January 1 of the year, as in SARA.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.MARRIED_AT_DETERMINATION`.
        """
        return SaraPredicate.MARRIED_AT_DETERMINATION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fifth argument.
        """
        return 4

    def query(self) -> Query:
        married = variable(
            MarriedAtDetermination,
            domain=self.married_at_death() + self.married_at_close(),
        )
        return an(entity(married))

    def married_at_death(self) -> list[MarriedAtDetermination]:
        """:return: The individuals married at the death of their spouse in the year."""
        marriage = variable(Marriage, domain=self.world.marriages)
        person = variable(Party, domain=self.world.parties)
        spouse = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        death = variable(
            Death, domain=[death for death in self.world.deaths if death.day]
        )
        return an(
            entity(
                inference(MarriedAtDetermination)(
                    person=person,
                    spouse=spouse,
                    marriage=marriage,
                    year=year.number,
                    spouse_death_day=death.day,
                )
            ).where(
                in_(person, marriage.spouses),
                in_(spouse, marriage.spouses),
                person != spouse,
                death.person == spouse,
                death.day >= year.opening_day,
                death.day <= year.closing_day,
                or_(marriage.period.start == None, marriage.period.start <= death.day),
                or_(marriage.period.end == None, death.day <= marriage.period.end),
            )
        ).tolist()

    def married_at_close(self) -> list[MarriedAtDetermination]:
        """:return: The individuals married at the close of the year, their spouse not dying in it."""
        marriage = variable(Marriage, domain=self.world.marriages)
        person = variable(Party, domain=self.world.parties)
        spouse = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        death = variable(Death, domain=self.world.deaths)
        earlier_death = variable(Death, domain=self.world.deaths)
        return an(
            entity(
                inference(MarriedAtDetermination)(
                    person=person, spouse=spouse, marriage=marriage, year=year.number
                )
            ).where(
                in_(person, marriage.spouses),
                in_(spouse, marriage.spouses),
                person != spouse,
                or_(
                    marriage.period.start == None,
                    marriage.period.start <= year.closing_day,
                ),
                not_(
                    exists(
                        death,
                        and_(
                            death.person == spouse,
                            death.day != None,
                            death.day >= year.opening_day,
                            death.day <= year.closing_day,
                        ),
                    )
                ),
                or_(
                    and_(
                        marriage.period.end == None,
                        not_(
                            exists(
                                earlier_death,
                                and_(
                                    earlier_death.person == spouse,
                                    or_(
                                        earlier_death.day == None,
                                        earlier_death.day
                                        < year.opening_day_of_following_year,
                                    ),
                                ),
                            )
                        ),
                    ),
                    and_(
                        marriage.period.end != None,
                        marriage.period.end >= year.opening_day_of_following_year,
                    ),
                ),
            )
        ).tolist()


@dataclass
class LegalSeparationTest(Provision[LegallySeparatedIndividual]):
    """
    `§ 7703(a)(2) <https://www.law.cornell.edu/uscode/text/26/7703#a_2>`__: an individual legally separated from their spouse under a decree of
    divorce or of separate maintenance by the close of the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.LEGALLY_SEPARATED`.
        """
        return SaraPredicate.LEGALLY_SEPARATED

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fifth argument.
        """
        return 4

    def query(self) -> Query:
        separation = variable(LegalSeparation, domain=self.world.legal_separations)
        person = variable(Party, domain=self.world.parties)
        spouse = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(LegallySeparatedIndividual)(
                    person=person,
                    spouse=spouse,
                    marriage=separation.marriage,
                    year=year.number,
                    separation=separation,
                )
            ).where(
                in_(person, separation.marriage.spouses),
                in_(spouse, separation.marriage.spouses),
                person != spouse,
                separation.day <= year.closing_day,
            )
        )


@dataclass
class MarriedUnderGeneralRuleTest(Provision[MarriedUnderGeneralRule]):
    """
    `§ 7703(a) <https://www.law.cornell.edu/uscode/text/26/7703#a>`__: an individual married under `(1) <https://www.law.cornell.edu/uscode/text/26/7703#a_1>`__, not legally separated under `(2) <https://www.law.cornell.edu/uscode/text/26/7703#a_2>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.MARRIED_UNDER_GENERAL_RULE`.
        """
        return SaraPredicate.MARRIED_UNDER_GENERAL_RULE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        married = variable(
            MarriedAtDetermination,
            domain=MarriedAtDeterminationTest(world=self.world).conclusions,
        )
        separated = variable(
            LegallySeparatedIndividual,
            domain=LegalSeparationTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(MarriedUnderGeneralRule)(
                    person=married.person,
                    spouse=married.spouse,
                    marriage=married.marriage,
                    year=married.year,
                )
            ).where(
                not_(
                    exists(
                        separated,
                        and_(
                            separated.person == married.person,
                            separated.spouse == married.spouse,
                            separated.marriage == married.marriage,
                            separated.year == married.year,
                        ),
                    )
                )
            )
        )


@dataclass
class JointFilingTest(Provision[JointFiling]):
    """
    `§ 152(b)(2) <https://www.law.cornell.edu/uscode/text/26/152#b_2>`__: an individual married under `§ 7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__ who made a joint return with
    their spouse for the calendar year.

    A joint return for the year rules out `§ 7703(b)(1) <https://www.law.cornell.edu/uscode/text/26/7703#b_1>`__, so `§ 7703(a) <https://www.law.cornell.edu/uscode/text/26/7703#a>`__ decides the
    marriage alone, together with the case's stated conclusions of `§ 7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.JOINT_FILING`.
        """
        return SaraPredicate.JOINT_FILING

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        married = variable(
            MarriedIndividual,
            domain=list(
                dict.fromkeys(
                    MarriedUnderGeneralRuleTest(world=self.world).conclusions
                    + [
                        conclusion
                        for conclusion in self.world.stated_conclusions
                        if isinstance(conclusion, MarriedIndividual)
                    ]
                )
            ),
        )
        joint_return = variable(JointReturn, domain=self.world.joint_returns)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(JointFiling)(
                    individual=married.person,
                    spouse=married.spouse,
                    year=married.year,
                    joint_return=joint_return,
                )
            ).where(
                year.number == married.year,
                in_(married.person, joint_return.filers),
                in_(married.spouse, joint_return.filers),
                joint_return.period.start == year.opening_day,
                joint_return.period.end == year.closing_day,
            )
        )


@dataclass
class HouseholdMaintenanceTest(Provision[HouseholdMaintenance]):
    """
    `§ 7703(b)(2) <https://www.law.cornell.edu/uscode/text/26/7703#b_2>`__: an individual paying at least half the cost of maintaining a household
    in the calendar year, as SARA's program compares; the statute asks for over half.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HOUSEHOLD_MAINTENANCE`.
        """
        return SaraPredicate.HOUSEHOLD_MAINTENANCE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        contribution = variable(MaintenanceCost, domain=self.contributions())
        cost = variable(MaintenanceCost, domain=self.costs())
        return an(
            entity(
                inference(HouseholdMaintenance)(
                    person=contribution.payer,
                    household=contribution.household,
                    year=contribution.year,
                    cost=cost.amount,
                )
            ).where(
                contribution.household == cost.household,
                contribution.year == cost.year,
                MaintenanceCost.is_at_least_half_of(contribution, cost),
            )
        )

    def maintenance_payments(self) -> list[Payment]:
        """:return: The payments for a household on a stated day."""
        return [
            payment
            for payment in self.world.payments
            if payment.household_maintained is not None and payment.day is not None
        ]

    def contributions(self) -> list[MaintenanceCost]:
        """:return: What each party pays for each household in each calendar year."""
        payment = variable(Payment, domain=self.maintenance_payments())
        return an(
            entity(
                inference(MaintenanceCost)(
                    household=payment.household_maintained,
                    year=payment.day.year,
                    amount=total(payment.amount, default=0),
                    payer=payment.payer,
                )
            ).grouped_by(payment.payer, payment.household_maintained, payment.day.year)
        ).tolist()

    def costs(self) -> list[MaintenanceCost]:
        """:return: What is paid for each household in each calendar year, by anyone."""
        payment = variable(Payment, domain=self.maintenance_payments())
        return an(
            entity(
                inference(MaintenanceCost)(
                    household=payment.household_maintained,
                    year=payment.day.year,
                    amount=total(payment.amount, default=0),
                )
            ).grouped_by(payment.household_maintained, payment.day.year)
        ).tolist()


@dataclass
class HomeOfChildTest(Provision[HomeOfChild]):
    """
    `§ 7703(b)(1) <https://www.law.cornell.edu/uscode/text/26/7703#b_1>`__: an individual making no joint return who keeps as their home a
    household that is, for at least half the year, the home of a qualifying child of
    theirs.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HOME_OF_CHILD`.
        """
        return SaraPredicate.HOME_OF_CHILD

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        child = variable(
            QualifyingChildDependent,
            domain=QualifyingChildDependentTest(world=self.world).conclusions,
        )
        home = variable(Residence, domain=self.world.residences)
        child_home = variable(
            Residence,
            domain=[
                residence
                for residence in self.world.residences
                if residence.period.start is not None
            ],
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        joint_return = variable(JointReturn, domain=self.world.joint_returns)
        return an(
            entity(
                inference(HomeOfChild)(
                    person=child.taxpayer,
                    household=home.household,
                    year=child.year,
                    child=child.individual,
                )
            ).where(
                year.number == child.year,
                in_(child.taxpayer, home.residents),
                in_(child.individual, child_home.residents),
                child_home.household == home.household,
                CalendarYear.days_within(year, child_home.period) >= year.half_length,
                not_(
                    exists(
                        joint_return,
                        and_(
                            in_(child.taxpayer, joint_return.filers),
                            joint_return.period.start == year.opening_day,
                            joint_return.period.end == year.closing_day,
                        ),
                    )
                ),
            )
        )


@dataclass
class AbsentSpouseTest(Provision[AbsentSpouse]):
    """
    `§ 7703(b)(3) <https://www.law.cornell.edu/uscode/text/26/7703#b_3>`__: a married individual whose spouse is no member of a household during the
    last 6 months of the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.ABSENT_SPOUSE`.
        """
        return SaraPredicate.ABSENT_SPOUSE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        married = variable(
            MarriedUnderGeneralRule,
            domain=MarriedUnderGeneralRuleTest(world=self.world).conclusions,
        )
        household = variable(Household, domain=self.world.households())
        year = variable(CalendarYear, domain=self.world.years_in_question())
        residence = variable(
            Residence,
            domain=[
                residence
                for residence in self.world.residences
                if residence.period.start is not None
            ],
        )
        return an(
            entity(
                inference(AbsentSpouse)(
                    person=married.person,
                    household=household,
                    year=married.year,
                    spouse=married.spouse,
                )
            ).where(
                year.number == married.year,
                not_(
                    exists(
                        residence,
                        and_(
                            in_(married.spouse, residence.residents),
                            residence.household == household,
                            residence.period.start
                            <= year.opening_day_of_following_year,
                            or_(
                                residence.period.end == None,
                                residence.period.end
                                >= year.opening_day_of_last_six_months,
                            ),
                        ),
                    )
                ),
            )
        )


@dataclass
class LivingApartTest(Provision[IndividualLivingApart]):
    """
    `§ 7703(b) <https://www.law.cornell.edu/uscode/text/26/7703#b>`__: a married individual keeping, and paying for, the home of a child of
    theirs, their spouse absent from it in the last 6 months of the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.LIVING_APART`.
        """
        return SaraPredicate.LIVING_APART

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        home = variable(
            HomeOfChild, domain=HomeOfChildTest(world=self.world).conclusions
        )
        maintenance = variable(
            HouseholdMaintenance,
            domain=HouseholdMaintenanceTest(world=self.world).conclusions,
        )
        absence = variable(
            AbsentSpouse, domain=AbsentSpouseTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(IndividualLivingApart)(
                    person=absence.person, spouse=absence.spouse, year=absence.year
                )
            ).where(
                home.person == absence.person,
                home.household == absence.household,
                home.year == absence.year,
                maintenance.person == absence.person,
                maintenance.household == absence.household,
                maintenance.year == absence.year,
            )
        )


@dataclass
class MarriedIndividualTest(Provision[MarriedIndividual]):
    """
    `§ 7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__: an individual married under `(a) <https://www.law.cornell.edu/uscode/text/26/7703#a>`__ who does not live apart from their
    spouse under `(b) <https://www.law.cornell.edu/uscode/text/26/7703#b>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.MARRIED`.
        """
        return SaraPredicate.MARRIED

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        married = variable(
            MarriedUnderGeneralRule,
            domain=MarriedUnderGeneralRuleTest(world=self.world).conclusions,
        )
        apart = variable(
            IndividualLivingApart, domain=LivingApartTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(MarriedIndividual)(
                    person=married.person,
                    spouse=married.spouse,
                    marriage=married.marriage,
                    year=married.year,
                )
            ).where(
                not_(
                    exists(
                        apart,
                        and_(
                            apart.person == married.person,
                            apart.spouse == married.spouse,
                            apart.year == married.year,
                        ),
                    )
                )
            )
        )

    def separate_filers(self) -> list[MarriedIndividual]:
        """:return: The married individuals making no joint return with their spouse for the year."""
        married = variable(MarriedIndividual, domain=self.conclusions)
        filing = variable(
            JointFiling, domain=JointFilingTest(world=self.world).conclusions
        )
        return an(
            entity(married).where(
                not_(
                    exists(
                        filing,
                        and_(
                            filing.individual == married.person,
                            filing.spouse == married.spouse,
                            filing.year == married.year,
                        ),
                    )
                )
            )
        ).tolist()


# %% relationships of a qualifying child


@dataclass
class ChildOrDescendantOfChildTest(Provision[ChildOrDescendantOfChildRelationship]):
    """
    `§ 152(c)(2)(A) <https://www.law.cornell.edu/uscode/text/26/152#c_2_A>`__: a child of the taxpayer, or a descendant of such a child, for the days
    of the child's or the descendant's own relation.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.CHILD_OR_DESCENDANT_OF_CHILD`.
        """
        return SaraPredicate.CHILD_OR_DESCENDANT_OF_CHILD

    def query(self) -> Query:
        relationship = variable(
            ChildOrDescendantOfChildRelationship,
            domain=self.children() + self.descendants_of_children(),
        )
        return an(entity(relationship))

    def children(self) -> list[ChildOrDescendantOfChildRelationship]:
        """:return: The children of each taxpayer."""
        child = variable(
            ChildRelationship, domain=ChildRelation(world=self.world).conclusions
        )
        return an(
            entity(
                inference(ChildOrDescendantOfChildRelationship)(
                    individual=child.relative,
                    taxpayer=child.person,
                    relative=child.relative,
                    period=child.period,
                )
            )
        ).tolist()

    def descendants_of_children(self) -> list[ChildOrDescendantOfChildRelationship]:
        """:return: The descendants of the children of each taxpayer."""
        child = variable(
            ChildRelationship, domain=ChildRelation(world=self.world).conclusions
        )
        descendant = variable(
            DescendantRelationship,
            domain=DescendantRelation(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(ChildOrDescendantOfChildRelationship)(
                    individual=descendant.relative,
                    taxpayer=child.person,
                    relative=child.relative,
                    period=descendant.period,
                )
            ).where(
                descendant.person == child.relative,
                descendant.relative != child.relative,
            )
        ).tolist()


@dataclass
class SiblingOrStepsiblingTest(Provision[SiblingOrStepsiblingRelationship]):
    """
    `§ 152(d)(2)(B) <https://www.law.cornell.edu/uscode/text/26/152#d_2_B>`__: a brother, sister, stepbrother or stepsister of the taxpayer.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SIBLING_OR_STEPSIBLING`.
        """
        return SaraPredicate.SIBLING_OR_STEPSIBLING

    def query(self) -> Query:
        sibling = variable(
            Relationship,
            domain=SiblingRelation(world=self.world).conclusions
            + StepsiblingRelation(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(SiblingOrStepsiblingRelationship)(
                    individual=sibling.relative,
                    taxpayer=sibling.person,
                    period=sibling.period,
                )
            )
        )


@dataclass
class SiblingOrDescendantOfSiblingTest(
    Provision[SiblingOrDescendantOfSiblingRelationship]
):
    """
    `§ 152(c)(2)(B) <https://www.law.cornell.edu/uscode/text/26/152#c_2_B>`__: a brother, sister, stepbrother or stepsister of the taxpayer, or a
    descendant of one, for the days both relations last.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SIBLING_OR_DESCENDANT_OF_SIBLING`.
        """
        return SaraPredicate.SIBLING_OR_DESCENDANT_OF_SIBLING

    def query(self) -> Query:
        sibling = variable(
            SiblingOrStepsiblingRelationship,
            domain=SiblingOrStepsiblingTest(world=self.world).conclusions,
        )
        descendant = variable(
            DescendantRelationship,
            domain=DescendantRelation(world=self.world).conclusions,
        )
        relationship = variable(
            SiblingOrDescendantOfSiblingRelationship,
            domain=an(
                entity(
                    inference(SiblingOrDescendantOfSiblingRelationship)(
                        individual=sibling.individual,
                        taxpayer=sibling.taxpayer,
                        relative=sibling.individual,
                        period=sibling.period,
                    )
                )
            ).tolist()
            + an(
                entity(
                    inference(SiblingOrDescendantOfSiblingRelationship)(
                        individual=descendant.relative,
                        taxpayer=sibling.taxpayer,
                        relative=sibling.individual,
                        period=Period.intersect(sibling.period, descendant.period),
                    )
                ).where(descendant.person == sibling.individual)
            ).tolist(),
        )
        return an(entity(relationship))


@dataclass
class QualifyingChildRelationshipTest(Provision[QualifyingChildRelationship]):
    """
    `§ 152(c)(2) <https://www.law.cornell.edu/uscode/text/26/152#c_2>`__: an individual bearing a relationship of `(A) <https://www.law.cornell.edu/uscode/text/26/152#c_2_A>`__ or `(B) <https://www.law.cornell.edu/uscode/text/26/152#c_2_B>`__ to the taxpayer.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.QUALIFYING_CHILD_RELATIONSHIP`.
        """
        return SaraPredicate.QUALIFYING_CHILD_RELATIONSHIP

    def query(self) -> Query:
        relationship = variable(
            RelationshipToTaxpayer,
            domain=ChildOrDescendantOfChildTest(world=self.world).conclusions
            + SiblingOrDescendantOfSiblingTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(QualifyingChildRelationship)(
                    individual=relationship.individual,
                    taxpayer=relationship.taxpayer,
                    period=relationship.period,
                )
            )
        )


@dataclass
class QualifyingChildRelationshipUntilDeathTest(
    Provision[QualifyingChildRelationshipUntilDeath]
):
    """
    `§ 152(c)(1)(A) <https://www.law.cornell.edu/uscode/text/26/152#c_1_A>`__: a relationship of `§ 152(c)(2) <https://www.law.cornell.edu/uscode/text/26/152#c_2>`__, ending at the latest when either the
    individual or the taxpayer dies.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.QUALIFYING_CHILD_RELATIONSHIP_UNTIL_DEATH`.
        """
        return SaraPredicate.QUALIFYING_CHILD_RELATIONSHIP_UNTIL_DEATH

    def query(self) -> Query:
        relationship = variable(
            QualifyingChildRelationship,
            domain=QualifyingChildRelationshipTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(QualifyingChildRelationshipUntilDeath)(
                    individual=relationship.individual,
                    taxpayer=relationship.taxpayer,
                    period=Period.intersect(
                        Period.intersect(
                            relationship.period,
                            World.lifetime(self.world, relationship.taxpayer),
                        ),
                        World.lifetime(self.world, relationship.individual),
                    ),
                )
            )
        )


@dataclass
class SharedAbodeTest(Provision[SharedAbode]):
    """
    `§ 152(c)(1)(B) <https://www.law.cornell.edu/uscode/text/26/152#c_1_B>`__: an individual sharing the taxpayer's principal place of abode for at
    least half the year, counting only the days of their relationship, as SARA compares.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SHARED_ABODE`.
        """
        return SaraPredicate.SHARED_ABODE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The sixth argument.
        """
        return 5

    def query(self) -> Query:
        relationship = variable(
            QualifyingChildRelationshipUntilDeath,
            domain=QualifyingChildRelationshipUntilDeathTest(
                world=self.world
            ).conclusions,
        )
        residence = variable(Residence, domain=self.world.residences)
        taxpayer_residence = variable(Residence, domain=self.world.residences)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(SharedAbode)(
                    individual=relationship.individual,
                    taxpayer=relationship.taxpayer,
                    period=relationship.period,
                    household=residence.household,
                    year=year.number,
                )
            ).where(
                in_(relationship.individual, residence.residents),
                in_(relationship.taxpayer, taxpayer_residence.residents),
                residence.household == taxpayer_residence.household,
                CalendarYear.days_within(
                    year,
                    Period.intersect(
                        Period.intersect(relationship.period, residence.period),
                        taxpayer_residence.period,
                    ),
                )
                >= year.half_length,
            )
        )


@dataclass
class AgeRequirementTest(Provision[AgeRequirement]):
    """
    `§ 152(c)(3) <https://www.law.cornell.edu/uscode/text/26/152#c_3>`__: an individual younger than the taxpayer, or with no stated birth and a
    descendant of theirs, who is less than 25 years old at the close of the year.

    As in SARA, the day an individual becomes a child of a parent counts as a birthday.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.AGE_REQUIREMENT`.
        """
        return SaraPredicate.AGE_REQUIREMENT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    @classproperty
    def age_limit(cls) -> int:
        """
        The years an individual has to be younger than.
        """
        return 25

    def query(self) -> Query:
        individual = variable(Party, domain=self.world.parties)
        taxpayer = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        birth = variable(Birth, domain=self.world.births)
        any_birth = variable(Birth, domain=self.world.births)
        taxpayer_birth = variable(Birth, domain=self.world.births)
        birthday = variable(Birth, domain=self.birthdays())
        descendant = variable(
            DescendantRelationship,
            domain=DescendantRelation(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(AgeRequirement)(
                    individual=individual, taxpayer=taxpayer, year=year.number
                )
            ).where(
                or_(
                    exists(
                        birth,
                        and_(
                            birth.person == individual,
                            exists(
                                taxpayer_birth,
                                and_(
                                    taxpayer_birth.person == taxpayer,
                                    taxpayer_birth.day <= birth.day,
                                ),
                            ),
                        ),
                    ),
                    and_(
                        not_(exists(any_birth, any_birth.person == individual)),
                        exists(
                            descendant,
                            and_(
                                descendant.relative == individual,
                                descendant.person == taxpayer,
                            ),
                        ),
                    ),
                ),
                exists(
                    birthday,
                    and_(
                        birthday.person == individual,
                        CalendarYear.days_lived_by_close(year, birthday.day)
                        <= CalendarYear.days_of_years_after_close(year, self.age_limit),
                    ),
                ),
            )
        )

    def birthdays(self) -> list[Birth]:
        """:return: The stated births, and a birth on the first day of each stated relation of a child to a parent."""
        return self.world.births + [
            Birth(person=kinship.child, day=kinship.period.start)
            for kinship in self.world.kinships
            if kinship.period.start is not None
        ]


@dataclass
class AgeRequirementOfQualifyingChildTest(Provision[AgeRequirementOfQualifyingChild]):
    """
    `§ 152(c)(1)(C) <https://www.law.cornell.edu/uscode/text/26/152#c_1_C>`__: an individual meeting the age requirements of `§ 152(c)(3) <https://www.law.cornell.edu/uscode/text/26/152#c_3>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.AGE_REQUIREMENT_OF_QUALIFYING_CHILD`.
        """
        return SaraPredicate.AGE_REQUIREMENT_OF_QUALIFYING_CHILD

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        age = variable(
            AgeRequirement, domain=AgeRequirementTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(AgeRequirementOfQualifyingChild)(
                    individual=age.individual, taxpayer=age.taxpayer, year=age.year
                )
            )
        )


@dataclass
class NoJointReturnTest(Provision[NoJointReturn]):
    """
    `§ 152(c)(1)(E) <https://www.law.cornell.edu/uscode/text/26/152#c_1_E>`__: an individual who made no joint return with their spouse for the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.NO_JOINT_RETURN`.
        """
        return SaraPredicate.NO_JOINT_RETURN

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        individual = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        filing = variable(
            JointFiling, domain=JointFilingTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(NoJointReturn)(individual=individual, year=year.number)
            ).where(
                not_(
                    exists(
                        filing,
                        and_(
                            filing.individual == individual,
                            filing.year == year.number,
                        ),
                    )
                )
            )
        )


# %% qualifying child


@dataclass
class QualifyingChildUnderGeneralRuleTest(Provision[QualifyingChildUnderGeneralRule]):
    """
    `§ 152(c)(1) <https://www.law.cornell.edu/uscode/text/26/152#c_1>`__: an individual bearing a relationship to the taxpayer `(A) <https://www.law.cornell.edu/uscode/text/26/152#c_1_A>`__, sharing their
    abode for half the year within it `(B) <https://www.law.cornell.edu/uscode/text/26/152#c_1_B>`__, meeting the age requirements `(C) <https://www.law.cornell.edu/uscode/text/26/152#c_1_C>`__ and making no joint
    return `(E) <https://www.law.cornell.edu/uscode/text/26/152#c_1_E>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.QUALIFYING_CHILD_UNDER_GENERAL_RULE`.
        """
        return SaraPredicate.QUALIFYING_CHILD_UNDER_GENERAL_RULE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        abode = variable(
            SharedAbode, domain=SharedAbodeTest(world=self.world).conclusions
        )
        age = variable(
            AgeRequirementOfQualifyingChild,
            domain=AgeRequirementOfQualifyingChildTest(world=self.world).conclusions,
        )
        no_joint_return = variable(
            NoJointReturn, domain=NoJointReturnTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(QualifyingChildUnderGeneralRule)(
                    individual=abode.individual,
                    taxpayer=abode.taxpayer,
                    year=abode.year,
                )
            ).where(
                exists(
                    age,
                    and_(
                        age.individual == abode.individual,
                        age.taxpayer == abode.taxpayer,
                        age.year == abode.year,
                    ),
                ),
                exists(
                    no_joint_return,
                    and_(
                        no_joint_return.individual == abode.individual,
                        no_joint_return.year == abode.year,
                    ),
                ),
            )
        )


@dataclass
class QualifyingChildTest(Provision[QualifyingChild]):
    """
    `§ 152(c) <https://www.law.cornell.edu/uscode/text/26/152#c>`__: a qualifying child under `(1) <https://www.law.cornell.edu/uscode/text/26/152#c_1>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.QUALIFYING_CHILD`.
        """
        return SaraPredicate.QUALIFYING_CHILD

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        child = variable(
            QualifyingChildUnderGeneralRule,
            domain=QualifyingChildUnderGeneralRuleTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(QualifyingChild)(
                    individual=child.individual,
                    taxpayer=child.taxpayer,
                    year=child.year,
                )
            )
        )


# %% relationships of a qualifying relative


@dataclass
class ChildOrDescendantTest(Provision[ChildOrDescendantRelationship]):
    """
    `§ 152(d)(2)(A) <https://www.law.cornell.edu/uscode/text/26/152#d_2_A>`__: a child of the taxpayer or a descendant of a child.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.CHILD_OR_DESCENDANT`.
        """
        return SaraPredicate.CHILD_OR_DESCENDANT

    def query(self) -> Query:
        relationship = variable(
            ChildOrDescendantOfChildRelationship,
            domain=ChildOrDescendantOfChildTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(ChildOrDescendantRelationship)(
                    individual=relationship.individual,
                    taxpayer=relationship.taxpayer,
                    period=relationship.period,
                )
            )
        )


@dataclass
class AncestorTest(Provision[AncestorRelationship]):
    """
    `§ 152(d)(2)(C) <https://www.law.cornell.edu/uscode/text/26/152#d_2_C>`__: the father or mother of the taxpayer, or an ancestor of either.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.ANCESTOR`.
        """
        return SaraPredicate.ANCESTOR

    def query(self) -> Query:
        descendant = variable(
            DescendantRelationship,
            domain=DescendantRelation(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(AncestorRelationship)(
                    individual=descendant.person,
                    taxpayer=descendant.relative,
                    period=descendant.period,
                )
            )
        )


@dataclass
class StepparentOfTaxpayerTest(Provision[StepparentOfTaxpayerRelationship]):
    """
    `§ 152(d)(2)(D) <https://www.law.cornell.edu/uscode/text/26/152#d_2_D>`__: a stepfather or stepmother of the taxpayer.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.STEPPARENT_OF_TAXPAYER`.
        """
        return SaraPredicate.STEPPARENT_OF_TAXPAYER

    def query(self) -> Query:
        stepparent = variable(
            StepparentRelationship,
            domain=StepparentRelation(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(StepparentOfTaxpayerRelationship)(
                    individual=stepparent.relative,
                    taxpayer=stepparent.person,
                    period=stepparent.period,
                )
            )
        )


@dataclass
class NephewOrNieceTest(Provision[NephewOrNieceRelationship]):
    """
    `§ 152(d)(2)(E) <https://www.law.cornell.edu/uscode/text/26/152#d_2_E>`__: a son or daughter of a brother or sister of the taxpayer, for the days
    both relations last.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.NEPHEW_OR_NIECE`.
        """
        return SaraPredicate.NEPHEW_OR_NIECE

    def query(self) -> Query:
        sibling = variable(
            SiblingRelationship, domain=SiblingRelation(world=self.world).conclusions
        )
        child = variable(
            ChildRelationship, domain=ChildRelation(world=self.world).conclusions
        )
        return an(
            entity(
                inference(NephewOrNieceRelationship)(
                    individual=child.relative,
                    taxpayer=sibling.relative,
                    relative=sibling.person,
                    period=Period.intersect(sibling.period, child.period),
                )
            ).where(child.person == sibling.person)
        )


@dataclass
class UncleOrAuntTest(Provision[UncleOrAuntRelationship]):
    """
    `§ 152(d)(2)(F) <https://www.law.cornell.edu/uscode/text/26/152#d_2_F>`__: a brother or sister of the father or mother of the taxpayer, for the
    days both relations last.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.UNCLE_OR_AUNT`.
        """
        return SaraPredicate.UNCLE_OR_AUNT

    def query(self) -> Query:
        child = variable(
            ChildRelationship, domain=ChildRelation(world=self.world).conclusions
        )
        sibling = variable(
            SiblingRelationship, domain=SiblingRelation(world=self.world).conclusions
        )
        return an(
            entity(
                inference(UncleOrAuntRelationship)(
                    individual=sibling.person,
                    taxpayer=child.relative,
                    relative=child.person,
                    period=Period.intersect(sibling.period, child.period),
                )
            ).where(sibling.relative == child.person)
        )


@dataclass
class InLawTest(Provision[InLawRelationship]):
    """
    `§ 152(d)(2)(G) <https://www.law.cornell.edu/uscode/text/26/152#d_2_G>`__: a son-, daughter-, father-, mother-, brother- or sister-in-law of the
    taxpayer.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.IN_LAW`.
        """
        return SaraPredicate.IN_LAW

    def query(self) -> Query:
        in_law = variable(
            Relationship,
            domain=ChildInLawRelation(world=self.world).conclusions
            + ParentInLawRelation(world=self.world).conclusions
            + SiblingInLawRelation(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(InLawRelationship)(
                    individual=in_law.relative,
                    taxpayer=in_law.person,
                    period=in_law.period,
                )
            )
        )


@dataclass
class HouseholdMemberTest(Provision[HouseholdMemberRelationship]):
    """
    `§ 152(d)(2)(H) <https://www.law.cornell.edu/uscode/text/26/152#d_2_H>`__: an individual, never the taxpayer's spouse during the year, who lives
    in the taxpayer's household the whole year, as the taxpayer does.

    As in SARA, only a marriage whose start is stated makes a spouse.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HOUSEHOLD_MEMBER`.
        """
        return SaraPredicate.HOUSEHOLD_MEMBER

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        residences = [
            residence
            for residence in self.world.residences
            if residence.period.start is not None
        ]
        residence = variable(Residence, domain=residences)
        taxpayer_residence = variable(Residence, domain=residences)
        individual = variable(Party, domain=self.world.parties)
        taxpayer = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        marriage = variable(
            Marriage,
            domain=[
                marriage
                for marriage in self.world.marriages
                if marriage.period.start is not None
            ],
        )
        return an(
            entity(
                inference(HouseholdMemberRelationship)(
                    individual=individual,
                    taxpayer=taxpayer,
                    year=year.number,
                    household=residence.household,
                    period=Period.intersect(
                        taxpayer_residence.period, residence.period
                    ),
                )
            ).where(
                individual != taxpayer,
                in_(individual, residence.residents),
                in_(taxpayer, taxpayer_residence.residents),
                residence.household == taxpayer_residence.household,
                residence.period.start <= year.opening_day,
                taxpayer_residence.period.start <= year.opening_day,
                or_(
                    residence.period.end == None,
                    residence.period.end >= year.closing_day,
                ),
                or_(
                    taxpayer_residence.period.end == None,
                    taxpayer_residence.period.end >= year.closing_day,
                ),
                not_(
                    exists(
                        marriage,
                        and_(
                            in_(individual, marriage.spouses),
                            in_(taxpayer, marriage.spouses),
                            marriage.period.start <= year.closing_day,
                            or_(
                                marriage.period.end == None,
                                marriage.period.end >= year.opening_day,
                            ),
                        ),
                    )
                ),
            )
        )


@dataclass
class QualifyingRelativeRelationshipTest(Provision[QualifyingRelativeRelationship]):
    """
    `§ 152(d)(2) <https://www.law.cornell.edu/uscode/text/26/152#d_2>`__: an individual bearing a relationship of `(A) <https://www.law.cornell.edu/uscode/text/26/152#d_2_A>`__ through `(H) <https://www.law.cornell.edu/uscode/text/26/152#d_2_H>`__ to the taxpayer.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.QUALIFYING_RELATIVE_RELATIONSHIP`.
        """
        return SaraPredicate.QUALIFYING_RELATIVE_RELATIONSHIP

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        relationship = variable(
            RelationshipToTaxpayer, domain=self.relationships_regardless_of_year()
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        member = variable(
            HouseholdMemberRelationship,
            domain=HouseholdMemberTest(world=self.world).conclusions,
        )
        relationship_in_year = variable(
            QualifyingRelativeRelationship,
            domain=an(
                entity(
                    inference(QualifyingRelativeRelationship)(
                        individual=relationship.individual,
                        taxpayer=relationship.taxpayer,
                        year=year.number,
                        period=relationship.period,
                    )
                )
            ).tolist()
            + an(
                entity(
                    inference(QualifyingRelativeRelationship)(
                        individual=member.individual,
                        taxpayer=member.taxpayer,
                        year=member.year,
                        period=member.period,
                    )
                )
            ).tolist(),
        )
        return an(entity(relationship_in_year))

    def relationships_regardless_of_year(self) -> list[RelationshipToTaxpayer]:
        """:return: The relationships of `(A) <https://www.law.cornell.edu/uscode/text/26/152#d_2_A>`__ through `(G) <https://www.law.cornell.edu/uscode/text/26/152#d_2_G>`__, which do not depend on the year."""
        return [
            relationship
            for test in (
                ChildOrDescendantTest,
                SiblingOrStepsiblingTest,
                AncestorTest,
                StepparentOfTaxpayerTest,
                NephewOrNieceTest,
                UncleOrAuntTest,
                InLawTest,
            )
            for relationship in test(world=self.world).conclusions
        ]


@dataclass
class QualifyingRelativeRelationshipUntilDeathTest(
    Provision[QualifyingRelativeRelationshipUntilDeath]
):
    """
    `§ 152(d)(1)(A) <https://www.law.cornell.edu/uscode/text/26/152#d_1_A>`__: a relationship of `§ 152(d)(2) <https://www.law.cornell.edu/uscode/text/26/152#d_2>`__, ending at the latest when either the
    individual or the taxpayer dies.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.QUALIFYING_RELATIVE_RELATIONSHIP_UNTIL_DEATH`.
        """
        return SaraPredicate.QUALIFYING_RELATIVE_RELATIONSHIP_UNTIL_DEATH

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        relationship = variable(
            QualifyingRelativeRelationship,
            domain=QualifyingRelativeRelationshipTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(QualifyingRelativeRelationshipUntilDeath)(
                    individual=relationship.individual,
                    taxpayer=relationship.taxpayer,
                    year=relationship.year,
                    period=Period.intersect(
                        Period.intersect(
                            relationship.period,
                            World.lifetime(self.world, relationship.taxpayer),
                        ),
                        World.lifetime(self.world, relationship.individual),
                    ),
                )
            )
        )


@dataclass
class NoGrossIncomeTest(Provision[NoGrossIncome]):
    """
    `§ 152(d)(1)(B) <https://www.law.cornell.edu/uscode/text/26/152#d_1_B>`__: an individual with no gross income for the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.NO_GROSS_INCOME`.
        """
        return SaraPredicate.NO_GROSS_INCOME

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        individual = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        income = variable(
            GrossIncome, domain=GrossIncomeOfParty(world=self.world).conclusions
        )
        return an(
            entity(
                inference(NoGrossIncome)(individual=individual, year=year.number)
            ).where(
                not_(
                    exists(
                        income,
                        and_(
                            income.person == individual,
                            income.year == year.number,
                            income.amount != 0,
                        ),
                    )
                )
            )
        )


@dataclass
class NoQualifyingChildTest(Provision[NoQualifyingChild]):
    """
    `§ 152(d)(1)(D) <https://www.law.cornell.edu/uscode/text/26/152#d_1_D>`__: an individual who is no qualifying child of any taxpayer for the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.NO_QUALIFYING_CHILD`.
        """
        return SaraPredicate.NO_QUALIFYING_CHILD

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        individual = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        child = variable(
            QualifyingChild, domain=QualifyingChildTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(NoQualifyingChild)(individual=individual, year=year.number)
            ).where(
                not_(
                    exists(
                        child,
                        and_(child.individual == individual, child.year == year.number),
                    )
                )
            )
        )


# %% qualifying relative


@dataclass
class QualifyingRelativeUnderGeneralRuleTest(
    Provision[QualifyingRelativeUnderGeneralRule]
):
    """
    `§ 152(d)(1) <https://www.law.cornell.edu/uscode/text/26/152#d_1>`__: an individual bearing a relationship to the taxpayer `(A) <https://www.law.cornell.edu/uscode/text/26/152#d_1_A>`__ with no gross
    income `(B) <https://www.law.cornell.edu/uscode/text/26/152#d_1_B>`__ who is no qualifying child of anyone `(D) <https://www.law.cornell.edu/uscode/text/26/152#d_1_D>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.QUALIFYING_RELATIVE_UNDER_GENERAL_RULE`.
        """
        return SaraPredicate.QUALIFYING_RELATIVE_UNDER_GENERAL_RULE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        relationship = variable(
            QualifyingRelativeRelationshipUntilDeath,
            domain=QualifyingRelativeRelationshipUntilDeathTest(
                world=self.world
            ).conclusions,
        )
        no_income = variable(
            NoGrossIncome, domain=NoGrossIncomeTest(world=self.world).conclusions
        )
        no_child = variable(
            NoQualifyingChild,
            domain=NoQualifyingChildTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(QualifyingRelativeUnderGeneralRule)(
                    individual=relationship.individual,
                    taxpayer=relationship.taxpayer,
                    year=relationship.year,
                    period=relationship.period,
                )
            ).where(
                exists(
                    no_income,
                    and_(
                        no_income.individual == relationship.individual,
                        no_income.year == relationship.year,
                    ),
                ),
                exists(
                    no_child,
                    and_(
                        no_child.individual == relationship.individual,
                        no_child.year == relationship.year,
                    ),
                ),
            )
        )


@dataclass
class QualifyingRelativeTest(Provision[QualifyingRelative]):
    """
    `§ 152(d) <https://www.law.cornell.edu/uscode/text/26/152#d>`__: a qualifying relative under `(1) <https://www.law.cornell.edu/uscode/text/26/152#d_1>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.QUALIFYING_RELATIVE`.
        """
        return SaraPredicate.QUALIFYING_RELATIVE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        relative = variable(
            QualifyingRelativeUnderGeneralRule,
            domain=QualifyingRelativeUnderGeneralRuleTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(QualifyingRelative)(
                    individual=relative.individual,
                    taxpayer=relative.taxpayer,
                    year=relative.year,
                    period=relative.period,
                )
            )
        )


# %% dependents


@dataclass
class QualifyingChildDependentTest(Provision[QualifyingChildDependent]):
    """
    `§ 152(a)(1) <https://www.law.cornell.edu/uscode/text/26/152#a_1>`__: a qualifying child.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.QUALIFYING_CHILD_DEPENDENT`.
        """
        return SaraPredicate.QUALIFYING_CHILD_DEPENDENT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        child = variable(
            QualifyingChild, domain=QualifyingChildTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(QualifyingChildDependent)(
                    individual=child.individual,
                    taxpayer=child.taxpayer,
                    year=child.year,
                )
            )
        )


@dataclass
class QualifyingRelativeDependentTest(Provision[QualifyingRelativeDependent]):
    """
    `§ 152(a)(2) <https://www.law.cornell.edu/uscode/text/26/152#a_2>`__: a qualifying relative.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.QUALIFYING_RELATIVE_DEPENDENT`.
        """
        return SaraPredicate.QUALIFYING_RELATIVE_DEPENDENT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        relative = variable(
            QualifyingRelative,
            domain=QualifyingRelativeTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(QualifyingRelativeDependent)(
                    individual=relative.individual,
                    taxpayer=relative.taxpayer,
                    year=relative.year,
                    period=relative.period,
                )
            )
        )


@dataclass
class DependentUnderDefinitionTest(Provision[DependentUnderDefinition]):
    """
    `§ 152(a) <https://www.law.cornell.edu/uscode/text/26/152#a>`__: a qualifying child `(1) <https://www.law.cornell.edu/uscode/text/26/152#a_1>`__, for no days in particular, or a qualifying relative
    `(2) <https://www.law.cornell.edu/uscode/text/26/152#a_2>`__, for the days of their relationship.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.DEPENDENT_UNDER_DEFINITION`.
        """
        return SaraPredicate.DEPENDENT_UNDER_DEFINITION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        child = variable(
            QualifyingChildDependent,
            domain=QualifyingChildDependentTest(world=self.world).conclusions,
        )
        relative = variable(
            QualifyingRelativeDependent,
            domain=QualifyingRelativeDependentTest(world=self.world).conclusions,
        )
        dependent = variable(
            DependentUnderDefinition,
            domain=an(
                entity(
                    inference(DependentUnderDefinition)(
                        individual=child.individual,
                        taxpayer=child.taxpayer,
                        year=child.year,
                    )
                )
            ).tolist()
            + an(
                entity(
                    inference(DependentUnderDefinition)(
                        individual=relative.individual,
                        taxpayer=relative.taxpayer,
                        year=relative.year,
                        period=relative.period,
                    )
                )
            ).tolist(),
        )
        return an(entity(dependent))


@dataclass
class DependentTest(Provision[Dependent]):
    """
    `§ 152 <https://www.law.cornell.edu/uscode/text/26/152>`__: a dependent under `(a) <https://www.law.cornell.edu/uscode/text/26/152#a>`__ who made no joint return `(b)(2) <https://www.law.cornell.edu/uscode/text/26/152#b_2>`__, of a taxpayer
    who is no such dependent of anyone themself `(b)(1) <https://www.law.cornell.edu/uscode/text/26/152#b_1>`__.

    SARA's program asks `(b)(1) <https://www.law.cornell.edu/uscode/text/26/152#b_1>`__ of the taxpayer recursively; krrood queries do not recurse, so
    it is asked one level deep, which differs only for chains of three dependents.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.DEPENDENT`.
        """
        return SaraPredicate.DEPENDENT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        candidate = variable(DependentCandidate, domain=self.candidates())
        taxpayer_as_candidate = variable(DependentCandidate, domain=self.candidates())
        return an(
            entity(
                inference(Dependent)(
                    individual=candidate.individual,
                    taxpayer=candidate.taxpayer,
                    year=candidate.year,
                )
            ).where(
                not_(
                    exists(
                        taxpayer_as_candidate,
                        and_(
                            taxpayer_as_candidate.individual == candidate.taxpayer,
                            taxpayer_as_candidate.year == candidate.year,
                        ),
                    )
                )
            )
        )

    def candidates(self) -> list[DependentCandidate]:
        """:return: The dependents under `(a) <https://www.law.cornell.edu/uscode/text/26/152#a>`__ who made no joint return, `(b)(1) <https://www.law.cornell.edu/uscode/text/26/152#b_1>`__ aside."""
        dependent = variable(
            DependentUnderDefinition,
            domain=DependentUnderDefinitionTest(world=self.world).conclusions,
        )
        filing = variable(
            JointFiling, domain=JointFilingTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(DependentCandidate)(
                    individual=dependent.individual,
                    taxpayer=dependent.taxpayer,
                    year=dependent.year,
                )
            ).where(
                dependent.individual != dependent.taxpayer,
                not_(
                    exists(
                        filing,
                        and_(
                            filing.individual == dependent.individual,
                            filing.year == dependent.year,
                        ),
                    )
                ),
            )
        ).tolist()


@dataclass
class DependentOfOtherTaxpayerTest(Provision[DependentOfOtherTaxpayer]):
    """
    `§ 152(b)(1) <https://www.law.cornell.edu/uscode/text/26/152#b_1>`__: a taxpayer who is a dependent of another for the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.DEPENDENT_OF_OTHER_TAXPAYER`.
        """
        return SaraPredicate.DEPENDENT_OF_OTHER_TAXPAYER

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        dependent = variable(
            Dependent, domain=DependentTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(DependentOfOtherTaxpayer)(
                    taxpayer=dependent.individual,
                    other_taxpayer=dependent.taxpayer,
                    year=dependent.year,
                )
            )
        )


@dataclass
class DependencyExceptionTest(Provision[DependencyException]):
    """
    `§ 152(b) <https://www.law.cornell.edu/uscode/text/26/152#b>`__: a taxpayer who is a dependent `(1) <https://www.law.cornell.edu/uscode/text/26/152#b_1>`__, or an individual who made a joint
    return `(2) <https://www.law.cornell.edu/uscode/text/26/152#b_2>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.DEPENDENCY_EXCEPTION`.
        """
        return SaraPredicate.DEPENDENCY_EXCEPTION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        individual = variable(Party, domain=self.world.parties)
        taxpayer = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        dependent_taxpayer = variable(
            DependentOfOtherTaxpayer,
            domain=DependentOfOtherTaxpayerTest(world=self.world).conclusions,
        )
        filing = variable(
            JointFiling, domain=JointFilingTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(DependencyException)(
                    individual=individual, taxpayer=taxpayer, year=year.number
                )
            ).where(
                or_(
                    exists(
                        dependent_taxpayer,
                        and_(
                            dependent_taxpayer.taxpayer == taxpayer,
                            dependent_taxpayer.year == year.number,
                        ),
                    ),
                    exists(
                        filing,
                        and_(
                            filing.individual == individual, filing.year == year.number
                        ),
                    ),
                )
            )
        )


# %% exemptions allowed for dependents and spouses


@dataclass
class ExemptionForDependentTest(Provision[ExemptionForDependent]):
    """
    `§ 151(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__: a taxpayer allowed an exemption for each of their dependents.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.EXEMPTION_FOR_DEPENDENT`.
        """
        return SaraPredicate.EXEMPTION_FOR_DEPENDENT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        dependent = variable(
            Dependent, domain=DependentTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(ExemptionForDependent)(
                    individual=dependent.individual,
                    taxpayer=dependent.taxpayer,
                    year=dependent.year,
                )
            )
        )


@dataclass
class ExemptionForSpouseTest(Provision[ExemptionForSpouse]):
    """
    `§ 151(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__: a married taxpayer making no joint return, allowed an exemption for their
    spouse, who has no gross income and is no dependent.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.EXEMPTION_FOR_SPOUSE`.
        """
        return SaraPredicate.EXEMPTION_FOR_SPOUSE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        married = variable(
            MarriedIndividual,
            domain=MarriedIndividualTest(world=self.world).separate_filers(),
        )
        dependent = variable(
            Dependent, domain=DependentTest(world=self.world).conclusions
        )
        no_income = variable(
            NoGrossIncome, domain=NoGrossIncomeTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(ExemptionForSpouse)(
                    individual=married.spouse,
                    taxpayer=married.person,
                    year=married.year,
                )
            ).where(
                not_(
                    exists(
                        dependent,
                        and_(
                            dependent.individual == married.spouse,
                            dependent.year == married.year,
                        ),
                    )
                ),
                exists(
                    no_income,
                    and_(
                        no_income.individual == married.spouse,
                        no_income.year == married.year,
                    ),
                ),
            )
        )


# %% surviving spouse


@dataclass
class DeceasedSpouseTest(Provision[DeceasedSpouse]):
    """
    `§ 2(a)(1)(A) <https://www.law.cornell.edu/uscode/text/26/2#a_1_A>`__: a taxpayer whose spouse died, married to them, during either of the two
    years before the calendar year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.DECEASED_SPOUSE`.
        """
        return SaraPredicate.DECEASED_SPOUSE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fifth argument.
        """
        return 4

    def query(self) -> Query:
        marriage = variable(
            Marriage,
            domain=[
                marriage
                for marriage in self.world.marriages
                if marriage.period.start is not None
            ],
        )
        taxpayer = variable(Party, domain=self.world.parties)
        death = variable(
            Death, domain=[death for death in self.world.deaths if death.day]
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(DeceasedSpouse)(
                    taxpayer=taxpayer,
                    spouse=death.person,
                    marriage=marriage,
                    year_of_death=death.day.year,
                    year=year.number,
                )
            ).where(
                in_(taxpayer, marriage.spouses),
                in_(death.person, marriage.spouses),
                taxpayer != death.person,
                marriage.period.start <= death.day,
                or_(marriage.period.end == None, death.day <= marriage.period.end),
                death.day >= year.opening_day_of_year_before_preceding,
                death.day <= year.closing_day_of_preceding_year,
            )
        )


@dataclass
class HomeForDependentChildTest(Provision[HomeForDependentChild]):
    """
    `§ 2(a)(1)(B) <https://www.law.cornell.edu/uscode/text/26/2#a_1_B>`__: a taxpayer maintaining, all year, the home of a son, stepson, daughter or
    stepdaughter they are allowed an exemption for under `§ 151(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HOME_FOR_DEPENDENT_CHILD`.
        """
        return SaraPredicate.HOME_FOR_DEPENDENT_CHILD

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        exemption = variable(
            ExemptionForDependent,
            domain=ExemptionForDependentTest(world=self.world).conclusions,
        )
        maintenance = variable(
            HouseholdMaintenance,
            domain=HouseholdMaintenanceTest(world=self.world).conclusions,
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        residences = [
            residence
            for residence in self.world.residences
            if residence.period.start is not None
        ]
        residence = variable(Residence, domain=residences)
        taxpayer_residence = variable(Residence, domain=residences)
        child = variable(
            ChildRelationship, domain=ChildRelation(world=self.world).conclusions
        )
        stepparent = variable(
            StepparentRelationship,
            domain=StepparentRelation(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(HomeForDependentChild)(
                    taxpayer=exemption.taxpayer,
                    household=maintenance.household,
                    individual=exemption.individual,
                    year=exemption.year,
                )
            ).where(
                year.number == exemption.year,
                maintenance.person == exemption.taxpayer,
                maintenance.year == exemption.year,
                in_(exemption.taxpayer, taxpayer_residence.residents),
                in_(exemption.individual, residence.residents),
                taxpayer_residence.household == maintenance.household,
                residence.household == maintenance.household,
                taxpayer_residence.period.start <= year.opening_day,
                residence.period.start <= year.opening_day,
                or_(
                    taxpayer_residence.period.end == None,
                    taxpayer_residence.period.end >= year.closing_day,
                ),
                or_(
                    residence.period.end == None,
                    residence.period.end >= year.closing_day,
                ),
                or_(
                    exists(
                        child,
                        and_(
                            child.relative == exemption.individual,
                            child.person == exemption.taxpayer,
                            or_(
                                child.period.start == None,
                                child.period.start <= year.opening_day,
                            ),
                            or_(
                                child.period.end == None,
                                child.period.end >= year.closing_day,
                            ),
                        ),
                    ),
                    exists(
                        stepparent,
                        and_(
                            stepparent.relative == exemption.taxpayer,
                            stepparent.person == exemption.individual,
                            or_(
                                stepparent.period.start == None,
                                stepparent.period.start <= year.opening_day,
                            ),
                            or_(
                                stepparent.period.end == None,
                                stepparent.period.end >= year.closing_day,
                            ),
                        ),
                    ),
                ),
            )
        )


@dataclass
class SurvivingSpouseUnderGeneralRuleTest(Provision[SurvivingSpouseUnderGeneralRule]):
    """
    `§ 2(a)(1) <https://www.law.cornell.edu/uscode/text/26/2#a_1>`__: a taxpayer meeting both `(A) <https://www.law.cornell.edu/uscode/text/26/2#a_1_A>`__ and `(B) <https://www.law.cornell.edu/uscode/text/26/2#a_1_B>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SURVIVING_SPOUSE_UNDER_GENERAL_RULE`.
        """
        return SaraPredicate.SURVIVING_SPOUSE_UNDER_GENERAL_RULE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The sixth argument.
        """
        return 5

    def query(self) -> Query:
        deceased_spouse = variable(
            DeceasedSpouse, domain=DeceasedSpouseTest(world=self.world).conclusions
        )
        home = variable(
            HomeForDependentChild,
            domain=HomeForDependentChildTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(SurvivingSpouseUnderGeneralRule)(
                    deceased_spouse=deceased_spouse, home=home
                )
            ).where(
                home.taxpayer == deceased_spouse.taxpayer,
                home.year == deceased_spouse.year,
            )
        )


@dataclass
class RemarriedTaxpayerTest(Provision[RemarriedTaxpayer]):
    """
    `§ 2(a)(2)(A) <https://www.law.cornell.edu/uscode/text/26/2#a_2_A>`__: a taxpayer who married again, after an earlier marriage, before the
    close of the calendar year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.REMARRIED_TAXPAYER`.
        """
        return SaraPredicate.REMARRIED_TAXPAYER

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fifth argument.
        """
        return 4

    def query(self) -> Query:
        marriages = [
            marriage
            for marriage in self.world.marriages
            if marriage.period.start is not None
        ]
        previous_marriage = variable(Marriage, domain=marriages)
        remarriage = variable(Marriage, domain=marriages)
        taxpayer = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(RemarriedTaxpayer)(
                    taxpayer=taxpayer,
                    remarriage=remarriage,
                    previous_marriage=previous_marriage,
                    year=year.number,
                )
            ).where(
                in_(taxpayer, previous_marriage.spouses),
                in_(taxpayer, remarriage.spouses),
                remarriage != previous_marriage,
                previous_marriage.period.start <= remarriage.period.start,
                remarriage.period.start <= year.closing_day,
            )
        )


@dataclass
class SpousesWithoutNonresidentAlienTest(Provision[SpousesWithoutNonresidentAlien]):
    """
    `§ 2(a)(2)(B) <https://www.law.cornell.edu/uscode/text/26/2#a_2_B>`__: a taxpayer and their spouse, neither of whom is a nonresident alien at
    any time during the year, so that they could have made a joint return.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SPOUSES_WITHOUT_NONRESIDENT_ALIEN`.
        """
        return SaraPredicate.SPOUSES_WITHOUT_NONRESIDENT_ALIEN

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        marriage = variable(Marriage, domain=self.world.marriages)
        taxpayer = variable(Party, domain=self.world.parties)
        spouse = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        status = variable(
            NonresidentAlienStatus, domain=self.world.nonresident_alien_statuses
        )
        return an(
            entity(
                inference(SpousesWithoutNonresidentAlien)(
                    taxpayer=taxpayer, spouse=spouse, year=year.number
                )
            ).where(
                in_(taxpayer, marriage.spouses),
                in_(spouse, marriage.spouses),
                taxpayer != spouse,
                not_(
                    exists(
                        status,
                        and_(
                            or_(status.person == taxpayer, status.person == spouse),
                            or_(
                                status.period.start == None,
                                status.period.start <= year.closing_day,
                            ),
                            or_(
                                status.period.end == None,
                                status.period.end >= year.opening_day,
                            ),
                        ),
                    )
                ),
            )
        )


@dataclass
class SurvivingSpouseTest(Provision[SurvivingSpouse]):
    """
    `§ 2(a) <https://www.law.cornell.edu/uscode/text/26/2#a>`__: a surviving spouse under `(1) <https://www.law.cornell.edu/uscode/text/26/2#a_1>`__ who neither remarried `(2)(A) <https://www.law.cornell.edu/uscode/text/26/2#a_2_A>`__ nor could not
    have made a joint return `(2)(B) <https://www.law.cornell.edu/uscode/text/26/2#a_2_B>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SURVIVING_SPOUSE`.
        """
        return SaraPredicate.SURVIVING_SPOUSE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        survivor = variable(
            SurvivingSpouseUnderGeneralRule,
            domain=SurvivingSpouseUnderGeneralRuleTest(world=self.world).conclusions,
        )
        remarried = variable(
            RemarriedTaxpayer,
            domain=RemarriedTaxpayerTest(world=self.world).conclusions,
        )
        could_file_jointly = variable(
            SpousesWithoutNonresidentAlien,
            domain=SpousesWithoutNonresidentAlienTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(SurvivingSpouse)(
                    taxpayer=survivor.deceased_spouse.taxpayer,
                    spouse=survivor.deceased_spouse.spouse,
                    year=survivor.deceased_spouse.year,
                )
            ).where(
                not_(
                    exists(
                        remarried,
                        and_(
                            remarried.taxpayer == survivor.deceased_spouse.taxpayer,
                            remarried.previous_marriage
                            == survivor.deceased_spouse.marriage,
                            remarried.year == survivor.deceased_spouse.year,
                        ),
                    )
                ),
                exists(
                    could_file_jointly,
                    and_(
                        could_file_jointly.taxpayer
                        == survivor.deceased_spouse.taxpayer,
                        could_file_jointly.spouse == survivor.deceased_spouse.spouse,
                        could_file_jointly.year == survivor.deceased_spouse.year,
                    ),
                ),
            )
        )


# %% status of the head of household


@dataclass
class SeparatedForHeadOfHouseholdTest(Provision[SeparatedForHeadOfHousehold]):
    """
    `§ 2(b)(2)(A) <https://www.law.cornell.edu/uscode/text/26/2#b_2_A>`__: a taxpayer legally separated from their spouse under a decree of divorce
    or of separate maintenance, as under `§ 7703(a)(2) <https://www.law.cornell.edu/uscode/text/26/7703#a_2>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SEPARATED_FOR_HEAD_OF_HOUSEHOLD`.
        """
        return SaraPredicate.SEPARATED_FOR_HEAD_OF_HOUSEHOLD

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fifth argument.
        """
        return 4

    def query(self) -> Query:
        separated = variable(
            LegallySeparatedIndividual,
            domain=LegalSeparationTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(SeparatedForHeadOfHousehold)(
                    separation=separated.separation,
                    taxpayer=separated.person,
                    spouse=separated.spouse,
                    year=separated.year,
                )
            )
        )


@dataclass
class NonresidentAlienSpouseTest(Provision[NonresidentAlienSpouse]):
    """
    `§ 2(b)(2)(B) <https://www.law.cornell.edu/uscode/text/26/2#b_2_B>`__: a taxpayer whose spouse is a nonresident alien at some time during the
    year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.NONRESIDENT_ALIEN_SPOUSE`.
        """
        return SaraPredicate.NONRESIDENT_ALIEN_SPOUSE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        marriage = variable(Marriage, domain=self.world.marriages)
        taxpayer = variable(Party, domain=self.world.parties)
        status = variable(
            NonresidentAlienStatus, domain=self.world.nonresident_alien_statuses
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(NonresidentAlienSpouse)(
                    taxpayer=taxpayer, spouse=status.person, year=year.number
                )
            ).where(
                in_(taxpayer, marriage.spouses),
                in_(status.person, marriage.spouses),
                or_(
                    status.period.start == None, status.period.start <= year.closing_day
                ),
                or_(status.period.end == None, status.period.end >= year.opening_day),
            )
        )


@dataclass
class SpouseDeceasedInYearTest(Provision[SpouseDeceasedInYear]):
    """
    `§ 2(b)(2)(C) <https://www.law.cornell.edu/uscode/text/26/2#b_2_C>`__: a taxpayer whose spouse, no nonresident alien in the year, died married to
    them during it.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SPOUSE_DECEASED_IN_YEAR`.
        """
        return SaraPredicate.SPOUSE_DECEASED_IN_YEAR

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        marriage = variable(Marriage, domain=self.world.marriages)
        taxpayer = variable(Party, domain=self.world.parties)
        death = variable(
            Death, domain=[death for death in self.world.deaths if death.day]
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        nonresident_spouse = variable(
            NonresidentAlienSpouse,
            domain=NonresidentAlienSpouseTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(SpouseDeceasedInYear)(
                    taxpayer=taxpayer,
                    marriage=marriage,
                    spouse=death.person,
                    year=year.number,
                )
            ).where(
                in_(taxpayer, marriage.spouses),
                in_(death.person, marriage.spouses),
                death.day >= year.opening_day,
                death.day <= year.closing_day,
                or_(marriage.period.end == None, death.day <= marriage.period.end),
                not_(
                    exists(
                        nonresident_spouse,
                        and_(
                            nonresident_spouse.taxpayer == taxpayer,
                            nonresident_spouse.spouse == death.person,
                            nonresident_spouse.year == year.number,
                        ),
                    )
                ),
            )
        )


@dataclass
class MarriedChildTest(Provision[MarriedChild]):
    """
    `§ 2(b)(1)(A)(i)(I) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_i_I>`__: an individual married at the close of the year, under `§ 7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.MARRIED_CHILD`.
        """
        return SaraPredicate.MARRIED_CHILD

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        married = variable(
            MarriedIndividual,
            domain=MarriedIndividualTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(MarriedChild)(individual=married.person, year=married.year)
            )
        )


@dataclass
class ChildFilingJointlyTest(Provision[ChildFilingJointly]):
    """
    `§ 2(b)(1)(A)(i)(II) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_i_II>`__: an individual who is no dependent of the taxpayer by reason of
    `§ 152(b)(2) <https://www.law.cornell.edu/uscode/text/26/152#b_2>`__, which SARA's program asks with the taxpayer in the place of the spouse.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.CHILD_FILING_JOINTLY`.
        """
        return SaraPredicate.CHILD_FILING_JOINTLY

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
                inference(ChildFilingJointly)(
                    individual=filing.individual,
                    taxpayer=filing.spouse,
                    year=filing.year,
                )
            )
        )


@dataclass
class QualifyingChildOfHouseholdTest(Provision[QualifyingChildOfHousehold]):
    """
    `§ 2(b)(1)(A)(i) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_i>`__: a qualifying child of the taxpayer, unless married `(I) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_i_I>`__ and no
    dependent by reason of `§ 152(b)(2) <https://www.law.cornell.edu/uscode/text/26/152#b_2>`__ `(II) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_i_II>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.QUALIFYING_CHILD_OF_HOUSEHOLD`.
        """
        return SaraPredicate.QUALIFYING_CHILD_OF_HOUSEHOLD

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        child = variable(
            QualifyingChild, domain=QualifyingChildTest(world=self.world).conclusions
        )
        married = variable(
            MarriedChild, domain=MarriedChildTest(world=self.world).conclusions
        )
        filing = variable(
            ChildFilingJointly,
            domain=ChildFilingJointlyTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(QualifyingChildOfHousehold)(
                    taxpayer=child.taxpayer,
                    individual=child.individual,
                    year=child.year,
                )
            ).where(
                not_(
                    and_(
                        exists(
                            married,
                            and_(
                                married.individual == child.individual,
                                married.year == child.year,
                            ),
                        ),
                        exists(
                            filing,
                            and_(
                                filing.individual == child.individual,
                                filing.taxpayer == child.taxpayer,
                                filing.year == child.year,
                            ),
                        ),
                    )
                )
            )
        )


@dataclass
class DependentOfHouseholdTest(Provision[DependentOfHousehold]):
    """
    `§ 2(b)(1)(A)(ii) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_ii>`__: a dependent of the taxpayer they are allowed an exemption for under
    `§ 151 <https://www.law.cornell.edu/uscode/text/26/151>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.DEPENDENT_OF_HOUSEHOLD`.
        """
        return SaraPredicate.DEPENDENT_OF_HOUSEHOLD

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        dependent = variable(
            Dependent, domain=DependentTest(world=self.world).conclusions
        )
        exemption = variable(
            AnnualDependency,
            domain=ExemptionForSpouseTest(world=self.world).conclusions
            + ExemptionForDependentTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(DependentOfHousehold)(
                    taxpayer=dependent.taxpayer,
                    individual=dependent.individual,
                    year=dependent.year,
                )
            ).where(
                exists(
                    exemption,
                    and_(
                        exemption.taxpayer == dependent.taxpayer,
                        exemption.individual == dependent.individual,
                        exemption.year == dependent.year,
                    ),
                )
            )
        )


@dataclass
class HomeForQualifyingIndividualTest(Provision[HomeForQualifyingIndividual]):
    """
    `§ 2(b)(1)(A) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A>`__: a taxpayer maintaining their home all year as the home, for at least half
    a year, of a qualifying individual of `(i) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_i>`__ or `(ii) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_ii>`__.

    As in SARA, the individual's residence is measured whole, not within the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HOME_FOR_QUALIFYING_INDIVIDUAL`.
        """
        return SaraPredicate.HOME_FOR_QUALIFYING_INDIVIDUAL

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        qualifying = variable(
            HeadOfHousehold,
            domain=QualifyingChildOfHouseholdTest(world=self.world).conclusions
            + DependentOfHouseholdTest(world=self.world).conclusions,
        )
        maintenance = variable(
            HouseholdMaintenance,
            domain=HouseholdMaintenanceTest(world=self.world).conclusions,
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        residence = variable(Residence, domain=self.world.residences)
        taxpayer_residence = variable(Residence, domain=self.world.residences)
        return an(
            entity(
                inference(HomeForQualifyingIndividual)(
                    taxpayer=qualifying.taxpayer,
                    household=maintenance.household,
                    individual=qualifying.individual,
                    year=qualifying.year,
                )
            ).where(
                year.number == qualifying.year,
                maintenance.person == qualifying.taxpayer,
                maintenance.year == qualifying.year,
                in_(qualifying.taxpayer, taxpayer_residence.residents),
                in_(qualifying.individual, residence.residents),
                taxpayer_residence.household == maintenance.household,
                residence.household == maintenance.household,
                or_(
                    taxpayer_residence.period.start == None,
                    taxpayer_residence.period.start <= year.opening_day,
                ),
                or_(
                    taxpayer_residence.period.end == None,
                    taxpayer_residence.period.end >= year.closing_day,
                ),
                CalendarYear.days_spanned(year, residence.period) >= year.half_length,
            )
        )


@dataclass
class HomeForParentTest(Provision[HomeForParent]):
    """
    `§ 2(b)(1)(B) <https://www.law.cornell.edu/uscode/text/26/2#b_1_B>`__: a taxpayer maintaining, all year, the home of their father or mother, whom
    they are allowed an exemption for under `§ 151(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HOME_FOR_PARENT`.
        """
        return SaraPredicate.HOME_FOR_PARENT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fifth argument.
        """
        return 4

    def query(self) -> Query:
        exemption = variable(
            ExemptionForDependent,
            domain=ExemptionForDependentTest(world=self.world).conclusions,
        )
        maintenance = variable(
            HouseholdMaintenance,
            domain=HouseholdMaintenanceTest(world=self.world).conclusions,
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        residence = variable(
            Residence,
            domain=[
                residence
                for residence in self.world.residences
                if residence.period.start is not None
            ],
        )
        child = variable(
            ChildRelationship, domain=ChildRelation(world=self.world).conclusions
        )
        return an(
            entity(
                inference(HomeForParent)(
                    taxpayer=exemption.taxpayer,
                    household=maintenance.household,
                    individual=exemption.individual,
                    year=exemption.year,
                )
            ).where(
                year.number == exemption.year,
                maintenance.person == exemption.taxpayer,
                maintenance.year == exemption.year,
                in_(exemption.individual, residence.residents),
                residence.household == maintenance.household,
                residence.period.start <= year.opening_day,
                or_(
                    residence.period.end == None,
                    residence.period.end >= year.closing_day,
                ),
                exists(
                    child,
                    and_(
                        child.relative == exemption.taxpayer,
                        child.person == exemption.individual,
                        or_(
                            child.period.start == None,
                            child.period.start <= year.opening_day,
                        ),
                        or_(
                            child.period.end == None,
                            child.period.end >= year.closing_day,
                        ),
                    ),
                ),
            )
        )


@dataclass
class HeadOfHouseholdHomeTest(Provision[HeadOfHouseholdHome]):
    """
    `§ 2(b)(1) <https://www.law.cornell.edu/uscode/text/26/2#b_1>`__: a taxpayer, not married at the close of the year and no surviving spouse,
    keeping a home under `(A) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A>`__ or `(B) <https://www.law.cornell.edu/uscode/text/26/2#b_1_B>`__.

    Marital status follows `(2) <https://www.law.cornell.edu/uscode/text/26/2#b_2>`__ rather than `§ 7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__, as in SARA.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HEAD_OF_HOUSEHOLD_HOME`.
        """
        return SaraPredicate.HEAD_OF_HOUSEHOLD_HOME

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        home = variable(
            HomeForDependent,
            domain=HomeForQualifyingIndividualTest(world=self.world).conclusions
            + HomeForParentTest(world=self.world).conclusions,
        )
        survivor = variable(
            SurvivingSpouse, domain=SurvivingSpouseTest(world=self.world).conclusions
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(HeadOfHouseholdHome)(
                    taxpayer=home.taxpayer,
                    household=home.household,
                    individual=home.individual,
                    year=home.year,
                )
            ).where(
                year.number == home.year,
                not_(self.is_married_at_close(home.taxpayer, year)),
                not_(
                    exists(
                        survivor,
                        and_(
                            survivor.taxpayer == home.taxpayer,
                            survivor.year == home.year,
                        ),
                    )
                ),
            )
        )

    def is_married_at_close(self, taxpayer: Party, year: CalendarYear) -> Query:
        """
        :return: Whether *taxpayer* is married at the close of *year* under `(2) <https://www.law.cornell.edu/uscode/text/26/2#b_2>`__: to a
            spouse alive then, or dying in the year, not legally separated from them and
            no nonresident alien in it.
        """
        marriage = variable(
            Marriage,
            domain=[
                marriage
                for marriage in self.world.marriages
                if marriage.period.start is not None
            ],
        )
        spouse = variable(Party, domain=self.world.parties)
        death = variable(Death, domain=self.world.deaths)
        later_death = variable(Death, domain=self.world.deaths)
        no_death = variable(Death, domain=self.world.deaths)
        deceased_in_year = variable(
            SpouseDeceasedInYear,
            domain=SpouseDeceasedInYearTest(world=self.world).conclusions,
        )
        separated = variable(
            SeparatedForHeadOfHousehold,
            domain=SeparatedForHeadOfHouseholdTest(world=self.world).conclusions,
        )
        nonresident_spouse = variable(
            NonresidentAlienSpouse,
            domain=NonresidentAlienSpouseTest(world=self.world).conclusions,
        )
        return exists(
            marriage,
            exists(
                spouse,
                and_(
                    in_(taxpayer, marriage.spouses),
                    in_(spouse, marriage.spouses),
                    spouse != taxpayer,
                    marriage.period.start <= year.closing_day,
                    or_(
                        and_(
                            exists(death, death.person == spouse),
                            or_(
                                exists(
                                    deceased_in_year,
                                    and_(
                                        deceased_in_year.taxpayer == taxpayer,
                                        deceased_in_year.marriage == marriage,
                                        deceased_in_year.spouse == spouse,
                                        deceased_in_year.year == year.number,
                                    ),
                                ),
                                exists(
                                    later_death,
                                    and_(
                                        later_death.person == spouse,
                                        later_death.day != None,
                                        later_death.day >= year.closing_day,
                                    ),
                                ),
                            ),
                        ),
                        and_(
                            not_(exists(no_death, no_death.person == spouse)),
                            or_(
                                marriage.period.end == None,
                                marriage.period.end
                                >= year.opening_day_of_following_year,
                            ),
                        ),
                    ),
                    not_(
                        exists(
                            separated,
                            and_(
                                separated.separation.marriage == marriage,
                                separated.year == year.number,
                            ),
                        )
                    ),
                    not_(
                        exists(
                            nonresident_spouse,
                            and_(
                                nonresident_spouse.taxpayer == taxpayer,
                                nonresident_spouse.spouse == spouse,
                                nonresident_spouse.year == year.number,
                            ),
                        )
                    ),
                ),
            ),
        )


@dataclass
class NonresidentAlienTaxpayerTest(Provision[NonresidentAlienTaxpayer]):
    """
    `§ 2(b)(3)(A) <https://www.law.cornell.edu/uscode/text/26/2#b_3_A>`__: a taxpayer who is a nonresident alien at some time during the year.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.NONRESIDENT_ALIEN_TAXPAYER`.
        """
        return SaraPredicate.NONRESIDENT_ALIEN_TAXPAYER

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    def query(self) -> Query:
        nonresident = variable(
            NonresidentAlienTaxpayer,
            domain=self.nonresident_from_opening() + self.nonresident_by_close(),
        )
        return an(entity(nonresident))

    def nonresident_from_opening(self) -> list[NonresidentAlienTaxpayer]:
        """:return: The taxpayers who are nonresident aliens from no stated day on, still at the year's opening."""
        status = variable(
            NonresidentAlienStatus,
            domain=[
                status
                for status in self.world.nonresident_alien_statuses
                if status.period.start is None
            ],
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(NonresidentAlienTaxpayer)(
                    taxpayer=status.person, year=year.number, day=year.opening_day
                )
            ).where(
                or_(status.period.end == None, status.period.end >= year.opening_day)
            )
        ).tolist()

    def nonresident_by_close(self) -> list[NonresidentAlienTaxpayer]:
        """:return: The taxpayers who become nonresident aliens by the year's close and are still on its last day."""
        status = variable(
            NonresidentAlienStatus,
            domain=[
                status
                for status in self.world.nonresident_alien_statuses
                if status.period.start is not None
            ],
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(NonresidentAlienTaxpayer)(
                    taxpayer=status.person, year=year.number, day=year.closing_day
                )
            ).where(
                status.period.start <= year.closing_day,
                or_(status.period.end == None, status.period.end >= year.closing_day),
            )
        ).tolist()


@dataclass
class HouseholdMemberDependentTest(Provision[HouseholdMemberDependent]):
    """
    `§ 2(b)(3)(B) <https://www.law.cornell.edu/uscode/text/26/2#b_3_B>`__: an individual who would be no dependent of the taxpayer but for
    `§ 152(d)(2)(H) <https://www.law.cornell.edu/uscode/text/26/152#d_2_H>`__, compared with the year as SARA's program compares it.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HOUSEHOLD_MEMBER_DEPENDENT`.
        """
        return SaraPredicate.HOUSEHOLD_MEMBER_DEPENDENT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        member = variable(
            HouseholdMemberRelationship,
            domain=HouseholdMemberTest(world=self.world).conclusions,
        )
        year = variable(CalendarYear, domain=self.world.years_in_question())
        exception = variable(
            DependencyException,
            domain=DependencyExceptionTest(world=self.world).conclusions,
        )
        child = variable(
            QualifyingChildDependent,
            domain=QualifyingChildDependentTest(world=self.world).conclusions,
        )
        no_income = variable(
            NoGrossIncome, domain=NoGrossIncomeTest(world=self.world).conclusions
        )
        no_child = variable(
            NoQualifyingChild,
            domain=NoQualifyingChildTest(world=self.world).conclusions,
        )
        relationship = variable(
            RelationshipToTaxpayer,
            domain=QualifyingRelativeRelationshipTest(
                world=self.world
            ).relationships_regardless_of_year(),
        )
        return an(
            entity(
                inference(HouseholdMemberDependent)(
                    taxpayer=member.taxpayer,
                    individual=member.individual,
                    year=member.year,
                )
            ).where(
                year.number == member.year,
                or_(
                    member.period.start == None, member.period.start <= year.opening_day
                ),
                or_(member.period.end == None, member.period.end >= year.closing_day),
                not_(
                    exists(
                        exception,
                        and_(
                            exception.individual == member.individual,
                            exception.taxpayer == member.taxpayer,
                            exception.year == member.year,
                        ),
                    )
                ),
                not_(
                    exists(
                        child,
                        and_(
                            child.individual == member.individual,
                            child.taxpayer == member.taxpayer,
                            child.year == member.year,
                        ),
                    )
                ),
                exists(
                    no_income,
                    and_(
                        no_income.individual == member.individual,
                        no_income.year == member.year,
                    ),
                ),
                exists(
                    no_child,
                    and_(
                        no_child.individual == member.individual,
                        no_child.year == member.year,
                    ),
                ),
                not_(
                    exists(
                        relationship,
                        and_(
                            relationship.individual == member.individual,
                            relationship.taxpayer == member.taxpayer,
                            or_(
                                relationship.period.start == None,
                                relationship.period.start <= year.opening_day,
                            ),
                            or_(
                                relationship.period.end == None,
                                relationship.period.end <= year.closing_day,
                            ),
                        ),
                    )
                ),
            )
        )


@dataclass
class HeadOfHouseholdLimitationTest(Provision[HeadOfHouseholdLimitation]):
    """
    `§ 2(b)(3) <https://www.law.cornell.edu/uscode/text/26/2#b_3>`__: no head of household while a nonresident alien `(A) <https://www.law.cornell.edu/uscode/text/26/2#b_3_A>`__, or by reason of an
    individual who would be no dependent but for `§ 152(d)(2)(H) <https://www.law.cornell.edu/uscode/text/26/152#d_2_H>`__ `(B) <https://www.law.cornell.edu/uscode/text/26/2#b_3_B>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HEAD_OF_HOUSEHOLD_LIMITATION`.
        """
        return SaraPredicate.HEAD_OF_HOUSEHOLD_LIMITATION

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        taxpayer = variable(Party, domain=self.world.parties)
        individual = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        nonresident = variable(
            NonresidentAlienTaxpayer,
            domain=NonresidentAlienTaxpayerTest(world=self.world).conclusions,
        )
        member = variable(
            HouseholdMemberDependent,
            domain=HouseholdMemberDependentTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(HeadOfHouseholdLimitation)(
                    taxpayer=taxpayer, individual=individual, year=year.number
                )
            ).where(
                or_(
                    exists(
                        nonresident,
                        and_(
                            nonresident.taxpayer == taxpayer,
                            nonresident.year == year.number,
                        ),
                    ),
                    exists(
                        member,
                        and_(
                            member.taxpayer == taxpayer,
                            member.individual == individual,
                            member.year == year.number,
                        ),
                    ),
                )
            )
        )


@dataclass
class HeadOfHouseholdTest(Provision[HeadOfHousehold]):
    """
    `§ 2(b) <https://www.law.cornell.edu/uscode/text/26/2#b>`__: a taxpayer keeping a home under `(1) <https://www.law.cornell.edu/uscode/text/26/2#b_1>`__, not limited by `(3) <https://www.law.cornell.edu/uscode/text/26/2#b_3>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HEAD_OF_HOUSEHOLD`.
        """
        return SaraPredicate.HEAD_OF_HOUSEHOLD

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        home = variable(
            HeadOfHouseholdHome,
            domain=HeadOfHouseholdHomeTest(world=self.world).conclusions,
        )
        limitation = variable(
            HeadOfHouseholdLimitation,
            domain=HeadOfHouseholdLimitationTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(HeadOfHousehold)(
                    taxpayer=home.taxpayer, individual=home.individual, year=home.year
                )
            ).where(
                not_(
                    exists(
                        limitation,
                        and_(
                            limitation.taxpayer == home.taxpayer,
                            limitation.individual == home.individual,
                            limitation.year == home.year,
                        ),
                    )
                )
            )
        )


# %% applicable amount


@dataclass
class JointReturnOrSurvivorApplicableAmountTest(
    Provision[JointReturnOrSurvivorApplicableAmount]
):
    """
    `§ 68(b)(1)(A) <https://www.law.cornell.edu/uscode/text/26/68#b_1_A>`__: $300,000 for a taxpayer making a joint return, or surviving their spouse.

    The statute asks whether the taxpayer is a surviving spouse; SARA's program asks
    whether anyone is.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.JOINT_RETURN_OR_SURVIVOR_APPLICABLE_AMOUNT`.
        """
        return SaraPredicate.JOINT_RETURN_OR_SURVIVOR_APPLICABLE_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fifth argument.
        """
        return 4

    @classproperty
    def amount(cls) -> float:
        """
        The applicable amount.
        """
        return 300_000

    def query(self) -> Query:
        filing = variable(
            JointFiling, domain=JointFilingTest(world=self.world).conclusions
        )
        survivor = variable(
            SurvivingSpouse, domain=SurvivingSpouseTest(world=self.world).conclusions
        )
        amount = variable(
            JointReturnOrSurvivorApplicableAmount,
            domain=an(
                entity(
                    inference(JointReturnOrSurvivorApplicableAmount)(
                        taxpayer=filing.individual,
                        amount=self.amount,
                        year=filing.year,
                        joint_return=filing.joint_return,
                    )
                )
            ).tolist()
            + an(
                entity(
                    inference(JointReturnOrSurvivorApplicableAmount)(
                        taxpayer=survivor.taxpayer,
                        amount=self.amount,
                        year=survivor.year,
                        surviving_spouse=survivor.taxpayer,
                    )
                )
            ).tolist(),
        )
        return an(entity(amount))


@dataclass
class HeadOfHouseholdApplicableAmountTest(Provision[HeadOfHouseholdApplicableAmount]):
    """
    `§ 68(b)(1)(B) <https://www.law.cornell.edu/uscode/text/26/68#b_1_B>`__: $275,000 for a head of household.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.HEAD_OF_HOUSEHOLD_APPLICABLE_AMOUNT`.
        """
        return SaraPredicate.HEAD_OF_HOUSEHOLD_APPLICABLE_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    @classproperty
    def amount(cls) -> float:
        """
        The applicable amount.
        """
        return 275_000

    def query(self) -> Query:
        head = variable(
            HeadOfHousehold, domain=HeadOfHouseholdTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(HeadOfHouseholdApplicableAmount)(
                    taxpayer=head.taxpayer, amount=self.amount, year=head.year
                )
            )
        )


@dataclass
class UnmarriedApplicableAmountTest(Provision[UnmarriedApplicableAmount]):
    """
    `§ 68(b)(1)(C) <https://www.law.cornell.edu/uscode/text/26/68#b_1_C>`__: $250,000 for an individual not married, no surviving spouse and no head
    of household.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.UNMARRIED_APPLICABLE_AMOUNT`.
        """
        return SaraPredicate.UNMARRIED_APPLICABLE_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    @classproperty
    def amount(cls) -> float:
        """
        The applicable amount.
        """
        return 250_000

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
        head = variable(
            HeadOfHousehold, domain=HeadOfHouseholdTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(UnmarriedApplicableAmount)(
                    taxpayer=taxpayer, amount=self.amount, year=year.number
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
                not_(
                    exists(
                        head, and_(head.taxpayer == taxpayer, head.year == year.number)
                    )
                ),
            )
        )


@dataclass
class SeparateReturnApplicableAmountTest(Provision[SeparateReturnApplicableAmount]):
    """
    `§ 68(b)(1)(D) <https://www.law.cornell.edu/uscode/text/26/68#b_1_D>`__: half the amount of `(A) <https://www.law.cornell.edu/uscode/text/26/68#b_1_A>`__ for a married individual filing
    separately.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SEPARATE_RETURN_APPLICABLE_AMOUNT`.
        """
        return SaraPredicate.SEPARATE_RETURN_APPLICABLE_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        married = variable(
            MarriedIndividual,
            domain=MarriedIndividualTest(world=self.world).separate_filers(),
        )
        return an(
            entity(
                inference(SeparateReturnApplicableAmount)(
                    taxpayer=married.person,
                    amount=round(JointReturnOrSurvivorApplicableAmountTest.amount / 2),
                    year=married.year,
                )
            )
        )


@dataclass
class ApplicableAmountTest(Provision[ApplicableAmount]):
    """
    `§ 68(b) <https://www.law.cornell.edu/uscode/text/26/68#b>`__: the applicable amount of any of `(1)(A) <https://www.law.cornell.edu/uscode/text/26/68#b_1_A>`__ through `(D) <https://www.law.cornell.edu/uscode/text/26/68#b_1_D>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.APPLICABLE_AMOUNT`.
        """
        return SaraPredicate.APPLICABLE_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        amount = variable(
            SaraConclusion,
            domain=[
                conclusion
                for test in (
                    JointReturnOrSurvivorApplicableAmountTest,
                    HeadOfHouseholdApplicableAmountTest,
                    UnmarriedApplicableAmountTest,
                    SeparateReturnApplicableAmountTest,
                )
                for conclusion in test(world=self.world).conclusions
            ],
        )
        return an(
            entity(
                inference(ApplicableAmount)(
                    taxpayer=amount.taxpayer, amount=amount.amount, year=amount.year
                )
            )
        )


# %% exemption amount


@dataclass
class GeneralExemptionAmountTest(Provision[GeneralExemptionAmount]):
    """
    `§ 151(d)(1) <https://www.law.cornell.edu/uscode/text/26/151#d_1>`__: the exemption amount of $2,000, except as otherwise provided.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.GENERAL_EXEMPTION_AMOUNT`.
        """
        return SaraPredicate.GENERAL_EXEMPTION_AMOUNT

    @classproperty
    def amount(cls) -> float:
        """
        The exemption amount.
        """
        return 2_000

    def query(self) -> Query:
        return an(entity(inference(GeneralExemptionAmount)(amount=self.amount)))


@dataclass
class SuspendedExemptionAmountTest(Provision[SuspendedExemptionAmount]):
    """
    `§ 151(d)(5) <https://www.law.cornell.edu/uscode/text/26/151#d_5>`__: a zero exemption amount for taxable years beginning after 2017 and before
    2026.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.SUSPENDED_EXEMPTION_AMOUNT`.
        """
        return SaraPredicate.SUSPENDED_EXEMPTION_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The second argument.
        """
        return 1

    @classproperty
    def first_year(cls) -> int:
        """
        The first calendar year of the suspension.
        """
        return 2018

    @classproperty
    def last_year(cls) -> int:
        """
        The last calendar year of the suspension.
        """
        return 2025

    def query(self) -> Query:
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(inference(SuspendedExemptionAmount)(year=year.number)).where(
                year.number >= self.first_year, year.number <= self.last_year
            )
        )


@dataclass
class DisallowedExemptionAmountTest(Provision[DisallowedExemptionAmount]):
    """
    `§ 151(d)(2) <https://www.law.cornell.edu/uscode/text/26/151#d_2>`__: a zero exemption amount for an individual another taxpayer is allowed an
    exemption for under `§ 151(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__ or `(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.DISALLOWED_EXEMPTION_AMOUNT`.
        """
        return SaraPredicate.DISALLOWED_EXEMPTION_AMOUNT

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
        return an(
            entity(
                inference(DisallowedExemptionAmount)(
                    individual=exemption.individual,
                    other_taxpayer=exemption.taxpayer,
                    year=exemption.year,
                )
            ).where(exemption.individual != exemption.taxpayer)
        )


@dataclass
class ApplicablePercentageTest(Provision[ApplicablePercentage]):
    """
    `§ 151(d)(3)(B) <https://www.law.cornell.edu/uscode/text/26/151#d_3_B>`__: 2 percentage points for each $2,500, or $1,250 for a married
    individual filing separately, by which gross income exceeds the applicable amount;
    at most 100.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.APPLICABLE_PERCENTAGE`.
        """
        return SaraPredicate.APPLICABLE_PERCENTAGE

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    @classproperty
    def step(cls) -> float:
        """
        The excess each 2 percentage points are counted for.
        """
        return 2_500

    @classproperty
    def step_for_separate_return(cls) -> float:
        """
        The excess each 2 percentage points are counted for, for a married individual
        filing separately.
        """
        return 1_250

    def query(self) -> Query:
        percentage = variable(
            ApplicablePercentage,
            domain=self.percentages(files_separately=True)
            + self.percentages(files_separately=False),
        )
        return an(entity(percentage))

    def percentages(self, files_separately: bool) -> list[ApplicablePercentage]:
        """:return: The applicable percentages of the taxpayers who file separately while married, or of the others."""
        income = variable(
            GrossIncome, domain=GrossIncomeOfParty(world=self.world).conclusions
        )
        applicable_amount = variable(
            ApplicableAmount, domain=ApplicableAmountTest(world=self.world).conclusions
        )
        separate_filer = variable(
            MarriedIndividual,
            domain=MarriedIndividualTest(world=self.world).separate_filers(),
        )
        files_separately_while_married = exists(
            separate_filer,
            and_(
                separate_filer.person == income.person,
                separate_filer.year == income.year,
            ),
        )
        return an(
            entity(
                inference(ApplicablePercentage)(
                    taxpayer=income.person,
                    year=income.year,
                    percentage=ApplicablePercentageTest.percentage_of_excess(
                        self,
                        income.amount,
                        applicable_amount.amount,
                        self.step_for_separate_return
                        if files_separately
                        else self.step,
                    ),
                    gross_income=income.amount,
                    applicable_amount=applicable_amount.amount,
                )
            ).where(
                applicable_amount.taxpayer == income.person,
                applicable_amount.year == income.year,
                files_separately_while_married
                if files_separately
                else not_(files_separately_while_married),
            )
        ).tolist()

    @symbolic_function
    def percentage_of_excess(
        self, gross_income: float, applicable_amount: float, step: float
    ) -> int:
        """:return: 2 percentage points for each *step*, or fraction of one, by which *gross_income* exceeds *applicable_amount*, at most 100."""
        excess = max(gross_income - applicable_amount, 0)
        return min(2 * math.ceil(excess / step), 100)


@dataclass
class ReducedExemptionAmountTest(Provision[ReducedExemptionAmount]):
    """
    `§ 151(d)(3)(A) <https://www.law.cornell.edu/uscode/text/26/151#d_3_A>`__: the exemption amount of `(1) <https://www.law.cornell.edu/uscode/text/26/151#d_1>`__, reduced by the applicable percentage of
    it where gross income exceeds the applicable amount of `§ 68(b) <https://www.law.cornell.edu/uscode/text/26/68#b>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.REDUCED_EXEMPTION_AMOUNT`.
        """
        return SaraPredicate.REDUCED_EXEMPTION_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The seventh argument.
        """
        return 6

    def query(self) -> Query:
        percentage = variable(
            ApplicablePercentage,
            domain=ApplicablePercentageTest(world=self.world).conclusions,
        )
        general = variable(
            GeneralExemptionAmount,
            domain=GeneralExemptionAmountTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(ReducedExemptionAmount)(
                    percentage=percentage,
                    exemption_amount_before=general.amount,
                    amount=ReducedExemptionAmountTest.reduced_amount(
                        self, general.amount, percentage.percentage
                    ),
                )
            ).where(percentage.gross_income > percentage.applicable_amount)
        )

    @symbolic_function
    def reduced_amount(self, amount: float, percentage: int) -> float:
        """:return: *amount* less *percentage* percent of it in whole dollars, at least 0."""
        return max(amount - Provision.share_in_whole_dollars(amount, percentage), 0)


@dataclass
class PhasedOutExemptionAmountTest(Provision[PhasedOutExemptionAmount]):
    """
    `§ 151(d)(3) <https://www.law.cornell.edu/uscode/text/26/151#d_3>`__: the exemption amount after the phaseout of `(A) <https://www.law.cornell.edu/uscode/text/26/151#d_3_A>`__.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.PHASED_OUT_EXEMPTION_AMOUNT`.
        """
        return SaraPredicate.PHASED_OUT_EXEMPTION_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        reduction = variable(
            ReducedExemptionAmount,
            domain=ReducedExemptionAmountTest(world=self.world).conclusions,
        )
        return an(entity(inference(PhasedOutExemptionAmount)(reduction=reduction)))


@dataclass
class ExemptionAmountTest(Provision[ExemptionAmount]):
    """
    `§ 151(d) <https://www.law.cornell.edu/uscode/text/26/151#d>`__: the exemption amount: zero under `(2) <https://www.law.cornell.edu/uscode/text/26/151#d_2>`__ or `(5) <https://www.law.cornell.edu/uscode/text/26/151#d_5>`__, else that of `(1) <https://www.law.cornell.edu/uscode/text/26/151#d_1>`__, phased out
    under `(3) <https://www.law.cornell.edu/uscode/text/26/151#d_3>`__ where it applies.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.EXEMPTION_AMOUNT`.
        """
        return SaraPredicate.EXEMPTION_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The third argument.
        """
        return 2

    def query(self) -> Query:
        amount = variable(
            ExemptionAmount,
            domain=self.zero_amounts()
            + self.phased_out_amounts()
            + self.general_amounts(),
        )
        return an(entity(amount))

    def zero_amounts(self) -> list[ExemptionAmount]:
        """:return: The zero exemption amounts of `(2) <https://www.law.cornell.edu/uscode/text/26/151#d_2>`__ and `(5) <https://www.law.cornell.edu/uscode/text/26/151#d_5>`__."""
        taxpayer = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        return an(
            entity(
                inference(ExemptionAmount)(
                    taxpayer=taxpayer, amount=0, year=year.number
                )
            ).where(self.is_zero(taxpayer, year))
        ).tolist()

    def phased_out_amounts(self) -> list[ExemptionAmount]:
        """:return: The exemption amounts phased out under `(3) <https://www.law.cornell.edu/uscode/text/26/151#d_3>`__, where they are not zero."""
        taxpayer = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        phased_out = variable(
            PhasedOutExemptionAmount,
            domain=PhasedOutExemptionAmountTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(ExemptionAmount)(
                    taxpayer=taxpayer,
                    amount=phased_out.reduction.amount,
                    year=year.number,
                )
            ).where(
                phased_out.reduction.percentage.taxpayer == taxpayer,
                phased_out.reduction.percentage.year == year.number,
                not_(self.is_zero(taxpayer, year)),
            )
        ).tolist()

    def general_amounts(self) -> list[ExemptionAmount]:
        """:return: The exemption amounts of `(1) <https://www.law.cornell.edu/uscode/text/26/151#d_1>`__, where none of `(2) <https://www.law.cornell.edu/uscode/text/26/151#d_2>`__, `(3) <https://www.law.cornell.edu/uscode/text/26/151#d_3>`__ and `(5) <https://www.law.cornell.edu/uscode/text/26/151#d_5>`__ applies."""
        taxpayer = variable(Party, domain=self.world.parties)
        year = variable(CalendarYear, domain=self.world.years_in_question())
        phased_out = variable(
            PhasedOutExemptionAmount,
            domain=PhasedOutExemptionAmountTest(world=self.world).conclusions,
        )
        return an(
            entity(
                inference(ExemptionAmount)(
                    taxpayer=taxpayer,
                    amount=GeneralExemptionAmountTest.amount,
                    year=year.number,
                )
            ).where(
                not_(self.is_zero(taxpayer, year)),
                not_(
                    exists(
                        phased_out,
                        and_(
                            phased_out.reduction.percentage.taxpayer == taxpayer,
                            phased_out.reduction.percentage.year == year.number,
                        ),
                    )
                ),
            )
        ).tolist()

    def is_zero(self, taxpayer: Party, year: CalendarYear) -> Query:
        """:return: Whether *taxpayer*'s exemption amount for *year* is zero under `(2) <https://www.law.cornell.edu/uscode/text/26/151#d_2>`__ or `(5) <https://www.law.cornell.edu/uscode/text/26/151#d_5>`__."""
        disallowed = variable(
            DisallowedExemptionAmount,
            domain=DisallowedExemptionAmountTest(world=self.world).conclusions,
        )
        suspended = variable(
            SuspendedExemptionAmount,
            domain=SuspendedExemptionAmountTest(world=self.world).conclusions,
        )
        return or_(
            exists(
                disallowed,
                and_(disallowed.individual == taxpayer, disallowed.year == year.number),
            ),
            exists(suspended, suspended.year == year.number),
        )


@dataclass
class DependentExemptionAmountTest(Provision[DependentExemptionAmount]):
    """
    `§ 151(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__: an exemption of the exemption amount for each dependent of the taxpayer.
    """

    @classproperty
    def predicate(cls) -> SaraPredicate:
        """
        :attr:`SaraPredicate.DEPENDENT_EXEMPTION_AMOUNT`.
        """
        return SaraPredicate.DEPENDENT_EXEMPTION_AMOUNT

    @classproperty
    def year_position(cls) -> int | None:
        """
        The fourth argument.
        """
        return 3

    def query(self) -> Query:
        exemption = variable(
            ExemptionForDependent,
            domain=ExemptionForDependentTest(world=self.world).conclusions,
        )
        amount = variable(
            ExemptionAmount, domain=ExemptionAmountTest(world=self.world).conclusions
        )
        return an(
            entity(
                inference(DependentExemptionAmount)(
                    taxpayer=exemption.taxpayer,
                    amount=amount.amount,
                    year=exemption.year,
                    individual=exemption.individual,
                )
            ).where(
                amount.taxpayer == exemption.taxpayer,
                amount.year == exemption.year,
            )
        )
