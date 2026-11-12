"""
Tests of reading the test files of Catala's examples, in English and Polish.
"""

from __future__ import annotations

import datetime
from fractions import Fraction
from pathlib import Path

from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import (
    Assertion,
    CatalaLanguage,
    CatalaProgram,
    CatalaTestReader,
    ConstructorWithContent,
    Definition,
    Negation,
    Reference,
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
