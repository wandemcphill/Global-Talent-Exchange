from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.schemas.avatar import PlayerAvatarView


_FNV_OFFSET = 2166136261
_FNV_PRIME = 16777619

_EUROPE_CODES = frozenset(
    {
        "AL",
        "AM",
        "AT",
        "AZ",
        "BA",
        "BE",
        "BG",
        "BY",
        "CH",
        "CY",
        "CZ",
        "DE",
        "DK",
        "EE",
        "ES",
        "FI",
        "FR",
        "GB",
        "GE",
        "GR",
        "HR",
        "HU",
        "IE",
        "IS",
        "IT",
        "LT",
        "LU",
        "LV",
        "MD",
        "ME",
        "MK",
        "MT",
        "NL",
        "NO",
        "PL",
        "PT",
        "RO",
        "RS",
        "SE",
        "SI",
        "SK",
        "TR",
        "UA",
    }
)
_AFRICA_CODES = frozenset(
    {
        "AO",
        "BF",
        "BJ",
        "CD",
        "CG",
        "CI",
        "CM",
        "CV",
        "DZ",
        "EG",
        "ET",
        "GA",
        "GH",
        "GM",
        "GN",
        "KE",
        "LR",
        "LY",
        "MA",
        "ML",
        "MZ",
        "NA",
        "NE",
        "NG",
        "RW",
        "SD",
        "SL",
        "SN",
        "SS",
        "TG",
        "TN",
        "TZ",
        "UG",
        "ZA",
        "ZM",
        "ZW",
    }
)
_SOUTH_AMERICA_CODES = frozenset(
    {"AR", "BO", "BR", "CL", "CO", "EC", "GF", "GY", "PE", "PY", "SR", "UY", "VE"}
)
_NORTH_AMERICA_CODES = frozenset(
    {"CA", "CR", "CU", "DO", "GT", "HN", "HT", "JM", "MX", "NI", "PA", "SV", "TT", "US"}
)
_ASIA_PACIFIC_CODES = frozenset(
    {
        "AU",
        "BD",
        "CN",
        "HK",
        "ID",
        "IN",
        "JP",
        "KH",
        "KR",
        "LA",
        "LK",
        "MM",
        "MN",
        "MY",
        "NZ",
        "PH",
        "PK",
        "SG",
        "TH",
        "TW",
        "VN",
    }
)
_MIDDLE_EAST_CODES = frozenset(
    {"AE", "BH", "IL", "IQ", "IR", "JO", "KW", "LB", "OM", "PS", "QA", "SA", "SY", "YE"}
)

_REGION_SKIN_WEIGHTS = {
    "africa": [1, 2, 6, 18, 28, 34],
    "europe": [30, 28, 18, 9, 3, 1],
    "south_america": [7, 14, 22, 21, 12, 6],
    "north_america": [6, 11, 20, 20, 12, 7],
    "asia_pacific": [19, 24, 22, 10, 3, 1],
    "middle_east": [8, 17, 24, 20, 10, 5],
    "global": [8, 14, 19, 19, 14, 10],
}
_REGION_HAIR_COLOR_WEIGHTS = {
    "africa": [58, 28, 8, 1, 1, 0],
    "europe": [18, 30, 20, 18, 8, 6],
    "south_america": [32, 34, 18, 8, 4, 4],
    "north_america": [26, 28, 18, 14, 5, 9],
    "asia_pacific": [44, 32, 12, 4, 1, 7],
    "middle_east": [40, 34, 14, 5, 2, 5],
    "global": [30, 28, 18, 10, 4, 10],
}
_POSITION_FACE_WEIGHTS = {
    "goalkeeper": [1, 1, 4, 1, 2],
    "defender": [1, 2, 4, 1, 2],
    "midfielder": [3, 2, 2, 2, 1],
    "forward": [2, 1, 2, 3, 2],
    "utility": [2, 2, 2, 1, 1],
}
_POSITION_HAIR_WEIGHTS = {
    "goalkeeper": [18, 22, 16, 8, 10, 2, 18, 3, 3],
    "defender": [18, 22, 24, 7, 8, 2, 14, 2, 3],
    "midfielder": [12, 18, 14, 16, 14, 3, 10, 6, 7],
    "forward": [12, 15, 22, 14, 10, 4, 9, 6, 8],
    "utility": [14, 18, 18, 12, 11, 3, 12, 5, 7],
}
_ACCESSORY_TYPE_WEIGHTS = [0, 58, 24, 18]


@dataclass(frozen=True, slots=True)
class AvatarIdentityInput:
    player_id: str | None = None
    player_name: str | None = None
    position: str | None = None
    normalized_position: str | None = None
    nationality: str | None = None
    nationality_code: str | None = None
    birth_year: int | None = None
    age: int | None = None
    preferred_foot: str | None = None
    avatar_seed_token: str | None = None
    avatar_dna_seed: str | int | None = None


class AvatarService:
    avatar_version = 1
    version = "fm_v1"

    def build_avatar(self, identity: AvatarIdentityInput) -> PlayerAvatarView:
        seed_token = self._resolve_seed_token(identity)
        dna_seed = self._hash_token(seed_token)
        use_trait_bias = not self._has_canonical_seed(identity)
        region = self._region_for_identity(identity) if use_trait_bias else "global"
        position_group = (
            self._position_group(identity.normalized_position or identity.position)
            if use_trait_bias
            else "utility"
        )
        age = identity.age
        if use_trait_bias and age is None and identity.birth_year is not None:
            age = max(16, 2026 - identity.birth_year)
        if not use_trait_bias:
            age = None
        preferred_foot = identity.preferred_foot if use_trait_bias else None

        skin_tone = self._pick_weighted(
            self._hash_slot(seed_token, "skin"),
            _REGION_SKIN_WEIGHTS[region],
        )
        hair_style = self._pick_weighted(
            self._hash_slot(seed_token, "hair_style"),
            self._hair_style_weights(position_group=position_group, age=age),
        )
        hair_color = self._pick_weighted(
            self._hash_slot(seed_token, "hair_color"),
            _REGION_HAIR_COLOR_WEIGHTS[region],
        )
        face_shape = self._pick_weighted(
            self._hash_slot(seed_token, "face_shape"),
            self._face_shape_weights(position_group=position_group, age=age),
        )
        eyebrow_style = self._pick_weighted(
            self._hash_slot(seed_token, "eyebrows"),
            self._eyebrow_weights(position_group=position_group),
        )
        eye_type = self._pick_weighted(
            self._hash_slot(seed_token, "eyes"),
            self._eye_weights(position_group=position_group),
        )
        nose_type = self._pick_weighted(
            self._hash_slot(seed_token, "nose"),
            self._nose_weights(region=region),
        )
        mouth_type = self._pick_weighted(
            self._hash_slot(seed_token, "mouth"),
            self._mouth_weights(age=age),
        )
        beard_style = self._pick_weighted(
            self._hash_slot(seed_token, "beard"),
            self._beard_weights(age=age, position_group=position_group),
        )
        accessory_score = self._percent(seed_token, "accessory")
        accessory_threshold = self._accessory_threshold(position_group=position_group, age=age)
        accessory_type = 0
        if accessory_score < accessory_threshold:
            accessory_type = self._pick_weighted(
                self._hash_slot(seed_token, "accessory_type"),
                _ACCESSORY_TYPE_WEIGHTS,
            )
        if accessory_type == 0:
            accessory_score = 100

        return PlayerAvatarView(
            avatar_version=self.avatar_version,
            version=self.version,
            seed_token=seed_token,
            dna_seed=dna_seed,
            skin_tone=skin_tone,
            hair_style=hair_style,
            hair_color=hair_color,
            face_shape=face_shape,
            eyebrow_style=eyebrow_style,
            eye_type=eye_type,
            nose_type=nose_type,
            mouth_type=mouth_type,
            beard_style=beard_style,
            has_accessory=accessory_type != 0,
            accessory_type=accessory_type,
            jersey_style=self._pick_weighted(
                self._hash_slot(seed_token, "jersey"),
                self._jersey_weights(position_group=position_group),
            ),
            accent_tone=self._pick_weighted(
                self._hash_slot(seed_token, "accent"),
                self._accent_weights(position_group=position_group, preferred_foot=preferred_foot),
            ),
        )

    def build_from_player(
        self,
        player: Any,
        *,
        nationality_code: str | None = None,
        summary_payload: dict[str, Any] | None = None,
    ) -> PlayerAvatarView:
        birth_year = player.date_of_birth.year if getattr(player, "date_of_birth", None) is not None else None
        summary = summary_payload if isinstance(summary_payload, dict) else {}
        return self.build_avatar(
            AvatarIdentityInput(
                player_id=getattr(player, "id", None),
                player_name=getattr(player, "full_name", None),
                position=getattr(player, "position", None),
                normalized_position=getattr(player, "normalized_position", None),
                nationality=getattr(getattr(player, "country", None), "name", None),
                nationality_code=nationality_code
                or getattr(getattr(player, "country", None), "alpha2_code", None)
                or getattr(getattr(player, "country", None), "alpha3_code", None)
                or getattr(getattr(player, "country", None), "fifa_code", None),
                birth_year=birth_year,
                preferred_foot=getattr(player, "preferred_foot", None),
                avatar_seed_token=summary.get("avatar_seed_token") or getattr(player, "avatar_seed_token", None),
                avatar_dna_seed=summary.get("avatar_dna_seed") or getattr(player, "avatar_dna_seed", None),
            )
        )

    def build_from_payload(self, payload: AvatarIdentityInput) -> PlayerAvatarView:
        return self.build_avatar(payload)

    def _resolve_seed_token(self, identity: AvatarIdentityInput) -> str:
        explicit_token = self._clean_text(identity.avatar_seed_token)
        if explicit_token:
            return explicit_token
        explicit_seed = self._clean_text(identity.avatar_dna_seed)
        if explicit_seed:
            return explicit_seed
        player_id = self._clean_text(identity.player_id)
        if player_id:
            return player_id
        parts = [
            self._clean_text(identity.player_name) or "generic-player",
            self._clean_text(identity.nationality_code) or self._clean_text(identity.nationality),
            self._clean_text(identity.normalized_position or identity.position),
            str(identity.birth_year) if identity.birth_year is not None else "",
        ]
        return "|".join(parts)

    def _has_canonical_seed(self, identity: AvatarIdentityInput) -> bool:
        return bool(
            self._clean_text(identity.avatar_seed_token)
            or self._clean_text(identity.avatar_dna_seed)
            or self._clean_text(identity.player_id)
        )

    def _region_for_identity(self, identity: AvatarIdentityInput) -> str:
        code = self._normalize_code(identity.nationality_code)
        if code in _AFRICA_CODES:
            return "africa"
        if code in _EUROPE_CODES:
            return "europe"
        if code in _SOUTH_AMERICA_CODES:
            return "south_america"
        if code in _NORTH_AMERICA_CODES:
            return "north_america"
        if code in _ASIA_PACIFIC_CODES:
            return "asia_pacific"
        if code in _MIDDLE_EAST_CODES:
            return "middle_east"
        return "global"

    def _position_group(self, position: str | None) -> str:
        normalized = self._clean_text(position).upper()
        if normalized in {"GK", "GOALKEEPER"}:
            return "goalkeeper"
        if normalized in {"CB", "RB", "LB", "RWB", "LWB", "DEF", "DF"}:
            return "defender"
        if normalized in {"CM", "CDM", "CAM", "LM", "RM", "MID", "MF"}:
            return "midfielder"
        if normalized in {"ST", "CF", "LW", "RW", "SS", "FW", "ATT"}:
            return "forward"
        return "utility"

    def _hair_style_weights(self, *, position_group: str, age: int | None) -> list[int]:
        weights = list(_POSITION_HAIR_WEIGHTS[position_group])
        if age is not None and age < 21:
            weights[6] = max(weights[6] - 6, 2)
            weights[3] += 4
            weights[7] += 3
        if age is not None and age >= 31:
            weights[6] += 9
            weights[0] += 3
            weights[4] = max(weights[4] - 4, 2)
        return weights

    def _face_shape_weights(self, *, position_group: str, age: int | None) -> list[int]:
        weights = list(_POSITION_FACE_WEIGHTS[position_group])
        if age is not None and age < 21:
            weights[0] += 2
            weights[1] += 2
            weights[2] = max(weights[2] - 1, 1)
        if age is not None and age >= 30:
            weights[2] += 2
            weights[4] += 1
        return weights

    def _eyebrow_weights(self, *, position_group: str) -> list[int]:
        if position_group == "forward":
            return [2, 3, 4, 2]
        if position_group == "goalkeeper":
            return [2, 2, 4, 2]
        return [3, 4, 3, 2]

    def _eye_weights(self, *, position_group: str) -> list[int]:
        if position_group == "midfielder":
            return [3, 4, 3, 2]
        if position_group == "forward":
            return [2, 3, 4, 2]
        return [4, 3, 2, 2]

    def _nose_weights(self, *, region: str) -> list[int]:
        if region == "africa":
            return [2, 3, 4, 3]
        if region in {"europe", "asia_pacific"}:
            return [4, 4, 2, 1]
        return [3, 4, 3, 2]

    def _mouth_weights(self, *, age: int | None) -> list[int]:
        if age is not None and age < 21:
            return [4, 4, 2, 1]
        if age is not None and age >= 30:
            return [3, 2, 3, 3]
        return [3, 3, 3, 2]

    def _beard_weights(self, *, age: int | None, position_group: str) -> list[int]:
        if age is None:
            age = 24
        if age < 21:
            return [90, 8, 1, 1, 0, 0]
        if age < 27:
            return [60, 18, 8, 8, 4, 2]
        if age < 32:
            return [35, 18, 12, 18, 6, 11]
        weights = [28, 14, 12, 20, 8, 18]
        if position_group == "goalkeeper":
            weights[3] += 4
            weights[5] += 2
        return weights

    def _jersey_weights(self, *, position_group: str) -> list[int]:
        if position_group == "goalkeeper":
            return [4, 1, 1, 2]
        if position_group == "forward":
            return [3, 3, 1, 2]
        return [4, 2, 2, 1]

    def _accent_weights(self, *, position_group: str, preferred_foot: str | None) -> list[int]:
        weights = [3, 3, 2, 2, 2, 2]
        if position_group == "goalkeeper":
            weights[4] += 2
            weights[5] += 2
        if position_group == "forward":
            weights[0] += 2
            weights[3] += 1
        if self._clean_text(preferred_foot).startswith("left"):
            weights[2] += 2
        return weights

    def _accessory_threshold(self, *, position_group: str, age: int | None) -> int:
        threshold = 8
        if position_group == "goalkeeper":
            threshold = 16
        elif position_group == "forward":
            threshold = 11
        if age is not None and age < 21:
            threshold = max(threshold - 3, 4)
        return threshold

    def _percent(self, seed_token: str, slot: str) -> int:
        return self._hash_slot(seed_token, slot) % 100

    def _hash_slot(self, seed_token: str, slot: str) -> int:
        return self._hash_token(f"{self.version}|{seed_token}|{slot}")

    def _hash_token(self, value: str) -> int:
        hashed = _FNV_OFFSET
        for byte in value.encode("utf-8"):
            hashed ^= byte
            hashed = (hashed * _FNV_PRIME) & 0xFFFFFFFF
        return hashed

    def _pick_weighted(self, hashed: int, weights: list[int]) -> int:
        total = sum(max(weight, 0) for weight in weights)
        if total <= 0:
            return 0
        cursor = hashed % total
        for index, weight in enumerate(weights):
            if cursor < max(weight, 0):
                return index
            cursor -= max(weight, 0)
        return len(weights) - 1

    def _clean_text(self, value: object | None) -> str:
        if value is None:
            return ""
        return " ".join(str(value).strip().lower().split())

    def _normalize_code(self, value: str | None) -> str:
        cleaned = self._clean_text(value).upper()
        if len(cleaned) >= 2:
            return cleaned[:2]
        return cleaned
