"""
SARA's cases: the facts each states, the goal it tests, and the split it belongs to.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from krrood.patterns.path_enumeration import PathEnumeration

from law_as_code_benchmarks.sara.exceptions import UnexpectedTestDirectives
from law_as_code_benchmarks.sara.prolog_term import CompoundTerm, TermReader

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


class CasePayloadKey(StrEnum):
    """The keys of the JSON object :file:`ground_case.pl` writes a case as."""

    FACTS = "facts"
    """The ground facts the case states."""

    TESTS = "tests"
    """The goals of the case's test directives."""


class GoalFunctor(StrEnum):
    """The functors of goals with a meaning of their own in a test directive."""

    NEGATION = "\\+"
    """Negation as failure: the test passes if its argument has no solution."""


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
    def load(cls, identifier: str, swipl: str = "swipl") -> SaraCase:
        """
        :param identifier: The case's identifier.
        :param swipl: The SWI-Prolog executable that expands the case's rules into facts.
        :return: The case, its facts expanded.
        """
        output = subprocess.run(
            [
                swipl,
                str(Path(__file__).with_name("ground_case.pl")),
                "--",
                str(SaraDirectory.CASES / f"{identifier}.pl"),
            ],
            cwd=SaraDirectory.ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        payload = json.loads(output)
        reader = TermReader()
        tests = [reader.read(test) for test in payload[CasePayloadKey.TESTS]]
        if len(tests) != 1:
            raise UnexpectedTestDirectives(
                identifier=identifier, number_of_tests=len(tests)
            )
        return cls(
            identifier=identifier,
            facts=[reader.read(fact) for fact in payload[CasePayloadKey.FACTS]],
            test=TestGoal.from_directive(tests[0]),
        )
