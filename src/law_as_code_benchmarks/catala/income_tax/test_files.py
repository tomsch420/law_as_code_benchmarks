"""
The test files of Catala's ``impot_revenu`` example, under the CeCILL 2.1 licence and so
fetched from catala-examples at a fixed revision rather than kept in the repository.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from krrood.ormatic.utils import classproperty
from krrood.patterns.path_enumeration import PathEnumeration

from law_as_code_benchmarks.catala.income_tax.commercial import (
    CommercialHouseholdCase,
)
from law_as_code_benchmarks.catala.income_tax.non_commercial import (
    NonCommercialHouseholdCase,
)
from law_as_code_benchmarks.catala.income_tax.oracles import (
    DeficitImputationCase,
    ProportionalDistributionCase,
)
from law_as_code_benchmarks.catala.income_tax.parts import PartsCase
from law_as_code_benchmarks.catala.income_tax.wages import (
    DeclarantWagesCase,
    HouseholdWagesCase,
)
from law_as_code_benchmarks.catala.scope_test import ScopeCase, ScopeTest, ScopeTestFile
from law_as_code_benchmarks.law.fetched_test_file import FetchedTestFile


class IncomeTaxDirectory(PathEnumeration):
    """
    Where the test files are fetched to, kept out of the repository.
    """

    TESTS = Path(__file__).parents[4] / "resources" / "catala_impot_revenu"
    """
    The directory holding the fetched test files.
    """


class IncomeTaxTestFile(ScopeTestFile, FetchedTestFile, StrEnum):
    """
    The test files of ``impot_revenu/tests``, each named as catala-examples names it.
    """

    PARTS = "nombre_de_parts.catala_fr"
    """
    Five households' parts.
    """

    PAST_DEFICITS = "deficits_anterieurs.catala_fr"
    """
    One imputation on past deficits.
    """

    PRORATA = "prorata.catala_fr"
    """
    Three distributions in proportion.
    """

    WAGES = "traitements_salaires.catala_fr"
    """
    Eleven declarants' or households' wages and pensions.
    """

    NON_COMMERCIAL = "benefices_non_commerciaux.catala_fr"
    """
    Four households' non-commercial profits.
    """

    COMMERCIAL = "benefices_industriels_commerciaux.catala_fr"
    """
    Three households' industrial and commercial profits.
    """

    @classproperty
    def revision(cls) -> str:
        """
        The commit of catala-examples the files are fetched at.
        """
        return "9e251b932288cf5f4a74af072d203144a057494b"

    @classproperty
    def repository(cls) -> str:
        """
        catala-examples.
        """
        return "CatalaLang/catala-examples"

    @classproperty
    def directory_in_repository(cls) -> str:
        """
        The tests of ``impot_revenu``.
        """
        return "impot_revenu/tests"

    @classproperty
    def fetch_script(cls) -> str:
        """
        The script fetching the income tax tests.
        """
        return "scripts/fetch_catala_income_tax_tests.py"

    @property
    def directory(self) -> Path:
        """
        The directory the files are fetched to.
        """
        return IncomeTaxDirectory.TESTS

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """
        The scopes the example's tests call.
        """
        return [
            PartsCase,
            DeficitImputationCase,
            ProportionalDistributionCase,
            DeclarantWagesCase,
            HouseholdWagesCase,
            NonCommercialHouseholdCase,
            CommercialHouseholdCase,
        ]

    def read_tests(self) -> list[ScopeTest]:
        """
        Extends :meth:`ScopeTestFile.read_tests`.

        :raises UnfetchedTestFile: Where the file has not been fetched.
        """
        self.ensure_fetched()
        return super().read_tests()
