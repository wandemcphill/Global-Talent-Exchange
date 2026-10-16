from __future__ import annotations

from enum import StrEnum


class YouthProspectRatingBand(StrEnum):
    FOUNDATION = "foundation"
    DEVELOPMENT = "development"
    HIGH_UPSIDE = "high_upside"
    ELITE = "elite"


__all__ = ["YouthProspectRatingBand"]
