from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.admin_godmode.runtime_paths import admin_godmode_state_path
from app.auth.dependencies import get_current_user, get_session
from app.auth.service import AuthService
from app.core.database import load_model_modules
from app.models.base import Base
from app.models.notification_record import NotificationRecord
from app.models.treasury import TreasuryAuditEvent, TreasuryWithdrawalStatus
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.models.withdrawal_review import WithdrawalReview
from app.policies.service import PolicyService
from app.treasury.router import router as treasury_router
from app.wallets.router import router as wallets_router
from app.wallets.service import LedgerPosting, WalletService
from backend.tests.support.secrets import TEST_PASSWORD


def test_full_withdrawal_e2e_kyc_bank_quote_admin_paid_receipt_ledger(tmp_path) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    load_model_modules()
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    auth = AuthService()
    user = auth.register_user(
        session,
        email="withdrawal-e2e@example.com",
        username="withdrawale2e",
        password=TEST_PASSWORD,
        full_name="Withdrawal E2E",
        region_code="NG",
    )
    admin = auth.register_user(
        session,
        email="withdrawal-admin@example.com",
        username="withdrawaladmin",
        password=TEST_PASSWORD,
        full_name="Withdrawal Admin",
        role=UserRole.SUPER_ADMIN,
    )
    session.commit()
    _seed_policy_acceptances(session, user)
    _fund_user(session, user, amount=Decimal("100.0000"))

    app = FastAPI()
    app.include_router(wallets_router)
    app.include_router(treasury_router)
    app.state.settings = SimpleNamespace(config_root=tmp_path)
    app.state.cache_backend = None
    state_path = admin_godmode_state_path(tmp_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "roles": {
                    "default_admin_role": "scoped_admin",
                    "available_roles": {"scoped_admin": [], "god_mode": ["manage_treasury_withdrawals"]},
                    "assignments": [],
                }
            }
        ),
        encoding="utf-8",
    )
    current_user_id = {"value": user.id}

    def override_session():
        yield session

    def override_current_user() -> User:
        return session.get(User, current_user_id["value"])

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(app) as client:
        kyc_response = client.post(
            "/api/kyc",
            json={
                "nin": "12345678901",
                "address_line1": "12 Marina",
                "city": "Lagos",
                "state": "Lagos",
                "country": "Nigeria",
                "selfie_attachment_id": "selfie-e2e",
                "country_confirmation": "Nigeria",
            },
        )
        assert kyc_response.status_code == 200, kyc_response.text
        profile_id = kyc_response.json()["id"]

        current_user_id["value"] = admin.id
        kyc_review = client.post(f"/api/admin/treasury/kyc/{profile_id}/review", json={"status": "verified"})
        assert kyc_review.status_code == 200, kyc_review.text

        current_user_id["value"] = user.id
        bank_response = client.post(
            "/api/bank-accounts",
            json={
                "bank_name": "GT Bank",
                "account_number": "0123456789",
                "account_name": "Withdrawal E2E",
                "bank_code": "058",
                "currency_code": "NGN",
                "set_active": True,
            },
        )
        assert bank_response.status_code == 201, bank_response.text
        bank_account_id = bank_response.json()["id"]

        quote_response = client.post(
            "/api/wallets/withdrawals/quote",
            json={"amount_coin": "20.0000", "source_scope": "trade"},
        )
        assert quote_response.status_code == 200, quote_response.text
        assert quote_response.json()["blocked_reason"] is None

        withdrawal_response = client.post(
            "/api/wallets/withdrawals",
            json={"amount_coin": "20.0000", "bank_account_id": bank_account_id, "source_scope": "trade"},
        )
        assert withdrawal_response.status_code == 201, withdrawal_response.text
        withdrawal_id = withdrawal_response.json()["id"]

        current_user_id["value"] = admin.id
        approved = client.post(
            f"/api/admin/treasury/withdrawals/{withdrawal_id}/status",
            json={"status": "approved", "admin_notes": "Approved in E2E."},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == TreasuryWithdrawalStatus.APPROVED.value

        paid = client.post(
            f"/api/admin/treasury/withdrawals/{withdrawal_id}/status",
            json={"status": "paid", "admin_notes": "Paid in E2E."},
        )
        assert paid.status_code == 200, paid.text
        assert paid.json()["status"] == TreasuryWithdrawalStatus.PAID.value

        current_user_id["value"] = user.id
        receipt = client.get(f"/api/wallets/withdrawals/{withdrawal_id}/receipt")
        assert receipt.status_code == 200, receipt.text
        assert receipt.json()["withdrawal"]["status"] == TreasuryWithdrawalStatus.PAID.value

        ledger = client.get("/api/wallets/ledger", params={"page": 1, "page_size": 10})
        assert ledger.status_code == 200, ledger.text
        reasons = {item["reason"] for item in ledger.json()["items"]}
        assert LedgerEntryReason.WITHDRAWAL_HOLD.value in reasons
        assert LedgerEntryReason.WITHDRAWAL_SETTLEMENT.value in reasons

    reviews = session.scalars(select(WithdrawalReview).where(WithdrawalReview.withdrawal_request_id == withdrawal_id)).all()
    audits = session.scalars(
        select(TreasuryAuditEvent).where(TreasuryAuditEvent.resource_id == withdrawal_id)
    ).all()
    notifications = session.scalars(
        select(NotificationRecord).where(NotificationRecord.resource_id == withdrawal_id)
    ).all()
    assert {review.status_to for review in reviews} >= {"approved", "paid"}
    assert any(item.event_type == "treasury.withdrawal.status_changed" for item in audits)
    assert notifications
    session.close()


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
    session.commit()


def _fund_user(session, user: User, *, amount: Decimal) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="withdrawal-e2e-funding",
        description="Seed withdrawal E2E wallet balance",
        actor=user,
    )
    session.commit()
