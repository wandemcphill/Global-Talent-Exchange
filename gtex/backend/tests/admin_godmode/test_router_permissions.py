from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.models  # noqa: F401
import app.orders.models  # noqa: F401
from app.admin_godmode.router import router as admin_router
from app.admin_godmode.service import AdminGodModeService
from app.auth.dependencies import get_current_admin, get_session
from app.auth.service import AuthService
from app.models.base import Base
from app.models.user import User, UserRole
from app.wallets.service import WalletService


@contextmanager
def _admin_test_client(
    tmp_path: Path,
    *,
    role: UserRole = UserRole.ADMIN,
    permissions: list[str] | None = None,
) -> Iterator[tuple[TestClient, User]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    admin = AuthService().ensure_admin_user(
        session,
        email=f"{role.value}-godmode@example.com",
        password="SuperSecret1",
        username=f"{role.value}_godmode",
        display_name="God Mode Admin",
        role=role,
    )
    session.commit()

    app = FastAPI()
    app.include_router(admin_router)
    app.state.settings = SimpleNamespace(config_root=tmp_path)
    app.state.session_factory = SessionLocal

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: admin

    if permissions is not None:
        AdminGodModeService(wallet_service=WalletService()).upsert_admin_assignment(
            app,
            session,
            admin=admin,
            role_name=None,
            permissions=permissions,
            is_enabled=True,
        )
        session.commit()

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, admin
    finally:
        session.close()
        engine.dispose()


def test_scoped_admin_bootstrap_returns_clean_403(tmp_path: Path) -> None:
    with _admin_test_client(tmp_path) as (client, _admin):
        response = client.get("/api/admin/god-mode/bootstrap")

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission view_audit_log is required for this action."


def test_god_mode_payment_rails_fail_closed_without_capability(tmp_path: Path) -> None:
    with _admin_test_client(tmp_path) as (client, _admin):
        response = client.get("/api/admin/god-mode/payment-rails")

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission manage_payment_rails is required for this action."


def test_delegated_payment_rail_admin_can_read_payment_rails(tmp_path: Path) -> None:
    with _admin_test_client(tmp_path, permissions=["manage_payment_rails"]) as (client, _admin):
        response = client.get("/api/admin/god-mode/payment-rails")

    assert response.status_code == 200
    assert response.json()["rails"]


def test_treasury_withdrawal_requires_treasury_capability_not_withdrawal_ops(tmp_path: Path) -> None:
    with _admin_test_client(tmp_path, permissions=["manage_withdrawals"]) as (client, _admin):
        response = client.post(
            "/api/admin/god-mode/treasury/withdrawals",
            json={
                "unit": "coin",
                "amount": "1.0000",
                "destination_reference": "treasury-bank-ref",
                "reason": "Treasury route capability regression",
                "confirmation_text": "CONFIRM TREASURY WITHDRAWAL",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission manage_treasury_withdrawals is required for this action."
