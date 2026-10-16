from __future__ import annotations

from enum import StrEnum


class CompetitionPayoutMode(StrEnum):
    WINNER_TAKE_ALL = "winner_take_all"
    TOP_N = "top_n"
    CUSTOM_PERCENT = "custom_percent"


__all__ = ["CompetitionPayoutMode"]
