"""
OpenFisca France's YAML tests of family allowances: where they are fetched from, the
situation and month each describes, the outputs it expects within its error margin,
and what the family benefits model computes for them.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from pathlib import Path

import yaml
from krrood.ormatic.utils import classproperty
from krrood.patterns.path_enumeration import PathEnumeration
from typing_extensions import Any

from law_as_code_benchmarks.catala.base_allowance import (
    ChildrenRatioProvision,
    HouseholdBracketProvision,
    PaidBaseAllowanceProvision,
)
from law_as_code_benchmarks.catala.conclusions import HouseholdAmount, ResourceBracket
from law_as_code_benchmarks.catala.domain import Household
from law_as_code_benchmarks.catala.exceptions import AmbiguousConclusion
from law_as_code_benchmarks.catala.provision import (
    FamilyBenefitsProvision,
)
from law_as_code_benchmarks.catala.supplements import (
    AllowanceDegressiveSupplementProvision,
    FamilyAllowanceProvision,
    PaidAgeSupplementsProvision,
)
from law_as_code_benchmarks.openfisca.arithmetic import ArithmeticReader
from law_as_code_benchmarks.openfisca.exceptions import (
    UnexpectedOpenFiscaVariable,
)
from law_as_code_benchmarks.openfisca.situation import Situation
from law_as_code_benchmarks.law.provision import ConclusionType
from law_as_code_benchmarks.law.fetched_test_file import FetchedTestFile
from law_as_code_benchmarks.law.scoring import ReproducibleTest

# %% test files


class OpenFiscaDirectory(PathEnumeration):
    """Where OpenFisca France's tests are fetched to, kept out of the repository."""

    TESTS = Path(__file__).parents[3] / "resources" / "openfisca"
    """The directory holding the fetched test files."""


class OpenFiscaTestFile(FetchedTestFile, StrEnum):
    """
    OpenFisca France's test files of family allowances, ``tests/formulas/af*.yaml``,
    each named as OpenFisca names it.
    """

    FAMILY_ALLOWANCES = "af.yaml"
    """Amounts from 2006 to 2015, shared residences among them."""

    JANUARY_2018 = "af_2018_01.yaml"
    """The cases of January 2018, by resources."""

    APRIL_2018 = "af_2018_04.yaml"
    """The cases of the revaluation of April 2018."""

    APRIL_2020 = "af_2020_04.yaml"
    """A single child overseas, just above the first ceiling, in April 2020."""

    AGE_SUPPLEMENT_2026 = "af_majoration_age_2026.yaml"
    """The age supplement around the reform of March 2026."""

    @classproperty
    def revision(cls) -> str:
        """The commit of OpenFisca France the files are fetched at."""
        return "be579829102c0d9e2e1e9749542f6092faf1fff0"

    @classproperty
    def repository(cls) -> str:
        """OpenFisca France."""
        return "openfisca/openfisca-france"

    @classproperty
    def directory_in_repository(cls) -> str:
        """The tests of formulas."""
        return "tests/formulas"

    @classproperty
    def fetch_script(cls) -> str:
        """The script fetching OpenFisca France's tests."""
        return "scripts/fetch_openfisca_tests.py"

    @property
    def path(self) -> Path:
        """Where the file is fetched to."""
        return OpenFiscaDirectory.TESTS / self.value

    @property
    def is_computed_by_openfisca(self) -> bool:
        """Whether every value the file expects was computed by OpenFisca itself."""
        return self == OpenFiscaTestFile.APRIL_2020

    def read_tests(self) -> list[OpenFiscaTest]:
        """
        :return: The file's tests, in order.
        :raises UnfetchedTestFile: Where the file has not been fetched.
        """
        self.ensure_fetched()
        return self.tests_in(self.path.read_text())

    def tests_in(self, text: str) -> list[OpenFiscaTest]:
        """:return: The tests *text*, a YAML test file, holds, in order and named after this file."""
        return [
            OpenFiscaTest.from_json(self, index, json)
            for index, json in enumerate(yaml.safe_load(text))
        ]


class OpenFiscaComputedTest(StrEnum):
    """
    The tests of :attr:`OpenFiscaTestFile.FAMILY_ALLOWANCES` whose expected values come
    from no published amount and are taken to be OpenFisca's own, by name.
    """

    SHARED_RESIDENCE = (
        "Allocations familiales - Couple, 3 enfants dont 1 en garde alternée"
    )
    """A shared residence in September 2015."""

    SHARED_RESIDENCE_BEFORE_MAY_2007 = (
        "Allocations familiales - Garde alternée avant mai 2007"
    )
    """A shared residence in April 2006."""

    AGE_SUPPLEMENT_SHARED_RESIDENCE = "Majoration âge - Garde alternée"
    """The age supplement of a child in shared residence in April 2015."""

    AGE_SUPPLEMENT_SHARED_RESIDENCE_BEFORE_MAY_2007 = (
        "Majoration âge - Garde alternée avant mai 2007"
    )
    """The age supplement of a child in shared residence in April 2007."""


# %% outputs


class OpenFiscaVariable(StrEnum):
    """The outputs the tests expect, each spelled as OpenFisca France names it."""

    FAMILY_ALLOWANCE = "af"
    """The family allowances paid for the month, gross of the CRDS."""

    BASE_ALLOWANCE = "af_base"
    """The base allowance, age supplements and flat allowance aside."""

    AGE_SUPPLEMENTS = "af_majoration"
    """The age supplements."""

    DEGRESSIVE_SUPPLEMENT = "af_complement_degressif"
    """The degressive supplement to the base allowance and the age supplements."""

    MODULATION_RATE = "af_taux_modulation"
    """The share of the full rates the household's bracket pays."""

    SHARED_RESIDENCE_COEFFICIENT = "af_coeff_garde_alternee"
    """The share of the base allowance shared residences leave the household."""

    def value_computed_for(self, household: Household) -> Fraction:
        """:return: The output's value the family benefits model computes for *household*."""
        match self:
            case OpenFiscaVariable.FAMILY_ALLOWANCE:
                return self.euros(FamilyAllowanceProvision(household=household))
            case OpenFiscaVariable.BASE_ALLOWANCE:
                return self.euros(PaidBaseAllowanceProvision(household=household))
            case OpenFiscaVariable.AGE_SUPPLEMENTS:
                return self.euros(PaidAgeSupplementsProvision(household=household))
            case OpenFiscaVariable.DEGRESSIVE_SUPPLEMENT:
                return self.euros(
                    AllowanceDegressiveSupplementProvision(household=household)
                )
            case OpenFiscaVariable.MODULATION_RATE:
                bracket = self.sole_conclusion(
                    HouseholdBracketProvision(household=household)
                ).bracket
                return (
                    bracket.value.second_child
                    / ResourceBracket.FIRST.value.second_child
                )
            case OpenFiscaVariable.SHARED_RESIDENCE_COEFFICIENT:
                return self.sole_conclusion(
                    ChildrenRatioProvision(household=household)
                ).ratio

    @classmethod
    def euros(cls, provision: FamilyBenefitsProvision[HouseholdAmount]) -> Fraction:
        """:return: The amount *provision* concludes, in euros."""
        return Fraction(cls.sole_conclusion(provision).amount.cents, 100)

    @staticmethod
    def sole_conclusion(
        provision: FamilyBenefitsProvision[ConclusionType],
    ) -> ConclusionType:
        """
        :return: The one conclusion *provision* draws.
        :raises AmbiguousConclusion: Where it does not draw exactly one.
        """
        conclusions = provision.conclusions
        if len(conclusions) != 1:
            raise AmbiguousConclusion(
                provision=type(provision), conclusions=conclusions
            )
        return conclusions[0]


@dataclass(frozen=True)
class ExpectedOutput:
    """An output a test expects."""

    variable: OpenFiscaVariable
    """The output's variable."""

    value: Fraction
    """The value expected."""


@dataclass(frozen=True)
class ErrorMargin:
    """
    How far a computed output may be from the expected value, as OpenFisca's test runner
    allows: an absolute margin, or one relative to the expected value.
    """

    absolute: Fraction = Fraction(0)
    """The absolute margin, used where no relative one is given; exact by default."""

    relative: Fraction | None = None
    """The margin as a share of the expected value; None where the test gives none."""

    def admits(self, expected: Fraction, computed: Fraction) -> bool:
        """:return: Whether *computed* is within the margin of *expected*."""
        allowed = (
            self.absolute if self.relative is None else abs(self.relative * expected)
        )
        return abs(computed - expected) <= allowed


# %% tests


class YamlKey(StrEnum):
    """The keys of a test in a test file."""

    NAME = "name"
    """The test's name."""

    PERIOD = "period"
    """The month the test is for."""

    ABSOLUTE_ERROR_MARGIN = "absolute_error_margin"
    """The absolute margin."""

    RELATIVE_ERROR_MARGIN = "relative_error_margin"
    """The relative margin."""

    INPUT = "input"
    """The situation."""

    OUTPUT = "output"
    """The outputs expected."""


@dataclass
class OpenFiscaTest(ReproducibleTest):
    """A test of a file: a situation in a month, and the outputs expected for it."""

    test_file: OpenFiscaTestFile
    """The file holding the test."""

    number: int
    """The test's place in its file, from one."""

    name: str
    """The test's name, which several tests of a file may share."""

    month: datetime.date
    """The first day of the month the test is for."""

    situation: Situation
    """The situation the test describes."""

    margin: ErrorMargin = field(default_factory=ErrorMargin)
    """How far a computed output may be from the expected value."""

    expected_outputs: list[ExpectedOutput] = field(default_factory=list)
    """The outputs expected."""

    @property
    def identifier(self) -> str:
        """The test's file and number."""
        return f"{self.test_file.value}:{self.number}"

    @property
    def is_computed_by_openfisca(self) -> bool:
        """Whether the values the test expects were computed by OpenFisca itself."""
        return self.test_file.is_computed_by_openfisca or (
            self.name in OpenFiscaComputedTest
        )

    def computed_outputs(self) -> dict[OpenFiscaVariable, Fraction]:
        """:return: The value the family benefits model computes for each output expected."""
        household = self.situation.to_household(self.month)
        return {
            output.variable: output.variable.value_computed_for(household)
            for output in self.expected_outputs
        }

    def is_reproduced(self) -> bool:
        """:return: Whether the model computes every output expected within the margin."""
        computed = self.computed_outputs()
        return all(
            self.margin.admits(output.value, computed[output.variable])
            for output in self.expected_outputs
        )

    @classmethod
    def from_json(
        cls, test_file: OpenFiscaTestFile, index: int, json: dict[str, Any]
    ) -> OpenFiscaTest:
        """
        :param test_file: The file holding the test.
        :param index: The test's place in the file, from zero.
        :param json: The test as the file writes it.
        :return: The test.
        :raises UnexpectedOpenFiscaVariable: Where it expects an output the reader does
            not map.
        """
        name = json[YamlKey.NAME]
        for variable in json[YamlKey.OUTPUT]:
            if variable not in OpenFiscaVariable:
                raise UnexpectedOpenFiscaVariable(test=name, variable=variable)
        relative = json.get(YamlKey.RELATIVE_ERROR_MARGIN)
        return cls(
            test_file=test_file,
            number=index + 1,
            name=name,
            month=datetime.date.fromisoformat(f"{json[YamlKey.PERIOD]}-01"),
            situation=Situation.from_json(name, json[YamlKey.INPUT]),
            margin=ErrorMargin(
                absolute=ArithmeticReader().read(
                    json.get(YamlKey.ABSOLUTE_ERROR_MARGIN, 0)
                ),
                relative=None
                if relative is None
                else ArithmeticReader().read(relative),
            ),
            expected_outputs=[
                ExpectedOutput(
                    variable=OpenFiscaVariable(variable),
                    value=ArithmeticReader().read(value),
                )
                for variable, value in json[YamlKey.OUTPUT].items()
            ],
        )
