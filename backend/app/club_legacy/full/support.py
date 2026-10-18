"""Shared helpers for Club Legacy phases 4-6."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.club_legacy.models import ClubLegacyAuditEvent


def money(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def remember_refusal(
    session: Session,
    *,
    club_id: str | None,
    actor_user_id: str | None,
    action: str,
    detail: dict,
) -> None:
    """Record a refused attempt in this transaction and keep a plain copy for the API.

    Route handlers roll the business transaction back when they return an error.
    The copy in ``session.info`` is written again after that rollback so the
    attempt stays in the audit table.
    """
    payload = {
        "club_id": club_id,
        "actor_user_id": actor_user_id,
        "action": action,
        "detail_json": dict(detail),
    }
    session.add(ClubLegacyAuditEvent(**payload))
    session.flush()
    session.info.setdefault("legacy_refusals", []).append(payload)
