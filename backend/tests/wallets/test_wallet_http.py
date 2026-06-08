from __future__ import annotations

from decimal import Decimal
import hashlib
import hmac
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
import pytest

import app.ingestion.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.models  # noqa: F401
import app.orders.models  # noqa: F401
from app.admin_godmode.runtime_paths import admin_godmode_state_path
from app.auth.dependencies import get_current_user, get_session
from app.auth.service import AuthService
from app.ingestion.models import Player
from app.models.fancoin_purchase_order import PurchaseOrderStatus
from app.models.policy import CountryFeaturePolicy, PolicyAcceptanceRecord
from app.models.risk_ops import AuditLog
from app.models.treasury import PaymentMode, RateDirection
from app.policies.service import PolicyService
from app.services.runtime_control_service import RuntimeControlService
from app.treasury.service import GTEX_PLATFORM_POSITIONING, TreasuryService
from app.wallets.router import router
from app.wallets.rail_service import WalletRailService
from app.wallets.service import LedgerPosting, WalletService
from app.models.wallet import LedgerEntryReason, LedgerTransactionType, LedgerUnit
from app.models.user import KycStatus


class FakeCacheBackend:
    enabled = True

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.values[key] = value

    def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            self.values.pop(key, None)

    def ping(self) -> bool:
        return True


@pytest.fixture()
def api_context(gtex_db_session):
    # Shared session-scoped schema (tests/conftest.py::gtex_db_engine) with
    # per-test rollback, instead of rebuilding all ~567 tables per test.
    session = gtex_db_session
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
    app.state.settings = SimpleNamespace(config_root=None)

    def override_session():
        yield session

    def override_current_user():
        return current_user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(app) as client:
        yield client, session, current_user


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


def _configure_korapay_purchase_settings(session) -> None:
    settings = TreasuryService().ensure_settings(session)
    settings.deposit_mode = PaymentMode.AUTOMATIC
    settings.deposit_rate_value = Decimal("1000.0000")
    settings.deposit_rate_direction = RateDirection.FIAT_PER_COIN
    settings.min_deposit = Decimal("0.0000")
    settings.max_deposit = Decimal("100000.0000")
    session.commit()


def _create_korapay_purchase_order(session, current_user, *, provider_reference: str = "korapay-webhook-ref-001"):
    _configure_korapay_purchase_settings(session)
    order = WalletRailService(session).create_purchase_order(
        user=current_user,
        settings=TreasuryService().ensure_settings(session),
        amount=Decimal("1000.0000"),
        input_unit="fiat",
        provider_key="korapay",
        source_scope="wallet",
        unit=LedgerUnit.COIN,
        processor_mode="automatic_gateway",
        payout_channel="gateway",
        provider_reference=provider_reference,
    )
    session.commit()
    return order


def _korapay_signature(payload: dict[str, object], secret: str) -> str:
    canonical_payload = json.dumps(payload["data"], separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical_payload, hashlib.sha256).hexdigest()


def _enable_hybrid_deposits(session) -> None:
    settings = TreasuryService().ensure_settings(session)
    settings.deposit_mode = PaymentMode.HYBRID
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
    assert payload["currency"] == "coin"
    assert payload["holdings"] == []
    assert Decimal(str(payload["available_balance"])) == Decimal("0.0000")
    assert Decimal(str(payload["reserved_balance"])) == Decimal("0.0000")
    assert Decimal(str(payload["total_balance"])) == Decimal("0.0000")


def test_get_wallet_summary_returns_available_reserved_and_total_balances(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("100"), unit=LedgerUnit.COIN)
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, current_user, LedgerUnit.COIN)
    escrow_account = wallet_service.get_user_escrow_account(session, current_user, LedgerUnit.COIN)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(
                account=user_account, amount=Decimal("-50"), transaction_type=LedgerTransactionType.WITHDRAWAL
            ),
            LedgerPosting(
                account=escrow_account, amount=Decimal("50"), transaction_type=LedgerTransactionType.WITHDRAWAL
            ),
        ],
        reason=LedgerEntryReason.WITHDRAWAL_HOLD,
        reference="wallet-http-summary-hold",
        description="Wallet HTTP summary hold",
        actor=current_user,
        transaction_type=LedgerTransactionType.WITHDRAWAL,
    )
    session.commit()

    response = client.get("/api/wallets/summary", params={"currency": "coin"})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "available_balance",
        "reserved_balance",
        "locked_balance",
        "pending_withdrawal_balance",
        "lock_reasons",
        "total_balance",
        "currency",
    }
    assert payload["currency"] == "coin"
    assert Decimal(str(payload["available_balance"])) == Decimal("50.0000")
    assert Decimal(str(payload["reserved_balance"])) == Decimal("50.0000")
    assert Decimal(str(payload["locked_balance"])) == Decimal("50.0000")
    assert Decimal(str(payload["pending_withdrawal_balance"])) == Decimal("0.0000")
    assert len(payload["lock_reasons"]) == 1
    lock_reason = payload["lock_reasons"][0]
    assert lock_reason["code"] == "wallet_hold"
    assert lock_reason["label"] == "Wallet holds"
    assert Decimal(str(lock_reason["amount"])) == Decimal("50.0000")
    assert lock_reason["currency"] == "coin"
    assert lock_reason["source"] == "wallet"
    assert lock_reason["reference"]
    assert lock_reason["message"] == "Wallet holds: 50.0000 coin"
    assert Decimal(str(payload["total_balance"])) == Decimal("100.0000")


def test_list_wallet_ledger_returns_latest_entries_first(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("100"), unit=LedgerUnit.COIN)
    WalletService().request_payout(
        session,
        user=current_user,
        amount=Decimal("50"),
        destination_reference="bank:test-wallet-ledger",
        unit=LedgerUnit.COIN,
        actor=current_user,
    )
    session.commit()

    response = client.get("/api/wallets/ledger", params={"page": 1, "page_size": 3})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"page", "page_size", "total", "items"}
    assert payload["page"] == 1
    assert payload["page_size"] == 3
    assert payload["total"] == 5
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
    assert all(item["reason"] == "withdrawal_hold" for item in payload["items"])


def test_api_wallet_accounts_and_payment_event_contracts(api_context) -> None:
    client, session, _current_user = api_context
    _enable_automatic_deposits(session)

    accounts_response = client.get("/api/wallets/accounts")
    payment_event_response = client.post(
        "/api/wallets/payment-events",
        json={
            "provider": "korapay",
            "provider_reference": "korapay-ref-001",
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
    assert payment_payload["provider"] == "korapay"
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
            "provider": "korapay",
            "provider_reference": "korapay-ref-locked",
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
    assert Decimal(str(payload["fee_amount"])) == Decimal("2.0000")
    assert Decimal(str(payload["net_amount"])) == Decimal("18.0000")
    assert Decimal(str(payload["total_debit"])) == Decimal("20.0000")

    overview_response = client.get("/api/wallets/overview")
    assert overview_response.status_code == 200, overview_response.text
    overview = overview_response.json()
    assert Decimal(str(overview["available_balance"])) == Decimal("80.0000")
    assert Decimal(str(overview["reserved_balance"])) == Decimal("20.0000")
    assert Decimal(str(overview["locked_balance"])) == Decimal("20.0000")
    assert Decimal(str(overview["pending_withdrawal_balance"])) == Decimal("20.0000")
    assert Decimal(str(overview["pending_withdrawals"])) == Decimal("20.0000")
    assert len(overview["lock_reasons"]) == 1
    lock_reason = overview["lock_reasons"][0]
    assert lock_reason["code"] == "withdrawal_hold"
    assert lock_reason["label"] == "Withdrawal holds"
    assert Decimal(str(lock_reason["amount"])) == Decimal("20.0000")
    assert lock_reason["currency"] == "coin"
    assert lock_reason["source"] == "withdrawal"
    assert str(lock_reason["reference"]).startswith("payout-request:")
    assert lock_reason["message"] == "Withdrawal holds: 20.0000 coin"


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


def test_create_competition_withdrawal_request_applies_reward_fee_policy(api_context) -> None:
    client, session, current_user = api_context
    _provision_withdrawable_user(session, current_user)
    client.app.state.settings = SimpleNamespace(config_root=Path(session.bind.engine.url.database).parent)
    state_path = admin_godmode_state_path(client.app.state.settings.config_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        '{"withdrawal_controls":{"egame_withdrawals_enabled":true,"trade_withdrawals_enabled":true,"processor_mode":"manual_bank_transfer","deposits_via_bank_transfer":true,"payouts_via_bank_transfer":true}}',
        encoding="utf-8",
    )
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, current_user, LedgerUnit.COIN)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("50")),
            LedgerPosting(account=platform_account, amount=Decimal("-50")),
        ],
        reason=LedgerEntryReason.COMPETITION_REWARD,
        reference="wallet-http-competition-reward",
        actor=current_user,
    )
    session.commit()

    response = client.post(
        "/api/wallets/withdrawals",
        json={
            "amount_coin": "20.0000",
            "source_scope": "competition",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["source_scope"] == "competition"
    assert payload["processor_mode"] == "manual_bank_transfer"
    assert payload["payout_channel"] == "bank_transfer"
    assert Decimal(str(payload["amount_coin"])) == Decimal("20.0000")
    assert Decimal(str(payload["fee_amount"])) == Decimal("2.0000")
    assert Decimal(str(payload["net_amount"])) == Decimal("18.0000")
    assert Decimal(str(payload["total_debit"])) == Decimal("20.0000")

    adaptive_response = client.get("/api/wallets/adaptive-overview")
    assert adaptive_response.status_code == 200, adaptive_response.text
    adaptive = adaptive_response.json()
    assert Decimal(str(adaptive["competition_reward_balance"])) == Decimal("50.0000")
    assert Decimal(str(adaptive["competition_reward_withdrawable_balance"])) == Decimal("30.0000")


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


def test_create_trade_withdrawal_request_stays_manual_when_gateway_mode_enabled(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("100"), unit=LedgerUnit.COIN)
    _provision_withdrawable_user(session, current_user)
    _enable_automatic_withdrawals(session)
    client.app.state.settings = SimpleNamespace(config_root=Path(session.bind.engine.url.database).parent)
    state_path = admin_godmode_state_path(client.app.state.settings.config_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        '{"withdrawal_controls":{"egame_withdrawals_enabled":false,"trade_withdrawals_enabled":true,"processor_mode":"manual_bank_transfer","deposits_via_bank_transfer":true,"payouts_via_bank_transfer":true}}',
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
    assert payload["processor_mode"] == "manual_bank_transfer"
    assert payload["payout_channel"] == "bank_transfer"


def test_wallet_adaptive_overview_surfaces_withdrawal_policy(api_context) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("50"))
    client.app.state.settings = SimpleNamespace(config_root=Path(session.bind.engine.url.database).parent)
    state_path = admin_godmode_state_path(client.app.state.settings.config_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        '{"withdrawal_controls":{"egame_withdrawals_enabled":true,"trade_withdrawals_enabled":true,"processor_mode":"manual_bank_transfer","deposits_via_bank_transfer":true,"payouts_via_bank_transfer":true}}',
        encoding="utf-8",
    )

    response = client.get("/api/wallets/adaptive-overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["processor_mode"] == "manual_bank_transfer"
    assert payload["egame_withdrawals_enabled"] is True
    labels = {item["label"]: item["value"] for item in payload["insights"]}
    assert labels["Withdrawal rail"] == "Manual bank transfer"
    assert labels["E-game cash-out"] == "Enabled"


def test_wallet_overview_surfaces_provider_status_and_live_restrictions(api_context, monkeypatch) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("50"), unit=LedgerUnit.COIN)
    _enable_automatic_deposits(session)
    monkeypatch.delenv("GTE_KORAPAY_SECRET_KEY", raising=False)
    monkeypatch.delenv("KORAPAY_SECRET_KEY", raising=False)
    monkeypatch.delenv("GTE_KORAPAY_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("KORAPAY_PRIVATE_KEY", raising=False)
    client.app.state.settings = SimpleNamespace(config_root=Path(session.bind.engine.url.database).parent)
    state_path = admin_godmode_state_path(client.app.state.settings.config_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        '{"withdrawal_controls":{"egame_withdrawals_enabled":true,"trade_withdrawals_enabled":true,"processor_mode":"automatic_gateway","deposits_via_bank_transfer":false,"payouts_via_bank_transfer":false}}',
        encoding="utf-8",
    )

    response = client.get("/api/wallets/overview")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["country_code"] == "NG"
    assert Decimal(str(payload["available_balance"])) == Decimal("50.0000")
    assert Decimal(str(payload["reserved_balance"])) == Decimal("0.0000")
    assert Decimal(str(payload["locked_balance"])) == Decimal("0.0000")
    assert Decimal(str(payload["pending_withdrawal_balance"])) == Decimal("0.0000")
    assert payload["lock_reasons"] == []
    assert payload["required_policy_acceptances_missing"] == 0
    assert payload["policy_blocked"] is False
    assert payload["deposit_mode"] == "gateway"
    assert payload["withdrawal_mode"] == "bank_transfer"
    assert set(payload["payment_provider_status"]) == {"bank_transfer_manual", "korapay"}
    assert payload["payment_provider_status"]["bank_transfer_manual"] == "blocked"
    assert payload["payment_provider_status"]["korapay"] == "unavailable"


def test_wallet_overview_supports_hybrid_bank_transfer_and_korapay(api_context, monkeypatch) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("50"), unit=LedgerUnit.COIN)
    _enable_hybrid_deposits(session)
    monkeypatch.setenv("GTE_KORAPAY_SECRET_KEY", "sk_test_launch")
    client.app.state.settings = SimpleNamespace(config_root=Path(session.bind.engine.url.database).parent)
    state_path = admin_godmode_state_path(client.app.state.settings.config_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        '{"withdrawal_controls":{"egame_withdrawals_enabled":true,"trade_withdrawals_enabled":true,"processor_mode":"manual_bank_transfer","deposits_via_bank_transfer":true,"payouts_via_bank_transfer":true}}',
        encoding="utf-8",
    )

    response = client.get("/api/wallets/overview")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["deposit_mode"] == "hybrid"
    assert set(payload["payment_provider_status"]) == {"bank_transfer_manual", "korapay"}
    assert payload["payment_provider_status"]["bank_transfer_manual"] == "ready"
    assert payload["payment_provider_status"]["korapay"] == "ready"


def test_manual_deposit_request_is_not_blocked_by_missing_policy_acceptance(api_context) -> None:
    client, session, current_user = api_context
    session.execute(delete(PolicyAcceptanceRecord).where(PolicyAcceptanceRecord.user_id == current_user.id))
    session.commit()

    response = client.post(
        "/api/wallets/deposits",
        json={
            "amount": "4500.0000",
            "input_unit": "fiat",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "awaiting_payment"
    assert Decimal(str(payload["amount_coin"])) == Decimal("5.0000")


def test_wallet_overview_marks_missing_korapay_secret_unavailable_in_production(api_context, monkeypatch) -> None:
    client, session, current_user = api_context
    _fund_user(session, current_user, amount=Decimal("50"), unit=LedgerUnit.COIN)
    _enable_automatic_deposits(session)
    monkeypatch.setenv("GTE_APP_ENV", "production")
    monkeypatch.delenv("GTE_KORAPAY_SECRET_KEY", raising=False)
    monkeypatch.delenv("KORAPAY_SECRET_KEY", raising=False)
    monkeypatch.delenv("GTE_KORAPAY_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("KORAPAY_PRIVATE_KEY", raising=False)
    client.app.state.settings = SimpleNamespace(config_root=Path(session.bind.engine.url.database).parent)
    state_path = admin_godmode_state_path(client.app.state.settings.config_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        '{"withdrawal_controls":{"egame_withdrawals_enabled":true,"trade_withdrawals_enabled":true,"processor_mode":"automatic_gateway","deposits_via_bank_transfer":false,"payouts_via_bank_transfer":false}}',
        encoding="utf-8",
    )

    response = client.get("/api/wallets/overview")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload["payment_provider_status"]) == {"bank_transfer_manual", "korapay"}
    assert payload["payment_provider_status"]["bank_transfer_manual"] == "blocked"
    assert payload["payment_provider_status"]["korapay"] == "unavailable"


def test_wallet_overview_and_eligibility_block_null_cached_balance(api_context) -> None:
    client, _, current_user = api_context
    cache_backend = FakeCacheBackend()
    client.app.state.cache_backend = cache_backend
    cache_backend.values[WalletService._wallet_summary_cache_key(current_user.id, LedgerUnit.COIN)] = json.dumps(
        {
            "user_id": current_user.id,
            "currency": LedgerUnit.COIN.value,
            "balance": None,
            "locked": "0.0000",
            "total": "0.0000",
        }
    )

    for path in ("/api/wallets/overview", "/api/wallets/withdrawals/eligibility"):
        response = client.get(path)

        assert response.status_code == 503, response.text
        assert response.json()["detail"] == "Balance data unavailable — sync in progress."


def test_korapay_provider_webhook_requires_valid_signature(api_context, monkeypatch) -> None:
    client, session, current_user = api_context
    secret = "wallet-webhook-signature-secret"
    monkeypatch.setenv("GTE_KORAPAY_WEBHOOK_SECRET", secret)
    monkeypatch.delenv("GTE_KORAPAY_WEBHOOK_SIGNATURE_OPTIONAL", raising=False)
    order = _create_korapay_purchase_order(
        session,
        current_user,
        provider_reference="korapay-webhook-signature-ref",
    )
    payload = {
        "event": "charge.success",
        "data": {
            "id": "kora-signature-event-1",
            "reference": order.provider_reference,
            "amount": "1000.0000",
            "currency": "NGN",
            "status": "success",
            "metadata": {"purchase_order_reference": order.reference},
        },
    }

    missing_signature = client.post("/wallets/providers/korapay/webhook", json=payload)
    invalid_signature = client.post(
        "/wallets/providers/korapay/webhook",
        json=payload,
        headers={"x-korapay-signature": "not-the-korapay-signature"},
    )
    session.refresh(order)
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, current_user, LedgerUnit.COIN)

    assert missing_signature.status_code == 401
    assert "signature header" in missing_signature.json()["detail"]
    assert invalid_signature.status_code == 401
    assert "signature is invalid" in invalid_signature.json()["detail"]
    assert order.status == PurchaseOrderStatus.PROCESSING
    assert order.ledger_transaction_id is None
    assert wallet_service.get_balance(session, user_account) == Decimal("0.0000")


def test_korapay_provider_webhook_duplicate_delivery_is_idempotent(api_context, monkeypatch) -> None:
    client, session, current_user = api_context
    secret = "wallet-webhook-idempotency-secret"
    monkeypatch.setenv("GTE_KORAPAY_WEBHOOK_SECRET", secret)
    monkeypatch.delenv("GTE_KORAPAY_WEBHOOK_SIGNATURE_OPTIONAL", raising=False)
    order = _create_korapay_purchase_order(
        session,
        current_user,
        provider_reference="korapay-webhook-idempotent-ref",
    )
    payload = {
        "event": "charge.success",
        "data": {
            "id": "kora-idempotent-event-1",
            "reference": order.provider_reference,
            "amount": "1000.0000",
            "currency": "NGN",
            "status": "success",
            "metadata": {"purchase_order_reference": order.reference},
        },
    }
    headers = {"x-korapay-signature": _korapay_signature(payload, secret)}

    first_delivery = client.post("/wallets/providers/korapay/webhook", json=payload, headers=headers)
    session.refresh(order)
    first_ledger_transaction_id = order.ledger_transaction_id
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, current_user, LedgerUnit.COIN)
    balance_after_first_delivery = wallet_service.get_balance(session, user_account)

    second_delivery = client.post("/wallets/providers/korapay/webhook", json=payload, headers=headers)
    session.refresh(order)
    webhook_audits = session.scalars(
        select(AuditLog).where(
            AuditLog.action_key == "wallet.purchase_order.webhook",
            AuditLog.resource_type == "purchase_order",
            AuditLog.resource_id == order.id,
        )
    ).all()

    assert first_delivery.status_code == 200, first_delivery.text
    assert second_delivery.status_code == 200, second_delivery.text
    assert first_delivery.json()["order_status"] == "settled"
    assert second_delivery.json()["order_status"] == "settled"
    assert order.status == PurchaseOrderStatus.SETTLED
    assert order.provider_event_id == "kora-idempotent-event-1"
    assert order.ledger_transaction_id == first_ledger_transaction_id
    assert wallet_service.get_balance(session, user_account) == balance_after_first_delivery
    assert balance_after_first_delivery == order.net_amount
    assert len(webhook_audits) == 1


@pytest.mark.parametrize("provider_key", ["paystack", "retired_gateway"])
def test_retired_provider_is_not_exposed_as_wallet_gateway(api_context, provider_key: str) -> None:
    client, session, _ = api_context
    _enable_automatic_deposits(session)

    top_up_response = client.post(
        "/wallets/top-up/initiate",
        json={
            "amount": "1000.0000",
            "provider": provider_key,
            "unit": "coin",
        },
    )
    webhook_response = client.post(f"/wallets/providers/{provider_key}/webhook", json={})
    quote_response = client.post(
        "/wallets/purchase-orders/quote",
        json={
            "amount": "1000.0000",
            "input_unit": "fiat",
            "provider_key": provider_key,
            "unit": "coin",
            "source_scope": "wallet",
        },
    )

    assert top_up_response.status_code == 404
    assert top_up_response.json()["detail"] == "Unknown payment provider."
    assert webhook_response.status_code == 404
    assert f"Unknown payment provider '{provider_key}'" in webhook_response.json()["detail"]
    assert quote_response.status_code == 404
    assert f"Unknown payment provider '{provider_key}'" in quote_response.json()["detail"]


def test_provider_webhook_rejects_stub_provider(api_context) -> None:
    client, _, _ = api_context

    response = client.post("/wallets/providers/cards/webhook", json={})

    assert response.status_code == 404
    assert "Unknown payment provider 'cards'" in response.json()["detail"]


def test_purchase_order_quote_rejects_stub_provider(api_context) -> None:
    client, _, _ = api_context

    response = client.post(
        "/wallets/purchase-orders/quote",
        json={
            "amount": "1000.0000",
            "input_unit": "fiat",
            "provider_key": "cards",
            "unit": "coin",
            "source_scope": "wallet",
        },
    )

    assert response.status_code == 404
    assert "Unknown payment provider 'cards'" in response.json()["detail"]


def test_wallet_overview_handles_missing_country_policy_rows(api_context) -> None:
    client, session, current_user = api_context
    policy_service = PolicyService(session)
    profile = policy_service.ensure_user_region_profile(user=current_user, region_code="US")
    profile.region_code = "US"
    session.execute(delete(CountryFeaturePolicy))
    session.commit()

    response = client.get("/api/wallets/overview")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert Decimal(str(payload["withdrawable_now"])) == Decimal("0.0000")


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
    assert Decimal(str(quote_payload["fee_amount"])) == Decimal("2.0000")
    assert Decimal(str(quote_payload["net_amount"])) == Decimal("18.0000")
    assert Decimal(str(quote_payload["total_debit"])) == Decimal("20.0000")

    response = client.post(
        "/api/wallets/withdrawals",
        json={"amount_coin": "20.0000", "source_scope": "trade"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["source_scope"] == "trade"
    assert payload["processor_mode"] == "manual_bank_transfer"
    assert Decimal(str(payload["fee_amount"])) == Decimal("2.0000")
    assert Decimal(str(payload["net_amount"])) == Decimal("18.0000")
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
    assert Decimal(str(receipt["fee_amount"])) == Decimal("2.0000")
    assert Decimal(str(receipt["net_amount"])) == Decimal("18.0000")
    assert Decimal(str(receipt["total_debit"])) == Decimal("20.0000")
    assert receipt["platform_positioning"] == GTEX_PLATFORM_POSITIONING
