from __future__ import annotations

import hmac
import json
from decimal import Decimal
from hashlib import sha256, sha512

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.tests.support.secrets import TEST_PASSWORD
from app.auth.service import AuthService, DuplicateUserError
from app.live_matches.service import ensure_live_match_hub
from app.main import INITIAL_ADMIN_DISPLAY_NAME, INITIAL_ADMIN_EMAIL, INITIAL_ADMIN_PASSWORD
from app.models import (
    CountryFeaturePolicy,
    EconomyBurnEvent,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerUnit,
    PlayerCardMomentum,
    User,
)
from app.models.competition_reward_pool import CompetitionRewardPool
from app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from app.models.treasury import PaymentMode
from app.models.wallet import PaymentStatus
from app.services.runtime_control_service import RuntimeControlService
from app.treasury.service import TreasuryService
from app.wallets.rail_service import WalletRailService
from app.wallets.service import LedgerPosting, WalletService


def _error_message(response) -> str:
    payload = response.json()
    return str(payload.get("message") or payload.get("detail") or "").lower()


def _prepare_admin(client, app_session_factory) -> None:
    startup_thread = getattr(client.app.state, "deferred_startup_thread", None)
    if startup_thread is not None and startup_thread.is_alive():
        startup_thread.join(timeout=5)
    with app_session_factory() as session:
        try:
            AuthService().ensure_admin_user(
                session,
                email=INITIAL_ADMIN_EMAIL,
                password=INITIAL_ADMIN_PASSWORD,
                username="finance-admin",
                display_name=INITIAL_ADMIN_DISPLAY_NAME,
            )
        except (DuplicateUserError, IntegrityError):
            session.rollback()
            assert session.scalar(select(User).where(User.email == INITIAL_ADMIN_EMAIL)) is not None
        if session.scalar(select(CountryFeaturePolicy).where(CountryFeaturePolicy.country_code == "GLOBAL")) is None:
            session.add(
                CountryFeaturePolicy(
                    country_code="GLOBAL",
                    bucket_type="default",
                    deposits_enabled=True,
                    market_trading_enabled=True,
                    platform_reward_withdrawals_enabled=True,
                    user_hosted_gift_withdrawals_enabled=True,
                    gtex_competition_gift_withdrawals_enabled=True,
                    national_reward_withdrawals_enabled=True,
                    one_time_region_change_after_days=180,
                    active=True,
                )
            )
        session.commit()


def _login_admin(client) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": INITIAL_ADMIN_EMAIL, "password": INITIAL_ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seed_finance_state(app_session_factory) -> tuple[str, str]:
    with app_session_factory() as session:
        user = AuthService().register_user(
            session,
            email="finance-user@example.com",
            username="financeuser",
            password=TEST_PASSWORD,
        )
        wallet_service = WalletService()
        treasury = TreasuryService()
        settings = treasury.ensure_settings(session)
        settings.deposit_mode = PaymentMode.AUTOMATIC
        user_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
        platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=Decimal("450.0000")),
                LedgerPosting(account=platform_account, amount=Decimal("-450.0000")),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            reference="finance-seed-balance",
            actor=user,
        )
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=Decimal("-25.0000")),
                LedgerPosting(account=platform_account, amount=Decimal("25.0000")),
            ],
            reason=LedgerEntryReason.COMPETITION_ENTRY,
            source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
            reference="finance-seed-match-entry",
            actor=user,
        )
        session.add(
            EconomyBurnEvent(
                user_id=user.id,
                source_type="gift",
                source_id="gift-1",
                amount=Decimal("15.0000"),
                unit=LedgerUnit.CREDIT,
                reason="fan_gift_burn",
                metadata_json={"channel": "live_match"},
            )
        )
        session.add(
            CompetitionRewardPool(
                competition_id="competition-1",
                pool_type="entry_fee",
                currency="coin",
                amount_minor=125_000,
                status="planned",
                metadata_json={},
            )
        )
        session.add(
            PlayerCardMomentum(
                player_id="player-1",
                last_trade_price_credits=Decimal("72.5000"),
                momentum_7d_pct=Decimal("18.4000"),
                momentum_30d_pct=Decimal("26.0000"),
                trend_direction="up",
                metadata_json={},
            )
        )
        rail_service = WalletRailService(session)
        order = rail_service.create_purchase_order(
            user=user,
            settings=settings,
            amount=Decimal("10000.0000"),
            input_unit="fiat",
            provider_key="paystack",
            source_scope="wallet",
            unit=LedgerUnit.COIN,
            processor_mode="automatic_gateway",
            payout_channel="gateway",
            provider_reference="ps_live_ref_snapshot",
            notes="seeded purchase order",
        )
        rail_service.settle_purchase_order(order=order, actor=user)
        session.commit()
        return user.id, order.reference


def _seed_paystack_order(app_session_factory) -> FancoinPurchaseOrder:
    return _seed_provider_order(
        app_session_factory,
        provider_key="paystack",
        provider_reference="ps_live_ref_webhook",
        email="paystack-user@example.com",
        username="paystackuser",
    )


def _seed_provider_order(
    app_session_factory,
    *,
    provider_key: str,
    provider_reference: str,
    email: str,
    username: str,
) -> FancoinPurchaseOrder:
    with app_session_factory() as session:
        existing = session.scalar(select(User).where(User.email == email))
        if existing is None:
            user = AuthService().register_user(
                session,
                email=email,
                username=username,
                password=TEST_PASSWORD,
            )
        else:
            user = session.get(User, existing.id)
        settings = TreasuryService().ensure_settings(session)
        settings.deposit_mode = PaymentMode.AUTOMATIC
        order = WalletRailService(session).create_purchase_order(
            user=user,
            settings=settings,
            amount=Decimal("9000.0000"),
            input_unit="fiat",
            provider_key=provider_key,
            source_scope="wallet",
            unit=LedgerUnit.COIN,
            processor_mode="automatic_gateway",
            payout_channel="gateway",
            provider_reference=provider_reference,
            notes="webhook pending order",
        )
        session.commit()
        session.refresh(order)
        return order


def _create_user_auth_headers(app_session_factory, *, email: str, username: str) -> tuple[str, dict[str, str]]:
    with app_session_factory() as session:
        existing = session.scalar(select(User).where(User.email == email))
        if existing is None:
            user = AuthService().register_user(
                session,
                email=email,
                username=username,
                password=TEST_PASSWORD,
            )
        else:
            user = session.get(User, existing.id)
        token, _ = AuthService().issue_access_token(user, session=session)
        session.commit()
        return user.id, {"Authorization": f"Bearer {token}"}


def test_control_tower_snapshot_returns_finance_metrics(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    _seed_finance_state(app_session_factory)
    headers = _login_admin(client)

    response = client.get("/api/admin/finance/control-tower", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert Decimal(payload["gtex_supply"]) > Decimal("0")
    assert Decimal(payload["daily_revenue_naira"]) > Decimal("0")
    assert payload["cash_rails"]["payment_methods"]
    assert {"Cards", "Apple Pay", "Google Pay"}.isdisjoint(payload["cash_rails"]["payment_methods"])
    assert len(payload["history"]) >= 7
    assert payload["projection"]["days"] == 30


def test_simulator_returns_30_day_projection(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)

    response = client.post(
        "/api/admin/finance/simulate",
        headers=headers,
        json={
            "daily_active_users": 25000,
            "avg_matches_per_user": "4.0",
            "fan_spend_per_match": "8.0",
            "gtex_purchase_rate": "0.05",
            "gtex_purchase_amount": "1.5",
            "tournament_entry_gtex": "3.0",
            "tournament_participation_rate": "0.2",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["days"] == 30
    assert len(payload["projections"]) == 30
    assert payload["summary"]["inflation_risk"] in {"LOW", "MEDIUM", "HIGH"}


def test_paystack_webhook_settles_purchase_order(client, app_session_factory, monkeypatch) -> None:
    _prepare_admin(client, app_session_factory)
    order = _seed_paystack_order(app_session_factory)
    monkeypatch.setenv("GTE_PAYSTACK_WEBHOOK_SECRET", "paystack-secret")
    payload = {
        "event": "charge.success",
        "data": {
            "id": 9001,
            "reference": "ps_live_ref_webhook",
            "amount": 900000,
            "currency": "NGN",
            "status": "success",
            "metadata": {
                "purchase_order_reference": order.reference,
            },
        },
    }
    raw_body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = hmac.new(b"paystack-secret", raw_body, sha512).hexdigest()

    response = client.post(
        "/integrations/payments/paystack/webhook",
        headers={"content-type": "application/json", "x-paystack-signature": signature},
        content=raw_body,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ok"
    assert response.json()["order_status"] == PurchaseOrderStatus.SETTLED.value

    with app_session_factory() as session:
        refreshed = session.get(FancoinPurchaseOrder, order.id)
        assert refreshed is not None
        assert refreshed.status == PurchaseOrderStatus.SETTLED


def test_wallet_protection_reports_active_wallet_transaction_locks(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)
    user_id, _user_headers = _create_user_auth_headers(
        app_session_factory,
        email="wallet-lock-user@example.com",
        username="walletlockuser",
    )
    RuntimeControlService(client.app).acquire_wallet_transaction_lock(
        user_id=user_id,
        operation="withdrawal_request",
        ttl_seconds=120,
        updated_by_user_id=user_id,
    )

    response = client.get("/api/admin/finance/wallet-protection", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["active_wallet_transaction_lock_count"] == 1
    assert payload["active_wallet_transaction_locks"][0]["user_id"] == user_id


def test_reconciliation_summary_surfaces_missing_ledger_links(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)
    with app_session_factory() as session:
        user = AuthService().register_user(
            session,
            email="reconciliation-user@example.com",
            username="reconciliationuser",
            password=TEST_PASSWORD,
        )
        treasury = TreasuryService()
        settings = treasury.ensure_settings(session)
        settings.deposit_mode = PaymentMode.HYBRID
        rail_service = WalletRailService(session)
        order = rail_service.create_purchase_order(
            user=user,
            settings=settings,
            amount=Decimal("9000.0000"),
            input_unit="fiat",
            provider_key="paystack",
            source_scope="wallet",
            unit=LedgerUnit.COIN,
            processor_mode="automatic_gateway",
            payout_channel="gateway",
            provider_reference="ps_missing_ledger_ref",
            notes="missing ledger settlement",
        )
        order.status = PurchaseOrderStatus.SETTLED
        order.ledger_transaction_id = None

        payment_event = WalletService().create_payment_event(
            session,
            user=user,
            provider="paystack",
            provider_reference="payevt_missing_ledger_ref",
            amount=Decimal("50.0000"),
        )
        payment_event.status = PaymentStatus.VERIFIED
        payment_event.ledger_transaction_id = None

        deposit = treasury.create_deposit_request(session, user=user, amount=Decimal("10000.0000"), input_unit="fiat")
        deposit.status = deposit.status.CONFIRMED
        deposit.ledger_transaction_id = None
        session.commit()

    response = client.get("/api/admin/finance/reconciliation", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["settled_purchase_orders_missing_ledger"] >= 1
    assert payload["settled_payment_events_missing_ledger"] >= 1
    assert payload["confirmed_deposits_missing_ledger"] >= 1
    assert any(item["issue_type"] == "settled_purchase_order_missing_ledger" for item in payload["issues"])
    assert any(item["issue_type"] == "verified_payment_event_missing_ledger" for item in payload["issues"])


def test_manual_price_override_routes_support_create_list_and_delete(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)

    create_response = client.post(
        "/api/admin/finance/manual-price-overrides",
        headers=headers,
        json={
            "asset_type": "player",
            "asset_id": "player-manual-price-test",
            "override_price": "321.5000",
            "currency": "credits",
            "reason": "operator reset",
        },
    )

    assert create_response.status_code == 200, create_response.text
    assert create_response.json()["override_price"] == "321.5000"

    list_response = client.get("/api/admin/finance/manual-price-overrides", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert any(item["asset_id"] == "player-manual-price-test" for item in list_response.json())

    delete_response = client.delete(
        "/api/admin/finance/manual-price-overrides/player/player-manual-price-test",
        headers=headers,
    )
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["asset_id"] == "player-manual-price-test"


def test_account_controls_can_freeze_login_and_ban_accounts(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    admin_headers = _login_admin(client)
    user_id, user_headers = _create_user_auth_headers(
        app_session_factory,
        email="finance-controlled-user@example.com",
        username="financecontrolled",
    )

    freeze_response = client.post(
        "/api/admin/finance/account-controls",
        headers=admin_headers,
        json={
            "user_id": user_id,
            "freeze_login": True,
            "freeze_wallet": False,
            "freeze_matches": False,
            "freeze_social": False,
            "ban_account": False,
            "reason": "manual review",
        },
    )
    assert freeze_response.status_code == 200, freeze_response.text

    me_response = client.get("/api/auth/me", headers=user_headers)
    assert me_response.status_code == 423, me_response.text
    assert "manual review" in _error_message(me_response)

    clear_response = client.delete(f"/api/admin/finance/account-controls/{user_id}", headers=admin_headers)
    assert clear_response.status_code == 200, clear_response.text

    ban_response = client.post(
        "/api/admin/finance/account-controls",
        headers=admin_headers,
        json={
            "user_id": user_id,
            "freeze_login": False,
            "freeze_wallet": False,
            "freeze_matches": False,
            "freeze_social": False,
            "ban_account": True,
            "reason": "ban test",
        },
    )
    assert ban_response.status_code == 200, ban_response.text
    assert ban_response.json()["ban_account"] is True

    banned_me_response = client.get("/api/auth/me", headers=user_headers)
    assert banned_me_response.status_code == 401, banned_me_response.text
    assert "could not be loaded" in _error_message(banned_me_response)

    restore_response = client.delete(f"/api/admin/finance/account-controls/{user_id}", headers=admin_headers)
    assert restore_response.status_code == 200, restore_response.text


def test_match_kill_switch_routes_toggle_live_hub_state(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)
    match_id = "finance-kill-switch-match"

    create_response = client.post(
        "/api/admin/finance/match-kill-switches",
        headers=headers,
        json={"match_id": match_id, "enabled": True, "reason": "operator halt"},
    )

    assert create_response.status_code == 200, create_response.text
    assert create_response.json()["enabled"] is True
    assert ensure_live_match_hub(client.app).is_match_halted(match_id) is True

    list_response = client.get("/api/admin/finance/match-kill-switches", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert any(item["match_id"] == match_id for item in list_response.json())

    delete_response = client.delete(f"/api/admin/finance/match-kill-switches/{match_id}", headers=headers)
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["enabled"] is False
    assert ensure_live_match_hub(client.app).is_match_halted(match_id) is False


def test_wallet_protection_summary_surfaces_duplicate_deposit_candidates(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)
    duplicate_reference = "ps_duplicate_wallet_protection"
    _seed_provider_order(
        app_session_factory,
        provider_key="paystack",
        provider_reference=duplicate_reference,
        email="wallet-duplicate-a@example.com",
        username="walletduplicatea",
    )
    _seed_provider_order(
        app_session_factory,
        provider_key="paystack",
        provider_reference=duplicate_reference,
        email="wallet-duplicate-b@example.com",
        username="walletduplicateb",
    )

    response = client.get("/api/admin/finance/wallet-protection", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    duplicate = next(
        item for item in payload["duplicate_deposit_candidates"] if item["provider_reference"] == duplicate_reference
    )
    assert duplicate["provider_key"] == "paystack"
    assert duplicate["occurrence_count"] >= 2
    assert len(duplicate["order_ids"]) >= 2


def test_paystack_webhook_rejects_invalid_signature_when_secret_is_configured(
    client, app_session_factory, monkeypatch
) -> None:
    _prepare_admin(client, app_session_factory)
    _seed_paystack_order(app_session_factory)
    monkeypatch.setenv("GTE_PAYSTACK_WEBHOOK_SECRET", "paystack-secret")

    response = client.post(
        "/integrations/payments/paystack/webhook",
        headers={"x-paystack-signature": "invalid-signature"},
        json={
            "event": "charge.success",
            "data": {
                "id": 9002,
                "reference": "ps_live_ref_webhook",
                "amount": 900000,
                "currency": "NGN",
                "status": "success",
            },
        },
    )

    assert response.status_code == 401, response.text
    assert "signature is invalid" in _error_message(response)


def test_korapay_webhook_verifies_signature_and_settles_purchase_order(
    client, app_session_factory, monkeypatch
) -> None:
    _prepare_admin(client, app_session_factory)
    order = _seed_provider_order(
        app_session_factory,
        provider_key="korapay",
        provider_reference="kp_live_ref_webhook",
        email="korapay-user@example.com",
        username="korapayuser",
    )
    monkeypatch.setenv("GTE_KORAPAY_WEBHOOK_SECRET", "korapay-secret")
    payload = {
        "event": "charge.success",
        "data": {
            "id": "kp-event-1",
            "reference": "kp_live_ref_webhook",
            "amount": "9000.0000",
            "currency": "NGN",
            "status": "success",
            "metadata": {
                "purchase_order_reference": order.reference,
            },
        },
    }
    signature = hmac.new(
        b"korapay-secret",
        json.dumps(payload["data"], separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
        sha256,
    ).hexdigest()

    response = client.post(
        "/integrations/payments/korapay/webhook",
        headers={"x-korapay-signature": signature},
        json=payload,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ok"
    assert response.json()["signature_verified"] is True
    assert response.json()["order_status"] == PurchaseOrderStatus.SETTLED.value

    with app_session_factory() as session:
        refreshed = session.get(FancoinPurchaseOrder, order.id)
        assert refreshed is not None
        assert refreshed.status == PurchaseOrderStatus.SETTLED


def test_korapay_webhook_rejects_invalid_signature_when_secret_is_configured(
    client, app_session_factory, monkeypatch
) -> None:
    _prepare_admin(client, app_session_factory)
    _seed_provider_order(
        app_session_factory,
        provider_key="korapay",
        provider_reference="kp_live_ref_invalid_sig",
        email="korapay-invalid@example.com",
        username="korapayinvalid",
    )
    monkeypatch.setenv("GTE_KORAPAY_WEBHOOK_SECRET", "korapay-secret")

    response = client.post(
        "/integrations/payments/korapay/webhook",
        headers={"x-korapay-signature": "invalid-signature"},
        json={
            "event": "charge.success",
            "data": {
                "id": "kp-event-invalid",
                "reference": "kp_live_ref_invalid_sig",
                "amount": "9000.0000",
                "currency": "NGN",
                "status": "success",
            },
        },
    )

    assert response.status_code == 401, response.text
    assert "signature is invalid" in _error_message(response)
