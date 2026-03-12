from __future__ import annotations

from enum import StrEnum


class PlayerPathwayStage(StrEnum):
    DISCOVERED = "discovered"
    SHORTLISTED = "shortlisted"
    INVITED = "invited"
    TRIALING = "trialing"
    ACADEMY_SIGNED = "academy_signed"
    PROMOTED = "promoted"
    RELEASED = "released"


__all__ = ["PlayerPathwayStage"]
