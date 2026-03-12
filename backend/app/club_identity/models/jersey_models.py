from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class JerseyType(StrEnum):
    HOME = "home"
    AWAY = "away"
    THIRD = "third"
    GOALKEEPER = "goalkeeper"


class CollarStyle(StrEnum):
    CREW = "crew"
    V_NECK = "v_neck"
    POLO = "polo"
    WRAP = "wrap"


class SleeveStyle(StrEnum):
    SHORT = "short"
    LONG = "long"
    RAGLAN = "raglan"
    CUFFED = "cuffed"


class PatternType(StrEnum):
    SOLID = "solid"
    STRIPES = "stripes"
    HOOPS = "hoops"
    SASH = "sash"
    CHEVRON = "chevron"
    GRADIENT = "gradient"


class BadgePlacement(StrEnum):
    LEFT_CHEST = "left_chest"
    CENTER_CHEST = "center_chest"
    RIGHT_CHEST = "right_chest"


class BadgeShape(StrEnum):
    SHIELD = "shield"
    ROUND = "round"
    DIAMOND = "diamond"
    PENNANT = "pennant"


class IconFamily(StrEnum):
    STAR = "star"
    LION = "lion"
    EAGLE = "eagle"
    CROWN = "crown"
    OAK = "oak"
    BOLT = "bolt"


@dataclass(slots=True, frozen=True)
class ColorPaletteProfile:
    palette_name: str
    primary_color: str
    secondary_color: str
    accent_color: str
    shorts_color: str
    socks_color: str


@dataclass(slots=True, frozen=True)
class BadgeProfile:
    shape: BadgeShape
    initials: str
    icon_family: IconFamily
    primary_color: str
    secondary_color: str
    accent_color: str
    badge_url: str | None = None
    trophy_star_count: int = 0
    commemorative_patch: str | None = None


@dataclass(slots=True, frozen=True)
class JerseyVariant:
    jersey_type: JerseyType
    primary_color: str
    secondary_color: str
    accent_color: str
    collar_style: CollarStyle
    sleeve_style: SleeveStyle
    pattern_type: PatternType
    badge_placement: BadgePlacement
    front_text: str
    shorts_color: str
    socks_color: str
    theme_tags: tuple[str, ...] = field(default_factory=tuple)
    commemorative_patch: str | None = None


@dataclass(slots=True, frozen=True)
class JerseySet:
    home: JerseyVariant
    away: JerseyVariant
    third: JerseyVariant
    goalkeeper: JerseyVariant


@dataclass(slots=True, frozen=True)
class MatchIdentityPayload:
    club_name: str
    short_club_code: str
    badge_url: str | None
    generated_badge: BadgeProfile
    home_kit_colors: tuple[str, str, str]
    away_kit_colors: tuple[str, str, str]


@dataclass(slots=True, frozen=True)
class ClubIdentityProfile:
    club_id: str
    club_name: str
    short_club_code: str
    color_palette: ColorPaletteProfile
    badge_profile: BadgeProfile
    jersey_set: JerseySet
    match_identity: MatchIdentityPayload
