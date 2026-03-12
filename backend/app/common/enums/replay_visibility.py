from __future__ import annotations

from enum import StrEnum


class ReplayVisibility(StrEnum):
    PRIVATE = "private"
    PARTICIPANTS = "participants"
    COMPETITION = "competition"
    PUBLIC = "public"
