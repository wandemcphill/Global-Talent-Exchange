from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import backend.app.ingestion.models  # noqa: F401
import backend.app.ledger.models  # noqa: F401
import backend.app.models  # noqa: F401
import backend.app.orders.models  # noqa: F401
from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.auth.service import AuthService
from backend.app.ingestion.models import Player
from backend.app.models.base import Base
from backend.app.wallets.router import router
from backend.app.wallets.service import LedgerPosting, WalletService
from backend.app.models.wallet import LedgerEntryReason, LedgerUnit


@pytest.fixture()
def api_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    current_user = AuthService().register_user(
        session,
        email="wallet-http@example.com",
        username="wallethttp",
        password="SuperSecret1",
    )
    session.commit()

    app = FastAPI()
    app.include_router(router)

    def override_session():
        yield session

    def override_current_user():
        return current_user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(app) as client:
        yield client, session, current_user

    session.close()


def _create_player(session, *, provider_external_id: str = "player-wallet-1") -> Player:
    player = Player(
        source_provider="manual",
        provider_external_id=provider_external_id,
        full_name="Wallet Test Player",
        is_tradable=True,
    )
    session.add(player)
    session.commit()
    return player


def _fund_user(session, current_user, *, amount: Decimal) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, current_user, LedgerUnit.CREDIT)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="wallet-http-funding",
        description="Seed wallet credits for testing",
        actor=current_user,
    )
    session.commit()


def test_get_portfolio_returns_empty_holdings_for_new_user(api_context) -> None:
    client, _session, current_user = api_context

    response = client.get("/api/portfolio/snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == current_user.id
    assert payload["currency"] == "credit"
    assert payload["holdings"] == []
    assert Decimal(str(payload["available_balance"])) == Decimal("0.0000")
    assert Decimal(str(payload["reserved_balance"])) == Decimal("0.0000")
    assert Decimal(str(payload["total_balance"])) == Decimal("0.0000")


def test_get_wallet_summary_returns_available_reserved_and_total_balances(api_context) -> None:
    client, session, current_user = api_context
    player = _create_player(session)
    _fund_user(session, current_user, amount=Decimal("100"))

    order_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "buy",
            "quantity": 10,
            "max_price": 5,
        },
    )
    assert order_response.status_code == 201

    response = client.get("/api/wallets/summary")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "available_balance",
        "reserved_balance",
        "total_balance",
        "currency",
    }
    assert payload["currency"] == "credit"
    assert Decimal(str(payload["available_balance"])) == Decimal("50.0000")
    assert Decimal(str(payload["reserved_balance"])) == Decimal("50.0000")
    assert Decimal(str(payload["total_balance"])) == Decimal("100.0000")


def test_list_wallet_ledger_returns_latest_entries_first(api_context) -> None:
    client, session, current_user = api_context
    player = _create_player(session, provider_external_id="player-wallet-ledger")
    _fund_user(session, current_user, amount=Decimal("100"))

    order_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "buy",
            "quantity": 10,
            "max_price": 5,
        },
    )
    assert order_response.status_code == 201

    response = client.get("/api/wallets/ledger", params={"page": 1, "page_size": 3})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"page", "page_size", "total", "items"}
    assert payload["page"] == 1
    assert payload["page_size"] == 3
    assert payload["total"] == 3
    assert len(payload["items"]) == 3
    assert set(payload["items"][0]) == {
        "id",
        "transaction_id",
        "account_id",
        "amount",
        "unit",
        "reason",
        "reference",
        "external_reference",
        "description",
        "created_at",
    }
    assert all(item["reason"] == "withdrawal_hold" for item in payload["items"][:2])
    assert payload["items"][2]["reason"] == "adjustment"


def test_api_wallet_accounts_and_payment_event_contracts(api_context) -> None:
    client, _session, _current_user = api_context

    accounts_response = client.get("/api/wallets/accounts")
    payment_event_response = client.post(
        "/api/wallets/payment-events",
        json={
            "provider": "monnify",
            "provider_reference": "monnify-ref-001",
            "amount": "50.0000",
            "pack_code": "starter-50",
        },
    )

    assert accounts_response.status_code == 200
    accounts_payload = accounts_response.json()
    assert len(accounts_payload) == 2
    assert set(accounts_payload[0]) == {
        "id",
        "code",
        "label",
        "unit",
        "kind",
        "allow_negative",
        "is_active",
        "balance",
    }

    assert payment_event_response.status_code == 201
    payment_payload = payment_event_response.json()
    assert set(payment_payload) == {
        "id",
        "provider",
        "provider_reference",
        "pack_code",
        "amount",
        "unit",
        "status",
        "created_at",
        "verified_at",
        "processed_at",
        "ledger_transaction_id",
    }
    assert payment_payload["provider"] == "monnify"
    assert payment_payload["status"] == "pending"


def test_create_trade_withdrawal_request_reserves_balance(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("100"))

    response = client.post(
        "/api/wallets/withdrawals",
        json={
            "amount": 20,
            "unit": "credit",
            "source_scope": "trade",
            "destination_reference": "bank:0012345678",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["source_scope"] == "trade"
    assert Decimal(str(payload["fee_amount"])) == Decimal("5.0000")
    assert Decimal(str(payload["total_debit"])) == Decimal("25.0000")


def test_create_competition_withdrawal_request_is_blocked_by_default(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("100"))

    response = client.post(
        "/api/wallets/withdrawals",
        json={
            "amount": 20,
            "unit": "credit",
            "source_scope": "competition",
            "destination_reference": "bank:0012345678",
        },
    )

    assert response.status_code == 409
    assert "locked" in response.json()["detail"].lower()


def test_create_trade_withdrawal_request_requires_bank_reference_in_manual_mode(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("100"))

    response = client.post(
        "/api/wallets/withdrawals",
        json={
            "amount": 20,
            "unit": "credit",
            "source_scope": "trade",
            "destination_reference": "acct-0012345678",
        },
    )

    assert response.status_code == 422
    assert "bank:" in response.json()["detail"].lower()


def test_create_trade_withdrawal_request_uses_processing_when_gateway_mode_enabled(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("100"))
    client.app.state.settings = SimpleNamespace(config_root=Path(session.bind.url.database).parent)
    (client.app.state.settings.config_root / "admin_god_mode.json").write_text(
        '{"commissions":{"withdrawal_fee_bps":1000,"minimum_withdrawal_fee_credits":"5.0000"},"withdrawal_controls":{"egame_withdrawals_enabled":false,"trade_withdrawals_enabled":true,"processor_mode":"automatic_gateway","deposits_via_bank_transfer":false,"payouts_via_bank_transfer":false}}',
        encoding="utf-8",
    )

    response = client.post(
        "/api/wallets/withdrawals",
        json={
            "amount": 20,
            "unit": "credit",
            "source_scope": "trade",
            "destination_reference": "gateway:user-bank-token",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "processing"
    assert payload["processing_mode"] == "automatic_gateway"
    assert payload["payout_channel"] == "gateway"


def test_wallet_adaptive_overview_surfaces_withdrawal_policy(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("50"))
    client.app.state.settings = SimpleNamespace(config_root=Path(session.bind.url.database).parent)
    (client.app.state.settings.config_root / "admin_god_mode.json").write_text(
        '{"withdrawal_controls":{"egame_withdrawals_enabled":true,"trade_withdrawals_enabled":true,"processor_mode":"manual_bank_transfer","deposits_via_bank_transfer":true,"payouts_via_bank_transfer":true}}',
        encoding="utf-8",
    )

    response = client.get("/api/wallets/adaptive-overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["processor_mode"] == "manual_bank_transfer"
    assert payload["egame_withdrawals_enabled"] is True
    labels = {item["label"]: item["value"] for item in payload["insights"]}
    assert labels["Withdrawal rail"] == "Bank transfer"
    assert labels["E-game cash-out"] == "Enabled"
