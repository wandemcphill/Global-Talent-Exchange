from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import FastAPI, HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.market.read_models  # noqa: F401
import app.players.read_models  # noqa: F401
import app.value_engine.read_models  # noqa: F401
from app.ingestion.models import (
    Club,
    Competition,
    Country,
    LiquidityBand,
    Player,
    PlayerImageMetadata,
    SupplyTier,
)

from app.market import (
    ListingStatus,
    ListingType,
    MarketConflictError,
    MarketEngine,
    MarketValidationError,
    OfferStatus,
    TradeIntentDirection,
    TradeIntentStatus,
)
from app.market.router import (
    get_market_player_detail,
    get_market_player_history,
    get_market_browse_catalog,
    list_market_club_players,
    list_market_league_clubs,
    list_market_leagues,
    list_market_national_team_eligible_players,
    list_market_national_teams,
    list_market_nationalities,
    list_market_players,
)
from app.market.repositories import (
    SqlAlchemyMarketPlayerRepository,
    clear_market_records_cache,
)
from app.market.service import MarketPlayerQueryService
from app.models.base import Base
from app.models.transfer_market import TransferListing
from app.players.read_models import PlayerSummaryReadModel
from app.services.runtime_control_service import RuntimeControlService
from app.value_engine.read_models import PlayerValueSnapshotRecord


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _build_market_query_service(
    session,
    *,
    runtime_controls: RuntimeControlService | None = None,
) -> MarketPlayerQueryService:
    return MarketPlayerQueryService(
        session=session,
        today=date(2026, 3, 11),
        runtime_controls=runtime_controls,
    )


def _seed_market_player_catalog(session) -> None:
    country_ng = Country(
        id="country-ng",
        source_provider="synthetic",
        provider_external_id="country-ng",
        name="Nigeria",
        alpha2_code="NG",
        alpha3_code="NGA",
        fifa_code="NGA",
    )
    country_es = Country(
        id="country-es",
        source_provider="synthetic",
        provider_external_id="country-es",
        name="Spain",
        alpha2_code="ES",
        alpha3_code="ESP",
        fifa_code="ESP",
    )
    competition = Competition(
        id="competition-prem",
        source_provider="synthetic",
        provider_external_id="competition-prem",
        name="Premier League",
        slug="premier-league",
        domestic_level=1,
    )
    supply_tier = SupplyTier(
        id="tier-elite",
        code="elite",
        name="Elite",
        rank=1,
        min_score=80.0,
        max_score=100.0,
        target_share=0.1,
        circulating_supply=100,
        daily_pack_supply=10,
        season_mint_cap=500,
    )
    liquidity_band = LiquidityBand(
        id="liquidity-1",
        code="liquid",
        name="Liquid",
        rank=1,
        min_price_credits=50,
        max_price_credits=None,
        max_spread_bps=250,
        maker_inventory_target=20,
        instant_sell_fee_bps=200,
    )
    alpha_fc = Club(
        id="club-alpha",
        source_provider="synthetic",
        provider_external_id="club-alpha",
        country_id=country_ng.id,
        current_competition_id=competition.id,
        name="Alpha FC",
        slug="alpha-fc",
        short_name="Alpha",
        code="ALP",
    )
    beta_united = Club(
        id="club-beta",
        source_provider="synthetic",
        provider_external_id="club-beta",
        country_id=country_es.id,
        current_competition_id=competition.id,
        name="Beta United",
        slug="beta-united",
        short_name="Beta",
        code="BET",
    )
    players = [
        Player(
            id="player-1",
            source_provider="synthetic",
            provider_external_id="player-1",
            country_id=country_ng.id,
            current_club_id=alpha_fc.id,
            current_competition_id=competition.id,
            supply_tier_id=supply_tier.id,
            liquidity_band_id=liquidity_band.id,
            full_name="Ayo Striker",
            first_name="Ayo",
            last_name="Striker",
            short_name="A. Striker",
            position="Forward",
            normalized_position="forward",
            date_of_birth=date(2001, 6, 1),
            preferred_foot="right",
            shirt_number=9,
            height_cm=182,
            weight_kg=78,
            market_value_eur=45_000_000.0,
            is_tradable=True,
        ),
        Player(
            id="player-2",
            source_provider="synthetic",
            provider_external_id="player-2",
            country_id=country_ng.id,
            current_club_id=beta_united.id,
            current_competition_id=competition.id,
            supply_tier_id=supply_tier.id,
            liquidity_band_id=liquidity_band.id,
            full_name="Bola Midfield",
            first_name="Bola",
            last_name="Midfield",
            short_name="B. Midfield",
            position="Midfielder",
            normalized_position="midfielder",
            date_of_birth=date(2006, 6, 20),
            preferred_foot="left",
            shirt_number=8,
            height_cm=176,
            weight_kg=70,
            market_value_eur=38_000_000.0,
            is_tradable=True,
        ),
        Player(
            id="player-3",
            source_provider="synthetic",
            provider_external_id="player-3",
            country_id=country_es.id,
            current_club_id=alpha_fc.id,
            current_competition_id=competition.id,
            supply_tier_id=supply_tier.id,
            liquidity_band_id=liquidity_band.id,
            full_name="Carlos Keeper",
            first_name="Carlos",
            last_name="Keeper",
            short_name="C. Keeper",
            position="Goalkeeper",
            normalized_position="goalkeeper",
            date_of_birth=date(1994, 2, 1),
            preferred_foot="right",
            shirt_number=1,
            height_cm=190,
            weight_kg=84,
            market_value_eur=18_000_000.0,
            is_tradable=True,
        ),
        Player(
            id="player-4",
            source_provider="synthetic",
            provider_external_id="player-4",
            country_id=country_es.id,
            current_club_id=beta_united.id,
            current_competition_id=competition.id,
            supply_tier_id=supply_tier.id,
            liquidity_band_id=liquidity_band.id,
            full_name="Diego Defender",
            first_name="Diego",
            last_name="Defender",
            short_name="D. Defender",
            position="Defender",
            normalized_position="defender",
            date_of_birth=date(1998, 8, 15),
            preferred_foot="right",
            shirt_number=4,
            height_cm=185,
            weight_kg=80,
            market_value_eur=24_000_000.0,
            is_tradable=True,
        ),
    ]
    session.add_all([country_ng, country_es, competition, supply_tier, liquidity_band, alpha_fc, beta_united, *players])
    session.add(
        PlayerImageMetadata(
            id="image-player-1-primary",
            player_id="player-1",
            source_provider="sportmonks",
            provider_external_id="sportmonks-player-1-primary",
            source_url="https://cdn.sportmonks.test/players/player-1.png",
            is_primary=True,
            moderation_status="approved",
        )
    )

    summary_common = {
        "supply_tier": {
            "code": "elite",
            "name": "Elite",
            "circulating_supply": 100,
            "daily_pack_supply": 10,
            "season_mint_cap": 500,
        },
        "liquidity_band": {
            "code": "liquid",
            "name": "Liquid",
            "max_spread_bps": 250,
            "maker_inventory_target": 20,
            "instant_sell_fee_bps": 200,
        },
    }
    nigeria_u20 = {
        "name": "Nigeria",
        "code": "NGA",
        "age_group": "U20",
        "label": "Nigeria U20",
        "kind": "youth",
    }
    spain_u17 = {
        "name": "Spain",
        "code": "ESP",
        "age_group": "U17",
        "label": "Spain U17",
        "kind": "youth",
    }
    session.add_all(
        [
            PlayerSummaryReadModel(
                player_id="player-1",
                player_name="Ayo Striker",
                current_club_id="club-alpha",
                current_club_name="Alpha FC",
                current_competition_id="competition-prem",
                current_competition_name="Premier League",
                last_snapshot_id="snapshot-1b",
                last_snapshot_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
                current_value_credits=220.0,
                previous_value_credits=200.0,
                movement_pct=10.0,
                average_rating=7.6,
                market_interest_score=72,
                summary_json={
                    "position": "forward",
                    "drivers": ["finishing", "momentum"],
                    "football_truth_value_credits": 205.0,
                    "market_signal_value_credits": 15.0,
                    "published_card_value_credits": 220.0,
                    "global_scouting_index": 84.0,
                    "previous_global_scouting_index": 79.0,
                    "global_scouting_index_movement_pct": 6.33,
                    "national_team": nigeria_u20,
                    **summary_common,
                },
            ),
            PlayerSummaryReadModel(
                player_id="player-2",
                player_name="Bola Midfield",
                current_club_id="club-beta",
                current_club_name="Beta United",
                current_competition_id="competition-prem",
                current_competition_name="Premier League",
                last_snapshot_id="snapshot-2a",
                last_snapshot_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
                current_value_credits=180.0,
                previous_value_credits=150.0,
                movement_pct=20.0,
                average_rating=7.9,
                market_interest_score=81,
                summary_json={
                    "position": "midfielder",
                    "drivers": ["creativity", "scouting buzz"],
                    "football_truth_value_credits": 165.0,
                    "market_signal_value_credits": 15.0,
                    "published_card_value_credits": 180.0,
                    "global_scouting_index": 91.0,
                    "previous_global_scouting_index": 83.0,
                    "global_scouting_index_movement_pct": 9.64,
                    "national_team": nigeria_u20,
                    **summary_common,
                },
            ),
            PlayerSummaryReadModel(
                player_id="player-3",
                player_name="Carlos Keeper",
                current_club_id="club-alpha",
                current_club_name="Alpha FC",
                current_competition_id="competition-prem",
                current_competition_name="Premier League",
                last_snapshot_id="snapshot-3a",
                last_snapshot_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
                current_value_credits=90.0,
                previous_value_credits=100.0,
                movement_pct=-10.0,
                average_rating=6.8,
                market_interest_score=44,
                summary_json={
                    "position": "goalkeeper",
                    "drivers": ["shot stopping"],
                    "football_truth_value_credits": 88.0,
                    "market_signal_value_credits": 2.0,
                    "published_card_value_credits": 90.0,
                    "global_scouting_index": 70.0,
                    "previous_global_scouting_index": 72.0,
                    "global_scouting_index_movement_pct": -2.78,
                    "national_team": spain_u17,
                    **summary_common,
                },
            ),
        ]
    )

    session.add_all(
        [
            PlayerValueSnapshotRecord(
                id="snapshot-1a",
                player_id="player-1",
                player_name="Ayo Striker",
                as_of=datetime(2026, 3, 9, tzinfo=timezone.utc),
                previous_credits=190.0,
                target_credits=200.0,
                movement_pct=5.26,
                football_truth_value_credits=188.0,
                market_signal_value_credits=12.0,
                breakdown_json={
                    "published_card_value_credits": 200.0,
                    "global_scouting_index": 79.0,
                    "previous_global_scouting_index": 76.0,
                    "global_scouting_index_movement_pct": 3.95,
                    "holder_count": 12,
                    "top_holder_share_pct": 0.31,
                    "top_3_holder_share_pct": 0.58,
                    "snapshot_market_price_credits": 198.0,
                    "quoted_market_price_credits": 199.5,
                    "trusted_trade_price_credits": 200.0,
                    "trade_trust_score": 0.82,
                },
                drivers_json=["finishing"],
            ),
            PlayerValueSnapshotRecord(
                id="snapshot-1b",
                player_id="player-1",
                player_name="Ayo Striker",
                as_of=datetime(2026, 3, 10, tzinfo=timezone.utc),
                previous_credits=200.0,
                target_credits=220.0,
                movement_pct=10.0,
                football_truth_value_credits=205.0,
                market_signal_value_credits=15.0,
                breakdown_json={
                    "published_card_value_credits": 220.0,
                    "global_scouting_index": 84.0,
                    "previous_global_scouting_index": 79.0,
                    "global_scouting_index_movement_pct": 6.33,
                    "holder_count": 14,
                    "top_holder_share_pct": 0.29,
                    "top_3_holder_share_pct": 0.55,
                    "snapshot_market_price_credits": 219.0,
                    "quoted_market_price_credits": 220.0,
                    "trusted_trade_price_credits": 221.0,
                    "trade_trust_score": 0.88,
                },
                drivers_json=["finishing", "momentum"],
            ),
            PlayerValueSnapshotRecord(
                id="snapshot-2a",
                player_id="player-2",
                player_name="Bola Midfield",
                as_of=datetime(2026, 3, 10, tzinfo=timezone.utc),
                previous_credits=150.0,
                target_credits=180.0,
                movement_pct=20.0,
                football_truth_value_credits=165.0,
                market_signal_value_credits=15.0,
                breakdown_json={
                    "published_card_value_credits": 180.0,
                    "global_scouting_index": 91.0,
                    "previous_global_scouting_index": 83.0,
                    "global_scouting_index_movement_pct": 9.64,
                },
                drivers_json=["creativity", "scouting buzz"],
            ),
            PlayerValueSnapshotRecord(
                id="snapshot-3a",
                player_id="player-3",
                player_name="Carlos Keeper",
                as_of=datetime(2026, 3, 10, tzinfo=timezone.utc),
                previous_credits=100.0,
                target_credits=90.0,
                movement_pct=-10.0,
                football_truth_value_credits=88.0,
                market_signal_value_credits=2.0,
                breakdown_json={
                    "published_card_value_credits": 90.0,
                    "global_scouting_index": 70.0,
                    "previous_global_scouting_index": 72.0,
                    "global_scouting_index_movement_pct": -2.78,
                },
                drivers_json=["shot stopping"],
            ),
        ]
    )
    session.commit()


def test_transfer_listing_requires_ask_price() -> None:
    engine = MarketEngine()

    with pytest.raises(MarketValidationError):
        engine.create_listing(
            asset_id="asset-1",
            seller_user_id="seller-1",
            listing_type=ListingType.TRANSFER,
        )


def test_duplicate_open_listing_for_same_asset_is_rejected() -> None:
    engine = MarketEngine()
    engine.create_listing(
        asset_id="asset-1",
        seller_user_id="seller-1",
        listing_type=ListingType.TRANSFER,
        ask_price=150,
    )

    with pytest.raises(MarketConflictError):
        engine.create_listing(
            asset_id="asset-1",
            seller_user_id="seller-1",
            listing_type=ListingType.TRANSFER,
            ask_price=160,
        )


def test_market_real_player_metadata_uses_summary_and_eur_value_fallback(session) -> None:
    country = Country(
        id="country-eng",
        source_provider="synthetic",
        provider_external_id="country-eng",
        name="England",
        alpha2_code="GB",
        alpha3_code="ENG",
        fifa_code="ENG",
    )
    player = Player(
        id="real-player-sparse",
        source_provider="transfermarkt",
        provider_external_id="real-player-sparse",
        country_id=country.id,
        full_name="Sparse Real Player",
        position="Forward",
        normalized_position="forward",
        date_of_birth=None,
        market_value_eur=12_500_000.0,
        current_market_reference_value=None,
        is_real_player=True,
        is_tradable=True,
    )
    session.add_all([country, player])
    session.add(
        PlayerSummaryReadModel(
            player_id=player.id,
            player_name=player.full_name,
            current_club_id="club-summary-only",
            current_club_name="Summary FC",
            current_competition_id="competition-summary-only",
            current_competition_name="Summary League",
            last_snapshot_id=None,
            last_snapshot_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
            current_value_credits=0.0,
            previous_value_credits=0.0,
            movement_pct=0.0,
            average_rating=None,
            market_interest_score=0,
            summary_json={},
        )
    )
    session.commit()

    result = _build_market_query_service(session).list_players(search="Sparse Real")

    item = result.items[0]
    assert item.player_id == player.id
    assert item.age is None
    assert item.current_club_id == "club-summary-only"
    assert item.current_club_name == "Summary FC"
    assert item.current_competition_id == "competition-summary-only"
    assert item.current_competition_name == "Summary League"
    assert item.market_value_eur == 12_500_000.0
    assert item.current_value_credits is not None
    assert item.current_value_credits > 0

    detail = _build_market_query_service(session).get_player_detail(player.id)
    assert detail.identity.current_club_name == "Summary FC"
    assert detail.identity.current_competition_name == "Summary League"
    assert detail.market_profile.market_value_eur == item.market_value_eur
    assert detail.value.current_value_credits == item.current_value_credits
    assert _build_market_query_service(session).get_player_ticker(player.id).player_id == player.id


def test_listing_offer_counter_accept_flow_completes_listing() -> None:
    engine = MarketEngine()
    listing = engine.create_listing(
        asset_id="asset-1",
        seller_user_id="seller-1",
        listing_type=ListingType.HYBRID,
        ask_price=120,
        desired_asset_ids=("asset-x",),
    )

    initial_offer = engine.create_offer(
        asset_id=listing.asset_id,
        seller_user_id=listing.seller_user_id,
        buyer_user_id="buyer-1",
        listing_id=listing.listing_id,
        cash_amount=90,
        offered_asset_ids=("asset-x",),
    )
    competing_offer = engine.create_offer(
        asset_id=listing.asset_id,
        seller_user_id=listing.seller_user_id,
        buyer_user_id="buyer-2",
        listing_id=listing.listing_id,
        cash_amount=120,
    )

    counter = engine.counter_offer(
        offer_id=initial_offer.offer_id,
        acting_user_id="seller-1",
        cash_amount=110,
        offered_asset_ids=("asset-x",),
    )
    accepted = engine.accept_offer(offer_id=counter.offer_id, acting_user_id="buyer-1")

    assert accepted.status is OfferStatus.ACCEPTED
    assert engine.get_listing(listing.listing_id).status is ListingStatus.COMPLETED
    assert engine.get_offer(initial_offer.offer_id).status is OfferStatus.COUNTERED
    assert engine.get_offer(competing_offer.offer_id).status is OfferStatus.REJECTED


def test_direct_offer_flow_works_without_listing() -> None:
    engine = MarketEngine()

    offer = engine.create_offer(
        asset_id="asset-9",
        seller_user_id="seller-9",
        buyer_user_id="buyer-9",
        cash_amount=75,
    )
    accepted = engine.accept_offer(offer_id=offer.offer_id, acting_user_id="seller-9")

    assert accepted.status is OfferStatus.ACCEPTED
    offers = engine.list_offers_for_asset(asset_id="asset-9", seller_user_id="seller-9")
    assert offers[0].listing_id is None


def test_trade_intent_matches_open_listing_and_is_fulfilled_on_sale() -> None:
    engine = MarketEngine()
    listing = engine.create_listing(
        asset_id="asset-10",
        seller_user_id="seller-10",
        listing_type=ListingType.TRANSFER,
        ask_price=95,
    )
    buy_intent = engine.create_trade_intent(
        user_id="buyer-10",
        asset_id="asset-10",
        direction=TradeIntentDirection.BUY,
        price_ceiling=100,
    )

    matches = engine.match_trade_intents(listing_id=listing.listing_id)
    offer = engine.create_offer(
        asset_id="asset-10",
        seller_user_id="seller-10",
        buyer_user_id="buyer-10",
        listing_id=listing.listing_id,
        cash_amount=95,
    )
    engine.accept_offer(offer_id=offer.offer_id, acting_user_id="seller-10")

    assert [intent.intent_id for intent in matches] == [buy_intent.intent_id]
    assert engine.get_trade_intent(buy_intent.intent_id).status is TradeIntentStatus.FULFILLED


def test_swap_intent_requires_assets_or_cash_ceiling() -> None:
    engine = MarketEngine()

    with pytest.raises(MarketValidationError):
        engine.create_trade_intent(
            user_id="buyer-1",
            asset_id="asset-11",
            direction=TradeIntentDirection.SWAP,
        )


def test_cancelling_listing_rejects_pending_listing_offers() -> None:
    engine = MarketEngine()
    listing = engine.create_listing(
        asset_id="asset-12",
        seller_user_id="seller-12",
        listing_type=ListingType.TRANSFER,
        ask_price=130,
    )
    offer = engine.create_offer(
        asset_id="asset-12",
        seller_user_id="seller-12",
        buyer_user_id="buyer-12",
        listing_id=listing.listing_id,
        cash_amount=130,
    )

    cancelled = engine.cancel_listing(listing_id=listing.listing_id, acting_user_id="seller-12")

    assert cancelled.status is ListingStatus.CANCELLED
    assert engine.get_offer(offer.offer_id).status is OfferStatus.REJECTED


def test_market_player_list_pagination_returns_total_and_window(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(limit=2, offset=1)

    assert payload.total == 4
    assert [item.player_id for item in payload.items] == ["player-2", "player-3"]


def test_market_player_list_includes_primary_image_url(session) -> None:
    _seed_market_player_catalog(session)

    payload = list_market_players(
        limit=20,
        cursor=None,
        offset=0,
        position=None,
        nationality=None,
        national_team=None,
        club=None,
        league=None,
        division=None,
        min_age=None,
        max_age=None,
        min_value=None,
        max_value=None,
        search=None,
        sort="current_value",
        service=_build_market_query_service(session),
    )

    by_id = {item.player_id: item for item in payload.items}
    assert by_id["player-1"].image_url == "https://cdn.sportmonks.test/players/player-1.png"
    assert by_id["player-1"].nationality_code == "NGA"
    assert by_id["player-1"].current_club_id == "club-alpha"
    assert by_id["player-1"].current_competition_id == "competition-prem"
    assert by_id["player-1"].current_competition_name == "Premier League"
    assert by_id["player-1"].current_division_id == "division-1"
    assert by_id["player-1"].current_division_name == "Division 1"
    assert by_id["player-1"].is_tradable is True


def test_market_player_list_filters_transfer_hub_availability_terms(session) -> None:
    _seed_market_player_catalog(session)
    session.add(
        TransferListing(
            id="listing-player-1-loan-to-buy",
            player_id="player-1",
            selling_club_id="club-alpha",
            base_price=Decimal("1250000.00"),
            status="open",
            listing_type="loan_to_buy",
            visibility="public",
            expires_at=datetime(2026, 3, 18, tzinfo=timezone.utc),
            salary_amount=Decimal("25000.00"),
            contract_years_remaining=Decimal("2.50"),
            buy_clause_amount=Decimal("1200000.00"),
            loan_terms_json={"months": 12, "wage_share_pct": 60},
            swap_terms_json={"minimum_rating": 70, "positions": ["midfielder"]},
            availability_json={"loan": True, "swap": True, "loan_to_buy": True},
        )
    )
    session.commit()

    service = _build_market_query_service(session)

    loan_to_buy_payload = service.list_players(availability="loan_to_buy")
    assert [item.player_id for item in loan_to_buy_payload.items] == ["player-1"]
    listed_player = loan_to_buy_payload.items[0]
    assert listed_player.transfer_listing_id == "listing-player-1-loan-to-buy"
    assert listed_player.transfer_listing_status == "open"
    assert listed_player.selling_club_id == "club-alpha"
    assert listed_player.availability_label == "Loan To Buy"
    assert listed_player.asking_type == "loan_to_buy"
    assert listed_player.salary_amount == 25000.0
    assert listed_player.contract_years_remaining == 2.5
    assert listed_player.buy_clause_amount == 1200000.0
    assert listed_player.loan_terms == {"months": 12, "wage_share_pct": 60}
    assert listed_player.swap_terms == {"minimum_rating": 70, "positions": ["midfielder"]}
    assert listed_player.availability == {"loan": True, "swap": True, "loan_to_buy": True}

    transfer_payload = service.list_players(availability="transfer")
    assert transfer_payload.items == ()

    all_players = service.list_players()
    unlisted_player = next(item for item in all_players.items if item.player_id == "player-2")
    assert unlisted_player.transfer_listing_id is None
    assert unlisted_player.availability_label == "Transfer eligible"
    assert unlisted_player.asking_type == "transfer_eligible"


def test_market_browse_catalog_counts_full_tradeable_universe(session) -> None:
    _seed_market_player_catalog(session)

    payload = get_market_browse_catalog(service=_build_market_query_service(session))

    assert payload.total == 4
    assert [(item.id, item.label, item.count) for item in payload.countries] == [
        ("NGA", "Nigeria", 2),
        ("ESP", "Spain", 2),
    ]
    assert [(item.id, item.label, item.count) for item in payload.leagues] == [
        ("competition-prem", "Premier League", 4),
    ]
    assert payload.leagues[0].country_id == "NGA"
    assert payload.leagues[0].league_id == "competition-prem"
    assert [(item.id, item.label, item.count) for item in payload.divisions] == [
        ("division-1", "Division 1", 4),
    ]
    assert payload.divisions[0].parent_id == "competition-prem"
    assert payload.divisions[0].league_id == "competition-prem"
    assert payload.divisions[0].division_id == "division-1"
    assert [(item.id, item.label, item.count) for item in payload.clubs] == [
        ("club-alpha", "Alpha FC", 2),
        ("club-beta", "Beta United", 2),
    ]
    assert payload.clubs[0].parent_id == "division-1"
    assert payload.clubs[0].league_id == "competition-prem"
    assert payload.clubs[0].division_id == "division-1"


def test_market_browse_endpoints_expose_league_club_and_nationality_paths(session) -> None:
    _seed_market_player_catalog(session)
    service = _build_market_query_service(session)

    leagues = list_market_leagues(service=service)
    clubs = list_market_league_clubs("competition-prem", service=service)
    club_players = list_market_club_players("club-alpha", limit=100, service=service)
    nationalities = list_market_nationalities(service=service)
    national_teams = list_market_national_teams(service=service)
    eligible_players = list_market_national_team_eligible_players("NGA", limit=100, service=service)

    assert leagues == [
        {
            "league_id": "competition-prem",
            "slug": "premier-league",
            "display_name": "Premier League",
            "country": None,
            "country_code": None,
            "crest_url": None,
            "player_count": 4,
            "club_count": 2,
        }
    ]
    assert [club["club_id"] for club in clubs] == ["club-alpha", "club-beta"]
    assert [item.player_id for item in club_players.items] == ["player-1", "player-3"]
    assert [item["country_code"] for item in nationalities] == ["NGA", "ESP"]
    assert [team["team_id"] for team in national_teams] == ["NGA", "ESP"]
    assert [item.player_id for item in eligible_players.items] == ["player-1", "player-2"]


def test_market_player_list_supports_cursor_pagination(session) -> None:
    _seed_market_player_catalog(session)
    service = _build_market_query_service(session)

    first_page = service.list_players(limit=2)
    second_page = service.list_players(limit=2, cursor=first_page.next_cursor)

    assert [item.player_id for item in first_page.items] == ["player-1", "player-2"]
    assert first_page.has_more is True
    assert first_page.next_cursor is not None
    assert [item.player_id for item in second_page.items] == ["player-3", "player-4"]
    assert second_page.has_more is False
    assert second_page.next_cursor is None


def test_market_player_list_traverses_cursor_pages_without_duplicates(session) -> None:
    _seed_market_player_catalog(session)
    service = _build_market_query_service(session)

    seen: list[str] = []
    cursor: str | None = None
    has_more = True
    while has_more:
        page = service.list_players(limit=1, cursor=cursor)
        assert len(page.items) == 1
        seen.extend(item.player_id for item in page.items)
        cursor = page.next_cursor
        has_more = page.has_more

    assert seen == ["player-1", "player-2", "player-3", "player-4"]
    assert len(seen) == len(set(seen))


def test_market_player_list_filters_by_position(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(position="forward")

    assert [item.player_id for item in payload.items] == ["player-1"]


def test_market_player_list_filters_by_nationality(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(nationality="Nigeria")

    assert [item.player_id for item in payload.items] == ["player-1", "player-2"]


def test_market_player_list_filters_by_national_team(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(national_team="Nigeria U20")

    assert [item.player_id for item in payload.items] == ["player-1", "player-2"]


def test_market_player_list_filters_by_club(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(club="Alpha FC")

    assert [item.player_id for item in payload.items] == ["player-1", "player-3"]


def test_market_player_list_filters_by_league(session) -> None:
    _seed_market_player_catalog(session)
    la_liga = Competition(
        id="competition-laliga",
        source_provider="synthetic",
        provider_external_id="competition-laliga",
        name="La Liga",
        slug="la-liga",
    )
    player_four = session.get(Player, "player-4")

    assert player_four is not None

    session.add(la_liga)
    player_four.current_competition_id = la_liga.id
    player_four.current_competition = la_liga
    session.commit()

    premier_payload = _build_market_query_service(session).list_players(league="Premier League")
    la_liga_payload = _build_market_query_service(session).list_players(league="la-liga")

    assert [item.player_id for item in premier_payload.items] == ["player-1", "player-2", "player-3"]
    assert [item.player_id for item in la_liga_payload.items] == ["player-4"]


def test_market_player_list_filters_by_division(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(division="division-1")

    assert [item.player_id for item in payload.items] == ["player-1", "player-2", "player-3", "player-4"]


def test_market_player_list_filters_by_age_range(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(min_age=20, max_age=27, sort="age")

    assert [item.player_id for item in payload.items] == ["player-1", "player-4"]


def test_market_player_list_filters_by_value_range(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(min_value=100.0, max_value=200.0)

    assert [item.player_id for item in payload.items] == ["player-2"]


def test_market_player_list_filters_by_search(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(search="alpha")

    assert [item.player_id for item in payload.items] == ["player-1", "player-3"]


def test_market_player_list_searches_by_league_name(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(search="premier")

    assert [item.player_id for item in payload.items] == ["player-1", "player-2", "player-3", "player-4"]


def test_market_player_list_searches_by_national_team_name(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(search="nigeria u20")

    assert [item.player_id for item in payload.items] == ["player-1", "player-2"]


def test_market_player_list_sorts_by_supported_keys(session) -> None:
    _seed_market_player_catalog(session)
    service = _build_market_query_service(session)

    assert [item.player_id for item in service.list_players(sort="current_value").items] == [
        "player-1",
        "player-2",
        "player-3",
        "player-4",
    ]
    assert [item.player_id for item in service.list_players(sort="trend_score").items] == [
        "player-2",
        "player-1",
        "player-3",
        "player-4",
    ]
    assert [item.player_id for item in service.list_players(sort="age").items] == [
        "player-2",
        "player-1",
        "player-4",
        "player-3",
    ]
    assert [item.player_id for item in service.list_players(sort="name").items] == [
        "player-1",
        "player-2",
        "player-3",
        "player-4",
    ]


def test_market_player_list_supports_mixed_real_and_regen_with_nullable_rows(session) -> None:
    _seed_market_player_catalog(session)
    session.get(Player, "player-1").is_real_player = True
    session.get(Player, "player-2").is_real_player = False
    session.commit()

    payload = _build_market_query_service(session).list_players(limit=10, sort="current_value")
    by_id = {item.player_id: item for item in payload.items}

    assert payload.total == 4
    assert by_id["player-1"].current_value_credits == 220.0
    assert by_id["player-1"].global_scouting_index == 84.0
    assert by_id["player-1"].previous_global_scouting_index == 79.0
    assert by_id["player-1"].global_scouting_index_movement_pct == 6.33
    assert by_id["player-2"].current_value_credits == 180.0
    assert by_id["player-4"].current_value_credits is not None
    assert by_id["player-4"].current_value_credits > 0
    assert by_id["player-4"].movement_pct is None
    assert by_id["player-4"].market_interest_score is None
    assert by_id["player-1"].avatar.seed_token
    assert by_id["player-2"].avatar.seed_token


def test_market_player_detail_returns_composed_market_view(session) -> None:
    _seed_market_player_catalog(session)

    payload = get_market_player_detail("player-1", service=_build_market_query_service(session))

    assert payload.player_id == "player-1"
    assert payload.identity.current_club_name == "Alpha FC"
    assert payload.market_profile.holder_count == 14
    assert payload.value.current_value_credits == 220.0
    assert payload.trend.global_scouting_index == 84.0


def test_manual_price_override_updates_market_views(session) -> None:
    _seed_market_player_catalog(session)
    app = FastAPI()
    runtime_controls = RuntimeControlService(app)
    runtime_controls.upsert_price_override(
        asset_type="player",
        asset_id="player-1",
        override_price=Decimal("333.5000"),
        currency="credits",
        reason="manual operator intervention",
        updated_by_user_id="admin-1",
    )
    service = _build_market_query_service(session, runtime_controls=runtime_controls)

    list_payload = service.list_players(limit=10, sort="current_value")
    detail_payload = get_market_player_detail("player-1", service=service)

    player_row = next(item for item in list_payload.items if item.player_id == "player-1")
    assert player_row.current_value_credits == 333.5
    assert player_row.movement_pct == 66.75
    assert detail_payload.value.current_value_credits == 333.5
    assert detail_payload.value.published_card_value_credits == 333.5
    assert detail_payload.value.movement_pct == 66.75


def test_market_player_detail_not_found_returns_404(session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_market_player_detail("missing-player", service=_build_market_query_service(session))

    assert exc_info.value.status_code == 404


def test_market_player_history_returns_existing_snapshots(session) -> None:
    _seed_market_player_catalog(session)

    payload = get_market_player_history("player-1", service=_build_market_query_service(session))

    assert payload.player_id == "player-1"
    assert [entry.snapshot_id for entry in payload.history] == ["snapshot-1b", "snapshot-1a"]


def test_market_player_history_returns_empty_contract_when_no_history_exists(session) -> None:
    _seed_market_player_catalog(session)

    payload = get_market_player_history("player-4", service=_build_market_query_service(session))

    assert payload.player_id == "player-4"
    assert payload.history == []


def test_market_player_list_combines_filters(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(
        position="forward",
        nationality="Nigeria",
        club="Alpha FC",
        league="Premier League",
        min_age=20,
        max_age=25,
        min_value=200.0,
        max_value=250.0,
        search="ayo",
    )

    assert [item.player_id for item in payload.items] == ["player-1"]


def test_market_player_list_rejects_invalid_sort(session) -> None:
    _seed_market_player_catalog(session)

    with pytest.raises(HTTPException) as exc_info:
        list_market_players(
            limit=20,
            offset=0,
            position=None,
            nationality=None,
            national_team=None,
            club=None,
            league=None,
            division=None,
            min_age=None,
            max_age=None,
            min_value=None,
            max_value=None,
            search=None,
            sort="unsupported",
            service=_build_market_query_service(session),
        )

    assert exc_info.value.status_code == 400
    assert "sort must be one of" in exc_info.value.detail


def _new_tradable_player(player_id: str, full_name: str) -> Player:
    return Player(
        id=player_id,
        source_provider="synthetic",
        provider_external_id=player_id,
        country_id="country-ng",
        current_club_id="club-alpha",
        current_competition_id="competition-prem",
        supply_tier_id="tier-elite",
        liquidity_band_id="liquidity-1",
        full_name=full_name,
        first_name=full_name.split(" ")[0],
        last_name=full_name.split(" ")[-1],
        short_name=full_name,
        position="Forward",
        normalized_position="forward",
        date_of_birth=date(2002, 2, 2),
        preferred_foot="right",
        shirt_number=21,
        height_cm=180,
        weight_kg=75,
        market_value_eur=10_000_000.0,
        is_tradable=True,
    )


def test_player_records_cache_serves_within_ttl(session, monkeypatch) -> None:
    monkeypatch.setenv("GTE_MARKET_RECORDS_CACHE_TTL_SECONDS", "300")
    clear_market_records_cache()
    try:
        _seed_market_player_catalog(session)
        session.commit()

        repository = SqlAlchemyMarketPlayerRepository(session)
        first = repository.list_player_records()
        assert len(first) == 4

        # A write within the TTL window must NOT be observed (cache hit).
        session.add(_new_tradable_player("player-5", "Zed Newman"))
        session.commit()
        cached = repository.list_player_records()
        assert len(cached) == 4

        # Clearing the cache forces a reload that now sees the new player.
        clear_market_records_cache()
        reloaded = repository.list_player_records()
        assert len(reloaded) == 5
    finally:
        clear_market_records_cache()


def test_list_players_uses_cached_records_across_sessions(monkeypatch) -> None:
    monkeypatch.setenv("GTE_MARKET_RECORDS_CACHE_TTL_SECONDS", "300")
    clear_market_records_cache()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        # Session A populates the process cache, then is closed.
        with SessionLocal() as session_a:
            _seed_market_player_catalog(session_a)
            session_a.commit()
            first = _build_market_query_service(session_a).list_players(sort="current_value")
            first_ids = [item.player_id for item in first.items]
        assert first_ids

        # Session B must reuse the cached (now detached) records through the full
        # filter/sort/build path without raising DetachedInstanceError, and must
        # produce identical results.
        with SessionLocal() as session_b:
            service_b = _build_market_query_service(session_b)
            again = service_b.list_players(sort="current_value")
            assert [item.player_id for item in again.items] == first_ids
            # Exercise derived-value sort + search + availability on cached records.
            assert service_b.list_players(sort="trend_score").items
            assert service_b.list_players(search="Ayo").items
            assert service_b.browse_catalog().total == len(first_ids)
    finally:
        clear_market_records_cache()
        engine.dispose()


def test_player_candidates_cache_serves_within_ttl(session, monkeypatch) -> None:
    monkeypatch.setenv("GTE_MARKET_RECORDS_CACHE_TTL_SECONDS", "300")
    clear_market_records_cache()
    try:
        _seed_market_player_catalog(session)
        session.commit()

        repository = SqlAlchemyMarketPlayerRepository(session)
        first = repository.list_player_candidates()
        assert len(first) == 4

        # A write within the TTL window must NOT be observed (cache hit).
        session.add(_new_tradable_player("player-5", "Zed Newman"))
        session.commit()
        cached = repository.list_player_candidates()
        assert len(cached) == 4

        # Clearing the cache forces a reload that now sees the new player.
        clear_market_records_cache()
        reloaded = repository.list_player_candidates()
        assert len(reloaded) == 5
    finally:
        clear_market_records_cache()


def test_candidates_cache_is_independent_of_records_cache(session, monkeypatch) -> None:
    monkeypatch.setenv("GTE_MARKET_RECORDS_CACHE_TTL_SECONDS", "300")
    clear_market_records_cache()
    try:
        _seed_market_player_catalog(session)
        session.commit()

        repository = SqlAlchemyMarketPlayerRepository(session)
        # Populate only the candidates cache.
        repository.list_player_candidates()

        # A write must still be observed by list_player_records(), since it has
        # its own independent cache entry that hasn't been populated yet.
        session.add(_new_tradable_player("player-5", "Zed Newman"))
        session.commit()
        assert len(repository.list_player_records()) == 5

        # clear_market_records_cache() must drop BOTH caches, not just one.
        clear_market_records_cache()
        session.add(_new_tradable_player("player-6", "Yaw Sixth"))
        session.commit()
        assert len(repository.list_player_candidates()) == 6
        assert len(repository.list_player_records()) == 6
    finally:
        clear_market_records_cache()


def test_list_player_candidates_matches_full_records_player_ids(session) -> None:
    _seed_market_player_catalog(session)
    session.commit()

    repository = SqlAlchemyMarketPlayerRepository(session)
    candidate_ids = [record.player.id for record in repository.list_player_candidates()]
    full_ids = [record.player.id for record in repository.list_player_records()]

    # The lighter candidates load must select the exact same rows, in the
    # same order, as the full-fidelity load -- it only trims which
    # relationships get eager-loaded per row, never which rows are returned.
    assert candidate_ids == full_ids == ["player-1", "player-2", "player-3", "player-4"]


def test_get_player_records_by_ids_hydrates_and_preserves_membership(session) -> None:
    _seed_market_player_catalog(session)
    session.commit()

    repository = SqlAlchemyMarketPlayerRepository(session)
    assert repository.get_player_records_by_ids([]) == []

    # Order of the input ids must not matter -- callers re-order by id.
    records = repository.get_player_records_by_ids(["player-3", "player-1", "does-not-exist"])
    by_id = {record.player.id: record for record in records}
    assert set(by_id) == {"player-1", "player-3"}

    # This is the exact relationship the list endpoint's hydration step
    # depends on: get_player_records_by_ids must carry image_metadata, which
    # list_player_candidates() deliberately omits.
    assert by_id["player-1"].player.image_metadata
    assert by_id["player-1"].player.image_metadata[0].source_url == "https://cdn.sportmonks.test/players/player-1.png"


def test_get_player_records_by_ids_excludes_non_tradable_players(session) -> None:
    _seed_market_player_catalog(session)
    non_tradable = _new_tradable_player("player-untradable", "Non Tradable")
    non_tradable.is_tradable = False
    session.add(non_tradable)
    session.commit()

    repository = SqlAlchemyMarketPlayerRepository(session)
    records = repository.get_player_records_by_ids(["player-1", "player-untradable"])
    assert [record.player.id for record in records] == ["player-1"]


def _issue_share_market(session, *, player_id: str, price: str) -> None:
    from decimal import Decimal as _Decimal

    from app.models.player_token_market import PlayerShareMarket

    session.add(
        PlayerShareMarket(
            player_id=player_id,
            total_shares=1000,
            circulating_shares=0,
            share_price_coin=_Decimal(price),
            status="active",
            metadata_json={},
        )
    )
    session.commit()


def test_market_player_list_publishes_the_tradable_share_price(session) -> None:
    """PHASE5-A P1-2: the Market contract must expose the tradable price, not
    only valuation. share_price_coin comes straight from PlayerShareMarket."""
    _seed_market_player_catalog(session)
    _issue_share_market(session, player_id="player-1", price="0.7500")
    clear_market_records_cache()

    payload = _build_market_query_service(session).list_players(limit=20, offset=0)
    by_id = {item.player_id: item for item in payload.items}

    assert by_id["player-1"].share_price_coin == Decimal("0.7500")


def test_market_player_list_reports_an_unissued_market_as_unavailable(session) -> None:
    """UNKNOWN != ZERO: a player with no issued share market has no tradable
    price, and reading the market must never issue one."""
    from app.models.player_token_market import PlayerShareMarket

    _seed_market_player_catalog(session)
    _issue_share_market(session, player_id="player-1", price="0.7500")
    clear_market_records_cache()

    payload = _build_market_query_service(session).list_players(limit=20, offset=0)
    by_id = {item.player_id: item for item in payload.items}

    assert by_id["player-2"].share_price_coin is None
    assert by_id["player-2"].current_value_credits is not None
    assert session.query(PlayerShareMarket).count() == 1


def test_market_player_detail_publishes_the_tradable_share_price(session) -> None:
    _seed_market_player_catalog(session)
    _issue_share_market(session, player_id="player-1", price="1.2500")
    clear_market_records_cache()

    service = _build_market_query_service(session)
    priced = service.get_player_detail("player-1")
    unpriced = service.get_player_detail("player-2")

    assert priced.market_profile.share_price_coin == Decimal("1.2500")
    assert unpriced.market_profile.share_price_coin is None
