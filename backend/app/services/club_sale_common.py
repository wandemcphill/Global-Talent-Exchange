from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.club_sale import ClubSaleAuditEvent
from backend.app.risk_ops_engine.service import RiskOpsService

AMOUNT_QUANTUM = Decimal("0.0001")
CLUB_SALE_PLATFORM_FEE_BPS = 1_000
CLUB_SALE_VALUATION_VERSION = "club_sale_v1"


class ClubSaleError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


def normalize_coin(value: Decimal | str | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0.0000")
    return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)


def append_club_sale_audit(
    session: Session,
    risk_ops: RiskOpsService,
    *,
    club_id: str,
    actor_user_id: str | None,
    event_type: str,
    detail: str,
    listing_id: str | None = None,
    inquiry_id: str | None = None,
    offer_id: str | None = None,
    transfer_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    payload_json = {
        "detail": detail,
        **(payload or {}),
    }
    session.add(
        ClubSaleAuditEvent(
            club_id=club_id,
            actor_user_id=actor_user_id,
            action=event_type,
            listing_id=listing_id,
            inquiry_id=inquiry_id,
            offer_id=offer_id,
            transfer_id=transfer_id,
            payload_json=payload_json,
        )
    )
    risk_ops.log_audit(
        actor_user_id=actor_user_id,
        action_key=event_type,
        resource_type="club_sale",
        resource_id=transfer_id or offer_id or inquiry_id or listing_id or club_id,
        detail=detail,
        metadata_json=payload_json,
    )


__all__ = [
    "AMOUNT_QUANTUM",
    "CLUB_SALE_PLATFORM_FEE_BPS",
    "CLUB_SALE_VALUATION_VERSION",
    "ClubSaleError",
    "append_club_sale_audit",
    "normalize_coin",
]
