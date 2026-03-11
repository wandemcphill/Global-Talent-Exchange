from datetime import date, datetime, timezone

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.ingestion.models  # noqa: F401
import backend.app.market.read_models  # noqa: F401
import backend.app.players.read_models  # noqa: F401
import backend.app.value_engine.read_models  # noqa: F401
from backend.app.ingestion.models import Club, Competition, Country, LiquidityBand, Player, SupplyTier

from backend.app.market import (
    ListingStatus,
    ListingType,
    MarketConflictError,
    MarketEngine,
    MarketValidationError,
    OfferStatus,
    TradeIntentDirection,
    TradeIntentStatus,
)
from backend.app.market.router import (
    get_market_player_detail,
    get_market_player_history,
    list_market_players,
)
from backend.app.market.service import MarketPlayerQueryService
from backend.app.models.base import Base
from backend.app.players.read_models import PlayerSummaryReadModel
from backend.app.value_engine.read_models import PlayerValueSnapshotRecord


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


def _build_market_query_service(session) -> MarketPlayerQueryService:
    return MarketPlayerQueryService(session=session, today=date(2026, 3, 11))


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


def test_market_player_list_filters_by_position(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(position="forward")

    assert [item.player_id for item in payload.items] == ["player-1"]


def test_market_player_list_filters_by_nationality(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(nationality="Nigeria")

    assert [item.player_id for item in payload.items] == ["player-1", "player-2"]


def test_market_player_list_filters_by_club(session) -> None:
    _seed_market_player_catalog(session)

    payload = _build_market_query_service(session).list_players(club="Alpha FC")

    assert [item.player_id for item in payload.items] == ["player-1", "player-3"]


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


def test_market_player_detail_returns_composed_market_view(session) -> None:
    _seed_market_player_catalog(session)

    payload = get_market_player_detail("player-1", service=_build_market_query_service(session))

    assert payload.player_id == "player-1"
    assert payload.identity.current_club_name == "Alpha FC"
    assert payload.market_profile.holder_count == 14
    assert payload.value.current_value_credits == 220.0
    assert payload.trend.global_scouting_index == 84.0


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
            club=None,
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
