from __future__ import annotations

import hmac
import json
from decimal import Decimal
from hashlib import sha256
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.tests.support.secrets import TEST_PASSWORD
from app.admin_finance import router as admin_finance_router
from app.admin_finance.service import AdminFinanceService
from app.auth.service import AuthService, DuplicateUserError
from app.live_matches.service import ensure_live_match_hub
from app.main import INITIAL_ADMIN_DISPLAY_NAME, INITIAL_ADMIN_EMAIL, INITIAL_ADMIN_PASSWORD
from app.models import (
    Attachment,
    CountryFeaturePolicy,
    EconomyBurnEvent,
    KycStatus,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerUnit,
    PlayerCardMomentum,
    User,
)
from app.models.competition_reward_pool import CompetitionRewardPool
from app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from app.models.treasury import DepositStatus, PaymentMode, RateDirection, TreasuryAuditEvent, TreasuryWithdrawalStatus
from app.models.wallet import PaymentStatus
from app.policies.service import PolicyService
from app.services.runtime_control_service import RuntimeControlService
from app.treasury.service import TreasuryService
from app.wallets.rail_service import WalletRailService
from app.wallets.service import LedgerPosting, WalletService


def _error_message(response) -> str:
    payload = _response_payload(response)
    return str(payload.get("message") or payload.get("detail") or "").lower()


def _response_payload(response):
    payload = json.loads(response.text or "null")
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


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
    with client.app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == INITIAL_ADMIN_EMAIL))
        assert admin is not None
        token, _ = AuthService().issue_access_token(admin, session=session)
        session.commit()
    return {"Authorization": f"Bearer {token}", "X-API-Version": "2"}


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
            provider_key="korapay",
            source_scope="wallet",
            unit=LedgerUnit.COIN,
            processor_mode="automatic_gateway",
            payout_channel="gateway",
            provider_reference="kp_live_ref_snapshot",
            notes="seeded purchase order",
        )
        rail_service.settle_purchase_order(order=order, actor=user)
        session.commit()
        return user.id, order.reference


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
        return user.id, {"Authorization": f"Bearer {token}", "X-API-Version": "2"}


def _seed_submitted_deposit(app_session_factory, *, email: str, username: str) -> str:
    with app_session_factory() as session:
        user = AuthService().register_user(
            session,
            email=email,
            username=username,
            password=TEST_PASSWORD,
        )
        treasury = TreasuryService()
        settings = treasury.ensure_settings(session)
        settings.deposit_mode = PaymentMode.MANUAL
        deposit = treasury.create_deposit_request(session, user=user, amount=Decimal("10000.0000"), input_unit="fiat")
        attachment = Attachment(
            filename=f"{deposit.reference}.png",
            content_type="image/png",
            size_bytes=5,
            data=b"proof",
            metadata_json={"kind": "manual_bank_transfer_proof"},
            created_by_user_id=user.id,
        )
        session.add(attachment)
        session.flush()
        treasury.submit_deposit_request(
            session,
            user=user,
            deposit_request_id=deposit.id,
            payer_name=user.full_name or user.email,
            sender_bank="GTEX Test Bank",
            transfer_reference=f"TR-{deposit.reference}",
            proof_attachment_id=attachment.id,
        )
        session.commit()
        return deposit.id


def _seed_policy_acceptances(session, user: User) -> None:
    service = PolicyService(session)
    service.seed_defaults()
    profile = service.ensure_user_region_profile(user=user, region_code="NG")
    profile.region_code = "NG"
    for version in service.list_missing_acceptances(user_id=user.id):
        service.accept_document(
            user_id=user.id,
            document_key=version.document.document_key,
            version_label=version.version_label,
            ip_address=None,
            device_id=None,
        )
    session.flush()


def _seed_pending_withdrawal(app_session_factory, *, email: str, username: str) -> str:
    with app_session_factory() as session:
        user = AuthService().register_user(
            session,
            email=email,
            username=username,
            password=TEST_PASSWORD,
        )
        user.kyc_status = KycStatus.FULLY_VERIFIED
        _seed_policy_acceptances(session, user)

        wallet_service = WalletService()
        treasury = TreasuryService()
        settings = treasury.ensure_settings(session)
        settings.withdrawal_mode = PaymentMode.MANUAL
        settings.withdrawal_rate_value = Decimal("1.0000")
        settings.withdrawal_rate_direction = RateDirection.FIAT_PER_COIN
        settings.min_withdrawal = Decimal("0.0000")
        settings.max_withdrawal = Decimal("100000.0000")

        user_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
        platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=Decimal("250.0000")),
                LedgerPosting(account=platform_account, amount=Decimal("-250.0000")),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            reference=f"withdrawal-seed-balance-{username}",
            actor=user,
        )
        bank_account = treasury.create_user_bank_account(
            session,
            user=user,
            bank_name="GTEX Manual Bank",
            account_number="1234567890",
            account_name="GTEX Withdrawal User",
            bank_code="001",
            currency_code="NGN",
            set_active=True,
        )
        withdrawal = treasury.create_withdrawal_request(
            session,
            user=user,
            amount_coin=Decimal("25.0000"),
            bank_account_id=bank_account.id,
            source_scope="trade",
            notes="admin payment queue withdrawal",
        )
        session.commit()
        return withdrawal.id


def test_control_tower_snapshot_returns_finance_metrics(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    _seed_finance_state(app_session_factory)
    headers = _login_admin(client)

    response = client.get("/api/v2/admin/finance/control-tower", headers=headers)

    assert response.status_code == 200, response.text
    payload = _response_payload(response)
    assert Decimal(payload["gtex_supply"]) > Decimal("0")
    assert Decimal(payload["daily_revenue_naira"]) > Decimal("0")
    assert payload["cash_rails"]["payment_methods"] == ["Manual bank transfer", "KoraPay"]
    assert {"Cards", "Apple Pay", "Google Pay"}.isdisjoint(payload["cash_rails"]["payment_methods"])
    assert len(payload["history"]) >= 7
    assert payload["projection"]["days"] == 30


def test_control_tower_cash_rails_whitelist_canonical_payment_methods(
    monkeypatch,
) -> None:
    class _FakePaymentGatewayService:
        def __init__(self, *, session, settings) -> None:
            del session, settings

        def list_methods(self):
            return [
                SimpleNamespace(method_key="bank_transfer_manual", display_name="Manual bank transfer"),
                SimpleNamespace(method_key="korapay", display_name="KoraPay"),
                SimpleNamespace(method_key="cards", display_name="Cards"),
                SimpleNamespace(
                    method_key="".join(("pay", "stack")),
                    display_name="".join(("Pay", "stack")),
                ),
                SimpleNamespace(method_key="apple_pay", display_name="Apple Pay"),
                SimpleNamespace(method_key="google_pay", display_name="Google Pay"),
                SimpleNamespace(method_key="voucher_processor", display_name="Voucher Processor"),
            ]

    class _FakeTreasuryService:
        def ensure_settings(self, session):
            del session
            return SimpleNamespace(
                deposit_mode="hybrid",
                withdrawal_mode="hybrid",
                currency_code="NGN",
                min_withdrawal=Decimal("0.0000"),
                max_withdrawal=Decimal("1000000.0000"),
            )

    class _ScalarZeroSession:
        def scalar(self, *args, **kwargs):
            del args, kwargs
            return 0

    monkeypatch.setattr("app.admin_finance.service.PaymentGatewayService", _FakePaymentGatewayService)

    payload = AdminFinanceService(
        session=_ScalarZeroSession(),
        settings=SimpleNamespace(),
        treasury_service=_FakeTreasuryService(),
    )._cash_rail_summary()

    assert payload["payment_methods"] == ["Manual bank transfer", "KoraPay"]
    assert payload["withdrawal_mode"] == "manual"
    assert payload["automatic_withdrawals_enabled"] is False
    assert {
        "Apple Pay",
        "Cards",
        "Google Pay",
        "Voucher Processor",
        "".join(("Pay", "stack")),
    }.isdisjoint(payload["payment_methods"])


def test_simulator_returns_30_day_projection(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)

    response = client.post(
        "/api/v2/admin/finance/simulate",
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
    payload = _response_payload(response)
    assert payload["days"] == 30
    assert len(payload["projections"]) == 30
    assert payload["summary"]["inflation_risk"] in {"LOW", "MEDIUM", "HIGH"}


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

    response = client.get("/api/v2/admin/finance/wallet-protection", headers=headers)

    assert response.status_code == 200, response.text
    payload = _response_payload(response)
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
            provider_key="korapay",
            source_scope="wallet",
            unit=LedgerUnit.COIN,
            processor_mode="automatic_gateway",
            payout_channel="gateway",
            provider_reference="kp_missing_ledger_ref",
            notes="missing ledger settlement",
        )
        order.status = PurchaseOrderStatus.SETTLED
        order.ledger_transaction_id = None

        payment_event = WalletService().create_payment_event(
            session,
            user=user,
            provider="korapay",
            provider_reference="kora_evt_missing_ledger_ref",
            amount=Decimal("50.0000"),
        )
        payment_event.status = PaymentStatus.VERIFIED
        payment_event.ledger_transaction_id = None

        deposit = treasury.create_deposit_request(session, user=user, amount=Decimal("10000.0000"), input_unit="fiat")
        deposit.status = deposit.status.CONFIRMED
        deposit.ledger_transaction_id = None
        session.commit()

    response = client.get("/api/v2/admin/finance/reconciliation", headers=headers)

    assert response.status_code == 200, response.text
    payload = _response_payload(response)
    assert payload["settled_purchase_orders_missing_ledger"] >= 1
    assert payload["settled_payment_events_missing_ledger"] >= 1
    assert payload["confirmed_deposits_missing_ledger"] >= 1
    assert any(item["issue_type"] == "settled_purchase_order_missing_ledger" for item in payload["issues"])
    assert any(item["issue_type"] == "verified_payment_event_missing_ledger" for item in payload["issues"])


def test_admin_payment_queue_tabs_and_actions_are_treasury_audited(client, app_session_factory, monkeypatch) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)

    def _empty_bids_section(self, *, include_items, q, limit, offset):
        return {
            "key": "bids",
            "label": "Bids",
            "item_type": "transfer_bid",
            "statuses": [],
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "action_state": "audit_only",
            "blocked_reason": (
                "Transfer bid approve, reject, and counter requests are audit-only in the admin payment queue."
            ),
        }

    monkeypatch.setattr(AdminFinanceService, "_transfer_bid_queue_section", _empty_bids_section)

    approve_deposit_id = _seed_submitted_deposit(
        app_session_factory,
        email="admin-queue-approve@example.com",
        username="adminqueueapprove",
    )
    reject_deposit_id = _seed_submitted_deposit(
        app_session_factory,
        email="admin-queue-reject@example.com",
        username="adminqueuereject",
    )
    reinstate_deposit_id = _seed_submitted_deposit(
        app_session_factory,
        email="admin-queue-reinstate@example.com",
        username="adminqueuereinstate",
    )

    with app_session_factory() as session:
        admin = session.scalar(select(User).where(User.email == INITIAL_ADMIN_EMAIL))
        assert admin is not None
        TreasuryService().reject_deposit(
            session,
            actor=admin,
            deposit_request_id=reinstate_deposit_id,
            admin_notes="seed rejected queue row",
        )
        session.commit()

    pending_response = client.get(
        "/api/v2/admin/finance/payment-queue",
        headers=headers,
        params={"tab": "pending", "q": "admin-queue"},
    )
    assert pending_response.status_code == 200, pending_response.text
    pending_payload = _response_payload(pending_response)
    assert {tab["key"] for tab in pending_payload["tabs"]} == {"pending", "approved", "rejected", "bids"}
    assert pending_payload["bids"]["action_state"] == "audit_only"
    assert {item["id"] for item in pending_payload["pending"]["items"]} >= {approve_deposit_id, reject_deposit_id}
    pending_items = {item["id"]: item for item in pending_payload["pending"]["items"]}
    pending_row = pending_items[approve_deposit_id]
    assert pending_row["severity"] == "medium"
    assert pending_row["timestamps"]["submitted_at"] == pending_row["submitted_at"]
    assert pending_row["actor"]["user"]["id"] == pending_row["user_id"]
    assert pending_row["actor"]["admin"] is None
    assert pending_row["escalation"]["state"] == "awaiting_admin_review"
    assert pending_row["audit"]["reference"] == f"deposit:{approve_deposit_id}"
    assert pending_row["audit"]["last_event_type"] is None
    assert pending_row["action_controls"]["approve"]["requires_admin_notes"] is True
    assert pending_row["action_controls"]["reject"]["auditable"] is True
    assert pending_row["notes"]["admin"] is None
    assert pending_row["proof_attachment_id"] is not None
    assert pending_row["proof_attachment_ids"] == [pending_row["proof_attachment_id"]]

    invalid_tab_response = client.get(
        "/api/v2/admin/finance/payment-queue",
        headers=headers,
        params={"tab": "settled"},
    )
    missing_notes_response = client.post(
        f"/api/v2/admin/finance/payment-queue/deposits/{approve_deposit_id}/approve",
        headers=headers,
        json={},
    )

    assert invalid_tab_response.status_code == 422, invalid_tab_response.text
    assert missing_notes_response.status_code == 400, missing_notes_response.text
    assert "admin_notes" in _error_message(missing_notes_response)

    approve_response = client.post(
        f"/api/v2/admin/finance/payment-queue/deposits/{approve_deposit_id}/approve",
        headers=headers,
        json={"admin_notes": "approved through admin payment queue"},
    )
    reject_response = client.post(
        f"/api/v2/admin/finance/payment-queue/deposits/{reject_deposit_id}/reject",
        headers=headers,
        json={"admin_notes": "rejected through admin payment queue"},
    )
    reinstate_response = client.post(
        f"/api/v2/admin/finance/payment-queue/deposits/{reinstate_deposit_id}/reinstate",
        headers=headers,
        json={"admin_notes": "reinstated through admin payment queue"},
    )

    assert approve_response.status_code == 200, approve_response.text
    assert reject_response.status_code == 200, reject_response.text
    assert reinstate_response.status_code == 200, reinstate_response.text
    approve_payload = _response_payload(approve_response)
    reject_payload = _response_payload(reject_response)
    reinstate_payload = _response_payload(reinstate_response)
    assert approve_payload["item"]["status"] == DepositStatus.CONFIRMED.value
    assert reject_payload["item"]["status"] == DepositStatus.REJECTED.value
    assert reinstate_payload["item"]["status"] == DepositStatus.UNDER_REVIEW.value
    assert approve_payload["audit"]["last_event_type"] == "treasury.deposit.confirmed"
    assert reject_payload["audit"]["last_event_type"] == "treasury.deposit.rejected"
    assert reinstate_payload["audit"]["last_event_type"] == "treasury.deposit.review"
    assert approve_payload["item"]["actor"]["admin"]["email"] == INITIAL_ADMIN_EMAIL
    assert reject_payload["item"]["notes"]["admin"] == "rejected through admin payment queue"
    assert reinstate_payload["item"]["escalation"]["state"] == "under_review"

    approved_response = client.get(
        "/api/v2/admin/finance/payment-queue",
        headers=headers,
        params={"tab": "approved", "q": "admin-queue"},
    )
    rejected_response = client.get(
        "/api/v2/admin/finance/payment-queue",
        headers=headers,
        params={"tab": "rejected", "q": "admin-queue"},
    )
    assert approved_response.status_code == 200, approved_response.text
    assert rejected_response.status_code == 200, rejected_response.text
    assert approve_deposit_id in {item["id"] for item in _response_payload(approved_response)["approved"]["items"]}
    assert reject_deposit_id in {item["id"] for item in _response_payload(rejected_response)["rejected"]["items"]}

    with app_session_factory() as session:
        event_rows = session.execute(
            select(
                TreasuryAuditEvent.resource_id,
                TreasuryAuditEvent.event_type,
                TreasuryAuditEvent.actor_email,
                TreasuryAuditEvent.payload,
            ).where(TreasuryAuditEvent.resource_id.in_([approve_deposit_id, reject_deposit_id, reinstate_deposit_id]))
        ).all()
    events_by_resource: dict[str, dict[str, tuple[str | None, dict[str, object]]]] = {}
    for resource_id, event_type, actor_email, payload in event_rows:
        events_by_resource.setdefault(resource_id, {})[event_type] = (actor_email, payload)

    approved_actor, approved_payload = events_by_resource[approve_deposit_id]["treasury.deposit.confirmed"]
    rejected_actor, rejected_payload = events_by_resource[reject_deposit_id]["treasury.deposit.rejected"]
    reinstated_actor, reinstated_payload = events_by_resource[reinstate_deposit_id]["treasury.deposit.review"]
    assert approved_actor == INITIAL_ADMIN_EMAIL
    assert rejected_actor == INITIAL_ADMIN_EMAIL
    assert reinstated_actor == INITIAL_ADMIN_EMAIL
    assert approved_payload["notes"] == "approved through admin payment queue"
    assert rejected_payload["notes"] == "rejected through admin payment queue"
    assert reinstated_payload["notes"] == "reinstated through admin payment queue"


def test_payment_queue_withdrawal_action_uses_real_treasury_row_and_audit(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)
    withdrawal_id = _seed_pending_withdrawal(
        app_session_factory,
        email="admin-queue-withdrawal@example.com",
        username="adminqueuewithdrawal",
    )
    admin_notes = "approved withdrawal through admin payment queue"

    response = client.post(
        f"/api/v2/admin/finance/payment-queue/withdrawals/{withdrawal_id}/approve",
        headers=headers,
        json={"admin_notes": admin_notes},
    )

    assert response.status_code == 200, response.text
    payload = _response_payload(response)
    assert payload["action"] == "approve"
    assert payload["item_type"] == "withdrawal"
    assert payload["action_state"] == "completed"
    assert payload["business_state_changed"] is True
    assert payload["wallet_state_changed"] is False
    assert payload["audit_reference"] == f"withdrawal:{withdrawal_id}"
    assert payload["item"]["status"] == TreasuryWithdrawalStatus.APPROVED.value
    assert payload["item"]["queue"] == "approved"
    assert payload["item"]["processor_mode"] == "manual_bank_transfer"
    assert payload["item"]["payout_channel"] == "bank_transfer"
    assert Decimal(str(payload["item"]["amount_coin"])) == Decimal("25.0000")
    assert Decimal(str(payload["item"]["fee_amount"])) == Decimal("2.5000")
    assert Decimal(str(payload["item"]["net_amount"])) == Decimal("22.5000")
    assert Decimal(str(payload["item"]["total_debit"])) == Decimal("25.0000")
    assert payload["item"]["notes"]["admin"] == admin_notes
    assert payload["audit"]["reference"] == f"withdrawal:{withdrawal_id}"
    assert payload["audit"]["resource_type"] == "treasury_withdrawal"
    assert payload["audit"]["resource_id"] == withdrawal_id
    assert payload["audit"]["last_event_type"] == "treasury.withdrawal.status_changed"
    assert payload["audit"]["last_actor_email"] == INITIAL_ADMIN_EMAIL

    with app_session_factory() as session:
        audit = session.scalar(
            select(TreasuryAuditEvent)
            .where(
                TreasuryAuditEvent.resource_type == "treasury_withdrawal",
                TreasuryAuditEvent.resource_id == withdrawal_id,
                TreasuryAuditEvent.event_type == "treasury.withdrawal.status_changed",
            )
            .order_by(TreasuryAuditEvent.created_at.desc())
        )

    assert audit is not None
    assert audit.payload["status"] == TreasuryWithdrawalStatus.APPROVED.value
    assert audit.payload["previous"] == TreasuryWithdrawalStatus.PENDING_REVIEW.value
    assert audit.payload["notes"] == admin_notes
    assert audit.payload["gross_amount"] == "25.0000"
    assert audit.payload["fee_amount"] == "2.5000"
    assert audit.payload["net_amount"] == "22.5000"
    assert audit.payload["processor_mode"] == "manual_bank_transfer"
    assert audit.payload["payout_channel"] == "bank_transfer"


def test_payment_queue_bid_counter_records_audit_only_review(monkeypatch) -> None:
    captured = {}

    class _FakePlayerLifecycleService:
        def __init__(self, session) -> None:
            captured["session"] = session

        def record_admin_transfer_bid_review_action(self, window_id, bid_id, payload, *, actor):
            captured["window_id"] = window_id
            captured["bid_id"] = bid_id
            captured["payload"] = payload
            captured["actor"] = actor
            return SimpleNamespace(
                model_dump=lambda mode: {
                    "review": {"id": bid_id, "status": "submitted"},
                    "audit_event": {"id": "audit-counter", "event_status": payload.action},
                    "action_state": "audit_recorded",
                    "business_state_changed": False,
                    "wallet_state_changed": False,
                }
            )

    monkeypatch.setattr("app.services.player_lifecycle_service.PlayerLifecycleService", _FakePlayerLifecycleService)

    result = AdminFinanceService(session=SimpleNamespace()).record_payment_queue_bid_action(
        actor=SimpleNamespace(id="admin-counter", role="super_admin"),
        window_id="window-counter",
        bid_id="bid-counter",
        action="counter",
        admin_notes="Counter requested by payment queue operator.",
    )

    assert captured["window_id"] == "window-counter"
    assert captured["bid_id"] == "bid-counter"
    assert captured["payload"].action == "escalate"
    assert captured["payload"].reason == "admin_payment_queue_counter_requested"
    assert captured["payload"].escalation_state == "counter_requested"
    assert result["business_state_changed"] is False
    assert result["wallet_state_changed"] is False
    assert result["blocked_reason"].startswith("Transfer bid business mutations")


def test_payment_queue_bid_route_commits_audit_only_action(monkeypatch) -> None:
    class _FakeSession:
        def __init__(self) -> None:
            self.committed = False
            self.rolled_back = False

        def commit(self) -> None:
            self.committed = True

        def rollback(self) -> None:
            self.rolled_back = True

    class _FakePaymentQueueService:
        def record_payment_queue_bid_action(self, *, actor, window_id, bid_id, action, admin_notes):
            return {
                "action": action,
                "item_type": "transfer_bid",
                "action_state": "audit_recorded",
                "business_state_changed": False,
                "wallet_state_changed": False,
                "audit_reference": f"transfer-bid:{bid_id}",
                "blocked_reason": "Transfer bid business mutations stay outside the admin payment queue.",
            }

    monkeypatch.setattr(admin_finance_router, "_require_payment_queue_permission", lambda request, actor: None)
    monkeypatch.setattr(admin_finance_router, "_queue_service", lambda request, session: _FakePaymentQueueService())

    session = _FakeSession()
    result = admin_finance_router._run_bid_queue_action(
        SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace()))),
        session,
        SimpleNamespace(id="admin-queue-operator"),
        "window-route",
        "bid-route",
        {"admin_notes": "Counter through admin queue"},
        "counter",
    )

    assert session.committed is True
    assert session.rolled_back is False
    assert result.action == "counter"
    assert result.action_state == "audit_recorded"
    assert result.business_state_changed is False


def test_payment_queue_withdrawal_route_commits_and_rolls_back(monkeypatch) -> None:
    class _FakeSession:
        def __init__(self) -> None:
            self.commits = 0
            self.rollbacks = 0

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    class _FakePaymentQueueService:
        fail = False

        def approve_payment_queue_withdrawal(self, *, actor, withdrawal_id, admin_notes):
            if self.fail:
                raise ValueError("withdrawal is locked")
            return {
                "action": "approve",
                "item_type": "withdrawal",
                "action_state": "completed",
                "business_state_changed": True,
                "wallet_state_changed": False,
                "audit_reference": f"withdrawal:{withdrawal_id}",
                "audit": {"last_event_type": "treasury.withdrawal.status_changed"},
                "notes": {"admin": admin_notes},
                "item": {
                    "id": withdrawal_id,
                    "status": "approved",
                    "notes": {"admin": admin_notes},
                },
            }

        def reject_payment_queue_withdrawal(self, *, actor, withdrawal_id, admin_notes):
            return {
                "action": "reject",
                "item_type": "withdrawal",
                "action_state": "completed",
                "business_state_changed": True,
                "wallet_state_changed": True,
                "audit_reference": f"withdrawal:{withdrawal_id}",
                "audit": {"last_event_type": "treasury.withdrawal.status_changed"},
                "notes": {"admin": admin_notes},
                "item": {
                    "id": withdrawal_id,
                    "status": "rejected",
                    "notes": {"admin": admin_notes},
                },
            }

        def reinstate_payment_queue_withdrawal(self, *, actor, withdrawal_id, admin_notes):
            return {
                "action": "reinstate",
                "item_type": "withdrawal",
                "action_state": "completed",
                "business_state_changed": True,
                "wallet_state_changed": False,
                "audit_reference": f"withdrawal:{withdrawal_id}",
                "audit": {"last_event_type": "treasury.withdrawal.status_changed"},
                "notes": {"admin": admin_notes},
                "item": {
                    "id": withdrawal_id,
                    "status": "pending_review",
                    "notes": {"admin": admin_notes},
                },
            }

    fake_service = _FakePaymentQueueService()
    monkeypatch.setattr(admin_finance_router, "_require_payment_queue_permission", lambda request, actor: None)
    monkeypatch.setattr(admin_finance_router, "_queue_service", lambda request, session: fake_service)

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace())))
    actor = SimpleNamespace(id="admin-queue-operator")
    session = _FakeSession()

    missing_notes = admin_finance_router._run_withdrawal_queue_action
    try:
        missing_notes(request, session, actor, "withdrawal-missing", {}, "approve")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("missing admin_notes should block withdrawal action")

    approve_result = admin_finance_router._run_withdrawal_queue_action(
        request,
        session,
        actor,
        "withdrawal-approve",
        {"admin_notes": "approve withdrawal through queue"},
        "approve",
    )
    reject_result = admin_finance_router._run_withdrawal_queue_action(
        request,
        session,
        actor,
        "withdrawal-reject",
        {"admin_notes": "reject withdrawal through queue"},
        "reject",
    )
    reinstate_result = admin_finance_router._run_withdrawal_queue_action(
        request,
        session,
        actor,
        "withdrawal-reinstate",
        {"admin_notes": "reinstate withdrawal through queue"},
        "reinstate",
    )

    fake_service.fail = True
    conflict = admin_finance_router._run_withdrawal_queue_action
    try:
        conflict(
            request,
            session,
            actor,
            "withdrawal-conflict",
            {"admin_notes": "conflict withdrawal through queue"},
            "approve",
        )
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
    else:
        raise AssertionError("conflicting withdrawal action should roll back")

    assert session.commits == 3
    assert session.rollbacks == 1
    assert approve_result.item["status"] == "approved"
    assert reject_result.wallet_state_changed is True
    assert reinstate_result.item["status"] == "pending_review"
    assert reject_result.notes["admin"] == "reject withdrawal through queue"


def test_manual_price_override_routes_support_create_list_and_delete(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)

    create_response = client.post(
        "/api/v2/admin/finance/manual-price-overrides",
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
    assert _response_payload(create_response)["override_price"] == "321.5000"

    list_response = client.get("/api/v2/admin/finance/manual-price-overrides", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert any(item["asset_id"] == "player-manual-price-test" for item in _response_payload(list_response))

    delete_response = client.delete(
        "/api/v2/admin/finance/manual-price-overrides/player/player-manual-price-test",
        headers=headers,
    )
    assert delete_response.status_code == 200, delete_response.text
    assert _response_payload(delete_response)["asset_id"] == "player-manual-price-test"


def test_account_controls_can_freeze_login_and_ban_accounts(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    admin_headers = _login_admin(client)
    user_id, user_headers = _create_user_auth_headers(
        app_session_factory,
        email="finance-controlled-user@example.com",
        username="financecontrolled",
    )

    freeze_response = client.post(
        "/api/v2/admin/finance/account-controls",
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

    me_response = client.get("/api/v2/auth/me", headers=user_headers)
    assert me_response.status_code == 423, me_response.text
    assert "manual review" in _error_message(me_response)

    clear_response = client.delete(f"/api/v2/admin/finance/account-controls/{user_id}", headers=admin_headers)
    assert clear_response.status_code == 200, clear_response.text

    ban_response = client.post(
        "/api/v2/admin/finance/account-controls",
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
    assert _response_payload(ban_response)["ban_account"] is True

    banned_me_response = client.get("/api/v2/auth/me", headers=user_headers)
    assert banned_me_response.status_code == 401, banned_me_response.text
    assert "could not be loaded" in _error_message(banned_me_response)

    restore_response = client.delete(f"/api/v2/admin/finance/account-controls/{user_id}", headers=admin_headers)
    assert restore_response.status_code == 200, restore_response.text


def test_match_kill_switch_routes_toggle_live_hub_state(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)
    match_id = "finance-kill-switch-match"

    create_response = client.post(
        "/api/v2/admin/finance/match-kill-switches",
        headers=headers,
        json={"match_id": match_id, "enabled": True, "reason": "operator halt"},
    )

    assert create_response.status_code == 200, create_response.text
    assert _response_payload(create_response)["enabled"] is True
    assert ensure_live_match_hub(client.app).is_match_halted(match_id) is True

    list_response = client.get("/api/v2/admin/finance/match-kill-switches", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert any(item["match_id"] == match_id for item in _response_payload(list_response))

    delete_response = client.delete(f"/api/v2/admin/finance/match-kill-switches/{match_id}", headers=headers)
    assert delete_response.status_code == 200, delete_response.text
    assert _response_payload(delete_response)["enabled"] is False
    assert ensure_live_match_hub(client.app).is_match_halted(match_id) is False


def test_wallet_protection_summary_surfaces_duplicate_deposit_candidates(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)
    duplicate_reference = "kp_duplicate_wallet_protection"
    _seed_provider_order(
        app_session_factory,
        provider_key="korapay",
        provider_reference=duplicate_reference,
        email="wallet-duplicate-a@example.com",
        username="walletduplicatea",
    )
    _seed_provider_order(
        app_session_factory,
        provider_key="korapay",
        provider_reference=duplicate_reference,
        email="wallet-duplicate-b@example.com",
        username="walletduplicateb",
    )

    response = client.get("/api/v2/admin/finance/wallet-protection", headers=headers)

    assert response.status_code == 200, response.text
    payload = _response_payload(response)
    duplicate = next(
        item for item in payload["duplicate_deposit_candidates"] if item["provider_reference"] == duplicate_reference
    )
    assert duplicate["provider_key"] == "korapay"
    assert duplicate["occurrence_count"] >= 2
    assert len(duplicate["order_ids"]) >= 2


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
        "/api/v2/integrations/payments/korapay/webhook",
        headers={"x-korapay-signature": signature, "X-API-Version": "2"},
        json=payload,
    )

    assert response.status_code == 200, response.text
    payload = _response_payload(response)
    assert payload["status"] == "ok"
    assert payload["signature_verified"] is True
    assert payload["order_status"] == PurchaseOrderStatus.SETTLED.value

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
        "/api/v2/integrations/payments/korapay/webhook",
        headers={"x-korapay-signature": "invalid-signature", "X-API-Version": "2"},
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
