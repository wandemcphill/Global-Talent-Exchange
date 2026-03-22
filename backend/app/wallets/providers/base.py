from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol


class ProviderEventType(StrEnum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    PENDING = "pending"
    CAPTURED = "captured"
    SETTLED = "settled"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    CHARGEBACK = "chargeback"
    REVERSED = "reversed"
    DISPUTED = "disputed"


@dataclass(frozen=True, slots=True)
class ProviderEvent:
    provider_key: str
    event_type: ProviderEventType
    provider_reference: str
    purchase_order_reference: str | None
    event_id: str | None
    amount: Decimal | None
    currency: str | None
    raw_payload: dict[str, Any]


class ProviderAdapter(Protocol):
    key: str
    display_name: str

    def parse_webhook(self, payload: dict[str, Any], headers: dict[str, str] | None = None) -> ProviderEvent | None:
        ...


class GenericProviderAdapter:
    def __init__(self, *, key: str, display_name: str) -> None:
        self.key = key
        self.display_name = display_name

    def parse_webhook(self, payload: dict[str, Any], headers: dict[str, str] | None = None) -> ProviderEvent | None:
        if not isinstance(payload, dict):
            return None
        raw_type = payload.get("event_type") or payload.get("status") or payload.get("type")
        if not raw_type:
            return None
        try:
            event_type = ProviderEventType(str(raw_type).strip().lower())
        except ValueError:
            return None
        provider_reference = payload.get("provider_reference") or payload.get("transaction_id") or payload.get("reference")
        if not provider_reference:
            return None
        purchase_order_reference = payload.get("purchase_order_reference") or payload.get("order_reference") or payload.get("order_id")
        event_id = payload.get("event_id") or payload.get("id")
        amount_raw = payload.get("amount") or payload.get("gross_amount")
        amount = None
        if amount_raw is not None:
            try:
                amount = Decimal(str(amount_raw)).quantize(Decimal("0.0001"))
            except Exception:
                amount = None
        currency = payload.get("currency") or payload.get("currency_code")
        return ProviderEvent(
            provider_key=self.key,
            event_type=event_type,
            provider_reference=str(provider_reference),
            purchase_order_reference=str(purchase_order_reference) if purchase_order_reference else None,
            event_id=str(event_id) if event_id else None,
            amount=amount,
            currency=str(currency) if currency else None,
            raw_payload=payload,
        )
