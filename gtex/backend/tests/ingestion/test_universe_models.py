from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.ingestion.models import (
    Club,
    Competition,
    Country,
    ImageModerationStatus,
    InternalLeague,
    InternalLeagueCode,
    LiquidityBand,
    Player,
    PlayerImageMetadata,
    PlayerVerification,
    Season,
    SupplyTier,
    VerificationStatus,
)


def _build_universe_entities():
    internal_league = InternalLeague(
        code=InternalLeagueCode.LEAGUE_A.value,
        name="League A",
        rank=1,
        competition_multiplier=1.20,
        visibility_weight=1.00,
        description="Top internal league",
    )
    supply_tier = SupplyTier(
        code="elite",
        name="Elite",
        rank=1,
        min_score=0.90,
        max_score=1.00,
        target_share=0.04,
        circulating_supply=180,
        daily_pack_supply=4,
        season_mint_cap=260,
    )
    liquidity_band = LiquidityBand(
        code="premium",
        name="Premium",
        rank=1,
        min_price_credits=150,
        max_price_credits=399,
        max_spread_bps=700,
        maker_inventory_target=120,
        instant_sell_fee_bps=850,
    )
    country = Country(
        source_provider="manual",
        provider_external_id="country-ng",
        name="Nigeria",
        alpha2_code="NG",
        alpha3_code="NGA",
        fifa_code="NGA",
        confederation_code="CAF",
        market_region="africa",
    )
    competition = Competition(
        source_provider="manual",
        provider_external_id="competition-1",
        country=country,
        internal_league=internal_league,
        name="Elite Continental League",
        slug="elite-continental-league",
        code="ECL",
        competition_type="league",
        format_type="domestic_league",
        age_bracket="senior",
        domestic_level=1,
        gender="men",
        is_major=True,
        is_tradable=True,
        competition_strength=1.2,
    )
    season = Season(
        source_provider="manual",
        provider_external_id="season-2026",
        competition=competition,
        label="2026/27",
        year_start=2026,
        year_end=2027,
        start_date=date(2026, 8, 1),
        end_date=date(2027, 5, 20),
        is_current=True,
        season_status="active",
        trading_window_opens_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        trading_window_closes_at=datetime(2027, 5, 20, tzinfo=timezone.utc),
        data_completeness_score=0.98,
    )
    club = Club(
        source_provider="manual",
        provider_external_id="club-1",
        country=country,
        current_competition=competition,
        internal_league=internal_league,
        name="Lagos Atlas FC",
        slug="lagos-atlas-fc",
        short_name="Atlas",
        code="LAF",
        gender="men",
        popularity_score=0.82,
        is_tradable=True,
    )
    player = Player(
        source_provider="manual",
        provider_external_id="player-1",
        country=country,
        current_club=club,
        current_competition=competition,
        internal_league=internal_league,
        supply_tier=supply_tier,
        liquidity_band=liquidity_band,
        full_name="Ayo Forward",
        short_name="Ayo",
        position="Forward",
        normalized_position="forward",
        market_value_eur=65_000_000,
        profile_completeness_score=0.96,
        is_tradable=True,
    )
    verification = PlayerVerification(
        player=player,
        status=VerificationStatus.VERIFIED.value,
        verification_source="ops-review",
        verified_at=datetime(2026, 3, 11, tzinfo=timezone.utc),
        confidence_score=0.99,
        rights_confirmed=True,
    )
    image = PlayerImageMetadata(
        source_provider="manual",
        provider_external_id="img-1",
        player=player,
        image_role="portrait",
        source_url="https://images.example.com/ayo-forward.jpg",
        storage_key="players/ayo-forward/portrait.webp",
        width=768,
        height=1024,
        mime_type="image/webp",
        file_size_bytes=182_000,
        checksum_sha256="abc123",
        moderation_status=ImageModerationStatus.APPROVED.value,
        rights_cleared=True,
        is_primary=True,
        last_processed_at=datetime(2026, 3, 11, tzinfo=timezone.utc),
    )
    return internal_league, supply_tier, liquidity_band, country, competition, season, club, player, verification, image


def test_phase_two_universe_models_persist_relationships(session) -> None:
    entities = _build_universe_entities()
    session.add_all(entities)
    session.commit()

    player = session.query(Player).filter_by(provider_external_id="player-1").one()

    assert player.current_competition is not None
    assert player.current_competition.code == "ECL"
    assert player.internal_league is not None
    assert player.internal_league.code == InternalLeagueCode.LEAGUE_A.value
    assert player.supply_tier is not None
    assert player.supply_tier.code == "elite"
    assert player.liquidity_band is not None
    assert player.liquidity_band.code == "premium"
    assert player.verification is not None
    assert player.verification.status == VerificationStatus.VERIFIED.value
    assert player.image_metadata[0].moderation_status == ImageModerationStatus.APPROVED.value
    assert player.country is not None
    assert player.country.fifa_code == "NGA"
    assert player.current_club is not None
    assert player.current_club.current_competition_id == player.current_competition.id


def test_player_verification_is_one_to_one(session) -> None:
    entities = _build_universe_entities()
    session.add_all(entities)
    session.commit()

    player = session.query(Player).filter_by(provider_external_id="player-1").one()
    duplicate_verification = PlayerVerification(
        player_id=player.id,
        status=VerificationStatus.PENDING.value,
    )
    session.add(duplicate_verification)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()


def test_player_image_role_and_catalog_codes_are_unique(session) -> None:
    entities = _build_universe_entities()
    session.add_all(entities)
    session.commit()

    player = session.query(Player).filter_by(provider_external_id="player-1").one()
    duplicate_image_role = PlayerImageMetadata(
        source_provider="manual",
        provider_external_id="img-2",
        player_id=player.id,
        image_role="portrait",
    )
    duplicate_supply_tier = SupplyTier(
        code="elite",
        name="Elite Duplicate",
        rank=9,
        min_score=0.80,
        max_score=0.89,
        target_share=0.05,
        circulating_supply=100,
        daily_pack_supply=2,
        season_mint_cap=120,
    )
    session.add_all([duplicate_image_role, duplicate_supply_tier])

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
