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

import app.ingestion.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.models  # noqa: F401
import app.orders.models  # noqa: F401
from app.auth.dependencies import get_current_user, get_session
from app.auth.service import AuthService
from app.ingestion.models import Player
from app.models.base import Base
from app.models.treasury import PaymentMode
from app.policies.service import PolicyService
from app.services.runtime_control_service import RuntimeControlService
from app.treasury.service import GTEX_PLATFORM_POSITIONING, TreasuryService
from app.wallets.router import router
from app.wallets.service import LedgerPosting, WalletService
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.models.user import KycStatus


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
        region_code="NG",
        username="wallethttp",
        password="SuperSecret1",
    )
    session.commit()
    _seed_policy_defaults(session, current_user)

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


def _fund_user(session, current_user, *, amount: Decimal, unit: LedgerUnit = LedgerUnit.CREDIT) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, current_user, unit)
    platform_account = wallet_service.ensure_platform_account(session, unit)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="wallet-http-funding",
        description=f"Seed wallet {unit.value}s for testing",
        actor=current_user,
    )
    session.commit()


def _seed_policy_defaults(session, current_user) -> None:
    service = PolicyService(session)
    service.seed_defaults()
    profile = service.ensure_user_region_profile(user=current_user, region_code="NG")
    profile.region_code = "NG"
    for version in service.list_missing_acceptances(user_id=current_user.id):
        service.accept_document(
            user_id=current_user.id,
            document_key=version.document.document_key,
            version_label=version.version_label,
            ip_address=None,
            device_id=None,
        )
    session.commit()


def _enable_automatic_deposits(session) -> None:
    settings = TreasuryService().ensure_settings(session)
    settings.deposit_mode = PaymentMode.AUTOMATIC
    session.commit()


def _enable_automatic_withdrawals(session) -> None:
    settings = TreasuryService().ensure_settings(session)
    settings.withdrawal_mode = PaymentMode.AUTOMATIC
    session.commit()


def _provision_withdrawable_user(session, current_user) -> None:
    treasury = TreasuryService()
    treasury.create_user_bank_account(
        session,
        user=current_user,
        bank_name="GT Bank",
        account_number="0123456789",
        account_name="Wallet HTTP",
        bank_code="058",
        currency_code="NGN",
        set_active=True,
    )
    treasury.submit_kyc(
        session,
        user=current_user,
        nin="12345678901",
        bvn=None,
        address_line1="12 Marina",
        address_line2=None,
        city="Lagos",
        state="Lagos",
        country="Nigeria",
        id_document_attachment_id=None,
    )
    current_user.kyc_status = KycStatus.FULLY_VERIFIED
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
    _fund_user(session, current_user, amount=Decimal("100"), unit=LedgerUnit.COIN)

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

    response = client.get("/api/wallets/summary", params={"currency": "coin"})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "available_balance",
        "reserved_balance",
        "total_balance",
        "currency",
    }
    assert payload["currency"] == "coin"
    assert Decimal(str(payload["available_balance"])) == Decimal("50.0000")
    assert Decimal(str(payload["reserved_balance"])) == Decimal("50.0000")
    assert Decimal(str(payload["total_balance"])) == Decimal("100.0000")


def test_list_wallet_ledger_returns_latest_entries_first(api_context) -> None:
    client, session, current_user = api_context
    player = _create_player(session, provider_external_id="player-wallet-ledger")
    _fund_user(session, current_user, amount=Decimal("100"), unit=LedgerUnit.COIN)

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
        "transaction_type",
        "reason",
        "source_tag",
        "reference",
        "external_reference",
        "description",
        "created_at",
    }
    assert all(item["reason"] == "withdrawal_hold" for item in payload["items"][:2])
    assert payload["items"][2]["reason"] == "adjustment"


def test_api_wallet_accounts_and_payment_event_contracts(api_context) -> None:
    client, session, _current_user = api_context
    _enable_automatic_deposits(session)

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


def test_payment_event_rejects_when_wallet_transaction_lock_exists(api_context) -> None:
    client, session, current_user = api_context
    _enable_automatic_deposits(session)
    RuntimeControlService(client.app).acquire_wallet_transaction_lock(
        user_id=current_user.id,
        operation="payment_event_create",
        ttl_seconds=120,
        updated_by_user_id=current_user.id,
    )

    response = client.post(
        "/api/wallets/payment-events",
        json={
            "provider": "monnify",
            "provider_reference": "monnify-ref-locked",
            "amount": "50.0000",
            "pack_code": "starter-50",
        },
    )

    assert response.status_code == 409
    assert "another wallet transaction is already in progress" in response.json()["detail"].lower()


def test_create_trade_withdrawal_request_reserves_balance(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("100"), unit=LedgerUnit.COIN)
    _provision_withdrawable_user(session, current_user)

    response = client.post(
        "/api/wallets/withdrawals",
        json={
            "amount_coin": "20.0000",
            "source_scope": "trade",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["source_scope"] == "trade"
    assert payload["status"] == "pending_review"
    assert payload["processor_mode"] == "manual_bank_transfer"
    assert Decimal(str(payload["fee_amount"])) == Decimal("5.0000")
    assert Decimal(str(payload["total_debit"])) == Decimal("25.0000")


def test_create_competition_withdrawal_request_is_blocked_by_default(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("100"), unit=LedgerUnit.COIN)
    _provision_withdrawable_user(session, current_user)

    response = client.post(
        "/api/wallets/withdrawals",
        json={
            "amount_coin": "20.0000",
            "source_scope": "competition",
        },
    )

    assert response.status_code == 409
    assert "e-game reward withdrawals" in response.json()["detail"].lower()


def test_create_trade_withdrawal_request_requires_bank_account_details(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("100"), unit=LedgerUnit.COIN)
    current_user.kyc_status = KycStatus.FULLY_VERIFIED
    session.commit()

    response = client.post(
        "/api/wallets/withdrawals",
        json={
            "amount_coin": "20.0000",
            "source_scope": "trade",
        },
    )

    assert response.status_code == 409
    assert "bank account details are required" in response.json()["detail"].lower()


def test_create_trade_withdrawal_request_uses_processing_when_gateway_mode_enabled(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("100"), unit=LedgerUnit.COIN)
    _provision_withdrawable_user(session, current_user)
    _enable_automatic_withdrawals(session)
    client.app.state.settings = SimpleNamespace(config_root=Path(session.bind.url.database).parent)
    (client.app.state.settings.config_root / "admin_god_mode.json").write_text(
        '{"commissions":{"withdrawal_fee_bps":1000,"minimum_withdrawal_fee_credits":"5.0000"},"withdrawal_controls":{"egame_withdrawals_enabled":false,"trade_withdrawals_enabled":true,"processor_mode":"automatic_gateway","deposits_via_bank_transfer":false,"payouts_via_bank_transfer":false}}',
        encoding="utf-8",
    )

    response = client.post(
        "/api/wallets/withdrawals",
        json={
            "amount_coin": "20.0000",
            "source_scope": "trade",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "pending_review"
    assert payload["processor_mode"] == "automatic_gateway"
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


def test_withdrawal_quote_and_receipt_include_fee_breakdown(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("120"), unit=LedgerUnit.COIN)
    _provision_withdrawable_user(session, current_user)

    quote_response = client.post(
        "/api/wallets/withdrawals/quote",
        json={"amount_coin": "20.0000", "source_scope": "trade"},
    )
    assert quote_response.status_code == 200, quote_response.text
    quote_payload = quote_response.json()
    assert Decimal(str(quote_payload["gross_amount"])) == Decimal("20.0000")
    assert Decimal(str(quote_payload["fee_amount"])) == Decimal("5.0000")
    assert Decimal(str(quote_payload["total_debit"])) == Decimal("25.0000")

    response = client.post(
        "/api/wallets/withdrawals",
        json={"amount_coin": "20.0000", "source_scope": "trade"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["source_scope"] == "trade"
    assert payload["processor_mode"] == "manual_bank_transfer"
    assert Decimal(str(payload["fee_amount"])) == Decimal("5.0000")
    assert payload["platform_positioning"] == GTEX_PLATFORM_POSITIONING
    assert payload["legal_disclosures"] == [
        "No guaranteed profit.",
        "Prices are volatile.",
        "Platform controls mechanics.",
        "Rewards are promotional for GTEX competitions.",
    ]

    receipt_response = client.get(f"/api/wallets/withdrawals/{payload['id']}/receipt")
    assert receipt_response.status_code == 200, receipt_response.text
    receipt = receipt_response.json()
    assert receipt["withdrawal"]["id"] == payload["id"]
    assert Decimal(str(receipt["gross_amount"])) == Decimal("20.0000")
    assert Decimal(str(receipt["fee_amount"])) == Decimal("5.0000")
    assert Decimal(str(receipt["total_debit"])) == Decimal("25.0000")
    assert receipt["platform_positioning"] == GTEX_PLATFORM_POSITIONING
