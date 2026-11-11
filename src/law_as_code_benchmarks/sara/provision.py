"""
A provision of SARA's statutes as a krrood rule, and the conclusions it draws.

A provision is asked as SARA's Prolog program is, by a goal naming its predicate. It
holds where one of its conclusions, inferred or stated by the case, agrees with every
argument the goal binds, and binds the goal's named variables as it agrees.
"""

from __future__ import annotations

import datetime
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum

from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from krrood.patterns.subclass_safe_generic import SubClassSafeGeneric
from krrood.symbol_graph.symbol_graph import Symbol
from krrood.utils import recursive_subclasses
from typing_extensions import Generic, TypeVar

from law_as_code_benchmarks.sara.domain import World
from law_as_code_benchmarks.sara.prolog_term import (
    CompoundTerm,
    PrologText,
    PrologVariable,
    Term,
)

# %% predicates


class SaraPredicate(StrEnum):
    """The predicates of SARA's Prolog program that are modelled, each named as the program names it."""

    SERVICE_FOR_UNITED_STATES_GOVERNMENT = "s3306_c_6"
    """`§ 3306(c)(6) <https://www.law.cornell.edu/uscode/text/26/3306#c_6>`__: service in the employ of the United States Government."""

    SERVICE_FOR_STATE = "s3306_c_7"
    """`§ 3306(c)(7) <https://www.law.cornell.edu/uscode/text/26/3306#c_7>`__: service in the employ of a State."""

    SERVICE_BY_HOSPITAL_PATIENT = "s3306_c_10_B"
    """`§ 3306(c)(10)(B) <https://www.law.cornell.edu/uscode/text/26/3306#c_10_B>`__: service for a hospital by a patient of that hospital."""

    SERVICE_FOR_FOREIGN_GOVERNMENT = "s3306_c_11"
    """`§ 3306(c)(11) <https://www.law.cornell.edu/uscode/text/26/3306#c_11>`__: service in the employ of a foreign government."""

    SERVICE_FOR_INTERNATIONAL_ORGANIZATION = "s3306_c_16"
    """`§ 3306(c)(16) <https://www.law.cornell.edu/uscode/text/26/3306#c_16>`__: service in the employ of an international organization."""

    SERVICE_ABROAD_FOR_AMERICAN_EMPLOYER = "s3306_c_B"
    """`§ 3306(c)(B) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__: service outside the United States by a citizen for an American employer."""

    LABOR_NOT_BY_ADMITTED_ALIEN = "s3306_c_1_B"
    """`§ 3306(c)(1)(B) <https://www.law.cornell.edu/uscode/text/26/3306#c_1_B>`__: agricultural labor not performed by an alien admitted to perform it."""

    EMPLOYER_OF_AGRICULTURAL_LABOR = "s3306_c_1_A_i"
    """`§ 3306(c)(1)(A)(i) <https://www.law.cornell.edu/uscode/text/26/3306#c_1_A_i>`__: a person who paid $20,000 or more in cash for agricultural labor."""

    EMPLOYMENT = "s3306_c"
    """`§ 3306(c) <https://www.law.cornell.edu/uscode/text/26/3306#c>`__: service that is *employment*."""

    WAGES = "s3306_b"
    """`§ 3306(b) <https://www.law.cornell.edu/uscode/text/26/3306#b>`__: remuneration for employment that is *wages*."""

    DEATH_BENEFIT_PLAN = "s3306_b_2_C"
    """`§ 3306(b)(2)(C) <https://www.law.cornell.edu/uscode/text/26/3306#b_2_C>`__: a plan making provision for employees in case of death."""

    EMPLOYER = "s3306_a"
    """`§ 3306(a) <https://www.law.cornell.edu/uscode/text/26/3306#a>`__: a person who is an *employer* for a calendar year."""

    EMPLOYER_BY_WAGES = "s3306_a_1_A"
    """`§ 3306(a)(1)(A) <https://www.law.cornell.edu/uscode/text/26/3306#a_1_A>`__: a person who paid wages of $1,500 or more."""

    EMPLOYER_BY_DAYS_OF_EMPLOYMENT = "s3306_a_1_B"
    """`§ 3306(a)(1)(B) <https://www.law.cornell.edu/uscode/text/26/3306#a_1_B>`__: a person who employed someone on 10 days, each in a different week."""

    EMPLOYER_BY_AGRICULTURAL_WAGES = "s3306_a_2_A"
    """`§ 3306(a)(2)(A) <https://www.law.cornell.edu/uscode/text/26/3306#a_2_A>`__: a person who paid wages of $20,000 or more for agricultural labor."""

    EMPLOYER_OF_DOMESTIC_SERVICE = "s3306_a_3"
    """`§ 3306(a)(3) <https://www.law.cornell.edu/uscode/text/26/3306#a_3>`__: a person who paid $1,000 or more in cash for domestic service."""

    TOTAL_WAGES = "total_wages_employer"
    """The wages an employer paid in a period, each employee's capped at $7,000 by `§ 3306(b)(1) <https://www.law.cornell.edu/uscode/text/26/3306#b_1>`__."""

    EXCISE_TAX = "s3301"
    """`§ 3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__: the excise tax on an employer, 6 percent of the wages paid in a calendar year."""

    CHILD = "is_child_of"
    """SARA's utility: that one party is a child of another."""

    DESCENDANT = "is_descendent_of"
    """SARA's utility: that one party is a descendant of another."""

    SIBLING = "is_sibling_of"
    """SARA's utility: that one party is a brother or sister of another."""

    STEPSIBLING = "is_stepsibling_of"
    """SARA's utility: that a parent of one party married a parent of another."""

    SIBLING_IN_LAW = "is_sibling_in_law_of"
    """SARA's utility: that one party married a brother or sister of another."""

    CHILD_IN_LAW = "is_child_in_law_of"
    """SARA's utility: that one party married a child of another."""

    PARENT_IN_LAW = "is_parent_in_law_of"
    """SARA's utility: that one party married a parent of another."""

    STEPPARENT = "is_stepparent_of"
    """SARA's utility: that one party married a parent of another, the marriage's start stated."""

    GROSS_INCOME = "gross_income"
    """SARA's utility: a party's gross income for a calendar year."""

    MARRIED = "s7703"
    """`§ 7703 <https://www.law.cornell.edu/uscode/text/26/7703>`__: an individual married for a calendar year."""

    MARRIED_UNDER_GENERAL_RULE = "s7703_a"
    """`§ 7703(a) <https://www.law.cornell.edu/uscode/text/26/7703#a>`__: an individual married under the general rule."""

    MARRIED_AT_DETERMINATION = "s7703_a_1"
    """`§ 7703(a)(1) <https://www.law.cornell.edu/uscode/text/26/7703#a_1>`__: an individual married at the close of the year, or at the spouse's death."""

    LEGALLY_SEPARATED = "s7703_a_2"
    """`§ 7703(a)(2) <https://www.law.cornell.edu/uscode/text/26/7703#a_2>`__: an individual legally separated under a decree."""

    LIVING_APART = "s7703_b"
    """`§ 7703(b) <https://www.law.cornell.edu/uscode/text/26/7703#b>`__: a married individual living apart, not considered married."""

    HOME_OF_CHILD = "s7703_b_1"
    """`§ 7703(b)(1) <https://www.law.cornell.edu/uscode/text/26/7703#b_1>`__: a household kept as the home of a child."""

    HOUSEHOLD_MAINTENANCE = "s7703_b_2"
    """`§ 7703(b)(2) <https://www.law.cornell.edu/uscode/text/26/7703#b_2>`__: an individual furnishing over half the cost of a household."""

    ABSENT_SPOUSE = "s7703_b_3"
    """`§ 7703(b)(3) <https://www.law.cornell.edu/uscode/text/26/7703#b_3>`__: a spouse no member of the household in the last 6 months of the year."""

    DEPENDENT = "s152"
    """`§ 152 <https://www.law.cornell.edu/uscode/text/26/152>`__: a dependent."""

    DEPENDENT_UNDER_DEFINITION = "s152_a"
    """`§ 152(a) <https://www.law.cornell.edu/uscode/text/26/152#a>`__: a qualifying child or qualifying relative."""

    QUALIFYING_CHILD_DEPENDENT = "s152_a_1"
    """`§ 152(a)(1) <https://www.law.cornell.edu/uscode/text/26/152#a_1>`__: a dependent as a qualifying child."""

    QUALIFYING_RELATIVE_DEPENDENT = "s152_a_2"
    """`§ 152(a)(2) <https://www.law.cornell.edu/uscode/text/26/152#a_2>`__: a dependent as a qualifying relative."""

    DEPENDENCY_EXCEPTION = "s152_b"
    """`§ 152(b) <https://www.law.cornell.edu/uscode/text/26/152#b>`__: the exceptions to dependency."""

    DEPENDENT_OF_OTHER_TAXPAYER = "s152_b_1"
    """`§ 152(b)(1) <https://www.law.cornell.edu/uscode/text/26/152#b_1>`__: a taxpayer who is a dependent, treated as having none."""

    JOINT_FILING = "s152_b_2"
    """`§ 152(b)(2) <https://www.law.cornell.edu/uscode/text/26/152#b_2>`__: a married individual who made a joint return with their spouse."""

    QUALIFYING_CHILD = "s152_c"
    """`§ 152(c) <https://www.law.cornell.edu/uscode/text/26/152#c>`__: a qualifying child."""

    QUALIFYING_CHILD_UNDER_GENERAL_RULE = "s152_c_1"
    """`§ 152(c)(1) <https://www.law.cornell.edu/uscode/text/26/152#c_1>`__: a qualifying child."""

    QUALIFYING_CHILD_RELATIONSHIP_UNTIL_DEATH = "s152_c_1_A"
    """`§ 152(c)(1)(A) <https://www.law.cornell.edu/uscode/text/26/152#c_1_A>`__: a relationship of a qualifying child, until either party's death."""

    SHARED_ABODE = "s152_c_1_B"
    """`§ 152(c)(1)(B) <https://www.law.cornell.edu/uscode/text/26/152#c_1_B>`__: the taxpayer's principal place of abode, shared for over half the year."""

    AGE_REQUIREMENT_OF_QUALIFYING_CHILD = "s152_c_1_C"
    """`§ 152(c)(1)(C) <https://www.law.cornell.edu/uscode/text/26/152#c_1_C>`__: the age requirements of a qualifying child."""

    NO_JOINT_RETURN = "s152_c_1_E"
    """`§ 152(c)(1)(E) <https://www.law.cornell.edu/uscode/text/26/152#c_1_E>`__: an individual who made no joint return with a spouse."""

    QUALIFYING_CHILD_RELATIONSHIP = "s152_c_2"
    """`§ 152(c)(2) <https://www.law.cornell.edu/uscode/text/26/152#c_2>`__: the relationships of a qualifying child."""

    CHILD_OR_DESCENDANT_OF_CHILD = "s152_c_2_A"
    """`§ 152(c)(2)(A) <https://www.law.cornell.edu/uscode/text/26/152#c_2_A>`__: a child of the taxpayer, or a descendant of one."""

    SIBLING_OR_DESCENDANT_OF_SIBLING = "s152_c_2_B"
    """`§ 152(c)(2)(B) <https://www.law.cornell.edu/uscode/text/26/152#c_2_B>`__: a brother, sister, stepbrother or stepsister of the taxpayer, or a descendant of one."""

    AGE_REQUIREMENT = "s152_c_3"
    """`§ 152(c)(3) <https://www.law.cornell.edu/uscode/text/26/152#c_3>`__: younger than the taxpayer and less than 25 years old."""

    QUALIFYING_RELATIVE = "s152_d"
    """`§ 152(d) <https://www.law.cornell.edu/uscode/text/26/152#d>`__: a qualifying relative."""

    QUALIFYING_RELATIVE_UNDER_GENERAL_RULE = "s152_d_1"
    """`§ 152(d)(1) <https://www.law.cornell.edu/uscode/text/26/152#d_1>`__: a qualifying relative."""

    QUALIFYING_RELATIVE_RELATIONSHIP_UNTIL_DEATH = "s152_d_1_A"
    """`§ 152(d)(1)(A) <https://www.law.cornell.edu/uscode/text/26/152#d_1_A>`__: a relationship of a qualifying relative, until either party's death."""

    NO_GROSS_INCOME = "s152_d_1_B"
    """`§ 152(d)(1)(B) <https://www.law.cornell.edu/uscode/text/26/152#d_1_B>`__: an individual with no gross income."""

    NO_QUALIFYING_CHILD = "s152_d_1_D"
    """`§ 152(d)(1)(D) <https://www.law.cornell.edu/uscode/text/26/152#d_1_D>`__: an individual who is no qualifying child of any taxpayer."""

    QUALIFYING_RELATIVE_RELATIONSHIP = "s152_d_2"
    """`§ 152(d)(2) <https://www.law.cornell.edu/uscode/text/26/152#d_2>`__: the relationships of a qualifying relative."""

    CHILD_OR_DESCENDANT = "s152_d_2_A"
    """`§ 152(d)(2)(A) <https://www.law.cornell.edu/uscode/text/26/152#d_2_A>`__: a child or a descendant of a child."""

    SIBLING_OR_STEPSIBLING = "s152_d_2_B"
    """`§ 152(d)(2)(B) <https://www.law.cornell.edu/uscode/text/26/152#d_2_B>`__: a brother, sister, stepbrother or stepsister."""

    ANCESTOR = "s152_d_2_C"
    """`§ 152(d)(2)(C) <https://www.law.cornell.edu/uscode/text/26/152#d_2_C>`__: the father or mother, or an ancestor of either."""

    STEPPARENT_OF_TAXPAYER = "s152_d_2_D"
    """`§ 152(d)(2)(D) <https://www.law.cornell.edu/uscode/text/26/152#d_2_D>`__: a stepfather or stepmother."""

    NEPHEW_OR_NIECE = "s152_d_2_E"
    """`§ 152(d)(2)(E) <https://www.law.cornell.edu/uscode/text/26/152#d_2_E>`__: a son or daughter of a brother or sister."""

    UNCLE_OR_AUNT = "s152_d_2_F"
    """`§ 152(d)(2)(F) <https://www.law.cornell.edu/uscode/text/26/152#d_2_F>`__: a brother or sister of the father or mother."""

    IN_LAW = "s152_d_2_G"
    """`§ 152(d)(2)(G) <https://www.law.cornell.edu/uscode/text/26/152#d_2_G>`__: a son-, daughter-, father-, mother-, brother- or sister-in-law."""

    HOUSEHOLD_MEMBER = "s152_d_2_H"
    """`§ 152(d)(2)(H) <https://www.law.cornell.edu/uscode/text/26/152#d_2_H>`__: a member of the taxpayer's household all year, never their spouse in it."""

    EXEMPTION_FOR_DEPENDENT = "s151_c_applies"
    """`§ 151(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__: that a taxpayer is allowed an exemption for a dependent."""

    EXEMPTION_FOR_SPOUSE = "s151_b_applies"
    """`§ 151(b) <https://www.law.cornell.edu/uscode/text/26/151#b>`__: that a taxpayer is allowed an exemption for their spouse."""

    DEPENDENT_EXEMPTION_AMOUNT = "s151_c"
    """`§ 151(c) <https://www.law.cornell.edu/uscode/text/26/151#c>`__: the exemption amount for a dependent."""

    EXEMPTION_AMOUNT = "s151_d"
    """`§ 151(d) <https://www.law.cornell.edu/uscode/text/26/151#d>`__: the exemption amount."""

    GENERAL_EXEMPTION_AMOUNT = "s151_d_1"
    """`§ 151(d)(1) <https://www.law.cornell.edu/uscode/text/26/151#d_1>`__: the exemption amount, except as otherwise provided."""

    DISALLOWED_EXEMPTION_AMOUNT = "s151_d_2"
    """`§ 151(d)(2) <https://www.law.cornell.edu/uscode/text/26/151#d_2>`__: a zero exemption amount for someone another taxpayer may deduct an exemption for."""

    PHASED_OUT_EXEMPTION_AMOUNT = "s151_d_3"
    """`§ 151(d)(3) <https://www.law.cornell.edu/uscode/text/26/151#d_3>`__: the exemption amount after the phaseout."""

    REDUCED_EXEMPTION_AMOUNT = "s151_d_3_A"
    """`§ 151(d)(3)(A) <https://www.law.cornell.edu/uscode/text/26/151#d_3_A>`__: the exemption amount reduced by the applicable percentage."""

    APPLICABLE_PERCENTAGE = "s151_d_3_B"
    """`§ 151(d)(3)(B) <https://www.law.cornell.edu/uscode/text/26/151#d_3_B>`__: the applicable percentage of the phaseout."""

    SUSPENDED_EXEMPTION_AMOUNT = "s151_d_5"
    """`§ 151(d)(5) <https://www.law.cornell.edu/uscode/text/26/151#d_5>`__: a zero exemption amount for 2018 through 2025."""

    APPLICABLE_AMOUNT = "s68_b"
    """`§ 68(b) <https://www.law.cornell.edu/uscode/text/26/68#b>`__: the applicable amount."""

    SURVIVING_SPOUSE = "s2_a"
    """`§ 2(a) <https://www.law.cornell.edu/uscode/text/26/2#a>`__: a surviving spouse."""

    SURVIVING_SPOUSE_UNDER_GENERAL_RULE = "s2_a_1"
    """`§ 2(a)(1) <https://www.law.cornell.edu/uscode/text/26/2#a_1>`__: a surviving spouse under the general rule."""

    DECEASED_SPOUSE = "s2_a_1_A"
    """`§ 2(a)(1)(A) <https://www.law.cornell.edu/uscode/text/26/2#a_1_A>`__: a taxpayer whose spouse died in the two years before."""

    HOME_FOR_DEPENDENT_CHILD = "s2_a_1_B"
    """`§ 2(a)(1)(B) <https://www.law.cornell.edu/uscode/text/26/2#a_1_B>`__: a home kept for a dependent son, stepson, daughter or stepdaughter."""

    REMARRIED_TAXPAYER = "s2_a_2_A"
    """`§ 2(a)(2)(A) <https://www.law.cornell.edu/uscode/text/26/2#a_2_A>`__: a taxpayer who remarried."""

    SPOUSES_WITHOUT_NONRESIDENT_ALIEN = "s2_a_2_B"
    """`§ 2(a)(2)(B) <https://www.law.cornell.edu/uscode/text/26/2#a_2_B>`__: spouses who could have made a joint return."""

    HEAD_OF_HOUSEHOLD = "s2_b"
    """`§ 2(b) <https://www.law.cornell.edu/uscode/text/26/2#b>`__: a head of household."""

    HEAD_OF_HOUSEHOLD_HOME = "s2_b_1"
    """`§ 2(b)(1) <https://www.law.cornell.edu/uscode/text/26/2#b_1>`__: an unmarried taxpayer keeping a home for a qualifying individual."""

    HOME_FOR_QUALIFYING_INDIVIDUAL = "s2_b_1_A"
    """`§ 2(b)(1)(A) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A>`__: a home kept for a qualifying child or a dependent."""

    QUALIFYING_CHILD_OF_HOUSEHOLD = "s2_b_1_A_i"
    """`§ 2(b)(1)(A)(i) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_i>`__: a qualifying child of the household."""

    MARRIED_CHILD = "s2_b_1_A_i_I"
    """`§ 2(b)(1)(A)(i)(I) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_i_I>`__: a child married at the close of the year."""

    CHILD_FILING_JOINTLY = "s2_b_1_A_i_II"
    """`§ 2(b)(1)(A)(i)(II) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_i_II>`__: a child who is no dependent by reason of § 152(b)(2)."""

    DEPENDENT_OF_HOUSEHOLD = "s2_b_1_A_ii"
    """`§ 2(b)(1)(A)(ii) <https://www.law.cornell.edu/uscode/text/26/2#b_1_A_ii>`__: a dependent of the household."""

    HOME_FOR_PARENT = "s2_b_1_B"
    """`§ 2(b)(1)(B) <https://www.law.cornell.edu/uscode/text/26/2#b_1_B>`__: a home kept for a father or mother."""

    SEPARATED_FOR_HEAD_OF_HOUSEHOLD = "s2_b_2_A"
    """`§ 2(b)(2)(A) <https://www.law.cornell.edu/uscode/text/26/2#b_2_A>`__: a taxpayer legally separated, not considered married."""

    NONRESIDENT_ALIEN_SPOUSE = "s2_b_2_B"
    """`§ 2(b)(2)(B) <https://www.law.cornell.edu/uscode/text/26/2#b_2_B>`__: a taxpayer whose spouse is a nonresident alien, considered not married."""

    SPOUSE_DECEASED_IN_YEAR = "s2_b_2_C"
    """`§ 2(b)(2)(C) <https://www.law.cornell.edu/uscode/text/26/2#b_2_C>`__: a taxpayer whose spouse died in the year, considered married."""

    HEAD_OF_HOUSEHOLD_LIMITATION = "s2_b_3"
    """`§ 2(b)(3) <https://www.law.cornell.edu/uscode/text/26/2#b_3>`__: the limitations on heads of household."""

    NONRESIDENT_ALIEN_TAXPAYER = "s2_b_3_A"
    """`§ 2(b)(3)(A) <https://www.law.cornell.edu/uscode/text/26/2#b_3_A>`__: a taxpayer who is a nonresident alien during the year."""

    HOUSEHOLD_MEMBER_DEPENDENT = "s2_b_3_B"
    """`§ 2(b)(3)(B) <https://www.law.cornell.edu/uscode/text/26/2#b_3_B>`__: an individual who would be no dependent but for § 152(d)(2)(H)."""


# %% bindings


@dataclass(frozen=True)
class Bindings:
    """The values a goal's named variables are bound to so far."""

    values: dict[str, Term] = field(default_factory=dict)
    """The value of each bound variable, by name; None for one bound to an argument a conclusion leaves open."""

    def unify(self, asked: Term, concluded: Term) -> Bindings | None:
        """
        :param asked: An argument of a goal.
        :param concluded: The argument a conclusion gives in its place.
        :return: The bindings extended so that *asked* agrees with *concluded*; None if it cannot.
        """
        if asked is None:
            return self
        if isinstance(asked, PrologVariable):
            if asked.name not in self.values:
                return Bindings(values={**self.values, asked.name: concluded})
            asked = self.values[asked.name]
        if self.text_of(asked) != self.text_of(concluded):
            return None
        return self

    def resolve(self, term: Term) -> Term:
        """:return: The value *term* is bound to, if it is a bound variable; else *term* itself."""
        if isinstance(term, PrologVariable):
            return self.values.get(term.name)
        return term

    @staticmethod
    def text_of(term: Term) -> Term:
        """:return: The characters of a Prolog string, as the domain model names things; any other term itself."""
        return term.value if isinstance(term, PrologText) else term


# %% conclusions


@dataclass(eq=False)
class SaraConclusion(Symbol, ABC):
    """What a provision concludes, for the arguments of its predicate."""

    @abstractmethod
    def prolog_arguments(self) -> tuple[Term, ...]:
        """:return: The conclusion as the arguments of the provision's predicate, in the program's order."""

    @staticmethod
    def day_text(day: datetime.date | None) -> str | None:
        """:return: *day* as SARA's program writes it, ``YYYY-MM-DD``; None for a day it leaves open."""
        return None if day is None else day.isoformat()

    def unify(self, goal: CompoundTerm, bindings: Bindings) -> Bindings | None:
        """:return: *bindings*, extended so that the conclusion agrees with every argument of *goal*; None if it cannot."""
        arguments = self.prolog_arguments()
        if len(goal.arguments) != len(arguments):
            return None
        for asked, concluded in zip(goal.arguments, arguments):
            bindings = bindings.unify(asked, concluded)
            if bindings is None:
                return None
        return bindings


ConclusionType = TypeVar("ConclusionType", bound=SaraConclusion)


# %% provisions


@dataclass
class Provision(Generic[ConclusionType], SubClassSafeGeneric, ABC):
    """A provision of the statutes, drawing its conclusions about a case."""

    world: World
    """The circumstances of the case."""

    @classproperty
    @abstractmethod
    def predicate(cls) -> SaraPredicate:
        """The predicate of SARA's program the provision is asked by."""

    @classproperty
    def year_position(cls) -> int | None:
        """The position of the calendar year among the predicate's arguments; None where it takes none."""
        return None

    @abstractmethod
    def query(self) -> Query:
        """:return: A query inferring the provision's conclusions about the case."""

    @classmethod
    def from_goal(cls, goal: CompoundTerm, world: World) -> Provision:
        """:return: The provision about *world*, the calendar year *goal* names among the years it considers."""
        if cls.year_position is not None:
            year = goal.arguments[cls.year_position]
            if isinstance(year, int):
                world.include_calendar_year(year)
        return cls(world=world)

    @property
    def conclusions(self) -> list[ConclusionType]:
        """The conclusions the provision infers, followed by those of its kind the case states, drawn once per case."""
        provision_type = type(self)
        if provision_type not in self.world.drawn_conclusions:
            conclusion_type = self.get_type_of_generic_parameter(
                parameter=ConclusionType
            )
            self.world.drawn_conclusions[provision_type] = self.query().tolist() + [
                conclusion
                for conclusion in self.world.stated_conclusions
                if isinstance(conclusion, conclusion_type)
            ]
        return self.world.drawn_conclusions[provision_type]

    def solutions(self, goal: CompoundTerm, bindings: Bindings) -> list[Bindings]:
        """:return: The bindings each conclusion agreeing with *goal*, which names the predicate, extends *bindings* to."""
        return [
            solution
            for conclusion in self.conclusions
            if (solution := conclusion.unify(goal, bindings)) is not None
        ]

    def holds(self, goal: CompoundTerm) -> bool:
        """:return: Whether one of the provision's conclusions agrees with *goal*, which names its predicate."""
        return bool(self.solutions(goal, Bindings()))

    @classmethod
    def modelling(cls, predicate_name: str) -> type[Provision] | None:
        """:return: The provision asked by the predicate named *predicate_name*; None if none is modelled."""
        for provision in recursive_subclasses(cls):
            if (
                not inspect.isabstract(provision)
                and provision.predicate == predicate_name
            ):
                return provision
        return None
