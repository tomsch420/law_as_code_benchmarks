"""
The tests of Catala's examples as krrood cases: a test scope gives a scope its inputs,
and asserts what its outputs are. A :class:`ScopeCase` holds the inputs of one scope,
mapped onto a domain dataclass, and answers its outputs with the example's provisions.
"""

from __future__ import annotations

import inspect
import sys
import types
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from fractions import Fraction
from pathlib import Path

from krrood.ormatic.utils import classproperty
from typing_extensions import Any, Self, get_args, get_origin

from law_as_code_benchmarks.catala.assessment import AssessedCase, CatalaConclusion
from law_as_code_benchmarks.catala.exceptions import (
    AmbiguousConclusion,
    UnexpectedCatalaStatement,
    UnknownCatalaConstructor,
    UnmodelledScope,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.provision import ConclusionType, Provision
from law_as_code_benchmarks.catala.reader import (
    Application,
    Assertion,
    CatalaLanguage,
    CatalaProgram,
    CatalaTestReader,
    CatalaValue,
    ConstructorPattern,
    ConstructorWithContent,
    Definition,
    ListMap,
    Reference,
    ScopeBody,
    ScopeCall,
    StructureLiteral,
)

# %% tests


class CatalaTest(ABC):
    """A test scope of a Catala example, and whether the model reproduces it."""

    @property
    @abstractmethod
    def identifier(self) -> str:
        """The test's file and scope, which name it uniquely."""

    @abstractmethod
    def is_reproduced(self) -> bool:
        """:return: Whether the model concludes everything the test asserts."""


# %% records


@dataclass
class CatalaRecord:
    """
    A dataclass a Catala structure, or a scope's inputs, map onto: each Catala field
    onto the field :attr:`catala_names` names, its value converted to the field's type.
    """

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The field each Catala name maps onto, where the two differ."""
        return {}

    @classmethod
    def from_catala(cls, values: dict[str, CatalaValue]) -> Self:
        """:return: The record of *values*, by Catala name, converted to the types of the fields they map onto."""
        arguments = {}
        for catala_name, value in values.items():
            field_name = cls.catala_names.get(catala_name, catala_name)
            arguments[field_name] = cls.converted(value, cls.field_type(field_name))
        return cls(**arguments)

    @classmethod
    def field_type(cls, field_name: str) -> Any:
        """:return: The type of the field *field_name*, evaluated in the module of the class declaring it."""
        declaring = next(
            klass
            for klass in cls.__mro__
            if field_name in vars(klass).get("__annotations__", {})
        )
        annotation = declaring.__annotations__[field_name]
        if not isinstance(annotation, str):
            return annotation
        return eval(annotation, vars(sys.modules[declaring.__module__]))

    @classmethod
    def converted(cls, value: CatalaValue, field_type: Any) -> Any:
        """
        :return: *value* as *field_type*: a structure as its record, an enumeration's
            constructor as the member of that name, each element of a list, a whole
            number as a fraction where one is asked; any other value as it is.
        """
        origin = get_origin(field_type)
        if origin is list:
            (element_type,) = get_args(field_type)
            return [cls.converted(element, element_type) for element in value]
        if origin is types.UnionType:
            (field_type,) = [
                argument
                for argument in get_args(field_type)
                if argument is not type(None)
            ]
        if not inspect.isclass(field_type):
            return value
        if issubclass(field_type, CatalaVariant) and isinstance(
            value, (ConstructorWithContent, Reference)
        ):
            return field_type.from_constructor(value)
        if issubclass(field_type, CatalaRecord) and isinstance(value, StructureLiteral):
            return field_type.from_catala(value.fields)
        if issubclass(field_type, Enum) and isinstance(value, Reference):
            return field_type(value.last_part)
        if field_type is Fraction and isinstance(value, int):
            return Fraction(value)
        return value


@dataclass
class CatalaVariant(CatalaRecord, ABC):
    """
    A Catala enumeration whose constructors carry content, mapped onto a class with one
    subclass per constructor. A subclass holds the constructor's content in the field
    :attr:`content_field` names.
    """

    @classproperty
    def catala_constructor(cls) -> str | None:
        """The constructor the class stands for; None for the class of the whole enumeration."""
        return None

    @classproperty
    def content_field(cls) -> str | None:
        """The field holding the constructor's content; None for a constructor without content."""
        return None

    @classmethod
    def from_constructor(cls, value: ConstructorWithContent | Reference) -> Self:
        """
        :return: The instance of the subclass standing for *value*'s constructor, holding
            its content.
        :raises UnknownCatalaConstructor: Where no subclass stands for it.
        """
        constructor = (
            value.constructor if isinstance(value, ConstructorWithContent) else value
        ).last_part
        variant = next(
            (
                subclass
                for subclass in cls.subclasses()
                if subclass.catala_constructor == constructor
            ),
            None,
        )
        if variant is None:
            raise UnknownCatalaConstructor(enumeration=cls, constructor=constructor)
        if isinstance(value, Reference):
            return variant()
        return variant.from_catala({variant.content_field: value.content})

    @classmethod
    def subclasses(cls) -> list[type[CatalaVariant]]:
        """:return: The class and every class deriving from it."""
        return [cls] + [
            descendant
            for subclass in cls.__subclasses__()
            for descendant in subclass.subclasses()
        ]


# %% scope cases


@dataclass(eq=False)
class ScopeCase(CatalaRecord, AssessedCase, ABC):
    """The inputs a test gives one scope of an example, which the example's provisions answer the scope's outputs about."""

    @classproperty
    @abstractmethod
    def catala_scope(cls) -> str:
        """The name of the scope, without its module."""

    @classproperty
    @abstractmethod
    def catala_outputs(cls) -> type[StrEnum]:
        """The outputs of the scope the case answers, each valued as Catala names it."""

    @abstractmethod
    def output(self, variable: str) -> CatalaValue:
        """:return: The value the provisions conclude for the scope's output *variable*; None where they conclude none."""

    def concludes_every_output(self) -> bool:
        """:return: Whether the provisions conclude a value for each of :attr:`catala_outputs`."""
        return all(
            self.output(variable) is not None for variable in self.catala_outputs
        )

    def sole_conclusion(
        self, provision_type: type[ScopeProvision[ConclusionType]]
    ) -> ConclusionType | None:
        """
        :return: The one conclusion the provision of *provision_type* draws about the
            case; None where it draws none.
        :raises AmbiguousConclusion: Where it draws several.
        """
        conclusions = provision_type(case=self).conclusions
        if len(conclusions) > 1:
            raise AmbiguousConclusion(provision=provision_type, conclusions=conclusions)
        return conclusions[0] if conclusions else None


# %% provisions about scope cases


@dataclass
class ScopeProvision(Provision[ConclusionType], ABC):
    """A provision of an example whose tests give scopes their inputs, drawing its conclusions about one scope case."""

    case: ScopeCase
    """The scope case assessed."""

    @property
    def assessed_case(self) -> AssessedCase:
        return self.case


@dataclass(eq=False)
class CaseConclusion(CatalaConclusion):
    """A conclusion about a scope case."""

    case: ScopeCase
    """The case."""


@dataclass(eq=False)
class CaseAmount(CaseConclusion):
    """An amount a provision gives a scope case."""

    amount: Money = field(default_factory=lambda: Money.zero)
    """The amount."""


@dataclass(eq=False)
class CaseFraction(CaseConclusion):
    """A fraction a provision gives a scope case, such as a share or a rate."""

    fraction: Fraction = Fraction(0)
    """The fraction."""


@dataclass(eq=False)
class CaseCondition(CaseConclusion):
    """Whether a condition of a provision holds for a scope case, false where no rule says it does."""

    holds: bool = False
    """Whether the condition holds."""


@dataclass
class OutputAssertion:
    """That a scope's output has a value."""

    case: ScopeCase
    """The scope's inputs."""

    variable: str
    """The output."""

    expected: CatalaValue | ConstructorPattern
    """Its value, or the constructor its value is of."""

    argument_output: str | None = None
    """The output the output, a function, is applied to; None for an output that is no function."""

    def is_reproduced(self) -> bool:
        """
        :return: Whether the provisions conclude the value for the output, applied to
            its argument output where it is a function, or one of the constructor; an
            enumeration's member matches a constructor of its name.
        """
        concluded = self.case.output(self.variable)
        if self.argument_output is not None:
            argument = self.case.output(self.argument_output)
            concluded = None if argument is None else concluded(argument)
        if isinstance(self.expected, ConstructorPattern):
            return self.expected.is_matched_by(concluded)
        if isinstance(self.expected, Reference) and isinstance(concluded, StrEnum):
            return concluded == self.expected.last_part
        return concluded == self.expected


@dataclass
class ScopeTest(CatalaTest):
    """A test scope giving one scope its inputs and asserting its outputs."""

    file_name: str
    """The name of the file holding the test."""

    scope: str
    """The test scope's name."""

    assertions: list[OutputAssertion] = field(default_factory=list)
    """What the test asserts."""

    unasserted_cases: list[ScopeCase] = field(default_factory=list)
    """The scopes the test calls but asserts nothing of, which Catala's test still requires to compute every output."""

    @property
    def identifier(self) -> str:
        return f"{self.file_name}:{self.scope}"

    def is_reproduced(self) -> bool:
        return all(assertion.is_reproduced() for assertion in self.assertions) and all(
            case.concludes_every_output() for case in self.unasserted_cases
        )

    @classmethod
    def from_scope(
        cls,
        file_name: str,
        scope: ScopeBody,
        program: CatalaProgram,
        cases: list[type[ScopeCase]],
    ) -> ScopeTest:
        """
        :param file_name: The name of the file holding the scope.
        :param scope: A test scope.
        :param program: The file's scopes, which resolve variables of its data scopes.
        :param cases: The kinds of case the example models, one per scope.
        :return: The test the scope states, about the subscopes the example models; a
            variable of the test defined as a subscope's output, or as an output applied
            to another, stands for it, and the result the command line prints for one
            the test does not assert is asserted.
        :raises UnmodelledScope: Where the test asserts something of a subscope, or
            calls a scope, that no case models.
        """
        subscopes = dict(scope.subscopes)
        inputs: dict[str, dict[str, CatalaValue]] = {
            subscope: {} for subscope in subscopes
        }
        asserted = []
        outputs: dict[str, Reference | Application] = {}
        for statement in scope.statements:
            match statement:
                case Definition(target=Reference(parts=(subscope, variable))):
                    inputs[subscope][variable] = program.resolve(statement.value)
                case Definition(
                    target=Reference(parts=(result,)), value=ScopeCall() as call
                ):
                    subscopes[result] = call.scope.last_part
                    inputs[result] = program.resolve(call).arguments
                case Definition(
                    target=Reference(parts=(result,)), value=ListMap() as mapped
                ):
                    for index, call in enumerate(program.resolve(mapped).scope_calls()):
                        subscopes[f"{result}[{index}]"] = call.scope.last_part
                        inputs[f"{result}[{index}]"] = call.arguments
                case Definition(
                    target=Reference(parts=(result,)),
                    value=Reference(parts=(_, _))
                    | Application(
                        function=Reference(parts=(_, _)),
                        argument=Reference(parts=(_, _)),
                    ) as output,
                ):
                    outputs[result] = output
                case Assertion():
                    asserted.append(statement.asserted_value())
                case _:
                    raise UnexpectedCatalaStatement(
                        scope=scope.name, statement=statement
                    )
        asserted_variables = {
            expression.parts[0]
            for expression, _ in asserted
            if isinstance(expression, Reference)
        }
        for variable, _ in program.stated_results.get(scope.name, {}).items():
            if variable in outputs and variable not in asserted_variables:
                asserted.append(
                    (
                        Reference(parts=(variable,)),
                        program.stated_result(scope.name, variable),
                    )
                )
        case_types = {case.catala_scope: case for case in cases}
        built = {}
        assertions = []
        for expression, expected in asserted:
            if isinstance(expression, Reference) and expression.parts[0] in outputs:
                expression = outputs[expression.parts[0]]
            argument_output = None
            if isinstance(expression, Application):
                argument_output = expression.argument.last_part
                expression = expression.function
            if not (isinstance(expression, Reference) and len(expression.parts) == 2):
                raise UnexpectedCatalaStatement(scope=scope.name, statement=expression)
            subscope, variable = expression.parts
            scope_name = subscopes[subscope]
            if scope_name not in case_types:
                raise UnmodelledScope(scope=scope_name)
            if subscope not in built:
                built[subscope] = case_types[scope_name].from_catala(inputs[subscope])
            assertions.append(
                OutputAssertion(
                    case=built[subscope],
                    variable=variable,
                    expected=program.resolve(expected),
                    argument_output=argument_output,
                )
            )
        unasserted_cases = []
        for result in sorted(subscopes.keys() - scope.subscopes.keys() - built.keys()):
            if subscopes[result] not in case_types:
                raise UnmodelledScope(scope=subscopes[result])
            unasserted_cases.append(
                case_types[subscopes[result]].from_catala(inputs[result])
            )
        return cls(
            file_name=file_name,
            scope=scope.name,
            assertions=assertions,
            unasserted_cases=unasserted_cases,
        )


# %% test files


class ScopeTestFile:
    """
    A test file of an example whose tests give scopes their inputs, mixed into the
    example's enumeration of test files, each member's value the file's name.
    """

    @property
    def path(self) -> Path:
        """Where the file is kept."""
        return self.directory / self.value

    @property
    def directory(self) -> Path:
        """The directory holding the example's test files."""
        raise NotImplementedError

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """The kinds of case modelling the scopes the file's tests are about."""
        raise NotImplementedError

    def read_tests(self) -> list[ScopeTest]:
        """:return: The file's tests, in order."""
        program = CatalaTestReader(
            language=CatalaLanguage.from_path(self.path)
        ).read_program(self.path.read_text())
        return [
            ScopeTest.from_scope(self.value, scope, program, self.scope_cases)
            for scope in program.test_scopes
        ]
