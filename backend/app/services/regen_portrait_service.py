from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import base64
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player, PlayerImageMetadata
from app.models.regen import RegenProfile, RegenVisualProfile
from app.models.regen_ecosystem import NationalRegenSeed

FACE_RECIPE_VERSION = "gtex_regen_portrait_assignment_v4"
PORTRAIT_SIZE = 256
PORTRAIT_ROLE = "portrait"
NEWGEN_FACE_BANK_PROVIDER = "gtex_regen_newgen_face_bank"
NEWGEN_FACE_BANK_COLLECTION = "script_skin_tone_hair_colour"
FACE_BANK_SUBDIR = "regen_newgen_faces"
FACE_BANK_MANIFEST = f"{FACE_BANK_SUBDIR}/manifest.json"
OVERRIDE_PROVIDER = "gtex_portrait_override"
GENERATED_MEDIA_ROUTE = "/generated-media"
GENERATED_MEDIA_DIR = "backend/generated_media"


class RegenPortraitError(ValueError):
    pass


class RegenPortraitNotFoundError(RegenPortraitError):
    pass


@dataclass(frozen=True, slots=True)
class RegenPortraitResult:
    player_id: str
    face_seed: str | None
    face_recipe: dict[str, Any] | None
    portrait_url: str | None
    status: str
    storage_key: str | None = None

    def as_payload(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "face_seed": self.face_seed,
            "face_recipe": self.face_recipe,
            "portrait_url": self.portrait_url,
            "status": self.status,
            "storage_key": self.storage_key,
        }


class RegenPortraitService:
    def __init__(self, session: Session):
        self.session = session

    def ensure_player_portrait(
        self,
        player: Player,
        *,
        regen: RegenProfile | None = None,
        visual_profile: RegenVisualProfile | None = None,
        force: bool = False,
    ) -> RegenPortraitResult:
        if bool(player.is_real_player):
            existing = self._approved_image_url(player)
            return RegenPortraitResult(
                player_id=player.id,
                face_seed=None,
                face_recipe=None,
                portrait_url=existing,
                status="real_player_image" if existing else "real_player_image_missing",
                storage_key=None,
            )

        regen = regen or self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player.id))
        if regen is None:
            raise RegenPortraitNotFoundError("regen_profile_not_found")

        dna = dict(player.dna_profile or {}) if isinstance(player.dna_profile, dict) else {}
        if dna.get("portraitStatus") == "banned" and not force:
            return RegenPortraitResult(
                player_id=player.id,
                face_seed=str(dna.get("faceSeed") or "") or None,
                face_recipe=dna.get("faceRecipe") if isinstance(dna.get("faceRecipe"), dict) else None,
                portrait_url=None,
                status="banned",
                storage_key=None,
            )

        existing_recipe = dna.get("faceRecipe") if isinstance(dna.get("faceRecipe"), dict) else None
        existing_url = self._first_string(dna, "portraitUrl", "portrait_url", "image_url")
        existing_seed = self._first_string(dna, "faceSeed", "face_seed")
        existing_status = str(dna.get("portraitStatus") or "ready")
        visual_profile = visual_profile or self.session.scalar(
            select(RegenVisualProfile).where(RegenVisualProfile.regen_profile_id == regen.id)
        )
        seed = existing_seed or (visual_profile.portrait_seed if visual_profile is not None else None)
        seed = seed or self._deterministic_player_seed(player, regen)
        recipe = self._face_recipe(seed=seed, player=player, regen=regen)
        if (
            existing_recipe
            and existing_url
            and existing_seed
            and not force
            and self._existing_portrait_is_current_face_bank(
                existing_url=existing_url,
                existing_recipe=existing_recipe,
                expected_recipe=recipe,
                metadata=dna,
            )
        ):
            return RegenPortraitResult(
                player_id=player.id,
                face_seed=existing_seed,
                face_recipe=existing_recipe,
                portrait_url=existing_url,
                status=existing_status,
                storage_key=self._storage_key_from_url(existing_url),
            )

        bank_asset = self._select_regen_face_bank_asset(seed=seed, recipe=recipe)
        if bank_asset is None:
            self._deactivate_existing_portrait_image(player.id)
            player.dna_profile = {
                **dna,
                "faceSeed": seed,
                "faceRecipe": recipe,
                "portraitUrl": None,
                "portraitStatus": "portrait_asset_missing",
                "portraitRecipeVersion": FACE_RECIPE_VERSION,
                "portraitStorageKey": None,
                "portraitSourceProvider": NEWGEN_FACE_BANK_PROVIDER,
                "portraitSourceCollection": NEWGEN_FACE_BANK_COLLECTION,
            }
            self.session.flush()
            return RegenPortraitResult(
                player_id=player.id,
                face_seed=seed,
                face_recipe=recipe,
                portrait_url=None,
                status="portrait_asset_missing",
                storage_key=None,
            )

        storage_key = str(bank_asset["storage_key"])
        portrait_url = self._generated_media_url(storage_key)
        checksum = str(bank_asset.get("sha256") or "")
        file_size_bytes = self._optional_int(bank_asset.get("bytes"))
        mime_type = self._mime_type_for_storage_key(storage_key)
        width = self._optional_int(bank_asset.get("width")) or PORTRAIT_SIZE
        height = self._optional_int(bank_asset.get("height")) or PORTRAIT_SIZE
        source_provider = self._asset_source_provider(bank_asset)
        provider_external_id = f"{source_provider}:{storage_key}"
        portrait_status = self._asset_status(bank_asset)

        image = self._portrait_image_row(player.id)
        if image is None:
            image = PlayerImageMetadata(
                source_provider=source_provider,
                provider_external_id=provider_external_id,
                player_id=player.id,
                image_role=PORTRAIT_ROLE,
            )
            self.session.add(image)
        image.source_provider = source_provider
        image.provider_external_id = provider_external_id
        image.source_url = portrait_url
        image.storage_key = storage_key
        image.width = width
        image.height = height
        image.mime_type = mime_type
        image.file_size_bytes = file_size_bytes
        image.checksum_sha256 = checksum
        image.moderation_status = "approved"
        image.rights_cleared = True
        image.is_primary = True
        image.last_processed_at = datetime.now(UTC)

        player.dna_profile = {
            **dna,
            "faceSeed": seed,
            "faceRecipe": recipe,
            "portraitUrl": portrait_url,
            "portraitStatus": portrait_status,
            "portraitGeneratedAt": datetime.now(UTC).isoformat(),
            "portraitRecipeVersion": FACE_RECIPE_VERSION,
            "portraitSourceProvider": source_provider,
            "portraitSourceCollection": str(bank_asset.get("collection") or ""),
            "portraitStorageKey": storage_key,
            "portraitEthnicity": str(bank_asset.get("ethnicity") or ""),
        }
        self._upsert_visual_profile(
            regen=regen,
            visual_profile=visual_profile,
            seed=seed,
            recipe=recipe,
            portrait_url=portrait_url,
            status=portrait_status,
        )
        self.session.flush()
        return RegenPortraitResult(
            player_id=player.id,
            face_seed=seed,
            face_recipe=recipe,
            portrait_url=portrait_url,
            status=portrait_status,
            storage_key=storage_key,
        )

    def ensure_national_seed_portrait(self, seed: NationalRegenSeed, *, force: bool = False) -> dict[str, Any]:
        metadata = dict(seed.metadata_json or {})
        if metadata.get("portraitStatus") == "banned" and not force:
            return metadata
        existing_url = self._first_string(metadata, "portraitUrl", "portrait_url", "image_url")
        existing_recipe = metadata.get("faceRecipe") if isinstance(metadata.get("faceRecipe"), dict) else None
        portrait_country_code = (
            self._first_string(
                metadata, "portraitCountryCode", "portrait_country_code", "naming_country_code", "nationality"
            )
            or seed.country_code
        )
        face_seed = self._first_string(metadata, "faceSeed", "face_seed")
        face_seed = face_seed or self._deterministic_seed(
            "national-seed",
            seed.seed_key,
            seed.display_name,
            seed.country_code,
            portrait_country_code,
            seed.primary_position,
        )
        recipe = self._face_recipe_from_context(
            seed=face_seed,
            age=seed.age,
            country_code=portrait_country_code,
            position=seed.primary_position,
            rating=seed.current_rating,
        )
        if (
            existing_url
            and existing_recipe
            and face_seed
            and not force
            and self._existing_portrait_is_current_face_bank(
                existing_url=existing_url,
                existing_recipe=existing_recipe,
                expected_recipe=recipe,
                metadata=metadata,
            )
        ):
            return metadata
        bank_asset = self._select_regen_face_bank_asset(seed=face_seed, recipe=recipe)
        if bank_asset is None:
            seed.metadata_json = {
                **metadata,
                "faceSeed": face_seed,
                "faceRecipe": recipe,
                "portraitUrl": None,
                "portraitStatus": "portrait_asset_missing",
                "portraitRecipeVersion": FACE_RECIPE_VERSION,
                "portraitStorageKey": None,
                "portraitCountryCode": portrait_country_code,
                "portraitSourceProvider": NEWGEN_FACE_BANK_PROVIDER,
                "portraitSourceCollection": NEWGEN_FACE_BANK_COLLECTION,
            }
            self.session.flush()
            return dict(seed.metadata_json or {})

        storage_key = str(bank_asset["storage_key"])
        portrait_url = self._generated_media_url(storage_key)
        portrait_status = self._asset_status(bank_asset)
        source_provider = self._asset_source_provider(bank_asset)
        seed.metadata_json = {
            **metadata,
            "faceSeed": face_seed,
            "faceRecipe": recipe,
            "portraitUrl": portrait_url,
            "portraitStatus": portrait_status,
            "portraitRecipeVersion": FACE_RECIPE_VERSION,
            "portraitStorageKey": storage_key,
            "portraitCountryCode": portrait_country_code,
            "portraitSourceProvider": source_provider,
            "portraitSourceCollection": str(bank_asset.get("collection") or ""),
            "portraitEthnicity": str(bank_asset.get("ethnicity") or ""),
        }
        self.session.flush()
        return dict(seed.metadata_json or {})

    def regenerate_player_portrait(self, player_id: str) -> RegenPortraitResult:
        player = self._require_player(player_id)
        return self.ensure_player_portrait(player, force=True)

    def override_player_portrait(
        self,
        player_id: str,
        *,
        portrait_url: str | None = None,
        image_data_uri: str | None = None,
        actor_user_id: str | None = None,
    ) -> RegenPortraitResult:
        player = self._require_player(player_id)
        if image_data_uri and image_data_uri.strip():
            portrait_url, storage_key, mime_type, file_size, checksum = self._save_data_uri_override(
                player.id, image_data_uri
            )
        else:
            portrait_url = (portrait_url or "").strip()
            if not portrait_url:
                raise RegenPortraitError("portrait_url_required")
            storage_key = self._storage_key_from_url(portrait_url)
            mime_type = "image/png"
            file_size = None
            checksum = None

        image = self._portrait_image_row(player.id)
        if image is None:
            image = PlayerImageMetadata(
                source_provider=OVERRIDE_PROVIDER,
                provider_external_id=f"{OVERRIDE_PROVIDER}:{player.id}",
                player_id=player.id,
                image_role=PORTRAIT_ROLE,
            )
            self.session.add(image)
        image.source_provider = OVERRIDE_PROVIDER
        image.provider_external_id = f"{OVERRIDE_PROVIDER}:{player.id}"
        image.source_url = portrait_url
        image.storage_key = storage_key
        image.width = PORTRAIT_SIZE if image_data_uri else image.width
        image.height = PORTRAIT_SIZE if image_data_uri else image.height
        image.mime_type = mime_type
        image.file_size_bytes = file_size
        image.checksum_sha256 = checksum
        image.moderation_status = "approved"
        image.rights_cleared = True
        image.is_primary = True
        image.last_processed_at = datetime.now(UTC)

        dna = dict(player.dna_profile or {}) if isinstance(player.dna_profile, dict) else {}
        player.dna_profile = {
            **dna,
            "portraitUrl": portrait_url,
            "portraitStatus": "override",
            "portraitOverrideBy": actor_user_id,
            "portraitOverrideAt": datetime.now(UTC).isoformat(),
        }
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player.id))
        visual_profile = (
            self.session.scalar(select(RegenVisualProfile).where(RegenVisualProfile.regen_profile_id == regen.id))
            if regen is not None
            else None
        )
        if regen is not None and visual_profile is not None:
            metadata = dict(visual_profile.metadata_json or {})
            visual_profile.metadata_json = {
                **metadata,
                "portraitUrl": portrait_url,
                "portraitStatus": "override",
                "portraitOverrideBy": actor_user_id,
                "portraitOverrideAt": datetime.now(UTC).isoformat(),
            }
        self.session.flush()
        return RegenPortraitResult(
            player_id=player.id,
            face_seed=str(player.dna_profile.get("faceSeed") or "") or None,
            face_recipe=(
                player.dna_profile.get("faceRecipe") if isinstance(player.dna_profile.get("faceRecipe"), dict) else None
            ),
            portrait_url=portrait_url,
            status="override",
            storage_key=storage_key,
        )

    def ban_player_portrait(
        self,
        player_id: str,
        *,
        reason: str | None = None,
        actor_user_id: str | None = None,
    ) -> RegenPortraitResult:
        player = self._require_player(player_id)
        image = self._portrait_image_row(player.id)
        banned_url = (
            image.source_url if image is not None else self._first_string(player.dna_profile or {}, "portraitUrl")
        )
        if image is not None:
            image.moderation_status = "rejected"
            image.is_primary = False
            image.last_processed_at = datetime.now(UTC)
        dna = dict(player.dna_profile or {}) if isinstance(player.dna_profile, dict) else {}
        player.dna_profile = {
            **dna,
            "portraitUrl": None,
            "portraitStatus": "banned",
            "bannedPortraitUrl": banned_url,
            "portraitBanReason": reason,
            "portraitBannedBy": actor_user_id,
            "portraitBannedAt": datetime.now(UTC).isoformat(),
        }
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player.id))
        if regen is not None:
            visual_profile = self.session.scalar(
                select(RegenVisualProfile).where(RegenVisualProfile.regen_profile_id == regen.id)
            )
            if visual_profile is not None:
                metadata = dict(visual_profile.metadata_json or {})
                visual_profile.metadata_json = {
                    **metadata,
                    "portraitUrl": None,
                    "portraitStatus": "banned",
                    "bannedPortraitUrl": banned_url,
                    "portraitBanReason": reason,
                    "portraitBannedBy": actor_user_id,
                    "portraitBannedAt": datetime.now(UTC).isoformat(),
                }
        self.session.flush()
        return RegenPortraitResult(
            player_id=player.id,
            face_seed=str(player.dna_profile.get("faceSeed") or "") or None,
            face_recipe=(
                player.dna_profile.get("faceRecipe") if isinstance(player.dna_profile.get("faceRecipe"), dict) else None
            ),
            portrait_url=None,
            status="banned",
            storage_key=None,
        )

    def _upsert_visual_profile(
        self,
        *,
        regen: RegenProfile,
        visual_profile: RegenVisualProfile | None,
        seed: str,
        recipe: dict[str, Any],
        portrait_url: str,
        status: str,
    ) -> RegenVisualProfile:
        if visual_profile is None:
            visual_profile = RegenVisualProfile(
                regen_profile_id=regen.id,
                portrait_seed=seed,
                skin_tone=str(recipe.get("skinToneId") or ""),
                hair_profile=str(recipe.get("hairStyleId") or ""),
                accessory_profile_json={},
                kit_style=str(recipe.get("shirtStyleId") or ""),
                metadata_json={},
            )
            self.session.add(visual_profile)
        visual_profile.portrait_seed = seed
        visual_profile.skin_tone = str(recipe.get("skinToneId") or "")
        visual_profile.hair_profile = str(recipe.get("hairStyleId") or "")
        visual_profile.kit_style = str(recipe.get("shirtStyleId") or "")
        metadata = dict(visual_profile.metadata_json or {})
        visual_profile.metadata_json = {
            **metadata,
            "faceRecipe": recipe,
            "portraitUrl": portrait_url,
            "portraitStatus": status,
            "portraitRecipeVersion": FACE_RECIPE_VERSION,
            "updatedAt": datetime.now(UTC).isoformat(),
        }
        regen_metadata = dict(regen.metadata_json or {})
        visual_metadata = (
            dict(regen_metadata.get("visual_profile")) if isinstance(regen_metadata.get("visual_profile"), dict) else {}
        )
        visual_metadata.update(
            {
                "portrait_seed": seed,
                "face_seed": seed,
                "face_recipe": recipe,
                "portrait_url": portrait_url,
                "image_url": portrait_url,
                "portrait_status": status,
                "recipe_version": FACE_RECIPE_VERSION,
            }
        )
        regen.metadata_json = {
            **regen_metadata,
            "visual_profile": visual_metadata,
            "faceSeed": seed,
            "faceRecipe": recipe,
            "portraitUrl": portrait_url,
            "image_url": portrait_url,
        }
        return visual_profile

    def _face_recipe(self, *, seed: str, player: Player, regen: RegenProfile) -> dict[str, Any]:
        age = self._age_from_birthdate(player.date_of_birth)
        country_code = regen.birth_country_code or (player.country.alpha2_code if player.country is not None else None)
        return self._face_recipe_from_context(
            seed=seed,
            age=age,
            country_code=country_code,
            position=player.normalized_position or player.position,
            rating=regen.current_gsi,
        )

    def _face_recipe_from_context(
        self,
        *,
        seed: str,
        age: int | None,
        country_code: str | None,
        position: str | None,
        rating: int | None,
    ) -> dict[str, Any]:
        region = self._nationality_region(country_code)
        resolved_rating = max(40, min(99, int(rating or 60)))
        resolved_position = str(position or "CM").upper()
        resolved_country = str(country_code or "GTX").upper()
        ethnicity_groups = self._portrait_ethnicity_groups(resolved_country)
        rating_bucket = max(0, min(9, int(resolved_rating / 10)))
        potential = min(99, resolved_rating + 10 + self._index_for(seed, "potential", 10))
        stats = self._stats_for_position(seed=seed, position=resolved_position, rating=resolved_rating)
        jersey_primary, jersey_trim = self._jersey_colors(resolved_country, resolved_position)
        return {
            "seed": seed,
            "skinToneId": self._choice_id(seed, "skin", "skin", 8, salt=region),
            "faceShapeId": self._choice_id(seed, "face", "face", 6),
            "eyeShapeId": self._choice_id(seed, "eye_shape", "eye_shape", 6),
            "eyeColorId": self._choice_id(seed, "eye", "eye", 6, salt=region),
            "browId": self._choice_id(seed, "brow", "brow", 6),
            "noseId": self._choice_id(seed, "nose", "nose", 6),
            "mouthId": self._choice_id(seed, "mouth", "mouth", 6),
            "hairStyleId": self._choice_id(seed, "hair_style", "hair_style", 10, salt=str(age or "youth")),
            "hairColorId": self._choice_id(seed, "hair", "hair", 8, salt=region),
            "facialHairId": self._choice_id(seed, "facial", "facial", 6, salt=str(age or 17)),
            "ageBand": self._age_band(age),
            "nationalityRegion": region,
            "portraitEthnicity": ethnicity_groups[0],
            "portraitEthnicityGroups": list(ethnicity_groups),
            "shirtStyleId": self._choice_id(seed, "shirt_style", "shirt_style", 6, salt=resolved_position),
            "shirtColorId": self._choice_id(seed, "shirt", "shirt", 8, salt=resolved_position),
            "backgroundStyleId": self._choice_id(seed, "bg", "bg", 6, salt=str(rating_bucket)),
            "jerseyPrimaryHex": jersey_primary,
            "jerseyTrimHex": jersey_trim,
            "countryCode": resolved_country,
            "position": resolved_position,
            "rating": resolved_rating,
            "potential": potential,
            "statPac": stats["PAC"],
            "statSho": stats["SHO"],
            "statPas": stats["PAS"],
            "statDri": stats["DRI"],
            "statDef": stats["DEF"],
            "statPhy": stats["PHY"],
        }

    @staticmethod
    def _index_for(seed: str, key: str, count: int) -> int:
        digest = hashlib.sha256(f"{seed}:{key}".encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % count

    @classmethod
    def _stats_for_position(cls, *, seed: str, position: str, rating: int) -> dict[str, int]:
        normalized = position.upper()
        profiles = {
            "GK": {"PAC": -18, "SHO": -28, "PAS": -8, "DRI": -15, "DEF": 7, "PHY": 8},
            "CB": {"PAC": -4, "SHO": -16, "PAS": -4, "DRI": -8, "DEF": 10, "PHY": 8},
            "RB": {"PAC": 8, "SHO": -12, "PAS": 0, "DRI": 2, "DEF": 5, "PHY": 2},
            "LB": {"PAC": 8, "SHO": -12, "PAS": 0, "DRI": 2, "DEF": 5, "PHY": 2},
            "DM": {"PAC": -1, "SHO": -8, "PAS": 6, "DRI": 0, "DEF": 7, "PHY": 6},
            "CM": {"PAC": 0, "SHO": -2, "PAS": 8, "DRI": 5, "DEF": 0, "PHY": 0},
            "AM": {"PAC": 4, "SHO": 5, "PAS": 8, "DRI": 9, "DEF": -18, "PHY": -3},
            "RW": {"PAC": 10, "SHO": 4, "PAS": 3, "DRI": 10, "DEF": -22, "PHY": -6},
            "LW": {"PAC": 10, "SHO": 4, "PAS": 3, "DRI": 10, "DEF": -22, "PHY": -6},
            "ST": {"PAC": 5, "SHO": 10, "PAS": -5, "DRI": 4, "DEF": -24, "PHY": 5},
        }
        base = profiles.get(normalized, profiles["CM"])
        return {
            key: max(25, min(99, rating + offset + cls._index_for(seed, f"stat:{key}", 9) - 4))
            for key, offset in base.items()
        }

    @classmethod
    def _jersey_colors(cls, country_code: str, position: str) -> tuple[str, str]:
        country = country_code.upper()
        country_palette = {
            "NG": ("#158a4b", "#f4f6ef"),
            "NGA": ("#158a4b", "#f4f6ef"),
            "GH": ("#f2c84b", "#13964a"),
            "BRA": ("#f1d33b", "#1b9a4a"),
            "BR": ("#f1d33b", "#1b9a4a"),
            "ENG": ("#f5f6f2", "#d5172e"),
            "GB": ("#f5f6f2", "#d5172e"),
            "FR": ("#1e4fa3", "#f5f6f2"),
            "FRA": ("#1e4fa3", "#f5f6f2"),
            "DE": ("#f3f1e8", "#1d1d1d"),
            "GER": ("#f3f1e8", "#1d1d1d"),
            "AR": ("#75c9ee", "#f5f6f2"),
            "ARG": ("#75c9ee", "#f5f6f2"),
            "IT": ("#2452a4", "#f5f6f2"),
            "ITA": ("#2452a4", "#f5f6f2"),
            "ES": ("#c82127", "#f4c542"),
            "ESP": ("#c82127", "#f4c542"),
            "KR": ("#e84352", "#f5f6f2"),
            "KOR": ("#e84352", "#f5f6f2"),
        }
        if country in country_palette:
            return country_palette[country]
        palette = (
            ("#be202e", "#f4f6ef"),
            ("#1553a8", "#f4f6ef"),
            ("#148a4b", "#f4f6ef"),
            ("#262a32", "#d9ab42"),
            ("#753696", "#f4f6ef"),
            ("#169daa", "#081015"),
        )
        return palette[cls._index_for(f"{country}:{position}", "jersey", len(palette))]

    def _deterministic_player_seed(self, player: Player, regen: RegenProfile) -> str:
        return self._deterministic_seed(
            "regen-player",
            player.id,
            regen.regen_id,
            player.full_name,
            regen.birth_country_code,
            regen.primary_position,
        )

    @staticmethod
    def _deterministic_seed(*parts: object) -> str:
        raw = ":".join(str(part or "").strip() for part in parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _choice_id(seed: str, key: str, prefix: str, count: int, *, salt: str = "") -> str:
        digest = hashlib.sha256(f"{seed}:{key}:{salt}".encode("utf-8")).hexdigest()
        return f"{prefix}_{int(digest[:8], 16) % count:02d}"

    @staticmethod
    def _age_band(age: int | None) -> str:
        if age is None or age <= 17:
            return "u18"
        if age <= 20:
            return "u21"
        if age <= 24:
            return "young_senior"
        return "senior"

    @staticmethod
    def _age_from_birthdate(value: date | None) -> int | None:
        if value is None:
            return None
        today = date.today()
        return today.year - value.year - ((today.month, today.day) < (value.month, value.day))

    @staticmethod
    def _nationality_region(country_code: str | None) -> str:
        code = (country_code or "").strip().upper()
        africa = {
            "AGO",
            "AO",
            "BEN",
            "BJ",
            "BFA",
            "BF",
            "BDI",
            "BI",
            "CAF",
            "CF",
            "COD",
            "CD",
            "COG",
            "CG",
            "CM",
            "CMR",
            "CPV",
            "CV",
            "CIV",
            "CI",
            "EG",
            "EGY",
            "GAB",
            "GA",
            "GHA",
            "GH",
            "GIN",
            "GN",
            "GMB",
            "GM",
            "GNB",
            "GW",
            "GNQ",
            "GQ",
            "KEN",
            "KE",
            "LBR",
            "LR",
            "MAR",
            "MA",
            "MDG",
            "MG",
            "ML",
            "MLI",
            "MOZ",
            "MZ",
            "MRT",
            "MR",
            "MUS",
            "MU",
            "NER",
            "NE",
            "NG",
            "NGA",
            "RWA",
            "RW",
            "SEN",
            "SN",
            "SLE",
            "SL",
            "STP",
            "ST",
            "TCD",
            "TD",
            "TGO",
            "TG",
            "TZA",
            "TZ",
            "TN",
            "TUN",
            "ZA",
            "ZAF",
            "ZMB",
            "ZM",
            "ZWE",
            "ZW",
        }
        europe = {
            "AT",
            "AUT",
            "BE",
            "BEL",
            "DE",
            "DEU",
            "GER",
            "DK",
            "DNK",
            "ES",
            "ESP",
            "FR",
            "FRA",
            "GB",
            "GBR",
            "EN",
            "ENG",
            "HR",
            "HRV",
            "IT",
            "ITA",
            "NL",
            "NLD",
            "NO",
            "NOR",
            "PT",
            "PRT",
            "RS",
            "SRB",
            "SE",
            "SWE",
        }
        south_america = {
            "AR",
            "ARG",
            "BO",
            "BOL",
            "BR",
            "BRA",
            "CL",
            "CHL",
            "CO",
            "COL",
            "EC",
            "ECU",
            "PE",
            "PER",
            "PY",
            "PRY",
            "UY",
            "URY",
            "VE",
            "VEN",
        }
        north_america = {
            "AG",
            "ATG",
            "BQ",
            "CU",
            "CUB",
            "CA",
            "CAN",
            "CR",
            "CRI",
            "GD",
            "GRD",
            "GF",
            "GUF",
            "GY",
            "GUY",
            "HT",
            "HTI",
            "JM",
            "JAM",
            "MF",
            "MAF",
            "MQ",
            "MTQ",
            "MX",
            "MEX",
            "NC",
            "NCL",
            "TT",
            "TTO",
            "US",
            "USA",
        }
        asia = {
            "CN",
            "CHN",
            "IR",
            "IRN",
            "JP",
            "JPN",
            "KR",
            "KOR",
            "PS",
            "PSE",
            "QA",
            "QAT",
            "SA",
            "SAU",
            "SY",
            "SYR",
            "TM",
            "TKM",
            "TR",
            "TUR",
        }
        oceania = {"AU", "AUS", "NZ", "NZL"}
        if code in africa:
            return "africa"
        if code in europe:
            return "europe"
        if code in south_america:
            return "south_america"
        if code in north_america:
            return "north_america"
        if code in asia:
            return "asia"
        if code in oceania:
            return "oceania"
        return "global"

    def _save_data_uri_override(self, player_id: str, image_data_uri: str) -> tuple[str, str, str, int, str]:
        header, _, payload = image_data_uri.partition(",")
        if not payload or "base64" not in header.lower():
            raise RegenPortraitError("portrait_image_data_uri_invalid")
        mime_type = "image/png"
        if "image/jpeg" in header.lower() or "image/jpg" in header.lower():
            mime_type = "image/jpeg"
            extension = "jpg"
        else:
            extension = "png"
        raw = base64.b64decode(payload, validate=True)
        if not raw:
            raise RegenPortraitError("portrait_image_data_empty")
        checksum = hashlib.sha256(raw).hexdigest()
        storage_key, portrait_url = self._save_file(
            raw, "portrait_overrides", f"{player_id}_{checksum[:16]}.{extension}"
        )
        return portrait_url, storage_key, mime_type, len(raw), checksum

    @staticmethod
    def _media_root() -> Path:
        configured = os.environ.get("GTE_GENERATED_MEDIA_ROOT")
        if configured:
            return Path(configured)
        return Path(__file__).resolve().parents[3] / GENERATED_MEDIA_DIR

    @staticmethod
    def _public_base_url() -> str:
        configured = (
            os.environ.get("GTE_GENERATED_MEDIA_BASE_URL")
            or os.environ.get("GTE_PUBLIC_API_BASE_URL")
            or os.environ.get("GTE_API_BASE_URL")
            or "http://127.0.0.1:8000"
        )
        return configured.rstrip("/")

    def _save_file(self, payload: bytes, subdir: str, filename: str) -> tuple[str, str]:
        safe_filename = "".join(ch for ch in filename if ch.isalnum() or ch in {"-", "_", "."})
        root = self._media_root()
        directory = root / subdir
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / safe_filename
        path.write_bytes(payload)
        storage_key = f"{subdir}/{safe_filename}"
        return storage_key, f"{self._public_base_url()}{GENERATED_MEDIA_ROUTE}/{storage_key}"

    def _portrait_image_row(self, player_id: str) -> PlayerImageMetadata | None:
        return self.session.scalar(
            select(PlayerImageMetadata).where(
                PlayerImageMetadata.player_id == player_id,
                PlayerImageMetadata.image_role == PORTRAIT_ROLE,
            )
        )

    def _require_player(self, player_id: str) -> Player:
        player = self.session.get(Player, player_id)
        if player is None:
            raise RegenPortraitNotFoundError("player_not_found")
        return player

    @staticmethod
    def _approved_image_url(player: Player) -> str | None:
        candidates = sorted(
            player.image_metadata,
            key=lambda image: (
                not image.is_primary,
                image.moderation_status != "approved",
                image.created_at or datetime.min,
                image.id,
            ),
        )
        for image in candidates:
            if image.moderation_status == "rejected":
                continue
            if image.source_url:
                return image.source_url
            if image.storage_key:
                return image.storage_key
        return None

    @staticmethod
    def _first_string(payload: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _select_regen_face_bank_asset(self, *, seed: str, recipe: dict[str, Any]) -> dict[str, Any] | None:
        assets = self._face_bank_assets()
        if not assets:
            return None

        ethnicity_groups = self._portrait_groups_from_recipe(recipe)
        pool = [asset for asset in assets if self._asset_matches_portrait_groups(asset, ethnicity_groups)]
        if not pool:
            return None
        key = f"{NEWGEN_FACE_BANK_COLLECTION}:{':'.join(ethnicity_groups)}"
        return pool[self._index_for(seed, key, len(pool))]

    def _existing_portrait_is_current_face_bank(
        self,
        *,
        existing_url: str,
        existing_recipe: dict[str, Any],
        expected_recipe: dict[str, Any],
        metadata: dict[str, Any],
    ) -> bool:
        if self._is_legacy_procedural_portrait(existing_url):
            return False
        if str(metadata.get("portraitSourceCollection") or "") not in {"", NEWGEN_FACE_BANK_COLLECTION}:
            return False
        if str(metadata.get("portraitSourceProvider") or "") not in {"", NEWGEN_FACE_BANK_PROVIDER}:
            return False
        if str(metadata.get("portraitRecipeVersion") or "") != FACE_RECIPE_VERSION:
            return False
        if self._portrait_groups_from_recipe(existing_recipe) != self._portrait_groups_from_recipe(expected_recipe):
            return False
        storage_key = self._storage_key_from_url(existing_url)
        if not storage_key:
            return False
        asset = self._face_bank_asset_by_storage_key(storage_key)
        if asset is None:
            return False
        return self._asset_matches_portrait_groups(asset, self._portrait_groups_from_recipe(expected_recipe))

    def _face_bank_asset_by_storage_key(self, storage_key: str) -> dict[str, Any] | None:
        normalized_key = storage_key.replace("\\", "/").lstrip("/").lower()
        for asset in self._face_bank_assets():
            candidate = str(asset.get("storage_key") or "").replace("\\", "/").lstrip("/").lower()
            if candidate == normalized_key:
                return asset
        return None

    def _face_bank_assets(self) -> list[dict[str, Any]]:
        manifest_path = self._face_bank_manifest_path()
        try:
            stat = manifest_path.stat()
        except OSError:
            return []
        return list(
            self._cached_face_bank_assets(
                str(manifest_path),
                int(stat.st_mtime_ns),
                int(stat.st_size),
            )
        )

    @classmethod
    @lru_cache(maxsize=8)
    def _cached_face_bank_assets(
        cls,
        manifest_path: str,
        modified_ns: int,
        size_bytes: int,
    ) -> tuple[dict[str, Any], ...]:
        del modified_ns, size_bytes
        try:
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ()
        raw_assets = manifest.get("assets")
        if not isinstance(raw_assets, list):
            return ()
        return tuple(cls._usable_newgen_face_bank_assets(raw_assets))

    @classmethod
    def _usable_newgen_face_bank_assets(cls, raw_assets: list[Any]) -> list[dict[str, Any]]:
        allowed_extensions = (".png", ".jpg", ".jpeg", ".webp")
        assets = [
            asset
            for asset in raw_assets
            if isinstance(asset, dict)
            and str(asset.get("collection") or "") == NEWGEN_FACE_BANK_COLLECTION
            and isinstance(asset.get("storage_key"), str)
            and str(asset["storage_key"]).lower().endswith(allowed_extensions)
            and cls._normalize_ethnicity_label(asset.get("ethnicity")) != ""
        ]
        return sorted(assets, key=lambda asset: str(asset.get("storage_key") or "").lower())

    @classmethod
    def _asset_matches_portrait_groups(cls, asset: dict[str, Any], groups: tuple[str, ...]) -> bool:
        asset_group = cls._normalize_ethnicity_label(asset.get("ethnicity"))
        allowed = {cls._normalize_ethnicity_label(group) for group in groups}
        return asset_group in allowed

    @classmethod
    def _portrait_groups_from_recipe(cls, recipe: dict[str, Any]) -> tuple[str, ...]:
        raw_groups = recipe.get("portraitEthnicityGroups")
        values: list[str] = []
        if isinstance(raw_groups, list):
            values.extend(str(value) for value in raw_groups if str(value or "").strip())
        raw_group = recipe.get("portraitEthnicity")
        if isinstance(raw_group, str) and raw_group.strip():
            values.append(raw_group)
        unique: list[str] = []
        seen: set[str] = set()
        for value in values or ["Mixed"]:
            normalized = cls._normalize_ethnicity_label(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(value.strip())
        return tuple(unique or ["Mixed"])

    @classmethod
    def _normalize_ethnicity_label(cls, value: object) -> str:
        return " ".join(str(value or "").replace("_", " ").replace("-", " ").strip().lower().split())

    @classmethod
    def _portrait_ethnicity_groups(cls, country_code: str | None) -> tuple[str, ...]:
        code = (country_code or "").strip().upper()
        african = {
            "AGO",
            "AO",
            "BEN",
            "BJ",
            "BFA",
            "BF",
            "BDI",
            "BI",
            "BWA",
            "BW",
            "CAF",
            "CF",
            "CIV",
            "CI",
            "CMR",
            "CM",
            "COD",
            "CD",
            "COG",
            "CG",
            "COM",
            "KM",
            "CPV",
            "CV",
            "DJI",
            "DJ",
            "ERI",
            "ER",
            "ETH",
            "ET",
            "GAB",
            "GA",
            "GHA",
            "GH",
            "GIN",
            "GN",
            "GMB",
            "GM",
            "GNB",
            "GW",
            "GNQ",
            "GQ",
            "KEN",
            "KE",
            "LBR",
            "LR",
            "LSO",
            "LS",
            "MDG",
            "MG",
            "MLI",
            "ML",
            "MOZ",
            "MZ",
            "MRT",
            "MR",
            "MUS",
            "MU",
            "MWI",
            "MW",
            "NAM",
            "NA",
            "NER",
            "NE",
            "NGA",
            "NG",
            "RWA",
            "RW",
            "SEN",
            "SN",
            "SLE",
            "SL",
            "SOM",
            "SO",
            "SSD",
            "SS",
            "STP",
            "ST",
            "SWZ",
            "SZ",
            "SYC",
            "SC",
            "TCD",
            "TD",
            "TGO",
            "TG",
            "TZA",
            "TZ",
            "UGA",
            "UG",
            "ZAF",
            "ZA",
            "ZMB",
            "ZM",
            "ZWE",
            "ZW",
        }
        middle_east = {
            "AFG",
            "AF",
            "ARE",
            "AE",
            "BHR",
            "BH",
            "DZA",
            "DZ",
            "EGY",
            "EG",
            "IRN",
            "IR",
            "IRQ",
            "IQ",
            "ISR",
            "IL",
            "JOR",
            "JO",
            "KWT",
            "KW",
            "LBN",
            "LB",
            "LBY",
            "LY",
            "MAR",
            "MA",
            "OMN",
            "OM",
            "PSE",
            "PS",
            "QAT",
            "QA",
            "SAU",
            "SA",
            "SDN",
            "SD",
            "SYR",
            "SY",
            "TUN",
            "TN",
            "TUR",
            "TR",
            "YEM",
            "YE",
        }
        indian = {
            "BGD",
            "BD",
            "IND",
            "IN",
            "LKA",
            "LK",
            "MDV",
            "MV",
            "NPL",
            "NP",
            "PAK",
            "PK",
        }
        east_asian = {
            "CHN",
            "CN",
            "HKG",
            "HK",
            "JPN",
            "JP",
            "KOR",
            "KR",
            "MAC",
            "MO",
            "MNG",
            "MN",
            "PRK",
            "KP",
            "TWN",
            "TW",
        }
        southeast_asian = {
            "BRN",
            "BN",
            "IDN",
            "ID",
            "KHM",
            "KH",
            "LAO",
            "LA",
            "MMR",
            "MM",
            "MYS",
            "MY",
            "PHL",
            "PH",
            "SGP",
            "SG",
            "THA",
            "TH",
            "TLS",
            "TL",
            "VNM",
            "VN",
        }
        hispanic = {
            "ARG",
            "AR",
            "BOL",
            "BO",
            "CHL",
            "CL",
            "COL",
            "CO",
            "CRI",
            "CR",
            "CUB",
            "CU",
            "DOM",
            "DO",
            "ECU",
            "EC",
            "SLV",
            "SV",
            "GTM",
            "GT",
            "HND",
            "HN",
            "MEX",
            "MX",
            "NIC",
            "NI",
            "PAN",
            "PA",
            "PER",
            "PE",
            "PRI",
            "PR",
            "PRY",
            "PY",
            "URY",
            "UY",
            "VEN",
            "VE",
        }
        north_european = {
            "AUT",
            "AT",
            "BEL",
            "BE",
            "BLR",
            "BY",
            "CHE",
            "CH",
            "CZE",
            "CZ",
            "DEU",
            "DE",
            "GER",
            "DNK",
            "DK",
            "ENG",
            "EST",
            "EE",
            "FIN",
            "FI",
            "FRA",
            "FR",
            "GBR",
            "GB",
            "IRL",
            "IE",
            "ISL",
            "IS",
            "LTU",
            "LT",
            "LUX",
            "LU",
            "LVA",
            "LV",
            "NLD",
            "NL",
            "NOR",
            "NO",
            "POL",
            "PL",
            "RUS",
            "RU",
            "SCO",
            "SVK",
            "SK",
            "SWE",
            "SE",
            "UKR",
            "UA",
            "WAL",
        }
        south_european = {
            "ALB",
            "AL",
            "BIH",
            "BA",
            "BGR",
            "BG",
            "ESP",
            "ES",
            "GRC",
            "GR",
            "HRV",
            "HR",
            "ITA",
            "IT",
            "MKD",
            "MK",
            "MNE",
            "ME",
            "PRT",
            "PT",
            "ROU",
            "RO",
            "SRB",
            "RS",
            "SVN",
            "SI",
            "XK",
            "XKX",
        }
        caribbean_african = {
            "AG",
            "ATG",
            "BQ",
            "GD",
            "GRD",
            "GF",
            "GUF",
            "GY",
            "GUY",
            "HTI",
            "HT",
            "JAM",
            "JM",
            "MF",
            "MAF",
            "MQ",
            "MTQ",
            "TTO",
            "TT",
        }

        if code in african:
            return ("African",)
        if code in middle_east:
            return ("Middle east",)
        if code in indian:
            return ("Indian",)
        if code in east_asian:
            return ("East asian",)
        if code in southeast_asian:
            return ("Mixed", "East asian")
        if code in hispanic:
            return ("Hispanic",)
        if code in {"BRA", "BR"}:
            return ("Mixed", "Hispanic", "African")
        if code in caribbean_african:
            return ("African", "Mixed")
        if code in north_european:
            return ("North european",)
        if code in south_european:
            return ("South european",)
        if code in {"USA", "US", "CAN", "CA", "AUS", "AU", "NZL", "NZ"}:
            return ("Mixed", "North european", "African", "Hispanic")
        return ("Mixed",)

    @staticmethod
    def _asset_source_provider(asset: dict[str, Any]) -> str:
        return NEWGEN_FACE_BANK_PROVIDER

    @staticmethod
    def _asset_status(asset: dict[str, Any]) -> str:
        return "ready_newgen_face_bank"

    @staticmethod
    def _mime_type_for_storage_key(storage_key: str) -> str:
        lowered = storage_key.lower()
        if lowered.endswith(".jpg") or lowered.endswith(".jpeg"):
            return "image/jpeg"
        if lowered.endswith(".webp"):
            return "image/webp"
        return "image/png"

    def _deactivate_existing_portrait_image(self, player_id: str) -> None:
        image = self._portrait_image_row(player_id)
        if image is None:
            return
        image.is_primary = False
        image.moderation_status = "rejected"
        image.last_processed_at = datetime.now(UTC)

    @classmethod
    def _asset_matches_region(cls, asset: dict[str, Any], region: str) -> bool:
        label = " ".join(
            str(asset.get(key) or "").lower() for key in ("ethnicity", "hair_colour", "source_path", "storage_key")
        )
        if region == "africa":
            return "african" in label or "africa" in label or "mena" in label
        if region == "asia":
            return any(token in label for token in ("asian", "seasian", "mesa", "mena", "middle east", "east asian"))
        if region == "south_america":
            return any(token in label for token in ("south american", "hispanic", "samed"))
        if region == "north_america":
            return any(token in label for token in ("caucasian", "hispanic", "north european"))
        if region == "europe":
            return any(
                token in label
                for token in (
                    "caucasian",
                    "central european",
                    "eeca",
                    "italmed",
                    "scandinavian",
                    "spanmed",
                    "yugogreek",
                    "north european",
                    "south european",
                )
            )
        if region == "oceania":
            return any(token in label for token in ("caucasian", "south european"))
        return True

    @classmethod
    def _optional_int(cls, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _face_bank_manifest_path(self) -> Path:
        configured = os.environ.get("GTEX_REGEN_FACE_BANK_MANIFEST") or os.environ.get("GTE_REGEN_FACE_BANK_MANIFEST")
        if configured:
            return Path(configured)
        return self._media_root() / FACE_BANK_MANIFEST

    def _generated_media_url(self, storage_key: str) -> str:
        # Percent-encode each path segment but keep "/" as a separator: most of
        # the scripted face bank has spaces in its filenames (e.g.
        # ".../Untitled-1 copy.png"), and an unencoded space produces an invalid
        # URL that gets persisted onto dna_profile.portraitUrl and the image
        # metadata rows.  `_storage_key_from_url` reverses this.
        quoted_key = quote(storage_key.lstrip("/"), safe="/")
        return f"{self._public_base_url()}{GENERATED_MEDIA_ROUTE}/{quoted_key}"

    @staticmethod
    def _storage_key_from_url(url: str | None) -> str | None:
        if not url:
            return None
        marker = f"{GENERATED_MEDIA_ROUTE}/"
        if marker in url:
            # Decode so the key round-trips back to the manifest's raw form;
            # face bank lookups compare against unencoded storage keys.
            return unquote(url.split(marker, 1)[1])
        return None

    @staticmethod
    def _is_legacy_procedural_portrait(url: str | None) -> bool:
        if not url:
            return False
        lowered = url.lower()
        return (
            lowered.endswith(".svg")
            or "/national_regen_portraits/" in lowered
            or "/regen_portraits/" in lowered
            or "/regen_newgen_faces/fm_ai/" in lowered
            or "/portrait_overrides/" in lowered
            or "/regen_portrait_overrides/" in lowered
        )


__all__ = [
    "FACE_RECIPE_VERSION",
    "NEWGEN_FACE_BANK_PROVIDER",
    "RegenPortraitError",
    "RegenPortraitNotFoundError",
    "RegenPortraitResult",
    "RegenPortraitService",
]
