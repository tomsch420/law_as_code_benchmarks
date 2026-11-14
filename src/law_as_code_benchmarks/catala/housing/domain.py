"""
The situation the personal housing aids are computed for: the household, its dwelling
and how it occupies it, the persons in its charge and the applicant, each mirrored from
the structures and enumerations of the prologue of Catala's ``aides_logement``.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction

from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.catala.domain import SchoolingStage, Territory
from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.scope_test import CatalaRecord, CatalaVariant

# %% enumerations without content


class HousingZone(StrEnum):
    """The geographic zones of the arrêté of March 17, 1978, each named as Catala's ``ZoneDHabitation``."""

    ZONE_1 = "Zone1"
    """Zone I, the Paris area."""

    ZONE_2 = "Zone2"
    """Zone II, the large towns, Corsica and the overseas departments."""

    ZONE_3 = "Zone3"
    """Zone III, the rest of the territory."""


class BenefitReceived(StrEnum):
    """The family benefits a household receives that matter to the housing aids, each named as Catala's ``PrestationReçue``."""

    FAMILY_ALLOWANCES = "AllocationsFamiliales"
    """The family allowances."""

    FAMILY_SUPPLEMENT = "ComplémentFamilial"
    """The family supplement."""

    FAMILY_SUPPORT_ALLOWANCE = "AllocationSoutienFamilial"
    """The family support allowance."""

    DISABLED_CHILD_EDUCATION_ALLOWANCE = "AllocationSoutienEnfantHandicapé"
    """The allowance for the education of a disabled child."""


class Kinship(StrEnum):
    """How a person in the household's charge other than a child is related, each named as Catala's ``Parenté``."""

    ASCENDANT = "Ascendant"
    """A parent, grandparent or further ascendant."""

    DESCENDANT = "Descendant"
    """A child, grandchild or further descendant."""

    COLLATERAL_SECOND_OR_THIRD_DEGREE = "CollatéralDeuxièmeTroisièmeDegré"
    """A sibling, uncle, aunt, nephew or niece."""


class LoanType(StrEnum):
    """The loans financing a home bought, by the article defining them, each named as Catala's ``TypePrêt``."""

    ARTICLE_D331_32 = "D331_32"
    """A loan of article D331-32."""

    ARTICLES_D331_63_64 = "D331_63_64"
    """A loan of articles D331-63 and D331-64."""

    ARTICLE_D331_59_8 = "D331_59_8"
    """A loan of article D331-59-8."""

    ARTICLE_D331_76_1 = "D331_76_1"
    """A loan of article D331-76-1."""

    OTHER = "Autre"
    """Any other loan."""


class LoanHolder(StrEnum):
    """Who holds the loan financing a home bought, each named as Catala's ``TitulairePrêt``."""

    APPLICANT = "Demandeur"
    """The applicant."""

    SELLER_UNDER_LEASE_TO_OWN = "VendeurQuandDemandeurAContratLocationAccession"
    """The seller, the applicant holding a lease-to-own contract."""


class AcquisitionWorks(StrEnum):
    """The works on a home bought of article D832-15, each named as Catala's ``TypeTravauxLogementD832_15``."""

    WORKS_FOR_ACQUISITION = "TravauxPourAcquisitionD832_15_1"
    """Works done as part of buying the home, 1°."""

    WORKS_ON_ACQUIRED_HOME = "TravauxSurLogementDéjàAcquisD832_15_2"
    """Works on a home already bought, 2°."""

    NO_WORKS = "PasDeTravaux"
    """No works."""


class OwnershipWorks(StrEnum):
    """The works on a home bought of article R842-5, each named as Catala's ``TypeTravauxLogementR842_5``."""

    DECENCY = "ObjectifDécenceLogement"
    """Works making the home decent."""

    LISTED_IN_R321_15 = "PrévuDansListeR321_15"
    """Works on the list of article R321-15."""

    ENLARGE_OR_MAKE_HABITABLE = "AgrandirOuRendreHabitableD331_63"
    """Works enlarging the home or making it habitable, of article D331-63."""

    NO_WORKS = "PasDeTravaux"
    """No works."""


class ImprovedByOccupant(StrEnum):
    """Whether the occupant improved an old home, each named as Catala's ``AmélioréParOccupant``."""

    YES = "Oui"
    """The occupant improved it."""

    NO = "Non"
    """The occupant did not."""


class ResidenceHallType(StrEnum):
    """The kinds of residence hall (*logement-foyer*), each named as Catala's ``TypeLogementFoyer``."""

    ELDERLY_OR_DISABLED = "LogementPersonnesÂgéesOuHandicapées"
    """A hall for elderly or disabled persons."""

    SOCIAL_RESIDENCE = "RésidenceSociale"
    """A social residence."""

    YOUNG_WORKERS_OR_MIGRANTS_BEFORE_1995 = (
        "FoyerJeunesTravailleursOuMigrantsConventionnéL353_2Avant1995"
    )
    """A hostel for young workers or migrants under an agreement of L353-2 signed before 1995."""

    OTHER = "Autre"
    """Any other hall."""


class ResidenceHallRentCategory(StrEnum):
    """The categories of rent equivalence of article D842-16, each named as Catala's ``CatégorieÉquivalenceLoyerAllocationLogementFoyer``."""

    STUDENT_IN_UNIVERSITY_ROOM = "ÉtudiantLogéEnChambreCROUS"
    """A student in a room of a regional student services centre (*CROUS*)."""

    STUDENT_IN_RENOVATED_UNIVERSITY_ROOM = "ÉtudiantLogéEnChambreCROUSRéhabilitée"
    """A student in a renovated room of a regional student services centre."""

    ELDERLY_UNDER_D842_16_3 = "PersonnesÂgéesSelon3DeD842_16"
    """An elderly person of 3° of D842-16."""

    OTHER_PERSONS = "AutresPersonnes"
    """Anyone else."""


# %% family situation


@dataclass(eq=False)
class FamilySituation(CatalaVariant):
    """The applicant's family situation, Catala's ``SituationFamiliale``."""

    @classproperty
    def adult_count(cls) -> int:
        """How many adults the situation counts: one for a person alone, two for a couple."""
        return 2


@dataclass(eq=False)
class Single(FamilySituation):
    """A person alone, ``Célibataire``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Célibataire``."""
        return "Célibataire"

    @classproperty
    def adult_count(cls) -> int:
        """One."""
        return 1


@dataclass(eq=False)
class Married(FamilySituation):
    """A married couple, ``Mariés``."""

    wedding_date: datetime.date | None = None
    """The day the couple married, which article L841-1 counts from."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Mariés``."""
        return "Mariés"

    @classproperty
    def content_field(cls) -> str:
        """The wedding date."""
        return "wedding_date"


@dataclass(eq=False)
class CivilPartners(FamilySituation):
    """Partners of a civil solidarity pact, ``Pacsés``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Pacsés``."""
        return "Pacsés"


@dataclass(eq=False)
class Cohabiting(FamilySituation):
    """A couple living together unmarried, ``Concubins``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Concubins``."""
        return "Concubins"


@dataclass(eq=False)
class SeparatedSingle(FamilySituation):
    """A person separated in fact from their spouse, ``CélibataireSéparéDeFait``, of R821-3."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``CélibataireSéparéDeFait``."""
        return "CélibataireSéparéDeFait"

    @classproperty
    def adult_count(cls) -> int:
        """One."""
        return 1


@dataclass(eq=False)
class SeparatedCohabiting(FamilySituation):
    """A couple of whom one is separated in fact from a spouse, ``ConcubinageDontSéparéDeFait``, of R821-3."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``ConcubinageDontSéparéDeFait``."""
        return "ConcubinageDontSéparéDeFait"


# %% nationality


@dataclass(eq=False)
class ForeignerConditions(CatalaRecord):
    """The conditions a foreigner meets, Catala's ``ConditionsÉtrangers``."""

    meets_l512_2: bool
    """Whether the conditions of article L512-2 of the Code de la sécurité sociale are met."""

    meets_mayotte_ordinance_article_4: bool
    """Whether those of article 4 of the ordinance of 2002 on Mayotte are met."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``ConditionsÉtrangers``."""
        return {
            "satisfait_conditions_l512_2_code_sécurité_sociale": "meets_l512_2",
            "satisfait_art_4_ordonnance_2002_mayotte": "meets_mayotte_ordinance_article_4",
        }


@dataclass(eq=False)
class Nationality(CatalaVariant):
    """A person's nationality, Catala's ``Nationalité``."""


@dataclass(eq=False)
class French(Nationality):
    """French, ``Française``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Française``."""
        return "Française"


@dataclass(eq=False)
class Foreign(Nationality):
    """Foreign, ``Étrangère``, with the conditions met."""

    conditions: ForeignerConditions | None = None
    """The conditions the foreigner meets."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Étrangère``."""
        return "Étrangère"

    @classproperty
    def content_field(cls) -> str:
        """The conditions."""
        return "conditions"


# %% persons in the household's charge


@dataclass(eq=False)
class ChildCareSharing(CatalaVariant):
    """Whether a child lives with each parent in turn, Catala's ``SituationGardeAlternée``."""


@dataclass(eq=False)
class NoSharedResidence(ChildCareSharing):
    """The child does not, ``PasDeGardeAlternée``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``PasDeGardeAlternée``."""
        return "PasDeGardeAlternée"


@dataclass(eq=False)
class SharedResidence(ChildCareSharing):
    """The child does, ``GardeAlternéeCoefficientPriseEnCharge``, counting for a coefficient."""

    coefficient: Fraction = Fraction(0)
    """The share of the child the household is in charge of."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``GardeAlternéeCoefficientPriseEnCharge``."""
        return "GardeAlternéeCoefficientPriseEnCharge"

    @classproperty
    def content_field(cls) -> str:
        """The coefficient."""
        return "coefficient"


@dataclass(eq=False)
class DependentChild(CatalaRecord):
    """A child in the household's charge, Catala's ``EnfantÀCharge``."""

    identifier: int
    """The number the case gives the child."""

    nationality: Nationality
    """The child's nationality."""

    has_opened_family_allowance: bool
    """Whether the child has already given a right to family allowances."""

    birth_date: datetime.date
    """The day the child was born."""

    monthly_pay: Money
    """What the child earns in a month."""

    schooling_stage: SchoolingStage
    """Where the child stands to compulsory schooling."""

    care_sharing: ChildCareSharing
    """Whether the child lives with each parent in turn."""

    studying_or_unable_to_work: bool
    """Whether the child pursues studies, an apprenticeship, an internship or vocational training, or cannot work."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``EnfantÀCharge``."""
        return {
            "identifiant": "identifier",
            "nationalité": "nationality",
            "a_déjà_ouvert_droit_aux_allocations_familiales": "has_opened_family_allowance",
            "date_de_naissance": "birth_date",
            "rémuneration_mensuelle": "monthly_pay",
            "obligation_scolaire": "schooling_stage",
            "situation_garde_alternée": "care_sharing",
            "études_apprentissage_stage_formation_pro_impossibilité_travail": "studying_or_unable_to_work",
        }


@dataclass(eq=False)
class OtherDependentPerson(CatalaRecord):
    """A person in the household's charge other than a child, Catala's ``AutrePersonneÀCharge``."""

    birth_date: datetime.date
    """The day the person was born."""

    resources: Money
    """The person's resources."""

    related_up_to_third_degree: bool
    """Whether the person is an ascendant, a descendant or a collateral of the second or third degree."""

    kinship: Kinship
    """How the person is related."""

    disabled_or_restricted_from_work: bool
    """Whether the person's incapacity is of 80 % at least, or their access to work restricted."""

    beneficiary_l161_19_l351_8_l643_3: bool
    """Whether the person benefits from articles L161-19, L351-8 or L643-3 of the Code de la sécurité sociale."""

    old_age_allowance_holder: bool
    """Whether the person holds an allowance for the elderly."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``AutrePersonneÀCharge``."""
        return {
            "date_naissance": "birth_date",
            "ressources": "resources",
            "ascendant_descendant_collatéral_deuxième_troisième_degré": "related_up_to_third_degree",
            "parenté": "kinship",
            "incapacité_80_pourcent_ou_restriction_emploi": "disabled_or_restricted_from_work",
            "bénéficiaire_l161_19_l351_8_l643_3_sécu": "beneficiary_l161_19_l351_8_l643_3",
            "titulaire_allocation_personne_âgée": "old_age_allowance_holder",
        }


@dataclass(eq=False)
class Dependant(CatalaVariant):
    """A person in the household's charge, Catala's ``PersonneÀCharge``."""


@dataclass(eq=False)
class ChildDependant(Dependant):
    """A child, ``EnfantÀCharge``."""

    child: DependentChild | None = None
    """The child."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``EnfantÀCharge``."""
        return "EnfantÀCharge"

    @classproperty
    def content_field(cls) -> str:
        """The child."""
        return "child"


@dataclass(eq=False)
class OtherDependant(Dependant):
    """Another person, ``AutrePersonneÀCharge``."""

    person: OtherDependentPerson | None = None
    """The person."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``AutrePersonneÀCharge``."""
        return "AutrePersonneÀCharge"

    @classproperty
    def content_field(cls) -> str:
        """The person."""
        return "person"


# %% renting


@dataclass(eq=False)
class SocialLandlordAgreement(CatalaRecord):
    """What a social landlord agreed to, Catala's ``ConventionBailleurSocial``."""

    agreed_under_book_iii_title_v_chapter_iii: bool
    """Whether the dwelling is under an agreement of chapter III of title V of book III of the Code de la construction."""

    solidarity_rent_reduction: Money
    """The solidarity rent reduction (*réduction de loyer de solidarité*) the landlord grants."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``ConventionBailleurSocial``."""
        return {
            "conventionné_livre_III_titre_V_chap_III": "agreed_under_book_iii_title_v_chapter_iii",
            "réduction_loyer_solidarité_perçue": "solidarity_rent_reduction",
        }


@dataclass(eq=False)
class HousingAgencyAgreement(CatalaRecord):
    """What a private landlord agreed to with the national housing agency, Catala's ``ConventionANHA``."""

    agreed_under_book_iii_title_ii_chapter_i_section_3: bool
    """Whether the dwelling is under an agreement of section 3 of chapter I of title II of book III."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The field of ``ConventionANHA``."""
        return {
            "conventionné_livre_III_titre_II_chap_I_sec_3": "agreed_under_book_iii_title_ii_chapter_i_section_3"
        }


@dataclass(eq=False)
class Landlord(CatalaVariant):
    """Who lets the dwelling, Catala's ``TypeBailleur``."""


@dataclass(eq=False)
class SocialLandlord(Landlord):
    """A social landlord, ``BailleurSocial``."""

    agreement: SocialLandlordAgreement | None = None
    """What the landlord agreed to."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``BailleurSocial``."""
        return "BailleurSocial"

    @classproperty
    def content_field(cls) -> str:
        """The agreement."""
        return "agreement"


@dataclass(eq=False)
class AgreedPrivateLandlord(Landlord):
    """A private landlord under an agreement with the housing agency, ``BailleurPrivéAvecConventionnementSocial``."""

    agreement: HousingAgencyAgreement | None = None
    """What the landlord agreed to."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``BailleurPrivéAvecConventionnementSocial``."""
        return "BailleurPrivéAvecConventionnementSocial"

    @classproperty
    def content_field(cls) -> str:
        """The agreement."""
        return "agreement"


@dataclass(eq=False)
class PrivateLandlord(Landlord):
    """Any other private landlord, ``BailleurPrivé``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``BailleurPrivé``."""
        return "BailleurPrivé"


@dataclass(eq=False)
class MoveDetails(CatalaRecord):
    """The rent and allowance before a move, Catala's ``InfosChangementLogementD842_4``."""

    previous_rent: Money
    """The rent of the previous dwelling."""

    previous_housing_allowance: Money
    """The housing allowance received for it."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``InfosChangementLogementD842_4``."""
        return {
            "ancien_loyer_principal": "previous_rent",
            "ancienne_allocation_logement": "previous_housing_allowance",
        }


@dataclass(eq=False)
class HomeChange(CatalaVariant):
    """Whether the household moved, as article D842-4 asks, Catala's ``ChangementLogementD842_4``."""


@dataclass(eq=False)
class Moved(HomeChange):
    """The household moved, ``Changement``."""

    details: MoveDetails | None = None
    """The rent and allowance before the move."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Changement``."""
        return "Changement"

    @classproperty
    def content_field(cls) -> str:
        """The details."""
        return "details"


@dataclass(eq=False)
class NotMoved(HomeChange):
    """The household did not, ``PasDeChangement``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``PasDeChangement``."""
        return "PasDeChangement"


@dataclass(eq=False)
class Tenancy(CatalaRecord):
    """A dwelling rented, Catala's ``Location``."""

    landlord: Landlord
    """Who lets it."""

    rent: Money
    """The monthly rent, charges aside."""

    disability_aid_recipient: bool
    """Whether the household receives the allowance for a disabled adult or child."""

    is_room: bool
    """Whether the dwelling is a room."""

    is_house_share: bool
    """Whether the dwelling is shared with other tenants (*colocation*)."""

    paying_guests_elderly_or_disabled: bool
    """Whether elderly or disabled adults are lodged for payment by private persons."""

    furnished_d842_2: bool
    """Whether the dwelling is let furnished, as article D842-2 asks."""

    home_change: HomeChange
    """Whether the household moved, as article D842-4 asks."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``Location``."""
        return {
            "bailleur": "landlord",
            "loyer_principal": "rent",
            "bénéficiaire_aide_adulte_ou_enfant_handicapés": "disability_aid_recipient",
            "logement_est_chambre": "is_room",
            "colocation": "is_house_share",
            "âgées_ou_handicap_adultes_hébergées_onéreux_particuliers": "paying_guests_elderly_or_disabled",
            "logement_meublé_d842_2": "furnished_d842_2",
            "changement_logement_d842_4": "home_change",
        }


# %% buying


@dataclass(eq=False)
class OverseasFinancingAgreement(CatalaVariant):
    """Whether the State's representative overseas agreed to the financing, Catala's ``AccordFinancementReprésentantÉtatOutreMer``."""


@dataclass(eq=False)
class FinancingAgreed(OverseasFinancingAgreement):
    """The representative agreed, ``Accord``, on a day."""

    agreement_date: datetime.date | None = None
    """The day of the agreement."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Accord``."""
        return "Accord"

    @classproperty
    def content_field(cls) -> str:
        """The agreement date."""
        return "agreement_date"


@dataclass(eq=False)
class NoFinancingAgreement(OverseasFinancingAgreement):
    """The representative did not, ``PasdAccord``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``PasdAccord``."""
        return "PasdAccord"


@dataclass(eq=False)
class Loan(CatalaRecord):
    """The loan financing a home bought, Catala's ``Prêt``."""

    loan_type: LoanType
    """The article defining the loan."""

    signature_date: datetime.date
    """The day the loan was signed."""

    holder: LoanHolder
    """Who holds it."""

    overseas_financing_agreement: OverseasFinancingAgreement
    """Whether the State's representative overseas agreed to the financing."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``Prêt``."""
        return {
            "type_prêt": "loan_type",
            "date_signature": "signature_date",
            "titulaire_prêt": "holder",
            "accord_financement_représentant_État_outre_mer": "overseas_financing_agreement",
        }


@dataclass(eq=False)
class BuildingAge(CatalaVariant):
    """Whether a home bought is new or old, Catala's ``NeufOuAncien``."""


@dataclass(eq=False)
class NewBuilding(BuildingAge):
    """New, ``Neuf``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Neuf``."""
        return "Neuf"


@dataclass(eq=False)
class OldBuilding(BuildingAge):
    """Old, ``Ancien``, improved by its occupant or not."""

    improved_by_occupant: ImprovedByOccupant = ImprovedByOccupant.NO
    """Whether the occupant improved it."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Ancien``."""
        return "Ancien"

    @classproperty
    def content_field(cls) -> str:
        """Whether the occupant improved it."""
        return "improved_by_occupant"


@dataclass(eq=False)
class HomeOwner(CatalaRecord):
    """A household buying its home, Catala's ``Propriétaire``."""

    monthly_repayment: Money
    """The loan's monthly repayment."""

    monthly_loan_charges: Money
    """The loan's monthly charges."""

    entry_date: datetime.date
    """The day the household moved in."""

    acquisition_works: AcquisitionWorks
    """The works of article D832-15."""

    ownership_works: OwnershipWorks
    """The works of article R842-5."""

    first_occupation_by_beneficiary: bool
    """Whether the beneficiary is the first to live in the home."""

    co_ownership: bool
    """Whether the home is in a co-owned building."""

    situation_r822_11_13_17: bool
    """Whether the household is in the situation of articles R822-11, R822-13 or R822-17."""

    building_age: BuildingAge
    """Whether the home is new or old."""

    loan: Loan
    """The loan financing it."""

    state_aided_social_scalable_housing: bool
    """Whether the home comes of operations of scalable social housing for State-aided ownership."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``Propriétaire``."""
        return {
            "mensualité_principale": "monthly_repayment",
            "charges_mensuelles_prêt": "monthly_loan_charges",
            "date_entrée_logement": "entry_date",
            "type_travaux_logement_d832_15": "acquisition_works",
            "type_travaux_logement_r842_5": "ownership_works",
            "local_habité_première_fois_bénéficiaire": "first_occupation_by_beneficiary",
            "copropriété": "co_ownership",
            "situation_r822_11_13_17": "situation_r822_11_13_17",
            "ancienneté_logement": "building_age",
            "prêt": "loan",
            "opérations_logement_évolutifs_sociaux_accession_propriété_aidée_État": "state_aided_social_scalable_housing",
        }


# %% residence halls


@dataclass(eq=False)
class ResidenceHall(CatalaRecord):
    """A residence hall (*logement-foyer*) the applicant lives in, Catala's ``LogementFoyer``."""

    hall_type: ResidenceHallType
    """The kind of hall."""

    young_workers_hostel: bool
    """Whether it is a hostel for young workers."""

    meets_r832_21: bool
    """Whether it meets the conditions of article R832-21."""

    agreed_under_book_iii_title_v_chapter_iii: bool
    """Whether it is under an agreement of chapter III of title V of book III."""

    agreed_under_overseas_rules: bool
    """Whether it is under an agreement of the rules of the overseas departments."""

    agreement_date: datetime.date
    """The day of the agreement."""

    built_under_1957_law: bool
    """Whether it was built under III of article 12 of the law of 1957."""

    fee: Money
    """The monthly fee (*redevance*)."""

    rent_equivalence_category: ResidenceHallRentCategory
    """The category of rent equivalence of article D842-16."""

    disability_aid_recipient: bool
    """Whether the household receives the allowance for a disabled adult or child."""

    furnished_d842_2: bool
    """Whether the dwelling is let furnished, as article D842-2 asks."""

    is_room: bool
    """Whether the dwelling is a room."""

    is_house_share: bool
    """Whether the dwelling is shared."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``LogementFoyer``."""
        return {
            "type_logement": "hall_type",
            "logement_foyer_jeunes_travailleurs": "young_workers_hostel",
            "remplit_conditions_r832_21": "meets_r832_21",
            "conventionné_livre_III_titre_V_chap_III": "agreed_under_book_iii_title_v_chapter_iii",
            "conventionné_selon_règles_drom": "agreed_under_overseas_rules",
            "date_conventionnement": "agreement_date",
            "construit_application_loi_1957_12_III": "built_under_1957_law",
            "redevance": "fee",
            "catégorie_équivalence_loyer_d842_16": "rent_equivalence_category",
            "bénéficiaire_aide_adulte_ou_enfant_handicapés": "disability_aid_recipient",
            "logement_meublé_d842_2": "furnished_d842_2",
            "logement_est_chambre": "is_room",
            "colocation": "is_house_share",
        }


# %% how the dwelling is occupied


@dataclass(eq=False)
class Occupancy(CatalaVariant):
    """How the household occupies its dwelling, Catala's ``ModeOccupation``."""


@dataclass(eq=False)
class Tenant(Occupancy):
    """As a tenant, ``Locataire``."""

    tenancy: Tenancy | None = None
    """The tenancy."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Locataire``."""
        return "Locataire"

    @classproperty
    def content_field(cls) -> str:
        """The tenancy."""
        return "tenancy"


@dataclass(eq=False)
class Subtenant(Occupancy):
    """As a subtenant, ``SousLocataire``."""

    tenancy: Tenancy | None = None
    """The tenancy."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``SousLocataire``."""
        return "SousLocataire"

    @classproperty
    def content_field(cls) -> str:
        """The tenancy."""
        return "tenancy"


@dataclass(eq=False)
class ResidenceHallResident(Occupancy):
    """As a resident of a residence hall, ``RésidentLogementFoyer``."""

    hall: ResidenceHall | None = None
    """The hall."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``RésidentLogementFoyer``."""
        return "RésidentLogementFoyer"

    @classproperty
    def content_field(cls) -> str:
        """The hall."""
        return "hall"


@dataclass(eq=False)
class HomeBuyer(Occupancy):
    """As the buyer of a home used only to live in, ``AccessionPropriétéLocalUsageExclusifHabitation``."""

    owner: HomeOwner | None = None
    """The purchase."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``AccessionPropriétéLocalUsageExclusifHabitation``."""
        return "AccessionPropriétéLocalUsageExclusifHabitation"

    @classproperty
    def content_field(cls) -> str:
        """The purchase."""
        return "owner"


@dataclass(eq=False)
class LeaseToOwnBuyer(Occupancy):
    """Under a lease-to-own contract, ``LocationAccession``."""

    owner: HomeOwner | None = None
    """The purchase."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``LocationAccession``."""
        return "LocationAccession"

    @classproperty
    def content_field(cls) -> str:
        """The purchase."""
        return "owner"


# %% who owns the dwelling, and who lives in it besides


@dataclass(eq=False)
class RightHolder(CatalaVariant):
    """Who holds the ownership or the usufruct of the dwelling, Catala's ``ParentOuAutre``."""


@dataclass(eq=False)
class FamilyRightHolder(RightHolder):
    """
    The applicant, their spouse, a relative, or one of them through shares of a company,
    ``DemandeurOuConjointOuParentOuViaPartsSociétés``, holding a share.
    """

    share: Fraction = Fraction(0)
    """The share they hold."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``DemandeurOuConjointOuParentOuViaPartsSociétés``."""
        return "DemandeurOuConjointOuParentOuViaPartsSociétés"

    @classproperty
    def content_field(cls) -> str:
        """The share."""
        return "share"


@dataclass(eq=False)
class OtherRightHolder(RightHolder):
    """Anyone else, ``Autre``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Autre``."""
        return "Autre"


@dataclass(eq=False)
class SubletOccupant(CatalaRecord):
    """A person the dwelling is sublet to, Catala's ``PersonneSousLocation``."""

    birth_date: datetime.date
    """The day the person was born."""

    complies_with_l442_1: bool
    """Whether the subletting complies with article L442-1."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``PersonneSousLocation``."""
        return {
            "date_naissance_personne_sous_location": "birth_date",
            "conforme_article_l442_1": "complies_with_l442_1",
        }


@dataclass(eq=False)
class Subletting(CatalaVariant):
    """Whether the dwelling is let or sublet to third parties, Catala's ``LouéOuSousLouéÀDesTiers``."""


@dataclass(eq=False)
class NotSublet(Subletting):
    """It is not, ``Non``."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Non``."""
        return "Non"


@dataclass(eq=False)
class Sublet(Subletting):
    """It is, ``Oui``, to a person."""

    occupant: SubletOccupant | None = None
    """The person."""

    @classproperty
    def catala_constructor(cls) -> str:
        """``Oui``."""
        return "Oui"

    @classproperty
    def content_field(cls) -> str:
        """The person."""
        return "occupant"


# %% the dwelling, the household and the applicant


@dataclass(eq=False)
class Dwelling(CatalaRecord):
    """The household's dwelling, Catala's ``Logement``."""

    main_residence: bool
    """Whether it is the household's main residence."""

    occupancy: Occupancy
    """How the household occupies it."""

    owner: RightHolder
    """Who owns it."""

    subletting: Subletting
    """Whether it is let or sublet to third parties."""

    usufructuary: RightHolder
    """Who holds its usufruct."""

    decent: bool
    """Whether it is decent, as article 6 of loi n° 89-462 asks."""

    surface_square_metres: int
    """Its surface."""

    zone: HousingZone
    """The geographic zone it is in."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``Logement``."""
        return {
            "résidence_principale": "main_residence",
            "mode_occupation": "occupancy",
            "propriétaire": "owner",
            "loué_ou_sous_loué_à_des_tiers": "subletting",
            "usufruit": "usufructuary",
            "logement_decent_l89_462": "decent",
            "surface_m_carrés": "surface_square_metres",
        }


@dataclass(eq=False)
class HousingHousehold(CatalaRecord):
    """The household applying for a housing aid, Catala's ``Ménage``."""

    benefits_received: list[BenefitReceived]
    """The family benefits it receives."""

    dwelling: Dwelling
    """Its dwelling."""

    dependants: list[Dependant]
    """The persons in its charge."""

    other_occupants: int
    """How many other persons live in the dwelling."""

    family_situation: FamilySituation
    """The applicant's family situation."""

    attached_to_wealth_taxed_parent: bool
    """Whether the applicant is attached to the tax household of a parent liable to the real estate wealth tax."""

    child_expected_after_fourth_month: bool
    """Whether a child is expected, the pregnancy past its fourth month."""

    elderly_or_disabled_r844_4: bool
    """Whether the household is of elderly or disabled persons, as article R844-4 asks."""

    residence: Territory
    """Where the household lives."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``Ménage``."""
        return {
            "prestations_reçues": "benefits_received",
            "logement": "dwelling",
            "personnes_à_charge": "dependants",
            "nombre_autres_occupants_logement": "other_occupants",
            "situation_familiale": "family_situation",
            "condition_rattaché_foyer_fiscal_parent_ifi": "attached_to_wealth_taxed_parent",
            "enfant_à_naître_après_quatrième_mois_grossesse": "child_expected_after_fourth_month",
            "personnes_âgées_handicapées_foyer_r844_4": "elderly_or_disabled_r844_4",
            "résidence": "residence",
        }

    @property
    def dependent_children(self) -> list[DependentChild]:
        """The children among the persons in the household's charge."""
        return [
            dependant.child
            for dependant in self.dependants
            if isinstance(dependant, ChildDependant)
        ]


@dataclass(eq=False)
class Applicant(CatalaRecord):
    """The person applying for the aid, Catala's ``Demandeur``."""

    birth_date: datetime.date
    """The day the applicant was born."""

    nationality: Nationality
    """The applicant's nationality."""

    hosted_in_care_unit: bool
    """Whether the applicant is hosted in a long-term care unit of article L162-22-3 of the Code de la sécurité sociale."""

    non_salaried_farmer: bool
    """Whether the applicant is a non-salaried farmer of articles L781-8 and L781-46 of the Code rural."""

    official_with_interests_outside_mayotte: bool
    """Whether the applicant is a magistrate or official whose material and family interests lie outside Mayotte."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of ``Demandeur``."""
        return {
            "date_naissance": "birth_date",
            "nationalité": "nationality",
            "personne_hébergée_centre_soin_l_L162_22_3_sécurité_sociale": "hosted_in_care_unit",
            "est_non_salarié_agricole_l781_8_l_781_46_code_rural": "non_salaried_farmer",
            "magistrat_fonctionnaire_centre_intérêts_matériels_familiaux_hors_mayotte": "official_with_interests_outside_mayotte",
        }
