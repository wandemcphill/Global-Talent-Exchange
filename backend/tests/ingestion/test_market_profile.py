from __future__ import annotations

from backend.app.cache.redis_helpers import NullCacheBackend
from backend.app.ingestion.models import Club, Competition, Country, InternalLeague, Player, PlayerSeasonStat
from backend.app.ingestion.repository import IngestionRepository
from backend.app.ingestion.service import IngestionService


def test_market_profile_assigner_gives_obscure_players_lower_supply_and_tighter_liquidity(session) -> None:
    country = Country(
        source_provider="manual",
        provider_external_id="country-1",
        name="England",
    )
    league_a = InternalLeague(
        code="league_a",
        name="League A",
        rank=1,
        competition_multiplier=1.20,
        visibility_weight=1.0,
    )
    league_e = InternalLeague(
        code="league_e",
        name="League E",
        rank=5,
        competition_multiplier=0.85,
        visibility_weight=0.40,
    )
    high_competition = Competition(
        source_provider="manual",
        provider_external_id="competition-high",
        country=country,
        internal_league=league_a,
        name="Global Super League",
        slug="global-super-league",
        competition_type="league",
        competition_strength=1.20,
        is_major=True,
        is_tradable=True,
    )
    low_competition = Competition(
        source_provider="manual",
        provider_external_id="competition-low",
        country=country,
        internal_league=league_e,
        name="Regional Development League",
        slug="regional-development-league",
        competition_type="league",
        competition_strength=0.72,
        is_tradable=True,
    )
    high_club = Club(
        source_provider="manual",
        provider_external_id="club-high",
        country=country,
        current_competition=high_competition,
        internal_league=league_a,
        name="Capital Stars",
        slug="capital-stars",
        popularity_score=0.92,
        is_tradable=True,
    )
    low_club = Club(
        source_provider="manual",
        provider_external_id="club-low",
        country=country,
        current_competition=low_competition,
        internal_league=league_e,
        name="Smalltown United",
        slug="smalltown-united",
        popularity_score=0.08,
        is_tradable=True,
    )
    star_player = Player(
        source_provider="manual",
        provider_external_id="player-star",
        country=country,
        current_club=high_club,
        current_competition=high_competition,
        internal_league=league_a,
        full_name="Elite Star",
        position="Forward",
        normalized_position="forward",
        market_value_eur=95_000_000,
        profile_completeness_score=0.96,
        is_tradable=True,
    )
    obscure_player = Player(
        source_provider="manual",
        provider_external_id="player-obscure",
        country=country,
        current_club=low_club,
        current_competition=low_competition,
        internal_league=league_e,
        full_name="Obscure Prospect",
        position="Midfielder",
        normalized_position="midfielder",
        profile_completeness_score=0.35,
        is_tradable=True,
    )
    session.add_all(
        [
            country,
            league_a,
            league_e,
            high_competition,
            low_competition,
            high_club,
            low_club,
            star_player,
            obscure_player,
        ]
    )
    session.flush()

    session.add_all(
        [
            PlayerSeasonStat(
                source_provider="manual",
                provider_external_id="season-star",
                player_id=star_player.id,
                club_id=high_club.id,
                competition_id=high_competition.id,
                appearances=31,
                starts=30,
                minutes=2_710,
                goals=19,
                assists=11,
                average_rating=8.3,
            ),
            PlayerSeasonStat(
                source_provider="manual",
                provider_external_id="season-obscure",
                player_id=obscure_player.id,
                club_id=low_club.id,
                competition_id=low_competition.id,
                appearances=4,
                starts=2,
                minutes=255,
                goals=0,
                assists=0,
                average_rating=6.1,
            ),
        ]
    )
    session.flush()

    repository = IngestionRepository(session)
    repository.refresh_player_market_profiles({star_player.id, obscure_player.id})
    session.refresh(star_player)
    session.refresh(obscure_player)

    assert star_player.supply_tier is not None
    assert obscure_player.supply_tier is not None
    assert star_player.liquidity_band is not None
    assert obscure_player.liquidity_band is not None
    assert obscure_player.supply_tier.circulating_supply < star_player.supply_tier.circulating_supply
    assert obscure_player.liquidity_band.maker_inventory_target < star_player.liquidity_band.maker_inventory_target
    assert obscure_player.liquidity_band.instant_sell_fee_bps > star_player.liquidity_band.instant_sell_fee_bps


def test_bootstrap_sync_assigns_supply_and_liquidity_to_mock_players(session) -> None:
    service = IngestionService(session, cache_backend=NullCacheBackend())

    service.bootstrap_sync(provider_name="mock")
    session.commit()

    players = session.query(Player).all()

    assert players
    assert all(player.supply_tier is not None for player in players)
    assert all(player.liquidity_band is not None for player in players)
