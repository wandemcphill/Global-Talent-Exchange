from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.wallets.providers.base import ProviderEvent, ProviderEventType


class PaystackProviderAdapter:
    key = "paystack"
    display_name = "Paystack"

    def parse_webhook(self, payload: dict[str, Any], headers: dict[str, str] | None = None) -> ProviderEvent | None:
        del headers
        if not isinstance(payload, dict):
            return None
        raw_event = str(payload.get("event") or "").strip().lower()
        data = payload.get("data")
        if not raw_event or not isinstance(data, dict):
            return None

        mapped_type = self._map_event_type(raw_event, data)
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
                amount = (Decimal(str(raw_amount)) / Decimal("100")).quantize(Decimal("0.0001"))
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
        )

    def _map_event_type(self, raw_event: str, data: dict[str, Any]) -> ProviderEventType | None:
        status = str(data.get("status") or "").strip().lower()
        mapping = {
            "charge.success": ProviderEventType.SETTLED,
            "charge.failed": ProviderEventType.FAILED,
            "charge.dispute.create": ProviderEventType.DISPUTED,
            "refund.processed": ProviderEventType.REFUNDED,
            "transfer.success": ProviderEventType.SETTLED,
            "transfer.failed": ProviderEventType.FAILED,
            "transfer.reversed": ProviderEventType.REVERSED,
        }
        if raw_event in mapping:
            return mapping[raw_event]
        if status == "success":
            return ProviderEventType.SETTLED
        if status == "failed":
            return ProviderEventType.FAILED
        if status == "pending":
            return ProviderEventType.PENDING
        return None


__all__ = ["PaystackProviderAdapter"]
