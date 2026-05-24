from __future__ import annotations

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
from app.admin_finance.router import webhook_router
from app.auth.dependencies import get_session
from app.models.base import Base


@pytest.fixture()
def webhook_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()

    app = FastAPI()
    app.include_router(webhook_router)
    app.state.settings = SimpleNamespace()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as client:
        yield client

    session.close()


def test_paystack_webhook_is_gone_even_when_stale_secret_is_configured(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GTE_ENABLE_PAYSTACK", "true")
    monkeypatch.setenv("GTE_PAYSTACK_WEBHOOK_SECRET", "paystack-secret")

    response = webhook_client.post(
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

    assert response.status_code == 410, response.text
    assert "paystack is unavailable" in response.json()["detail"].lower()


def test_paystack_webhook_is_gone_by_default(webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GTE_ENABLE_PAYSTACK", raising=False)
    monkeypatch.delenv("GTE_PAYSTACK_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("GTE_PAYSTACK_WEBHOOK_SIGNATURE_OPTIONAL", raising=False)

    response = webhook_client.post(
        "/integrations/payments/paystack/webhook",
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

    assert response.status_code == 410, response.text
    assert "paystack is unavailable" in response.json()["detail"].lower()


def test_paystack_webhook_ignores_legacy_optional_signature_flag(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GTE_ENABLE_PAYSTACK", "true")
    monkeypatch.delenv("GTE_PAYSTACK_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("GTE_PAYSTACK_WEBHOOK_SIGNATURE_OPTIONAL", "true")

    response = webhook_client.post(
        "/integrations/payments/paystack/webhook",
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

    assert response.status_code == 410, response.text
    assert "paystack is unavailable" in response.json()["detail"].lower()


def test_korapay_webhook_rejects_invalid_signature_when_secret_is_configured(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GTE_KORAPAY_WEBHOOK_SECRET", "korapay-secret")

    response = webhook_client.post(
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
    assert "signature is invalid" in response.json()["detail"].lower()


def test_korapay_webhook_rejects_missing_secret_by_default(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GTE_KORAPAY_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("GTE_KORAPAY_WEBHOOK_SIGNATURE_OPTIONAL", raising=False)

    response = webhook_client.post(
        "/integrations/payments/korapay/webhook",
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
    assert "not configured" in response.json()["detail"].lower()


def test_korapay_webhook_signature_optional_flag_is_ignored_in_production(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    webhook_client.app.state.settings = SimpleNamespace(app_env="production")
    monkeypatch.delenv("GTE_KORAPAY_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("GTE_KORAPAY_WEBHOOK_SIGNATURE_OPTIONAL", "true")

    response = webhook_client.post(
        "/integrations/payments/korapay/webhook",
        json={
            "event": "charge.success",
            "data": {
                "id": "kp-event-prod-unsigned",
                "reference": "kp_live_ref_unsigned",
                "amount": "9000.0000",
                "currency": "NGN",
                "status": "success",
            },
        },
    )

    assert response.status_code == 401, response.text
    assert "not configured" in response.json()["detail"].lower()
