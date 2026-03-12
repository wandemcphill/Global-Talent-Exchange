from __future__ import annotations

from enum import StrEnum


class CompetitionVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    INVITE_ONLY = "invite_only"


__all__ = ["CompetitionVisibility"]
