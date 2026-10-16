from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.club_identity.models.jersey_models import (
    BadgePlacement,
    BadgeShape,
    CollarStyle,
    IconFamily,
    JerseyType,
    PatternType,
    SleeveStyle,
)


class _BaseView(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ColorPaletteProfileView(_BaseView):
    palette_name: str
    primary_color: str
    secondary_color: str
    accent_color: str
    shorts_color: str
    socks_color: str


class BadgeProfileView(_BaseView):
    shape: BadgeShape
    initials: str
    icon_family: IconFamily
    primary_color: str
    secondary_color: str
    accent_color: str
    badge_url: str | None = None
    trophy_star_count: int
    commemorative_patch: str | None = None


class JerseyVariantView(_BaseView):
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
    theme_tags: tuple[str, ...]
    commemorative_patch: str | None = None


class JerseySetView(_BaseView):
    home: JerseyVariantView
    away: JerseyVariantView
    third: JerseyVariantView
    goalkeeper: JerseyVariantView


class MatchIdentityPayloadView(_BaseView):
    club_name: str
    short_club_code: str
    badge_url: str | None = None
    generated_badge: BadgeProfileView
    home_kit_colors: tuple[str, str, str]
    away_kit_colors: tuple[str, str, str]


class ClubIdentityProfileView(_BaseView):
    club_id: str
    club_name: str
    short_club_code: str
    color_palette: ColorPaletteProfileView
    badge_profile: BadgeProfileView
    jersey_set: JerseySetView
    match_identity: MatchIdentityPayloadView


class ColorPaletteProfilePatch(BaseModel):
    palette_name: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    shorts_color: str | None = None
    socks_color: str | None = None


class BadgeProfilePatch(BaseModel):
    shape: BadgeShape | None = None
    initials: str | None = Field(default=None, min_length=1, max_length=6)
    icon_family: IconFamily | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    badge_url: str | None = None
    trophy_star_count: int | None = Field(default=None, ge=0, le=10)
    commemorative_patch: str | None = Field(default=None, max_length=32)


class JerseyVariantPatch(BaseModel):
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    collar_style: CollarStyle | None = None
    sleeve_style: SleeveStyle | None = None
    pattern_type: PatternType | None = None
    badge_placement: BadgePlacement | None = None
    front_text: str | None = Field(default=None, min_length=1, max_length=20)
    shorts_color: str | None = None
    socks_color: str | None = None
    theme_tags: tuple[str, ...] | None = None
    commemorative_patch: str | None = Field(default=None, max_length=32)


class JerseySetPatch(BaseModel):
    home: JerseyVariantPatch | None = None
    away: JerseyVariantPatch | None = None
    third: JerseyVariantPatch | None = None
    goalkeeper: JerseyVariantPatch | None = None


class ClubIdentityProfilePatch(BaseModel):
    club_name: str | None = Field(default=None, min_length=2, max_length=64)
    short_club_code: str | None = Field(default=None, min_length=2, max_length=6)
    color_palette: ColorPaletteProfilePatch | None = None
    badge_profile: BadgeProfilePatch | None = None
    jersey_set: JerseySetPatch | None = None
