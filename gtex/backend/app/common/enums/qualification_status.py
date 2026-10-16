from __future__ import annotations

from enum import StrEnum


class QualificationStatus(StrEnum):
    PENDING = "pending"
    DIRECT = "direct"
    PLAYOFF = "playoff"
    QUALIFIED = "qualified"
    ELIMINATED = "eliminated"
