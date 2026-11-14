"""
A provision of a law as a krrood rule, drawing conclusions about a case, which keeps
them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from krrood.entity_query_language.query.query import Query
from krrood.patterns.subclass_safe_generic import SubClassSafeGeneric
from krrood.symbol_graph.symbol_graph import Symbol
from typing_extensions import Generic, Hashable, TypeVar

# %% conclusions


@dataclass(eq=False)
class Conclusion(Symbol, ABC):
    """
    What a provision concludes about a case.
    """


ConclusionType = TypeVar("ConclusionType", bound=Conclusion)


# %% assessed cases


@dataclass(eq=False)
class AssessedCase:
    """
    A case provisions draw conclusions about, keeping them.
    """

    drawn_conclusions: dict[Hashable, list[Conclusion]] = field(
        default_factory=dict, kw_only=True
    )
    """
    The conclusions each provision drew about the case, by the provision's
    :meth:`Provision.drawn_conclusions_key`.
    """


# %% provisions


@dataclass
class Provision(Generic[ConclusionType], SubClassSafeGeneric, ABC):
    """
    A provision of a law, drawing its conclusions about a case once.
    """

    @property
    @abstractmethod
    def assessed_case(self) -> AssessedCase:
        """
        The case the provision draws its conclusions about.
        """

    @abstractmethod
    def query(self) -> Query:
        """:return: A query inferring the provision's conclusions about the case."""

    def draw_conclusions(self) -> list[ConclusionType]:
        """:return: The provision's conclusions about the case, drawn anew."""
        return self.query().tolist()

    def drawn_conclusions_key(self) -> Hashable:
        """:return: What the provision's conclusions are kept under in the case: its class, where they depend on nothing else."""
        return type(self)

    @property
    def conclusions(self) -> list[ConclusionType]:
        """
        The provision's conclusions about the case, drawn once and kept in it.
        """
        drawn = self.assessed_case.drawn_conclusions
        key = self.drawn_conclusions_key()
        if key not in drawn:
            drawn[key] = self.draw_conclusions()
        return drawn[key]
