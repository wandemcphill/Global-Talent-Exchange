from __future__ import annotations

from enum import StrEnum


class CompetitionStartMode(StrEnum):
    SCHEDULED = "scheduled"
    WHEN_FULL = "when_full"
    MANUAL_AFTER_MIN = "manual_after_min"


__all__ = ["CompetitionStartMode"]
