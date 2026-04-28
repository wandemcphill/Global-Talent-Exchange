from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import base64
import hashlib
import os
from pathlib import Path
import struct
from typing import Any
import zlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player, PlayerImageMetadata
from app.models.regen import RegenProfile, RegenVisualProfile
from app.models.regen_ecosystem import NationalRegenSeed

FACE_RECIPE_VERSION = "gtex_regen_face_v1"
PORTRAIT_SIZE = 256
PORTRAIT_ROLE = "portrait"
GENERATED_PROVIDER = "gtex_regen_portrait"
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


class _Canvas:
    def __init__(
        self, width: int = PORTRAIT_SIZE, height: int = PORTRAIT_SIZE, background: tuple[int, int, int] = (23, 35, 45)
    ):
        self.width = width
        self.height = height
        self.data = bytearray(background * width * height)

    def pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        offset = (y * self.width + x) * 3
        self.data[offset : offset + 3] = bytes(color)

    def rect(self, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        for y in range(max(0, y0), min(self.height, y1)):
            row_offset = (y * self.width) * 3
            for x in range(max(0, x0), min(self.width, x1)):
                offset = row_offset + (x * 3)
                self.data[offset : offset + 3] = bytes(color)

    def ellipse(self, cx: int, cy: int, rx: int, ry: int, color: tuple[int, int, int]) -> None:
        if rx <= 0 or ry <= 0:
            return
        rx2 = rx * rx
        ry2 = ry * ry
        threshold = rx2 * ry2
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) * (x - cx) * ry2) + ((y - cy) * (y - cy) * rx2) <= threshold:
                    self.pixel(x, y, color)

    def line(self, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int], thickness: int = 1) -> None:
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x = x0
        y = y0
        while True:
            for yy in range(y - thickness, y + thickness + 1):
                for xx in range(x - thickness, x + thickness + 1):
                    self.pixel(xx, yy, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def png(self) -> bytes:
        rows = bytearray()
        stride = self.width * 3
        for y in range(self.height):
            rows.append(0)
            start = y * stride
            rows.extend(self.data[start : start + stride])

        def chunk(kind: bytes, payload: bytes) -> bytes:
            return (
                struct.pack(">I", len(payload))
                + kind
                + payload
                + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
            )

        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
            + chunk(b"IEND", b"")
        )


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
        if existing_recipe and existing_url and existing_seed and not force:
            return RegenPortraitResult(
                player_id=player.id,
                face_seed=existing_seed,
                face_recipe=existing_recipe,
                portrait_url=existing_url,
                status=str(dna.get("portraitStatus") or "ready"),
                storage_key=self._storage_key_from_url(existing_url),
            )

        visual_profile = visual_profile or self.session.scalar(
            select(RegenVisualProfile).where(RegenVisualProfile.regen_profile_id == regen.id)
        )
        seed = existing_seed or (visual_profile.portrait_seed if visual_profile is not None else None)
        seed = seed or self._deterministic_player_seed(player, regen)
        recipe = self._face_recipe(seed=seed, player=player, regen=regen)
        png_bytes = self.render_png(recipe)
        storage_key, portrait_url = self._save_png(png_bytes, "regen_portraits", f"{player.id}_{seed[:16]}.png")
        checksum = hashlib.sha256(png_bytes).hexdigest()

        image = self._portrait_image_row(player.id)
        if image is None:
            image = PlayerImageMetadata(
                source_provider=GENERATED_PROVIDER,
                provider_external_id=f"{GENERATED_PROVIDER}:{player.id}",
                player_id=player.id,
                image_role=PORTRAIT_ROLE,
            )
            self.session.add(image)
        image.source_provider = GENERATED_PROVIDER
        image.provider_external_id = f"{GENERATED_PROVIDER}:{player.id}"
        image.source_url = portrait_url
        image.storage_key = storage_key
        image.width = PORTRAIT_SIZE
        image.height = PORTRAIT_SIZE
        image.mime_type = "image/png"
        image.file_size_bytes = len(png_bytes)
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
            "portraitStatus": "ready",
            "portraitGeneratedAt": datetime.now(UTC).isoformat(),
            "portraitRecipeVersion": FACE_RECIPE_VERSION,
        }
        self._upsert_visual_profile(
            regen=regen,
            visual_profile=visual_profile,
            seed=seed,
            recipe=recipe,
            portrait_url=portrait_url,
            status="ready",
        )
        self.session.flush()
        return RegenPortraitResult(
            player_id=player.id,
            face_seed=seed,
            face_recipe=recipe,
            portrait_url=portrait_url,
            status="ready",
            storage_key=storage_key,
        )

    def ensure_national_seed_portrait(self, seed: NationalRegenSeed, *, force: bool = False) -> dict[str, Any]:
        metadata = dict(seed.metadata_json or {})
        if metadata.get("portraitStatus") == "banned" and not force:
            return metadata
        existing_url = self._first_string(metadata, "portraitUrl", "portrait_url", "image_url")
        existing_recipe = metadata.get("faceRecipe") if isinstance(metadata.get("faceRecipe"), dict) else None
        face_seed = self._first_string(metadata, "faceSeed", "face_seed")
        if existing_url and existing_recipe and face_seed and not force:
            return metadata
        face_seed = face_seed or self._deterministic_seed(
            "national-seed",
            seed.seed_key,
            seed.display_name,
            seed.country_code,
            seed.primary_position,
        )
        recipe = self._face_recipe_from_context(
            seed=face_seed,
            age=seed.age,
            country_code=seed.country_code,
            position=seed.primary_position,
            rating=seed.current_rating,
        )
        png_bytes = self.render_png(recipe)
        storage_key, portrait_url = self._save_png(
            png_bytes, "national_regen_portraits", f"{seed.id}_{face_seed[:16]}.png"
        )
        seed.metadata_json = {
            **metadata,
            "faceSeed": face_seed,
            "faceRecipe": recipe,
            "portraitUrl": portrait_url,
            "portraitStatus": "ready",
            "portraitRecipeVersion": FACE_RECIPE_VERSION,
            "portraitStorageKey": storage_key,
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

    @staticmethod
    def render_png(recipe: dict[str, Any]) -> bytes:
        seed = str(recipe.get("seed") or "")
        background = _background_color(str(recipe.get("backgroundStyleId") or "bg_00"))
        canvas = _Canvas(background=background)
        canvas.rect(0, 170, PORTRAIT_SIZE, PORTRAIT_SIZE, _darken(background, 0.7))
        shirt_color = _shirt_color(str(recipe.get("shirtColorId") or "shirt_00"))
        canvas.ellipse(128, 235, 86, 56, _darken(shirt_color, 0.82))
        canvas.rect(62, 202, 194, 256, shirt_color)
        canvas.line(95, 205, 128, 246, _lighten(shirt_color, 1.22), 3)
        canvas.line(161, 205, 128, 246, _darken(shirt_color, 0.78), 3)

        skin = _skin_color(str(recipe.get("skinToneId") or "skin_02"))
        hair = _hair_color(str(recipe.get("hairColorId") or "hair_01"))
        face_shape = _index_from_id(str(recipe.get("faceShapeId") or "face_02"), 6)
        rx = (45, 48, 51, 47, 53, 49)[face_shape]
        ry = (58, 62, 57, 65, 60, 55)[face_shape]
        canvas.rect(111, 166, 145, 207, _darken(skin, 0.88))
        canvas.ellipse(92, 124, 12, 20, _darken(skin, 0.95))
        canvas.ellipse(164, 124, 12, 20, _darken(skin, 0.95))
        canvas.ellipse(128, 119, rx, ry, skin)

        hair_style = _index_from_id(str(recipe.get("hairStyleId") or "hair_style_01"), 7)
        if hair_style == 0:
            canvas.ellipse(128, 73, rx + 5, 26, hair)
            canvas.rect(82, 74, 174, 93, hair)
        elif hair_style == 1:
            canvas.ellipse(128, 69, rx + 10, 32, hair)
        elif hair_style == 2:
            canvas.ellipse(116, 75, rx - 2, 28, hair)
            canvas.rect(78, 79, 160, 94, hair)
        elif hair_style == 3:
            canvas.ellipse(128, 82, rx + 2, 18, hair)
        elif hair_style == 4:
            canvas.ellipse(128, 72, rx + 8, 22, hair)
            canvas.line(116, 63, 170, 91, _lighten(hair, 1.18), 3)
        elif hair_style == 5:
            canvas.ellipse(128, 68, rx + 15, 36, hair)
            canvas.ellipse(91, 86, 18, 24, hair)
            canvas.ellipse(165, 86, 18, 24, hair)
        else:
            canvas.rect(82, 77, 174, 91, hair)
            canvas.line(91, 76, 162, 74, hair, 5)

        eye_color = _eye_color(str(recipe.get("eyeColorId") or "eye_01"))
        eye_shape = _index_from_id(str(recipe.get("eyeShapeId") or "eye_shape_01"), 5)
        eye_rx = (6, 7, 5, 8, 6)[eye_shape]
        eye_ry = (4, 4, 3, 5, 4)[eye_shape]
        canvas.ellipse(109, 121, eye_rx + 2, eye_ry + 1, (245, 244, 238))
        canvas.ellipse(147, 121, eye_rx + 2, eye_ry + 1, (245, 244, 238))
        canvas.ellipse(109, 121, eye_rx, eye_ry, eye_color)
        canvas.ellipse(147, 121, eye_rx, eye_ry, eye_color)
        canvas.ellipse(110, 120, 2, 2, (30, 31, 32))
        canvas.ellipse(148, 120, 2, 2, (30, 31, 32))

        brow = _darken(hair, 0.85)
        brow_offset = _index_from_id(str(recipe.get("browId") or "brow_01"), 4)
        canvas.line(96, 108 - brow_offset, 120, 106, brow, 2)
        canvas.line(136, 106, 160, 108 - brow_offset, brow, 2)

        nose_id = _index_from_id(str(recipe.get("noseId") or "nose_01"), 5)
        canvas.line(128, 127, 125 + nose_id, 149, _darken(skin, 0.72), 2)
        canvas.ellipse(128, 151, 8 + (nose_id % 3), 4, _darken(skin, 0.82))

        mouth_id = _index_from_id(str(recipe.get("mouthId") or "mouth_01"), 5)
        mouth_color = (112, 45, 48) if _index_from_id(seed, 2) == 0 else (143, 68, 64)
        y = 170 + (mouth_id % 3)
        canvas.line(111, y, 145, y + (1 if mouth_id in {1, 3} else 0), mouth_color, 2)
        if mouth_id == 2:
            canvas.ellipse(128, y + 2, 16, 5, _lighten(mouth_color, 1.12))

        facial_hair = _index_from_id(str(recipe.get("facialHairId") or "facial_00"), 5)
        if facial_hair in {1, 3}:
            canvas.line(109, 162, 147, 163, _darken(hair, 0.8), 3)
        if facial_hair in {2, 3, 4}:
            canvas.ellipse(128, 176, 24, 13, _darken(hair, 0.82))
            canvas.ellipse(128, 170, 22, 10, skin)

        return canvas.png()

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
        rating_bucket = max(0, min(9, int((rating or 60) / 10)))
        return {
            "seed": seed,
            "skinToneId": self._choice_id(seed, "skin", "skin", 7, salt=region),
            "faceShapeId": self._choice_id(seed, "face", "face", 6),
            "eyeShapeId": self._choice_id(seed, "eye_shape", "eye_shape", 5),
            "eyeColorId": self._choice_id(seed, "eye", "eye", 5, salt=region),
            "browId": self._choice_id(seed, "brow", "brow", 5),
            "noseId": self._choice_id(seed, "nose", "nose", 6),
            "mouthId": self._choice_id(seed, "mouth", "mouth", 5),
            "hairStyleId": self._choice_id(seed, "hair_style", "hair_style", 7, salt=str(age or "youth")),
            "hairColorId": self._choice_id(seed, "hair", "hair", 6, salt=region),
            "facialHairId": self._choice_id(seed, "facial", "facial", 5, salt=str(age or 17)),
            "ageBand": self._age_band(age),
            "nationalityRegion": region,
            "shirtStyleId": self._choice_id(seed, "shirt_style", "shirt_style", 6, salt=str(position or "CM")),
            "shirtColorId": self._choice_id(seed, "shirt", "shirt", 8, salt=str(position or "CM")),
            "backgroundStyleId": self._choice_id(seed, "bg", "bg", 6, salt=str(rating_bucket)),
        }

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
        africa = {"DZ", "AO", "BJ", "BF", "CM", "CI", "EG", "GH", "GN", "MA", "ML", "NG", "SN", "TN", "ZA"}
        europe = {"AT", "BE", "DE", "DK", "ES", "FR", "GB", "HR", "IT", "NL", "NO", "PT", "RS", "SE"}
        south_america = {"AR", "BO", "BR", "CL", "CO", "EC", "PE", "PY", "UY", "VE"}
        north_america = {"CA", "CR", "JM", "MX", "US"}
        asia = {"CN", "IR", "JP", "KR", "QA", "SA", "TR"}
        oceania = {"AU", "NZ"}
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
        storage_key, portrait_url = self._save_png(
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

    def _save_png(self, png_bytes: bytes, subdir: str, filename: str) -> tuple[str, str]:
        safe_filename = "".join(ch for ch in filename if ch.isalnum() or ch in {"-", "_", "."})
        root = self._media_root()
        directory = root / subdir
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / safe_filename
        path.write_bytes(png_bytes)
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

    @staticmethod
    def _storage_key_from_url(url: str | None) -> str | None:
        if not url:
            return None
        marker = f"{GENERATED_MEDIA_ROUTE}/"
        if marker in url:
            return url.split(marker, 1)[1]
        return None


def _index_from_id(value: str, count: int) -> int:
    if value.startswith(
        (
            "skin_",
            "face_",
            "eye_",
            "eye_shape_",
            "brow_",
            "nose_",
            "mouth_",
            "hair_",
            "hair_style_",
            "facial_",
            "shirt_",
            "shirt_style_",
            "bg_",
        )
    ):
        try:
            return int(value.rsplit("_", 1)[1]) % count
        except (IndexError, ValueError):
            pass
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % count


def _lighten(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(channel * factor))) for channel in color)


def _darken(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return _lighten(color, factor)


def _skin_color(identifier: str) -> tuple[int, int, int]:
    palette = (
        (238, 190, 154),
        (216, 157, 116),
        (187, 124, 82),
        (145, 88, 58),
        (104, 63, 46),
        (246, 205, 171),
        (166, 100, 70),
    )
    return palette[_index_from_id(identifier, len(palette))]


def _hair_color(identifier: str) -> tuple[int, int, int]:
    palette = (
        (31, 26, 24),
        (72, 47, 35),
        (111, 74, 42),
        (174, 132, 72),
        (203, 179, 108),
        (18, 18, 20),
    )
    return palette[_index_from_id(identifier, len(palette))]


def _eye_color(identifier: str) -> tuple[int, int, int]:
    palette = (
        (54, 72, 53),
        (68, 92, 132),
        (76, 45, 30),
        (92, 70, 42),
        (42, 86, 88),
    )
    return palette[_index_from_id(identifier, len(palette))]


def _shirt_color(identifier: str) -> tuple[int, int, int]:
    palette = (
        (190, 32, 46),
        (21, 83, 168),
        (20, 138, 75),
        (238, 239, 232),
        (38, 42, 50),
        (245, 188, 43),
        (117, 54, 150),
        (22, 157, 170),
    )
    return palette[_index_from_id(identifier, len(palette))]


def _background_color(identifier: str) -> tuple[int, int, int]:
    palette = (
        (20, 56, 48),
        (45, 64, 82),
        (70, 50, 91),
        (35, 86, 103),
        (66, 72, 54),
        (84, 54, 54),
    )
    return palette[_index_from_id(identifier, len(palette))]


__all__ = [
    "FACE_RECIPE_VERSION",
    "RegenPortraitError",
    "RegenPortraitNotFoundError",
    "RegenPortraitResult",
    "RegenPortraitService",
]
