from __future__ import annotations

from datetime import date, datetime, timezone
import json

import app.models  # noqa: F401
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ingestion.models import Player
from app.models.base import Base
from app.models.regen import RegenProfile
from app.models.regen_ecosystem import NationalRegenSeed
from scripts.audit_repair_regen_portrait_lane import audit_or_repair


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _write_face_bank(tmp_path) -> None:
    face_path = tmp_path / "regen_newgen_faces" / "script_skin_hair" / "African" / "Black" / "africa-black-1.png"
    face_path.parent.mkdir(parents=True, exist_ok=True)
    face_path.write_bytes(b"fake-png")
    manifest = {
        "version": 1,
        "usage": "regen_newgen_only",
        "source_layout": "script_skin_hair",
        "fallback_policy": "no_fallbacks_use_ethnicity_matched_script_skin_hair_only",
        "assets": [
            {
                "collection": "script_skin_tone_hair_colour",
                "ethnicity": "African",
                "hair_colour": "Black",
                "source_path": "African/Black/africa-black-1.png",
                "storage_key": "regen_newgen_faces/script_skin_hair/African/Black/africa-black-1.png",
                "bytes": face_path.stat().st_size,
                "sha256": "test-sha",
            }
        ],
    }
    (tmp_path / "regen_newgen_faces" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _seed_regen_player(session: Session) -> Player:
    player = Player(
        id="regen-player-1",
        source_provider="gtex_regen",
        provider_external_id="regen:test",
        full_name="Ayo Prospect",
        position="CM",
        normalized_position="midfielder",
        date_of_birth=date(2008, 4, 1),
        is_real_player=False,
        is_tradable=True,
        dna_profile={
            "portraitUrl": "https://media.test/generated-media/regen_portraits/legacy.png",
            "portraitStatus": "ready",
        },
    )
    session.add(player)
    session.flush()
    session.add(
        RegenProfile(
            id="regen-profile-1",
            regen_id="regen-test",
            player_id=player.id,
            linked_unique_card_id="card-test",
            generated_for_club_id="club-test",
            birth_country_code="NG",
            primary_position="CM",
            secondary_positions_json=[],
            generated_at=datetime.now(timezone.utc),
            current_gsi=68,
            current_ability_range_json={"minimum": 65, "maximum": 70},
            potential_range_json={"minimum": 82, "maximum": 88},
            scout_confidence="medium",
            generation_source="academy",
            club_quality_score=70,
            metadata_json={},
        )
    )
    session.flush()
    return player


def _seed_national_regen(session: Session) -> NationalRegenSeed:
    seed = NationalRegenSeed(
        id="national-seed-1",
        seed_key="NG:u20:cm:1",
        display_name="Kelechi Seed",
        age=19,
        age_band="u20",
        country_code="NG",
        country_name="Nigeria",
        primary_position="CM",
        secondary_positions_json=[],
        current_rating=70,
        potential_rating=86,
        personality_seed_json={},
        metadata_json={
            "portraitUrl": "https://media.test/generated-media/national_regen_portraits/legacy.png",
            "portraitStatus": "ready",
        },
    )
    session.add(seed)
    session.flush()
    return seed


def test_regen_portrait_lane_audit_is_non_destructive(session: Session, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "https://media.test")
    _write_face_bank(tmp_path)
    player = _seed_regen_player(session)
    seed = _seed_national_regen(session)

    stats = audit_or_repair(session, apply=False)

    assert stats.player_regens_scanned == 1
    assert stats.national_seeds_scanned == 1
    assert stats.player_regens_repaired == 0
    assert stats.national_seeds_repaired == 0
    assert stats.repair_needed_samples
    assert player.dna_profile["portraitUrl"].endswith("/regen_portraits/legacy.png")
    assert seed.metadata_json["portraitUrl"].endswith("/national_regen_portraits/legacy.png")


def test_regen_portrait_lane_apply_repairs_seeded_regens(session: Session, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "https://media.test")
    _write_face_bank(tmp_path)
    player = _seed_regen_player(session)
    seed = _seed_national_regen(session)

    stats = audit_or_repair(session, apply=True)

    assert stats.player_regens_repaired == 1
    assert stats.national_seeds_repaired == 1
    assert stats.player_regens_missing_asset == 0
    assert stats.national_seeds_missing_asset == 0
    assert player.dna_profile["portraitUrl"].endswith(
        "/generated-media/regen_newgen_faces/script_skin_hair/African/Black/africa-black-1.png"
    )
    assert player.dna_profile["portraitStatus"] == "ready_newgen_face_bank"
    assert player.dna_profile["portraitSourceProvider"] == "gtex_regen_newgen_face_bank"
    assert seed.metadata_json["portraitUrl"].endswith(
        "/generated-media/regen_newgen_faces/script_skin_hair/African/Black/africa-black-1.png"
    )
    assert seed.metadata_json["portraitSourceCollection"] == "script_skin_tone_hair_colour"
