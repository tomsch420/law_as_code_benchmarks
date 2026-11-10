"""
The exceptions of the SARA benchmark's model.
"""

from __future__ import annotations

from dataclasses import dataclass

from krrood.exceptions import DataclassException
from typing_extensions import Any

# %% loading cases


@dataclass
class UnexpectedTestDirectives(DataclassException):
    """
    A case that does not test exactly one goal.
    """

    identifier: str
    """The case's identifier."""

    number_of_tests: int
    """
    How many test directives the case holds.
    """

    def error_message(self) -> str:
        return f"Case {self.identifier} holds {self.number_of_tests} test directives instead of one."

    def suggest_correction(self) -> str:
        return "Check that the case file is one of SARA's, unchanged."


# %% reading a case into the domain model


@dataclass
class ConflictingFacts(DataclassException):
    """
    A case relating an event to several values where the domain model takes one.
    """

    event: Any
    """The event's identifier."""

    functor: str
    """
    The functor of the facts, such as ``start_``.
    """

    def error_message(self) -> str:
        return f"The case states several {self.functor} facts for {self.event}."

    def suggest_correction(self) -> str:
        return "Model the value as a list where a case may state several."


@dataclass
class MissingFact(DataclassException):
    """
    A case leaving out a fact the domain model needs to read an event.
    """

    event: Any
    """The event's identifier."""

    functor: str
    """
    The functor of the missing fact, such as ``agent_``.
    """

    def error_message(self) -> str:
        return f"The case states no {self.functor} fact for {self.event}."

    def suggest_correction(self) -> str:
        return (
            "Make the value optional in the domain model where a case may leave it out."
        )
