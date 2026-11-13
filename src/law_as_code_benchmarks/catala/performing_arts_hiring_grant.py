"""
The hiring grant of the national fund for permanent employment in the performing arts
(*FONPEPS*), articles 1 to 3 of décret n° 2019-1011 du 1er octobre 2019 (`article 1
<https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000039165383>`__ on), as
Catala's ``asp/fonpeps`` example states them.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from pathlib import Path

from krrood.entity_query_language.factories import (
    add,
    alternative,
    an,
    and_,
    deduced_variable,
    entity,
    in_,
    inference,
    not_,
    or_,
    variable,
)
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from typing_extensions import Self

from law_as_code_benchmarks.catala.amounts import HourlyMinimumWage, MinimumWages
from law_as_code_benchmarks.catala.domain import DatedValue, Territory
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import (
    CatalaDirectory,
    CatalaValue,
    ConstructorWithContent,
    Reference,
)
from law_as_code_benchmarks.catala.scope_test import (
    CaseAmount,
    CaseCondition,
    CaseConclusion,
    ScopeCase,
    ScopeProvision,
    ScopeTestFile,
)

# %% the hiring


class ContractKind(StrEnum):
    """The contracts of employment article 1 grants the aid for, each named as Catala's ``Contrat`` constructor."""

    PERMANENT = "CDI"
    """A contract of indefinite duration."""

    FIXED_TERM = "CDD"
    """A contract of fixed duration."""


class BusinessRegime(StrEnum):
    """The employers of article 1, 1° to 4°, each named as Catala's ``RégimeEntreprise`` constructor."""

    PERFORMING_ARTS_BY_ACTIVITY = "IntermittentSpectacleParNatureActivité"
    """1° Covered mainly by a collective agreement of article 71 of annex VIII."""

    LISTED_PERFORMING_ARTS = "IntermittentSpectacleDansStructureListée"
    """2° On the list of employers of article 71 of annex VIII."""

    LIVE_PERFORMANCE_PRODUCER = "EntrepreneurSpectacleVivant"
    """3° A live performance producer affiliated to the paid-holidays fund of the performing arts."""

    LISTED_LYRIC_ARTISTS_EMPLOYER = "ArtisteLyriqueDansStructureListée"
    """4° On the minister's list of employers of permanent choir singers and resident voice artists."""


class HiringGrantOutput(StrEnum):
    """The outputs of Catala's ``AidePourEmbauche`` scope."""

    ELIGIBILITY = "éligibilité"
    """Whether the hiring is eligible for the aid."""

    AMOUNT = "montant"
    """The aid paid."""


@dataclass(eq=False)
class HiringCase(ScopeCase):
    """A hiring an employer asks the aid for, Catala's ``AidePourEmbauche`` scope."""

    contract_kind: ContractKind
    """Whether the contract is permanent or of fixed duration."""

    fixed_term_months: int | None
    """The months a fixed-term contract lasts; None for a permanent one."""

    business_regime: BusinessRegime
    """Which of article 1's employers the employer is."""

    permanent_choir_singer: bool
    """Whether the hiring is of a permanent choir singer (*artiste lyrique de chœur permanent*)."""

    replaces_singer_who_changed_duties: bool
    """
    Whether the hiring replaces a permanent choir singer whose contract was changed to
    other duties with the same employer.
    """

    school_resident_voice_artist: bool
    """Whether the hiring is of a voice artist in residence in a school for a project of collective singing."""

    performing_arts_duties: bool
    """Whether the job's duties fall under annexes VIII and X of the unemployment insurance rules."""

    annual_gross_salary: Money
    """The annual gross salary the contract provides."""

    assessment_date: datetime.date
    """The day the aid is assessed on, which sets the minimum wage in force."""

    contract_start_date: datetime.date
    """The day the contract's performance began."""

    part_time_share: Fraction | None = None
    """The share of full time worked; None for full time."""

    @classproperty
    def catala_scope(cls) -> str:
        """``AidePourEmbauche``."""
        return "AidePourEmbauche"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of Catala's ``AidePourEmbauche`` scope but the contract and working time."""
        return {
            "régime_entreprise": "business_regime",
            "artiste_lyrique_chœur_permanent": "permanent_choir_singer",
            "bénéficié_modification_contrat_travail_changement_fonctions_sans_changer_employeur": "replaces_singer_who_changed_duties",
            "artiste_voix_résidence_milieu_scolaire": "school_resident_voice_artist",
            "activité_intermittent_spectacle": "performing_arts_duties",
            "salaire_annuel_brut": "annual_gross_salary",
            "date_courante": "assessment_date",
            "date_début_exécution_contrat": "contract_start_date",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`HiringGrantOutput`."""
        return HiringGrantOutput

    @classmethod
    def from_catala(cls, values: dict[str, CatalaValue]) -> Self:
        """
        Extends :meth:`CatalaRecord.from_catala` with Catala's ``contrat``, a
        constructor whose content is a fixed term's duration, and ``temps_travail``,
        one whose content is the share of full time.
        """
        values = dict(values)
        contract: ConstructorWithContent | Reference = values.pop("contrat")
        working_time: ConstructorWithContent | Reference = values.pop("temps_travail")
        values["fixed_term_months"] = None
        if isinstance(contract, ConstructorWithContent):
            values["fixed_term_months"] = contract.content.whole_months
            contract = contract.constructor
        values["contract_kind"] = contract
        if isinstance(working_time, ConstructorWithContent):
            values["part_time_share"] = working_time.content
        return super().from_catala(values)

    def output(self, variable: str) -> CatalaValue:
        match HiringGrantOutput(variable):
            case HiringGrantOutput.ELIGIBILITY:
                return self.sole_conclusion(EligibilityProvision).holds
            case HiringGrantOutput.AMOUNT:
                amount = self.sole_conclusion(GrantAmountProvision)
                if amount is None:
                    return None
                return Grant(
                    amount=amount.amount,
                    frequency=amount.frequency,
                    instalment_count=amount.instalment_count,
                )


# %% conclusions


class PaymentFrequency(StrEnum):
    """How the aid is paid, each named as Catala's ``FréquenceVersement`` constructor."""

    ANNUAL = "Annuelle"
    """Once a year."""

    MONTHLY = "Mensuelle"
    """Once a month."""

    SINGLE = "Unique"
    """Once."""


@dataclass(frozen=True)
class Grant:
    """An aid paid in instalments, Catala's ``MontantAide``."""

    amount: Money
    """The amount of one instalment, or of the single payment."""

    frequency: PaymentFrequency
    """How often it is paid."""

    instalment_count: int
    """How many times it is paid: the years or months of Catala's frequency, or 1 for a single payment."""


@dataclass(eq=False)
class HiringMinimumWage(CaseAmount):
    """The gross hourly minimum wage in metropolitan France on the assessment date."""


@dataclass(eq=False)
class Eligibility(CaseCondition):
    """Articles 1 to 3: the hiring is eligible for the aid."""


@dataclass(eq=False)
class GrantConclusion(CaseConclusion):
    """An aid a provision gives a hiring, as :class:`Grant` states it."""

    amount: Money = field(default_factory=lambda: Money.zero)
    """The amount of one instalment, or of the single payment."""

    frequency: PaymentFrequency = PaymentFrequency.SINGLE
    """How often it is paid."""

    instalment_count: int = 1
    """How many times it is paid."""


@dataclass(eq=False)
class FlatRateGrant(GrantConclusion):
    """Article 3: the aid for a full-time hiring."""


@dataclass(eq=False)
class GrantAmount(GrantConclusion):
    """Article 3: the aid, prorated to the working time."""


# %% provisions


@dataclass
class HiringMinimumWageProvision(ScopeProvision[HiringMinimumWage]):
    """
    Article 2 I 2°: the minimum wage in force on the assessment date in metropolitan
    France, which Catala's example assumes for every employer.
    """

    def query(self) -> Query:
        case = variable(HiringCase, domain=[self.case])
        wage = variable(
            HourlyMinimumWage, domain=[member.value for member in MinimumWages]
        )
        return an(
            entity(inference(HiringMinimumWage)(case=case, amount=wage.amount)).where(
                DatedValue.is_in_force(wage, case.assessment_date),
                in_(Territory.METROPOLITAN_FRANCE, wage.territories),
            )
        )


@dataclass
class EligibilityProvision(ScopeProvision[Eligibility]):
    """
    Articles 1 to 3: a hiring is eligible where every requirement is met, and is not
    otherwise.
    """

    @classproperty
    def first_contract_start(cls) -> datetime.date:
        """Article 2 I 3°: the first day a contract's performance may begin on."""
        return datetime.date(2019, 10, 1)

    @classproperty
    def last_contract_start(cls) -> datetime.date:
        """Article 2 I 3°: the last day a contract's performance may begin on."""
        return datetime.date(2022, 12, 31)

    def query(self) -> Query:
        case = variable(HiringCase, domain=[self.case])
        wage = variable(
            HiringMinimumWage,
            domain=HiringMinimumWageProvision(case=self.case).conclusions,
        )
        permanent = case.contract_kind == ContractKind.PERMANENT
        fixed_term = case.contract_kind == ContractKind.FIXED_TERM
        eligibility = deduced_variable(Eligibility)
        query = an(
            entity(eligibility).where(
                # article 1: a permanent contract, or a fixed term of more than a month
                or_(permanent, case.fixed_term_months > 1),
                # article 1, 1° to 4°
                or_(
                    in_(
                        case.business_regime,
                        {
                            BusinessRegime.PERFORMING_ARTS_BY_ACTIVITY,
                            BusinessRegime.LISTED_PERFORMING_ARTS,
                            BusinessRegime.LIVE_PERFORMANCE_PRODUCER,
                        },
                    ),
                    and_(permanent, case.permanent_choir_singer == True),
                    and_(fixed_term, case.school_resident_voice_artist == True),
                ),
                # article 2 I 1° to 3°
                case.performing_arts_duties == True,
                # four times the annual minimum wage: 35 hours, 13/3 weeks a month, 12 months
                case.annual_gross_salary <= wage.amount * 4 * 35 * Fraction(13, 3) * 12,
                case.contract_start_date >= self.first_contract_start,
                case.contract_start_date <= self.last_contract_start,
                # article 2 II: a resident voice artist's contract lasts six months at least
                not_(
                    and_(
                        case.school_resident_voice_artist == True,
                        fixed_term,
                        case.fixed_term_months <= 6,
                    )
                ),
                # article 3: no aid for a part-time contract of one month to two
                not_(
                    and_(
                        fixed_term,
                        case.fixed_term_months >= 1,
                        case.fixed_term_months < 2,
                        case.part_time_share != None,
                    )
                ),
            )
        )
        with query:
            add(eligibility, inference(Eligibility)(case=case, holds=True))
            with alternative():
                add(eligibility, inference(Eligibility)(case=case, holds=False))
        return query


@dataclass
class FlatRateGrantProvision(ScopeProvision[FlatRateGrant]):
    """
    Article 3: 10,000 € a year for three years for a full-time permanent contract,
    16,000 € where it replaces a permanent choir singer who changed duties; 200, 300,
    400 or 500 € a month for a fixed term of one to four, four to eight, eight to twelve
    or twelve months and more, a single 9,000 € for a full-time resident voice artist.
    """

    def query(self) -> Query:
        case = variable(HiringCase, domain=[self.case])
        permanent = case.contract_kind == ContractKind.PERMANENT
        fixed_term = case.contract_kind == ContractKind.FIXED_TERM
        full_time = case.part_time_share == None
        grant = deduced_variable(FlatRateGrant)
        query = an(
            entity(grant).where(
                permanent,
                case.permanent_choir_singer == True,
                case.replaces_singer_who_changed_duties == True,
            )
        )
        with query:
            add(grant, self.annual_grant(case, Money.from_euros(16_000)))
            with alternative(permanent, full_time):
                add(grant, self.annual_grant(case, Money.from_euros(10_000)))
            with alternative(
                fixed_term, full_time, case.school_resident_voice_artist == True
            ):
                add(
                    grant,
                    inference(FlatRateGrant)(
                        case=case,
                        amount=Money.from_euros(9_000),
                        frequency=PaymentFrequency.SINGLE,
                        instalment_count=1,
                    ),
                )
            for first_month, last_month, monthly in [
                (1, 4, 200),
                (4, 8, 300),
                (8, 12, 400),
            ]:
                with alternative(
                    fixed_term,
                    case.fixed_term_months >= first_month,
                    case.fixed_term_months < last_month,
                ):
                    add(grant, self.monthly_grant(case, Money.from_euros(monthly)))
            with alternative(fixed_term, case.fixed_term_months >= 12):
                add(grant, self.monthly_grant(case, Money.from_euros(500)))
        return query

    @staticmethod
    def annual_grant(case: HiringCase, amount: Money) -> FlatRateGrant:
        """:return: The inference of *amount* a year for three years, over a variable of the case."""
        return inference(FlatRateGrant)(
            case=case,
            amount=amount,
            frequency=PaymentFrequency.ANNUAL,
            instalment_count=3,
        )

    @staticmethod
    def monthly_grant(case: HiringCase, amount: Money) -> FlatRateGrant:
        """:return: The inference of *amount* a month for as long as the fixed term, over a variable of the case."""
        return inference(FlatRateGrant)(
            case=case,
            amount=amount,
            frequency=PaymentFrequency.MONTHLY,
            instalment_count=case.fixed_term_months,
        )


@dataclass
class GrantAmountProvision(ScopeProvision[GrantAmount]):
    """Article 3: the flat-rate aid, prorated to the share of full time of a part-time hiring."""

    def query(self) -> Query:
        case = variable(HiringCase, domain=[self.case])
        flat_rate = variable(
            FlatRateGrant, domain=FlatRateGrantProvision(case=self.case).conclusions
        )
        amount = deduced_variable(GrantAmount)
        query = an(entity(amount).where(case.part_time_share != None))
        with query:
            add(
                amount,
                inference(GrantAmount)(
                    case=case,
                    amount=flat_rate.amount * case.part_time_share,
                    frequency=flat_rate.frequency,
                    instalment_count=flat_rate.instalment_count,
                ),
            )
            with alternative():
                add(
                    amount,
                    inference(GrantAmount)(
                        case=case,
                        amount=flat_rate.amount,
                        frequency=flat_rate.frequency,
                        instalment_count=flat_rate.instalment_count,
                    ),
                )
        return query


# %% test files


class HiringGrantTestFile(ScopeTestFile, StrEnum):
    """The test file of Catala's ``asp/fonpeps`` example."""

    HIRING_GRANT = "test_fonseps.catala_fr"
    """Its one test, of a part-time fixed-term contract."""

    @property
    def directory(self) -> Path:
        """:file:`asp/fonpeps/tests`."""
        return CatalaDirectory.ROOT / "asp" / "fonpeps" / "tests"

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """:class:`HiringCase`."""
        return [HiringCase]
