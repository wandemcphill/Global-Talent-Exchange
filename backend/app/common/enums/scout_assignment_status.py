from __future__ import annotations

from enum import StrEnum


class ScoutAssignmentStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


__all__ = ["ScoutAssignmentStatus"]
