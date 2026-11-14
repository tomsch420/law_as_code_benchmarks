"""
The exceptions of the model of Catala's ``impot_revenu`` example.
"""

from __future__ import annotations

from dataclasses import dataclass

from krrood.exceptions import DataclassException
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from law_as_code_benchmarks.catala.money import Money

# %% oracles


@dataclass
class UndistributableAmount(DataclassException):
    """
    An amount the prorata of Catala's oracles refuses to distribute, as its assertions
    do.
    """

    amount: Money
    """The amount."""

    bases: list[Money]
    """
    The bases of the proportion.
    """

    def error_message(self) -> str:
        return (
            f"{self.amount} cannot be distributed over {self.bases}: a base is negative, "
            "every base is nothing, or the amount has cents."
        )

    def suggest_correction(self) -> str:
        return "Give whole euros and bases of which one at least is positive."
