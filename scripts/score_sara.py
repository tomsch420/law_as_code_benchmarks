"""
Prints the modelled provisions' score on SARA's test split.

Run from the repository's root with SWI-Prolog on the path: ``python
scripts/score_sara.py``.
"""

from __future__ import annotations

from law_as_code_benchmarks.sara.case import SaraSplit
from law_as_code_benchmarks.sara.scoring import SplitScore

# %% score

if __name__ == "__main__":
    print(SplitScore.from_split(SaraSplit.TEST).summary())
