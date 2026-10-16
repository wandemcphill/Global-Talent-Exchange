from __future__ import annotations

from enum import StrEnum


class CompetitionFormat(StrEnum):
    LEAGUE = "league"
    CUP = "cup"


__all__ = ["CompetitionFormat"]
