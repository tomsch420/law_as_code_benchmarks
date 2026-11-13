"""
What the provisions of a Catala example draw conclusions about, and the conclusions.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field

from krrood.symbol_graph.symbol_graph import Symbol
from typing_extensions import Hashable

# %% conclusions


@dataclass(eq=False)
class CatalaConclusion(Symbol, ABC):
    """
    What a provision of a Catala example concludes.
    """


# %% assessed cases


@dataclass(eq=False)
class AssessedCase:
    """
    A case the provisions of a Catala example draw conclusions about, keeping them.
    """

    drawn_conclusions: dict[Hashable, list[CatalaConclusion]] = field(
        default_factory=dict, kw_only=True
    )
    """
    The conclusions each provision drew about the case, by provision.
    """
