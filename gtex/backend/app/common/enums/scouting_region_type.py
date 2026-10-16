from __future__ import annotations

from enum import StrEnum


class ScoutingRegionType(StrEnum):
    DOMESTIC = "domestic"
    REGIONAL = "regional"
    INTERNATIONAL = "international"
    DIASPORA = "diaspora"


__all__ = ["ScoutingRegionType"]
