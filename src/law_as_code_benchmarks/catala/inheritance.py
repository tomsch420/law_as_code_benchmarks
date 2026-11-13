"""
The reserved portion of an estate (*réserve héréditaire*) of articles 912 to 917 of the
French Code civil, as Catala's ``droit_successions`` example states it.
"""

from __future__ import annotations

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
    inference,
    variable,
)
from krrood.entity_query_language.factories import sum as total
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from krrood.symbol_graph.symbol_graph import Symbol

from law_as_code_benchmarks.law.provision import Conclusion
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import CatalaDirectory, CatalaValue
from law_as_code_benchmarks.catala.scope_test import (
    CaseAmount,
    CaseConclusion,
    CaseFraction,
    CatalaRecord,
    ScopeCase,
    ScopeProvision,
    ScopeTestFile,
)

# %% the estate


@dataclass(eq=False)
class Child(Symbol, CatalaRecord):
    """A child of the deceased, or a descendant standing in a child's place (article 913-1)."""

    identifier: int
    """The number the case gives the child."""

    renounced_succession: bool
    """Whether the child renounced the succession."""

    is_represented: bool
    """Whether the child is represented in the succession."""

    must_return_gift: bool
    """Whether the child must return a gift to the estate under article 845."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of Catala's ``Enfant``."""
        return {
            "identifiant": "identifier",
            "a_renoncé_à_la_succession": "renounced_succession",
            "est_représenté": "is_represented",
            "est_tenu_au_rapport_libéralité": "must_return_gift",
        }


@dataclass(eq=False)
class LifeInterest(Symbol, CatalaRecord):
    """A usufruct or life annuity the deceased disposed of (article 917)."""

    value: Money
    """What it is worth."""

    counts_towards_reserve: bool
    """Whether the heirs chose to count it towards the reserved portion."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of Catala's ``BienUsufruitRenteViagère``."""
        return {
            "valeur": "value",
            "prise_en_compte_pour_réserve_héréditaire": "counts_towards_reserve",
        }


class ReservedPortionOutput(StrEnum):
    """The outputs of Catala's ``RéserveHéréditaire`` scope."""

    RESERVED_SHARE = "quotité_réserve_héréditaire"
    """The share of the estate reserved."""

    RESERVE_BASE = "patrimoine_assiette_réserve_héréditaire"
    """The estate the share is taken of."""

    RESERVED_AMOUNT = "montant_réserve_héréditaire"
    """The amount reserved."""


@dataclass(eq=False)
class ReservedPortionCase(ScopeCase):
    """The estate of a deceased person, Catala's ``RéserveHéréditaire`` scope."""

    total_estate: Money = field(default_factory=lambda: Money.zero)
    """Everything the deceased left."""

    children: list[Child] = field(default_factory=list)
    """The deceased's children."""

    surviving_spouse_not_divorced: bool = False
    """Whether the deceased leaves a spouse they were not divorced from."""

    life_interests: list[LifeInterest] = field(default_factory=list)
    """The usufructs and life annuities the deceased disposed of."""

    @classproperty
    def catala_scope(cls) -> str:
        """``RéserveHéréditaire``."""
        return "RéserveHéréditaire"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of ``RéserveHéréditaire``."""
        return {
            "patrimoine_total": "total_estate",
            "enfants": "children",
            "conjoint_survivant_non_divorcé": "surviving_spouse_not_divorced",
            "biens_usufruit_rente_viagère": "life_interests",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`ReservedPortionOutput`."""
        return ReservedPortionOutput

    def output(self, variable: str) -> CatalaValue:
        match ReservedPortionOutput(variable):
            case ReservedPortionOutput.RESERVED_SHARE:
                return self.sole_conclusion(ReservedShareProvision).fraction
            case ReservedPortionOutput.RESERVE_BASE:
                return self.sole_conclusion(ReserveBaseProvision).amount
            case ReservedPortionOutput.RESERVED_AMOUNT:
                return self.sole_conclusion(ReservedAmountProvision).amount


# %% conclusions


@dataclass(eq=False)
class ChildCounted(Conclusion):
    """Article 913: whether a child counts among the children the deceased leaves."""

    child: Child
    """The child."""

    holds: bool = False
    """Whether the child counts."""


@dataclass(eq=False)
class CountedChildren(CaseConclusion):
    """The children the deceased leaves, as article 913 counts them."""

    children: list[Child] = field(default_factory=list)
    """The children."""

    @property
    def number_of_children(self) -> int:
        """How many children count."""
        return len(self.children)


@dataclass(eq=False)
class ReservedShare(CaseFraction):
    """Articles 913, 914-1 and 916: the share of the estate reserved for the heirs."""


@dataclass(eq=False)
class ReserveBase(CaseAmount):
    """Article 917: the estate the reserved share is taken of."""


@dataclass(eq=False)
class ReservedAmount(CaseAmount):
    """Article 912: the amount reserved for the heirs."""


# %% provisions


@dataclass
class ChildCountedProvision(ScopeProvision[ChildCounted]):
    """
    Article 913: a child who renounces the succession counts among the children the
    deceased leaves only where represented, or bound to return a gift under article
    845; every other child counts.
    """

    def query(self) -> Query:
        child = variable(Child, domain=self.case.children)
        counted = deduced_variable(ChildCounted)
        query = an(entity(counted).where(child.renounced_succession == False))
        with query:
            add(counted, inference(ChildCounted)(child=child, holds=True))
            with alternative(child.is_represented == True):
                add(counted, inference(ChildCounted)(child=child, holds=True))
            with alternative(child.must_return_gift == True):
                add(counted, inference(ChildCounted)(child=child, holds=True))
            with alternative():
                add(counted, inference(ChildCounted)(child=child, holds=False))
        return query


@dataclass
class CountedChildrenProvision(ScopeProvision[CountedChildren]):
    """The children who count under article 913."""

    def query(self) -> Query:
        counted = variable(
            ChildCounted, domain=ChildCountedProvision(case=self.case).conclusions
        )
        children = an(entity(counted.child).where(counted.holds == True)).tolist()
        return an(entity(inference(CountedChildren)(case=self.case, children=children)))


@dataclass
class ReservedShareProvision(ScopeProvision[ReservedShare]):
    """
    Article 913: a half of the estate is reserved for one child, two thirds for two,
    three quarters for three or more. Without children, article 914-1 reserves a
    quarter for a spouse the deceased was not divorced from, and article 916 nothing.
    """

    def query(self) -> Query:
        children = variable(
            CountedChildren, domain=CountedChildrenProvision(case=self.case).conclusions
        )
        case = children.case
        share = deduced_variable(ReservedShare)
        query = an(entity(share).where(children.number_of_children == 1))
        with query:
            add(share, inference(ReservedShare)(case=case, fraction=Fraction(1, 2)))
            with alternative(children.number_of_children == 2):
                add(share, inference(ReservedShare)(case=case, fraction=Fraction(1, 3)))
            with alternative(children.number_of_children >= 3):
                add(share, inference(ReservedShare)(case=case, fraction=Fraction(1, 4)))
            with alternative(case.surviving_spouse_not_divorced == True):
                add(
                    share,
                    inference(ReservedShare)(case=case, fraction=1 - Fraction(3, 4)),
                )
            with alternative():
                add(share, inference(ReservedShare)(case=case, fraction=Fraction(0)))
        return query


@dataclass
class ReserveBaseProvision(ScopeProvision[ReserveBase]):
    """
    Article 917: the whole estate, less the usufructs and life annuities the heirs did
    not choose to count towards the reserved portion.
    """

    def query(self) -> Query:
        interest = variable(LifeInterest, domain=self.case.life_interests)
        excluded = an(
            entity(total(interest.value, default=Money.zero)).where(
                interest.counts_towards_reserve == False
            )
        ).first()
        case = variable(ReservedPortionCase, domain=[self.case])
        return an(
            entity(
                inference(ReserveBase)(case=case, amount=case.total_estate - excluded)
            )
        )


@dataclass
class ReservedAmountProvision(ScopeProvision[ReservedAmount]):
    """Article 912: the reserved share of the estate article 917 leaves."""

    def query(self) -> Query:
        base = variable(
            ReserveBase, domain=ReserveBaseProvision(case=self.case).conclusions
        )
        share = variable(
            ReservedShare, domain=ReservedShareProvision(case=self.case).conclusions
        )
        return an(
            entity(
                inference(ReservedAmount)(
                    case=base.case, amount=base.amount * share.fraction
                )
            )
        )


# %% test files


class InheritanceTestFile(ScopeTestFile, StrEnum):
    """The test files of Catala's ``droit_successions`` example."""

    RESERVED_PORTION = "tests_droit_succession.catala_fr"
    """The tests of the reserved portion."""

    @property
    def directory(self) -> Path:
        """:file:`droit_successions/tests`."""
        return CatalaDirectory.ROOT / "droit_successions" / "tests"

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """The reserved portion."""
        return [ReservedPortionCase]
