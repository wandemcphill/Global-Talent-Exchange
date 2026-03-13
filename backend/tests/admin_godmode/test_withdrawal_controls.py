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
from backend.app.admin_godmode.router import router as admin_router
from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.auth.service import AuthService
from backend.app.models.base import Base
from backend.app.models.user import UserRole
from backend.app.wallets.router import router as wallet_router
from backend.app.wallets.service import LedgerPosting, WalletService
from backend.app.models.wallet import LedgerEntryReason, LedgerUnit


@pytest.fixture()
def admin_wallet_context(tmp_path: Path):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    auth = AuthService()
    admin_user = auth.register_user(
        session,
        email="admin-god@example.com",
        username="admingod",
        password="SuperSecret1",
        role=UserRole.ADMIN,
    )
    trader = auth.register_user(
        session,
        email="wallet-user@example.com",
        username="walletuser",
        password="SuperSecret1",
    )
    session.commit()

    app = FastAPI()
    app.include_router(admin_router)
    app.include_router(wallet_router)
    app.state.settings = SimpleNamespace(config_root=tmp_path)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: admin_user
    app.dependency_overrides[get_current_user] = lambda: trader

    with TestClient(app) as client:
        yield client, session, admin_user, trader

    session.close()


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
        reference="admin-godmode-funding",
        description="Seed wallet credits for testing",
        actor=current_user,
    )
    session.commit()


def _fund_competition_rewards(session, current_user, *, amount: Decimal) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, current_user, LedgerUnit.CREDIT)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.COMPETITION_REWARD,
        reference="admin-godmode-competition-reward",
        description="Seed competition winnings for withdrawal testing",
        actor=current_user,
    )
    session.commit()


def test_admin_can_update_withdrawal_controls_and_competition_topup(admin_wallet_context) -> None:
    client, _session, _admin_user, _trader = admin_wallet_context

    withdrawal_response = client.put(
        "/api/admin/god-mode/withdrawal-controls",
        json={
            "egame_withdrawals_enabled": True,
            "trade_withdrawals_enabled": True,
            "processor_mode": "automatic_gateway",
            "deposits_via_bank_transfer": False,
            "payouts_via_bank_transfer": False,
            "reason": "Switching to automatic gateway for smoke test",
        },
    )
    competition_response = client.put(
        "/api/admin/god-mode/competition-controls",
        json={
            "prize_pool_topup_pct": "12.50",
            "reason": "Boost launch-week arenas",
        },
    )

    assert withdrawal_response.status_code == 200
    assert competition_response.status_code == 200
    assert withdrawal_response.json()["processor_mode"] == "automatic_gateway"
    assert withdrawal_response.json()["egame_withdrawals_enabled"] is True
    assert competition_response.json()["prize_pool_topup_pct"] == "12.50"


def test_manual_bank_transfer_mode_blocks_gateway_deposit_endpoint(admin_wallet_context) -> None:
    client, _session, _admin_user, _trader = admin_wallet_context

    response = client.post(
        "/api/wallets/payment-events",
        json={
            "provider": "monnify",
            "provider_reference": "bank-manual-ref-001",
            "amount": "50.0000",
            "pack_code": "starter-50",
        },
    )

    assert response.status_code == 409
    assert "manual bank transfer" in response.json()["detail"].lower()


def test_automatic_gateway_mode_allows_gateway_deposit_endpoint(admin_wallet_context) -> None:
    client, _session, _admin_user, _trader = admin_wallet_context

    client.put(
        "/api/admin/god-mode/withdrawal-controls",
        json={
            "egame_withdrawals_enabled": False,
            "trade_withdrawals_enabled": True,
            "processor_mode": "automatic_gateway",
            "deposits_via_bank_transfer": False,
            "payouts_via_bank_transfer": False,
            "reason": "Enable automatic rails",
        },
    )

    response = client.post(
        "/api/wallets/payment-events",
        json={
            "provider": "monnify",
            "provider_reference": "gateway-ref-001",
            "amount": "50.0000",
            "pack_code": "starter-50",
        },
    )

    assert response.status_code == 201
    assert response.json()["provider"] == "monnify"


def test_competition_withdrawal_can_be_enabled_for_bank_transfer_review(admin_wallet_context) -> None:
    client, session, _admin_user, trader = admin_wallet_context
    _fund_competition_rewards(session, trader, amount=Decimal("100"))

    client.put(
        "/api/admin/god-mode/withdrawal-controls",
        json={
            "egame_withdrawals_enabled": True,
            "trade_withdrawals_enabled": True,
            "processor_mode": "manual_bank_transfer",
            "deposits_via_bank_transfer": True,
            "payouts_via_bank_transfer": True,
            "reason": "Enable e-game cash-out with manual review",
        },
    )

    response = client.post(
        "/api/wallets/withdrawals",
        json={
            "amount": 20,
            "unit": "credit",
            "source_scope": "competition",
            "destination_reference": "bank:0123456789",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "reviewing"
    assert payload["processing_mode"] == "manual_bank_transfer"
    assert payload["payout_channel"] == "bank_transfer"
