"""
SARA's own Prolog program answering a case, timed, for comparison with the krrood model.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from law_as_code_benchmarks.sara.case import SaraDirectory

# %% the reference run


class ReferenceRunKey(StrEnum):
    """The keys of the JSON object :file:`answer_case.pl` prints."""

    PASSED = "passed"
    """Whether the case's test directive succeeded."""

    SECONDS = "seconds"
    """The wall-clock time of the test directive alone."""


@dataclass(frozen=True)
class ReferenceRun:
    """SARA's program answering one case's test goal, the statutes and the case loaded beforehand."""

    passed: bool | None
    """Whether the program gives the case's reference answer; None where the case holds no test."""

    seconds: float | None
    """How long the program took to answer, loading excluded; None where the case holds no test."""

    @classmethod
    def from_identifier(cls, identifier: str, swipl: str = "swipl") -> ReferenceRun:
        """
        :param identifier: The case's identifier.
        :param swipl: The SWI-Prolog executable that runs SARA's program.
        :return: The program's run on the case.
        """
        output = subprocess.run(
            [
                swipl,
                str(Path(__file__).with_name("answer_case.pl")),
                "--",
                str(SaraDirectory.CASES / f"{identifier}.pl"),
            ],
            cwd=SaraDirectory.ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        payload = json.loads(output.strip().splitlines()[-1])
        return cls(
            passed=payload[ReferenceRunKey.PASSED],
            seconds=payload[ReferenceRunKey.SECONDS],
        )
