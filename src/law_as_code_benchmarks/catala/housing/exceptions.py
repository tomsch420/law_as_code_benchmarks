"""
The exceptions of the model of Catala's housing aids.
"""

from __future__ import annotations

from dataclasses import dataclass

from krrood.exceptions import DataclassException
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from law_as_code_benchmarks.catala.housing.domain import Occupancy

# %% computing


@dataclass
class UncoveredOccupancy(DataclassException):
    """
    A way of occupying a dwelling that no sector of D823-9 covers.
    """

    occupancy: Occupancy
    """The occupancy."""

    def error_message(self) -> str:
        return (
            f"No sector of D823-9 covers the occupancy {type(self.occupancy).__name__}."
        )

    def suggest_correction(self) -> str:
        return "Add a subclass of DwellingSector listing it in its occupancy_types."
