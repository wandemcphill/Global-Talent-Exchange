from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.access_control.service import AccessControlService
from app.core.config import DEFAULT_DATABASE_URL
from app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from app.federations.service import FederationService
from app.global_memory.models import NationalTeamCountryRanking
from app.ingestion.demo_bootstrap import DEFAULT_DEMO_PROVIDER_NAME
from app.ingestion.models import Country, Player
from app.marketplace.service import AgentAskingType
from app.models.agent_marketplace import AgentMarketplaceListing
from app.models.club_profile import ClubProfile
from app.models.competition import UserCompetition
from app.models.federation import (
    Federation,
    FederationLeague,
    FederationMembership,
    FederationMembershipStatus,
    FederationProposal,
    FederationProposalStatus,
    FederationSanction,
    FederationTreasuryEntry,
    FederationVote,
    FederationVoteType,
)
from app.models.national_team import NationalTeamCompetition, NationalTeamCompetitionEntry
from app.models.national_team_tournament import StadiumAd, StadiumAdPlacement, StoryEvent, StoryEventType, TournamentTheme
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.transfer_market import (
    ClubTeamDynamics,
    CoachDemand,
    CoachProfile,
    MarketWatchlistEntry,
    PlayerCoachRelationship,
    PlayerDecisionProfile,
    TransferListing,
    TransferListingBid,
    TransferNegotiation,
)
from app.models.user import User
from app.national_team_engine.competition_lifecycle_service import NationalCompetitionLifecycleService
from app.national_team_engine.tournament_service import NationalTeamTournamentService
from app.regen_universe.expansion_service import RegenUniverseExpansionService
from app.regen_universe.models import RegenAward, RegenSeason
from app.regen_universe.service import RegenUniverseService

DEMO_WORLD_VISIBILITY_SOURCE = "demo_world_visibility"
DEMO_WORLD_VISIBILITY_BATCH = "u17_batch"

_DEMO_USERNAMES = {
    "fan": "seed_fan",
    "scout": "seed_scout",
    "admin": "seed_admin",
}

_DEMO_CLUB_IDS = {
    "fan": "00000000-0000-0000-0000-000000000101",
    "scout": "00000000-0000-0000-0000-000000000102",
    "admin": "00000000-0000-0000-0000-000000000103",
}

_TRANSFER_LISTING_IDS = {
    "heated": "00000000-0000-0000-0000-000000000501",
    "waiting": "00000000-0000-0000-0000-000000000502",
    "negotiation": "00000000-0000-0000-0000-000000000503",
}

_TRANSFER_BID_IDS = {
    "heated_first": "00000000-0000-0000-0000-000000000601",
    "heated_second": "00000000-0000-0000-0000-000000000602",
    "negotiation_first": "00000000-0000-0000-0000-000000000603",
    "negotiation_second": "00000000-0000-0000-0000-000000000604",
}

_TRANSFER_NEGOTIATION_ID = "00000000-0000-0000-0000-000000000701"
_NATIONAL_TEAM_THEME_ID = "00000000-0000-0000-0000-000000000901"
_NATIONAL_TEAM_AD_ID = "00000000-0000-0000-0000-000000000902"
_NATIONAL_TEAM_STORY_ID = "00000000-0000-0000-0000-000000000903"


@dataclass(frozen=True, slots=True)
class DemoWorldVisibilitySummary:
    club_count: int
    marketplace_listing_count: int
    transfer_listing_count: int
    transfer_bid_count: int
    transfer_negotiation_count: int
    federation_count: int
    federation_membership_count: int
    federation_league_count: int
    national_team_competition_count: int
    national_team_entry_count: int
    national_team_ranking_count: int
    national_regen_seed_count: int
    regen_season_count: int
    regen_award_definition_count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "club_count": self.club_count,
            "marketplace_listing_count": self.marketplace_listing_count,
            "transfer_listing_count": self.transfer_listing_count,
            "transfer_bid_count": self.transfer_bid_count,
            "transfer_negotiation_count": self.transfer_negotiation_count,
            "federation_count": self.federation_count,
            "federation_membership_count": self.federation_membership_count,
            "federation_league_count": self.federation_league_count,
            "national_team_competition_count": self.national_team_competition_count,
            "national_team_entry_count": self.national_team_entry_count,
            "national_team_ranking_count": self.national_team_ranking_count,
            "national_regen_seed_count": self.national_regen_seed_count,
            "regen_season_count": self.regen_season_count,
            "regen_award_definition_count": self.regen_award_definition_count,
        }


@dataclass(frozen=True, slots=True)
class _DemoClubSpec:
    key: str
    name: str
    short_name: str
    slug: str
    primary_color: str
    secondary_color: str
    accent_color: str
    stadium: str
    city: str
    region: str
    description: str


_DEMO_CLUB_SPECS = (
    _DemoClubSpec(
        key="fan",
        name="Lagos Atlas FC",
        short_name="Atlas",
        slug="demo-lagos-atlas-fc",
        primary_color="#10263F",
        secondary_color="#F2B632",
        accent_color="#26D07C",
        stadium="Atlas Harbour",
        city="Lagos",
        region="West Africa",
        description="Demo visibility club anchoring the Lagos route.",
    ),
    _DemoClubSpec(
        key="scout",
        name="Rio Norte SC",
        short_name="Rio Norte",
        slug="demo-rio-norte-sc",
        primary_color="#1D3557",
        secondary_color="#E63946",
        accent_color="#F1FAEE",
        stadium="Mar Azul Ground",
        city="Rio de Janeiro",
        region="South America",
        description="Demo visibility club anchoring the South America route.",
    ),
    _DemoClubSpec(
        key="admin",
        name="Valencia Crest CF",
        short_name="Crest",
        slug="demo-valencia-crest-cf",
        primary_color="#2B2D42",
        secondary_color="#FF9F1C",
        accent_color="#F7F7FF",
        stadium="Crest Arena",
        city="Valencia",
        region="Europe",
        description="Demo visibility club anchoring the Europe route.",
    ),
)


@dataclass(slots=True)
class DemoWorldVisibilitySeeder:
    session: Session

    def seed(
        self,
        *,
        provider_name: str = DEFAULT_DEMO_PROVIDER_NAME,
    ) -> DemoWorldVisibilitySummary:
        users = self._load_demo_users()
        countries = self._resolve_seed_countries()
        clubs = self._upsert_demo_clubs(users=users, countries=countries)
        seeded_players = self._assign_players_to_demo_clubs(provider_name=provider_name, clubs=clubs, countries=countries)
        self._seed_marketplace(seed_players=seeded_players, users=users)
        self._seed_transfer_market(seed_players=seeded_players, clubs=clubs)
        self._seed_federations(users=users, clubs=clubs, countries=countries)
        self._seed_national_team_bundle(users=users, countries=countries)
        self.session.commit()
        return self._build_summary()

    def _load_demo_users(self) -> dict[str, User]:
        users: dict[str, User] = {}
        for key, username in _DEMO_USERNAMES.items():
            user = self.session.scalar(select(User).where(User.username == username))
            if user is None:
                raise ValueError(f"Demo visibility requires demo user '{username}'.")
            users[key] = user
        return users

    def _resolve_seed_countries(self) -> dict[str, Country]:
        preferred = {
            "fan": ("NG", "NGA", "Nigeria"),
            "scout": ("BR", "BRA", "Brazil"),
            "admin": ("ES", "ESP", "Spain"),
        }
        countries: dict[str, Country] = {}
        for key, codes in preferred.items():
            country = self._find_country(codes)
            if country is not None:
                countries[key] = country
        if len(countries) == len(preferred):
            return countries

        fallback = list(
            self.session.scalars(
                select(Country)
                .where(Country.is_enabled_for_universe.is_(True))
                .order_by(Country.name.asc(), Country.id.asc())
            ).all()
        )
        fallback_iter = iter(fallback)
        for key in preferred:
            countries.setdefault(key, next(fallback_iter))
        return countries

    def _find_country(self, codes: tuple[str, ...]) -> Country | None:
        upper_codes = {code.strip().upper() for code in codes if code}
        if not upper_codes:
            return None
        return self.session.scalar(
            select(Country).where(
                or_(
                    Country.alpha2_code.in_(upper_codes),
                    Country.alpha3_code.in_(upper_codes),
                    Country.fifa_code.in_(upper_codes),
                    Country.name.in_(codes),
                )
            )
        )

    def _upsert_demo_clubs(self, *, users: dict[str, User], countries: dict[str, Country]) -> dict[str, ClubProfile]:
        access_service = AccessControlService(self.session)
        clubs: dict[str, ClubProfile] = {}
        for spec in _DEMO_CLUB_SPECS:
            country = countries[spec.key]
            club = self.session.get(ClubProfile, _DEMO_CLUB_IDS[spec.key])
            if club is None:
                club = self.session.scalar(select(ClubProfile).where(ClubProfile.slug == spec.slug))
            if club is None:
                club = ClubProfile(
                    id=_DEMO_CLUB_IDS[spec.key],
                    owner_user_id=users[spec.key].id,
                    club_name=spec.name,
                    short_name=spec.short_name,
                    slug=spec.slug,
                    primary_color=spec.primary_color,
                    secondary_color=spec.secondary_color,
                    accent_color=spec.accent_color,
                    home_venue_name=spec.stadium,
                    country_code=self._country_code(country),
                    region_name=spec.region,
                    city_name=spec.city,
                    description=spec.description,
                )
                self.session.add(club)
            else:
                club.id = _DEMO_CLUB_IDS[spec.key]
                club.owner_user_id = users[spec.key].id
                club.club_name = spec.name
                club.short_name = spec.short_name
                club.slug = spec.slug
                club.primary_color = spec.primary_color
                club.secondary_color = spec.secondary_color
                club.accent_color = spec.accent_color
                club.home_venue_name = spec.stadium
                club.country_code = self._country_code(country)
                club.region_name = spec.region
                club.city_name = spec.city
                club.description = spec.description
            self.session.flush()
            access_service.ensure_club_organization(club, owner_user_id=users[spec.key].id)
            clubs[spec.key] = club
        return clubs

    def _assign_players_to_demo_clubs(
        self,
        *,
        provider_name: str,
        clubs: dict[str, ClubProfile],
        countries: dict[str, Country],
    ) -> dict[str, list[Player]]:
        def load_rows(*, provider_filter: str | None, require_real_players: bool) -> list[tuple[Player, Country | None]]:
            statement = (
                select(Player, Country)
                .outerjoin(Country, Country.id == Player.country_id)
                .order_by(
                    Player.market_value_eur.desc().nullslast(),
                    Player.full_name.asc(),
                    Player.id.asc(),
                )
            )
            if provider_filter:
                statement = statement.where(Player.source_provider == provider_filter)
            if require_real_players:
                statement = statement.where(Player.is_real_player.is_(True))
            return list(self.session.execute(statement).all())

        rows = load_rows(provider_filter=provider_name, require_real_players=True)
        if len(rows) < 9:
            rows = load_rows(provider_filter=provider_name, require_real_players=False)
        if len(rows) < 9:
            rows = load_rows(provider_filter=None, require_real_players=False)
        if len(rows) < 9:
            raise ValueError("Demo visibility requires at least nine demo players.")

        by_country: dict[str, list[Player]] = {}
        fallback: list[Player] = []
        for player, country in rows:
            fallback.append(player)
            code = self._country_code(country)
            by_country.setdefault(code, []).append(player)

        used_player_ids: set[str] = set()
        assignments: dict[str, list[Player]] = {key: [] for key in clubs}
        for key in clubs:
            preferred_code = self._country_code(countries[key])
            for player in by_country.get(preferred_code, []):
                if player.id in used_player_ids:
                    continue
                assignments[key].append(player)
                used_player_ids.add(player.id)
                if len(assignments[key]) == 3:
                    break
        for key in clubs:
            if len(assignments[key]) == 3:
                continue
            for player in fallback:
                if player.id in used_player_ids:
                    continue
                assignments[key].append(player)
                used_player_ids.add(player.id)
                if len(assignments[key]) == 3:
                    break

        for key, players in assignments.items():
            club = clubs[key]
            for player in players:
                player.current_club_profile_id = club.id
                player.real_world_club_name = club.club_name
                player.is_tradable = True
                if player.current_market_reference_value is None:
                    player.current_market_reference_value = float(player.market_value_eur or 7_500_000)
                if player.market_value_eur is None:
                    player.market_value_eur = float(player.current_market_reference_value)
        self.session.flush()
        return assignments

    def _seed_marketplace(self, *, seed_players: dict[str, list[Player]], users: dict[str, User]) -> None:
        listing_players = (
            seed_players["fan"][:2]
            + seed_players["scout"][:2]
            + seed_players["admin"][:2]
        )
        asking_types = (
            AgentAskingType.TRANSFER,
            AgentAskingType.TRIAL,
            AgentAskingType.LOAN,
            AgentAskingType.TRANSFER,
            AgentAskingType.TRIAL,
            AgentAskingType.TRANSFER,
        )
        for index, player in enumerate(listing_players):
            listing = self.session.scalar(
                select(AgentMarketplaceListing).where(AgentMarketplaceListing.player_id == player.id)
            )
            if listing is None:
                listing = AgentMarketplaceListing(player_id=player.id)
                self.session.add(listing)
            listing.agent_user_id = users["scout"].id if index % 2 == 0 else users["admin"].id
            listing.is_available = index != len(listing_players) - 1
            listing.asking_type = asking_types[index]
            listing.note = (
                "Demo visibility listing seeded for the live transfer desk."
                if listing.is_available
                else "Player is being held back while the board reviews the next move."
            )
        self.session.flush()

    def _seed_transfer_market(self, *, seed_players: dict[str, list[Player]], clubs: dict[str, ClubProfile]) -> None:
        now = datetime.now(UTC)
        heated_player = seed_players["fan"][0]
        waiting_player = seed_players["scout"][0]
        negotiation_player = seed_players["admin"][0]

        for key, club in clubs.items():
            self._upsert_coach_profile(club=club, tactical_philosophy=("pressing" if key == "fan" else "balanced"))
            self._upsert_team_dynamics(club=club, leader_player_ids=[player.id for player in seed_players[key][:2]])

        self._upsert_player_decision_profile(heated_player, preferred_country_code=clubs["admin"].country_code)
        self._upsert_player_decision_profile(waiting_player, preferred_country_code=clubs["fan"].country_code)
        self._upsert_player_decision_profile(negotiation_player, preferred_country_code=clubs["scout"].country_code)
        self._upsert_player_coach_relationship(negotiation_player, club=clubs["fan"])

        self._replace_transfer_listing(
            listing_id=_TRANSFER_LISTING_IDS["heated"],
            player=heated_player,
            selling_club=clubs["fan"],
            status="open",
            base_price=self._transfer_price(heated_player, factor="0.92"),
            current_highest_bid=self._transfer_price(heated_player, factor="1.07"),
            highest_bidder_id=clubs["admin"].id,
            expires_at=now + timedelta(hours=4),
            closed_at=None,
            reserve_price=self._transfer_price(heated_player, factor="1.02"),
            bids=(
                (
                    _TRANSFER_BID_IDS["heated_first"],
                    clubs["scout"].id,
                    self._transfer_price(heated_player, factor="0.98"),
                    now - timedelta(minutes=80),
                ),
                (
                    _TRANSFER_BID_IDS["heated_second"],
                    clubs["admin"].id,
                    self._transfer_price(heated_player, factor="1.07"),
                    now - timedelta(minutes=18),
                ),
            ),
            negotiation=None,
        )
        self._upsert_watchlist_entry(
            club=clubs["scout"],
            player=heated_player,
            source="transfer_center",
            discovery_score=87.0,
            listing_id=_TRANSFER_LISTING_IDS["heated"],
        )
        self._upsert_watchlist_entry(
            club=clubs["admin"],
            player=heated_player,
            source="board_review",
            discovery_score=91.0,
            listing_id=_TRANSFER_LISTING_IDS["heated"],
        )

        self._replace_transfer_listing(
            listing_id=_TRANSFER_LISTING_IDS["waiting"],
            player=waiting_player,
            selling_club=clubs["scout"],
            status="open",
            base_price=self._transfer_price(waiting_player, factor="0.95"),
            current_highest_bid=self._transfer_price(waiting_player, factor="0.95"),
            highest_bidder_id=None,
            expires_at=now + timedelta(hours=9),
            closed_at=None,
            reserve_price=self._transfer_price(waiting_player, factor="1.00"),
            bids=(),
            negotiation=None,
        )
        self._upsert_watchlist_entry(
            club=clubs["fan"],
            player=waiting_player,
            source="scouting",
            discovery_score=76.0,
            listing_id=_TRANSFER_LISTING_IDS["waiting"],
        )

        self._replace_transfer_listing(
            listing_id=_TRANSFER_LISTING_IDS["negotiation"],
            player=negotiation_player,
            selling_club=clubs["admin"],
            status="closed",
            base_price=self._transfer_price(negotiation_player, factor="0.90"),
            current_highest_bid=self._transfer_price(negotiation_player, factor="1.05"),
            highest_bidder_id=clubs["fan"].id,
            expires_at=now - timedelta(hours=2),
            closed_at=now - timedelta(hours=1),
            reserve_price=self._transfer_price(negotiation_player, factor="1.00"),
            bids=(
                (
                    _TRANSFER_BID_IDS["negotiation_first"],
                    clubs["scout"].id,
                    self._transfer_price(negotiation_player, factor="0.97"),
                    now - timedelta(hours=4),
                ),
                (
                    _TRANSFER_BID_IDS["negotiation_second"],
                    clubs["fan"].id,
                    self._transfer_price(negotiation_player, factor="1.05"),
                    now - timedelta(hours=3, minutes=10),
                ),
            ),
            negotiation={
                "id": _TRANSFER_NEGOTIATION_ID,
                "bidder_club_id": clubs["fan"].id,
                "status": "counter_offer",
                "wage_offer_amount": Decimal("148500.0000"),
                "contract_years": 4,
                "expected_role": "Important Player",
                "agent_response": "counter_offer",
                "coach_stance": "approve",
                "coach_reason": "Fits the tactical transition lane immediately.",
                "player_decision_json": {
                    "action": "delay",
                    "score": 71.5,
                    "concerns": ["Wants a stronger appearance bonus."],
                },
                "coach_opinion_json": {
                    "stance": "approve",
                    "reason": "The player fixes the left-sided creation gap.",
                    "tactical_fit": 79.0,
                    "personality_fit": 74.0,
                },
                "concerns_json": ["Wage structure under review", "Agent wants appearance upside"],
                "decision_due_at": now + timedelta(hours=18),
                "metadata_json": {
                    "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
                    "agent_negotiation": {
                        "action": "counter_offer",
                        "demands": ["Appearance bonus", "Release clause clarity"],
                        "confidence_score": 78.0,
                    },
                    "notes": "Counter-offer seeded for transfer center detail validation.",
                    "bonus_terms": "Appearance bonus plus resale ladder.",
                },
            },
        )
        self.session.flush()

    def _seed_federations(
        self,
        *,
        users: dict[str, User],
        clubs: dict[str, ClubProfile],
        countries: dict[str, Country],
    ) -> None:
        self._replace_federation_bundle(
            federation_id="00000000-0000-0000-0000-000000000201",
            league_id="00000000-0000-0000-0000-000000000301",
            competition_id="00000000-0000-0000-0000-000000000401",
            proposal_id="00000000-0000-0000-0000-000000000801",
            vote_id="00000000-0000-0000-0000-000000000811",
            sanction_id="00000000-0000-0000-0000-000000000821",
            treasury_id="00000000-0000-0000-0000-000000000831",
            owner=users["fan"],
            club=clubs["fan"],
            member_clubs=(clubs["fan"], clubs["admin"]),
            region_code="west_africa",
            region_label="West Africa",
            name="GTEX West Africa Federation",
            league_name="West Africa Elite Circuit",
            country_code=self._country_code(countries["fan"]),
        )
        self._replace_federation_bundle(
            federation_id="00000000-0000-0000-0000-000000000202",
            league_id="00000000-0000-0000-0000-000000000302",
            competition_id="00000000-0000-0000-0000-000000000402",
            proposal_id="00000000-0000-0000-0000-000000000802",
            vote_id="00000000-0000-0000-0000-000000000812",
            sanction_id="00000000-0000-0000-0000-000000000822",
            treasury_id="00000000-0000-0000-0000-000000000832",
            owner=users["scout"],
            club=clubs["scout"],
            member_clubs=(clubs["scout"], clubs["fan"]),
            region_code="south_america",
            region_label="South America",
            name="GTEX Atlantic Federation",
            league_name="Atlantic Prospect Series",
            country_code=self._country_code(countries["scout"]),
        )
        self._replace_federation_bundle(
            federation_id="00000000-0000-0000-0000-000000000203",
            league_id="00000000-0000-0000-0000-000000000303",
            competition_id="00000000-0000-0000-0000-000000000403",
            proposal_id="00000000-0000-0000-0000-000000000803",
            vote_id="00000000-0000-0000-0000-000000000813",
            sanction_id="00000000-0000-0000-0000-000000000823",
            treasury_id="00000000-0000-0000-0000-000000000833",
            owner=users["admin"],
            club=clubs["admin"],
            member_clubs=(clubs["admin"], clubs["fan"], clubs["scout"]),
            region_code="europe",
            region_label="Europe",
            name="GTEX Continental Federation",
            league_name="Continental Prestige League",
            country_code=self._country_code(countries["admin"]),
        )

    def _seed_national_team_bundle(self, *, users: dict[str, User], countries: dict[str, Country]) -> None:
        regen_service = RegenUniverseService(self.session)
        regen_service.seed_defaults()

        expansion_service = RegenUniverseExpansionService(self.session)
        expansion_service.seed_preseeded_national_regens(
            country_codes=[self._country_code(country) for country in countries.values()],
            seeds_per_country=18,
            age_min=14,
            age_max=17,
            include_legendary_regens=True,
            preseed_batch=DEMO_WORLD_VISIBILITY_BATCH,
        )

        tournament_service = NationalTeamTournamentService(self.session)
        tournament_service.seed_default_competitions(actor=users["admin"])

        competition = self.session.scalar(
            select(NationalTeamCompetition).where(NationalTeamCompetition.key == "gtex-u17-world-cup")
        )
        if competition is None:
            raise ValueError("Expected seeded national-team competition 'gtex-u17-world-cup'.")

        now = datetime.now(UTC)
        competition.entry_opens_at = now - timedelta(days=2)
        competition.entry_closes_at = now + timedelta(days=12)
        competition.kickoff_at = now + timedelta(days=18)
        competition.completed_at = None
        competition.status = "registration"
        competition_metadata = dict(competition.metadata_json or {})
        competition_metadata.pop("lifecycle_state", None)
        competition.notes = "Demo visibility competition seeded for the live national-team routes."
        competition.metadata_json = {
            **competition_metadata,
            "demo_visibility_seed": True,
            "highlight_country_codes": [self._country_code(country) for country in countries.values()],
        }

        self.session.execute(
            delete(NationalTeamCompetitionEntry).where(
                NationalTeamCompetitionEntry.competition_id == competition.id,
                NationalTeamCompetitionEntry.user_id.in_([user.id for user in users.values()]),
            )
        )
        self.session.flush()

        lifecycle = NationalCompetitionLifecycleService(self.session)
        for key, user in users.items():
            country = countries[key]
            squad = self._national_team_squad(country_code=self._country_code(country))
            lifecycle.submit_entry(
                competition_id=competition.id,
                actor=user,
                payload=SimpleNamespace(
                    country_code=self._country_code(country),
                    country_name=country.name,
                    squad=squad,
                ),
            )
        lifecycle.lock_entries(competition_id=competition.id)

        self._upsert_national_team_theme(competition=competition)
        self._upsert_national_team_ad(competition=competition, reference_at=now)
        self._upsert_national_team_story_event(competition=competition)
        self._upsert_country_rankings(competition=competition, countries=list(countries.values()))
        self.session.flush()

    def _replace_transfer_listing(
        self,
        *,
        listing_id: str,
        player: Player,
        selling_club: ClubProfile,
        status: str,
        base_price: Decimal,
        current_highest_bid: Decimal,
        highest_bidder_id: str | None,
        expires_at: datetime,
        closed_at: datetime | None,
        reserve_price: Decimal,
        bids: tuple[tuple[str, str, Decimal, datetime], ...],
        negotiation: dict[str, Any] | None,
    ) -> None:
        self.session.execute(delete(TransferNegotiation).where(TransferNegotiation.listing_id == listing_id))
        self.session.execute(delete(TransferListingBid).where(TransferListingBid.listing_id == listing_id))

        listing = self.session.get(TransferListing, listing_id)
        if listing is None:
            listing = TransferListing(id=listing_id, player_id=player.id, selling_club_id=selling_club.id, expires_at=expires_at)
            self.session.add(listing)

        listing.player_id = player.id
        listing.selling_club_id = selling_club.id
        listing.base_price = base_price
        listing.current_highest_bid = current_highest_bid
        listing.highest_bidder_id = highest_bidder_id
        listing.status = status
        listing.expires_at = expires_at
        listing.closed_at = closed_at
        listing.reserve_price = reserve_price
        listing.bid_count = len(bids)
        listing.watchlist_count = self._watchlist_count(player.id)
        listing.anti_sniping_extension_count = 1 if status == "open" and bids else 0
        listing.last_bid_at = bids[-1][3] if bids else None
        listing.metadata_json = {
            "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
            "drama_events": [
                {
                    "type": "demo_visibility_seed",
                    "headline": "Demo transfer lane primed",
                    "occurred_at": datetime.now(UTC).isoformat(),
                }
            ],
        }
        self.session.flush()

        for bid_id, bidder_club_id, amount, timestamp in bids:
            self.session.add(
                TransferListingBid(
                    id=bid_id,
                    listing_id=listing.id,
                    bidder_club_id=bidder_club_id,
                    amount=amount,
                    timestamp=timestamp,
                    metadata_json={"seed_source": DEMO_WORLD_VISIBILITY_SOURCE},
                )
            )

        if negotiation is not None:
            self.session.add(
                TransferNegotiation(
                    id=negotiation["id"],
                    listing_id=listing.id,
                    winning_bid_id=bids[-1][0] if bids else None,
                    player_id=player.id,
                    selling_club_id=selling_club.id,
                    bidder_club_id=negotiation["bidder_club_id"],
                    status=negotiation["status"],
                    wage_offer_amount=negotiation["wage_offer_amount"],
                    contract_years=negotiation["contract_years"],
                    expected_role=negotiation["expected_role"],
                    agent_response=negotiation["agent_response"],
                    coach_stance=negotiation["coach_stance"],
                    coach_reason=negotiation["coach_reason"],
                    player_decision_json=negotiation["player_decision_json"],
                    coach_opinion_json=negotiation["coach_opinion_json"],
                    clauses_json={"release_clause_amount": "28500000.0000"},
                    concerns_json=negotiation["concerns_json"],
                    decision_due_at=negotiation["decision_due_at"],
                    metadata_json=negotiation["metadata_json"],
                )
            )

    def _replace_federation_bundle(
        self,
        *,
        federation_id: str,
        league_id: str,
        competition_id: str,
        proposal_id: str,
        vote_id: str,
        sanction_id: str,
        treasury_id: str,
        owner: User,
        club: ClubProfile,
        member_clubs: tuple[ClubProfile, ...],
        region_code: str,
        region_label: str,
        name: str,
        league_name: str,
        country_code: str,
    ) -> None:
        self.session.execute(delete(FederationVote).where(FederationVote.federation_id == federation_id))
        self.session.execute(delete(FederationProposal).where(FederationProposal.federation_id == federation_id))
        self.session.execute(delete(FederationSanction).where(FederationSanction.federation_id == federation_id))
        self.session.execute(delete(FederationTreasuryEntry).where(FederationTreasuryEntry.federation_id == federation_id))
        self.session.execute(delete(FederationMembership).where(FederationMembership.federation_id == federation_id))
        self.session.execute(delete(FederationLeague).where(FederationLeague.federation_id == federation_id))

        federation = self.session.get(Federation, federation_id)
        if federation is None:
            federation = Federation(id=federation_id, name=name, owner_user_id=owner.id)
            self.session.add(federation)
        federation.name = name
        federation.owner_user_id = owner.id
        federation.structure_json = {
            "tier": "continental",
            "country_anchor": country_code,
            "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
        }
        federation.rules_json = {
            "economy": {"federation_share_bps": 1400},
            "nationality_rules": {"home_country_codes": [country_code], "max_foreign_players": 10},
            "transfer_restrictions": {"max_fee": "75000000.0000"},
        }
        federation.reputation_score = 63.0
        federation.ranking_score = 0.0
        federation.treasury_balance = Decimal("1250000.0000")
        federation.audience_size = 0
        federation.is_public = True
        federation.default_reality_mode = "hybrid"
        federation.metadata_json = {
            "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
            "region_code": region_code,
            "region_label": region_label,
        }
        self.session.flush()

        competition = self.session.get(UserCompetition, competition_id)
        if competition is None:
            competition = UserCompetition(
                id=competition_id,
                host_user_id=owner.id,
                name=league_name,
                description=f"Demo federation competition shell for {name}.",
                competition_type="league",
                format="league",
                visibility="public",
                currency="USD",
            )
            self.session.add(competition)
        competition.host_user_id = owner.id
        competition.name = league_name
        competition.description = f"Demo federation competition shell for {name}."
        competition.competition_type = "league"
        competition.source_type = "federation_league"
        competition.source_id = league_id
        competition.format = "league"
        competition.visibility = "public"
        competition.status = "open"
        competition.currency = "USD"
        competition.gross_pool_minor = 2_400_000
        competition.net_prize_pool_minor = 1_800_000
        competition.metadata_json = {"seed_source": DEMO_WORLD_VISIBILITY_SOURCE, "federation_id": federation.id}
        self.session.flush()

        self.session.add(
            FederationLeague(
                id=league_id,
                federation_id=federation.id,
                linked_competition_id=competition.id,
                name=league_name,
                competition_type="league",
                format="round_robin",
                divisions_json=[{"name": "Premier", "club_slots": len(member_clubs)}],
                promotion_relegation_rules_json={"promotion_slots": 1, "relegation_slots": 1},
                entry_requirements_json={"founding_year_max": 2024},
                governance_rules_override_json={},
                season_label=str(datetime.now(UTC).year),
                status="active",
                metadata_json={"seed_source": DEMO_WORLD_VISIBILITY_SOURCE},
            )
        )

        for offset, member_club in enumerate(member_clubs, start=1):
            self.session.add(
                FederationMembership(
                    id=f"00000000-0000-0000-0000-{int(federation_id[-3:]) * 10 + offset:012d}",
                    federation_id=federation.id,
                    club_id=member_club.id,
                    user_id=member_club.owner_user_id,
                    role="member_club",
                    status=FederationMembershipStatus.ACTIVE.value,
                    entry_requirements_json={},
                    metadata_json={"seed_source": DEMO_WORLD_VISIBILITY_SOURCE},
                )
            )

        self.session.add(
            FederationProposal(
                id=proposal_id,
                federation_id=federation.id,
                league_id=league_id,
                proposer_user_id=owner.id,
                proposal_type="rule_change",
                title="Adjust federation share ladder",
                summary="Demo governance proposal keeping the live governance table populated.",
                payload_json={"rules_patch": {"economy": {"federation_share_bps": 1500}}},
                status=FederationProposalStatus.OPEN.value,
                voting_starts_at=datetime.now(UTC) - timedelta(hours=12),
                voting_ends_at=datetime.now(UTC) + timedelta(days=2),
                yes_votes=2,
                no_votes=0,
                abstain_votes=0,
                metadata_json={"seed_source": DEMO_WORLD_VISIBILITY_SOURCE},
            )
        )
        self.session.add(
            FederationVote(
                id=vote_id,
                proposal_id=proposal_id,
                federation_id=federation.id,
                user_id=owner.id,
                vote_type=FederationVoteType.YES.value,
                weight=2,
                comment="Seeded vote to populate the live governance rail.",
                metadata_json={"seed_source": DEMO_WORLD_VISIBILITY_SOURCE},
            )
        )
        self.session.add(
            FederationSanction(
                id=sanction_id,
                federation_id=federation.id,
                league_id=league_id,
                club_id=club.id,
                player_id=None,
                applied_by_user_id=owner.id,
                sanction_type="fine",
                reason="Late documentation filing during the seeded visibility cycle.",
                fine_amount=Decimal("125000.0000"),
                points_deduction=0,
                suspension_matches=0,
                starts_at=datetime.now(UTC) - timedelta(days=1),
                ends_at=datetime.now(UTC) + timedelta(days=3),
                status="active",
                metadata_json={"seed_source": DEMO_WORLD_VISIBILITY_SOURCE},
            )
        )
        self.session.add(
            FederationTreasuryEntry(
                id=treasury_id,
                federation_id=federation.id,
                source_type="broadcast_rights",
                source_reference=f"demo-broadcast-{region_code}",
                gross_amount=Decimal("2400000.0000"),
                federation_share=Decimal("360000.0000"),
                club_distribution_json=[
                    {"club_id": member_club.id, "amount": "680000.0000"}
                    for member_club in member_clubs
                ],
                metadata_json={"seed_source": DEMO_WORLD_VISIBILITY_SOURCE},
            )
        )

        service = FederationService(self.session)
        service._sync_snapshot_fields(federation)
        service.generate_narratives(federation.id)
        service.refresh_rankings()

    def _national_team_squad(self, *, country_code: str) -> list[dict[str, Any]]:
        seeds = list(
            self.session.scalars(
                select(NationalRegenSeed)
                .where(
                    NationalRegenSeed.country_code == country_code,
                    NationalRegenSeed.preseed_batch == DEMO_WORLD_VISIBILITY_BATCH,
                )
                .order_by(
                    NationalRegenSeed.current_rating.desc(),
                    NationalRegenSeed.potential_rating.desc(),
                    NationalRegenSeed.display_name.asc(),
                )
                .limit(18)
            ).all()
        )
        if len(seeds) < 18:
            raise ValueError(
                f"Demo visibility expected at least 18 national regen seeds for '{country_code}'."
            )

        squad: list[dict[str, Any]] = []
        for shirt_number, seed in enumerate(seeds, start=1):
            metadata = dict(seed.metadata_json or {})
            age_value = metadata.get("age")
            age = age_value if isinstance(age_value, int) else None
            squad.append(
                {
                    "player_name": seed.display_name,
                    "age": age,
                    "overall_rating": seed.current_rating,
                    "position": seed.primary_position,
                    "metadata_json": {
                        "seed_key": seed.seed_key,
                        "seed_type": seed.seed_type,
                        "country_code": seed.country_code,
                        "preseed_batch": seed.preseed_batch,
                        "shirt_number": shirt_number,
                        "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
                    },
                }
            )
        return squad

    def _upsert_national_team_theme(self, *, competition: NationalTeamCompetition) -> None:
        theme = self.session.get(TournamentTheme, _NATIONAL_TEAM_THEME_ID)
        if theme is None:
            theme = self.session.scalar(
                select(TournamentTheme).where(TournamentTheme.competition_id == competition.id)
            )
        if theme is None:
            theme = TournamentTheme(id=_NATIONAL_TEAM_THEME_ID, competition_id=competition.id)
            self.session.add(theme)

        theme.competition_id = competition.id
        theme.video_asset_url = "https://assets.gtex.local/themes/u17-world-cup/hero.mp4"
        theme.audio_theme_url = "https://assets.gtex.local/themes/u17-world-cup/theme.mp3"
        theme.visual_style = "gtex_u17_world_feed"
        theme.metadata_json = {
            "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
            "headline": "Round 1 is open",
            "strapline": "Fast Cup countdown takes the banner slot.",
        }

    def _upsert_national_team_ad(
        self,
        *,
        competition: NationalTeamCompetition,
        reference_at: datetime,
    ) -> None:
        ad = self.session.get(StadiumAd, _NATIONAL_TEAM_AD_ID)
        if ad is None:
            ad = StadiumAd(id=_NATIONAL_TEAM_AD_ID, competition_id=competition.id, asset_url="")
            self.session.add(ad)

        ad.competition_id = competition.id
        ad.asset_url = "https://assets.gtex.local/stadium-ads/u17-world-cup-fast-cup.png"
        ad.placement = StadiumAdPlacement.DIGITAL_SCREEN
        ad.start_date = reference_at - timedelta(days=2)
        ad.end_date = reference_at + timedelta(days=14)
        ad.priority = 20
        ad.rotation_interval_seconds = 18
        ad.metadata_json = {
            "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
            "campaign": "fast_cup_countdown",
        }

    def _upsert_national_team_story_event(self, *, competition: NationalTeamCompetition) -> None:
        story = self.session.get(StoryEvent, _NATIONAL_TEAM_STORY_ID)
        if story is None:
            story = StoryEvent(id=_NATIONAL_TEAM_STORY_ID, competition_id=competition.id)
            self.session.add(story)

        story.competition_id = competition.id
        story.match_id = None
        story.type = StoryEventType.STAR_BREAKOUT
        story.entities = {
            "competition_id": competition.id,
            "seed_batch": DEMO_WORLD_VISIBILITY_BATCH,
            "focus_country_codes": ["NG", "BR", "ES"],
        }
        story.narrative_text = (
            "Club and academy generation feeds are live, and the seeded U17 national"
            " competition now has breakout storylines for the presentation rail."
        )
        story.metadata_json = {
            "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
            "priority": "featured",
        }

    def _upsert_country_rankings(
        self,
        *,
        competition: NationalTeamCompetition,
        countries: list[Country],
    ) -> None:
        for index, country in enumerate(countries, start=1):
            code = self._country_code(country)
            ranking = self.session.scalar(
                select(NationalTeamCountryRanking).where(NationalTeamCountryRanking.country_code == code)
            )
            if ranking is None:
                ranking = NationalTeamCountryRanking(country_code=code, country_name=country.name)
                self.session.add(ranking)

            ranking.country_name = country.name
            ranking.elo_rating = 1665.0 - (index * 23.0)
            ranking.matches_played = 12 + index
            ranking.wins = 8 + max(0, 3 - index)
            ranking.draws = 2
            ranking.losses = max(1, index - 1)
            ranking.titles = 1 if index == 1 else 0
            ranking.last_competition_id = competition.id
            ranking.metadata_json = {
                "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
                "competition_key": competition.key,
                "highlighted": index == 1,
            }

    def _upsert_player_decision_profile(self, player: Player, *, preferred_country_code: str) -> None:
        profile = self.session.scalar(
            select(PlayerDecisionProfile).where(PlayerDecisionProfile.player_id == player.id)
        )
        if profile is None:
            profile = PlayerDecisionProfile(player_id=player.id)
            self.session.add(profile)

        transfer_value = self._transfer_price(player, factor="1.00")
        profile.preferred_leagues_json = [
            f"{preferred_country_code}_elite",
            "continental_showcase",
        ]
        profile.preferred_play_style = "progressive"
        profile.wage_expectation_amount = max(
            Decimal("18000.0000"),
            (transfer_value / Decimal("145")).quantize(Decimal("0.0001")),
        )
        profile.ambition_level = 74
        profile.happiness = 68.0
        profile.loyalty = 54.0
        profile.ambition = 79.0
        profile.frustration = 21.0
        profile.metadata_json = {
            "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
            "preferred_country_code": preferred_country_code,
        }

    def _upsert_coach_profile(self, *, club: ClubProfile, tactical_philosophy: str) -> None:
        profile = self.session.scalar(select(CoachProfile).where(CoachProfile.club_id == club.id))
        if profile is None:
            profile = CoachProfile(club_id=club.id)
            self.session.add(profile)

        profile.personality_json = {
            "composure": 74,
            "adaptability": 71,
            "media_temperature": "measured",
        }
        profile.tactical_philosophy = tactical_philosophy
        profile.authority_level = 73.0 if tactical_philosophy == "pressing" else 67.0
        profile.transfer_preference = "targeted"
        profile.metadata_json = {
            "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
            "club_slug": club.slug,
        }
        self.session.flush()

        demand = self.session.scalar(
            select(CoachDemand).where(
                CoachDemand.club_id == club.id,
                CoachDemand.need == "Left-sided creation",
            )
        )
        if demand is None:
            demand = CoachDemand(club_id=club.id, coach_profile_id=profile.id, need="Left-sided creation")
            self.session.add(demand)
        demand.coach_profile_id = profile.id
        demand.urgency = "high" if tactical_philosophy == "pressing" else "medium"
        demand.active = True
        demand.metadata_json = {
            "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
            "club_slug": club.slug,
        }

    def _upsert_team_dynamics(self, *, club: ClubProfile, leader_player_ids: list[str]) -> None:
        dynamics = self.session.scalar(
            select(ClubTeamDynamics).where(ClubTeamDynamics.club_id == club.id)
        )
        if dynamics is None:
            dynamics = ClubTeamDynamics(club_id=club.id)
            self.session.add(dynamics)

        leaders = leader_player_ids[:2]
        dynamics.leaders_json = leaders
        dynamics.cliques_json = [
            {
                "name": "Leadership spine",
                "player_ids": leaders,
            }
        ]
        dynamics.morale_groups_json = [
            {
                "label": "first_team",
                "score": 78,
                "player_ids": leader_player_ids,
            }
        ]
        dynamics.chemistry_risk = 18.0
        dynamics.metadata_json = {
            "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
            "leader_count": len(leaders),
        }

    def _upsert_player_coach_relationship(self, player: Player, *, club: ClubProfile) -> None:
        relationship = self.session.scalar(
            select(PlayerCoachRelationship).where(
                PlayerCoachRelationship.player_id == player.id,
                PlayerCoachRelationship.club_id == club.id,
            )
        )
        if relationship is None:
            relationship = PlayerCoachRelationship(player_id=player.id, club_id=club.id)
            self.session.add(relationship)

        relationship.relationship_score = 76.0
        relationship.integration_success_modifier = 8.0
        relationship.conflict_level = 12.0
        relationship.metadata_json = {
            "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
            "club_slug": club.slug,
        }

    def _upsert_watchlist_entry(
        self,
        *,
        club: ClubProfile,
        player: Player,
        source: str,
        discovery_score: float,
        listing_id: str | None = None,
    ) -> None:
        watchlist = self.session.scalar(
            select(MarketWatchlistEntry).where(
                MarketWatchlistEntry.club_id == club.id,
                MarketWatchlistEntry.player_id == player.id,
            )
        )
        if watchlist is None:
            watchlist = MarketWatchlistEntry(club_id=club.id, player_id=player.id)
            self.session.add(watchlist)

        watchlist.source = source
        watchlist.discovery_score = discovery_score
        watchlist.metadata_json = {
            "seed_source": DEMO_WORLD_VISIBILITY_SOURCE,
            "listing_id": listing_id,
        }
        self.session.flush()

        if listing_id:
            listing = self.session.get(TransferListing, listing_id)
            if listing is not None:
                listing.watchlist_count = self._watchlist_count(player.id)

    def _watchlist_count(self, player_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(MarketWatchlistEntry)
                .where(MarketWatchlistEntry.player_id == player_id)
            )
            or 0
        )

    def _build_summary(self) -> DemoWorldVisibilitySummary:
        club_ids = tuple(_DEMO_CLUB_IDS.values())
        federation_ids = (
            "00000000-0000-0000-0000-000000000201",
            "00000000-0000-0000-0000-000000000202",
            "00000000-0000-0000-0000-000000000203",
        )

        club_count = int(
            self.session.scalar(
                select(func.count()).select_from(ClubProfile).where(ClubProfile.id.in_(club_ids))
            )
            or 0
        )
        marketplace_listing_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(AgentMarketplaceListing)
                .join(Player, Player.id == AgentMarketplaceListing.player_id)
                .where(Player.current_club_profile_id.in_(club_ids))
            )
            or 0
        )
        transfer_listing_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(TransferListing)
                .where(TransferListing.id.in_(tuple(_TRANSFER_LISTING_IDS.values())))
            )
            or 0
        )
        transfer_bid_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(TransferListingBid)
                .where(TransferListingBid.id.in_(tuple(_TRANSFER_BID_IDS.values())))
            )
            or 0
        )
        transfer_negotiation_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(TransferNegotiation)
                .where(TransferNegotiation.id == _TRANSFER_NEGOTIATION_ID)
            )
            or 0
        )
        federation_count = int(
            self.session.scalar(
                select(func.count()).select_from(Federation).where(Federation.id.in_(federation_ids))
            )
            or 0
        )
        federation_membership_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(FederationMembership)
                .where(FederationMembership.federation_id.in_(federation_ids))
            )
            or 0
        )
        federation_league_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(FederationLeague)
                .where(FederationLeague.federation_id.in_(federation_ids))
            )
            or 0
        )
        national_team_competition_count = int(
            self.session.scalar(select(func.count()).select_from(NationalTeamCompetition))
            or 0
        )
        national_team_entry_count = int(
            self.session.scalar(select(func.count()).select_from(NationalTeamCompetitionEntry))
            or 0
        )
        national_team_ranking_count = int(
            self.session.scalar(select(func.count()).select_from(NationalTeamCountryRanking))
            or 0
        )
        national_regen_seed_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(NationalRegenSeed)
                .where(NationalRegenSeed.preseed_batch == DEMO_WORLD_VISIBILITY_BATCH)
            )
            or 0
        )
        regen_season_count = int(
            self.session.scalar(select(func.count()).select_from(RegenSeason))
            or 0
        )
        regen_award_definition_count = int(
            self.session.scalar(select(func.count()).select_from(RegenAward))
            or 0
        )
        return DemoWorldVisibilitySummary(
            club_count=club_count,
            marketplace_listing_count=marketplace_listing_count,
            transfer_listing_count=transfer_listing_count,
            transfer_bid_count=transfer_bid_count,
            transfer_negotiation_count=transfer_negotiation_count,
            federation_count=federation_count,
            federation_membership_count=federation_membership_count,
            federation_league_count=federation_league_count,
            national_team_competition_count=national_team_competition_count,
            national_team_entry_count=national_team_entry_count,
            national_team_ranking_count=national_team_ranking_count,
            national_regen_seed_count=national_regen_seed_count,
            regen_season_count=regen_season_count,
            regen_award_definition_count=regen_award_definition_count,
        )

    def _country_code(self, country: Country | None) -> str:
        if country is None:
            raise ValueError("Demo visibility requires a country record.")
        for value in (country.alpha2_code, country.fifa_code, country.alpha3_code, country.name):
            if not value:
                continue
            normalized = "".join(character for character in str(value).upper() if character.isalnum())
            if normalized:
                return normalized[:8]
        raise ValueError(f"Country '{country.id}' is missing a usable code.")

    def _transfer_price(self, player: Player, *, factor: str) -> Decimal:
        base_value = Decimal(
            str(
                player.current_market_reference_value
                or player.market_value_eur
                or 7_500_000
            )
        )
        return max(
            Decimal("150000.00"),
            (base_value * Decimal(factor)).quantize(Decimal("0.01")),
        )


def seed_world_visibility_data(
    *,
    database_url: str = DEFAULT_DATABASE_URL,
    provider_name: str = DEFAULT_DEMO_PROVIDER_NAME,
) -> DemoWorldVisibilitySummary:
    engine = create_database_engine(database_url)
    try:
        ensure_database_schema_current(engine)
        session_factory = create_session_factory(engine)
        with session_factory() as session:
            return DemoWorldVisibilitySeeder(session).seed(provider_name=provider_name)
    finally:
        engine.dispose()


__all__ = [
    "DEMO_WORLD_VISIBILITY_BATCH",
    "DEMO_WORLD_VISIBILITY_SOURCE",
    "DemoWorldVisibilitySeeder",
    "DemoWorldVisibilitySummary",
    "seed_world_visibility_data",
]
