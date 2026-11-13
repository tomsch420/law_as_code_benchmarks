"""
Tests of reading the test files of Catala's examples, in English, Polish and French.
"""

from __future__ import annotations

import datetime
from fractions import Fraction
from pathlib import Path

import pytest

from law_as_code_benchmarks.catala.exceptions import (
    AmbiguousAnniversary,
    DurationInDays,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import (
    Assertion,
    CatalaLanguage,
    CatalaProgram,
    CatalaTestReader,
    CatalaValue,
    ConstructorPattern,
    ConstructorWithContent,
    Definition,
    Duration,
    Negation,
    Reference,
    ScopeCall,
    StructureLiteral,
)

# %% reading


def read_program(file_name: str) -> CatalaProgram:
    """:return: The program of :file:`test_files/{file_name}`, read in the language of its suffix."""
    path = Path(__file__).parent / "test_files" / file_name
    return CatalaTestReader(language=CatalaLanguage.from_path(path)).read_program(
        path.read_text()
    )


def test_a_test_scope_and_its_subscopes_are_read_from_a_metadata_block() -> None:
    """
    The test scope of a ``catala-metadata`` block is a test, and declares the scope of
    each subscope without its module.
    """
    (test,) = read_program("employee_discount.catala_en").test_scopes
    assert (test.name, test.subscopes) == (
        "Test1",
        {"section": "QualifiedEmployeeDiscount", "data_": "Data"},
    )


def test_english_statements_are_read() -> None:
    """
    A definition over several lines, a constructor with content, a decimal, and
    assertions negated with ``not`` or bare.
    """
    (test,) = read_program("employee_discount.catala_en").test_scopes
    section = ("section",)
    assert test.statements == [
        Definition(
            target=Reference(parts=section + ("customer_price",)),
            value=Reference(parts=("data_", "price")),
        ),
        Definition(
            target=Reference(parts=section + ("discount_type",)),
            value=Reference(parts=("T", "DiscountType", "Services")),
        ),
        Definition(
            target=Reference(parts=section + ("return_type",)),
            value=ConstructorWithContent(
                constructor=Reference(parts=("T", "ReturnType", "SingleReturn")),
                content=Reference(parts=("data_", "periods")),
            ),
        ),
        Assertion(
            expression=Reference(parts=section + ("gross_profit_percentage",)),
            expected=Fraction(2, 5),
        ),
        Assertion(
            expression=Negation(operand=Reference(parts=section + ("is_property",)))
        ),
        Assertion(expression=Reference(parts=section + ("is_services",))),
    ]


def test_variables_of_data_scopes_resolve_to_their_values() -> None:
    """
    A data scope's variable resolves to its value, within lists and through another
    variable of the data scope, and dollars read with thousands separated by commas.
    """
    program = read_program("employee_discount.catala_en")
    assert program.resolve(Reference(parts=("data_", "price"))) == Money(cents=150050)
    assert program.resolve(Reference(parts=("data_", "periods"))) == [
        StructureLiteral(
            structure=Reference(parts=("T", "Period")),
            fields={
                "begin": datetime.date(2019, 1, 1),
                "end": datetime.date(2020, 1, 1),
            },
        )
    ]


def test_polish_statements_are_read() -> None:
    """
    ``definicja … wynosi`` defines, ``prawda`` is true, ``asercja`` asserts, and złoty
    read with a decimal comma.
    """
    (test,) = read_program("sale_tax.catala_pl").test_scopes
    assert test.statements == [
        Definition(
            target=Reference(parts=("sprzedaż", "kwota")), value=Money(cents=100050)
        ),
        Definition(
            target=Reference(parts=("sprzedaż", "inne_prawa_majątkowe")), value=True
        ),
        Assertion(
            expression=Reference(parts=("sprzedaż", "podatek")),
            expected=Money(cents=1000),
        ),
    ]


# %% scope calls


def test_a_french_scope_call_is_read_with_its_arguments() -> None:
    """
    A test scope defines its result as a call of a scope: a duration in months, euros
    with a space between thousands and a percentage are read, and a constant declared
    outside any scope resolves to its value.
    """
    program = read_program("hiring_grant_call.catala_fr")
    (test,) = program.test_scopes
    (definition, *_) = test.statements
    assert program.resolve(definition.value) == ScopeCall(
        scope=Reference(parts=("F", "AidePourEmbauche")),
        arguments={
            "contrat": ConstructorWithContent(
                constructor=Reference(parts=("CDD",)), content=Duration(months=9)
            ),
            "salaire_annuel_brut": Money.from_euros(30_000),
            "temps_travail": ConstructorWithContent(
                constructor=Reference(parts=("TempsPartiel",)),
                content=Fraction(1, 2),
            ),
            "parcelles": [
                StructureLiteral(
                    structure=Reference(parts=("BCAE7", "ParcelleTerreArable")),
                    fields={"surface_hectares": Fraction(25)},
                )
            ],
        },
    )


def test_an_assertion_with_a_pattern_asserts_the_constructor() -> None:
    """
    ``assertion x sous forme NonRespecté`` asserts that *x* is of the constructor, and a
    bare assertion that its expression holds.
    """
    (test,) = read_program("hiring_grant_call.catala_fr").test_scopes
    (_, holds, pattern) = test.statements
    assert holds == Assertion(expression=Reference(parts=("calcul", "éligibilité")))
    assert pattern.asserted_value() == (
        Reference(parts=("calcul", "respect")),
        ConstructorPattern(constructor=Reference(parts=("NonRespecté",))),
    )


@pytest.mark.parametrize(
    "value, is_matched",
    [
        (Reference(parts=("NonRespecté",)), True),
        (
            ConstructorWithContent(
                constructor=Reference(parts=("NonRespecté",)), content=Fraction(0)
            ),
            True,
        ),
        (Reference(parts=("Respecté",)), False),
        (Fraction(0), False),
    ],
)
def test_a_constructor_pattern_matches_its_constructor_with_or_without_content(
    value: CatalaValue, is_matched: bool
) -> None:
    """
    A pattern matches a value of its constructor, whatever its content, and nothing
    else.
    """
    pattern = ConstructorPattern(constructor=Reference(parts=("BCAE7", "NonRespecté")))
    assert pattern.is_matched_by(value) == is_matched


# %% durations


@pytest.mark.parametrize(
    "duration, day, later",
    [
        (Duration(years=1), datetime.date(2024, 3, 31), datetime.date(2025, 3, 31)),
        (Duration(months=14), datetime.date(2024, 11, 30), datetime.date(2026, 1, 30)),
        (Duration(days=365), datetime.date(2024, 1, 1), datetime.date(2024, 12, 31)),
    ],
)
def test_a_duration_after_a_day_keeps_the_day_of_the_month(
    duration: Duration, day: datetime.date, later: datetime.date
) -> None:
    """
    Years and months keep the day of the month; days count one by one.
    """
    assert duration.date_after(day) == later


@pytest.mark.parametrize(
    "duration, day",
    [
        (Duration(years=1), datetime.date(2024, 2, 29)),
        (Duration(months=1), datetime.date(2025, 1, 31)),
    ],
)
def test_a_duration_landing_on_a_day_the_month_lacks_is_refused(
    duration: Duration, day: datetime.date
) -> None:
    """
    A year after February 29, or a month after January 31, has no day Catala rounds to.
    """
    with pytest.raises(AmbiguousAnniversary):
        duration.date_after(day)


def test_a_duration_counts_its_years_in_months_but_refuses_days() -> None:
    """
    A year counts twelve months; a duration with days cannot be counted in months.
    """
    assert Duration(years=1, months=2).whole_months == 14
    with pytest.raises(DurationInDays):
        Duration(days=30).whole_months
