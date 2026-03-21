from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select

from app.admin.router import (
    get_liquidity_bands,
    get_supply_tiers,
    update_liquidity_bands,
    update_supply_tiers,
    update_suspicion_thresholds,
    update_value_controls,
)
from app.admin.schemas import SuspicionThresholdsPayload, ValueControlsPayload
from app.admin.service import ConfigAdminService
from app.auth.service import AuthService
from app.core.config import BACKEND_ROOT, load_settings
from app.ingestion.market_profile import PlayerMarketProfileService
from app.ingestion.models import (
    Club,
    Competition,
    Country,
    InternalLeague,
    LiquidityBand,
    MarketSignal,
    Player,
    SupplyTier,
)
from app.main import create_app
from app.market.read_models import MarketSummaryReadModel
from app.models.user import UserRole
from app.surveillance.router import (
    list_circular_trade_alerts,
    list_holder_concentration_alerts,
    list_suspicious_clusters,
    list_suspicious_players,
    list_thin_market_alerts,
)
from app.surveillance.service import SurveillanceService
from app.value_engine.read_models import PlayerValueSnapshotRecord


def _seed_low_thresholds(config_root: Path) -> None:
    (config_root / "suspicion_thresholds.toml").write_text(
        "\n".join(
            [
                "player_min_suspicious_events = 5",
                "player_min_suspicious_share = 0.20",
                "player_price_band_breach_ratio = 0.05",
                "cluster_min_member_count = 3",
                "cluster_min_interaction_count = 3",
                "cluster_max_asset_count = 2",
                "thin_market_min_price_credits = 100",
                "thin_market_max_pending_offers = 1",
                "thin_market_max_active_trade_intents = 1",
                "holder_concentration_min_assets = 3",
                "holder_concentration_share = 0.50",
                "circular_trade_min_cycle_length = 3",
                "circular_trade_min_repetitions = 1",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _build_app(tmp_path: Path):
    config_root = tmp_path / "config"
    shutil.copytree(BACKEND_ROOT / "config", config_root)
    _seed_low_thresholds(config_root)
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'phase8.db').as_posix()}"
    settings = load_settings(
        environ={
            "GTE_DATABASE_URL": database_url,
            "GTE_AUTH_SECRET": "phase8-test-secret",
        },
        config_root=config_root,
    )
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    app = create_app(settings=settings, engine=engine, run_migration_check=True)
    return app, config_root


def _admin_user(app):
    with app.state.session_factory() as session:
        service = AuthService()
        user = service.register_user(
            session,
            email="admin@example.com",
            username="adminuser",
            password="SuperSecret1",
            role=UserRole.ADMIN,
        )
        session.commit()
        session.refresh(user)
        return user


@pytest.mark.anyio
async def test_admin_config_endpoints_persist_and_reload_runtime_settings(tmp_path: Path) -> None:
    app, config_root = _build_app(tmp_path)

    async with app.router.lifespan_context(app):
        admin_user = _admin_user(app)
        request = SimpleNamespace(app=app)
        admin_service = ConfigAdminService()

        supply_payload = get_supply_tiers(request=request, _=admin_user)
        supply_payload.tiers[0].daily_pack_supply += 3
        with app.state.session_factory() as session:
            updated_supply = update_supply_tiers(
                payload=supply_payload,
                request=request,
                session=session,
                service=admin_service,
                _=admin_user,
            )
        assert updated_supply.tiers[0].daily_pack_supply == supply_payload.tiers[0].daily_pack_supply

        liquidity_payload = get_liquidity_bands(request=request, _=admin_user)
        liquidity_payload.bands[0].maker_inventory_target += 25
        with app.state.session_factory() as session:
            updated_liquidity = update_liquidity_bands(
                payload=liquidity_payload,
                request=request,
                session=session,
                service=admin_service,
                _=admin_user,
            )
        assert updated_liquidity.bands[0].maker_inventory_target == liquidity_payload.bands[0].maker_inventory_target

        updated_thresholds = update_suspicion_thresholds(
            payload=SuspicionThresholdsPayload(
                player_min_suspicious_events=9,
                player_min_suspicious_share=0.33,
                player_price_band_breach_ratio=0.07,
                cluster_min_member_count=3,
                cluster_min_interaction_count=4,
                cluster_max_asset_count=2,
                thin_market_min_price_credits=120,
                thin_market_max_pending_offers=1,
                thin_market_max_active_trade_intents=1,
                holder_concentration_min_assets=3,
                holder_concentration_share=0.52,
                circular_trade_min_cycle_length=3,
                circular_trade_min_repetitions=1,
            ),
            request=request,
            service=admin_service,
            _=admin_user,
        )
        assert updated_thresholds.player_min_suspicious_share == 0.33

        updated_value_controls = update_value_controls(
            payload=ValueControlsPayload(
                component_weights={
                    "ftv_weight": 0.64,
                    "msv_weight": 0.24,
                    "sgv_weight": 0.07,
                    "egv_weight": 0.05,
                },
                price_band_limits=[
                    {"code": "default", "min_ratio": 0.82, "max_ratio": 1.18},
                    {"code": "entry", "min_ratio": 0.90, "max_ratio": 1.07},
                ],
            ),
            request=request,
            service=admin_service,
            _=admin_user,
        )
        assert updated_value_controls.component_weights is not None
        assert updated_value_controls.component_weights.msv_weight == 0.24

    assert app.state.settings.suspicion_thresholds.player_min_suspicious_events == 9
    assert app.state.value_engine_bridge.settings.value_engine_weighting.ftv_weight == 0.64
    assert "daily_pack_supply = 45" in (config_root / "supply_tiers.toml").read_text(encoding="utf-8")
    assert "maker_inventory_target = 85" in (config_root / "liquidity_bands.toml").read_text(encoding="utf-8")
    assert "player_min_suspicious_events = 9" in (config_root / "suspicion_thresholds.toml").read_text(encoding="utf-8")
    value_engine_config = (config_root / "value_engine_weighting.toml").read_text(encoding="utf-8")
    assert "[component_weights]" in value_engine_config
    assert "ftv_weight = 0.64" in value_engine_config


@pytest.mark.anyio
async def test_surveillance_endpoints_surface_phase8_alerts(tmp_path: Path) -> None:
    app, _config_root = _build_app(tmp_path)

    async with app.router.lifespan_context(app):
        admin_user = _admin_user(app)
        request = SimpleNamespace(app=app)
        surveillance_service = SurveillanceService(settings=app.state.settings)
        now = datetime(2026, 3, 11, tzinfo=timezone.utc)

        with app.state.session_factory() as session:
            PlayerMarketProfileService(settings=app.state.settings).ensure_catalogs(session)
            elite_tier = session.scalar(select(SupplyTier).where(SupplyTier.code == "elite"))
            entry_band = session.scalar(select(LiquidityBand).where(LiquidityBand.code == "entry"))

            country = Country(source_provider="manual", provider_external_id="country-1", name="England")
            league = InternalLeague(
                code="manual_league",
                name="Manual League",
                rank=99,
                competition_multiplier=1.2,
                visibility_weight=1.0,
            )
            competition = Competition(
                source_provider="manual",
                provider_external_id="competition-1",
                country=country,
                internal_league=league,
                name="Manual League",
                slug="manual-league",
                competition_type="league",
                is_tradable=True,
            )
            club = Club(
                source_provider="manual",
                provider_external_id="club-1",
                country=country,
                current_competition=competition,
                internal_league=league,
                name="Capital Stars",
                slug="capital-stars",
                is_tradable=True,
            )
            player = Player(
                source_provider="manual",
                provider_external_id="player-1",
                country=country,
                current_club=club,
                current_competition=competition,
                internal_league=league,
                supply_tier=elite_tier,
                liquidity_band=entry_band,
                full_name="Alert Player",
                position="Forward",
                normalized_position="forward",
                market_value_eur=25_000_000,
                is_tradable=True,
            )
            session.add_all([country, league, competition, club, player])
            session.flush()

            session.execute(
                PlayerValueSnapshotRecord.__table__.insert(),
                [
                    {
                        "id": "snapshot-1",
                        "player_id": player.id,
                        "player_name": player.full_name,
                        "as_of": now,
                        "previous_credits": 100.0,
                        "target_credits": 118.0,
                        "movement_pct": 0.18,
                        "football_truth_value_credits": 100.0,
                        "market_signal_value_credits": 130.0,
                        "breakdown_json": {
                            "football_truth_value_credits": 100.0,
                            "market_signal_value_credits": 130.0,
                            "published_card_value_credits": 118.0,
                        },
                        "drivers_json": ["market_demand"],
                    }
                ],
            )
            session.execute(
                MarketSummaryReadModel.__table__.insert(),
                [
                    {
                        "asset_id": "asset-thin",
                        "open_listing_id": "lst-thin",
                        "open_listing_type": "transfer",
                        "seller_user_id": "holder-1",
                        "ask_price": 300,
                        "pending_offer_count": 0,
                        "best_offer_price": None,
                        "active_trade_intent_count": 0,
                        "last_activity_at": now,
                    }
                ],
            )
            session.add_all(
                [
                    MarketSignal(
                        source_provider="manual",
                        provider_external_id="sig-1",
                        player_id=player.id,
                        signal_type="purchases",
                        score=10.0,
                        as_of=now,
                    ),
                    MarketSignal(
                        source_provider="manual",
                        provider_external_id="sig-2",
                        player_id=player.id,
                        signal_type="suspicious_purchases",
                        score=8.0,
                        as_of=now,
                    ),
                ]
            )
            session.commit()

        market_engine = app.state.market_engine
        for asset_id in ("asset-h1", "asset-h2", "asset-h3"):
            market_engine.create_listing(
                asset_id=asset_id,
                seller_user_id="holder-1",
                listing_type="transfer",
                ask_price=150,
            )
        market_engine.create_listing(
            asset_id="asset-h4",
            seller_user_id="holder-2",
            listing_type="transfer",
            ask_price=150,
        )

        listing_a = market_engine.create_listing(
            asset_id="asset-cycle",
            seller_user_id="user-a",
            listing_type="transfer",
            ask_price=210,
        )
        offer_ab = market_engine.create_offer(
            asset_id="asset-cycle",
            seller_user_id="user-a",
            buyer_user_id="user-b",
            cash_amount=210,
            listing_id=listing_a.listing_id,
        )
        market_engine.accept_offer(offer_id=offer_ab.offer_id, acting_user_id="user-a")

        listing_b = market_engine.create_listing(
            asset_id="asset-cycle",
            seller_user_id="user-b",
            listing_type="transfer",
            ask_price=212,
        )
        offer_bc = market_engine.create_offer(
            asset_id="asset-cycle",
            seller_user_id="user-b",
            buyer_user_id="user-c",
            cash_amount=212,
            listing_id=listing_b.listing_id,
        )
        market_engine.accept_offer(offer_id=offer_bc.offer_id, acting_user_id="user-b")

        listing_c = market_engine.create_listing(
            asset_id="asset-cycle",
            seller_user_id="user-c",
            listing_type="transfer",
            ask_price=211,
        )
        offer_ca = market_engine.create_offer(
            asset_id="asset-cycle",
            seller_user_id="user-c",
            buyer_user_id="user-a",
            cash_amount=211,
            listing_id=listing_c.listing_id,
        )
        market_engine.accept_offer(offer_id=offer_ca.offer_id, acting_user_id="user-c")

        with app.state.session_factory() as session:
            suspicious_players = list_suspicious_players(
                request=request,
                session=session,
                service=surveillance_service,
                lookback_days=7,
                limit=50,
                _=admin_user,
            )
            thin_market = list_thin_market_alerts(
                request=request,
                session=session,
                service=surveillance_service,
                limit=50,
                _=admin_user,
            )
        suspicious_clusters = list_suspicious_clusters(
            request=request,
            service=surveillance_service,
            limit=50,
            _=admin_user,
        )
        holder_concentration = list_holder_concentration_alerts(
            request=request,
            service=surveillance_service,
            limit=50,
            _=admin_user,
        )
        circular_trades = list_circular_trade_alerts(
            request=request,
            service=surveillance_service,
            limit=50,
            _=admin_user,
        )

        assert suspicious_players[0].player_name == "Alert Player"
        assert thin_market[0].asset_id == "asset-thin"
        assert suspicious_clusters[0].has_cycle is True
        assert set(suspicious_clusters[0].member_user_ids) == {"user-a", "user-b", "user-c"}
        assert holder_concentration[0].holder_user_id == "holder-1"
        assert circular_trades[0].asset_id == "asset-cycle"
