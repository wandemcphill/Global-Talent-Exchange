from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.market.router import router as market_router
from app.models.base import Base
from app.models.player_token_market import PlayerShareHolding
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.players.legacy_token_service import PlayerTokenMarketService
from app.players import router as players_router_module
from app.players.router import router as players_router
from app.risk_ops_engine.service import RiskOpsService
from app.models.risk_ops import RiskActionType
from app.wallets.funding_service import WalletFundingService
from app.wallets.service import LedgerPosting, WalletService


def _build_session() -> tuple[object, Session]:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, session_factory()


def _create_user(session: Session, *, user_id: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id.replace("-", "_"),
        password_hash="hashed",
        role=role,
    )
    session.add(user)
    session.flush()
    WalletService().ensure_default_accounts(session, user)
    session.flush()
    return user


def _seed_imported_real_player(session: Session, *, player_id: str) -> Player:
    player = Player(
        id=player_id,
        source_provider="transfermarkt_2nd_zip",
        provider_external_id=f"transfermarkt:{player_id}",
        full_name="Victor Osimhen",
        canonical_display_name="Victor Osimhen",
        position="Striker",
        normalized_position="striker",
        date_of_birth=date(1998, 12, 29),
        preferred_foot="right",
        is_real_player=True,
        real_player_tier="featured",
        identity_confidence_score=0.99,
        source_last_refreshed_at=datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
        real_world_club_name="Galactic FC",
        real_world_league_name="Global Elite League",
        current_market_reference_value=120_000_000.0,
        market_reference_currency="EUR",
        normalization_profile_version="real_player_v1",
    )
    session.add(player)
    session.flush()

    source_link = RealPlayerSourceLink(
        id=f"source-link-{player_id}",
        gtex_player_id=player.id,
        source_name="transfermarkt_2nd_zip",
        source_player_key=f"transfermarkt:{player_id}",
        canonical_name=player.full_name,
        known_aliases_json=["Osimhen"],
        nationality="Nigeria",
        date_of_birth=player.date_of_birth,
        birth_year=1998,
        primary_position="Striker",
        current_real_world_club=player.real_world_club_name,
        identity_confidence_score=0.99,
        is_verified_real_player=True,
        verification_state="verified",
    )
    session.add(source_link)
    session.flush()

    session.add(
        RealPlayerProfile(
            id=f"profile-{player_id}",
            gtex_player_id=player.id,
            source_link_id=source_link.id,
            source_name="transfermarkt_2nd_zip",
            source_player_key=source_link.source_player_key,
            canonical_name=player.full_name,
            known_aliases_json=["Osimhen"],
            nationality="Nigeria",
            birth_year=1998,
            date_of_birth=player.date_of_birth,
            dominant_foot="right",
            primary_position="Striker",
            secondary_positions_json=["Forward"],
            current_club_name=player.real_world_club_name,
            current_league_name=player.real_world_league_name,
            competition_level="elite",
            appearances=31,
            minutes_played=2460,
            goals=24,
            assists=5,
            clean_sheets=0,
            injury_status="fit",
            current_market_reference_value=120_000_000.0,
            market_reference_currency="EUR",
            source_last_refreshed_at=player.source_last_refreshed_at,
            normalization_profile_version="real_player_v1",
            normalized_signals_json={"competition_level": "elite"},
            ingestion_batch_id="2nd-zip-proof-batch",
            ingestion_source_version="2026-03-29",
            pricing_snapshot_id=f"snapshot-{player_id}",
            metadata_json={"proof": "player_share_market"},
        )
    )
    session.flush()
    return player


def _seed_coin_balance(session: Session, *, user: User, amount: Decimal) -> None:
    wallet = WalletService()
    user_account = wallet.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference=f"seed:{user.id}",
        actor=user,
    )


def _set_wallet_compliance_status(session: Session, *, user: User, status: str) -> None:
    wallet = WalletFundingService().ensure_wallet(session, user)
    wallet.compliance_status = status
    session.flush()


def _block_trading(session: Session, *, user: User) -> None:
    RiskOpsService(session).create_action(
        actor_user_id=None,
        user_id=user.id,
        action_type=RiskActionType.BLOCK_TRADING,
        reason="Test trading restriction.",
    )
    session.flush()


def _build_client(
    session: Session,
    *,
    admin_user: User,
    current_user: User,
    monkeypatch,
) -> tuple[TestClient, dict[str, User]]:
    app = FastAPI()
    app.include_router(players_router)
    app.include_router(market_router)

    auth_context = {"admin": admin_user, "user": current_user}

    def _session_override():
        return session

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_admin] = lambda: auth_context["admin"]
    app.dependency_overrides[get_current_user] = lambda: auth_context["user"]
    monkeypatch.setattr(players_router_module, "_require_manager_supply_permission", lambda request, actor: None)

    return TestClient(app), auth_context


def test_issue_player_share_market_for_imported_real_player_records_issue_event(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="share-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="share-fan")
        player = _seed_imported_real_player(session, player_id="real-player-1")
        client, _auth = _build_client(session, admin_user=admin, current_user=fan, monkeypatch=monkeypatch)

        with client:
            response = client.post(
                f"/players/{player.id}/shares/market",
                json={"total_shares": 1500, "price": "0.7500", "liquidity": "30.0000", "status": "active"},
            )
            events_response = client.get(f"/players/{player.id}/shares/events")

        assert response.status_code == 200, response.text
        assert events_response.status_code == 200, events_response.text

        payload = response.json()
        events = events_response.json()

        assert payload["player_id"] == player.id
        assert payload["total_shares"] == 1500
        assert payload["share_price_coin"] == "0.7500"
        assert payload["liquidity_coin"] == "30.0000"
        assert payload["status"] == "active"
        assert payload["metadata_json"]["is_real_player"] is True
        assert events[0]["event_type"] == "issue"
        assert events[0]["metadata_json"]["market_id"] == payload["id"]
        assert events[0]["metadata_json"]["is_real_player"] is True
        assert events[0]["metadata_json"]["total_shares"] == 1500
    finally:
        session.close()
        engine.dispose()


def test_read_player_share_market_and_events_after_issue(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="share-read-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="share-read-fan")
        player = _seed_imported_real_player(session, player_id="real-player-2")
        client, _auth = _build_client(session, admin_user=admin, current_user=fan, monkeypatch=monkeypatch)

        with client:
            issue_response = client.post(
                f"/players/{player.id}/shares/market",
                json={"total_shares": 1000, "share_price_coin": "1.2500", "status": "active"},
            )
            market_response = client.get(f"/players/{player.id}/shares/market")
            events_response = client.get(f"/players/{player.id}/shares/events")

        assert issue_response.status_code == 200, issue_response.text
        assert market_response.status_code == 200, market_response.text
        assert events_response.status_code == 200, events_response.text

        market_payload = market_response.json()
        event_payload = events_response.json()

        assert market_payload["player_id"] == player.id
        assert market_payload["total_shares"] == 1000
        assert market_payload["circulating_shares"] == 0
        assert market_payload["share_price_coin"] == "1.2500"
        assert market_payload["metadata_json"]["player_name"] == "Victor Osimhen"
        assert market_payload["metadata_json"]["is_real_player"] is True
        assert [item["event_type"] for item in event_payload] == ["issue"]
    finally:
        session.close()
        engine.dispose()


def test_read_player_share_market_auto_initializes_before_manual_issue(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="share-unissued-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="share-unissued-fan")
        player = _seed_imported_real_player(session, player_id="real-player-unissued")
        client, _auth = _build_client(session, admin_user=admin, current_user=fan, monkeypatch=monkeypatch)

        with client:
            market_response = client.get(f"/players/{player.id}/shares/market")

        assert market_response.status_code == 200, market_response.text
        payload = market_response.json()
        assert payload["player_id"] == player.id
        assert payload["status"] == "active"
        assert payload["market_issued"] is True
        assert payload["total_shares"] == 1000
        assert payload["circulating_shares"] == 0
        assert Decimal(payload["share_price_coin"]) > Decimal("0.0000")
        assert Decimal(payload["liquidity_coin"]) > Decimal("0.0000")
        assert payload["metadata_json"]["market_issued"] is True
        assert payload["metadata_json"]["auto_initialized"] is True
    finally:
        session.close()
        engine.dispose()


def test_buy_player_shares_updates_market_holding_and_event_log(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="share-buy-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="share-buy-fan")
        player = _seed_imported_real_player(session, player_id="real-player-3")
        _seed_coin_balance(session, user=fan, amount=Decimal("50.0000"))
        client, auth = _build_client(session, admin_user=admin, current_user=fan, monkeypatch=monkeypatch)

        with client:
            issue_response = client.post(
                f"/players/{player.id}/shares/market",
                json={"total_shares": 1000, "share_price_coin": "0.5000", "status": "active"},
            )
            auth["user"] = fan
            buy_response = client.post(
                f"/players/{player.id}/shares/buy",
                json={"share_count": 10},
            )
            events_response = client.get(f"/players/{player.id}/shares/events")

        assert issue_response.status_code == 200, issue_response.text
        assert buy_response.status_code == 201, buy_response.text
        assert events_response.status_code == 200, events_response.text

        payload = buy_response.json()
        holding = session.query(PlayerShareHolding).filter_by(user_id=fan.id, player_id=player.id).one()
        events = events_response.json()

        assert payload["gross_amount_coin"] == "5.0000"
        assert payload["fee_amount_coin"] == "1.0000"
        assert payload["net_amount_coin"] == "6.0000"
        assert payload["transaction_id"]
        assert payload["market"]["circulating_shares"] == 10
        assert payload["holding"]["share_count"] == 10
        assert payload["holding"]["average_cost_coin"] == "0.6000"
        assert holding.share_count == 10
        assert holding.average_cost_coin == Decimal("0.6000")
        assert [item["event_type"] for item in events] == ["buy", "issue"]
        assert events[0]["metadata_json"]["transaction_id"] == payload["transaction_id"]
        assert events[0]["metadata_json"]["circulating_shares"] == 10
    finally:
        session.close()
        engine.dispose()


def test_list_player_share_markets_returns_only_tradable_active_markets(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="share-list-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="share-list-fan")
        tradable = _seed_imported_real_player(session, player_id="real-player-tradable")
        blocked = _seed_imported_real_player(session, player_id="real-player-blocked")
        blocked.is_tradable = False
        session.flush()
        # The listing is read-only: it shows issued markets and no longer mints
        # one per listed row inside the GET, so a market has to exist first.
        # Only the tradable player can be issued one -- issue_market rejects an
        # untradable player outright -- which is itself the first half of the
        # guarantee this test covers.
        PlayerTokenMarketService(session).issue_market(
            actor=admin,
            player_id=tradable.id,
            total_shares=1000,
            share_price_coin=Decimal("1.0000"),
        )
        session.flush()
        client, _auth = _build_client(session, admin_user=admin, current_user=fan, monkeypatch=monkeypatch)

        with client:
            response = client.get("/players/markets")

        assert response.status_code == 200, response.text
        payload = response.json()
        item_ids = {item["player_id"] for item in payload["items"]}

        assert tradable.id in item_ids
        assert blocked.id not in item_ids
        assert all(item["status"] == "active" for item in payload["items"])
    finally:
        session.close()
        engine.dispose()


def test_buy_player_shares_requires_verified_wallet_compliance(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="share-kyc-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="share-kyc-fan")
        player = _seed_imported_real_player(session, player_id="real-player-kyc-buy")
        _seed_coin_balance(session, user=fan, amount=Decimal("50.0000"))
        _set_wallet_compliance_status(session, user=fan, status="pending")
        client, auth = _build_client(session, admin_user=admin, current_user=fan, monkeypatch=monkeypatch)

        with client:
            issue_response = client.post(
                f"/players/{player.id}/shares/market",
                json={"total_shares": 1000, "share_price_coin": "0.5000", "liquidity_coin": "20.0000"},
            )
            auth["user"] = fan
            buy_response = client.post(
                f"/players/{player.id}/shares/buy",
                json={"share_count": 10},
            )

        assert issue_response.status_code == 200, issue_response.text
        assert buy_response.status_code == 409, buy_response.text
        assert "wallet compliance is verified" in buy_response.json()["detail"].lower()
    finally:
        session.close()
        engine.dispose()


def test_sell_player_shares_rejects_active_trading_risk_block(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="share-risk-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="share-risk-fan")
        player = _seed_imported_real_player(session, player_id="real-player-risk-sell")
        _seed_coin_balance(session, user=fan, amount=Decimal("50.0000"))
        _block_trading(session, user=fan)
        client, auth = _build_client(session, admin_user=admin, current_user=fan, monkeypatch=monkeypatch)

        with client:
            issue_response = client.post(
                f"/players/{player.id}/shares/market",
                json={"total_shares": 1000, "share_price_coin": "0.5000", "liquidity_coin": "20.0000"},
            )
            auth["user"] = fan
            sell_response = client.post(
                f"/players/{player.id}/shares/sell",
                json={"share_count": 1},
            )

        assert issue_response.status_code == 200, issue_response.text
        assert sell_response.status_code == 423, sell_response.text
        assert "trading is temporarily blocked" in sell_response.json()["detail"].lower()
    finally:
        session.close()
        engine.dispose()


def test_market_buy_and_sell_endpoints_execute_share_trades(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="share-market-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="share-market-fan")
        player = _seed_imported_real_player(session, player_id="real-player-market-trade")
        _seed_coin_balance(session, user=fan, amount=Decimal("50.0000"))
        client, auth = _build_client(session, admin_user=admin, current_user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(
                f"/players/{player.id}/shares/market",
                json={"total_shares": 1000, "share_price_coin": "0.5000", "liquidity_coin": "20.0000"},
            )
            auth["user"] = fan
            buy_response = client.post("/market/buy", json={"player_id": player.id, "share_count": 10})
            sell_response = client.post("/market/sell", json={"player_id": player.id, "share_count": 4})

        assert buy_response.status_code == 201, buy_response.text
        assert sell_response.status_code == 201, sell_response.text

        buy_payload = buy_response.json()
        sell_payload = sell_response.json()
        assert buy_payload["holding"]["share_count"] == 10
        assert Decimal(buy_payload["fee_amount_coin"]) > Decimal("0.0000")
        assert sell_payload["holding"]["share_count"] == 6
        assert sell_payload["market"]["circulating_shares"] == 6
        assert Decimal(sell_payload["gross_amount_coin"]) > Decimal("0.0000")
        assert Decimal(sell_payload["fee_amount_coin"]) > Decimal("0.0000")
        assert Decimal(sell_payload["net_amount_coin"]) < Decimal(sell_payload["gross_amount_coin"])
    finally:
        session.close()
        engine.dispose()
