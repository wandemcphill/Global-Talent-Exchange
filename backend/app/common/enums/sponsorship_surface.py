from __future__ import annotations

from enum import StrEnum


class SponsorshipSurface(StrEnum):
    STADIUM_BOARD = "stadium_board"
    TUNNEL_WALKOUT = "tunnel_walkout"
    REPLAY_STING = "replay_sting"
    HALFTIME_OVERLAY = "halftime_overlay"
    LINEUP_STRIP = "lineup_strip"
    FINALS_TROPHY_BACKDROP = "finals_trophy_backdrop"


__all__ = ["SponsorshipSurface"]
