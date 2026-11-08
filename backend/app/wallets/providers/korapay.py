from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import hashlib
import hmac
import json
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

KORAPAY_DEFAULT_BASE_URL = "https://api.korapay.com/merchant/api/v1"
AMOUNT_QUANTUM = Decimal("0.0001")


def _normalize_for_js(val: Any) -> Any:
    if isinstance(val, dict):
        # In ECMAScript/V8, integer index keys are iterated first in numeric ascending order,
        # then non-integer string keys in insertion order.
        int_keys = []
        str_keys = []
        for k in val.keys():
            k_str = str(k)
            if k_str.isdigit() and (len(k_str) == 1 or not k_str.startswith("0")) and int(k_str) < 2**32 - 1:
                int_keys.append((int(k_str), k_str))
            else:
                str_keys.append(k_str)
        int_keys.sort(key=lambda x: x[0])
        ordered_keys = [k for _, k in int_keys] + str_keys
        return {k: _normalize_for_js(val[k]) for k in ordered_keys}
    elif isinstance(val, list):
        return [_normalize_for_js(item) for item in val]
    elif isinstance(val, float):
        # In JavaScript JSON.stringify, floats with exact integer values (e.g. 250000.0) format as integers (250000)
        if val.is_integer():
            return int(val)
        return val
    return val


def _js_json_stringify(value: Any) -> str:
    """Format dict according to JavaScript JSON.stringify for KoraPay signature checks.

    Guarantees cross-language parity with Node.js JSON.stringify:
    - Eliminates Python whitespace (separators=(',', ':'))
    - Preserves literal UTF-8 Unicode characters (ensure_ascii=False)
    - Normalizes integer-valued floats (250000.0 -> 250000)
    - Orders numeric object keys in ascending order per ECMA-262
    """
    normalized = _normalize_for_js(value)
    return json.dumps(normalized, separators=(",", ":"), ensure_ascii=False)


class KoraPayProviderAdapter:
    key = "korapay"
    provider_key = "korapay"
    display_name = "KoraPay"

    def __init__(self, *, base_url: str | None = None, secret_key: str | None = None) -> None:
        self._override_base_url = base_url
        self._override_secret_key = secret_key

    def _base_url(self) -> str:
        if self._override_base_url:
            return self._override_base_url.rstrip("/")
        for name in ("GTE_KORAPAY_BASE_URL", "KORAPAY_BASE_URL"):
            val = os.getenv(name)
            if val and val.strip():
                return val.strip().rstrip("/")
        return KORAPAY_DEFAULT_BASE_URL

    def _secret_key(self) -> str | None:
        if self._override_secret_key:
            return self._override_secret_key.strip()
        for name in (
            "GTE_KORAPAY_SECRET_KEY",
            "KORAPAY_SECRET_KEY",
            "GTE_KORAPAY_PRIVATE_KEY",
            "KORAPAY_PRIVATE_KEY",
        ):
            val = os.getenv(name)
            if val and val.strip():
                return val.strip()
        return None

    def _webhook_secret(self) -> str | None:
        for name in (
            "GTE_KORAPAY_WEBHOOK_SECRET",
            "KORAPAY_WEBHOOK_SECRET",
        ):
            val = os.getenv(name)
            if val and val.strip():
                return val.strip()
        return self._secret_key()

    def is_configured(self) -> bool:
        return bool(self._secret_key())

    def is_live(self) -> bool:
        if not self.is_configured():
            return False
        env = (os.getenv("GTE_APP_ENV") or os.getenv("APP_ENV") or "development").strip().lower()
        if env in {"production", "prod", "release"}:
            return bool(self._webhook_secret())
        return True

    def _redirect_url(self) -> str | None:
        for name in ("GTE_KORAPAY_REDIRECT_URL", "KORAPAY_REDIRECT_URL"):
            val = os.getenv(name)
            if val and val.strip():
                return val.strip()
        return None

    def _notification_url(self) -> str | None:
        for name in ("GTE_KORAPAY_NOTIFICATION_URL", "KORAPAY_NOTIFICATION_URL"):
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
            raise ValueError("KoraPay secret key is not configured.")

        normalized_amount = Decimal(str(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        payload: dict[str, Any] = {
            "amount": int(normalized_amount),
            "currency": currency.upper(),
            "reference": order_reference,
            "customer": {
                "email": customer_email,
                "name": (customer_name or customer_email).strip(),
            },
            "narration": narration or f"GTEX checkout {order_reference}",
            "merchant_bears_cost": True,
            "metadata": {
                "order_reference": order_reference,
                **(metadata or {}),
            },
        }
        resolved_redirect = callback_url or self._redirect_url()
        if resolved_redirect:
            payload["redirect_url"] = resolved_redirect
        resolved_notification = self._notification_url()
        if resolved_notification:
            payload["notification_url"] = resolved_notification

        response = httpx.post(
            f"{self._base_url()}/charges/initialize",
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
        if not isinstance(data, dict) or not data.get("checkout_url"):
            raise ValueError("KoraPay did not return a valid checkout URL.")

        return CheckoutSession(
            reference=order_reference,
            checkout_url=str(data.get("checkout_url")),
            provider=self.key,
            amount=Decimal(str(payload["amount"])),
            currency=currency.upper(),
            status="pending",
            mock_mode=bool(data.get("mock_mode", False)),
            metadata=metadata,
            raw_response=body,
        )

    def verify_payment(self, *, reference: str) -> PaymentVerification:
        secret = self._secret_key()
        if not secret:
            raise ValueError("KoraPay secret key is not configured.")
        norm_ref = str(reference).strip()
        if not norm_ref:
            raise ValueError("KoraPay transaction reference is required.")

        response = httpx.get(
            f"{self._base_url()}/charges/{norm_ref}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=30.0,
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("KoraPay returned an invalid verification response.")

        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict):
            raise ValueError("KoraPay verification data is missing.")

        status_raw = str(data.get("status") or data.get("transaction_status") or "").strip().lower()
        if status_raw in {"success", "successful", "completed"}:
            status = "success"
        elif status_raw in {"pending", "processing"}:
            status = "pending"
        elif status_raw in {"reversed", "chargeback"}:
            status = "reversed"
        else:
            status = "failed"

        amount = Decimal(str(data.get("amount") or 0)).quantize(AMOUNT_QUANTUM)
        fee = Decimal(str(data.get("fee") or 0)).quantize(AMOUNT_QUANTUM) if data.get("fee") is not None else None
        provider_ref = str(data.get("payment_reference") or data.get("reference") or norm_ref)
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
        secret = self._webhook_secret()
        if not secret:
            raise ValueError("KoraPay webhook cannot be verified: webhook secret is not configured.")
        norm_headers = {str(k).lower(): str(v).strip() for k, v in headers.items()}
        signature = norm_headers.get("x-korapay-signature")
        if not signature:
            raise ValueError("KoraPay webhook signature header (x-korapay-signature) is missing.")

        data_source: object = payload
        if raw_body:
            try:
                data_source = json.loads(raw_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("KoraPay webhook raw body is not valid JSON.") from exc

        data = data_source.get("data") if isinstance(data_source, dict) else None
        if not isinstance(data, dict):
            raise ValueError("KoraPay webhook payload.data is missing or invalid.")

        canonical_payload = _js_json_stringify(data).encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), canonical_payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("KoraPay webhook signature is invalid.")
        return True

    def parse_webhook(self, payload: dict[str, Any], headers: dict[str, str] | None = None) -> ProviderEvent | None:
        del headers
        if not isinstance(payload, dict):
            return None
        raw_event = str(payload.get("event") or payload.get("type") or "").strip().lower()
        data = payload.get("data")
        if not raw_event or not isinstance(data, dict):
            return None

        mapped_type, is_payout = self._map_event_type(raw_event, data)
        if mapped_type is None:
            return None

        reference = (
            data.get("reference")
            or data.get("transaction_reference")
            or data.get("payment_reference")
            or data.get("merchant_reference")
        )
        if not reference:
            return None
        metadata = data.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        purchase_order_reference = (
            metadata.get("purchase_order_reference")
            or metadata.get("order_reference")
            or metadata.get("purchase-order-reference")
            or metadata.get("order-reference")
            or data.get("merchant_reference")
        )
        event_id = data.get("id") or payload.get("id")
        amount = None
        raw_amount = data.get("amount")
        if raw_amount is not None:
            try:
                amount = Decimal(str(raw_amount)).quantize(AMOUNT_QUANTUM)
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
            "collection.success": (ProviderEventType.SETTLED, False),
            "collection.failed": (ProviderEventType.FAILED, False),
            "transfer.success": (ProviderEventType.SETTLED, True),
            "transfer.failed": (ProviderEventType.FAILED, True),
            "transfer.reversed": (ProviderEventType.REVERSED, True),
            "charge.dispute": (ProviderEventType.DISPUTED, False),
            "refund.success": (ProviderEventType.REFUNDED, False),
        }
        if raw_event in mapping:
            return mapping[raw_event]
        is_payout = "transfer" in raw_event or "disburse" in raw_event
        if status in {"success", "successful"}:
            return ProviderEventType.SETTLED, is_payout
        if status in {"failed", "failure"}:
            return ProviderEventType.FAILED, is_payout
        if status in {"pending", "processing"}:
            return ProviderEventType.PENDING, is_payout
        if status == "reversed":
            return ProviderEventType.REVERSED, is_payout
        if status == "refunded":
            return ProviderEventType.REFUNDED, is_payout
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
        secret = self._secret_key()
        if not secret:
            raise ValueError("KoraPay secret key is not configured for payouts.")

        amount_val = float(Decimal(str(amount)).quantize(AMOUNT_QUANTUM))
        payload: dict[str, Any] = {
            "reference": reference,
            "destination": {
                "type": "bank_account",
                "amount": amount_val,
                "currency": currency.upper(),
                "narration": narration or f"GTEX Payout {reference}",
                "bank_account": {
                    "bank": bank_code,
                    "account": account_number,
                    "name": account_name,
                },
            },
            "customer": {
                "email": customer_email or "payouts@globaltalentexchange.com",
                "name": account_name,
            },
        }

        response = httpx.post(
            f"{self._base_url()}/transactions/disburse",
            json=payload,
            headers={
                "Authorization": f"Bearer {secret}",
                "Content-Type": "application/json",
            },
            timeout=35.0,
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else {}
        status_raw = str(data.get("status") or "").strip().lower()
        status = (
            "success"
            if status_raw in {"success", "successful"}
            else ("failed" if status_raw == "failed" else "pending")
        )
        provider_ref = str(data.get("reference") or data.get("trans_id") or reference)
        fee = Decimal(str(data.get("fee") or 0)).quantize(AMOUNT_QUANTUM) if data.get("fee") is not None else None

        return PayoutSession(
            reference=reference,
            provider_reference=provider_ref,
            transfer_code=str(data.get("trans_id") or data.get("id") or ""),
            status=status,
            amount=Decimal(str(amount_val)).quantize(AMOUNT_QUANTUM),
            currency=currency.upper(),
            processor_fee=fee,
            raw_payload=body,
        )

    def verify_payout(self, *, reference: str) -> PayoutVerification:
        secret = self._secret_key()
        if not secret:
            raise ValueError("KoraPay secret key is not configured for payouts.")
        norm_ref = str(reference).strip()
        if not norm_ref:
            raise ValueError("KoraPay transaction reference is required.")

        response = httpx.get(
            f"{self._base_url()}/transactions/disburse/{norm_ref}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=30.0,
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else {}
        status_raw = str(data.get("status") or "").strip().lower()
        if status_raw in {"success", "successful"}:
            status = "success"
        elif status_raw in {"failed", "rejected"}:
            status = "failed"
        elif status_raw == "reversed":
            status = "reversed"
        else:
            status = "pending"

        amount = Decimal(str(data.get("amount") or 0)).quantize(AMOUNT_QUANTUM)
        fee = Decimal(str(data.get("fee") or 0)).quantize(AMOUNT_QUANTUM) if data.get("fee") is not None else None
        reason = data.get("reason") or data.get("message")

        return PayoutVerification(
            reference=norm_ref,
            provider_reference=str(data.get("reference") or norm_ref),
            status=status,
            amount=amount,
            currency=str(data.get("currency") or "NGN").upper(),
            processor_fee=fee,
            failure_reason=str(reason) if reason else None,
            raw_payload=body,
        )

    def resolve_bank_account(self, *, account_number: str, bank_code: str) -> BankResolutionResult:
        secret = self._secret_key()
        if not secret:
            raise ValueError("KoraPay secret key is not configured.")

        response = httpx.post(
            f"{self._base_url()}/misc/banks/resolve",
            json={"bank": bank_code, "account": account_number},
            headers={
                "Authorization": f"Bearer {secret}",
                "Content-Type": "application/json",
            },
            timeout=25.0,
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else {}
        account_name = str(data.get("account_name") or "").strip()
        if not account_name:
            raise ValueError("Could not resolve account name with KoraPay.")
        return BankResolutionResult(
            account_number=account_number,
            account_name=account_name,
            bank_code=bank_code,
            bank_name=data.get("bank_name"),
        )

    def estimate_fee(self, *, amount: Decimal, operation: str = "checkout") -> ProviderFeeEstimate:
        norm_amount = Decimal(str(amount)).quantize(AMOUNT_QUANTUM)
        if operation == "payout":
            # KoraPay standard payout fee in NGN is typically NGN 25 - NGN 45
            fee = Decimal("25.0000")
            net = (norm_amount - fee).quantize(AMOUNT_QUANTUM)
            return ProviderFeeEstimate(
                amount=norm_amount,
                estimated_fee=fee,
                net_amount=max(Decimal("0.0000"), net),
                currency="NGN",
                is_estimate=True,
            )
        # Checkout collections: 1.5% capped at NGN 2,000
        calc_fee = (norm_amount * Decimal("0.015")).quantize(AMOUNT_QUANTUM)
        cap = Decimal("2000.0000")
        fee = min(calc_fee, cap)
        net = (norm_amount - fee).quantize(AMOUNT_QUANTUM)
        return ProviderFeeEstimate(
            amount=norm_amount,
            estimated_fee=fee,
            net_amount=max(Decimal("0.0000"), net),
            currency="NGN",
            is_estimate=True,
        )


__all__ = ["KoraPayProviderAdapter", "_js_json_stringify"]
