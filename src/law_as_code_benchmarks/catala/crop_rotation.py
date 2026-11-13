"""
The crop rotation standard of the 2025 conditionality of the common agricultural policy
(*bonne condition agricole et environnementale* 7), its annual and multi-year criteria,
as Catala's ``asp/bcae7`` example states them from the 2025 technical sheet.
"""

from __future__ import annotations

import datetime
from abc import ABC
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from pathlib import Path

from krrood.entity_query_language.factories import (
    add,
    alternative,
    an,
    deduced_variable,
    entity,
    inference,
    not_,
    or_,
    variable,
)
from krrood.entity_query_language.factories import sum as total
from krrood.entity_query_language.predicate import symbolic_function
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty
from typing_extensions import Self

from law_as_code_benchmarks.law.period import Period
from law_as_code_benchmarks.catala.exceptions import UncategorisedCrop
from law_as_code_benchmarks.law.provision import ConclusionType
from law_as_code_benchmarks.catala.reader import (
    CatalaDirectory,
    CatalaValue,
    ConstructorWithContent,
    Reference,
    StructureLiteral,
)
from law_as_code_benchmarks.catala.scope_test import (
    CaseConclusion,
    CatalaRecord,
    ScopeCase,
    ScopeProvision,
    ScopeTestFile,
)

# %% crops


class CropCategory(StrEnum):
    """Annex 3: the categories of crops that count as different crops, each named as Catala's ``CulturesDifférentesRotationDiversification`` constructor."""

    SPRING_SOFT_WHEAT = "BléTendreDePrintemps"
    """Spring soft wheat."""

    WINTER_SOFT_WHEAT = "BléTendreDHiver"
    """Winter soft wheat."""

    SPRING_DURUM_WHEAT = "BléDurDePrintemps"
    """Spring durum wheat."""

    WINTER_DURUM_WHEAT = "BléDurDHiver"
    """Winter durum wheat."""

    SPRING_OATS = "AvoineDePrintemps"
    """Spring oats."""

    WINTER_OATS = "AvoineDHiver"
    """Winter oats."""

    SPELT = "Epeautre"
    """Spelt."""

    OTHER_SPRING_CEREALS_AND_MIXTURES = "AutresCéréalesEtMélangesDePrintemps"
    """Other spring cereals and mixtures."""

    MAIZE_AND_SEED_MAIZE = "MaïsEtMaïsSemence"
    """Maize and seed maize."""

    FOXTAIL_MILLET = "Moha"
    """Foxtail millet (*moha*)."""

    MILLET = "Millet"
    """Millet."""

    SPRING_TRITICALE = "TriticaleDePrintemps"
    """Spring triticale."""

    WINTER_TRITICALE = "TriticaleDHiver"
    """Winter triticale."""

    OTHER_WINTER_CEREALS_AND_MIXTURES = "AutresCéréalesEtMélangesDHiver"
    """Other winter cereals and mixtures."""

    SPRING_RAPESEED = "ColzaDePrintemps"
    """Spring rapeseed."""

    BUCKWHEAT = "Sarrasin"
    """Buckwheat."""

    WINTER_RAPESEED = "ColzaDHiver"
    """Winter rapeseed."""

    SUNFLOWER = "Tournesol"
    """Sunflower."""

    OPIUM_POPPY = "Œillette"
    """Opium poppy (*œillette*)."""

    OTHER_OILSEEDS = "AutresOléagineuxDHiverEtDePrintemps"
    """Other winter and spring oilseeds."""

    BROAD_AND_FIELD_BEANS = "FèveEtFéverole"
    """Broad beans and field beans."""

    LENTIL = "Lentille"
    """Lentil."""

    OTHER_FORAGE_LEGUMES = "AutresLégumineusesFourragèresYComprisEnMélange"
    """Other forage legumes, mixtures included."""

    ALFALFA = "Luzerne"
    """Alfalfa."""

    SPRING_LUPIN = "LupinDePrintemps"
    """Spring lupin."""

    WINTER_LUPIN = "LupinDHiver"
    """Winter lupin."""

    LEGUME_AND_CEREAL_MIXTURE = (
        "MélangeDeLégumineusesProtéagineuxPrépondérantsEtDeCéréalesOléagineux"
    )
    """Mixtures of mainly legumes or protein crops with cereals or oilseeds."""

    SPRING_FIELD_PEAS = "PoisProtéagineuxDePrintemps"
    """Spring field peas."""

    SORGHUM = "Sorgho"
    """Sorghum."""

    WINTER_FIELD_PEAS = "PoisProtéagineuxDHiver"
    """Winter field peas."""

    WINTER_BARLEY = "OrgeDHiver"
    """Winter barley."""

    SPRING_BARLEY = "OrgeDePrintemps"
    """Spring barley."""

    WINTER_RYE = "SeigleDHiver"
    """Winter rye."""

    SPRING_RYE = "SeigleDePrintemps"
    """Spring rye."""

    CHICKPEA = "PoisChiche"
    """Chickpea."""

    SOYBEAN = "Soja"
    """Soybean."""

    OTHER_PROTEIN_CROPS = "AutresProtéagineux"
    """Other protein crops."""

    MAINLY_GRASS = "HerbePrédominantePrairiesJachèresMélangesLégumineusesGraminées"
    """Mainly grass: grassland, fallow land, legume and grass mixtures."""

    OTHER_FORAGE = "AutresFourrages"
    """Other forage."""

    TOBACCO = "Tabac"
    """Tobacco."""

    POTATO = "PommeDeTerre"
    """Potato."""

    FIBRE_FLAX = "LinFibres"
    """Fibre flax."""

    SPRING_LINSEED = "LinDePrintemps"
    """Spring linseed."""

    WINTER_LINSEED = "LinDHiver"
    """Winter linseed."""

    BEETS = "Betteraves"
    """Beets."""

    HEMP = "Chanvre"
    """Hemp."""

    FRUITS_VEGETABLES_AND_FLOWERS = "FruitsLégumesFleurs"
    """Fruits, vegetables and flowers, which annex 4 splits by crop code."""

    MUSTARD = "Moutarde"
    """Mustard."""

    AROMATIC_HERBS = "PlantesAromatiquesHerbacéesNonPérennesHorsPersil"
    """Non-perennial herbaceous aromatic plants but parsley."""

    MEDICINAL_AND_PERFUME_PLANTS = "PlantesMédicinalesEtÀParfumNonPérennes"
    """Non-perennial medicinal and perfume plants."""

    PARSLEY = "Persil"
    """Parsley."""

    ORNAMENTAL_HORTICULTURE = "HorticultureOrnementale"
    """Ornamental horticulture."""

    INTERROW_CROPS = "CulturesAssociéesDéclaréesAvecLeCodeCIDCIT"
    """Crops grown together, declared with the code CID or CIT."""

    RICE = "Riz"
    """Rice."""

    GARLIC = "Ail"
    """Garlic."""

    PINEAPPLE = "Ananas"
    """Pineapple."""

    ARTICHOKE = "Artichaut"
    """Artichoke."""

    CUCUMBER_GHERKIN_AND_COURGETTE = "ConcombreCornichonEtCourgette"
    """Cucumber, gherkin and courgette."""

    CELERY = "Céleri"
    """Celery."""

    CABBAGE = "Chou"
    """Cabbage."""

    SPINACH_SORREL_AND_CHARD = "EpinardOseilleEtBette"
    """Spinach, sorrel and chard."""

    OTHER_ANNUAL_VEGETABLE_OR_FRUIT = "AutreLégumeOuFruitAnnuel"
    """Another annual vegetable or fruit."""

    OPEN_FIELD_STRAWBERRY = "FraiseEnPleineTerre"
    """Open-field strawberry."""

    LETTUCE_ENDIVE_AND_OTHER_SALADS = "LaitueEndiveEtAutresSalades"
    """Lettuce, endive and other salads."""

    MIXED_MARKET_GARDENING = "MaraîchageDiversifié"
    """Mixed market gardening."""

    TURNIP_SWEDE_AND_OTHER_ROOT_VEGETABLES = (
        "NavetRutabagaEtAutresLégumesRacinesHorsCarotteRadisBetterave"
    )
    """Turnip, swede and other root vegetables but carrot, radish and beet."""

    ONION_AND_SHALLOT = "OignonEtÉchalote"
    """Onion and shallot."""

    LEEK = "Poireau"
    """Leek."""

    PUMPKIN_AND_OTHER_SQUASHES = "PotironCitrouilleEtAutresCourges"
    """Pumpkin and other squashes."""

    PEPPER_CHILLI_AND_AUBERGINE = "PoivronPimentEtAubergine"
    """Sweet pepper, chilli and aubergine."""

    RADISH = "Radis"
    """Radish."""

    TROPICAL_TUBER = "TuberculeTropical"
    """Tropical tuber."""

    OPEN_FIELD_TOMATOES = "TomatesEnPleineTerre"
    """Open-field tomatoes."""

    MELON_AND_WATERMELON = "MelonEtPastèque"
    """Melon and watermelon."""


class CropCode(StrEnum):
    """The crop codes of the common agricultural policy's declaration of land, each named by its code."""

    AAR = "AAR"
    """Annex 4: non-perennial herbaceous aromatic plants but parsley."""

    ACP = "ACP"
    """In no category of annex 4."""

    AFG = "AFG"
    """Annex 4: other forage."""

    AIL = "AIL"
    """Annex 4: garlic."""

    ANA = "ANA"
    """Annex 4: pineapple."""

    AME = "AME"
    """Annex 4: non-perennial medicinal and perfume plants."""

    ARA = "ARA"
    """Annex 4: other protein crops."""

    ARP = "ARP"
    """In no category of annex 4."""

    ART = "ART"
    """Annex 4: artichoke."""

    AVH = "AVH"
    """Annex 4: winter oats."""

    AVP = "AVP"
    """Annex 4: spring oats."""

    BDH = "BDH"
    """Annex 4: winter durum wheat."""

    BDP = "BDP"
    """Annex 4: spring durum wheat."""

    BTH = "BTH"
    """Annex 4: winter soft wheat."""

    BTP = "BTP"
    """Annex 4: spring soft wheat."""

    BTN = "BTN"
    """Annex 4: beets."""

    CAE = "CAE"
    """In no category of annex 4."""

    CAG = "CAG"
    """Annex 4: other spring cereals and mixtures."""

    CAH = "CAH"
    """Annex 4: other winter cereals and mixtures."""

    CAR = "CAR"
    """In no category of annex 4."""

    CEE = "CEE"
    """In no category of annex 4."""

    CEL = "CEL"
    """Annex 4: celery."""

    CID = "CID"
    """Annex 4: crops grown together, declared with the code CID or CIT."""

    CIT = "CIT"
    """Annex 4: crops grown together, declared with the code CID or CIT."""

    CHU = "CHU"
    """Annex 4: cabbage."""

    CHV = "CHV"
    """Annex 4: hemp."""

    CCN = "CCN"
    """Annex 4: cucumber, gherkin and courgette."""

    CML = "CML"
    """Annex 4: other winter and spring oilseeds."""

    CPL = "CPL"
    """Annex 4: other forage."""

    CSA = "CSA"
    """In no category of annex 4."""

    CZH = "CZH"
    """Annex 4: winter rapeseed."""

    CZP = "CZP"
    """Annex 4: spring rapeseed."""

    EPE = "EPE"
    """Annex 4: spelt."""

    EPI = "EPI"
    """Annex 4: spinach, sorrel and chard."""

    FEV = "FEV"
    """Annex 4: broad beans and field beans."""

    FLA = "FLA"
    """Annex 4: another annual vegetable or fruit."""

    FLP = "FLP"
    """In no category of annex 4."""

    FNU = "FNU"
    """Annex 4: other protein crops."""

    FRA = "FRA"
    """Annex 4: open-field strawberry."""

    FVL = "FVL"
    """Annex 4: broad beans and field beans."""

    FVP = "FVP"
    """Annex 4: broad beans and field beans."""

    GES = "GES"
    """Annex 4: other protein crops."""

    GRA = "GRA"
    """Annex 4: mainly grass: grassland, fallow land, legume and grass mixtures."""

    JAC = "JAC"
    """Annex 4: mainly grass: grassland, fallow land, legume and grass mixtures."""

    HBL = "HBL"
    """In no category of annex 4."""

    HPC = "HPC"
    """Annex 4: ornamental horticulture."""

    LAV = "LAV"
    """In no category of annex 4."""

    LBF = "LBF"
    """Annex 4: lettuce, endive and other salads."""

    LDH = "LDH"
    """Annex 4: winter lupin."""

    LDP = "LDP"
    """Annex 4: spring lupin."""

    LEC = "LEC"
    """Annex 4: lentil."""

    LIF = "LIF"
    """Annex 4: fibre flax."""

    LIH = "LIH"
    """Annex 4: winter linseed."""

    LIP = "LIP"
    """Annex 4: spring linseed."""

    LOT = "LOT"
    """Annex 4: other forage legumes, mixtures included."""

    LUZ = "LUZ"
    """Annex 4: alfalfa."""

    MCR = "MCR"
    """Annex 4: other winter cereals and mixtures."""

    MCS = "MCS"
    """Annex 4: other spring cereals and mixtures."""

    MDI = "MDI"
    """Annex 4: mixed market gardening."""

    MID = "MID"
    """Annex 4: maize and seed maize."""

    MIS = "MIS"
    """Annex 4: maize and seed maize."""

    MLC = "MLC"
    """Annex 4: mixtures of mainly legumes or protein crops with cereals or oilseeds."""

    MLO = "MLO"
    """Annex 4: melon and watermelon."""

    MLF = "MLF"
    """Annex 4: other forage legumes, mixtures included."""

    MLG = "MLG"
    """Annex 4: mainly grass: grassland, fallow land, legume and grass mixtures."""

    MLT = "MLT"
    """Annex 4: millet."""

    MOH = "MOH"
    """Annex 4: foxtail millet (*moha*)."""

    MOT = "MOT"
    """Annex 4: mustard."""

    MPC = "MPC"
    """Annex 4: mixtures of mainly legumes or protein crops with cereals or oilseeds."""

    MSW = "MSW"
    """In no category of annex 4."""

    NVT = "NVT"
    """Annex 4: turnip, swede and other root vegetables but carrot, radish and beet."""

    OAG = "OAG"
    """Annex 4: other winter and spring oilseeds."""

    OEI = "OEI"
    """Annex 4: opium poppy (*œillette*)."""

    OIG = "OIG"
    """Annex 4: onion and shallot."""

    OHR = "OHR"
    """Annex 4: other winter and spring oilseeds."""

    ORH = "ORH"
    """Annex 4: winter barley."""

    ORP = "ORP"
    """Annex 4: spring barley."""

    PAG = "PAG"
    """Annex 4: other protein crops."""

    PCH = "PCH"
    """Annex 4: chickpea."""

    PEV = "PEV"
    """In no category of annex 4."""

    PHI = "PHI"
    """Annex 4: winter field peas."""

    PHF = "PHF"
    """Annex 4: other protein crops."""

    PHS = "PHS"
    """Annex 4: other protein crops."""

    PME = "PME"
    """In no category of annex 4."""

    POR = "POR"
    """Annex 4: leek."""

    POT = "POT"
    """Annex 4: pumpkin and other squashes."""

    PPH = "PPH"
    """In no category of annex 4."""

    PPR = "PPR"
    """Annex 4: spring field peas."""

    PRF = "PRF"
    """In no category of annex 4."""

    PSL = "PSL"
    """Annex 4: parsley."""

    PTC = "PTC"
    """Annex 4: potato."""

    PTR = "PTR"
    """Annex 4: mainly grass: grassland, fallow land, legume and grass mixtures."""

    PVP = "PVP"
    """Annex 4: sweet pepper, chilli and aubergine."""

    RDI = "RDI"
    """Annex 4: radish."""

    RIZ = "RIZ"
    """Annex 4: rice."""

    SAI = "SAI"
    """Annex 4: other forage legumes, mixtures included."""

    SGH = "SGH"
    """Annex 4: winter rye."""

    SGP = "SGP"
    """Annex 4: spring rye."""

    SNE = "SNE"
    """In no category of annex 4."""

    SOG = "SOG"
    """Annex 4: sorghum."""

    SOJ = "SOJ"
    """Annex 4: soybean."""

    SPH = "SPH"
    """In no category of annex 4."""

    SPL = "SPL"
    """In no category of annex 4."""

    SRS = "SRS"
    """Annex 4: buckwheat."""

    TAB = "TAB"
    """Annex 4: tobacco."""

    TBT = "TBT"
    """Annex 4: tropical tuber."""

    TRN = "TRN"
    """Annex 4: sunflower."""

    TOM = "TOM"
    """Annex 4: open-field tomatoes."""

    TTH = "TTH"
    """Annex 4: winter triticale."""

    TTP = "TTP"
    """Annex 4: spring triticale."""

    TRE = "TRE"
    """Annex 4: other forage legumes, mixtures included."""

    VES = "VES"
    """Annex 4: other forage legumes, mixtures included."""

    @property
    def category(self) -> CropCategory:
        """
        Annex 4: the category of annex 3 the crop is in.

        :raises UncategorisedCrop: Where annex 4 puts the crop in none.
        """
        if self not in self.categories:
            raise UncategorisedCrop(code=self.value)
        return self.categories[self]

    @property
    def is_excluded_from_rotation(self) -> bool:
        """
        Annex 1: whether the crop is perennial, grassland, fallow land or grown under
        water, which takes its parcel out of the annual criterion.
        """
        return self in {
            CropCode.LOT,
            CropCode.LDH,
            CropCode.LDP,
            CropCode.LUZ,
            CropCode.VES,
            CropCode.SAI,
            CropCode.TRE,
            CropCode.BTN,
            CropCode.CSA,
            CropCode.HBL,
            CropCode.ART,
            CropCode.CEL,
            CropCode.FRA,
            CropCode.AME,
            CropCode.AAR,
            CropCode.PSL,
            CropCode.HPC,
            CropCode.MLG,
            CropCode.PTR,
            CropCode.JAC,
            CropCode.RIZ,
        }

    @classproperty
    def categories(cls) -> dict[CropCode, CropCategory]:
        """Annex 4: the category of each crop annex 4 lists."""
        return {
            CropCode.LOT: CropCategory.OTHER_FORAGE_LEGUMES,
            CropCode.MLF: CropCategory.OTHER_FORAGE_LEGUMES,
            CropCode.SAI: CropCategory.OTHER_FORAGE_LEGUMES,
            CropCode.TRE: CropCategory.OTHER_FORAGE_LEGUMES,
            CropCode.VES: CropCategory.OTHER_FORAGE_LEGUMES,
            CropCode.CAG: CropCategory.OTHER_SPRING_CEREALS_AND_MIXTURES,
            CropCode.MCS: CropCategory.OTHER_SPRING_CEREALS_AND_MIXTURES,
            CropCode.CAH: CropCategory.OTHER_WINTER_CEREALS_AND_MIXTURES,
            CropCode.MCR: CropCategory.OTHER_WINTER_CEREALS_AND_MIXTURES,
            CropCode.AFG: CropCategory.OTHER_FORAGE,
            CropCode.CPL: CropCategory.OTHER_FORAGE,
            CropCode.OAG: CropCategory.OTHER_OILSEEDS,
            CropCode.OHR: CropCategory.OTHER_OILSEEDS,
            CropCode.CML: CropCategory.OTHER_OILSEEDS,
            CropCode.ARA: CropCategory.OTHER_PROTEIN_CROPS,
            CropCode.PAG: CropCategory.OTHER_PROTEIN_CROPS,
            CropCode.GES: CropCategory.OTHER_PROTEIN_CROPS,
            CropCode.FNU: CropCategory.OTHER_PROTEIN_CROPS,
            CropCode.PHF: CropCategory.OTHER_PROTEIN_CROPS,
            CropCode.PHS: CropCategory.OTHER_PROTEIN_CROPS,
            CropCode.AVH: CropCategory.WINTER_OATS,
            CropCode.AVP: CropCategory.SPRING_OATS,
            CropCode.BTN: CropCategory.BEETS,
            CropCode.BDH: CropCategory.WINTER_DURUM_WHEAT,
            CropCode.BDP: CropCategory.SPRING_DURUM_WHEAT,
            CropCode.BTH: CropCategory.WINTER_SOFT_WHEAT,
            CropCode.BTP: CropCategory.SPRING_SOFT_WHEAT,
            CropCode.CHV: CropCategory.HEMP,
            CropCode.CZH: CropCategory.WINTER_RAPESEED,
            CropCode.CZP: CropCategory.SPRING_RAPESEED,
            CropCode.CIT: CropCategory.INTERROW_CROPS,
            CropCode.CID: CropCategory.INTERROW_CROPS,
            CropCode.EPE: CropCategory.SPELT,
            CropCode.FEV: CropCategory.BROAD_AND_FIELD_BEANS,
            CropCode.FVP: CropCategory.BROAD_AND_FIELD_BEANS,
            CropCode.FVL: CropCategory.BROAD_AND_FIELD_BEANS,
            CropCode.AIL: CropCategory.GARLIC,
            CropCode.ANA: CropCategory.PINEAPPLE,
            CropCode.ART: CropCategory.ARTICHOKE,
            CropCode.CCN: CropCategory.CUCUMBER_GHERKIN_AND_COURGETTE,
            CropCode.CEL: CropCategory.CELERY,
            CropCode.CHU: CropCategory.CABBAGE,
            CropCode.EPI: CropCategory.SPINACH_SORREL_AND_CHARD,
            CropCode.FLA: CropCategory.OTHER_ANNUAL_VEGETABLE_OR_FRUIT,
            CropCode.FRA: CropCategory.OPEN_FIELD_STRAWBERRY,
            CropCode.LBF: CropCategory.LETTUCE_ENDIVE_AND_OTHER_SALADS,
            CropCode.MDI: CropCategory.MIXED_MARKET_GARDENING,
            CropCode.MLO: CropCategory.MELON_AND_WATERMELON,
            CropCode.NVT: CropCategory.TURNIP_SWEDE_AND_OTHER_ROOT_VEGETABLES,
            CropCode.OIG: CropCategory.ONION_AND_SHALLOT,
            CropCode.POR: CropCategory.LEEK,
            CropCode.POT: CropCategory.PUMPKIN_AND_OTHER_SQUASHES,
            CropCode.PVP: CropCategory.PEPPER_CHILLI_AND_AUBERGINE,
            CropCode.RDI: CropCategory.RADISH,
            CropCode.TBT: CropCategory.TROPICAL_TUBER,
            CropCode.TOM: CropCategory.OPEN_FIELD_TOMATOES,
            CropCode.JAC: CropCategory.MAINLY_GRASS,
            CropCode.MLG: CropCategory.MAINLY_GRASS,
            CropCode.PTR: CropCategory.MAINLY_GRASS,
            CropCode.GRA: CropCategory.MAINLY_GRASS,
            CropCode.MLC: CropCategory.LEGUME_AND_CEREAL_MIXTURE,
            CropCode.MPC: CropCategory.LEGUME_AND_CEREAL_MIXTURE,
            CropCode.LEC: CropCategory.LENTIL,
            CropCode.LIH: CropCategory.WINTER_LINSEED,
            CropCode.LIP: CropCategory.SPRING_LINSEED,
            CropCode.LIF: CropCategory.FIBRE_FLAX,
            CropCode.LDH: CropCategory.WINTER_LUPIN,
            CropCode.LDP: CropCategory.SPRING_LUPIN,
            CropCode.LUZ: CropCategory.ALFALFA,
            CropCode.MID: CropCategory.MAIZE_AND_SEED_MAIZE,
            CropCode.MIS: CropCategory.MAIZE_AND_SEED_MAIZE,
            CropCode.MLT: CropCategory.MILLET,
            CropCode.MOH: CropCategory.FOXTAIL_MILLET,
            CropCode.MOT: CropCategory.MUSTARD,
            CropCode.OEI: CropCategory.OPIUM_POPPY,
            CropCode.ORP: CropCategory.SPRING_BARLEY,
            CropCode.ORH: CropCategory.WINTER_BARLEY,
            CropCode.AAR: CropCategory.AROMATIC_HERBS,
            CropCode.AME: CropCategory.MEDICINAL_AND_PERFUME_PLANTS,
            CropCode.PSL: CropCategory.PARSLEY,
            CropCode.HPC: CropCategory.ORNAMENTAL_HORTICULTURE,
            CropCode.PCH: CropCategory.CHICKPEA,
            CropCode.PHI: CropCategory.WINTER_FIELD_PEAS,
            CropCode.PPR: CropCategory.SPRING_FIELD_PEAS,
            CropCode.PTC: CropCategory.POTATO,
            CropCode.RIZ: CropCategory.RICE,
            CropCode.SRS: CropCategory.BUCKWHEAT,
            CropCode.SGP: CropCategory.SPRING_RYE,
            CropCode.SGH: CropCategory.WINTER_RYE,
            CropCode.SOJ: CropCategory.SOYBEAN,
            CropCode.SOG: CropCategory.SORGHUM,
            CropCode.TAB: CropCategory.TOBACCO,
            CropCode.TRN: CropCategory.SUNFLOWER,
            CropCode.TTH: CropCategory.WINTER_TRITICALE,
            CropCode.TTP: CropCategory.SPRING_TRITICALE,
        }


class CropQualification(StrEnum):
    """Whether a crop is a parcel's main crop of the season, each named as Catala's ``QualificationCulture`` constructor."""

    PRINCIPAL = "Principale"
    """The main crop."""

    SECONDARY = "Secondaire"
    """A secondary crop, such as a cover crop sown after the main one."""


@dataclass
class Crop(CatalaRecord):
    """A crop grown on a parcel for a period, Catala's ``Culture``."""

    code: CropCode
    """The crop."""

    period: Period
    """The days it is grown, both included."""

    qualification: CropQualification
    """Whether it is the main crop or a secondary one."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """Catala's ``période``."""
        return {"période": "period"}

    @classmethod
    def from_catala(cls, values: dict[str, CatalaValue]) -> Self:
        """Extends :meth:`CatalaRecord.from_catala` with Catala's ``Période``, whose ``début`` and ``fin`` are both included."""
        period: StructureLiteral = values["période"]
        return super().from_catala(
            values
            | {
                "période": Period(
                    first_day=period.fields["début"], last_day=period.fields["fin"]
                )
            }
        )


class ParcelSystem(StrEnum):
    """How a parcel is farmed, each named as Catala's ``SystèmeParcelle`` constructor."""

    SPRING_MONOCULTURE = "MonoculturePrintemps"
    """A spring crop grown year after year."""

    WINTER_MONOCULTURE = "MonocultureHiver"
    """A winter crop grown year after year."""

    OTHER = "Autre"
    """Any other system."""


@dataclass(frozen=True)
class RotationCalendar:
    """The days the criteria of the 2025 campaign look at."""

    campaign: Period = Period(datetime.date(2025, 1, 1), datetime.date(2025, 12, 31))
    """The year assessed by the annual criterion."""

    principal_crop_window: Period = Period(
        datetime.date(2025, 3, 1), datetime.date(2025, 7, 15)
    )
    """The days a main crop of the campaign must be grown on some of."""

    secondary_crop_deadline: datetime.date = datetime.date(2025, 11, 15)
    """The day a secondary crop of the campaign must be sown by."""

    multi_year_period: Period = Period(
        datetime.date(2022, 1, 1), datetime.date(2025, 12, 31)
    )
    """The four years the multi-year criterion looks back on."""

    secondary_crop_years: tuple[int, ...] = (2023, 2024, 2025)
    """The years that must each have a secondary crop by 15 November, 2022 left out."""


@dataclass
class Parcel(CatalaRecord):
    """A parcel of arable land and the crops grown on it, Catala's ``ParcelleTerreArable``."""

    area_hectares: Fraction
    """The parcel's area."""

    crops: list[Crop]
    """The crops grown on it, in chronological order."""

    system: ParcelSystem
    """How it is farmed."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of Catala's ``ParcelleTerreArable``."""
        return {
            "surface_hectares": "area_hectares",
            "cultures": "crops",
            "système": "system",
        }

    def crop_on(self, day: datetime.date) -> Crop | None:
        """:return: The first crop grown on *day*; None where none is."""
        return next((crop for crop in self.crops if crop.period.contains(day)), None)

    def crops_grown_during(self, period: Period) -> list[Crop]:
        """:return: The crops grown on a day of *period* at least."""
        return [crop for crop in self.crops if crop.period.overlaps(period)]

    @staticmethod
    @symbolic_function
    def grows_crop_excluded_from_rotation(parcel: Parcel, period: Period) -> bool:
        """:return: Whether a crop of annex 1 is grown on *parcel* during *period*."""
        return any(
            crop.code.is_excluded_from_rotation
            for crop in parcel.crops_grown_during(period)
        )

    @staticmethod
    @symbolic_function
    def meets_annual_criterion(parcel: Parcel, calendar: RotationCalendar) -> bool:
        """
        :return: Whether every crop of the campaign on *parcel* is in place, a main crop
            during the window and a secondary one by the deadline, and one at least is
            of another category than the crop before it.
        """
        previous: Crop | None = None
        in_place = True
        rotated = False
        for crop in parcel.crops:
            if (
                crop.period.first_day < calendar.campaign.last_day
                and crop.period.last_day > calendar.campaign.first_day
            ):
                match crop.qualification:
                    case CropQualification.SECONDARY:
                        in_place &= (
                            crop.period.first_day <= calendar.secondary_crop_deadline
                        )
                    case CropQualification.PRINCIPAL:
                        in_place &= crop.period.overlaps(calendar.principal_crop_window)
                rotated |= previous is None or (
                    previous.code.category != crop.code.category
                )
            previous = crop
        return in_place and rotated

    @staticmethod
    @symbolic_function
    def grows_two_main_crops(parcel: Parcel, calendar: RotationCalendar) -> bool:
        """
        :return: Whether a crop grown during the multi-year period is of another category
            than the main crop before it, as Catala compares secondary crops too.
        """
        previous_main: Crop | None = None
        rotated = False
        for crop in parcel.crops_grown_during(calendar.multi_year_period):
            rotated |= previous_main is not None and (
                previous_main.code.category != crop.code.category
            )
            if crop.qualification == CropQualification.PRINCIPAL:
                previous_main = crop
        return rotated

    @staticmethod
    @symbolic_function
    def grows_secondary_crop_every_year(
        parcel: Parcel, calendar: RotationCalendar
    ) -> bool:
        """
        :return: Whether, for each year of the multi-year criterion, a secondary crop of
            *parcel* was sown by 15 November of that year, as Catala reads it with no
            first day.
        """
        return all(
            any(
                crop.qualification == CropQualification.SECONDARY
                and crop.period.first_day <= datetime.date(year, 11, 15)
                for crop in parcel.crops
            )
            for year in calendar.secondary_crop_years
        )

    @staticmethod
    @symbolic_function
    def grows_crop_exempt_from_multi_year_criterion(
        parcel: Parcel, calendar: RotationCalendar
    ) -> bool:
        """
        :return: Whether a crop grown on *parcel* during the multi-year period is
            mixed vegetables under cover (*SNE*), seed maize, or one grown for a year
            at least.
        """
        return any(
            crop.code in {CropCode.SNE, CropCode.MIS}
            or (crop.period.last_day - crop.period.first_day).days >= 365
            for crop in parcel.crops_grown_during(calendar.multi_year_period)
        )

    @staticmethod
    @symbolic_function
    def keeps_winter_cover(parcel: Parcel, calendar: RotationCalendar) -> bool:
        """
        :return: Whether, each year of the multi-year criterion, the crop grown on
            *parcel* on 15 November is a secondary crop still grown on 15 February.
        """
        for year in calendar.secondary_crop_years:
            autumn_crop = parcel.crop_on(datetime.date(year, 11, 15))
            if autumn_crop is None:
                return False
            if autumn_crop.qualification != CropQualification.SECONDARY:
                return False
            if parcel.crop_on(datetime.date(year + 1, 2, 15)) != autumn_crop:
                return False
        return True


# %% the farm


class OrganicFarming(StrEnum):
    """Whether the farm is organic, each named as Catala's ``AgricultureBiologique`` constructor."""

    CERTIFIED = "CertificationObtenue"
    """Certified organic."""

    IN_CONVERSION = "EnCoursDeConversion"
    """Converting to organic farming."""

    CONVENTIONAL = "Conventionnelle"
    """Not organic."""


class ComplianceMode(StrEnum):
    """How a farm outside the Rhine plain meets the standard, each named as Catala's ``ModeRespectBCAE7`` constructor."""

    CROP_ROTATION = "RotationDesCultures"
    """By rotating its crops."""

    CROP_DIVERSIFICATION = "DiversificationDesCultures"
    """By diversifying its crops."""


class CropRotationOutput(StrEnum):
    """The outputs of Catala's ``ConditionnalitéBCAE7Pour2025`` scope the model answers."""

    ANNUAL_CRITERION = "rotation_cultures_critère_annuel"
    """Whether the annual criterion is respected, and by how much it is missed."""

    MULTI_YEAR_CRITERION = "rotation_cultures_critère_pluriannuel"
    """Whether the multi-year criterion is respected, and by how much it is missed."""


@dataclass(eq=False)
class FarmCase(ScopeCase):
    """A farm's arable land in the 2025 campaign, Catala's ``ConditionnalitéBCAE7Pour2025`` scope."""

    organic_farming: OrganicFarming
    """Whether the farm is organic."""

    parcels: list[Parcel]
    """Its parcels of arable land."""

    in_rhine_plain: bool
    """Whether the farm lies in the Rhine plain of Alsace."""

    compliance_mode: ComplianceMode
    """How the farm meets the standard outside the Rhine plain."""

    calendar: RotationCalendar = field(default_factory=RotationCalendar)
    """The days the criteria look at."""

    @classproperty
    def catala_scope(cls) -> str:
        """``ConditionnalitéBCAE7Pour2025``."""
        return "ConditionnalitéBCAE7Pour2025"

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The inputs of Catala's ``ConditionnalitéBCAE7Pour2025`` scope."""
        return {
            "agriculture_biologique": "organic_farming",
            "terres_arables": "parcels",
            "est_située_dans_la_plaine_du_Rhin": "in_rhine_plain",
            "choix_critère_hors_plaine_du_Rhin": "compliance_mode",
        }

    @classproperty
    def catala_outputs(cls) -> type[StrEnum]:
        """:class:`CropRotationOutput`."""
        return CropRotationOutput

    def output(self, variable: str) -> CatalaValue:
        match CropRotationOutput(variable):
            case CropRotationOutput.ANNUAL_CRITERION:
                criterion = self.sole_conclusion(AnnualCriterionProvision)
            case CropRotationOutput.MULTI_YEAR_CRITERION:
                criterion = self.sole_conclusion(MultiYearCriterionProvision)
        return None if criterion is None else criterion.to_catala()


# %% conclusions


@dataclass(eq=False)
class ParcelConclusion(CaseConclusion):
    """A conclusion about one parcel of a farm."""

    parcel: Parcel | None = None
    """The parcel."""


@dataclass(eq=False)
class CultivatedParcel(ParcelConclusion):
    """The parcel is cultivated arable land: no crop of annex 1 is grown on it in the campaign."""


@dataclass(eq=False)
class ParcelCondition(ParcelConclusion):
    """Whether a condition holds for one parcel, false where no rule says it does."""

    holds: bool = False
    """Whether the condition holds."""


@dataclass(eq=False)
class AnnualCriterionOfParcel(ParcelCondition):
    """The cultivated parcel meets the annual criterion."""


@dataclass(eq=False)
class MultiYearCriterionOfParcel(ParcelCondition):
    """The cultivated parcel meets the multi-year criterion, monoculture aside."""


@dataclass(eq=False)
class MonocultureCriterionOfParcel(ParcelCondition):
    """The cultivated parcel meets the multi-year criterion, with that of its monoculture system."""


@dataclass(eq=False)
class FarmArea(CaseConclusion):
    """An area of the farm's arable land."""

    hectares: Fraction = Fraction(0)
    """The area."""


@dataclass(eq=False)
class CultivatedArea(FarmArea):
    """The area of the cultivated arable land."""


@dataclass(eq=False)
class AreaMeetingAnnualCriterion(FarmArea):
    """The area of the cultivated parcels that meet the annual criterion."""


@dataclass(eq=False)
class AreaMissingMultiYearCriterion(FarmArea):
    """The area of the cultivated parcels that miss the multi-year criterion."""


@dataclass(eq=False)
class RotationCriterion(CaseConclusion):
    """Whether a criterion of the standard is respected, and by how much it is missed, Catala's ``RespectCritère``."""

    shortfall_proportion: Fraction | None = None
    """The share of the cultivated arable land the criterion is missed by; None where it is respected."""

    shortfall_hectares: Fraction | None = None
    """The area the criterion is missed by; None where it is respected."""

    def to_catala(self) -> CatalaValue:
        """:return: Catala's ``Respecté``, or ``NonRespecté`` with its ``ÉcartRespect``."""
        if self.shortfall_proportion is None:
            return Reference(parts=("Respecté",))
        return ConstructorWithContent(
            constructor=Reference(parts=("NonRespecté",)),
            content=StructureLiteral(
                structure=Reference(parts=("ÉcartRespect",)),
                fields={
                    "proportion": self.shortfall_proportion,
                    "surface_hectares": self.shortfall_hectares,
                },
            ),
        )


@dataclass(eq=False)
class AnnualCriterion(RotationCriterion):
    """The annual criterion of the farm."""


@dataclass(eq=False)
class MultiYearCriterion(RotationCriterion):
    """The multi-year criterion of the farm."""


# %% provisions


@dataclass
class CultivatedParcelProvision(ScopeProvision[CultivatedParcel]):
    """
    The cultivated arable land: the parcels on which no crop of annex 1, perennial,
    grassland, fallow land or rice, is grown in the campaign.
    """

    def query(self) -> Query:
        case = variable(FarmCase, domain=[self.case])
        parcel = variable(Parcel, domain=self.case.parcels)
        return an(
            entity(inference(CultivatedParcel)(case=case, parcel=parcel)).where(
                not_(
                    Parcel.grows_crop_excluded_from_rotation(
                        parcel, case.calendar.campaign
                    )
                )
            )
        )


@dataclass
class CultivatedAreaProvision(ScopeProvision[CultivatedArea]):
    """The area of the cultivated arable land, the sum of its parcels' areas."""

    def query(self) -> Query:
        cultivated = variable(
            CultivatedParcel,
            domain=CultivatedParcelProvision(case=self.case).conclusions,
        )
        hectares = an(
            entity(total(cultivated.parcel.area_hectares, default=Fraction(0)))
        ).first()
        case = variable(FarmCase, domain=[self.case])
        return an(entity(inference(CultivatedArea)(case=case, hectares=hectares)))


@dataclass
class CultivatedParcelCriterionProvision(ScopeProvision[ConclusionType], ABC):
    """A provision concluding whether each cultivated parcel meets a criterion."""

    @property
    def conclusions(self) -> list[ConclusionType]:
        """Extends :meth:`Provision.conclusions`: none where no parcel is cultivated."""
        # krrood raises on an else-if chain over an empty domain:
        # https://github.com/cram2/cognitive_robot_abstract_machine/issues/952
        if not CultivatedParcelProvision(case=self.case).conclusions:
            return []
        return super().conclusions


@dataclass
class AnnualCriterionOfParcelProvision(
    CultivatedParcelCriterionProvision[AnnualCriterionOfParcel]
):
    """
    The annual criterion of a cultivated parcel: every crop of the campaign in place,
    a main crop for some days of 1 March to 15 July and a secondary one sown by 15
    November, and one at least of another category than the crop before it.
    """

    def query(self) -> Query:
        case = variable(FarmCase, domain=[self.case])
        cultivated = variable(
            CultivatedParcel,
            domain=CultivatedParcelProvision(case=self.case).conclusions,
        )
        criterion = deduced_variable(AnnualCriterionOfParcel)
        query = an(
            entity(criterion).where(
                Parcel.meets_annual_criterion(cultivated.parcel, case.calendar)
            )
        )
        with query:
            add(
                criterion,
                inference(AnnualCriterionOfParcel)(
                    case=case, parcel=cultivated.parcel, holds=True
                ),
            )
            with alternative():
                add(
                    criterion,
                    inference(AnnualCriterionOfParcel)(
                        case=case, parcel=cultivated.parcel, holds=False
                    ),
                )
        return query


@dataclass
class AreaMeetingAnnualCriterionProvision(ScopeProvision[AreaMeetingAnnualCriterion]):
    """The area of the cultivated parcels that meet the annual criterion."""

    def query(self) -> Query:
        criterion = variable(
            AnnualCriterionOfParcel,
            domain=AnnualCriterionOfParcelProvision(case=self.case).conclusions,
        )
        hectares = an(
            entity(total(criterion.parcel.area_hectares, default=Fraction(0))).where(
                criterion.holds == True
            )
        ).first()
        case = variable(FarmCase, domain=[self.case])
        return an(
            entity(inference(AreaMeetingAnnualCriterion)(case=case, hectares=hectares))
        )


@dataclass
class AnnualCriterionProvision(ScopeProvision[AnnualCriterion]):
    """
    The annual criterion: respected where 35 % of the cultivated arable land at least
    meets it, or where there is none; missed otherwise by the share and area short of
    35 %.
    """

    @classproperty
    def required_share(cls) -> Fraction:
        """The share of the cultivated arable land that must meet the annual criterion."""
        return Fraction(35, 100)

    def query(self) -> Query:
        case = variable(FarmCase, domain=[self.case])
        cultivated = variable(
            CultivatedArea, domain=CultivatedAreaProvision(case=self.case).conclusions
        )
        meeting = variable(
            AreaMeetingAnnualCriterion,
            domain=AreaMeetingAnnualCriterionProvision(case=self.case).conclusions,
        )
        criterion = deduced_variable(AnnualCriterion)
        query = an(
            entity(criterion).where(
                or_(
                    cultivated.hectares == 0,
                    meeting.hectares >= cultivated.hectares * self.required_share,
                )
            )
        )
        with query:
            add(criterion, inference(AnnualCriterion)(case=case))
            with alternative():
                add(
                    criterion,
                    inference(AnnualCriterion)(
                        case=case,
                        shortfall_proportion=self.required_share
                        - meeting.hectares / cultivated.hectares,
                        shortfall_hectares=cultivated.hectares * self.required_share
                        - meeting.hectares,
                    ),
                )
        return query


@dataclass
class MultiYearCriterionOfParcelProvision(
    CultivatedParcelCriterionProvision[MultiYearCriterionOfParcel]
):
    """
    The multi-year criterion of a cultivated parcel: two different main crops in the
    four years, or a secondary crop every year from 2023. Mixed vegetables under cover,
    seed maize and a crop grown for a year at least meet it by exception.

    .. note:: Where several exceptions apply, the first concludes, where Catala stops on
        their conflict.
    """

    def query(self) -> Query:
        case = variable(FarmCase, domain=[self.case])
        cultivated = variable(
            CultivatedParcel,
            domain=CultivatedParcelProvision(case=self.case).conclusions,
        )
        parcel = cultivated.parcel
        criterion = deduced_variable(MultiYearCriterionOfParcel)
        query = an(
            entity(criterion).where(
                Parcel.grows_crop_exempt_from_multi_year_criterion(
                    parcel, case.calendar
                )
            )
        )
        with query:
            add(
                criterion,
                inference(MultiYearCriterionOfParcel)(
                    case=case, parcel=parcel, holds=True
                ),
            )
            with alternative(
                or_(
                    Parcel.grows_two_main_crops(parcel, case.calendar),
                    Parcel.grows_secondary_crop_every_year(parcel, case.calendar),
                )
            ):
                add(
                    criterion,
                    inference(MultiYearCriterionOfParcel)(
                        case=case, parcel=parcel, holds=True
                    ),
                )
            with alternative():
                add(
                    criterion,
                    inference(MultiYearCriterionOfParcel)(
                        case=case, parcel=parcel, holds=False
                    ),
                )
        return query


@dataclass
class MonocultureCriterionOfParcelProvision(
    CultivatedParcelCriterionProvision[MonocultureCriterionOfParcel]
):
    """
    The multi-year criterion of a cultivated parcel in spring monoculture also asks
    for a secondary crop on 15 November of each year from 2023, still grown on 15
    February; that of any other system is the multi-year criterion alone.
    """

    def query(self) -> Query:
        case = variable(FarmCase, domain=[self.case])
        multi_year = variable(
            MultiYearCriterionOfParcel,
            domain=MultiYearCriterionOfParcelProvision(case=self.case).conclusions,
        )
        parcel = multi_year.parcel
        criterion = deduced_variable(MonocultureCriterionOfParcel)
        query = an(
            entity(criterion).where(
                multi_year.holds == True,
                parcel.system == ParcelSystem.SPRING_MONOCULTURE,
                not_(Parcel.keeps_winter_cover(parcel, case.calendar)),
            )
        )
        with query:
            add(
                criterion,
                inference(MonocultureCriterionOfParcel)(
                    case=case, parcel=parcel, holds=False
                ),
            )
            with alternative():
                add(
                    criterion,
                    inference(MonocultureCriterionOfParcel)(
                        case=case, parcel=parcel, holds=multi_year.holds
                    ),
                )
        return query


@dataclass
class AreaMissingMultiYearCriterionProvision(
    ScopeProvision[AreaMissingMultiYearCriterion]
):
    """The area of the cultivated parcels that miss the multi-year criterion, with that of their monoculture system."""

    def query(self) -> Query:
        criterion = variable(
            MonocultureCriterionOfParcel,
            domain=MonocultureCriterionOfParcelProvision(case=self.case).conclusions,
        )
        hectares = an(
            entity(total(criterion.parcel.area_hectares, default=Fraction(0))).where(
                criterion.holds == False
            )
        ).first()
        case = variable(FarmCase, domain=[self.case])
        return an(
            entity(
                inference(AreaMissingMultiYearCriterion)(case=case, hectares=hectares)
            )
        )


@dataclass
class MultiYearCriterionProvision(ScopeProvision[MultiYearCriterion]):
    """
    The multi-year criterion: respected where every cultivated parcel meets it; missed
    otherwise by the area of those that do not and its share of the cultivated arable
    land.
    """

    def query(self) -> Query:
        case = variable(FarmCase, domain=[self.case])
        cultivated = variable(
            CultivatedArea, domain=CultivatedAreaProvision(case=self.case).conclusions
        )
        missing = variable(
            AreaMissingMultiYearCriterion,
            domain=AreaMissingMultiYearCriterionProvision(case=self.case).conclusions,
        )
        criterion = deduced_variable(MultiYearCriterion)
        query = an(entity(criterion).where(missing.hectares == 0))
        with query:
            add(criterion, inference(MultiYearCriterion)(case=case))
            with alternative():
                add(
                    criterion,
                    inference(MultiYearCriterion)(
                        case=case,
                        shortfall_proportion=missing.hectares / cultivated.hectares,
                        shortfall_hectares=missing.hectares,
                    ),
                )
        return query


# %% test files


class CropRotationTestFile(ScopeTestFile, StrEnum):
    """The test file of Catala's ``asp/bcae7`` example."""

    CROP_ROTATION = "tests_bcae7.catala_fr"
    """The examples of the technical sheet."""

    @property
    def directory(self) -> Path:
        """:file:`asp/bcae7/tests`."""
        return CatalaDirectory.ROOT / "asp" / "bcae7" / "tests"

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """:class:`FarmCase`."""
        return [FarmCase]
