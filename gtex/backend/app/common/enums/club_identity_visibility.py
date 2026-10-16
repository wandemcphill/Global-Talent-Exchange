from __future__ import annotations

from enum import StrEnum


class ClubIdentityVisibility(StrEnum):
    PUBLIC = "public"
    COMMUNITY = "community"
    PRIVATE = "private"
