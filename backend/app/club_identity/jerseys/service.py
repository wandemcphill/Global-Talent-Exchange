from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import math

from backend.app.club_identity.jerseys.repository import InMemoryClubIdentityRepository
from backend.app.club_identity.models.jersey_models import (
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

DEFAULT_PALETTES: tuple[ColorPaletteProfile, ...] = (
    ColorPaletteProfile("royal", "#123C73", "#F5F7FA", "#E2A400", "#0C1F3F", "#F5F7FA"),
    ColorPaletteProfile("forest", "#0F5132", "#F2F0E6", "#D97706", "#1B4332", "#E9F5DB"),
    ColorPaletteProfile("sunset", "#8A1538", "#F8E16C", "#FFD166", "#5C1D2B", "#F8E16C"),
    ColorPaletteProfile("ocean", "#005F73", "#E9D8A6", "#94D2BD", "#003845", "#E9D8A6"),
    ColorPaletteProfile("ember", "#7F1D1D", "#F8FAFC", "#F97316", "#111827", "#F8FAFC"),
    ColorPaletteProfile("violet", "#4C1D95", "#EDE9FE", "#22C55E", "#312E81", "#EDE9FE"),
)

DEFAULT_BADGE_SHAPES: tuple[BadgeShape, ...] = (
    BadgeShape.SHIELD,
    BadgeShape.ROUND,
    BadgeShape.DIAMOND,
    BadgeShape.PENNANT,
)

DEFAULT_ICON_FAMILIES: tuple[IconFamily, ...] = (
    IconFamily.STAR,
    IconFamily.LION,
    IconFamily.EAGLE,
    IconFamily.CROWN,
    IconFamily.OAK,
    IconFamily.BOLT,
)


def _normalize_hex(color: str) -> str:
    value = color.strip().upper()
    if not value.startswith("#"):
        value = f"#{value}"
    if len(value) != 7 or any(character not in "0123456789ABCDEF#" for character in value):
        raise ValueError(f"Invalid color value: {color}")
    return value


def _to_rgb(color: str) -> tuple[int, int, int]:
    normalized = _normalize_hex(color)
    return (
        int(normalized[1:3], 16),
        int(normalized[3:5], 16),
        int(normalized[5:7], 16),
    )


def _relative_luminance(color: str) -> float:
    red, green, blue = _to_rgb(color)

    def _channel(value: int) -> float:
        scaled = value / 255
        if scaled <= 0.03928:
            return scaled / 12.92
        return ((scaled + 0.055) / 1.055) ** 2.4

    return (0.2126 * _channel(red)) + (0.7152 * _channel(green)) + (0.0722 * _channel(blue))


def _contrast_ratio(color_a: str, color_b: str) -> float:
    luminance_a = _relative_luminance(color_a)
    luminance_b = _relative_luminance(color_b)
    lighter = max(luminance_a, luminance_b)
    darker = min(luminance_a, luminance_b)
    return (lighter + 0.05) / (darker + 0.05)


def _color_distance(color_a: str, color_b: str) -> float:
    a_red, a_green, a_blue = _to_rgb(color_a)
    b_red, b_green, b_blue = _to_rgb(color_b)
    return math.sqrt(
        ((a_red - b_red) ** 2) + ((a_green - b_green) ** 2) + ((a_blue - b_blue) ** 2)
    )


@dataclass(slots=True)
class ClubIdentityService:
    repository: InMemoryClubIdentityRepository

    def get_identity(self, club_id: str) -> ClubIdentityProfile:
        existing = self.repository.get(club_id)
        if existing is not None:
            return self._ensure_complete(existing)
        generated = self._build_default_identity(club_id=club_id)
        return self.repository.save(generated)

    def update_identity(self, club_id: str, payload: dict[str, object]) -> ClubIdentityProfile:
        current = self.get_identity(club_id)
        club_name = str(payload.get("club_name", current.club_name))
        short_club_code = str(payload.get("short_club_code", current.short_club_code))
        color_palette = self._merge_palette(current.color_palette, payload.get("color_palette"))
        badge_profile = self._merge_badge(
            current.badge_profile,
            payload.get("badge_profile"),
            color_palette,
            club_name,
        )
        jersey_set = current.jersey_set
        if "jersey_set" in payload:
            jersey_set = self._merge_jersey_set(
                current.jersey_set,
                payload.get("jersey_set"),
                color_palette,
                short_club_code,
            )
        profile = self._build_identity_profile(
            club_id=club_id,
            club_name=club_name,
            short_club_code=short_club_code,
            color_palette=color_palette,
            badge_profile=badge_profile,
            jersey_set=jersey_set,
        )
        return self.repository.save(self._ensure_complete(profile))

    def get_jerseys(self, club_id: str) -> JerseySet:
        return self.get_identity(club_id).jersey_set

    def update_jerseys(self, club_id: str, payload: dict[str, object]) -> JerseySet:
        current = self.get_identity(club_id)
        jersey_set = self._merge_jersey_set(
            current.jersey_set,
            payload,
            current.color_palette,
            current.short_club_code,
        )
        updated = replace(current, jersey_set=jersey_set)
        updated = self._ensure_complete(updated)
        self.repository.save(updated)
        return updated.jersey_set

    def get_badge(self, club_id: str) -> BadgeProfile:
        return self.get_identity(club_id).badge_profile

    def _build_default_identity(self, club_id: str, club_name: str | None = None) -> ClubIdentityProfile:
        resolved_name = club_name or self._titleize_club_name(club_id)
        short_code = self._build_short_code(resolved_name)
        palette = self._select_palette(club_id)
        badge = self._build_badge_profile(club_id, resolved_name, palette)
        jersey_set = self._build_default_jersey_set(short_code, palette)
        return self._build_identity_profile(
            club_id=club_id,
            club_name=resolved_name,
            short_club_code=short_code,
            color_palette=palette,
            badge_profile=badge,
            jersey_set=jersey_set,
        )

    def _build_identity_profile(
        self,
        *,
        club_id: str,
        club_name: str,
        short_club_code: str,
        color_palette: ColorPaletteProfile,
        badge_profile: BadgeProfile,
        jersey_set: JerseySet,
    ) -> ClubIdentityProfile:
        complete_jersey_set = self._ensure_jersey_set(jersey_set, color_palette, short_club_code)
        self._validate_variant(complete_jersey_set.home)
        self._validate_variant(complete_jersey_set.away)
        self._validate_variant(complete_jersey_set.third)
        self._validate_variant(complete_jersey_set.goalkeeper)
        self._validate_home_away_distinction(complete_jersey_set.home, complete_jersey_set.away)
        match_identity = MatchIdentityPayload(
            club_name=club_name,
            short_club_code=short_club_code,
            badge_url=badge_profile.badge_url,
            generated_badge=badge_profile,
            home_kit_colors=(
                complete_jersey_set.home.primary_color,
                complete_jersey_set.home.secondary_color,
                complete_jersey_set.home.accent_color,
            ),
            away_kit_colors=(
                complete_jersey_set.away.primary_color,
                complete_jersey_set.away.secondary_color,
                complete_jersey_set.away.accent_color,
            ),
        )
        return ClubIdentityProfile(
            club_id=club_id,
            club_name=club_name,
            short_club_code=short_club_code,
            color_palette=color_palette,
            badge_profile=badge_profile,
            jersey_set=complete_jersey_set,
            match_identity=match_identity,
        )

    def _ensure_complete(self, profile: ClubIdentityProfile) -> ClubIdentityProfile:
        return self._build_identity_profile(
            club_id=profile.club_id,
            club_name=profile.club_name,
            short_club_code=profile.short_club_code,
            color_palette=profile.color_palette,
            badge_profile=profile.badge_profile,
            jersey_set=profile.jersey_set,
        )

    def _ensure_jersey_set(
        self,
        jersey_set: JerseySet,
        palette: ColorPaletteProfile,
        short_code: str,
    ) -> JerseySet:
        home = jersey_set.home or self._build_default_variant(JerseyType.HOME, short_code, palette)
        away = jersey_set.away or self._build_default_variant(JerseyType.AWAY, short_code, palette)
        third = jersey_set.third or self._build_default_variant(JerseyType.THIRD, short_code, palette)
        goalkeeper = jersey_set.goalkeeper or self._build_default_variant(JerseyType.GOALKEEPER, short_code, palette)
        return JerseySet(home=home, away=away, third=third, goalkeeper=goalkeeper)

    def _build_default_jersey_set(self, short_code: str, palette: ColorPaletteProfile) -> JerseySet:
        return JerseySet(
            home=self._build_default_variant(JerseyType.HOME, short_code, palette),
            away=self._build_default_variant(JerseyType.AWAY, short_code, palette),
            third=self._build_default_variant(JerseyType.THIRD, short_code, palette),
            goalkeeper=self._build_default_variant(JerseyType.GOALKEEPER, short_code, palette),
        )

    def _build_default_variant(
        self,
        jersey_type: JerseyType,
        short_code: str,
        palette: ColorPaletteProfile,
    ) -> JerseyVariant:
        if jersey_type == JerseyType.HOME:
            return JerseyVariant(
                jersey_type=jersey_type,
                primary_color=palette.primary_color,
                secondary_color=palette.secondary_color,
                accent_color=palette.accent_color,
                collar_style=CollarStyle.CREW,
                sleeve_style=SleeveStyle.SHORT,
                pattern_type=PatternType.SOLID,
                badge_placement=BadgePlacement.LEFT_CHEST,
                front_text=short_code,
                shorts_color=palette.shorts_color,
                socks_color=palette.socks_color,
                theme_tags=("core",),
            )
        if jersey_type == JerseyType.AWAY:
            return JerseyVariant(
                jersey_type=jersey_type,
                primary_color=palette.secondary_color,
                secondary_color=palette.primary_color,
                accent_color=palette.accent_color,
                collar_style=CollarStyle.V_NECK,
                sleeve_style=SleeveStyle.RAGLAN,
                pattern_type=PatternType.SASH,
                badge_placement=BadgePlacement.LEFT_CHEST,
                front_text=short_code,
                shorts_color=palette.secondary_color,
                socks_color=palette.primary_color,
                theme_tags=("road",),
            )
        if jersey_type == JerseyType.THIRD:
            return JerseyVariant(
                jersey_type=jersey_type,
                primary_color=palette.accent_color,
                secondary_color=palette.primary_color,
                accent_color=palette.secondary_color,
                collar_style=CollarStyle.WRAP,
                sleeve_style=SleeveStyle.CUFFED,
                pattern_type=PatternType.GRADIENT,
                badge_placement=BadgePlacement.CENTER_CHEST,
                front_text=f"{short_code} ALT",
                shorts_color=palette.primary_color,
                socks_color=palette.accent_color,
                theme_tags=("limited", "unlockable"),
            )
        return JerseyVariant(
            jersey_type=jersey_type,
            primary_color="#1F2937",
            secondary_color="#A7F3D0",
            accent_color="#F9FAFB",
            collar_style=CollarStyle.CREW,
            sleeve_style=SleeveStyle.LONG,
            pattern_type=PatternType.CHEVRON,
            badge_placement=BadgePlacement.LEFT_CHEST,
            front_text=f"{short_code} GK",
            shorts_color="#111827",
            socks_color="#A7F3D0",
            theme_tags=("keeper",),
        )

    def _merge_palette(
        self,
        current: ColorPaletteProfile,
        payload: object,
    ) -> ColorPaletteProfile:
        if not isinstance(payload, dict):
            return current
        return ColorPaletteProfile(
            palette_name=str(payload.get("palette_name", current.palette_name)),
            primary_color=_normalize_hex(str(payload.get("primary_color", current.primary_color))),
            secondary_color=_normalize_hex(str(payload.get("secondary_color", current.secondary_color))),
            accent_color=_normalize_hex(str(payload.get("accent_color", current.accent_color))),
            shorts_color=_normalize_hex(str(payload.get("shorts_color", current.shorts_color))),
            socks_color=_normalize_hex(str(payload.get("socks_color", current.socks_color))),
        )

    def _merge_badge(
        self,
        current: BadgeProfile,
        payload: object,
        palette: ColorPaletteProfile,
        club_name: str,
    ) -> BadgeProfile:
        if not isinstance(payload, dict):
            return replace(
                current,
                primary_color=palette.primary_color,
                secondary_color=palette.secondary_color,
                accent_color=palette.accent_color,
            )
        shape_value = payload.get("shape", current.shape)
        icon_value = payload.get("icon_family", current.icon_family)
        return BadgeProfile(
            shape=shape_value if isinstance(shape_value, BadgeShape) else BadgeShape(str(shape_value)),
            initials=str(payload.get("initials", current.initials or self._build_short_code(club_name))),
            icon_family=icon_value if isinstance(icon_value, IconFamily) else IconFamily(str(icon_value)),
            primary_color=_normalize_hex(str(payload.get("primary_color", palette.primary_color))),
            secondary_color=_normalize_hex(str(payload.get("secondary_color", palette.secondary_color))),
            accent_color=_normalize_hex(str(payload.get("accent_color", palette.accent_color))),
            badge_url=payload.get("badge_url", current.badge_url),
            trophy_star_count=int(payload.get("trophy_star_count", current.trophy_star_count)),
            commemorative_patch=payload.get("commemorative_patch", current.commemorative_patch),
        )

    def _merge_jersey_set(
        self,
        current: JerseySet,
        payload: object,
        palette: ColorPaletteProfile,
        short_code: str,
    ) -> JerseySet:
        if not isinstance(payload, dict):
            return current
        return JerseySet(
            home=self._merge_variant(current.home, payload.get("home"), JerseyType.HOME, short_code, palette),
            away=self._merge_variant(current.away, payload.get("away"), JerseyType.AWAY, short_code, palette),
            third=self._merge_variant(current.third, payload.get("third"), JerseyType.THIRD, short_code, palette),
            goalkeeper=self._merge_variant(
                current.goalkeeper,
                payload.get("goalkeeper"),
                JerseyType.GOALKEEPER,
                short_code,
                palette,
            ),
        )

    def _merge_variant(
        self,
        current: JerseyVariant | None,
        payload: object,
        jersey_type: JerseyType,
        short_code: str,
        palette: ColorPaletteProfile,
    ) -> JerseyVariant:
        base = current or self._build_default_variant(jersey_type, short_code, palette)
        if payload is None:
            return base
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid payload for {jersey_type.value} jersey update")
        collar_value = payload.get("collar_style", base.collar_style)
        sleeve_value = payload.get("sleeve_style", base.sleeve_style)
        pattern_value = payload.get("pattern_type", base.pattern_type)
        badge_placement = payload.get("badge_placement", base.badge_placement)
        theme_tags = payload.get("theme_tags", base.theme_tags)
        return JerseyVariant(
            jersey_type=jersey_type,
            primary_color=_normalize_hex(str(payload.get("primary_color", base.primary_color))),
            secondary_color=_normalize_hex(str(payload.get("secondary_color", base.secondary_color))),
            accent_color=_normalize_hex(str(payload.get("accent_color", base.accent_color))),
            collar_style=collar_value if isinstance(collar_value, CollarStyle) else CollarStyle(str(collar_value)),
            sleeve_style=sleeve_value if isinstance(sleeve_value, SleeveStyle) else SleeveStyle(str(sleeve_value)),
            pattern_type=pattern_value if isinstance(pattern_value, PatternType) else PatternType(str(pattern_value)),
            badge_placement=(
                badge_placement if isinstance(badge_placement, BadgePlacement) else BadgePlacement(str(badge_placement))
            ),
            front_text=str(payload.get("front_text", base.front_text)),
            shorts_color=_normalize_hex(str(payload.get("shorts_color", base.shorts_color))),
            socks_color=_normalize_hex(str(payload.get("socks_color", base.socks_color))),
            theme_tags=tuple(str(tag) for tag in theme_tags),
            commemorative_patch=payload.get("commemorative_patch", base.commemorative_patch),
        )

    def _build_badge_profile(
        self,
        club_id: str,
        club_name: str,
        palette: ColorPaletteProfile,
    ) -> BadgeProfile:
        digest = sha256(club_id.encode("utf-8")).digest()
        shape = DEFAULT_BADGE_SHAPES[digest[0] % len(DEFAULT_BADGE_SHAPES)]
        icon_family = DEFAULT_ICON_FAMILIES[digest[1] % len(DEFAULT_ICON_FAMILIES)]
        return BadgeProfile(
            shape=shape,
            initials=self._build_short_code(club_name),
            icon_family=icon_family,
            primary_color=palette.primary_color,
            secondary_color=palette.secondary_color,
            accent_color=palette.accent_color,
        )

    def _select_palette(self, club_id: str) -> ColorPaletteProfile:
        digest = sha256(club_id.encode("utf-8")).digest()
        return DEFAULT_PALETTES[digest[0] % len(DEFAULT_PALETTES)]

    def _validate_variant(self, variant: JerseyVariant) -> None:
        if _color_distance(variant.primary_color, variant.secondary_color) < 45:
            raise ValueError(
                f"{variant.jersey_type.value} jersey primary and secondary colors are too similar for readable trims"
            )
        if max(
            _contrast_ratio(variant.primary_color, variant.secondary_color),
            _contrast_ratio(variant.primary_color, variant.accent_color),
        ) < 1.25:
            raise ValueError(
                f"{variant.jersey_type.value} jersey colors are too similar for readable trims or wordmarks"
            )

    def _validate_home_away_distinction(self, home: JerseyVariant, away: JerseyVariant) -> None:
        if (
            home.primary_color == away.primary_color
            and home.secondary_color == away.secondary_color
            and home.pattern_type == away.pattern_type
        ):
            raise ValueError("Home and away jerseys cannot be identical")
        if _color_distance(home.primary_color, away.primary_color) < 60:
            raise ValueError("Home and away jerseys must remain visually distinct")

    def _build_short_code(self, club_name: str) -> str:
        words = [part for part in club_name.replace("-", " ").split() if part]
        if len(words) >= 2:
            return "".join(word[0] for word in words[:3]).upper()
        return club_name.replace(" ", "")[:3].upper()

    def _titleize_club_name(self, club_id: str) -> str:
        return " ".join(part.capitalize() for part in club_id.replace("_", "-").split("-") if part)
