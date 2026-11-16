"""One Paystack reference credits the initiating user once."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
import app.owner_console.models  # noqa: F401
from app.auth.service import AuthService
from app.models.base import Base
from app.models.treasury import RateDirection
from app.models.wallet import LedgerTransaction
from app.owner_console import ledger, money
from app.owner_console.models import LedgerEvent, OwnerDepositIntent
from app.owner_console.service import OwnerError
from app.treasury.service import TreasuryService
from app.wallets.providers.base import CheckoutSession, PaymentVerification


class _Paystack:
    def initialize_checkout(self, **kwargs):
        return CheckoutSession(
            reference=kwargs["order_reference"],
            checkout_url="https://paystack.test/checkout",
            provider="paystack",
            amount=kwargs["amount"],
            currency="NGN",
        )

    def verify_payment(self, *, reference: str) -> PaymentVerification:
        return PaymentVerification(
            reference=reference,
            provider_reference=reference,
            status="success",
            amount=Decimal("250.00"),
            currency="NGN",
        )

    def verify_webhook_signature(self, *, raw_body, headers, payload=None) -> bool:
        del raw_body, payload
        return headers.get("x-paystack-signature") == "good"


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def _user(session, *, email: str, username: str):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",  # pragma: allowlist secret
    )
    session.commit()
    return user


def test_one_reference_credits_the_initiating_user_once(monkeypatch) -> None:
    adapter = _Paystack()
    monkeypatch.setattr("app.wallets.providers.registry.get_live_provider_adapter", lambda _provider: adapter)
    monkeypatch.setattr("app.wallets.providers.registry.get_provider_adapter", lambda _provider: adapter)
    session = _session()
    try:
        owner = _user(session, email="deposit-owner@example.com", username="deposit-owner")
        other = _user(session, email="deposit-other@example.com", username="deposit-other")
        settings = TreasuryService().ensure_settings(session)
        settings.deposit_rate_value = Decimal("100")
        settings.deposit_rate_direction = RateDirection.FIAT_PER_COIN
        session.commit()

        started = money.paystack_init(session, owner, 100, "https://app.test/callback")
        session.commit()
        reference = started["reference"]
        intent = session.scalar(select(OwnerDepositIntent).where(OwnerDepositIntent.reference == reference))
        assert intent is not None
        assert intent.user_id == owner.id
        assert intent.status == "pending"
        assert Decimal(intent.requested_amount_ngn) == Decimal("100.00")

        with pytest.raises(OwnerError) as bad_signature:
            money.paystack_webhook(
                session,
                b"{}",
                "bad",
                {"event": "charge.success", "data": {"reference": reference, "amount": 25000}},
            )
        assert bad_signature.value.code == "invalid_signature"
        assert ledger.balance(session, ledger.user_account(owner.id), ledger.GTEX) == Decimal("0.00")

        with pytest.raises(OwnerError) as conflict:
            money.paystack_verify(session, other, reference)
        assert conflict.value.code == "deposit_user_conflict"
        assert ledger.balance(session, ledger.user_account(other.id), ledger.GTEX) == Decimal("0.00")

        first = money.paystack_verify(session, owner, reference)
        session.commit()
        second = money.paystack_verify(session, owner, reference)
        session.commit()
        money.paystack_webhook(
            session,
            b"{}",
            "good",
            {
                "event": "charge.success",
                "data": {
                    "reference": reference,
                    "amount": 25000,
                    "metadata": {"user_id": other.id},
                },
            },
        )
        session.commit()

        assert first["status"] == "success"
        assert second["ledger_event"]["id"] == first["ledger_event"]["id"]
        events = list(session.scalars(select(LedgerEvent).where(LedgerEvent.related_object_id == reference)).all())
        assert len(events) == 1
        assert events[0].user_id == owner.id
        assert Decimal(events[0].gross_amount) == Decimal("2.50")
        assert (
            session.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(LedgerTransaction.idempotency_key == f"oc:deposit:paystack:{reference}:settle")
            )
            == 1
        )
        assert ledger.balance(session, ledger.user_account(owner.id), ledger.GTEX) == Decimal("2.50")
        assert ledger.balance(session, ledger.user_account(other.id), ledger.GTEX) == Decimal("0.00")
    finally:
        session.close()


def test_korapay_webhook_and_providerless_verify(monkeypatch) -> None:
    import hashlib
    import hmac
    import json
    from app.wallets.providers.korapay import KoraPayProviderAdapter, _js_json_stringify

    class _KoraStub(KoraPayProviderAdapter):
        def initialize_checkout(self, **kwargs):
            return CheckoutSession(
                reference=kwargs["order_reference"],
                checkout_url="https://korapay.test/checkout",
                provider="korapay",
                amount=kwargs["amount"],
                currency="NGN",
            )

        def verify_payment(self, *, reference: str) -> PaymentVerification:
            return PaymentVerification(
                reference=reference,
                provider_reference=reference,
                status="success",
                amount=Decimal("5000.00"),
                currency="NGN",
            )

    monkeypatch.setenv("GTE_KORAPAY_WEBHOOK_SECRET", "korapay-test-webhook-secret")
    adapter = _KoraStub()
    monkeypatch.setattr("app.wallets.providers.registry.get_live_provider_adapter", lambda _provider: adapter)
    monkeypatch.setattr("app.wallets.providers.registry.get_provider_adapter", lambda _provider: adapter)

    session = _session()
    try:
        owner = _user(session, email="korapay-owner@example.com", username="korapay-owner")
        settings = TreasuryService().ensure_settings(session)
        settings.deposit_rate_value = Decimal("100")
        settings.deposit_rate_direction = RateDirection.FIAT_PER_COIN
        session.commit()

        with pytest.raises(OwnerError) as bad_provider:
            money.paystack_init(session, owner, 5000, "https://app.test/callback", provider="paypal")
        assert bad_provider.value.code == "unsupported_deposit_provider"

        started = money.paystack_init(session, owner, 5000, "https://app.test/callback", provider="korapay")
        session.commit()
        ref = started["reference"]

        webhook_data = {
            "reference": ref,
            "amount": 5000,
            "currency": "NGN",
            "status": "success",
        }
        payload = {"event": "charge.success", "data": webhook_data}
        raw_body = json.dumps(payload).encode("utf-8")
        good_sig = hmac.new(
            b"korapay-test-webhook-secret",
            _js_json_stringify(webhook_data).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        with pytest.raises(OwnerError) as bad_sig:
            money.korapay_webhook(session, raw_body, "bad-signature", payload)
        assert bad_sig.value.code == "invalid_signature"

        money.korapay_webhook(session, raw_body, good_sig, payload)
        session.commit()
        verified = money.paystack_verify(session, owner, ref)
        session.commit()

        assert verified["status"] == "success"
        assert ledger.balance(session, ledger.user_account(owner.id), ledger.GTEX) == Decimal("50.00")
        intent = session.scalar(select(OwnerDepositIntent).where(OwnerDepositIntent.reference == ref))
        assert intent is not None and intent.credited_amount_kobo == 500000

        # Verify-first path without provider parameter resolves korapay intent cleanly.
        started_two = money.paystack_init(session, owner, 5000, "https://app.test/callback", provider="korapay")
        session.commit()
        ref_two = started_two["reference"]
        verified_two = money.paystack_verify(session, owner, ref_two)
        session.commit()
        assert verified_two["status"] == "success"
        assert ledger.balance(session, ledger.user_account(owner.id), ledger.GTEX) == Decimal("100.00")
    finally:
        session.close()
