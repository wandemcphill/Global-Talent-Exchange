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
