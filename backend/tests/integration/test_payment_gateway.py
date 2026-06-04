from __future__ import annotations

import os

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_wallet_user, get_session
from app.core.api_contract import install_api_contracts
from app.core.config import load_settings
from app.core.database import load_model_modules
from app.integrations.payments.router import router
from app.models.base import Base
from app.models.user import User


API_V2_HEADERS = {"X-API-Version": "2"}
PAYMENT_AMOUNT = "5000.0000"


@pytest.fixture(scope="module")
def payment_client() -> TestClient:
    database_url = "sqlite+pysqlite:///:memory:"
    settings = load_settings(
        environ={
            **os.environ,
            "DATABASE_URL": database_url,
            "GTE_DATABASE_URL": database_url,
        }
    )
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    load_model_modules()
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        user = User(
            email="payment-user@example.com",
            username="payment_user",
            full_name="Payment User",
            password_hash="test-password-hash",
        )
        session.add(user)
        session.commit()
        user_id = user.id

    app = FastAPI()
    app.state.settings = settings
    install_api_contracts(app)
    app.include_router(router)

    def _get_session():
        with session_factory() as session:
            yield session

    def _get_current_wallet_user(session: Session = Depends(get_session)) -> User:
        user = session.get(User, user_id)
        assert user is not None
        return user

    app.dependency_overrides[get_session] = _get_session
    app.dependency_overrides[get_current_wallet_user] = _get_current_wallet_user

    with TestClient(app) as client:
        yield client

    engine.dispose()


def _response_data(response):
    payload = response.json()
    if isinstance(payload, dict) and payload.get("success") is True and "data" in payload:
        return payload["data"]
    return payload


def test_payment_gateway_methods(payment_client):
    response = payment_client.get(
        "/api/v2/integrations/payments/methods",
        headers=API_V2_HEADERS,
    )
    assert response.status_code == 200, response.text
    body = _response_data(response)
    assert [method["method_key"] for method in body] == [
        "bank_transfer_manual",
        "korapay",
    ]
    assert [method["display_name"] for method in body] == [
        "Manual bank transfer",
        "KoraPay",
    ]
    assert {method["method_group"] for method in body} == {
        "manual_bank_transfer",
        "automatic_gateway",
    }
    assert {method["provider_key"] for method in body} == {"bank_transfer_manual", "korapay"}


def test_payment_gateway_quote_and_order(payment_client):
    quote = payment_client.post(
        "/api/v2/integrations/payments/quote",
        headers=API_V2_HEADERS,
        json={"amount": PAYMENT_AMOUNT, "input_unit": "fiat"},
    )
    assert quote.status_code == 200, quote.text
    payload = _response_data(quote)
    assert payload["provider_key"] == "korapay"
    assert payload["gross_amount"]

    order = payment_client.post(
        "/api/v2/integrations/payments/orders",
        headers=API_V2_HEADERS,
        json={"amount": PAYMENT_AMOUNT, "input_unit": "fiat"},
    )
    assert order.status_code == 201, order.text
    body = _response_data(order)
    assert body["provider_key"] == "korapay"
    assert body["reference"]
