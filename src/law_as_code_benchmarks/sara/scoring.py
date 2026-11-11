"""
Scores the modelled provisions on a split of SARA's cases: the share of cases each
answers as its test goal states, entailment and tax amounts apart, with how many cases
are modelled at all, and how long each stage of answering takes.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from enum import StrEnum

import law_as_code_benchmarks.sara.employment_tax  # noqa: F401, registers the provisions
import law_as_code_benchmarks.sara.family_status  # noqa: F401, registers the provisions
import law_as_code_benchmarks.sara.taxable_income  # noqa: F401, registers the provisions
import law_as_code_benchmarks.sara.income_tax  # noqa: F401, registers the provisions
from law_as_code_benchmarks.sara.case import SaraCase, SaraSplit
from law_as_code_benchmarks.sara.case_reader import WorldReader
from law_as_code_benchmarks.sara.goal import Goal
from law_as_code_benchmarks.sara.reference import ReferenceRun

# %% one case


class AmountPredicate(StrEnum):
    """
    The predicates SARA asks for an amount by.
    """

    TAX = "tax"
    """
    The tax a person owes for a year: income tax under `§ 1 <https://www.law.cornell.edu/uscode/text/26/1>`__ and employment tax under 
    `§ 3301 <https://www.law.cornell.edu/uscode/text/26/3301>`__.
    """


class AnswerKind(StrEnum):
    """
    What a case asks for.
    """

    ENTAILMENT = "entailment"
    """
    Whether a provision applies.
    """

    AMOUNT = "amount"
    """
    How much tax is owed.
    """

    @classmethod
    def from_predicate(cls, predicate_name: str) -> AnswerKind:
        """:return: What a test goal of the predicate named *predicate_name* asks for."""
        return cls.AMOUNT if predicate_name in set(AmountPredicate) else cls.ENTAILMENT


class TimedStage(StrEnum):
    """The stages of answering a case that are timed, each named as the summary reports it."""

    EXPANDING_FACTS = "expanding the case's facts (SWI-Prolog)"
    """Expanding the facts the case states, those its rules generate included."""

    READING_DOMAIN_MODEL = "reading the domain model"
    """Building the domain model from the facts."""

    ANSWERING_IN_KRROOD = "answering in krrood"
    """Answering the test goal with the krrood rules."""

    ANSWERING_IN_PROLOG = "answering in SARA's Prolog program"
    """Answering the test goal with SARA's program, the statutes and the case loaded beforehand."""


@dataclass
class Stopwatch:
    """Measures the wall-clock time between consecutive laps."""

    last_lap: float = field(default_factory=time.perf_counter)
    """When the last lap ended, by :func:`time.perf_counter`."""

    def lap(self) -> float:
        """:return: The seconds since the last lap, which ends now."""
        now = time.perf_counter()
        seconds, self.last_lap = now - self.last_lap, now
        return seconds


@dataclass(frozen=True)
class CaseResult:
    """
    How the model answered one case.
    """

    identifier: str
    """
    The case's identifier.
    """

    kind: AnswerKind
    """
    What the case asks for.
    """

    is_modelled: bool
    """
    Whether the provision the case asks about is modelled.
    """

    is_correct: bool
    """
    Whether the model answered as the case's test goal states; never for an unmodelled
    case.
    """

    durations: dict[TimedStage, float | None] = field(default_factory=dict)
    """The seconds each stage took, None where SARA's program found no test; empty for an unmodelled case."""

    reference_passed: bool | None = None
    """Whether SARA's program gives the case's reference answer; None for an unmodelled case."""

    @classmethod
    def from_identifier(cls, identifier: str, swipl: str = "swipl") -> CaseResult:
        """
        :param identifier: The case's identifier.
        :param swipl: The SWI-Prolog executable that expands the case's facts and runs SARA's program.
        :return: How the modelled provisions answer the case, and how long each stage took.
        """
        stopwatch = Stopwatch()
        case = SaraCase.load(identifier, swipl)
        expanding_facts = stopwatch.lap()
        goal = Goal.from_term(case.test.goal)
        kind = AnswerKind.from_predicate(case.test.goal.functor)
        if goal is None:
            return cls(
                identifier=identifier, kind=kind, is_modelled=False, is_correct=False
            )
        stopwatch.lap()
        world = WorldReader.from_facts(case.facts).read()
        reading_domain_model = stopwatch.lap()
        holds = goal.holds(world)
        answering_in_krrood = stopwatch.lap()
        reference = ReferenceRun.from_identifier(identifier, swipl)
        return cls(
            identifier=identifier,
            kind=kind,
            is_modelled=True,
            is_correct=holds == case.test.expected_to_hold,
            durations={
                TimedStage.EXPANDING_FACTS: expanding_facts,
                TimedStage.READING_DOMAIN_MODEL: reading_domain_model,
                TimedStage.ANSWERING_IN_KRROOD: answering_in_krrood,
                TimedStage.ANSWERING_IN_PROLOG: reference.seconds,
            },
            reference_passed=reference.passed,
        )


# %% a split


@dataclass
class SplitScore:
    """
    The results of every case of a split.
    """

    split: SaraSplit
    """
    The split scored.
    """

    results: list[CaseResult] = field(default_factory=list)
    """
    One result per case, in the split's order.
    """

    def results_of(self, kind: AnswerKind) -> list[CaseResult]:
        """:return: The results of the cases asking for *kind*."""
        return [result for result in self.results if result.kind == kind]

    def summary(self) -> str:
        """:return: For each kind of answer, the correct, modelled and total numbers of cases."""
        lines = [f"SARA {self.split.value} split, {len(self.results)} cases"]
        for kind in AnswerKind:
            results = self.results_of(kind)
            modelled = [result for result in results if result.is_modelled]
            correct = [result for result in modelled if result.is_correct]
            lines.append(
                f"{kind.value}: {len(correct)} of {len(modelled)} modelled cases correct; "
                f"{len(modelled)} of {len(results)} cases modelled"
            )
        return "\n".join(lines + self.timing_summary())

    def timing_summary(self) -> list[str]:
        """:return: For each timed stage, the median, maximum and total time over the modelled cases."""
        modelled = [result for result in self.results if result.is_modelled]
        if not modelled:
            return []
        reference_passed = [result for result in modelled if result.reference_passed]
        lines = [
            (
                f"SARA's Prolog program gives the reference answer in {len(reference_passed)} of "
                f"{len(modelled)} modelled cases"
            ),
            f"time per modelled case, over {len(modelled)} cases:",
        ]
        for stage in TimedStage:
            seconds = [
                result.durations[stage]
                for result in modelled
                if result.durations[stage] is not None
            ]
            lines.append(
                f"  {stage.value}: {statistics.median(seconds) * 1000:.3f} ms median, "
                f"{max(seconds) * 1000:.3f} ms maximum, {sum(seconds) * 1000:.1f} ms total"
            )
        return lines

    @classmethod
    def from_split(cls, split: SaraSplit, swipl: str = "swipl") -> SplitScore:
        """
        :param split: The split to score.
        :param swipl: The SWI-Prolog executable that expands the cases' facts and runs SARA's program.
        :return: The score of every case of the split.
        """
        return cls(
            split=split,
            results=[
                CaseResult.from_identifier(identifier, swipl)
                for identifier in split.case_identifiers()
            ],
        )
