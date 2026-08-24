from __future__ import annotations

from enum import StrEnum


class MatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"
    FAILED = "failed"

    @classmethod
    def coerce(cls, value: object) -> "MatchStatus | None":
        """Best-effort parse of a persisted status string.

        Returns ``None`` for values that are not part of the lifecycle vocabulary so
        callers can degrade gracefully instead of raising ``ValueError`` on rows written
        by older or external code paths.
        """
        if isinstance(value, cls):
            return value
        if value is None:
            return None
        candidate = str(value).strip().lower()
        if not candidate:
            return None
        try:
            return cls(candidate)
        except ValueError:
            return None
