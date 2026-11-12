"""
SARA's cases: the facts each states, the goal it tests, and the split it belongs to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from krrood.patterns.path_enumeration import PathEnumeration

from law_as_code_benchmarks.sara.exceptions import UnexpectedTestDirectives
from law_as_code_benchmarks.sara.case_rules import FactExpansion
from law_as_code_benchmarks.sara.prolog_term import (
    BuiltinPredicate,
    Clause,
    CompoundTerm,
    Directive,
    Operator,
    PrologReader,
)

# %% where SARA's files are


class SaraDirectory(PathEnumeration):
    """The directories of SARA's archive, as this repository keeps it."""

    ROOT = Path(__file__).parents[3] / "resources" / "sara"
    """The archive's root, which the paths in its cases are relative to."""

    CASES = ROOT / "cases"
    """One Prolog file per case."""

    SPLITS = ROOT / "splits"
    """One file per split, listing its cases' identifiers."""


class SaraSplit(StrEnum):
    """The splits SARA publishes its cases in."""

    TRAIN = "train"
    """The 256 cases for development."""

    TEST = "test"
    """The 120 cases scores are reported on."""

    def case_identifiers(self) -> list[str]:
        """:return: The identifiers of the split's cases, in the order the split lists them."""
        return (SaraDirectory.SPLITS / self.value).read_text().split()


# %% a case


class CaseFileHeading(StrEnum):
    """The comment lines a case file opens its sections with."""

    TEST = "\n% Test"
    """Opens the test directives, after the facts."""


class GoalFunctor(StrEnum):
    """The functors of goals with a meaning of their own in a test directive."""

    NEGATION = Operator.NEGATION.value
    """Negation as failure: the test passes if its argument has no solution."""

    CONJUNCTION = Operator.CONJUNCTION.value
    """Conjunction: the goal holds where both its arguments hold, with the same bindings."""

    UNBOUND = BuiltinPredicate.UNBOUND.value
    """That its argument is unbound: here, bound to an argument a conclusion leaves open."""

    FIRST_DAY_OF_YEAR = BuiltinPredicate.FIRST_DAY_OF_YEAR.value
    """SARA's utility relating a year to the ``YYYY-MM-DD`` string of its January 1."""

    DAY_ORDER = BuiltinPredicate.DAY_ORDER.value
    """SARA's utility holding where its first day is not after its second."""

    HALT = "halt"
    """Ends the Prolog session; a case's last directive, testing nothing."""


@dataclass(frozen=True)
class TestGoal:
    """The goal a case tests, and whether it is meant to hold or to fail."""

    goal: CompoundTerm
    """The goal, with ``None`` for each argument the test leaves unbound."""

    expected_to_hold: bool
    """Whether the goal has a solution under SARA's Prolog program."""

    @classmethod
    def from_directive(cls, directive: CompoundTerm) -> TestGoal:
        """
        :param directive: The goal of a case's test directive.
        :return: The test it states.
        """
        if directive.functor == GoalFunctor.NEGATION:
            return cls(goal=directive.arguments[0], expected_to_hold=False)
        return cls(goal=directive, expected_to_hold=True)


@dataclass
class SaraCase:
    """One case: the facts it states and the goal it tests."""

    identifier: str
    """The case's file name without its extension, such as ``tax_case_8``."""

    facts: list[CompoundTerm] = field(default_factory=list)
    """Every ground fact the case states, those its rules generate included."""

    test: TestGoal | None = None
    """The goal the case tests."""

    @classmethod
    def load(cls, identifier: str) -> SaraCase:
        """
        :param identifier: The case's identifier.
        :return: The case, its rules expanded into facts.
        :raises UnexpectedTestDirectives: For a case testing other than one goal.
        """
        text = (SaraDirectory.CASES / f"{identifier}.pl").read_text()
        facts_text, tests_text = text.split(CaseFileHeading.TEST, maxsplit=1)
        reader = PrologReader()
        clauses = [
            statement
            for statement in reader.read_clauses(cls.terminated(facts_text))
            if isinstance(statement, Clause)
        ]
        tests = [
            statement.goal
            for statement in reader.read_clauses(tests_text)
            if isinstance(statement, Directive) and statement.goal != GoalFunctor.HALT
        ]
        if len(tests) != 1:
            raise UnexpectedTestDirectives(
                identifier=identifier, number_of_tests=len(tests)
            )
        return cls(
            identifier=identifier,
            facts=FactExpansion(clauses=clauses).facts,
            test=TestGoal.from_directive(tests[0]),
        )

    @staticmethod
    def terminated(text: str) -> str:
        """
        :return: *text*, ending in a full stop: a few cases leave the full stop off their
            last fact.
        """
        stripped = text.rstrip()
        return stripped if stripped.endswith(Operator.END) else stripped + Operator.END
