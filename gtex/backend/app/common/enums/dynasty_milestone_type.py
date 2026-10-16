from __future__ import annotations

from enum import StrEnum


class DynastyMilestoneType(StrEnum):
    SEASONS_COMPLETED = "seasons_completed"
    TOP_FINISH_STREAK = "top_finish_streak"
    PARTICIPATION_STREAK = "participation_streak"
    TROPHY_STREAK = "trophy_streak"
    COMMUNITY_PRESTIGE = "community_prestige"
    CLUB_LOYALTY = "club_loyalty"
    CREATOR_LEGACY = "creator_legacy"
