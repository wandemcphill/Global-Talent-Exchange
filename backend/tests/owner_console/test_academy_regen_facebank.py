"""Academy regens keep a stable face from the newgen face bank."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.event_backbone import EventOutbox
from app.models.risk_ops import AuditLog
from app.models.user import User
from app.models.wallet import (
    LedgerAccount,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerTransaction,
)
from app.models.world_clock import WorldClockState
from app.owner_console import engine as owner_engine
from app.owner_console import ledger, service, storytelling
from app.owner_console.models import OWNER_CONSOLE_TABLES, OwnerClubState, OwnerSquadPlayer
from app.services.regen_portrait_service import RegenPortraitService
from app.services.world_clock_service import DEFAULT_CLOCK_ID

WORLD_NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def _session() -> Session:
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        eng,
        tables=[
            User.__table__,
            ClubProfile.__table__,
            AuditLog.__table__,
            EventOutbox.__table__,
            LedgerAccount.__table__,
            LedgerTransaction.__table__,
            LedgerEntry.__table__,
            LedgerBalanceProjection.__table__,
            WorldClockState.__table__,
            *OWNER_CONSOLE_TABLES,
        ],
    )
    factory = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)
    session = factory()
    session.add(
        WorldClockState(
            id=DEFAULT_CLOCK_ID,
            epoch_real_utc=WORLD_NOW,
            virtual_start_time=WORLD_NOW,
            progression_rate=1.0,
            is_paused=False,
            paused_at_virtual_time=None,
            virtual_months_per_season=12,
            metadata_json={"canonical": True},
        )
    )
    session.commit()
    return session


def _seed_club(session: Session, *, country_code: str = "NG") -> None:
    session.add(
        User(
            id="user-1",
            email="owner1@gtex.test",
            username="owner1",
            password_hash="hash",  # pragma: allowlist secret — synthetic test hash, not a credential
        )
    )
    session.add(
        ClubProfile(
            id="club-1",
            owner_user_id="user-1",
            club_name="Lagos Sovereign FC",
            slug="lagos-sovereign-fc",
            primary_color="#10b981",
            secondary_color="#0f172a",
            accent_color="#f59e0b",
            country_code=country_code,
        )
    )
    session.add(
        OwnerClubState(
            id="state-1",
            club_id="club-1",
            owner_user_id="user-1",
            club_name="Lagos Sovereign FC",
            stage="active",
            prestige=70,
            manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
            facilities_json={"training": 2, "academy": 4, "medical": 2, "stadium": 2, "commercial": 2},
            world_day=10,
            last_tick_at=WORLD_NOW,
            last_world_tick_date=WORLD_NOW.date(),
            value_history_json=[],
        )
    )
    ledger.record(
        session,
        event_type="club_launch_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account("club-1"),
        currency=ledger.GTEX,
        gross=Decimal(100_000),
        club_id="club-1",
        user_id="user-1",
        memo="Initial club grant",
    )
    session.commit()


def _write_manifest(path: Path) -> None:
    assets = [
        {
            "collection": "script_skin_tone_hair_colour",
            "ethnicity": "African",
            "storage_key": f"regen_newgen_faces/african-{index}.png",
            "cloudinary_secure_url": f"https://cdn.example/african-{index}.png",
        }
        for index in range(1, 9)
    ]
    assets.append(
        {
            "collection": "script_skin_tone_hair_colour",
            "ethnicity": "Mixed",
            "storage_key": "regen_newgen_faces/mixed-1.png",
            "cloudinary_secure_url": "https://cdn.example/mixed-1.png",
        }
    )
    path.write_text(json.dumps({"assets": assets}), encoding="utf-8")


def test_academy_intake_stores_distinct_nationality_faces(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    monkeypatch.setenv("GTEX_REGEN_FACE_BANK_MANIFEST", str(manifest))
    session = _session()
    _seed_club(session, country_code="NG")

    regens = service.academy_intake(session, "user-1", "club-1")

    assert len(regens) >= 2
    keys = []
    for regen in regens:
        personality = regen.personality_json
        assert personality["portrait_policy"] == "newgen_bank_only"
        assert personality["portrait_ethnicity"] == "African"
        assert personality["portrait_url"].startswith("https://cdn.example/african-")
        assert personality["portrait_storage_key"].startswith("regen_newgen_faces/african-")
        keys.append(personality["portrait_storage_key"])
        resolved = storytelling.resolve_player_portrait_url(session, regen.id, regen.name)
        assert resolved == personality["portrait_url"]
    assert len(set(keys)) == len(keys)

    monkeypatch.setattr(
        RegenPortraitService,
        "_select_regen_face_bank_asset",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("stored face was re-picked")),
    )
    again = storytelling.resolve_player_portrait_url(session, regens[0].id, regens[0].name)
    assert again == regens[0].personality_json["portrait_url"]


def test_existing_academy_regen_receives_one_face_on_read(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    monkeypatch.setenv("GTEX_REGEN_FACE_BANK_MANIFEST", str(manifest))
    session = _session()
    _seed_club(session)

    prospect = OwnerSquadPlayer(
        club_id="club-1",
        name="Adewale Okonkwo",
        position="midfielder",
        age=17,
        rating=52,
        potential=78,
        is_regen=True,
        acquired_via="academy",
        personality_json={"ambition": 14, "loyalty": 11},
    )
    session.add(prospect)
    session.flush()

    first = service.player_dict(prospect, session)
    stored = prospect.personality_json["portrait_url"]
    assert first["portrait_url"] == stored
    assert stored.startswith("https://cdn.example/african-")
    assert prospect.personality_json["portrait_ethnicity"] == "African"
    assert prospect.personality_json["ambition"] == 14

    monkeypatch.setattr(
        RegenPortraitService,
        "_select_regen_face_bank_asset",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("face was assigned twice")),
    )
    second = service.player_dict(prospect, session)
    assert second["portrait_url"] == stored
    assert storytelling.resolve_player_portrait_url(session, prospect.id, prospect.name) == stored


def test_missing_face_bank_does_not_fail_intake(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GTEX_REGEN_FACE_BANK_MANIFEST", str(tmp_path / "missing-manifest.json"))
    monkeypatch.setattr(storytelling, "_load_face_manifest", lambda: {})
    session = _session()
    _seed_club(session)

    regens = service.academy_intake(session, "user-1", "club-1")

    assert len(regens) >= 1
    for regen in regens:
        assert "portrait_url" not in (regen.personality_json or {})
        portrait = service.player_dict(regen, session)["portrait_url"]
        assert portrait.startswith("data:image/svg+xml")
