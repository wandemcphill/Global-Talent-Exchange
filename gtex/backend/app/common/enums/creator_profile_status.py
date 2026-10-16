from __future__ import annotations

from enum import StrEnum


class CreatorProfileStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"
