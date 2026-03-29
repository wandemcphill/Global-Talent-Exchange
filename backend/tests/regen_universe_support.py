from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, configure_mappers, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ingestion.models import (
    Competition,
    Club,
    Country,
    InternalLeague,
    Match,
    Player,
    PlayerMatchStat,
    PlayerSeasonStat,
    Season as IngestionSeason,
    TeamStanding,
)
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.player_contract import PlayerContract
from app.models.player_career_entry import PlayerCareerEntry
from app.models.player_lifecycle_event import PlayerLifecycleEvent
from app.models.player_rivalry import PlayerRivalry
from app.models.player_story import PlayerStory
from app.models.player_cards import PlayerCard, PlayerCardListing, PlayerCardSale, PlayerCardTier
from app.models.regen import (
    RegenAward as MarketRegenAward,
    RegenDemandSignal,
    RegenDiscoveryBadge,
    RegenLegacyRecord,
    RegenLineageProfile,
    RegenMarketActivity,
    RegenOnboardingFlag,
    RegenOriginMetadata,
    RegenPersonalityProfile,
    RegenProfile,
    RegenRecommendationItem,
    RegenRelationshipTag,
    RegenScoutReport,
    RegenTransferFeeRule,
    RegenTwinsGroup,
    RegenValueSnapshot,
)
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.user import User
from app.models.story_feed import StoryFeedItem
from app.players.read_models import PlayerSummaryReadModel
from app.regen_universe.models import (
    RegenAward,
    RegenAwardWinner,
    RegenHallOfFame,
    RegenPerformanceRecord,
    RegenRankingSnapshot,
    RegenSeason,
)
from app.regen_universe.service import RegenUniverseService


def build_regen_universe_session() -> Session:
    configure_mappers()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            ClubProfile.__table__,
            Country.__table__,
            InternalLeague.__table__,
            Competition.__table__,
            IngestionSeason.__table__,
            Club.__table__,
            Match.__table__,
            TeamStanding.__table__,
            Player.__table__,
            PlayerContract.__table__,
            PlayerCareerEntry.__table__,
            PlayerLifecycleEvent.__table__,
            PlayerRivalry.__table__,
            PlayerStory.__table__,
            PlayerCardTier.__table__,
            PlayerCard.__table__,
            PlayerCardListing.__table__,
            PlayerCardSale.__table__,
            RegenProfile.__table__,
            RegenPersonalityProfile.__table__,
            RegenOriginMetadata.__table__,
            RegenLineageProfile.__table__,
            RegenRelationshipTag.__table__,
            RegenDiscoveryBadge.__table__,
            MarketRegenAward.__table__,
            RegenLegacyRecord.__table__,
            RegenOnboardingFlag.__table__,
            RegenRecommendationItem.__table__,
            RegenTransferFeeRule.__table__,
            RegenTwinsGroup.__table__,
            RegenValueSnapshot.__table__,
            RegenMarketActivity.__table__,
            RegenDemandSignal.__table__,
            RegenScoutReport.__table__,
            NationalRegenSeed.__table__,
            PlayerSummaryReadModel.__table__,
            StoryFeedItem.__table__,
            PlayerSeasonStat.__table__,
            PlayerMatchStat.__table__,
            RegenSeason.__table__,
            RegenAward.__table__,
            RegenPerformanceRecord.__table__,
            RegenRankingSnapshot.__table__,
            RegenAwardWinner.__table__,
            RegenHallOfFame.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return session_factory()


def seed_two_season_universe(session: Session) -> dict[str, object]:
    owner = User(
        id="user-owner",
        email="owner@example.com",
        username="owner",
        password_hash="hashed",
        full_name="Owner User",
    )
    session.add(owner)
    country = Country(
        id="country-ng",
        source_provider="test",
        provider_external_id="country-ng",
        name="Nigeria",
        alpha2_code="NG",
        alpha3_code="NGA",
        fifa_code="NGA",
        confederation_code="CAF",
        market_region="africa",
        is_enabled_for_universe=True,
    )
    session.add(country)
    club_profile = ClubProfile(
        id="club-profile-1",
        owner_user_id=owner.id,
        club_name="Prestige FC",
        short_name="PFC",
        slug="prestige-fc",
        primary_color="#003366",
        secondary_color="#ffffff",
        accent_color="#ffcc00",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        visibility="public",
    )
    session.add(club_profile)
    tier = PlayerCardTier(
        id="tier-rare",
        code="RARE",
        name="Rare",
        rarity_rank=1,
    )
    session.add(tier)
    league = InternalLeague(
        id="league-top",
        code="L1",
        name="Top Flight",
        rank=1,
        competition_multiplier=1.2,
        visibility_weight=1.1,
    )
    competition = Competition(
        id="competition-premier",
        source_provider="test",
        provider_external_id="competition-premier",
        country_id=country.id,
        internal_league_id=league.id,
        name="Prestige Premier League",
        slug="prestige-premier-league",
        code="PPL",
        is_major=False,
        competition_strength=82.0,
    )
    prestige_club = Club(
        id="club-prestige",
        source_provider="test",
        provider_external_id="club-prestige",
        country_id=country.id,
        current_competition_id=competition.id,
        internal_league_id=league.id,
        name="Prestige United",
        slug="prestige-united",
        short_name="PUN",
        code="PUN",
    )
    ingestion_season_one = IngestionSeason(
        id="ingestion-season-1",
        source_provider="test",
        provider_external_id="ingestion-season-1",
        competition_id=competition.id,
        label="2025/2026",
        start_date=date(2025, 8, 1),
        end_date=date(2026, 5, 31),
        is_current=False,
    )
    ingestion_season_two = IngestionSeason(
        id="ingestion-season-2",
        source_provider="test",
        provider_external_id="ingestion-season-2",
        competition_id=competition.id,
        label="2026/2027",
        start_date=date(2026, 8, 1),
        end_date=date(2027, 5, 31),
        is_current=True,
    )
    session.add_all([league, competition, prestige_club, ingestion_season_one, ingestion_season_two])

    players = {
        "veteran": _create_regen_player(
            session,
            player_id="player-veteran",
            regen_id="regen-veteran",
            name="Victor Veteran",
            birth_date=date(1998, 3, 14),
            position="ST",
            normalized_position="forward",
            club_profile_id=club_profile.id,
            tier_id=tier.id,
        ),
        "wonderkid": _create_regen_player(
            session,
            player_id="player-wonderkid",
            regen_id="regen-wonderkid",
            name="Kelechi Wonderkid",
            birth_date=date(2006, 4, 10),
            position="ST",
            normalized_position="forward",
            club_profile_id=club_profile.id,
            tier_id=tier.id,
        ),
        "playmaker": _create_regen_player(
            session,
            player_id="player-playmaker",
            regen_id="regen-playmaker",
            name="Musa Playmaker",
            birth_date=date(2002, 9, 5),
            position="CM",
            normalized_position="midfielder",
            club_profile_id=club_profile.id,
            tier_id=tier.id,
        ),
        "defender": _create_regen_player(
            session,
            player_id="player-defender",
            regen_id="regen-defender",
            name="David Defender",
            birth_date=date(2000, 6, 7),
            position="CB",
            normalized_position="defender",
            club_profile_id=club_profile.id,
            tier_id=tier.id,
        ),
        "keeper": _create_regen_player(
            session,
            player_id="player-keeper",
            regen_id="regen-keeper",
            name="Gabriel Gloves",
            birth_date=date(1999, 1, 22),
            position="GK",
            normalized_position="goalkeeper",
            club_profile_id=club_profile.id,
            tier_id=tier.id,
        ),
        "breakout": _create_regen_player(
            session,
            player_id="player-breakout",
            regen_id="regen-breakout",
            name="Tunde Breakout",
            birth_date=date(2005, 12, 2),
            position="RW",
            normalized_position="forward",
            club_profile_id=club_profile.id,
            tier_id=tier.id,
        ),
    }

    season_one_stats = {
        "veteran": {"appearances": 26, "starts": 24, "minutes": 2240, "goals": 18, "assists": 6, "average_rating": 7.6},
        "wonderkid": {"appearances": 25, "starts": 22, "minutes": 2060, "goals": 17, "assists": 8, "average_rating": 7.4},
        "playmaker": {"appearances": 24, "starts": 23, "minutes": 2140, "goals": 4, "assists": 14, "average_rating": 7.5},
        "defender": {"appearances": 28, "starts": 28, "minutes": 2520, "goals": 2, "assists": 2, "clean_sheets": 12, "average_rating": 7.4},
        "keeper": {"appearances": 28, "starts": 28, "minutes": 2520, "clean_sheets": 14, "saves": 85, "average_rating": 7.5},
        "breakout": {"appearances": 18, "starts": 10, "minutes": 940, "goals": 2, "assists": 3, "average_rating": 6.7},
    }
    season_two_stats = {
        "veteran": {"appearances": 31, "starts": 31, "minutes": 2790, "goals": 30, "assists": 8, "average_rating": 7.9},
        "wonderkid": {"appearances": 30, "starts": 29, "minutes": 2660, "goals": 22, "assists": 10, "average_rating": 7.7},
        "playmaker": {"appearances": 31, "starts": 31, "minutes": 2780, "goals": 6, "assists": 18, "average_rating": 7.8},
        "defender": {"appearances": 32, "starts": 32, "minutes": 2880, "goals": 1, "assists": 4, "clean_sheets": 18, "average_rating": 7.6},
        "keeper": {"appearances": 32, "starts": 32, "minutes": 2880, "clean_sheets": 20, "saves": 102, "average_rating": 7.7},
        "breakout": {"appearances": 29, "starts": 25, "minutes": 2360, "goals": 18, "assists": 12, "average_rating": 7.8},
    }
    for label, stats in season_one_stats.items():
        _create_season_stats(
            session,
            player=players[label],
            competition_id=competition.id,
            season_id=ingestion_season_one.id,
            provider_external_id=f"{players[label].id}-season-1",
            **stats,
        )
    for label, stats in season_two_stats.items():
        _create_season_stats(
            session,
            player=players[label],
            competition_id=competition.id,
            season_id=ingestion_season_two.id,
            provider_external_id=f"{players[label].id}-season-2",
            **stats,
        )
    session.add(
        TeamStanding(
            id="standing-prestige-title",
            source_provider="test",
            provider_external_id="standing-prestige-title",
            competition_id=competition.id,
            season_id=ingestion_season_two.id,
            club_id=prestige_club.id,
            standing_type="total",
            position=1,
            played=38,
            won=28,
            drawn=6,
            lost=4,
            goals_for=88,
            goals_against=31,
            goal_difference=57,
            points=90,
        )
    )
    session.flush()

    service = RegenUniverseService(session)
    service.seed_defaults()
    first_regen_season = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
    assert first_regen_season is not None
    first_regen_season.start_date = ingestion_season_one.start_date
    first_regen_season.end_date = ingestion_season_one.end_date
    first_regen_season.metadata_json = {"source_ingestion_season_ids": [ingestion_season_one.id]}
    session.flush()
    return {
        "service": service,
        "players": players,
        "ingestion_season_one": ingestion_season_one,
        "ingestion_season_two": ingestion_season_two,
        "club_profile": club_profile,
        "competition": competition,
        "country": country,
        "club": prestige_club,
    }


def seed_tied_ranking_universe(session: Session) -> dict[str, object]:
    bundle = seed_two_season_universe(session)
    service: RegenUniverseService = bundle["service"]
    first_season = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
    assert first_season is not None
    service.close_season(first_season.id, start_next_season=True)
    second_season = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
    assert second_season is not None
    second_season.start_date = bundle["ingestion_season_two"].start_date
    second_season.end_date = bundle["ingestion_season_two"].end_date
    second_season.metadata_json = {"source_ingestion_season_ids": [bundle["ingestion_season_two"].id]}
    session.flush()

    alpha = _create_regen_player(
        session,
        player_id="player-alpha",
        regen_id="regen-alpha",
        name="Alpha Midfielder",
        birth_date=date(2004, 1, 1),
        position="CM",
        normalized_position="midfielder",
        club_profile_id=bundle["club_profile"].id,
        tier_id="tier-rare",
    )
    beta = _create_regen_player(
        session,
        player_id="player-beta",
        regen_id="regen-beta",
        name="Beta Midfielder",
        birth_date=date(2004, 1, 1),
        position="CM",
        normalized_position="midfielder",
        club_profile_id=bundle["club_profile"].id,
        tier_id="tier-rare",
    )
    for player in (alpha, beta):
        _create_season_stats(
            session,
            player=player,
            competition_id=bundle["competition"].id,
            season_id=bundle["ingestion_season_two"].id,
            provider_external_id=f"{player.id}-season-tie",
            appearances=20,
            starts=18,
            minutes=1800,
            goals=8,
            assists=12,
            average_rating=7.5,
        )
    session.flush()
    bundle["players"]["alpha"] = alpha
    bundle["players"]["beta"] = beta
    bundle["active_regen_season"] = second_season
    return bundle


def _create_regen_player(
    session: Session,
    *,
    player_id: str,
    regen_id: str,
    name: str,
    birth_date: date,
    position: str,
    normalized_position: str,
    club_profile_id: str,
    tier_id: str,
) -> Player:
    player = Player(
        id=player_id,
        source_provider="test",
        provider_external_id=player_id,
        full_name=name,
        position=position,
        normalized_position=normalized_position,
        date_of_birth=birth_date,
        is_real_player=False,
    )
    session.add(player)
    card = PlayerCard(
        id=f"card-{player_id}",
        player_id=player.id,
        tier_id=tier_id,
        edition_code="base",
        display_name=name,
        card_variant="base",
        supply_total=1,
        supply_available=1,
    )
    session.add(card)
    session.add(
        RegenProfile(
            id=f"profile-{player_id}",
            regen_id=regen_id,
            player_id=player.id,
            linked_unique_card_id=card.id,
            generated_for_club_id=club_profile_id,
            birth_country_code="NG",
            birth_region="Lagos",
            birth_city="Lagos",
            primary_position=position,
            secondary_positions_json=[],
            current_gsi=70,
            current_ability_range_json={"minimum": 64, "maximum": 74},
            potential_range_json={"minimum": 76, "maximum": 90},
            scout_confidence="high",
            generation_source="academy",
            metadata_json={},
        )
    )
    session.add(
        RegenPersonalityProfile(
            regen_profile_id=f"profile-{player_id}",
            temperament=56,
            leadership=61,
            ambition=74,
            loyalty=49,
            work_rate=68,
            flair=72 if normalized_position in {"forward", "midfielder"} else 48,
            resilience=66,
            personality_tags_json=["composed", "upside"],
        )
    )
    session.add(
        RegenOriginMetadata(
            regen_profile_id=f"profile-{player_id}",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
            hometown_club_affinity="Prestige FC",
            ethnolinguistic_profile="yoruba",
            religion_naming_pattern="mixed",
            urbanicity="urban",
            metadata_json={},
        )
    )
    return player


def _create_season_stats(
    session: Session,
    *,
    player: Player,
    competition_id: str,
    season_id: str,
    provider_external_id: str,
    appearances: int,
    starts: int,
    minutes: int,
    goals: int = 0,
    assists: int = 0,
    clean_sheets: int = 0,
    saves: int = 0,
    average_rating: float | None = None,
) -> None:
    session.add(
        PlayerSeasonStat(
            id=f"stat-{provider_external_id}",
            source_provider="test",
            provider_external_id=provider_external_id,
            player_id=player.id,
            competition_id=competition_id,
            season_id=season_id,
            appearances=appearances,
            starts=starts,
            minutes=minutes,
            goals=goals,
            assists=assists,
            clean_sheets=clean_sheets,
            saves=saves,
            average_rating=average_rating,
        )
    )
