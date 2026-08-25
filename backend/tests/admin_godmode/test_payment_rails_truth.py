from __future__ import annotations

import json
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
from app.admin_godmode.runtime_paths import admin_godmode_state_path
from app.auth.dependencies import get_current_admin
from app.auth.service import AuthService
from app.models.base import Base
from app.models.user import UserRole


def _build_client(tmp_path: Path) -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    admin_user = AuthService().ensure_admin_user(
        session,
        email="payment-rails-admin@example.com",
        password="SuperSecret1",
        username="payment_rails_admin",
        display_name="Payment Rails Admin",
        role=UserRole.SUPER_ADMIN,
    )
    session.commit()

    app = FastAPI()
    app.include_router(admin_router)
    app.state.settings = SimpleNamespace(config_root=tmp_path)
    app.state.session_factory = SessionLocal
    app.dependency_overrides[get_current_admin] = lambda: admin_user
    return TestClient(app)


def test_payment_rails_drop_stale_non_live_defaults(tmp_path: Path) -> None:
    state_path = admin_godmode_state_path(tmp_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "roles": {"default_admin_role": "scoped_admin", "available_roles": {}, "assignments": []},
                "commissions": {},
                "payment_rails": [
                    {
                        "provider": "bank_transfer_manual",
                        "deposits_enabled": True,
                        "withdrawals_enabled": True,
                        "is_live": True,
                        "maintenance_message": "Manual rail is available.",
                    },
                    {
                        "provider": "paystack",
                        "deposits_enabled": True,
                        "withdrawals_enabled": True,
                        "is_live": True,
                        "maintenance_message": None,
                    },
                    {
                        "provider": "korapay",
                        "deposits_enabled": True,
                        "withdrawals_enabled": True,
                        "is_live": True,
                        "maintenance_message": None,
                    },
                    {
                        "provider": "flutterwave",
                        "deposits_enabled": True,
                        "withdrawals_enabled": True,
                        "is_live": True,
                        "maintenance_message": None,
                    },
                    {
                        "provider": "monnify",
                        "deposits_enabled": True,
                        "withdrawals_enabled": True,
                        "is_live": True,
                        "maintenance_message": None,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with _build_client(tmp_path) as client:
        response = client.get("/api/admin/god-mode/payment-rails")

    assert response.status_code == 200
    rails = response.json()["rails"]
    assert [rail["provider"] for rail in rails] == ["bank_transfer_manual", "korapay"]
    assert {rail["provider"] for rail in rails} == {"bank_transfer_manual", "korapay"}
    assert "paystack" not in {rail["provider"] for rail in rails}
    assert "flutterwave" not in {rail["provider"] for rail in rails}
    assert "monnify" not in {rail["provider"] for rail in rails}


def test_payment_rail_update_rejects_unsupported_provider(tmp_path: Path) -> None:
    with _build_client(tmp_path) as client:
        response = client.put(
            "/api/admin/god-mode/payment-rails",
            json={
                "rails": [
                    {
                        "provider": "flutterwave",
                        "deposits_enabled": True,
                        "withdrawals_enabled": True,
                        "is_live": True,
                        "maintenance_message": None,
                    }
                ],
                "reason": "Keep admin rail controls truthful.",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported payment rail provider 'flutterwave'."


def test_payment_rail_update_rejects_paystack_provider(tmp_path: Path) -> None:
    with _build_client(tmp_path) as client:
        response = client.put(
            "/api/admin/god-mode/payment-rails",
            json={
                "rails": [
                    {
                        "provider": "paystack",
                        "deposits_enabled": True,
                        "withdrawals_enabled": True,
                        "is_live": True,
                        "maintenance_message": None,
                    }
                ],
                "reason": "Attempt to enable blocked Paystack checkout.",
            },
        )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Unsupported payment rail provider 'paystack'."
