from __future__ import annotations

from enum import StrEnum


class SponsorshipStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


__all__ = ["SponsorshipStatus"]
