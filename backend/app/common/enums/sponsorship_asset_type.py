from __future__ import annotations

from enum import StrEnum


class SponsorshipAssetType(StrEnum):
    JERSEY_FRONT = "jersey_front"
    JERSEY_BACK = "jersey_back"
    SLEEVE_SLOT = "sleeve_slot"
    CLUB_BANNER = "club_banner"
    PROFILE_HEADER = "profile_header"
    SHOWCASE_BACKDROP = "showcase_backdrop"
    TOURNAMENT_CARD_SLOT = "tournament_card_slot"


__all__ = ["SponsorshipAssetType"]
