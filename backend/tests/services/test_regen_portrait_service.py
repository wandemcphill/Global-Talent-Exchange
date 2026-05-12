from __future__ import annotations

from datetime import date, datetime, timezone
import json

import app.models  # noqa: F401
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ingestion.models import Player, PlayerImageMetadata
from app.models.base import Base
from app.models.regen import RegenProfile
from app.services.player_face_service import PlayerFaceService
from app.services.regen_portrait_service import (
    NEWGEN_FACE_BANK_COLLECTION,
    NEWGEN_FACE_BANK_PROVIDER,
    RegenPortraitService,
)

FACE_RECIPE_FIELDS = {
    "seed",
    "skinToneId",
    "faceShapeId",
    "eyeShapeId",
    "eyeColorId",
    "browId",
    "noseId",
    "mouthId",
    "hairStyleId",
    "hairColorId",
    "facialHairId",
    "ageBand",
    "nationalityRegion",
    "portraitEthnicity",
    "portraitEthnicityGroups",
    "shirtStyleId",
    "shirtColorId",
    "backgroundStyleId",
    "jerseyPrimaryHex",
    "jerseyTrimHex",
    "countryCode",
    "position",
    "rating",
    "potential",
    "statPac",
    "statSho",
    "statPas",
    "statDri",
    "statDef",
    "statPhy",
}


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _regen_player(session) -> tuple[Player, RegenProfile]:
    player = Player(
        id="player-reg-1",
        source_provider="gtex_regen",
        provider_external_id="regen:test-1",
        full_name="Ayo Test",
        position="CM",
        normalized_position="midfielder",
        date_of_birth=date(2008, 3, 4),
        is_real_player=False,
        is_tradable=True,
        dna_profile={},
    )
    session.add(player)
    session.flush()
    regen = RegenProfile(
        id="regen-profile-1",
        regen_id="regen-test-1",
        player_id=player.id,
        linked_unique_card_id="card-test-1",
        generated_for_club_id="club-test-1",
        birth_country_code="NG",
        primary_position="CM",
        secondary_positions_json=[],
        generated_at=datetime.now(timezone.utc),
        current_gsi=67,
        current_ability_range_json={"minimum": 63, "maximum": 70},
        potential_range_json={"minimum": 78, "maximum": 86},
        scout_confidence="medium",
        generation_source="academy",
        club_quality_score=72.0,
        metadata_json={},
    )
    session.add(regen)
    session.flush()
    return player, regen


def _write_face_bank(
    tmp_path,
    *,
    include_primary: bool = True,
    include_fallback: bool = True,
    include_north_european: bool = False,
) -> None:
    assets = []
    if include_primary:
        primary_path = tmp_path / "regen_newgen_faces" / "script_skin_hair" / "African" / "Black" / "africa-black-1.png"
        primary_path.parent.mkdir(parents=True, exist_ok=True)
        primary_path.write_bytes(b"fake-primary-png")
        assets.append(
            {
                "collection": "script_skin_tone_hair_colour",
                "ethnicity": "African",
                "hair_colour": "Black",
                "source_path": "African/Black/africa-black-1.png",
                "storage_key": "regen_newgen_faces/script_skin_hair/African/Black/africa-black-1.png",
                "bytes": primary_path.stat().st_size,
                "sha256": "primary-sha",
            }
        )
    if include_fallback:
        fallback_path = tmp_path / "regen_newgen_faces" / "fm_ai" / "African" / "African1.png"
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        fallback_path.write_bytes(b"fake-fallback-png")
        assets.append(
            {
                "collection": "fm_ai_face_generator",
                "ethnicity": "African",
                "hair_colour": "ai_generated",
                "source_path": "African/African1.png",
                "storage_key": "regen_newgen_faces/fm_ai/African/African1.png",
                "bytes": fallback_path.stat().st_size,
                "sha256": "fallback-sha",
            }
        )
    if include_north_european:
        north_european_path = (
            tmp_path
            / "regen_newgen_faces"
            / "script_skin_hair"
            / "North european"
            / "Blonde"
            / "north-european-blonde-1.png"
        )
        north_european_path.parent.mkdir(parents=True, exist_ok=True)
        north_european_path.write_bytes(b"fake-north-european-png")
        assets.append(
            {
                "collection": "script_skin_tone_hair_colour",
                "ethnicity": "North european",
                "hair_colour": "Blonde",
                "source_path": "North european/Blonde/north-european-blonde-1.png",
                "storage_key": (
                    "regen_newgen_faces/script_skin_hair/North european/Blonde/north-european-blonde-1.png"
                ),
                "bytes": north_european_path.stat().st_size,
                "sha256": "north-european-sha",
            }
        )
    manifest = {
        "version": 1,
        "usage": "regen_newgen_only",
        "source_packs": ["script_skin_hair", "fm-ai-face-generator"],
        "fallback_policy": "no_fallbacks_use_ethnicity_matched_script_skin_hair_only",
        "asset_count": len(assets),
        "assets": assets,
    }
    (tmp_path / "regen_newgen_faces" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_regen_portrait_is_deterministic_and_stored(session, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "https://media.test")
    _write_face_bank(tmp_path)
    player, regen = _regen_player(session)

    service = RegenPortraitService(session)
    first = service.ensure_player_portrait(player, regen=regen)
    second = service.ensure_player_portrait(player, regen=regen, force=True)

    assert first.face_seed == second.face_seed
    assert first.face_recipe == second.face_recipe
    assert first.portrait_url == second.portrait_url
    assert set(first.face_recipe or {}) == FACE_RECIPE_FIELDS
    assert player.dna_profile["faceSeed"] == first.face_seed
    assert player.dna_profile["faceRecipe"] == first.face_recipe
    assert player.dna_profile["portraitUrl"] == first.portrait_url
    assert first.storage_key is not None
    assert first.status == "ready_newgen_face_bank"
    assert player.dna_profile["portraitSourceProvider"] == NEWGEN_FACE_BANK_PROVIDER
    assert player.dna_profile["faceRecipe"]["portraitEthnicity"] == "African"
    assert player.dna_profile["faceRecipe"]["portraitEthnicityGroups"] == ["African"]
    assert player.dna_profile["portraitEthnicity"] == "African"
    assert first.storage_key == "regen_newgen_faces/script_skin_hair/African/Black/africa-black-1.png"
    assert (
        first.portrait_url
        == "https://media.test/generated-media/regen_newgen_faces/script_skin_hair/African/Black/africa-black-1.png"
    )

    image = session.scalar(select(PlayerImageMetadata).where(PlayerImageMetadata.player_id == player.id))
    assert image is not None
    assert image.source_url == first.portrait_url
    assert image.source_provider == NEWGEN_FACE_BANK_PROVIDER
    assert image.mime_type == "image/png"
    assert image.moderation_status == "approved"
    assert image.rights_cleared is True


def test_regen_portrait_does_not_use_fm_ai_bank_as_fallback(session, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "https://media.test")
    _write_face_bank(tmp_path, include_primary=False, include_fallback=True)
    player, regen = _regen_player(session)

    result = RegenPortraitService(session).ensure_player_portrait(player, regen=regen)

    assert result.status == "portrait_asset_missing"
    assert result.storage_key is None
    assert result.portrait_url is None
    assert player.dna_profile["portraitSourceProvider"] == NEWGEN_FACE_BANK_PROVIDER
    assert player.dna_profile["portraitSourceCollection"] == "script_skin_tone_hair_colour"


def test_regen_avatar_endpoint_payload_uses_newgen_bank_not_svg(session, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "https://media.test")
    _write_face_bank(tmp_path)
    player, regen = _regen_player(session)
    RegenPortraitService(session).ensure_player_portrait(player, regen=regen)

    payload = PlayerFaceService(session).get_avatar_render(player.id)

    assert (
        payload.portrait_url
        == "https://media.test/generated-media/regen_newgen_faces/script_skin_hair/African/Black/africa-black-1.png"
    )
    assert payload.portrait_status == "ready_newgen_face_bank"
    assert payload.portrait_source_provider == NEWGEN_FACE_BANK_PROVIDER
    assert payload.portrait_source_collection == NEWGEN_FACE_BANK_COLLECTION
    assert payload.portrait_storage_key == "regen_newgen_faces/script_skin_hair/African/Black/africa-black-1.png"
    assert payload.layered_svg is None
    assert payload.static_image_data_uri is None
    assert payload.face is None
    assert payload.legacy_avatar is None
    assert payload.capabilities == ["newgen_face_bank_image"]


def test_regen_portrait_rejects_mismatched_ethnicity_bank_asset(session, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "https://media.test")
    _write_face_bank(tmp_path, include_primary=False, include_fallback=False, include_north_european=True)
    player, regen = _regen_player(session)

    result = RegenPortraitService(session).ensure_player_portrait(player, regen=regen)

    assert result.status == "portrait_asset_missing"
    assert result.storage_key is None
    assert result.portrait_url is None
    assert player.dna_profile["faceRecipe"]["portraitEthnicity"] == "African"


def test_regen_portrait_regenerates_stale_mismatched_assignment(session, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "https://media.test")
    _write_face_bank(tmp_path, include_primary=True, include_fallback=False, include_north_european=True)
    player, regen = _regen_player(session)
    player.dna_profile = {
        "faceSeed": "stale-seed",
        "faceRecipe": {
            "seed": "stale-seed",
            "portraitEthnicity": "North european",
            "portraitEthnicityGroups": ["North european"],
        },
        "portraitUrl": (
            "https://media.test/generated-media/"
            "regen_newgen_faces/script_skin_hair/North european/Blonde/north-european-blonde-1.png"
        ),
        "portraitStatus": "ready_newgen_face_bank",
        "portraitRecipeVersion": "gtex_regen_portrait_assignment_v4",
        "portraitSourceProvider": NEWGEN_FACE_BANK_PROVIDER,
        "portraitSourceCollection": "script_skin_tone_hair_colour",
    }

    result = RegenPortraitService(session).ensure_player_portrait(player, regen=regen)

    assert result.status == "ready_newgen_face_bank"
    assert result.storage_key == "regen_newgen_faces/script_skin_hair/African/Black/africa-black-1.png"
    assert player.dna_profile["faceRecipe"]["portraitEthnicity"] == "African"


def test_regen_portrait_reports_missing_when_no_bank_exists(session, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "https://media.test")
    player, regen = _regen_player(session)

    result = RegenPortraitService(session).ensure_player_portrait(player, regen=regen)

    assert result.status == "portrait_asset_missing"
    assert result.portrait_url is None
    assert result.storage_key is None
    assert player.dna_profile["portraitStatus"] == "portrait_asset_missing"
    assert session.scalar(select(PlayerImageMetadata).where(PlayerImageMetadata.player_id == player.id)) is None


def test_regen_portrait_can_be_banned_and_overridden(session, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "https://media.test")
    _write_face_bank(tmp_path)
    player, regen = _regen_player(session)
    service = RegenPortraitService(session)
    generated = service.ensure_player_portrait(player, regen=regen)

    banned = service.ban_player_portrait(player.id, reason="bad crop", actor_user_id="admin-1")
    assert banned.status == "banned"
    assert banned.portrait_url is None
    assert player.dna_profile["portraitStatus"] == "banned"
    assert player.dna_profile["bannedPortraitUrl"] == generated.portrait_url

    image = session.scalar(select(PlayerImageMetadata).where(PlayerImageMetadata.player_id == player.id))
    assert image is not None
    assert image.moderation_status == "rejected"

    override = service.override_player_portrait(
        player.id,
        portrait_url="https://licensed.test/portrait.png",
        actor_user_id="admin-1",
    )
    assert override.status == "override"
    assert override.portrait_url == "https://licensed.test/portrait.png"
    assert player.dna_profile["portraitStatus"] == "override"
    assert player.dna_profile["portraitUrl"] == "https://licensed.test/portrait.png"
