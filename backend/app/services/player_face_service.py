from __future__ import annotations

import base64
import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.player_face import PlayerFace
from app.models.player_rivalry import PlayerRivalry
from app.models.player_story import PlayerStory
from app.models.regen import RegenLegacyRecord, RegenPersonalityProfile, RegenProfile
from app.schemas.avatar import PlayerAvatarRenderView, PlayerAvatarView, PlayerFaceView
from app.services.avatar_service import AvatarService

_REGION_PRESET_BY_CODE = {
    "NG": "west_african",
    "GH": "west_african",
    "CI": "west_african",
    "SN": "west_african",
    "JP": "east_asian",
    "KR": "east_asian",
    "CN": "east_asian",
    "PT": "southern_european",
    "ES": "southern_european",
    "IT": "southern_european",
    "DE": "central_european",
    "FR": "central_european",
    "BR": "south_american",
    "AR": "south_american",
    "US": "north_american",
}

_SKIN_LABELS = {
    "west_african": ["amber", "warm_brown", "rich_brown", "burnished_brown", "deep_cocoa", "ebony"],
    "east_asian": ["porcelain", "light_beige", "warm_beige", "golden_beige", "honey_beige", "amber"],
    "southern_european": ["ivory", "light_olive", "sun_kissed", "olive", "bronze", "deep_bronze"],
    "central_european": ["porcelain", "fair", "light_beige", "rose_beige", "sand", "olive"],
    "south_american": ["golden", "warm_beige", "olive", "copper", "burnished", "deep_copper"],
    "north_american": ["fair", "light_beige", "golden", "olive", "copper", "deep_brown"],
    "global": ["fair", "beige", "golden", "olive", "cocoa", "deep_brown"],
}
_SKIN_HEX = {
    "amber": "#d6a36d",
    "warm_brown": "#b97b52",
    "rich_brown": "#9b603f",
    "burnished_brown": "#7e4d33",
    "deep_cocoa": "#5c3927",
    "ebony": "#3d261d",
    "porcelain": "#f5dbc9",
    "light_beige": "#e8c7a8",
    "warm_beige": "#dcb48e",
    "golden_beige": "#d3a276",
    "honey_beige": "#c58f63",
    "ivory": "#efd8c8",
    "light_olive": "#d4b18b",
    "sun_kissed": "#c89468",
    "olive": "#b47c57",
    "bronze": "#9d6546",
    "deep_bronze": "#774b35",
    "fair": "#efcfbf",
    "rose_beige": "#d7b09a",
    "sand": "#c79b79",
    "golden": "#cb9a6a",
    "copper": "#a96a45",
    "burnished": "#905b3d",
    "deep_copper": "#6d452f",
    "beige": "#ddb796",
    "cocoa": "#87583d",
    "deep_brown": "#5a3a2b",
}
_HAIR_STYLE_LABELS = ["close_crop", "clean_buzz", "side_part", "curly_fade", "braids", "top_knot", "textured_wave", "locs", "shaved"]
_HAIR_STYLE_BY_AGE = {
    "veteran": {
        "curly_fade": "trimmed_curl",
        "braids": "neat_braids",
        "top_knot": "slick_back",
        "locs": "tied_locs",
    }
}
_HAIR_COLOR_LABELS = ["black", "dark_brown", "brown", "light_brown", "blonde", "silver"]
_HAIR_HEX = {
    "black": "#1d1a1a",
    "dark_brown": "#342521",
    "brown": "#5b3d2d",
    "light_brown": "#8a5b3d",
    "blonde": "#cba66a",
    "silver": "#a5abb2",
}
_FACE_SHAPE_LABELS = ["oval", "heart", "angular", "round", "diamond"]
_EYEBROW_LABELS = ["soft_arch", "sharp_arch", "straight", "bold"]
_EYE_LABELS = {
    "west_african": ["bright_almond", "wide_focus", "soft_round", "deep_set"],
    "east_asian": ["monolid", "soft_almond", "narrow_focus", "bright_round"],
    "global": ["almond", "wide_focus", "soft_round", "deep_set"],
}
_NOSE_LABELS = {
    "west_african": ["balanced_bridge", "rounded_bridge", "broad_bridge", "defined_bridge"],
    "east_asian": ["soft_bridge", "compact_bridge", "balanced_bridge", "defined_bridge"],
    "global": ["slim_bridge", "balanced_bridge", "rounded_bridge", "defined_bridge"],
}
_MOUTH_LABELS = {
    "west_african": ["soft_smile", "defined_full", "balanced_full", "composed_line"],
    "east_asian": ["composed_line", "soft_smile", "balanced_full", "gentle_curve"],
    "global": ["soft_smile", "balanced_full", "gentle_curve", "composed_line"],
}
_BEARD_LABELS = ["clean_shaven", "shadow", "chin_patch", "goatee", "short_beard", "full_beard"]
_ACCESSORY_LABELS = {
    0: None,
    1: "headband",
    2: "sport_goggles",
    3: "earring",
}


class PlayerFaceError(ValueError):
    pass


class PlayerFaceNotFoundError(PlayerFaceError):
    pass


class PlayerFaceService:
    def __init__(self, session: Session, *, avatar_service: AvatarService | None = None) -> None:
        self.session = session
        self.avatar_service = avatar_service or AvatarService()

    def get_avatar_render(self, player_id: str, *, render_format: str = "json") -> PlayerAvatarRenderView:
        player = self._require_player(player_id)
        legacy_avatar = self.avatar_service.build_from_player(
            player,
            nationality_code=self._country_code(player),
        )
        face_view = self._ensure_face(player, legacy_avatar=legacy_avatar)
        svg = self._build_svg(face_view, legacy_avatar)
        return PlayerAvatarRenderView(
            player_id=player.id,
            render_format=render_format,  # type: ignore[arg-type]
            face=face_view,
            legacy_avatar=legacy_avatar,
            layered_svg=svg if render_format in {"json", "svg"} else None,
            static_image_data_uri=self._svg_data_uri(svg) if render_format in {"json", "static"} else None,
            model_manifest=self._model_manifest(face_view, legacy_avatar) if render_format in {"json", "model"} else None,
        )

    def _ensure_face(self, player: Player, *, legacy_avatar: PlayerAvatarView) -> PlayerFaceView:
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player.id))
        legacy = self.session.scalar(select(RegenLegacyRecord).where(RegenLegacyRecord.player_id == player.id))
        story = self.session.scalar(select(PlayerStory).where(PlayerStory.player_id == player.id))
        personality = None
        if regen is not None:
            personality = self.session.scalar(
                select(RegenPersonalityProfile).where(RegenPersonalityProfile.regen_profile_id == regen.id)
            )
        rivalry = self.session.scalar(
            select(PlayerRivalry)
            .where(or_(PlayerRivalry.player_a_id == player.id, PlayerRivalry.player_b_id == player.id))
            .order_by(PlayerRivalry.intensity_score.desc(), PlayerRivalry.updated_at.desc())
        )
        age = self._player_age(player)
        age_stage = self._age_stage(age)
        region_preset = self._region_preset(player, regen=regen)
        rarity = self._rarity(regen=regen, legacy=legacy)
        avatar_seed = self._avatar_seed(player, regen=regen)
        documentary_hook = self._documentary_hook(story)
        rivalry_heat = round(float(rivalry.intensity_score), 2) if rivalry is not None else 0.0

        hairstyle = self._hairstyle_name(legacy_avatar.hair_style, age_stage=age_stage)
        skin_tone = self._palette_value(_SKIN_LABELS, region_preset, legacy_avatar.skin_tone)
        accessories = self._accessories(
            legacy_avatar=legacy_avatar,
            personality=personality,
            legacy=legacy,
            age_stage=age_stage,
        )
        features = {
            "face_shape": _FACE_SHAPE_LABELS[legacy_avatar.face_shape],
            "eyes": self._palette_value(_EYE_LABELS, region_preset, legacy_avatar.eye_type),
            "nose": self._palette_value(_NOSE_LABELS, region_preset, legacy_avatar.nose_type),
            "mouth": self._palette_value(_MOUTH_LABELS, region_preset, legacy_avatar.mouth_type),
            "eyebrows": _EYEBROW_LABELS[legacy_avatar.eyebrow_style],
            "beard_style": _BEARD_LABELS[legacy_avatar.beard_style],
            "hair_color": _HAIR_COLOR_LABELS[legacy_avatar.hair_color],
            "region_preset": region_preset,
            "dna_archetype": str((player.dna_profile or {}).get("archetype", "balanced")),
            "documentary_hook": documentary_hook,
            "rivalry_heat": rivalry_heat,
            "ageing": self._ageing_payload(age_stage),
        }
        visual_effects = ["subtle_glow", "animated_aura", "premium_frame"] if rarity == "generational" else []

        row = self.session.scalar(select(PlayerFace).where(PlayerFace.player_id == player.id))
        if row is None:
            row = PlayerFace(player_id=player.id)
            self.session.add(row)
        row.avatar_seed = avatar_seed
        row.facial_features = features
        row.hairstyle = hairstyle
        row.skin_tone = skin_tone
        row.accessories = accessories
        row.generated_at = datetime.now(timezone.utc)
        self.session.flush()

        return PlayerFaceView(
            player_id=player.id,
            avatar_seed=row.avatar_seed,
            facial_features=features,
            hairstyle=row.hairstyle,
            skin_tone=row.skin_tone,
            accessories=list(row.accessories or []),
            generated_at=row.generated_at,
            nationality=self._country_name(player, regen=regen),
            region_preset=region_preset,
            age_stage=age_stage,
            rarity=rarity,
            visual_effects=visual_effects,
        )

    def _build_svg(self, face: PlayerFaceView, legacy_avatar: PlayerAvatarView) -> str:
        face_shape = str(face.facial_features.get("face_shape", "oval"))
        skin_fill = _SKIN_HEX.get(str(face.skin_tone or "beige"), "#ddb796")
        hair_fill = _HAIR_HEX.get(str(face.facial_features.get("hair_color", "black")), "#1d1a1a")
        aura = face.rarity == "generational"
        accessories = set(face.accessories)
        frame = (
            '<rect x="8" y="8" width="184" height="184" rx="24" fill="none" stroke="#d4af37" stroke-width="4" />'
            if aura
            else '<rect x="12" y="12" width="176" height="176" rx="20" fill="none" stroke="#365a7c" stroke-width="2" />'
        )
        filter_block = (
            """
            <defs>
              <filter id="gtexAura">
                <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            """
            if aura
            else ""
        )
        head = {
            "oval": '<ellipse cx="100" cy="108" rx="48" ry="58" fill="{skin}" />',
            "heart": '<path d="M100 54c28 0 44 22 44 52 0 32-17 58-44 58S56 138 56 106c0-30 16-52 44-52Z" fill="{skin}" />',
            "angular": '<path d="M63 66c11-12 26-18 37-18s26 6 37 18c7 8 10 20 10 38 0 34-19 60-47 60s-47-26-47-60c0-18 3-30 10-38Z" fill="{skin}" />',
            "round": '<circle cx="100" cy="108" r="52" fill="{skin}" />',
            "diamond": '<path d="M100 48c22 0 42 18 42 48 0 38-22 68-42 68S58 134 58 96c0-30 20-48 42-48Z" fill="{skin}" />',
        }.get(face_shape, '<ellipse cx="100" cy="108" rx="48" ry="58" fill="{skin}" />').format(skin=skin_fill)
        hair = self._hair_svg(face.hairstyle or "close_crop", hair_fill)
        beard = self._beard_svg(str(face.facial_features.get("beard_style", "clean_shaven")), hair_fill)
        glow = '<ellipse cx="100" cy="104" rx="76" ry="82" fill="#f8d46d" opacity="0.18" filter="url(#gtexAura)" />' if aura else ""
        headband = '<rect x="52" y="80" width="96" height="10" rx="5" fill="#f7f7f7" opacity="0.9" />' if "headband" in accessories else ""
        captain_band = '<rect x="132" y="122" width="14" height="40" rx="4" fill="#f4d03f" opacity="0.95" />' if "captain_band" in accessories else ""
        goggles = (
            '<rect x="66" y="98" width="28" height="16" rx="7" fill="none" stroke="#dce7ef" stroke-width="3" />'
            '<rect x="106" y="98" width="28" height="16" rx="7" fill="none" stroke="#dce7ef" stroke-width="3" />'
            '<line x1="94" y1="106" x2="106" y2="106" stroke="#dce7ef" stroke-width="3" />'
            if "sport_goggles" in accessories
            else ""
        )
        earrings = '<circle cx="56" cy="126" r="3" fill="#d9d9d9" />' if "earring" in accessories else ""
        mouth_y = 132 + legacy_avatar.mouth_type
        eyebrow_y = 88 + legacy_avatar.eyebrow_style
        eye_y = 102 + legacy_avatar.eye_type
        return f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" role="img" aria-label="GTEX avatar for {face.player_id}">
  {filter_block}
  <rect width="200" height="200" rx="28" fill="#0f1f2f" />
  {glow}
  {frame}
  {hair}
  {head}
  {headband}
  <path d="M72 {eyebrow_y} Q84 {eyebrow_y - 5} 94 {eyebrow_y}" stroke="#241b19" stroke-width="4" fill="none" stroke-linecap="round" />
  <path d="M106 {eyebrow_y} Q116 {eyebrow_y - 5} 128 {eyebrow_y}" stroke="#241b19" stroke-width="4" fill="none" stroke-linecap="round" />
  <ellipse cx="82" cy="{eye_y}" rx="8" ry="5" fill="#ffffff" />
  <ellipse cx="118" cy="{eye_y}" rx="8" ry="5" fill="#ffffff" />
  <circle cx="82" cy="{eye_y}" r="3" fill="#231f20" />
  <circle cx="118" cy="{eye_y}" r="3" fill="#231f20" />
  <path d="M100 102 Q94 118 100 128 Q106 118 100 102Z" fill="#b57c58" opacity="0.5" />
  <path d="M84 {mouth_y} Q100 {mouth_y + 8} 116 {mouth_y}" stroke="#7b3d37" stroke-width="4" fill="none" stroke-linecap="round" />
  {beard}
  {goggles}
  {captain_band}
  {earrings}
</svg>
        """.strip()

    def _hair_svg(self, hairstyle: str, hair_fill: str) -> str:
        mapping = {
            "close_crop": f'<path d="M58 80c2-24 18-42 42-42s40 18 42 42H58Z" fill="{hair_fill}" />',
            "clean_buzz": f'<path d="M60 84c4-20 19-34 40-34 21 0 36 14 40 34H60Z" fill="{hair_fill}" />',
            "side_part": f'<path d="M58 84c4-28 24-42 46-42 22 0 37 10 38 42H58Z" fill="{hair_fill}" /><path d="M101 44 96 84" stroke="#5f4738" stroke-width="2" />',
            "curly_fade": f'<path d="M56 86c6-28 24-42 44-42s38 14 44 42H56Z" fill="{hair_fill}" /><circle cx="80" cy="54" r="8" fill="{hair_fill}" /><circle cx="100" cy="48" r="8" fill="{hair_fill}" /><circle cx="120" cy="55" r="8" fill="{hair_fill}" />',
            "braids": f'<path d="M60 84c4-24 22-40 40-40 18 0 36 16 40 40H60Z" fill="{hair_fill}" /><line x1="76" y1="52" x2="74" y2="86" stroke="#211814" stroke-width="3" /><line x1="100" y1="48" x2="100" y2="86" stroke="#211814" stroke-width="3" /><line x1="124" y1="52" x2="126" y2="86" stroke="#211814" stroke-width="3" />',
            "top_knot": f'<path d="M60 86c6-24 22-38 40-38 18 0 34 14 40 38H60Z" fill="{hair_fill}" /><circle cx="100" cy="40" r="12" fill="{hair_fill}" />',
            "textured_wave": f'<path d="M58 86c5-26 22-40 42-40s37 14 42 40H58Z" fill="{hair_fill}" /><path d="M72 58c8-8 18-9 28-4s18 5 28-2" stroke="#4a352d" stroke-width="3" fill="none" />',
            "locs": f'<path d="M60 82c5-24 22-38 40-38 18 0 35 14 40 38H60Z" fill="{hair_fill}" /><line x1="76" y1="54" x2="70" y2="92" stroke="#2c231f" stroke-width="4" /><line x1="100" y1="48" x2="100" y2="94" stroke="#2c231f" stroke-width="4" /><line x1="124" y1="54" x2="130" y2="92" stroke="#2c231f" stroke-width="4" />',
            "shaved": "",
            "trimmed_curl": f'<path d="M58 84c5-24 22-38 42-38s37 14 42 38H58Z" fill="{hair_fill}" />',
            "neat_braids": f'<path d="M60 84c4-24 22-40 40-40 18 0 36 16 40 40H60Z" fill="{hair_fill}" /><line x1="82" y1="52" x2="80" y2="84" stroke="#211814" stroke-width="3" /><line x1="100" y1="50" x2="100" y2="84" stroke="#211814" stroke-width="3" /><line x1="118" y1="52" x2="120" y2="84" stroke="#211814" stroke-width="3" />',
            "slick_back": f'<path d="M60 88c6-30 24-46 40-46 16 0 34 16 40 46H60Z" fill="{hair_fill}" />',
            "tied_locs": f'<path d="M60 84c5-24 22-38 40-38 18 0 35 14 40 38H60Z" fill="{hair_fill}" /><circle cx="100" cy="44" r="10" fill="{hair_fill}" />',
        }
        return mapping.get(hairstyle, mapping["close_crop"])

    def _beard_svg(self, beard_style: str, hair_fill: str) -> str:
        if beard_style == "clean_shaven":
            return ""
        if beard_style == "shadow":
            return '<path d="M78 138 Q100 148 122 138" stroke="#5b4338" stroke-width="6" opacity="0.22" fill="none" />'
        if beard_style == "chin_patch":
            return f'<ellipse cx="100" cy="145" rx="8" ry="6" fill="{hair_fill}" opacity="0.78" />'
        if beard_style == "goatee":
            return f'<path d="M92 138 Q100 154 108 138 Q108 154 100 160 Q92 154 92 138Z" fill="{hair_fill}" opacity="0.84" />'
        if beard_style == "short_beard":
            return f'<path d="M76 136 Q100 156 124 136 L118 154 Q100 168 82 154Z" fill="{hair_fill}" opacity="0.88" />'
        return f'<path d="M74 134 Q100 162 126 134 L120 162 Q100 176 80 162Z" fill="{hair_fill}" opacity="0.92" />'

    def _model_manifest(self, face: PlayerFaceView, legacy_avatar: PlayerAvatarView) -> dict[str, Any]:
        return {
            "format": "gtex_avatar_rig_v1",
            "status": "future_ready",
            "avatar_seed": face.avatar_seed,
            "layers": [
                "background",
                "frame",
                "aura" if face.rarity == "generational" else "base_frame",
                "hair",
                "head",
                "eyes",
                "nose",
                "mouth",
                "accessories",
            ],
            "traits": {
                "legacy_dna_seed": legacy_avatar.dna_seed,
                "age_stage": face.age_stage,
                "rarity": face.rarity,
            },
        }

    def _accessories(
        self,
        *,
        legacy_avatar: PlayerAvatarView,
        personality: RegenPersonalityProfile | None,
        legacy: RegenLegacyRecord | None,
        age_stage: str,
    ) -> list[str]:
        items: list[str] = []
        accessory = _ACCESSORY_LABELS.get(legacy_avatar.accessory_type)
        if accessory is not None:
            items.append(accessory)
        leadership = int(personality.leadership) if personality is not None else 0
        legacy_score = float(legacy.legacy_score) if legacy is not None else 0.0
        if leadership >= 68 or legacy_score >= 75:
            items.append("captain_band")
        if age_stage == "veteran" and "sport_goggles" not in items and legacy_avatar.accessory_type == 0:
            items.append("sport_goggles")
        return items

    def _avatar_seed(self, player: Player, *, regen: RegenProfile | None) -> str:
        seed_payload = json.dumps(
            {
                "player_id": player.id,
                "nationality": self._country_name(player, regen=regen),
                "dna_profile": player.dna_profile if isinstance(player.dna_profile, dict) else {},
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(seed_payload.encode("utf-8")).hexdigest()[:24]

    def _rarity(self, *, regen: RegenProfile | None, legacy: RegenLegacyRecord | None) -> str:
        potential_max = 0
        if regen is not None:
            potential_max = int((regen.potential_range_json or {}).get("maximum", regen.current_gsi))
        legacy_score = float(legacy.legacy_score) if legacy is not None else 0.0
        if (regen is not None and regen.is_special_lineage) or potential_max >= 94 or legacy_score >= 88:
            return "generational"
        if potential_max >= 90 or legacy_score >= 72:
            return "elite"
        return "standard"

    def _player_age(self, player: Player) -> int:
        today = date.today()
        if player.date_of_birth is None:
            return 20
        years = today.year - player.date_of_birth.year
        if (today.month, today.day) < (player.date_of_birth.month, player.date_of_birth.day):
            years -= 1
        return max(years, 0)

    @staticmethod
    def _age_stage(age: int) -> str:
        if age < 21:
            return "prospect"
        if age >= 31:
            return "veteran"
        return "prime"

    @staticmethod
    def _ageing_payload(age_stage: str) -> dict[str, Any]:
        if age_stage == "prospect":
            return {"jaw_definition": "soft", "eye_lines": "minimal", "facial_maturity": 0.25}
        if age_stage == "veteran":
            return {"jaw_definition": "set", "eye_lines": "subtle", "facial_maturity": 0.85}
        return {"jaw_definition": "balanced", "eye_lines": "light", "facial_maturity": 0.55}

    def _hairstyle_name(self, value: int, *, age_stage: str) -> str:
        style = _HAIR_STYLE_LABELS[value]
        return _HAIR_STYLE_BY_AGE.get(age_stage, {}).get(style, style)

    def _region_preset(self, player: Player, *, regen: RegenProfile | None) -> str:
        code = self._country_code(player, regen=regen)
        if code in _REGION_PRESET_BY_CODE:
            return _REGION_PRESET_BY_CODE[code]
        return "global"

    def _country_name(self, player: Player, *, regen: RegenProfile | None = None) -> str:
        if getattr(getattr(player, "country", None), "name", None):
            return str(player.country.name)
        if regen is not None and regen.birth_country_code:
            return str(regen.birth_country_code)
        return "global"

    def _country_code(self, player: Player, *, regen: RegenProfile | None = None) -> str | None:
        country = getattr(player, "country", None)
        for attr in ("alpha2_code", "alpha3_code", "fifa_code"):
            value = getattr(country, attr, None)
            if value:
                return str(value)[:2].upper()
        if regen is not None and regen.birth_country_code:
            return str(regen.birth_country_code)[:2].upper()
        return None

    @staticmethod
    def _documentary_hook(story: PlayerStory | None) -> str | None:
        if story is None:
            return None
        chapters = list((story.chapters or {}).get("chapters", []))
        if not chapters:
            return None
        summary = str(chapters[0].get("summary") or "").strip()
        return summary[:140] if summary else None

    @staticmethod
    def _palette_value(mapping: dict[str, list[str]], region_preset: str, index: int) -> str:
        values = mapping.get(region_preset) or mapping["global"]
        return values[index % len(values)]

    @staticmethod
    def _svg_data_uri(svg: str) -> str:
        encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"

    def _require_player(self, player_id: str) -> Player:
        player = self.session.get(Player, player_id)
        if player is None:
            raise PlayerFaceNotFoundError(f"player {player_id} was not found")
        return player


__all__ = ["PlayerFaceError", "PlayerFaceNotFoundError", "PlayerFaceService"]
