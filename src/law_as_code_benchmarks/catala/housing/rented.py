"""
The personal housing aids of a rented home: the personalised housing aid (Catala's
``CalculAidePersonnaliséeLogementLocatif``, articles D823-16 and D823-17 and the arrêté
of September 27, 2019) and the housing allowance computed on its scale
(``CalculAllocationLogementLocatif``, D842-1 to D842-4).
"""

from __future__ import annotations

import datetime
from abc import ABC
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from functools import cached_property
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
    or_,
    variable,
)
from krrood.entity_query_language.predicate import symbolic_function
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from typing_extensions import Callable

from law_as_code_benchmarks.catala.domain import DatedValue, Territory
from law_as_code_benchmarks.catala.housing.domain import HomeChange, HousingZone, Moved
from law_as_code_benchmarks.catala.housing.rented_scales import (
    FamilyRates,
    FamilyRateScales,
    IncomeAbatements,
    IncomeAbatementScales,
    MayotteAbatementScales,
    OverseasScale,
    OverseasScales,
    RentedHomeScale,
    RentedHomeScales,
    SaintPierreAbatementScales,
    ZoneAmounts,
)
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.provision import RuleBranch, RuleChain
from law_as_code_benchmarks.law.provision import AssessedCase, Conclusion, Provision
from law_as_code_benchmarks.catala.reader import CatalaDirectory, CatalaValue
from law_as_code_benchmarks.catala.scope_test import (
    CaseAmount,
    CaseConclusion,
    CaseFraction,
    ScopeCase,
    ScopeProvision,
    ScopeTestFile,
)
from law_as_code_benchmarks.law.rounding import Rounding

# %% inputs


class AidFamilySituation(StrEnum):
    """The family situation the scales of the aids know, each named as Catala's ``SituationFamilialeCalculAPL``."""

    SINGLE = "PersonneSeule"
    """A person alone."""

    COUPLE = "Couple"
    """A couple."""


class AidType(StrEnum):
    """The personal housing aids, each named as Catala's ``TypeAidesPersonnelleLogement``."""

    PERSONALISED_AID = "AidePersonnaliséeLogement"
    """The personalised housing aid."""

    FAMILY_ALLOWANCE = "AllocationLogementFamiliale"
    """The family housing allowance."""

    SOCIAL_ALLOWANCE = "AllocationLogementSociale"
    """The social housing allowance."""


# %% conclusions


@dataclass(eq=False)
class ScaledDependants(CaseConclusion):
    """How many dependants the scales count: all of them, or six at most overseas until 2022 (article 46)."""

    count: int = 0
    """The dependants counted."""


@dataclass(eq=False)
class RentCeiling(CaseAmount):
    """D823-16 2°: the rent ceiling."""


@dataclass(eq=False)
class FlatCharges(CaseAmount):
    """D823-16: the flat amount of charges."""


@dataclass(eq=False)
class FurnishedRent(CaseAmount):
    """D842-2: the rent, two thirds of it where the dwelling is let furnished."""


@dataclass(eq=False)
class EligibleRent(CaseAmount):
    """D823-16: the rent within the ceiling."""


@dataclass(eq=False)
class MinimumParticipation(CaseAmount):
    """D823-17 and article 13: the minimum participation of the household."""


@dataclass(eq=False)
class FamilyRate(CaseFraction):
    """D823-17 and article 14: the family composition rate."""


@dataclass(eq=False)
class ReferenceRent(CaseAmount):
    """Article 14: the reference rent."""


@dataclass(eq=False)
class RentRatio(CaseFraction):
    """Article 14: the eligible rent over the reference rent, to four decimals."""


@dataclass(eq=False)
class EligibleRentRate(CaseFraction):
    """Article 14: the rate of the eligible rent, to five decimals."""


@dataclass(eq=False)
class IncomeAbatement(CaseAmount):
    """D823-17 and article 15: the flat abatement of the household's resources."""


@dataclass(eq=False)
class PersonalParticipation(CaseAmount):
    """D823-17: the personal participation of the household."""


@dataclass(eq=False)
class InitialAid(CaseAmount):
    """D823-16: the aid the formula gives, before it is treated."""


@dataclass(eq=False)
class DegressivityCeiling(CaseAmount):
    """D823-16 and article 10: the rent above which the aid decreases."""


@dataclass(eq=False)
class SuppressionCeiling(CaseAmount):
    """D823-16 and article 10: the rent above which no aid is due."""


@dataclass(eq=False)
class SocialContribution(CaseConclusion):
    """The contribution to the repayment of the social debt (*CRDS*) on the aid: its rate, or an exemption."""

    rate: Fraction = Fraction(0)
    """The rate."""

    exempt: bool = False
    """Whether the aid is exempt, the contribution being nothing whatever the rate."""


# %% cases


class RentedAidOutput(StrEnum):
    """The outputs of ``CalculAidePersonnaliséeLogementLocatif`` the tests read."""

    FLAT_CHARGES = "montant_forfaitaire_charges_d823_16"
    """The flat amount of charges."""

    RENT_CEILING = "plafond_loyer_d823_16_2"
    """The rent ceiling."""

    MINIMUM_PARTICIPATION = "participation_minimale"
    """The minimum participation."""

    FAMILY_RATE = "taux_composition_familiale"
    """The family composition rate."""

    PERSONAL_PARTICIPATION = "participation_personnelle"
    """The personal participation."""

    INITIAL_AID = "aide_finale_formule_initiale"
    """The aid the formula gives."""

    TREATED_AID = "aide_finale_après_traitement"
    """The aid treated, net of the contribution and rounded."""

    AID_TREATMENT = "traitement_aide_finale"
    """The treatment of an aid, a function."""


@dataclass(eq=False)
class RentedAidCase(ScopeCase):
    """The inputs of the personalised housing aid of a rented home, Catala's ``CalculAidePersonnaliséeLogementLocatif``."""

    rent: Money
    """The monthly rent, charges aside."""

    resources: Money
    """The household's yearly resources, rounded."""

    disability_aid_recipient: bool
    """Whether the household receives the allowance for a disabled adult or child."""

    assessment_date: datetime.date
    """The day the aid is computed for."""

    dependant_count: int
    """How many persons are in the household's charge."""

    family_situation: AidFamilySituation
    """Whether the household is a person alone or a couple."""

    zone: HousingZone
    """The zone the dwelling is in."""

    is_room: bool
    """Whether the dwelling is a room."""

    paying_guests_elderly_or_disabled: bool
    """Whether elderly or disabled adults are lodged for payment by private persons."""

    aid_type: AidType
    """The aid computed."""

    is_house_share: bool
    """Whether the dwelling is shared with other tenants."""

    solidarity_rent_reduction: Money
    """The solidarity rent reduction the landlord grants."""

    furnished_d842_2: bool
    """Whether the dwelling is let furnished, as article D842-2 asks."""

    residence: Territory
    """Where the household lives."""

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculAidePersonnaliséeLogementLocatif``."""
        return "CalculAidePersonnaliséeLogementLocatif"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of the scope."""
        return {
            "loyer_principal": "rent",
            "ressources_ménage_arrondies": "resources",
            "bénéficiaire_aide_adulte_ou_enfant_handicapés": "disability_aid_recipient",
            "date_courante": "assessment_date",
            "nombre_personnes_à_charge": "dependant_count",
            "situation_familiale_calcul_apl": "family_situation",
            "logement_est_chambre": "is_room",
            "âgées_ou_handicap_adultes_hébergées_onéreux_particuliers": "paying_guests_elderly_or_disabled",
            "type_aide": "aid_type",
            "colocation": "is_house_share",
            "réduction_loyer_solidarité": "solidarity_rent_reduction",
            "logement_meublé_d842_2": "furnished_d842_2",
            "résidence": "residence",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`RentedAidOutput`."""
        return RentedAidOutput

    @classproperty
    def first_day_modelled(cls) -> datetime.date:
        """The first day Catala's example computes the aid for, October 1, 2020."""
        return datetime.date(2020, 10, 1)

    @cached_property
    def scale(self) -> RentedHomeScale | None:
        """The amounts of articles 7 to 16 in force."""
        return DatedValue.value_in_force(RentedHomeScales, self.assessment_date)

    @cached_property
    def abatements(self) -> IncomeAbatements | None:
        """The abatements of article 15 in force."""
        return DatedValue.value_in_force(IncomeAbatementScales, self.assessment_date)

    @cached_property
    def overseas_scale(self) -> OverseasScale | None:
        """The amounts of article 46 in force."""
        return DatedValue.value_in_force(OverseasScales, self.assessment_date)

    @cached_property
    def saint_pierre_abatements(self) -> IncomeAbatements | None:
        """The abatements of article 47 for Saint-Pierre-et-Miquelon in force."""
        return DatedValue.value_in_force(
            SaintPierreAbatementScales, self.assessment_date
        )

    @cached_property
    def mayotte_abatements(self) -> IncomeAbatements | None:
        """The abatements of article 47 for Mayotte in force."""
        return DatedValue.value_in_force(MayotteAbatementScales, self.assessment_date)

    def treated_aid(self, aid: Money) -> Money | None:
        """:return: *aid* treated as ``traitement_aide_finale`` treats it; None where no rule does."""
        return AidTreatment(case=self, aid=aid).sole_amount(MinimumAidProvision)

    def output(self, variable: str) -> CatalaValue | Callable[[Money], Money | None]:
        match RentedAidOutput(variable):
            case RentedAidOutput.FLAT_CHARGES:
                provision = FlatChargesProvision
            case RentedAidOutput.RENT_CEILING:
                provision = RentCeilingProvision
            case RentedAidOutput.MINIMUM_PARTICIPATION:
                provision = MinimumParticipationProvision
            case RentedAidOutput.FAMILY_RATE:
                fraction = self.sole_conclusion(FamilyRateProvision)
                return None if fraction is None else fraction.fraction
            case RentedAidOutput.PERSONAL_PARTICIPATION:
                provision = PersonalParticipationProvision
            case RentedAidOutput.INITIAL_AID:
                provision = InitialAidProvision
            case RentedAidOutput.TREATED_AID:
                return self.aid_after_treatment()
            case RentedAidOutput.AID_TREATMENT:
                return self.treated_aid
        amount = self.sole_conclusion(provision)
        return None if amount is None else amount.amount

    def aid_after_treatment(self) -> Money | None:
        """
        D823-16: the initial aid treated, less its contribution, rounded down to the euro,
        as Catala's ``aide_finale_après_traitement`` shows it; None where no rule gives one.
        """
        initial = self.sole_conclusion(InitialAidProvision)
        if initial is None:
            return None
        treated = self.treated_aid(initial.amount)
        contribution = self.sole_conclusion(SocialContributionProvision)
        if treated is None or contribution is None:
            return None
        net = (
            treated - Contribution.amount(treated, contribution) - Money(cents=50)
        ).rounded_to_units()
        return net if net >= Money.zero else Money.zero


@dataclass(eq=False)
class RentedAllowanceCase(RentedAidCase):
    """
    The inputs of the housing allowance of a rented home, Catala's
    ``CalculAllocationLogementLocatif``, computed on the scale of the personalised aid.
    """

    home_change: HomeChange
    """Whether the household moved, as article D842-4 asks."""

    @classproperty
    def catala_scope(cls) -> str:
        """``CalculAllocationLogementLocatif``."""
        return "CalculAllocationLogementLocatif"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """Extends the inputs of the personalised aid with the move of D842-4."""
        return super().catala_names | {"changement_logement_d842_4": "home_change"}

    @cached_property
    def personalised_aid(self) -> RentedAidCase:
        """D842-1: the computation of the personalised aid with the same inputs, Catala's ``calcul_apl_locatif``."""
        return RentedAidCase(
            rent=self.rent,
            resources=self.resources,
            disability_aid_recipient=self.disability_aid_recipient,
            assessment_date=self.assessment_date,
            dependant_count=self.dependant_count,
            family_situation=self.family_situation,
            zone=self.zone,
            is_room=self.is_room,
            paying_guests_elderly_or_disabled=self.paying_guests_elderly_or_disabled,
            aid_type=self.aid_type,
            is_house_share=self.is_house_share,
            solidarity_rent_reduction=self.solidarity_rent_reduction,
            furnished_d842_2=self.furnished_d842_2,
            residence=self.residence,
        )

    @property
    def keeps_previous_aid(self) -> bool:
        """D842-4: the household moved to a dwelling whose rent is not lower than the previous one."""
        return (
            isinstance(self.home_change, Moved)
            and self.rent >= self.home_change.details.previous_rent
        )

    def treated_aid(self, aid: Money) -> Money | None:
        """Extends :meth:`RentedAidCase.treated_aid`: D842-4 leaves the aid of a household that keeps its previous one as it is."""
        if self.keeps_previous_aid:
            return aid
        return self.personalised_aid.treated_aid(aid)

    def output(self, variable: str) -> CatalaValue | Callable[[Money], Money | None]:
        """
        Extends :meth:`RentedAidCase.output`: D842-4 gives a household that keeps its
        previous aid the rent less its previous rent net of its previous allowance.
        """
        match RentedAidOutput(variable):
            case RentedAidOutput.INITIAL_AID if self.keeps_previous_aid:
                details = self.home_change.details
                return self.rent - (
                    details.previous_rent - details.previous_housing_allowance
                )
            case RentedAidOutput.AID_TREATMENT:
                return self.treated_aid
            case RentedAidOutput.TREATED_AID:
                return None
        return self.personalised_aid.output(variable)

    def concludes_every_output(self) -> bool:
        """Extends :meth:`ScopeCase.concludes_every_output`: the allowance has no treated aid of its own."""
        return all(
            self.output(variable) is not None
            for variable in RentedAidOutput
            if variable != RentedAidOutput.TREATED_AID
        )


# %% provisions


@dataclass
class RentedAidProvision(ScopeProvision, ABC):
    """A provision of the personalised housing aid of a rented home."""

    @classproperty
    def overseas_territories(cls) -> frozenset[Territory]:
        """Article 46: the overseas departments, Saint-Barthélemy and Saint-Martin."""
        return frozenset(
            {
                Territory.GUADELOUPE,
                Territory.FRENCH_GUIANA,
                Territory.MARTINIQUE,
                Territory.REUNION,
                Territory.MAYOTTE,
                Territory.SAINT_BARTHELEMY,
                Territory.SAINT_MARTIN,
            }
        )

    @property
    def conclusions(self) -> list[Conclusion]:
        """Extends :meth:`Provision.conclusions`: none before the scales Catala's example states."""
        case: RentedAidCase = self.case
        if case.scale is None or case.abatements is None:
            return []
        return super().conclusions

    def sole(self, provision: type[RentedAidProvision]) -> CaseConclusion:
        """:return: A variable over the one conclusion *provision* draws about the case."""
        return variable(CaseConclusion, domain=provision(case=self.case).conclusions)


@dataclass
class ScaledDependantsProvision(RentedAidProvision):
    """Article 46: overseas, until 2022, the scales count six dependants at most."""

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        overseas = self.case.overseas_scale
        counted = deduced_variable(ScaledDependants)
        branches = []
        if overseas is not None and overseas.dependants_counted_at_most is not None:
            cap = overseas.dependants_counted_at_most
            branches.append(
                RuleBranch(
                    conditions=(
                        in_(case.residence, self.overseas_territories),
                        case.dependant_count > cap,
                    ),
                    inferred=inference(ScaledDependants)(case=case, count=cap),
                )
            )
        branches.append(
            RuleBranch(
                conditions=(),
                inferred=inference(ScaledDependants)(
                    case=case, count=case.dependant_count
                ),
            )
        )
        return RuleChain(conclusion=counted, branches=branches).query()


@dataclass
class RentCeilingProvision(RentedAidProvision):
    """
    D823-16 2° and article 7: the rent ceiling of a person alone, a couple, or one
    dependant and more for each further one, by zone. Article 8 sets that of a room,
    lower for elderly or disabled adults lodged for payment; article 16 that of sharing.
    """

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        scale: RentedHomeScale = self.case.scale
        dependants = variable(
            ScaledDependants,
            domain=ScaledDependantsProvision(case=self.case).conclusions,
        )
        couple = case.family_situation == AidFamilySituation.COUPLE
        single = case.family_situation == AidFamilySituation.SINGLE
        without_dependants = case.dependant_count == 0
        branches = [
            RuleBranch(
                conditions=(
                    case.is_room == True,
                    case.paying_guests_elderly_or_disabled == True,
                ),
                inferred=self.inferred(case, scale.hosted_room_ceiling),
            ),
            RuleBranch(
                conditions=(case.is_room == True,),
                inferred=self.inferred(case, scale.room_ceiling),
            ),
        ]
        for sharing, ceilings in (
            ((case.is_house_share == True,), scale.shared_ceilings),
            ((), scale.ceilings),
        ):
            branches += [
                RuleBranch(
                    conditions=(*sharing, without_dependants, single),
                    inferred=self.inferred(case, ceilings.single),
                ),
                RuleBranch(
                    conditions=(*sharing, without_dependants, couple),
                    inferred=self.inferred(case, ceilings.couple),
                ),
                RuleBranch(
                    conditions=(*sharing, case.dependant_count >= 1),
                    inferred=inference(RentCeiling)(
                        case=case,
                        amount=ZoneAmounts.amount_in(ceilings.one_dependant, case.zone)
                        + ZoneAmounts.amount_in(
                            ceilings.each_further_dependant, case.zone
                        )
                        * (dependants.count - 1),
                    ),
                ),
            ]
        return RuleChain(
            conclusion=deduced_variable(RentCeiling), branches=branches
        ).query()

    @staticmethod
    def inferred(case: RentedAidCase, amounts: ZoneAmounts) -> RentCeiling:
        """:return: The inference of the ceiling of *amounts* in the case's zone, over a variable of the case."""
        return inference(RentCeiling)(
            case=case, amount=ZoneAmounts.amount_in(amounts, case.zone)
        )


@dataclass
class FlatChargesProvision(RentedAidProvision):
    """
    D823-16 and article 9: the flat charges, and more for each dependant; article 16
    halves those of a person alone sharing; article 46 sets its own overseas.
    """

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        dependants = variable(
            ScaledDependants,
            domain=ScaledDependantsProvision(case=self.case).conclusions,
        )
        couple = case.family_situation == AidFamilySituation.COUPLE
        shared = case.is_house_share == True
        places = []
        if self.case.overseas_scale is not None:
            overseas = in_(case.residence, self.overseas_territories)
            places.append(((overseas,), self.case.overseas_scale))
        places.append(((), self.case.scale))
        branches = []
        for place, scale in places:
            branches += [
                RuleBranch(
                    conditions=(*place, shared, couple),
                    inferred=self.inferred(case, scale.charges, scale, dependants),
                ),
                RuleBranch(
                    conditions=(*place, shared),
                    inferred=self.inferred(
                        case, scale.shared_charges_single, scale, dependants
                    ),
                ),
                RuleBranch(
                    conditions=place,
                    inferred=self.inferred(case, scale.charges, scale, dependants),
                ),
            ]
        return RuleChain(
            conclusion=deduced_variable(FlatCharges), branches=branches
        ).query()

    @staticmethod
    def inferred(
        case: RentedAidCase,
        base: Money,
        scale: RentedHomeScale | OverseasScale,
        dependants: ScaledDependants,
    ) -> FlatCharges:
        """:return: The inference of *base* and the charges of each dependant counted, over variables of the case."""
        return inference(FlatCharges)(
            case=case, amount=base + scale.charges_per_dependant * dependants.count
        )


@dataclass
class FurnishedRentProvision(RentedAidProvision):
    """D842-2: two thirds of the rent of a dwelling let furnished."""

    @classproperty
    def furnished_share(cls) -> Fraction:
        """D842-2: two thirds."""
        return Fraction(2, 3)

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        rent = deduced_variable(FurnishedRent)
        query = an(entity(rent).where(case.furnished_d842_2 == True))
        with query:
            add(
                rent,
                inference(FurnishedRent)(
                    case=case, amount=case.rent * self.furnished_share
                ),
            )
            with alternative():
                add(rent, inference(FurnishedRent)(case=case, amount=case.rent))
        return query


@dataclass
class EligibleRentProvision(RentedAidProvision):
    """D823-16: the rent, the rent ceiling where it is higher."""

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        rent = self.sole(FurnishedRentProvision)
        ceiling = self.sole(RentCeilingProvision)
        eligible = deduced_variable(EligibleRent)
        query = an(entity(eligible).where(rent.amount > ceiling.amount))
        with query:
            add(eligible, inference(EligibleRent)(case=case, amount=ceiling.amount))
            with alternative():
                add(eligible, inference(EligibleRent)(case=case, amount=rent.amount))
        return query


@dataclass
class MinimumParticipationProvision(RentedAidProvision):
    """Article 13: 8.5 % of the eligible rent and flat charges, the least amount of the scale at least."""

    @classproperty
    def share_of_rent_and_charges(cls) -> Fraction:
        """Article 13: 8.5 %."""
        return Fraction(85, 1000)

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        rent = self.sole(EligibleRentProvision)
        charges = self.sole(FlatChargesProvision)
        least = self.case.scale.minimum_participation
        share = (rent.amount + charges.amount) * self.share_of_rent_and_charges
        participation = deduced_variable(MinimumParticipation)
        query = an(entity(participation).where(share >= least))
        with query:
            add(participation, inference(MinimumParticipation)(case=case, amount=share))
            with alternative():
                add(
                    participation,
                    inference(MinimumParticipation)(case=case, amount=least),
                )
        return query


@dataclass
class FamilyRateProvision(RentedAidProvision):
    """Article 14: the family composition rate, by household; article 46 sets its own overseas."""

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        couple = case.family_situation == AidFamilySituation.COUPLE
        overseas = self.case.overseas_scale
        branches = []
        if overseas is not None:
            branches.append(
                RuleBranch(
                    conditions=(in_(case.residence, self.overseas_territories),),
                    inferred=self.inferred(case, overseas.family_rates, couple),
                )
            )
        branches.append(
            RuleBranch(
                conditions=(),
                inferred=self.inferred(
                    case, FamilyRateScales.METROPOLITAN.value, couple
                ),
            )
        )
        return RuleChain(
            conclusion=deduced_variable(FamilyRate), branches=branches
        ).query()

    @staticmethod
    def inferred(case: RentedAidCase, rates: FamilyRates, couple: object) -> FamilyRate:
        """:return: The inference of the rate of *rates* for the case's household, over a variable of the case."""
        return inference(FamilyRate)(
            case=case,
            fraction=FamilyRates.rate_for(rates, couple, case.dependant_count),
        )


@dataclass
class ReferenceRentProvision(RentedAidProvision):
    """Article 14: the reference rent of a person alone, a couple, or one dependant and more for each further one."""

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        rents = self.case.scale.reference_rents
        dependants = variable(
            ScaledDependants,
            domain=ScaledDependantsProvision(case=self.case).conclusions,
        )
        reference = deduced_variable(ReferenceRent)
        query = an(
            entity(reference).where(
                case.dependant_count == 0,
                case.family_situation == AidFamilySituation.SINGLE,
            )
        )
        with query:
            add(reference, inference(ReferenceRent)(case=case, amount=rents.single))
            with alternative(case.dependant_count == 0):
                add(reference, inference(ReferenceRent)(case=case, amount=rents.couple))
            with alternative():
                add(
                    reference,
                    inference(ReferenceRent)(
                        case=case,
                        amount=rents.one_dependant
                        + rents.each_further_dependant * (dependants.count - 1),
                    ),
                )
        return query


@dataclass
class RentRatioProvision(RentedAidProvision):
    """Article 14: the eligible rent over the reference rent, to the second decimal of its percentage."""

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        rent = self.sole(EligibleRentProvision)
        reference = self.sole(ReferenceRentProvision)
        return an(
            entity(
                inference(RentRatio)(
                    case=case,
                    fraction=Rounding.round_half_away_from_zero(
                        rent.amount / reference.amount, 4
                    ),
                )
            )
        )


@dataclass
class EligibleRentRateProvision(RentedAidProvision):
    """
    Article 14: none below a rent ratio of 45 %, 0.45 % of the ratio above 45 % up to
    75 %, and 0.68 % of it above 75 %, to the third decimal of its percentage.
    """

    @classproperty
    def lower_threshold(cls) -> Fraction:
        """45 %."""
        return Fraction(45, 100)

    @classproperty
    def upper_threshold(cls) -> Fraction:
        """75 %."""
        return Fraction(75, 100)

    @classproperty
    def lower_slope(cls) -> Fraction:
        """0.45 %."""
        return Fraction(45, 10000)

    @classproperty
    def upper_slope(cls) -> Fraction:
        """0.68 %."""
        return Fraction(68, 10000)

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        ratio = self.sole(RentRatioProvision)
        rate = deduced_variable(EligibleRentRate)
        query = an(entity(rate).where(ratio.fraction < self.lower_threshold))
        with query:
            add(rate, inference(EligibleRentRate)(case=case, fraction=Fraction(0)))
            with alternative(ratio.fraction < self.upper_threshold):
                add(
                    rate,
                    self.inferred(
                        case, self.lower_slope * (ratio.fraction - self.lower_threshold)
                    ),
                )
            with alternative():
                add(
                    rate,
                    self.inferred(
                        case,
                        self.lower_slope * (self.upper_threshold - self.lower_threshold)
                        + self.upper_slope * (ratio.fraction - self.upper_threshold),
                    ),
                )
        return query

    @staticmethod
    def inferred(case: RentedAidCase, rate: Fraction) -> EligibleRentRate:
        """:return: The inference of *rate* rounded to five decimals, over a variable of the case."""
        return inference(EligibleRentRate)(
            case=case, fraction=Rounding.round_half_away_from_zero(rate, 5)
        )


@dataclass
class IncomeAbatementProvision(RentedAidProvision):
    """
    D823-17 and article 15: the abatement of resources, by household. Article 46 sets its
    own overseas for one dependant, article 47 its own in Saint-Pierre-et-Miquelon from
    July 2022, and in Mayotte in 2020 and 2021.
    """

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        couple = case.family_situation == AidFamilySituation.COUPLE
        dependants = variable(
            ScaledDependants,
            domain=ScaledDependantsProvision(case=self.case).conclusions,
        )
        territorial = [
            (case.residence == territory, abatements)
            for territory, abatements in (
                (Territory.MAYOTTE, self.case.mayotte_abatements),
                (
                    Territory.SAINT_PIERRE_AND_MIQUELON,
                    self.case.saint_pierre_abatements,
                ),
            )
            if abatements is not None
        ]
        overseas = self.case.overseas_scale
        if overseas is not None:
            territorial.append(
                (
                    and_(
                        in_(case.residence, self.overseas_territories),
                        case.dependant_count == 1,
                    ),
                    overseas.one_dependant_abatement,
                )
            )
        metropolitan = inference(IncomeAbatement)(
            case=case,
            amount=IncomeAbatements.abatement_for(
                self.case.abatements, couple, dependants.count
            ),
        )
        branches = [
            RuleBranch(
                conditions=(place,), inferred=self.inferred(case, amount, couple)
            )
            for place, amount in territorial
        ]
        branches.append(RuleBranch(conditions=(), inferred=metropolitan))
        return RuleChain(
            conclusion=deduced_variable(IncomeAbatement), branches=branches
        ).query()

    @staticmethod
    def inferred(
        case: RentedAidCase, amount: IncomeAbatements | Money, couple: object
    ) -> IncomeAbatement:
        """:return: The inference of *amount*, or of the abatement of the table for the case's household, over a variable of the case."""
        if isinstance(amount, Money):
            return inference(IncomeAbatement)(case=case, amount=amount)
        return inference(IncomeAbatement)(
            case=case,
            amount=IncomeAbatements.abatement_for(amount, couple, case.dependant_count),
        )


@dataclass
class PersonalParticipationProvision(RentedAidProvision):
    """
    D823-17: the minimum participation and the resources beyond the abatement, at the
    family rate and the rate of the eligible rent together.
    """

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        minimum = self.sole(MinimumParticipationProvision)
        abatement = self.sole(IncomeAbatementProvision)
        family = self.sole(FamilyRateProvision)
        rent_rate = self.sole(EligibleRentRateProvision)
        from_resources = (case.resources - abatement.amount) * (
            family.fraction + rent_rate.fraction
        )
        participation = deduced_variable(PersonalParticipation)
        query = an(entity(participation).where(from_resources < Money.zero))
        with query:
            add(
                participation,
                inference(PersonalParticipation)(case=case, amount=minimum.amount),
            )
            with alternative():
                add(
                    participation,
                    inference(PersonalParticipation)(
                        case=case, amount=minimum.amount + from_resources
                    ),
                )
        return query


@dataclass
class InitialAidProvision(RentedAidProvision):
    """D823-16: the eligible rent and flat charges less the personal participation, none below zero."""

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        rent = self.sole(EligibleRentProvision)
        charges = self.sole(FlatChargesProvision)
        participation = self.sole(PersonalParticipationProvision)
        aid = rent.amount + charges.amount - participation.amount
        initial = deduced_variable(InitialAid)
        query = an(entity(initial).where(aid < Money.zero))
        with query:
            add(initial, inference(InitialAid)(case=case, amount=Money.zero))
            with alternative():
                add(initial, inference(InitialAid)(case=case, amount=aid))
        return query


@dataclass
class DegressivityCeilingProvision(RentedAidProvision):
    """Article 10: 3.4 times the rent ceiling in zone I, 2.5 times elsewhere."""

    @classproperty
    def multiples(cls) -> dict[HousingZone, Fraction]:
        """The multiple of the rent ceiling in each zone."""
        return {
            HousingZone.ZONE_1: Fraction(34, 10),
            HousingZone.ZONE_2: Fraction(25, 10),
            HousingZone.ZONE_3: Fraction(25, 10),
        }

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        ceiling = self.sole(RentCeilingProvision)
        return an(
            entity(
                inference(DegressivityCeiling)(
                    case=case, amount=ceiling.amount * self.multiples[self.case.zone]
                )
            )
        )


@dataclass
class SuppressionCeilingProvision(RentedAidProvision):
    """Article 10: 4 times the rent ceiling in zone I, 3.1 times elsewhere."""

    @classproperty
    def multiples(cls) -> dict[HousingZone, Fraction]:
        """The multiple of the rent ceiling in each zone."""
        return {
            HousingZone.ZONE_1: Fraction(4),
            HousingZone.ZONE_2: Fraction(31, 10),
            HousingZone.ZONE_3: Fraction(31, 10),
        }

    def query(self) -> Query:
        case = variable(RentedAidCase, domain=[self.case])
        ceiling = self.sole(RentCeilingProvision)
        return an(
            entity(
                inference(SuppressionCeiling)(
                    case=case, amount=ceiling.amount * self.multiples[self.case.zone]
                )
            )
        )


@dataclass
class SocialContributionProvision(ScopeProvision):
    """
    Article 19 of the ordinance of 1996: the contribution to the repayment of the social
    debt is 0.5 % of the aid from 2020; LO6414-1 exempts Saint-Pierre-et-Miquelon.
    """

    @classproperty
    def rate(cls) -> Fraction:
        """0.5 %."""
        return Fraction(5, 1000)

    def query(self) -> Query:
        case = variable(ScopeCase, domain=[self.case])
        contribution = deduced_variable(SocialContribution)
        query = an(
            entity(contribution).where(
                case.residence == Territory.SAINT_PIERRE_AND_MIQUELON
            )
        )
        with query:
            add(
                contribution,
                inference(SocialContribution)(case=case, rate=self.rate, exempt=True),
            )
            with alternative():
                add(
                    contribution,
                    inference(SocialContribution)(
                        case=case, rate=self.rate, exempt=False
                    ),
                )
        return query


# %% the treatment of the aid


@dataclass(frozen=True)
class Contribution:
    """The contribution to the repayment of the social debt on an aid."""

    @staticmethod
    @symbolic_function
    def amount(aid: Money, contribution: SocialContribution) -> Money:
        """:return: *aid* at the rate of *contribution*, rounded down to the cent as Catala's example rounds it; none where it is exempt."""
        if contribution.exempt:
            return Money.zero
        hundredfold = (aid * contribution.rate) * 100
        return (hundredfold - Money(cents=50)).rounded_to_units() * Fraction(1, 100)


@dataclass(eq=False)
class AidTreatment(AssessedCase):
    """An aid treated as ``traitement_aide_finale`` treats it for a case."""

    case: ScopeCase
    """The case, whose scope's treatment it is."""

    aid: Money
    """The aid treated."""

    def sole_amount(self, provision: type[TreatmentProvision]) -> Money | None:
        """:return: The amount *provision* concludes; None where it concludes none."""
        conclusions = provision(treatment=self).conclusions
        return conclusions[0].amount if conclusions else None


@dataclass(eq=False)
class TreatedAid(Conclusion):
    """The aid after a step of its treatment."""

    treatment: AidTreatment
    """The treatment."""

    amount: Money = field(default_factory=lambda: Money.zero)
    """The aid after the step."""


@dataclass(eq=False)
class DegressiveAid(TreatedAid):
    """D823-16: the aid decreased with the rent."""


@dataclass(eq=False)
class FlatReducedAid(TreatedAid):
    """D823-16 and article 11: the aid less its flat reduction."""


@dataclass(eq=False)
class ContributionRoundedAid(TreatedAid):
    """D823-16: the aid net of its contribution rounded down to the euro, the contribution added back."""


@dataclass(eq=False)
class SolidarityReducedAid(TreatedAid):
    """L832-3: the aid less part of the solidarity rent reduction."""


@dataclass(eq=False)
class SaintPierrePhasedAid(TreatedAid):
    """Article 7 of décret n° 2021-1750: the aid phased in in Saint-Pierre-et-Miquelon."""


@dataclass(eq=False)
class MinimumCheckedAid(TreatedAid):
    """D823-16 and article 12: the aid, none below the least amount paid."""


@dataclass
class TreatmentProvision(Provision, ABC):
    """A step of the treatment of an aid."""

    treatment: AidTreatment
    """The treatment."""

    @property
    def assessed_case(self) -> AssessedCase:
        return self.treatment

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision] | None:
        """The step before this one; None for the first, which treats the aid itself."""
        return None

    def previous_amount(self, treatment: AidTreatment) -> Money:
        """:return: The aid after the previous step, over a variable of *treatment*."""
        if self.previous_step is None:
            return treatment.aid
        return variable(
            TreatedAid, domain=self.previous_step(treatment=self.treatment).conclusions
        ).amount

    def case_conclusion(self, provision: type[ScopeProvision]) -> CaseConclusion:
        """:return: A variable over the one conclusion *provision* draws about the case."""
        return variable(
            CaseConclusion, domain=provision(case=self.treatment.case).conclusions
        )


@dataclass
class DegressiveAidProvision(TreatmentProvision):
    """
    D823-16: no aid above the suppression ceiling, an aid decreasing in proportion
    between the degressivity and suppression ceilings; the aid unchanged for a household
    receiving the allowance for a disabled adult or child.
    """

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        case = treatment.case
        rent = self.case_conclusion(FurnishedRentProvision)
        degressivity = self.case_conclusion(DegressivityCeilingProvision)
        suppression = self.case_conclusion(SuppressionCeilingProvision)
        aid = deduced_variable(DegressiveAid)
        query = an(entity(aid).where(case.disability_aid_recipient == True))
        with query:
            add(
                aid, inference(DegressiveAid)(treatment=treatment, amount=treatment.aid)
            )
            with alternative(rent.amount > suppression.amount):
                add(
                    aid,
                    inference(DegressiveAid)(treatment=treatment, amount=Money.zero),
                )
            with alternative(rent.amount > degressivity.amount):
                add(
                    aid,
                    inference(DegressiveAid)(
                        treatment=treatment,
                        amount=treatment.aid
                        - treatment.aid
                        * (
                            (rent.amount - degressivity.amount)
                            / (suppression.amount - degressivity.amount)
                        ),
                    ),
                )
            with alternative():
                add(
                    aid,
                    inference(DegressiveAid)(treatment=treatment, amount=treatment.aid),
                )
        return query


@dataclass
class FlatReducedAidProvision(TreatmentProvision):
    """D823-16 and article 11: the aid less 5 €, none below zero."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`DegressiveAidProvision`."""
        return DegressiveAidProvision

    @classproperty
    def flat_reduction(cls) -> Money:
        """Article 11: 5 €."""
        return Money.from_euros(5)

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        previous = self.previous_amount(treatment)
        aid = deduced_variable(FlatReducedAid)
        query = an(entity(aid).where(previous - self.flat_reduction >= Money.zero))
        with query:
            add(
                aid,
                inference(FlatReducedAid)(
                    treatment=treatment, amount=previous - self.flat_reduction
                ),
            )
            with alternative():
                add(
                    aid,
                    inference(FlatReducedAid)(treatment=treatment, amount=Money.zero),
                )
        return query


@dataclass
class ContributionRoundedAidProvision(TreatmentProvision):
    """D823-16: the aid net of its contribution, rounded down to the euro, and the contribution added back."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`FlatReducedAidProvision`."""
        return FlatReducedAidProvision

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        previous = self.previous_amount(treatment)
        social = self.case_conclusion(SocialContributionProvision)
        contribution = Contribution.amount(previous, social)
        net = MoneyRounding.rounded_to_units(previous - contribution - Money(cents=50))
        aid = deduced_variable(ContributionRoundedAid)
        query = an(entity(aid).where(net + contribution >= Money.zero))
        with query:
            add(
                aid,
                inference(ContributionRoundedAid)(
                    treatment=treatment, amount=net + contribution
                ),
            )
            with alternative():
                add(
                    aid,
                    inference(ContributionRoundedAid)(
                        treatment=treatment, amount=Money.zero
                    ),
                )
        return query


@dataclass
class SolidarityReducedAidProvision(TreatmentProvision):
    """L832-3 and D823-16: the aid less 98 % of the solidarity rent reduction, none below zero."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`ContributionRoundedAidProvision`."""
        return ContributionRoundedAidProvision

    @classproperty
    def share_of_reduction(cls) -> Fraction:
        """D823-16: 98 %."""
        return Fraction(98, 100)

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        previous = self.previous_amount(treatment)
        reduced = previous - (
            treatment.case.solidarity_rent_reduction * self.share_of_reduction
        )
        aid = deduced_variable(SolidarityReducedAid)
        query = an(entity(aid).where(reduced >= Money.zero))
        with query:
            add(
                aid,
                inference(SolidarityReducedAid)(treatment=treatment, amount=reduced),
            )
            with alternative():
                add(
                    aid,
                    inference(SolidarityReducedAid)(
                        treatment=treatment, amount=Money.zero
                    ),
                )
        return query


@dataclass
class SaintPierrePhasedAidProvision(TreatmentProvision):
    """
    Article 7 of décret n° 2021-1750: in Saint-Pierre-et-Miquelon from 2022 to 2025, the
    aid less an eighth for each year before 2026.
    """

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`SolidarityReducedAidProvision`."""
        return SolidarityReducedAidProvision

    @classproperty
    def first_day(cls) -> datetime.date:
        """January 1, 2022."""
        return datetime.date(2022, 1, 1)

    @classproperty
    def last_day(cls) -> datetime.date:
        """December 31, 2025."""
        return datetime.date(2025, 12, 31)

    @classproperty
    def full_year(cls) -> int:
        """2026, the year the aid is paid in full."""
        return 2026

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        case = treatment.case
        previous = self.previous_amount(treatment)
        year = self.treatment.case.assessment_date.year
        aid = deduced_variable(SaintPierrePhasedAid)
        query = an(
            entity(aid).where(
                case.residence == Territory.SAINT_PIERRE_AND_MIQUELON,
                case.assessment_date >= self.first_day,
                case.assessment_date <= self.last_day,
            )
        )
        with query:
            add(
                aid,
                inference(SaintPierrePhasedAid)(
                    treatment=treatment,
                    amount=previous * (1 - Fraction(self.full_year - year, 8)),
                ),
            )
            with alternative():
                add(
                    aid,
                    inference(SaintPierrePhasedAid)(
                        treatment=treatment, amount=previous
                    ),
                )
        return query


@dataclass
class MinimumAidProvision(TreatmentProvision):
    """D823-16 and article 12: no aid below 10 € for the allowances; none for the personalised aid."""

    @classproperty
    def previous_step(cls) -> type[TreatmentProvision]:
        """:class:`SaintPierrePhasedAidProvision`."""
        return SaintPierrePhasedAidProvision

    @classproperty
    def least_allowance(cls) -> Money:
        """Article 12: 10 €."""
        return Money.from_euros(10)

    def query(self) -> Query:
        treatment = variable(AidTreatment, domain=[self.treatment])
        case = treatment.case
        previous = self.previous_amount(treatment)
        aid = deduced_variable(MinimumCheckedAid)
        query = an(
            entity(aid).where(
                or_(
                    case.aid_type == AidType.FAMILY_ALLOWANCE,
                    case.aid_type == AidType.SOCIAL_ALLOWANCE,
                ),
                previous < self.least_allowance,
            )
        )
        with query:
            add(
                aid,
                inference(MinimumCheckedAid)(treatment=treatment, amount=Money.zero),
            )
            with alternative():
                add(
                    aid,
                    inference(MinimumCheckedAid)(treatment=treatment, amount=previous),
                )
        return query


@dataclass(frozen=True)
class MoneyRounding:
    """Rounds money to whole units inside a rule."""

    @staticmethod
    @symbolic_function
    def rounded_to_units(amount: Money) -> Money:
        """:return: *amount* as :meth:`Money.rounded_to_units` rounds it."""
        return amount.rounded_to_units()


# %% test files


class RentedTestFile(ScopeTestFile, StrEnum):
    """The test files of the aids of rented homes of Catala's ``aides_logement`` example."""

    PERSONALISED_AID = "tests_calcul_apl_locatif.catala_fr"
    """Nine households asking the personalised aid."""

    HOUSING_ALLOWANCE = "tests_calcul_al_locatif.catala_fr"
    """Four households asking the housing allowance, one in Saint-Pierre-et-Miquelon."""

    TIME_COVERAGE = "tests_couverture_temporelle.catala_fr"
    """Three households whose aid is computed for each quarter from October 2023 to July 2027."""

    @property
    def directory(self) -> Path:
        """:file:`aides_logement/tests`."""
        return CatalaDirectory.ROOT / "aides_logement" / "tests"

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """The personalised aid and the housing allowance of rented homes."""
        return [RentedAidCase, RentedAllowanceCase]
