from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.fast_cups.models.domain import FastCupDivision, FastCupEntrant
from backend.app.fast_cups.repositories.database import FastCupRecord
from backend.app.fast_cups.services.ecosystem import build_fast_cup_ecosystem_for_session
from backend.app.models.base import Base


def test_fast_cup_ecosystem_persists_generated_cups_and_registrations() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[FastCupRecord.__table__])
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    ecosystem = build_fast_cup_ecosystem_for_session(session_local)
    base_now = datetime(2026, 7, 1, 12, 2, tzinfo=UTC)

    cups = ecosystem.list_upcoming_cups(now=base_now, horizon_intervals=1)
    senior_32 = next(cup for cup in cups if cup.division is FastCupDivision.SENIOR and cup.size == 32)

    joined = ecosystem.join_cup(
        cup_id=senior_32.cup_id,
        entrant=FastCupEntrant(
            club_id="senior-club-001",
            club_name="Senior Club 001",
            division=FastCupDivision.SENIOR,
            rating=4999,
            registered_at=senior_32.slot.registration_opens_at,
        ),
        now=senior_32.slot.registration_opens_at,
    )

    rebuilt = build_fast_cup_ecosystem_for_session(session_local)
    persisted_cups = rebuilt.list_upcoming_cups(now=base_now, horizon_intervals=1)
    persisted = next(cup for cup in persisted_cups if cup.cup_id == senior_32.cup_id)

    assert len(cups) == 8
    assert joined.entrants[0].club_id == "senior-club-001"
    assert len(persisted.entrants) == 1
    assert persisted.entrants[0].club_id == "senior-club-001"

    engine.dispose()
