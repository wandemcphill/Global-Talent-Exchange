from __future__ import annotations

from datetime import date, datetime, timezone

import app.models  # noqa: F401
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ingestion.models import Player, PlayerImageMetadata
from app.models.base import Base
from app.models.regen import RegenProfile
from app.services.regen_portrait_service import RegenPortraitService

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
    "shirtStyleId",
    "shirtColorId",
    "backgroundStyleId",
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


def test_regen_portrait_is_deterministic_and_stored(session, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "https://media.test")
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
    written = tmp_path / first.storage_key
    assert written.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    image = session.scalar(select(PlayerImageMetadata).where(PlayerImageMetadata.player_id == player.id))
    assert image is not None
    assert image.source_url == first.portrait_url
    assert image.moderation_status == "approved"
    assert image.rights_cleared is True


def test_regen_portrait_can_be_banned_and_overridden(session, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "https://media.test")
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
