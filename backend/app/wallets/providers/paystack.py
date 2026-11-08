from __future__ import annotations

from decimal import Decimal
import hashlib
import hmac
import logging
import os
from typing import Any

import httpx

from app.wallets.providers.base import (
    BankResolutionResult,
    CheckoutSession,
    PaymentVerification,
    PayoutSession,
    PayoutVerification,
    ProviderEvent,
    ProviderEventType,
    ProviderFeeEstimate,
)

logger = logging.getLogger(__name__)

PAYSTACK_DEFAULT_BASE_URL = "https://api.paystack.co"
AMOUNT_QUANTUM = Decimal("0.0001")


class PaystackProviderAdapter:
    key = "paystack"
    provider_key = "paystack"
    display_name = "Paystack"

    def __init__(self, *, base_url: str | None = None, secret_key: str | None = None) -> None:
        self._override_base_url = base_url
        self._override_secret_key = secret_key

    def _base_url(self) -> str:
        if self._override_base_url:
            return self._override_base_url.rstrip("/")
        for name in ("GTE_PAYSTACK_BASE_URL", "PAYSTACK_BASE_URL"):
            val = os.getenv(name)
            if val and val.strip():
                return val.strip().rstrip("/")
        return PAYSTACK_DEFAULT_BASE_URL

    def _secret_key(self) -> str | None:
        if self._override_secret_key:
            return self._override_secret_key.strip()
        for name in ("GTE_PAYSTACK_SECRET_KEY", "PAYSTACK_SECRET_KEY"):
            val = os.getenv(name)
            if val and val.strip():
                return val.strip()
        return None

    def _webhook_secret(self) -> str | None:
        # Paystack's webhook HMAC uses the API secret key (sk_live_ / sk_test_).
        # There is no separate webhook-signing secret in Paystack's contract.
        return self._secret_key()

    def is_configured(self) -> bool:
        return bool(self._secret_key())

    def is_live(self) -> bool:
        if not self.is_configured():
            return False
        env = (os.getenv("GTE_APP_ENV") or os.getenv("APP_ENV") or "development").strip().lower()
        if env in {"production", "prod", "release"}:
            secret = self._secret_key() or ""
            return secret.startswith("sk_live_")
        return True

    def _callback_url(self) -> str | None:
        for name in ("GTE_PAYSTACK_CALLBACK_URL", "PAYSTACK_CALLBACK_URL"):
            val = os.getenv(name)
            if val and val.strip():
                return val.strip()
        return None

    def initialize_checkout(
        self,
        *,
        order_reference: str,
        amount: Decimal,
        currency: str = "NGN",
        customer_email: str,
        customer_name: str | None = None,
        callback_url: str | None = None,
        metadata: dict[str, Any] | None = None,
        narration: str | None = None,
    ) -> CheckoutSession:
        secret = self._secret_key()
        if not secret:
            raise ValueError("Paystack secret key is not configured.")

        # Paystack requires amount in kobo (NGN * 100)
        amount_kobo = int((Decimal(str(amount)) * Decimal("100")).to_integral_value())
        payload: dict[str, Any] = {
            "email": customer_email,
            "amount": amount_kobo,
            "currency": currency.upper(),
            "reference": order_reference,
            "metadata": {
                "order_reference": order_reference,
                "purchase_order_reference": order_reference,
                "customer_name": customer_name or "",
                **(metadata or {}),
            },
        }
        resolved_callback = callback_url or self._callback_url()
        if resolved_callback:
            payload["callback_url"] = resolved_callback

        response = httpx.post(
            f"{self._base_url()}/transaction/initialize",
            json=payload,
            headers={
                "Authorization": f"Bearer {secret}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict) or not data.get("authorization_url"):
            raise ValueError("Paystack did not return an authorization URL.")

        return CheckoutSession(
            reference=order_reference,
            checkout_url=str(data.get("authorization_url")),
            provider=self.key,
            amount=Decimal(str(amount)).quantize(AMOUNT_QUANTUM),
            currency=currency.upper(),
            status="pending",
            mock_mode=bool(data.get("mock_mode", False)),
            metadata=metadata,
            raw_response=body,
        )

    def verify_payment(self, *, reference: str) -> PaymentVerification:
        secret = self._secret_key()
        if not secret:
            raise ValueError("Paystack secret key is not configured.")
        norm_ref = str(reference).strip()
        if not norm_ref:
            raise ValueError("Paystack transaction reference is required.")

        response = httpx.get(
            f"{self._base_url()}/transaction/verify/{norm_ref}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=30.0,
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("Paystack returned an invalid verification response.")

        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict):
            raise ValueError("Paystack verification data is missing.")

        status_raw = str(data.get("status") or "").strip().lower()
        if status_raw == "success":
            status = "success"
        elif status_raw in {"pending", "ongoing", "processing"}:
            status = "pending"
        elif status_raw in {"reversed", "chargeback"}:
            status = "reversed"
        else:
            status = "failed"

        raw_kobo = data.get("amount") or 0
        amount = (Decimal(str(raw_kobo)) / Decimal("100")).quantize(AMOUNT_QUANTUM)
        raw_fee = data.get("fees")
        fee = (Decimal(str(raw_fee)) / Decimal("100")).quantize(AMOUNT_QUANTUM) if raw_fee is not None else None
        provider_ref = str(data.get("reference") or norm_ref)
        provider_event_id = str(data.get("id")) if data.get("id") is not None else None
        customer = data.get("customer") if isinstance(data.get("customer"), dict) else {}
        customer_email = customer.get("email")

        return PaymentVerification(
            reference=norm_ref,
            provider_reference=provider_ref,
            status=status,
            amount=amount,
            currency=str(data.get("currency") or "NGN").upper(),
            provider_event_id=provider_event_id,
            processor_fee=fee,
            customer_email=customer_email,
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else None,
            raw_payload=body,
        )

    def verify_webhook_signature(
        self,
        *,
        raw_body: bytes | None,
        headers: dict[str, str],
        payload: dict[str, Any] | None = None,
    ) -> bool:
        del payload
        secret = self._webhook_secret()
        if not secret:
            raise ValueError("Paystack webhook cannot be verified: webhook secret is not configured.")
        norm_headers = {str(k).lower(): str(v).strip() for k, v in headers.items()}
        signature = norm_headers.get("x-paystack-signature")
        if not signature:
            raise ValueError("Paystack webhook signature header (x-paystack-signature) is missing.")
        if raw_body is None:
            raise ValueError("Paystack webhook raw body is missing.")

        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Paystack webhook signature is invalid.")
        return True

    def parse_webhook(self, payload: dict[str, Any], headers: dict[str, str] | None = None) -> ProviderEvent | None:
        del headers
        if not isinstance(payload, dict):
            return None
        raw_event = str(payload.get("event") or "").strip().lower()
        data = payload.get("data")
        if not raw_event or not isinstance(data, dict):
            return None

        mapped_type, is_payout = self._map_event_type(raw_event, data)
        if mapped_type is None:
            return None

        metadata = data.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        reference = data.get("reference") or data.get("transaction_reference")
        if not reference:
            return None
        purchase_order_reference = metadata.get("purchase_order_reference") or metadata.get("order_reference")
        event_id = data.get("id") or payload.get("id")
        amount = None
        raw_amount = data.get("amount")
        if raw_amount is not None:
            try:
                # Paystack sends amounts in kobo
                amount = (Decimal(str(raw_amount)) / Decimal("100")).quantize(AMOUNT_QUANTUM)
            except Exception:
                amount = None
        return ProviderEvent(
            provider_key=self.key,
            event_type=mapped_type,
            provider_reference=str(reference),
            purchase_order_reference=str(purchase_order_reference) if purchase_order_reference else None,
            event_id=str(event_id) if event_id is not None else None,
            amount=amount,
            currency=str(data.get("currency")) if data.get("currency") else None,
            raw_payload=payload,
            is_payout=is_payout,
        )

    def _map_event_type(self, raw_event: str, data: dict[str, Any]) -> tuple[ProviderEventType | None, bool]:
        status = str(data.get("status") or "").strip().lower()
        mapping = {
            "charge.success": (ProviderEventType.SETTLED, False),
            "charge.failed": (ProviderEventType.FAILED, False),
            "charge.dispute.create": (ProviderEventType.DISPUTED, False),
            "refund.processed": (ProviderEventType.REFUNDED, False),
            "transfer.success": (ProviderEventType.SETTLED, True),
            "transfer.failed": (ProviderEventType.FAILED, True),
            "transfer.reversed": (ProviderEventType.REVERSED, True),
        }
        if raw_event in mapping:
            return mapping[raw_event]
        is_payout = "transfer" in raw_event
        if status == "success":
            return ProviderEventType.SETTLED, is_payout
        if status == "failed":
            return ProviderEventType.FAILED, is_payout
        if status in {"pending", "processing"}:
            return ProviderEventType.PENDING, is_payout
        if status == "reversed":
            return ProviderEventType.REVERSED, is_payout
        return None, False

    def initiate_payout(
        self,
        *,
        reference: str,
        amount: Decimal,
        currency: str = "NGN",
        bank_code: str,
        account_number: str,
        account_name: str,
        narration: str | None = None,
        customer_email: str | None = None,
    ) -> PayoutSession:
        del customer_email
        secret = self._secret_key()
        if not secret:
            raise ValueError("Paystack secret key is not configured for payouts.")

        # Step 1: Create or fetch transfer recipient
        recipient_payload = {
            "type": "nuban",
            "name": account_name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency.upper(),
        }
        recipient_res = httpx.post(
            f"{self._base_url()}/transferrecipient",
            json=recipient_payload,
            headers={
                "Authorization": f"Bearer {secret}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        recipient_res.raise_for_status()
        recipient_body = recipient_res.json()
        recipient_data = recipient_body.get("data") if isinstance(recipient_body, dict) else {}
        recipient_code = recipient_data.get("recipient_code")
        if not recipient_code:
            raise ValueError("Failed to create transfer recipient on Paystack.")

        # Step 2: Initiate transfer
        amount_kobo = int((Decimal(str(amount)) * Decimal("100")).to_integral_value())
        transfer_payload = {
            "source": "balance",
            "amount": amount_kobo,
            "reference": reference,
            "recipient": recipient_code,
            "reason": narration or f"GTEX Withdrawal {reference}",
        }
        transfer_res = httpx.post(
            f"{self._base_url()}/transfer",
            json=transfer_payload,
            headers={
                "Authorization": f"Bearer {secret}",
                "Content-Type": "application/json",
            },
            timeout=35.0,
        )
        transfer_res.raise_for_status()
        transfer_body = transfer_res.json()
        transfer_data = transfer_body.get("data") if isinstance(transfer_body, dict) else {}
        status_raw = str(transfer_data.get("status") or "").strip().lower()
        status = (
            "success"
            if status_raw in {"success"}
            else ("failed" if status_raw in {"failed", "rejected"} else "pending")
        )
        provider_ref = str(transfer_data.get("reference") or reference)
        transfer_code = str(transfer_data.get("transfer_code") or "")

        return PayoutSession(
            reference=reference,
            provider_reference=provider_ref,
            transfer_code=transfer_code,
            status=status,
            amount=Decimal(str(amount)).quantize(AMOUNT_QUANTUM),
            currency=currency.upper(),
            processor_fee=None,
            raw_payload=transfer_body,
        )

    def verify_payout(self, *, reference: str) -> PayoutVerification:
        secret = self._secret_key()
        if not secret:
            raise ValueError("Paystack secret key is not configured for payouts.")
        norm_ref = str(reference).strip()
        if not norm_ref:
            raise ValueError("Paystack transaction reference is required.")

        response = httpx.get(
            f"{self._base_url()}/transfer/verify/{norm_ref}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=30.0,
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else {}
        status_raw = str(data.get("status") or "").strip().lower()
        if status_raw == "success":
            status = "success"
        elif status_raw in {"failed", "rejected"}:
            status = "failed"
        elif status_raw == "reversed":
            status = "reversed"
        else:
            status = "pending"

        amount_kobo = data.get("amount") or 0
        amount = (Decimal(str(amount_kobo)) / Decimal("100")).quantize(AMOUNT_QUANTUM)
        reason = data.get("reason") or data.get("gateway_response")

        return PayoutVerification(
            reference=norm_ref,
            provider_reference=str(data.get("reference") or norm_ref),
            status=status,
            amount=amount,
            currency=str(data.get("currency") or "NGN").upper(),
            processor_fee=None,
            failure_reason=str(reason) if reason else None,
            raw_payload=body,
        )

    def resolve_bank_account(self, *, account_number: str, bank_code: str) -> BankResolutionResult:
        secret = self._secret_key()
        if not secret:
            raise ValueError("Paystack secret key is not configured.")

        response = httpx.get(
            f"{self._base_url()}/bank/resolve",
            params={"account_number": account_number, "bank_code": bank_code},
            headers={"Authorization": f"Bearer {secret}"},
            timeout=25.0,
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else {}
        account_name = str(data.get("account_name") or "").strip()
        if not account_name:
            raise ValueError("Could not resolve account name with Paystack.")
        return BankResolutionResult(
            account_number=account_number,
            account_name=account_name,
            bank_code=bank_code,
        )

    def estimate_fee(self, *, amount: Decimal, operation: str = "checkout") -> ProviderFeeEstimate:
        norm_amount = Decimal(str(amount)).quantize(AMOUNT_QUANTUM)
        if operation == "payout":
            # Paystack standard transfer pricing:
            # <= 5000: NGN 10
            # 5001 - 50000: NGN 25
            # > 50000: NGN 50
            if norm_amount <= Decimal("5000.0000"):
                fee = Decimal("10.0000")
            elif norm_amount <= Decimal("50000.0000"):
                fee = Decimal("25.0000")
            else:
                fee = Decimal("50.0000")
            net = (norm_amount - fee).quantize(AMOUNT_QUANTUM)
            return ProviderFeeEstimate(
                amount=norm_amount,
                estimated_fee=fee,
                net_amount=max(Decimal("0.0000"), net),
                currency="NGN",
                is_estimate=True,
            )
        # Paystack standard checkout collections:
        # 1.5% + NGN 100 (NGN 100 waived for amounts < NGN 2500, fee capped at NGN 2000)
        calc_fee = norm_amount * Decimal("0.015")
        if norm_amount >= Decimal("2500.0000"):
            calc_fee += Decimal("100.0000")
        cap = Decimal("2000.0000")
        fee = min(calc_fee, cap).quantize(AMOUNT_QUANTUM)
        net = (norm_amount - fee).quantize(AMOUNT_QUANTUM)
        return ProviderFeeEstimate(
            amount=norm_amount,
            estimated_fee=fee,
            net_amount=max(Decimal("0.0000"), net),
            currency="NGN",
            is_estimate=True,
        )


__all__ = ["PaystackProviderAdapter"]
