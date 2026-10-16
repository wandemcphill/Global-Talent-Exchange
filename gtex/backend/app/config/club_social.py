from __future__ import annotations

CHALLENGE_WEB_PATH_PREFIX = "/challenge"
CHALLENGE_DEEP_LINK_PREFIX = "gtex://challenge"

DEFAULT_HIGH_VIEW_THRESHOLD = 500
DEFAULT_HIGH_GIFT_THRESHOLD = 25
DEFAULT_RIVALRY_FEATURE_THRESHOLD = 40
DEFAULT_RIVALRY_STORY_THRESHOLD = 65

DEFAULT_CHALLENGE_VISIBILITY = "public"
DEFAULT_CHALLENGE_STATUS = "open"

CHALLENGE_STATUSES: tuple[str, ...] = ("open", "accepted", "scheduled", "live", "settled")
REACTION_TYPES: tuple[str, ...] = (
    "what_a_goal",
    "big_save",
    "missed_chance",
    "red_card_chaos",
    "giant_killer_alert",
)
