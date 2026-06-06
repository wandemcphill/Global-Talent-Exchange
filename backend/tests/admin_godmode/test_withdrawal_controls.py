from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.tests.support.secrets import TEST_PASSWORD
from app.admin_godmode.router import router as admin_router
from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.auth.service import AuthService
from app.models.treasury import PaymentMode
from app.models.user import KycStatus, UserRole
from app.policies.service import PolicyService
from app.treasury.service import GTEX_PLATFORM_POSITIONING, TreasuryService
from app.wallets.router import router as wallet_router
from app.wallets.service import LedgerPosting, WalletService
from app.models.wallet import LedgerEntryReason, LedgerUnit


@pytest.fixture()
def admin_wallet_context(tmp_path: Path, gtex_db_session_factory):
    # Shared session-scoped schema (tests/conftest.py::gtex_db_engine) with
    # per-test rollback, instead of rebuilding all ~567 tables per test.
    SessionLocal = gtex_db_session_factory
    session = SessionLocal()
    auth = AuthService()
    admin_user = auth.register_user(
        session,
        email="admin-god@example.com",
        region_code="NG",
        username="admingod",
        password=TEST_PASSWORD,
        role=UserRole.ADMIN,
    )
    trader = auth.register_user(
        session,
        email="wallet-user@example.com",
        region_code="NG",
        username="walletuser",
        password=TEST_PASSWORD,
    )
    policy_service = PolicyService(session)
    policy_service.seed_defaults()
    for document in policy_service.list_documents(mandatory_only=True):
        version = policy_service.get_document(document.document_key)
        policy_service.accept_document(
            user_id=trader.id,
            document_key=document.document_key,
            version_label=version.version_label,
            ip_address="127.0.0.1",
            device_id="test-device",
        )
    trader.kyc_status = KycStatus.FULLY_VERIFIED
    TreasuryService().create_user_bank_account(
        session,
        user=trader,
        bank_name="Test Bank",
        account_number="0123456789",
        account_name="Wallet User",
        bank_code="001",
        currency_code="NGN",
        set_active=True,
    )
    session.commit()

    app = FastAPI()
    app.include_router(admin_router)
    app.include_router(wallet_router)
    app.state.settings = SimpleNamespace(config_root=tmp_path)
    app.state.session_factory = SessionLocal

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
    user_account = wallet_service.get_user_account(session, current_user, LedgerUnit.COIN)
    promo_pool_account = wallet_service.ensure_promo_pool_account(session, LedgerUnit.COIN)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=promo_pool_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="admin-godmode-promo-pool-topup",
        description="Top up promo pool for withdrawal testing",
        actor=current_user,
    )
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=promo_pool_account, amount=-amount),
        ],
        reason=LedgerEntryReason.COMPETITION_REWARD,
        reference="admin-godmode-competition-reward",
        description="Seed competition winnings for withdrawal testing",
        actor=current_user,
    )
    session.commit()


def _enable_automatic_deposits(session) -> None:
    settings = TreasuryService().ensure_settings(session)
    settings.deposit_mode = PaymentMode.AUTOMATIC
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
            "provider": "korapay",
            "provider_reference": "bank-manual-ref-001",
            "amount": "50.0000",
            "pack_code": "starter-50",
        },
    )

    assert response.status_code == 409
    assert "deposits are disabled" in response.json()["detail"].lower()


def test_automatic_gateway_mode_allows_gateway_deposit_endpoint(admin_wallet_context) -> None:
    client, session, _admin_user, _trader = admin_wallet_context
    _enable_automatic_deposits(session)

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
            "provider": "korapay",
            "provider_reference": "gateway-ref-001",
            "amount": "50.0000",
            "pack_code": "starter-50",
        },
    )

    assert response.status_code == 201
    assert response.json()["provider"] == "korapay"


def test_competition_withdrawal_can_be_enabled_for_bank_transfer_review(admin_wallet_context) -> None:
    client, session, _admin_user, trader = admin_wallet_context
    _fund_competition_rewards(session, trader, amount=Decimal("100"))
    bank_account = TreasuryService().ensure_user_bank_account(session, trader)
    assert bank_account is not None

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
            "amount_coin": 20,
            "bank_account_id": bank_account.id,
            "source_scope": "competition",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "pending_review"
    assert payload["processor_mode"] == "manual_bank_transfer"
    assert payload["payout_channel"] == "bank_transfer"
    assert payload["platform_positioning"] == GTEX_PLATFORM_POSITIONING
    assert payload["legal_disclosures"] == [
        "No guaranteed profit.",
        "Prices are volatile.",
        "Platform controls mechanics.",
        "Rewards are promotional for GTEX competitions.",
    ]
