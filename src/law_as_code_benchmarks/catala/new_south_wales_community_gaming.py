"""
The permitted gaming activities of the New South Wales Community Gaming Regulation, as
Catala's ``NSW_community_gaming`` example states them: each activity is permitted where
all of its requirements are complied with.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from pathlib import Path

from krrood.entity_query_language.core.base_expressions import SymbolicExpression
from krrood.entity_query_language.factories import (
    add,
    alternative,
    an,
    deduced_variable,
    entity,
    in_,
    inference,
    or_,
    variable,
)
from krrood.entity_query_language.query.query import Query
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.catala.money import Money
from law_as_code_benchmarks.catala.reader import CatalaDirectory, CatalaValue
from law_as_code_benchmarks.catala.scope_test import (
    CaseCondition,
    CatalaRecord,
    ScopeCase,
    ScopeProvision,
    ScopeTestFile,
)

# %% activities


class OrganisationType(StrEnum):
    """
    Who conducts an activity or benefits from it, each named as the constructors of the
    example's enumerations of organisations.
    """

    CHARITABLE = "Charitable"
    """A charitable organisation."""

    NON_PROFIT = "NonProfit"
    """A non-profit organisation."""

    PUBLIC_OR_CHARITABLE_OBJECT = "ObjectOfPublicOrCharitableCharacter"
    """An object of a public or charitable character."""

    NON_CHARITABLE = "NonCharitable"
    """An organisation that is not charitable."""

    PROFIT = "ProfitOrg"
    """An organisation conducted for profit."""

    PRIVATE_PURPOSE = "PrivatePurspose"
    """A private purpose, spelled as the example spells it."""


@dataclass
class DrawLottery(CatalaRecord):
    """A draw lottery."""

    organisation_type: OrganisationType
    """Who conducts it."""

    gross_proceeds: Money
    """Its gross proceeds."""

    total_prize_value: Money
    """The total value of its prizes."""

    proceeds_to_benefiting_organisation: Money
    """What of the proceeds is paid to the benefiting organisation."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of Catala's ``DrawLottery``."""
        return {
            "typeOrg": "organisation_type",
            "grossProceeds": "gross_proceeds",
            "totalValueOfThePrizes": "total_prize_value",
            "proceedsToBenefitingOrg": "proceeds_to_benefiting_organisation",
        }


@dataclass
class NoDrawLottery(DrawLottery):
    """A no-draw lottery."""

    tickets_produced: int = 0
    """The tickets produced or obtained for sale."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of Catala's ``NoDrawLottery``."""
        return {**DrawLottery.catala_names, "maxTickets": "tickets_produced"}


@dataclass
class ArtUnion(DrawLottery):
    """An art union gaming activity: prizes awarded by lot by an art union."""

    largest_money_prize: Money = field(default_factory=lambda: Money.zero)
    """The most money payable as a separate prize."""

    holds_authority: bool = False
    """Whether the person conducting it holds an authority in force and complies with it."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of Catala's ``ArtUnion``."""
        return {
            **DrawLottery.catala_names,
            "maxAmountMoneyAsSeparatePrize": "largest_money_prize",
            "holdsAuthority": "holds_authority",
        }


@dataclass
class CharityHousie(DrawLottery):
    """Charity housie."""

    total_expenses: Money = field(default_factory=lambda: Money.zero)
    """The total value of the expenses of conducting it."""

    tickets_per_participant: int = 0
    """The most tickets sold to one participant."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of Catala's ``CharityHousie``."""
        return {
            **DrawLottery.catala_names,
            "proceedsToBenefitingOrganisation": "proceeds_to_benefiting_organisation",
            "totalValueOfExpenses": "total_expenses",
            "maxTicketsPerParticipant": "tickets_per_participant",
        }


@dataclass
class ClubBingo(CatalaRecord):
    """Club bingo."""

    conducted_by_registered_club: bool
    """Whether a registered club conducts it on its premises to attract patronage."""

    prize_value_per_game: Money
    """The total value of the prizes of one game."""

    bonus_prize_value: Money
    """The value of the bonus prize offered at the end of a session."""

    bonus_prize_offered: bool
    """Whether a bonus prize is offered."""

    prizes_include_money: bool
    """Whether any prize consists of or includes money."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of Catala's ``ClubBingo``."""
        return {
            "registeredClub": "conducted_by_registered_club",
            "totalValuePrizePerGame": "prize_value_per_game",
            "bonusPrizeMaxValue": "bonus_prize_value",
            "bonusPrizeOffered": "bonus_prize_offered",
            "prizeContent": "prizes_include_money",
        }


@dataclass
class ProgressiveLottery(CatalaRecord):
    """A progressive lottery."""

    largest_money_prize: Money
    """The most money payable as a prize."""

    total_prize_value: Money
    """The total value of its prizes."""

    holds_authority: bool
    """Whether the person conducting it holds an authority in force and complies with it."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of Catala's ``ProgressiveLottery``."""
        return {
            "maxAmountPayable": "largest_money_prize",
            "totalValueOfThePrizes": "total_prize_value",
            "holdsAuthority": "holds_authority",
        }


@dataclass
class SocialHousie(CatalaRecord):
    """Social housie."""

    social_purposes_only: bool
    """Whether it is conducted solely for social purposes."""

    prize_value_per_session: Money
    """The total value of the prizes of one session."""

    on_licensed_premises: bool
    """Whether it is conducted on premises a licence under the Liquor Act 2007 relates to."""

    jackpot_prize_value: Money
    """The value of the jackpot prize where individual prizes are not won."""

    investment_returned: bool
    """Whether what participants invest, less prizes and expenses, is returned to them."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """The fields of Catala's ``SocialHousie``."""
        return {
            "socialPurposeOnly": "social_purposes_only",
            "totalValuePrizePerSession": "prize_value_per_session",
            "applicationOf2007Licence": "on_licensed_premises",
            "jackpotPrizeValue": "jackpot_prize_value",
            "investmentReturn": "investment_returned",
        }


# %% cases


class GamingOutput(StrEnum):
    """The outputs of Catala's ``GamingAuthorized`` scopes."""

    AUTHORIZED = "authorized"
    """Whether the activity is permitted."""


@dataclass(eq=False)
class GamingCase(ScopeCase, ABC):
    """A gaming activity, one of Catala's ``GamingAuthorized`` scopes."""

    @classproperty
    def catala_scope(cls) -> str:
        """``GamingAuthorized``, the scope of every activity's module."""
        return "GamingAuthorized"

    @classproperty
    @abstractmethod
    def provision(cls) -> type[PermittedActivityProvision]:
        """The provision permitting the activity."""

    def output(self, variable: str) -> CatalaValue:
        match GamingOutput(variable):
            case GamingOutput.AUTHORIZED:
                return self.sole_conclusion(self.provision).holds


@dataclass(eq=False)
class DrawLotteryCase(GamingCase):
    """A draw lottery, Catala's ``drawLottery`` input."""

    draw_lottery: DrawLottery | None = None
    """The lottery."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """Catala's ``drawLottery`` input."""
        return {"drawLottery": "draw_lottery"}

    @classproperty
    def provision(cls) -> type[PermittedActivityProvision]:
        """:class:`DrawLotteryProvision`."""
        return DrawLotteryProvision


@dataclass(eq=False)
class NoDrawLotteryCase(GamingCase):
    """A no-draw lottery, Catala's ``noDrawLottery`` input."""

    no_draw_lottery: NoDrawLottery | None = None
    """The lottery."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """Catala's ``noDrawLottery`` input."""
        return {"noDrawLottery": "no_draw_lottery"}

    @classproperty
    def provision(cls) -> type[PermittedActivityProvision]:
        """:class:`NoDrawLotteryProvision`."""
        return NoDrawLotteryProvision


@dataclass(eq=False)
class ArtUnionCase(GamingCase):
    """An art union gaming activity, Catala's ``artUnion`` input."""

    art_union: ArtUnion | None = None
    """The activity."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """Catala's ``artUnion`` input."""
        return {"artUnion": "art_union"}

    @classproperty
    def provision(cls) -> type[PermittedActivityProvision]:
        """:class:`ArtUnionProvision`."""
        return ArtUnionProvision


@dataclass(eq=False)
class CharityHousieCase(GamingCase):
    """Charity housie, Catala's ``charityHousie`` input."""

    charity_housie: CharityHousie | None = None
    """The activity."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """Catala's ``charityHousie`` input."""
        return {"charityHousie": "charity_housie"}

    @classproperty
    def provision(cls) -> type[PermittedActivityProvision]:
        """:class:`CharityHousieProvision`."""
        return CharityHousieProvision


@dataclass(eq=False)
class ClubBingoCase(GamingCase):
    """Club bingo, Catala's ``clubBingo`` input."""

    club_bingo: ClubBingo | None = None
    """The activity."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """Catala's ``clubBingo`` input."""
        return {"clubBingo": "club_bingo"}

    @classproperty
    def provision(cls) -> type[PermittedActivityProvision]:
        """:class:`ClubBingoProvision`."""
        return ClubBingoProvision


@dataclass(eq=False)
class ProgressiveLotteryCase(GamingCase):
    """A progressive lottery, Catala's ``progressiveLottery`` input."""

    progressive_lottery: ProgressiveLottery | None = None
    """The lottery."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """Catala's ``progressiveLottery`` input."""
        return {"progressiveLottery": "progressive_lottery"}

    @classproperty
    def provision(cls) -> type[PermittedActivityProvision]:
        """:class:`ProgressiveLotteryProvision`."""
        return ProgressiveLotteryProvision


@dataclass(eq=False)
class SocialHousieCase(GamingCase):
    """Social housie, Catala's ``socialHousie`` input."""

    social_housie: SocialHousie | None = None
    """The activity."""

    @classproperty
    def catala_names(cls) -> dict[str, str]:
        """Catala's ``socialHousie`` input."""
        return {"socialHousie": "social_housie"}

    @classproperty
    def provision(cls) -> type[PermittedActivityProvision]:
        """:class:`SocialHousieProvision`."""
        return SocialHousieProvision


# %% provisions


@dataclass(eq=False)
class PermittedActivity(CaseCondition):
    """Section 10 of the Act: the activity is a permitted gaming activity."""


@dataclass
class PermittedActivityProvision(ScopeProvision[PermittedActivity], ABC):
    """An activity is permitted where every requirement of its clause is complied with."""

    @abstractmethod
    def requirements(self, case: GamingCase) -> list[SymbolicExpression]:
        """:return: The requirements of the activity, over a variable of its case."""

    def query(self) -> Query:
        case = variable(type(self.case), domain=[self.case])
        permitted = deduced_variable(PermittedActivity)
        query = an(entity(permitted).where(*self.requirements(case)))
        with query:
            add(permitted, inference(PermittedActivity)(case=case, holds=True))
            with alternative():
                add(permitted, inference(PermittedActivity)(case=case, holds=False))
        return query


@dataclass
class DrawLotteryProvision(PermittedActivityProvision):
    """
    (a) conducted by or for a charitable or non-profit organisation, (b) at least 40 %
    of the gross proceeds paid to it, (c) prizes worth $30,000 at most.
    """

    def requirements(self, case: GamingCase) -> list[SymbolicExpression]:
        lottery = case.draw_lottery
        return [
            in_(
                lottery.organisation_type,
                {OrganisationType.CHARITABLE, OrganisationType.NON_PROFIT},
            ),
            lottery.proceeds_to_benefiting_organisation
            >= lottery.gross_proceeds * Fraction(40, 100),
            lottery.total_prize_value <= Money.from_euros(30_000),
        ]


@dataclass
class NoDrawLotteryProvision(PermittedActivityProvision):
    """
    (a) conducted by or for a charitable or non-profit organisation, (b) at least 40 %
    of the gross proceeds paid to it, (c) prizes worth $5,000 at most, (d) 3,000
    tickets at most.
    """

    def requirements(self, case: GamingCase) -> list[SymbolicExpression]:
        lottery = case.no_draw_lottery
        return [
            in_(
                lottery.organisation_type,
                {OrganisationType.CHARITABLE, OrganisationType.NON_PROFIT},
            ),
            lottery.proceeds_to_benefiting_organisation
            >= lottery.gross_proceeds * Fraction(40, 100),
            lottery.total_prize_value <= Money.from_euros(5_000),
            lottery.tickets_produced <= 3000,
        ]


@dataclass
class ArtUnionProvision(PermittedActivityProvision):
    """
    (a) at least 30 % of the gross proceeds paid to a charitable or non-profit
    organisation or an object of a public or charitable character, (b) prizes worth
    $30,000 or more, as Catala reads "exceeds", (c) no separate money prize above
    $30,000, (d) an authority held and complied with.
    """

    def requirements(self, case: GamingCase) -> list[SymbolicExpression]:
        union = case.art_union
        return [
            union.proceeds_to_benefiting_organisation
            >= union.gross_proceeds * Fraction(30, 100),
            in_(
                union.organisation_type,
                {
                    OrganisationType.CHARITABLE,
                    OrganisationType.NON_PROFIT,
                    OrganisationType.PUBLIC_OR_CHARITABLE_OBJECT,
                },
            ),
            union.total_prize_value >= Money.from_euros(30_000),
            union.largest_money_prize <= Money.from_euros(30_000),
            union.holds_authority == True,
        ]


@dataclass
class CharityHousieProvision(PermittedActivityProvision):
    """
    (a) conducted by or for a charitable organisation, (b) at least 12.5 % of the gross
    proceeds paid to it, (c) expenses less prizes at most 12.5 % of the gross proceeds,
    (d) prizes of a session worth $10,000 and 75 % of the gross proceeds at most, (e) 48
    tickets per participant at most.
    """

    def requirements(self, case: GamingCase) -> list[SymbolicExpression]:
        housie = case.charity_housie
        share = Fraction(125, 1000)
        return [
            housie.organisation_type == OrganisationType.CHARITABLE,
            housie.proceeds_to_benefiting_organisation >= housie.gross_proceeds * share,
            housie.total_expenses - housie.total_prize_value
            <= housie.gross_proceeds * share,
            housie.total_prize_value <= Money.from_euros(10_000),
            housie.total_prize_value <= housie.gross_proceeds * Fraction(75, 100),
            housie.tickets_per_participant <= 48,
        ]


@dataclass
class ClubBingoProvision(PermittedActivityProvision):
    """
    (a) conducted by a registered club, (b) prizes of a game worth $70 at most, (c) any
    bonus prize worth $70 at most, (d) no prize of money.
    """

    def requirements(self, case: GamingCase) -> list[SymbolicExpression]:
        bingo = case.club_bingo
        limit = Money.from_euros(70)
        return [
            bingo.conducted_by_registered_club == True,
            bingo.prize_value_per_game <= limit,
            or_(bingo.bonus_prize_value <= limit, bingo.bonus_prize_offered == False),
            bingo.prizes_include_money == False,
        ]


@dataclass
class ProgressiveLotteryProvision(PermittedActivityProvision):
    """
    (a) no money prize above $7,000, (b) where the prizes are worth $30,000 or more, an
    authority held and complied with, as Catala reads "exceeds".
    """

    def requirements(self, case: GamingCase) -> list[SymbolicExpression]:
        lottery = case.progressive_lottery
        return [
            lottery.largest_money_prize <= Money.from_euros(7_000),
            or_(
                lottery.total_prize_value < Money.from_euros(30_000),
                lottery.holds_authority == True,
            ),
        ]


@dataclass
class SocialHousieProvision(PermittedActivityProvision):
    """
    (a) solely for social purposes, (b) not on licensed premises, (c) prizes of a
    session worth $40 at most, (d) any jackpot worth $200 at most, (e) the investment
    returned to participants.
    """

    def requirements(self, case: GamingCase) -> list[SymbolicExpression]:
        housie = case.social_housie
        return [
            housie.social_purposes_only == True,
            housie.on_licensed_premises == False,
            housie.prize_value_per_session <= Money.from_euros(40),
            housie.jackpot_prize_value <= Money.from_euros(200),
            housie.investment_returned == True,
        ]


# %% test files


class NewSouthWalesCommunityGamingTestFile(ScopeTestFile, StrEnum):
    """The test files of Catala's ``NSW_community_gaming`` example, one per activity."""

    ART_UNION = "test_nsw_art_union.catala_en"
    """Art unions."""

    CHARITY_HOUSIE = "test_nsw_charity_housie.catala_en"
    """Charity housie."""

    CLUB_BINGO = "test_nsw_club_bingo.catala_en"
    """Club bingo."""

    DRAW_LOTTERY = "test_nsw_draw_lottery.catala_en"
    """Draw lotteries."""

    NO_DRAW_LOTTERY = "test_nsw_no_draw_lottery.catala_en"
    """No-draw lotteries."""

    PROGRESSIVE_LOTTERY = "test_nsw_progressive_lottery.catala_en"
    """Progressive lotteries."""

    @property
    def directory(self) -> Path:
        """:file:`NSW_community_gaming/tests`."""
        return CatalaDirectory.ROOT / "NSW_community_gaming" / "tests"

    @property
    def scope_cases(self) -> list[type[ScopeCase]]:
        """The activity the file tests."""
        return [
            {
                NewSouthWalesCommunityGamingTestFile.ART_UNION: ArtUnionCase,
                NewSouthWalesCommunityGamingTestFile.CHARITY_HOUSIE: CharityHousieCase,
                NewSouthWalesCommunityGamingTestFile.CLUB_BINGO: ClubBingoCase,
                NewSouthWalesCommunityGamingTestFile.DRAW_LOTTERY: DrawLotteryCase,
                NewSouthWalesCommunityGamingTestFile.NO_DRAW_LOTTERY: NoDrawLotteryCase,
                NewSouthWalesCommunityGamingTestFile.PROGRESSIVE_LOTTERY: ProgressiveLotteryCase,
            }[self]
        ]
