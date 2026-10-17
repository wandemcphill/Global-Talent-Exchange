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
from app.wallets.providers.registry import paystack_enabled, provider_live_deposit_ready


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
    app.state.settings = SimpleNamespace(app_env="production")

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as client:
        yield client

    session.close()


def _paystack_payload() -> dict[str, object]:
    return {
        "event": "charge.success",
        "data": {
            "id": 9002,
            "reference": "ps_live_ref_webhook",
            "amount": 900000,
            "currency": "NGN",
            "status": "success",
        },
    }


def test_paystack_enable_flag_requires_live_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GTE_ENABLE_PAYSTACK", "true")
    monkeypatch.delenv("GTE_PAYSTACK_SECRET_KEY", raising=False)
    monkeypatch.delenv("GTE_PAYSTACK_WEBHOOK_SECRET", raising=False)
    assert paystack_enabled() is False

    monkeypatch.setenv("GTE_PAYSTACK_SECRET_KEY", "paystack-secret")
    monkeypatch.setenv("GTE_PAYSTACK_WEBHOOK_SECRET", "paystack-secret")
    assert paystack_enabled() is True

    monkeypatch.setenv("GTE_ENABLE_PAYSTACK", "false")
    assert paystack_enabled() is False


def test_paystack_is_live_ready_with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GTE_ENABLE_PAYSTACK", "true")
    monkeypatch.setenv("GTE_PAYSTACK_SECRET_KEY", "paystack-secret")
    monkeypatch.setenv("GTE_PAYSTACK_WEBHOOK_SECRET", "paystack-secret")
    assert provider_live_deposit_ready("paystack") is True


def test_paystack_webhook_rejects_invalid_signature_when_secret_is_configured(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GTE_ENABLE_PAYSTACK", "true")
    monkeypatch.setenv("GTE_PAYSTACK_SECRET_KEY", "paystack-secret")
    monkeypatch.setenv("GTE_PAYSTACK_WEBHOOK_SECRET", "paystack-secret")

    response = webhook_client.post(
        "/integrations/payments/paystack/webhook",
        headers={"x-paystack-signature": "invalid-signature"},
        json=_paystack_payload(),
    )

    assert response.status_code == 401, response.text
    assert "signature is invalid" in response.json()["detail"].lower()


def test_paystack_webhook_is_blocked_when_signature_is_missing(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GTE_ENABLE_PAYSTACK", "true")
    monkeypatch.setenv("GTE_PAYSTACK_SECRET_KEY", "paystack-secret")
    monkeypatch.setenv("GTE_PAYSTACK_WEBHOOK_SECRET", "paystack-secret")

    response = webhook_client.post(
        "/integrations/payments/paystack/webhook",
        json=_paystack_payload(),
    )

    assert response.status_code == 401, response.text


def test_paystack_webhook_is_blocked_when_explicitly_disabled(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GTE_ENABLE_PAYSTACK", "false")

    response = webhook_client.post(
        "/integrations/payments/paystack/webhook",
        json=_paystack_payload(),
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


def test_korapay_webhook_verifies_js_canonical_signature_over_raw_body(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hmac
    from hashlib import sha256

    from app.admin_finance.service import _js_json_stringify

    secret = "korapay-secret"  # pragma: allowlist secret
    monkeypatch.setenv("GTE_KORAPAY_WEBHOOK_SECRET", secret)

    # KoraPay signs JSON.stringify(data) on the wire. The raw body carries a
    # float ("100.00") which JS parses to the number 100 and re-serializes as
    # "100"; verification must match that canonical form, not the raw bytes.
    raw_body = (
        '{"event":"charge.success","data":{'
        '"id":"kp-event-js","reference":"kp_live_ref_js",'
        '"amount":100.00,"currency":"NGN","status":"success"}}'
    ).encode("utf-8")
    data = {
        "id": "kp-event-js",
        "reference": "kp_live_ref_js",
        "amount": 100,
        "currency": "NGN",
        "status": "success",
    }
    signature = hmac.new(
        secret.encode("utf-8"),
        _js_json_stringify(data).encode("utf-8"),
        sha256,
    ).hexdigest()

    response = webhook_client.post(
        "/integrations/payments/korapay/webhook",
        content=raw_body,
        headers={
            "content-type": "application/json",
            "x-korapay-signature": signature,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["signature_verified"] is True


def test_js_json_stringify_renders_integral_floats_as_ints() -> None:
    from app.admin_finance.service import _js_json_stringify

    assert _js_json_stringify({"amount": 100.0, "fee": 1.5, "nested": [2.0, True, None]}) == (
        '{"amount":100,"fee":1.5,"nested":[2,true,null]}'
    )


def test_korapay_encryption_key_alone_is_not_a_webhook_secret(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GTE_KORAPAY_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("KORAPAY_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("GTE_KORAPAY_SECRET_KEY", raising=False)
    monkeypatch.delenv("KORAPAY_SECRET_KEY", raising=False)
    monkeypatch.delenv("GTE_KORAPAY_WEBHOOK_SIGNATURE_OPTIONAL", raising=False)
    monkeypatch.setenv("GTE_KORAPAY_ENCRYPTION_KEY", "encryption-only")

    response = webhook_client.post(
        "/integrations/payments/korapay/webhook",
        json={
            "event": "charge.success",
            "data": {
                "id": "kp-event-enc",
                "reference": "kp_live_ref_enc",
                "amount": "9000.0000",
                "currency": "NGN",
                "status": "success",
            },
        },
    )

    assert response.status_code == 401, response.text
    assert "not configured" in response.json()["detail"].lower()


def test_korapay_secret_key_env_is_accepted_as_webhook_secret(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hmac
    from hashlib import sha256

    from app.admin_finance.service import _js_json_stringify

    secret = "korapay-merchant-secret"  # pragma: allowlist secret
    monkeypatch.delenv("GTE_KORAPAY_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("KORAPAY_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("GTE_KORAPAY_SECRET_KEY", secret)

    data = {
        "id": "kp-event-sk",
        "reference": "kp_live_ref_sk",
        "amount": "9000.0000",
        "currency": "NGN",
        "status": "success",
    }
    signature = hmac.new(
        secret.encode("utf-8"),
        _js_json_stringify(data).encode("utf-8"),
        sha256,
    ).hexdigest()

    response = webhook_client.post(
        "/integrations/payments/korapay/webhook",
        headers={"x-korapay-signature": signature},
        json={"event": "charge.success", "data": data},
    )

    assert response.status_code == 200, response.text
    assert response.json()["signature_verified"] is True
