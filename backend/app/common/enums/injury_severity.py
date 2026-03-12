from __future__ import annotations

from enum import Enum


class InjurySeverity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    SEASON_ENDING = "season_ending"
