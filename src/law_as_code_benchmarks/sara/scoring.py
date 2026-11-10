"""
Scores the modelled provisions on a split of SARA's cases: the share of cases each
answers as its test goal states, entailment and tax amounts apart, with how many cases
are modelled at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import law_as_code_benchmarks.sara.employment_exclusions  # noqa: F401, registers the provisions
from law_as_code_benchmarks.sara.case import SaraCase, SaraSplit
from law_as_code_benchmarks.sara.case_reader import WorldReader
from law_as_code_benchmarks.sara.provision import Provision

# %% one case


class AmountPredicate(StrEnum):
    """
    The predicates SARA asks for an amount by.
    """

    TAX = "tax"
    """
    The tax a person owes for a year: income tax under § 1 and employment tax under §
    3301.
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

    @classmethod
    def from_case(cls, case: SaraCase) -> CaseResult:
        """:return: How the modelled provisions answer *case*."""
        goal = case.test.goal
        provision = Provision.modelling(goal.functor)
        kind = AnswerKind.from_predicate(goal.functor)
        if provision is None:
            return cls(
                identifier=case.identifier,
                kind=kind,
                is_modelled=False,
                is_correct=False,
            )
        holds = provision(
            world=WorldReader.from_facts(case.facts).read(), goal=goal
        ).holds()
        return cls(
            identifier=case.identifier,
            kind=kind,
            is_modelled=True,
            is_correct=holds == case.test.expected_to_hold,
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
        return "\n".join(lines)

    @classmethod
    def from_split(cls, split: SaraSplit, swipl: str = "swipl") -> SplitScore:
        """
        :param split: The split to score.
        :param swipl: The SWI-Prolog executable that expands the cases' rules into facts.
        :return: The score of every case of the split.
        """
        return cls(
            split=split,
            results=[
                CaseResult.from_case(SaraCase.load(identifier, swipl))
                for identifier in split.case_identifiers()
            ],
        )
