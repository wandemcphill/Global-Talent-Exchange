from __future__ import annotations

from enum import StrEnum


class AcademyPlayerStatus(StrEnum):
    TRIALIST = "trialist"
    ENROLLED = "enrolled"
    DEVELOPING = "developing"
    STANDOUT = "standout"
    PROMOTED = "promoted"
    RELEASED = "released"


__all__ = ["AcademyPlayerStatus"]
