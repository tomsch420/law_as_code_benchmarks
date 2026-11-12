"""
A stopwatch timing the stages of answering a benchmark's cases.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

# %% timing


@dataclass
class Stopwatch:
    """
    Measures the wall-clock time between consecutive laps.
    """

    last_lap: float = field(default_factory=time.perf_counter)
    """
    When the last lap ended, by :func:`time.perf_counter`.
    """

    def lap(self) -> float:
        """:return: The seconds since the last lap, which ends now."""
        now = time.perf_counter()
        seconds, self.last_lap = now - self.last_lap, now
        return seconds
