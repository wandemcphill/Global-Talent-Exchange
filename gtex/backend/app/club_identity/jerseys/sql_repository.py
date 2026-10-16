from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_identity.models.jersey_models import (
    BadgePlacement,
    BadgeProfile,
    BadgeShape,
    ClubIdentityProfile,
    CollarStyle,
    ColorPaletteProfile,
    IconFamily,
    JerseySet,
    JerseyType,
    JerseyVariant,
    MatchIdentityPayload,
    PatternType,
    SleeveStyle,
)
from app.models.club_identity_theme import ClubIdentityTheme
from app.models.club_jersey_design import ClubJerseyDesign
from app.models.club_profile import ClubProfile
from app.models.club_trophy import ClubTrophy


@dataclass(slots=True)
class SqlClubIdentityRepository:
    session: Session

    def get(self, club_id: str) -> ClubIdentityProfile | None:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            return None

        theme = self._active_theme(club_id)
        metadata = self._legacy_metadata(theme)
        palette_payload = self._as_dict(metadata.get("color_palette"))
        badge_payload = self._as_dict(metadata.get("badge_profile"))
        jersey_payload = self._as_dict(metadata.get("jersey_set"))
        short_code = str(metadata.get("short_club_code") or club.short_name or self._build_short_code(club.club_name))
        palette = ColorPaletteProfile(
            palette_name=str(palette_payload.get("palette_name") or "club"),
            primary_color=str(palette_payload.get("primary_color") or club.primary_color),
            secondary_color=str(palette_payload.get("secondary_color") or club.secondary_color),
            accent_color=str(palette_payload.get("accent_color") or club.accent_color),
            shorts_color=str(palette_payload.get("shorts_color") or club.primary_color),
            socks_color=str(palette_payload.get("socks_color") or club.secondary_color),
        )
        badge = BadgeProfile(
            shape=BadgeShape(str(badge_payload.get("shape") or "shield")),
            initials=str(badge_payload.get("initials") or short_code),
            icon_family=IconFamily(str(badge_payload.get("icon_family") or "star")),
            primary_color=str(badge_payload.get("primary_color") or club.primary_color),
            secondary_color=str(badge_payload.get("secondary_color") or club.secondary_color),
            accent_color=str(badge_payload.get("accent_color") or club.accent_color),
            badge_url=club.crest_asset_ref or self._string_or_none(badge_payload.get("badge_url")),
            trophy_star_count=self._int_value(
                badge_payload.get("trophy_star_count"),
                self._derive_trophy_star_count(club_id),
            ),
            commemorative_patch=self._string_or_none(badge_payload.get("commemorative_patch")),
        )
        designs = self.session.scalars(
            select(ClubJerseyDesign)
            .where(ClubJerseyDesign.club_id == club_id)
            .order_by(ClubJerseyDesign.created_at.asc())
        ).all()
        designs_by_slot = {str(item.slot_type): item for item in designs}
        jersey_set = JerseySet(
            home=self._variant(
                slot=JerseyType.HOME,
                palette=palette,
                front_text=short_code,
                design=designs_by_slot.get(JerseyType.HOME.value),
                stored=self._as_dict(jersey_payload.get(JerseyType.HOME.value)),
            ),
            away=self._variant(
                slot=JerseyType.AWAY,
                palette=palette,
                front_text=short_code,
                design=designs_by_slot.get(JerseyType.AWAY.value),
                stored=self._as_dict(jersey_payload.get(JerseyType.AWAY.value)),
            ),
            third=self._variant(
                slot=JerseyType.THIRD,
                palette=palette,
                front_text=f"{short_code} ALT",
                design=designs_by_slot.get(JerseyType.THIRD.value),
                stored=self._as_dict(jersey_payload.get(JerseyType.THIRD.value)),
            ),
            goalkeeper=self._variant(
                slot=JerseyType.GOALKEEPER,
                palette=palette,
                front_text=f"{short_code} GK",
                design=designs_by_slot.get(JerseyType.GOALKEEPER.value),
                stored=self._as_dict(jersey_payload.get(JerseyType.GOALKEEPER.value)),
            ),
        )
        return ClubIdentityProfile(
            club_id=club.id,
            club_name=club.club_name,
            short_club_code=short_code,
            color_palette=palette,
            badge_profile=badge,
            jersey_set=jersey_set,
            match_identity=MatchIdentityPayload(
                club_name=club.club_name,
                short_club_code=short_code,
                badge_url=badge.badge_url,
                generated_badge=badge,
                home_kit_colors=(
                    jersey_set.home.primary_color,
                    jersey_set.home.secondary_color,
                    jersey_set.home.accent_color,
                ),
                away_kit_colors=(
                    jersey_set.away.primary_color,
                    jersey_set.away.secondary_color,
                    jersey_set.away.accent_color,
                ),
            ),
        )

    def save(self, profile: ClubIdentityProfile) -> ClubIdentityProfile:
        club = self.session.get(ClubProfile, profile.club_id)
        if club is None:
            raise LookupError(f"club {profile.club_id} was not found")

        club.club_name = profile.club_name
        club.short_name = profile.short_club_code
        club.primary_color = profile.color_palette.primary_color
        club.secondary_color = profile.color_palette.secondary_color
        club.accent_color = profile.color_palette.accent_color
        club.crest_asset_ref = profile.badge_profile.badge_url

        theme = self._ensure_active_theme(club)
        theme.metadata_json = {
            "legacy_identity": {
                "short_club_code": profile.short_club_code,
                "color_palette": {
                    "palette_name": profile.color_palette.palette_name,
                    "primary_color": profile.color_palette.primary_color,
                    "secondary_color": profile.color_palette.secondary_color,
                    "accent_color": profile.color_palette.accent_color,
                    "shorts_color": profile.color_palette.shorts_color,
                    "socks_color": profile.color_palette.socks_color,
                },
                "badge_profile": {
                    "shape": profile.badge_profile.shape.value,
                    "initials": profile.badge_profile.initials,
                    "icon_family": profile.badge_profile.icon_family.value,
                    "primary_color": profile.badge_profile.primary_color,
                    "secondary_color": profile.badge_profile.secondary_color,
                    "accent_color": profile.badge_profile.accent_color,
                    "badge_url": profile.badge_profile.badge_url,
                    "trophy_star_count": profile.badge_profile.trophy_star_count,
                    "commemorative_patch": profile.badge_profile.commemorative_patch,
                },
                "jersey_set": {
                    JerseyType.HOME.value: self._jersey_metadata(profile.jersey_set.home),
                    JerseyType.AWAY.value: self._jersey_metadata(profile.jersey_set.away),
                    JerseyType.THIRD.value: self._jersey_metadata(profile.jersey_set.third),
                    JerseyType.GOALKEEPER.value: self._jersey_metadata(profile.jersey_set.goalkeeper),
                },
            }
        }

        for variant in (
            profile.jersey_set.home,
            profile.jersey_set.away,
            profile.jersey_set.third,
            profile.jersey_set.goalkeeper,
        ):
            design = self.session.scalar(
                select(ClubJerseyDesign).where(
                    ClubJerseyDesign.club_id == profile.club_id,
                    ClubJerseyDesign.slot_type == variant.jersey_type.value,
                )
            )
            if design is None:
                design = ClubJerseyDesign(
                    club_id=profile.club_id,
                    name=f"{profile.club_name} {variant.jersey_type.value.title()} Kit",
                    slot_type=variant.jersey_type.value,
                    base_template_id=variant.pattern_type.value,
                    primary_color=variant.primary_color,
                    secondary_color=variant.secondary_color,
                    trim_color=variant.accent_color,
                    sleeve_style=variant.sleeve_style.value,
                    motto_text=variant.front_text or None,
                    crest_placement=variant.badge_placement.value,
                    metadata_json={},
                )
                self.session.add(design)
            design.base_template_id = variant.pattern_type.value
            design.primary_color = variant.primary_color
            design.secondary_color = variant.secondary_color
            design.trim_color = variant.accent_color
            design.sleeve_style = variant.sleeve_style.value
            design.motto_text = variant.front_text or None
            design.crest_placement = variant.badge_placement.value
            design.metadata_json = {
                "collar_style": variant.collar_style.value,
                "pattern_type": variant.pattern_type.value,
                "theme_tags": list(variant.theme_tags),
                "commemorative_patch": variant.commemorative_patch,
                "shorts_color": variant.shorts_color,
                "socks_color": variant.socks_color,
            }

        self.session.flush()
        return profile

    def _active_theme(self, club_id: str) -> ClubIdentityTheme | None:
        return self.session.scalar(
            select(ClubIdentityTheme)
            .where(ClubIdentityTheme.club_id == club_id, ClubIdentityTheme.is_active.is_(True))
            .order_by(ClubIdentityTheme.updated_at.desc())
        )

    def _ensure_active_theme(self, club: ClubProfile) -> ClubIdentityTheme:
        theme = self._active_theme(club.id)
        if theme is not None:
            return theme
        theme = ClubIdentityTheme(
            club_id=club.id,
            name=f"{club.club_name} Identity",
            is_active=True,
            metadata_json={},
        )
        self.session.add(theme)
        self.session.flush()
        return theme

    def _derive_trophy_star_count(self, club_id: str) -> int:
        count = len(self.session.scalars(select(ClubTrophy.id).where(ClubTrophy.club_id == club_id)).all())
        return min(10, count)

    def _legacy_metadata(self, theme: ClubIdentityTheme | None) -> dict[str, Any]:
        if theme is None:
            return {}
        raw = dict(theme.metadata_json or {})
        legacy = raw.get("legacy_identity")
        return legacy if isinstance(legacy, dict) else {}

    def _variant(
        self,
        *,
        slot: JerseyType,
        palette: ColorPaletteProfile,
        front_text: str,
        design: ClubJerseyDesign | None,
        stored: dict[str, Any],
    ) -> JerseyVariant:
        metadata = {**stored, **(design.metadata_json or {})} if design is not None else dict(stored)
        defaults = {
            JerseyType.HOME: (
                palette.primary_color,
                palette.secondary_color,
                palette.accent_color,
                "crew",
                "short",
                "solid",
            ),
            JerseyType.AWAY: (
                palette.secondary_color,
                palette.primary_color,
                palette.accent_color,
                "v_neck",
                "raglan",
                "sash",
            ),
            JerseyType.THIRD: (
                palette.accent_color,
                palette.primary_color,
                palette.secondary_color,
                "crew",
                "short",
                "hoops",
            ),
            JerseyType.GOALKEEPER: ("#111827", "#F8FAFC", palette.accent_color, "crew", "long", "solid"),
        }[slot]
        pattern_value = str(
            metadata.get("pattern_type") or design.base_template_id if design is not None else defaults[5]
        )
        if pattern_value not in PatternType._value2member_map_:
            pattern_value = defaults[5]
        return JerseyVariant(
            jersey_type=slot,
            primary_color=str(
                design.primary_color if design is not None else stored.get("primary_color") or defaults[0]
            ),
            secondary_color=str(
                design.secondary_color if design is not None else stored.get("secondary_color") or defaults[1]
            ),
            accent_color=str(design.trim_color if design is not None else stored.get("accent_color") or defaults[2]),
            collar_style=CollarStyle(str(metadata.get("collar_style") or defaults[3])),
            sleeve_style=SleeveStyle(
                str(
                    design.sleeve_style
                    if design is not None and design.sleeve_style
                    else metadata.get("sleeve_style") or defaults[4]
                )
            ),
            pattern_type=PatternType(pattern_value),
            badge_placement=BadgePlacement(
                str(design.crest_placement if design is not None else metadata.get("badge_placement") or "left_chest")
            ),
            front_text=str(
                design.motto_text
                if design is not None and design.motto_text
                else metadata.get("front_text") or front_text
            ),
            shorts_color=str(metadata.get("shorts_color") or palette.shorts_color),
            socks_color=str(metadata.get("socks_color") or palette.socks_color),
            theme_tags=tuple(str(tag) for tag in (metadata.get("theme_tags") or self._theme_tags(slot))),
            commemorative_patch=self._string_or_none(metadata.get("commemorative_patch")),
        )

    def _jersey_metadata(self, variant: JerseyVariant) -> dict[str, Any]:
        return {
            "primary_color": variant.primary_color,
            "secondary_color": variant.secondary_color,
            "accent_color": variant.accent_color,
            "pattern_type": variant.pattern_type.value,
            "collar_style": variant.collar_style.value,
            "sleeve_style": variant.sleeve_style.value,
            "badge_placement": variant.badge_placement.value,
            "front_text": variant.front_text,
            "shorts_color": variant.shorts_color,
            "socks_color": variant.socks_color,
            "theme_tags": list(variant.theme_tags),
            "commemorative_patch": variant.commemorative_patch,
        }

    def _build_short_code(self, club_name: str) -> str:
        letters = "".join(part[:1].upper() for part in club_name.replace("-", " ").split() if part)
        return (letters or club_name[:3].upper())[:6]

    def _theme_tags(self, slot: JerseyType) -> list[str]:
        return {
            JerseyType.HOME: ["core"],
            JerseyType.AWAY: ["road"],
            JerseyType.THIRD: ["alt"],
            JerseyType.GOALKEEPER: ["keeper"],
        }[slot]

    def _as_dict(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _int_value(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _string_or_none(self, value: Any) -> str | None:
        if value is None:
            return None
        resolved = str(value).strip()
        return resolved or None
