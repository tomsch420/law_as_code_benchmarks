"""
The grant for the private works connecting a building to an optical fibre network, of
décret n° 2025-674 du 18 juillet 2025 (`article 1
<https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000051921603>`__ on) and the
arrêté of 2 September 2025, as Catala's ``asp/aide_fibre`` example states them.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path

from krrood.entity_query_language.factories import (
    add,
    alternative,
    an,
    and_,
    deduced_variable,
    entity,
    inference,
    or_,
    variable,
)
from krrood.entity_query_language.predicate import symbolic_function
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from krrood.patterns.path_enumeration import PathEnumeration
from typing_extensions import Self

from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import (
    CatalaDirectory,
    CatalaValue,
    ConstructorWithContent,
    Duration,
)
from law_as_code_benchmarks.catala.scope_test import (
    CaseAmount,
    CaseCondition,
    CatalaRecord,
    ScopeCase,
    ScopeProvision,
    ScopeTestFile,
)

# %% the communes of the annex


class FibreGrantDirectory(PathEnumeration):
    """The files of Catala's ``asp/aide_fibre`` example kept in the repository."""

    ROOT = CatalaDirectory.ROOT / "asp" / "aide_fibre"
    """The example's directory."""

    TESTS = ROOT / "tests"
    """Its test files."""

    COMMUNES = ROOT / "ocaml" / "Eligibilite_commune.ml"
    """
    The postal codes of the communes of the decree's annex, which Catala declares as an
    external function and the example implements in OCaml.
    """


@dataclass(frozen=True)
class AnnexCommunes:
    """The communes the decree's annex lists, by postal code."""

    postal_codes: frozenset[int]
    """Their postal codes."""

    @classmethod
    @cache
    def from_example(cls) -> AnnexCommunes:
        """:return: The communes of the list ``eligible_communes`` of the example's OCaml module."""
        source = FibreGrantDirectory.COMMUNES.read_text()
        (listed,) = re.findall(
            r"let eligible_communes =\s*\[(.*?)\]", source, re.DOTALL
        )
        return cls(
            postal_codes=frozenset(int(code) for code in re.findall(r"\d+", listed))
        )

    @staticmethod
    @symbolic_function
    def lists(postal_code: int) -> bool:
        """:return: Whether the annex lists the commune of *postal_code*."""
        return postal_code in AnnexCommunes.from_example().postal_codes


# %% the applicant and the works


@dataclass
class Individual(CatalaRecord):
    """An applicant who is a natural person without an economic activity, Catala's ``PersonnePhysique``."""

    detached_house_occupant: bool
    """Whether the works are in a detached house the applicant owns a real right in or rents."""

    main_residence: bool
    """Whether the house is the applicant's main residence."""

    postal_code: int
    """The postal code of the house's commune."""

    not_previously_aided: bool
    """Whether the house never received an aid for works connecting it to optical fibre."""

    family_quotient: Money
    """The applicant's reference taxable income divided by the shares of their tax household."""

    connection_failure_recorded: bool
    """Whether an operator recorded that connecting failed for want of works on the private part."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of Catala's ``PersonnePhysique``."""
        return {
            "travaux_dans_maison_individuelle_par_occupant": "detached_house_occupant",
            "résidence_principale": "main_residence",
            "code_postal_commune": "postal_code",
            "n_a_pas_déjà_bénéficié_de_l_aide": "not_previously_aided",
            "quotient_familial": "family_quotient",
            "échec_de_raccordement_constaté": "connection_failure_recorded",
        }


@dataclass
class Business(CatalaRecord):
    """An applicant with an economic activity, Catala's ``Entreprise``."""

    turnover: Money
    """The annual turnover of the last closed financial year."""

    employee_count: int
    """The number of employees."""

    activity_start: datetime.date
    """The day the business began its activity."""

    in_judicial_liquidation: bool
    """Whether the business is in judicial liquidation on the day it applies."""

    postal_code: int
    """The postal code of the premises' commune."""

    not_previously_aided: bool
    """Whether the premises never received an aid for works connecting them to optical fibre."""

    connection_failure_recorded: bool
    """Whether an operator recorded that connecting failed for want of works on the private part."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of Catala's ``Entreprise``."""
        return {
            "chiffre_affaire_dernier_exercice_clos": "turnover",
            "nombre_salariés": "employee_count",
            "début_activité": "activity_start",
            "en_liquidation_judiciaire_à_la_date_demande": "in_judicial_liquidation",
            "code_postal_commune": "postal_code",
            "n_a_pas_déjà_bénéficié_de_l_aide": "not_previously_aided",
            "échec_de_raccordement_constaté": "connection_failure_recorded",
        }

    @staticmethod
    @symbolic_function
    def has_operated_a_year(business: Business, day: datetime.date) -> bool:
        """:return: Whether *business* began its activity a year before *day* at least."""
        return Duration(years=1).date_after(business.activity_start) <= day


class ApplicantConstructor(StrEnum):
    """The constructors of Catala's ``Demandeur``."""

    INDIVIDUAL = "PersonnePhysique"
    """A natural person without an economic activity."""

    BUSINESS = "Entreprise"
    """A business."""


class WorksScale(StrEnum):
    """Article 5 of the arrêté: the categories of works, each named as Catala's ``AmpleurTravaux`` constructor."""

    SMALL = "FaibleAmpleur"
    """1° Works of small scale."""

    MEDIUM = "AmpleurMoyenne"
    """2° Works of medium scale."""

    LARGE = "GrosTravaux"
    """3° Large works."""


class FibreGrantOutput(StrEnum):
    """The outputs of Catala's ``CalculAide`` scope."""

    ELIGIBILITY = "éligibilité"
    """Whether the applicant is eligible for the grant."""

    AMOUNT = "montant"
    """The grant."""


@dataclass(eq=False)
class FibreConnectionCase(ScopeCase):
    """An application for the grant, Catala's ``CalculAide`` scope."""

    completion_date: datetime.date
    """The day the works were completed."""

    application_date: datetime.date
    """The day the application was filed."""

    works_scale: WorksScale
    """The category of the works."""

    invoice_amount: Money
    """The amount of the invoice for the works, all taxes included."""

    individual: Individual | None = None
    """The applicant, where a natural person; None for a business."""

    business: Business | None = None
    """The applicant, where a business; None for a natural person."""

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculAide``."""
        return "CalculAide"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of Catala's ``CalculAide`` scope but the applicant."""
        return {
            "date_achèvement": "completion_date",
            "date_demande": "application_date",
            "ampleur_travaux": "works_scale",
            "montant_facture_raccordement": "invoice_amount",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`FibreGrantOutput`."""
        return FibreGrantOutput

    @classmethod
    def from_catala(cls, values: dict[str, CatalaValue]) -> Self:
        """
        Extends :meth:`CatalaRecord.from_catala` with Catala's ``demandeur``, a
        constructor whose content is the natural person or the business.
        """
        values = dict(values)
        applicant: ConstructorWithContent = values.pop("demandeur")
        match ApplicantConstructor(applicant.constructor.last_part):
            case ApplicantConstructor.INDIVIDUAL:
                values["individual"] = applicant.content
            case ApplicantConstructor.BUSINESS:
                values["business"] = applicant.content
        return super().from_catala(values)

    def output(self, variable: str) -> CatalaValue:
        match FibreGrantOutput(variable):
            case FibreGrantOutput.ELIGIBILITY:
                return self.sole_conclusion(FibreGrantEligibilityProvision).holds
            case FibreGrantOutput.AMOUNT:
                amount = self.sole_conclusion(FibreGrantAmountProvision)
                return None if amount is None else amount.amount


# %% conclusions


@dataclass(eq=False)
class FibreGrantEligibility(CaseCondition):
    """Articles 1 and 3 of the decree: the applicant is eligible for the grant."""


@dataclass(eq=False)
class FlatRateFibreGrant(CaseAmount):
    """Article 5 of the arrêté: the flat sum of the works' category."""


@dataclass(eq=False)
class FibreGrantAmount(CaseAmount):
    """Article 4 of the decree: the grant, which the invoice caps."""


# %% provisions


@dataclass
class FibreGrantEligibilityProvision(ScopeProvision[FibreGrantEligibility]):
    """
    Article 1: works completed from 1 September 2025 to 31 May 2027. Article 3 I: a
    natural person meeting 1° to 6°, the family quotient at most 29,316 € (article 2 of
    the arrêté); article 3 II: a business meeting 1° to 7°.
    """

    @classproperty
    def first_completion_date(cls) -> datetime.date:
        """Article 1: the first day works may be completed on."""
        return datetime.date(2025, 9, 1)

    @classproperty
    def last_completion_date(cls) -> datetime.date:
        """Article 1: the last day works may be completed on."""
        return datetime.date(2027, 5, 31)

    @classproperty
    def family_quotient_ceiling(cls) -> Money:
        """Article 2 of the arrêté: the highest family quotient of an eligible natural person."""
        return Money.from_euros(29_316)

    @classproperty
    def turnover_ceiling(cls) -> Money:
        """Article 3 II 1°: the highest turnover of an eligible business."""
        return Money.from_euros(2_000_000)

    @classproperty
    def employee_ceiling(cls) -> int:
        """Article 3 II 2°: the most employees of an eligible business, which Catala reads as at most 10."""
        return 10

    def query(self) -> Query:
        case = variable(FibreConnectionCase, domain=[self.case])
        individual = case.individual
        business = case.business
        eligibility = deduced_variable(FibreGrantEligibility)
        query = an(
            entity(eligibility).where(
                case.completion_date >= self.first_completion_date,
                case.completion_date <= self.last_completion_date,
                or_(
                    and_(
                        individual != None,
                        individual.detached_house_occupant == True,
                        individual.main_residence == True,
                        AnnexCommunes.lists(individual.postal_code),
                        individual.not_previously_aided == True,
                        individual.family_quotient <= self.family_quotient_ceiling,
                        individual.connection_failure_recorded == True,
                    ),
                    and_(
                        business != None,
                        business.turnover <= self.turnover_ceiling,
                        business.employee_count <= self.employee_ceiling,
                        Business.has_operated_a_year(business, case.application_date),
                        business.in_judicial_liquidation == False,
                        AnnexCommunes.lists(business.postal_code),
                        business.not_previously_aided == True,
                        business.connection_failure_recorded == True,
                    ),
                ),
            )
        )
        with query:
            add(eligibility, inference(FibreGrantEligibility)(case=case, holds=True))
            with alternative():
                add(
                    eligibility,
                    inference(FibreGrantEligibility)(case=case, holds=False),
                )
        return query


@dataclass
class FlatRateFibreGrantProvision(ScopeProvision[FlatRateFibreGrant]):
    """Article 5 of the arrêté: 400 € for works of small scale, 800 € of medium scale, 1,200 € for large works."""

    @classproperty
    def flat_sums(cls) -> dict[WorksScale, Money]:
        """The flat sum of each category of works."""
        return {
            WorksScale.SMALL: Money.from_euros(400),
            WorksScale.MEDIUM: Money.from_euros(800),
            WorksScale.LARGE: Money.from_euros(1_200),
        }

    def query(self) -> Query:
        case = variable(FibreConnectionCase, domain=[self.case])
        grant = deduced_variable(FlatRateFibreGrant)
        scales = list(self.flat_sums.items())
        (first_scale, first_sum), *other_scales = scales
        query = an(entity(grant).where(case.works_scale == first_scale))
        with query:
            add(grant, inference(FlatRateFibreGrant)(case=case, amount=first_sum))
            for scale, flat_sum in other_scales:
                with alternative(case.works_scale == scale):
                    add(
                        grant, inference(FlatRateFibreGrant)(case=case, amount=flat_sum)
                    )
        return query


@dataclass
class FibreGrantAmountProvision(ScopeProvision[FibreGrantAmount]):
    """Article 4 of the decree: the flat sum, at most the invoice's amount."""

    def query(self) -> Query:
        case = variable(FibreConnectionCase, domain=[self.case])
        flat_sum = variable(
            FlatRateFibreGrant,
            domain=FlatRateFibreGrantProvision(case=self.case).conclusions,
        )
        amount = deduced_variable(FibreGrantAmount)
        query = an(entity(amount).where(flat_sum.amount > case.invoice_amount))
        with query:
            add(
                amount,
                inference(FibreGrantAmount)(case=case, amount=case.invoice_amount),
            )
            with alternative():
                add(
                    amount,
                    inference(FibreGrantAmount)(case=case, amount=flat_sum.amount),
                )
        return query


# %% test files


class FibreGrantTestFile(ScopeTestFile, StrEnum):
    """The test file of Catala's ``asp/aide_fibre`` example."""

    FIBRE_GRANT = "test_aide_fibre.catala_fr"
    """Its one test, of a natural person in Martinique doing large works."""

    @property
    def directory(self) -> Path:
        """:attr:`FibreGrantDirectory.TESTS`."""
        return FibreGrantDirectory.TESTS

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """:class:`FibreConnectionCase`."""
        return [FibreConnectionCase]
