from __future__ import annotations

from enum import StrEnum


class CompetitionStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    SEEDED = "seeded"
    LIVE = "live"
    PUBLISHED = "published"
    OPEN_FOR_JOIN = "open_for_join"
    FILLED = "filled"
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SETTLED = "settled"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


__all__ = ["CompetitionStatus"]
