from __future__ import annotations

import app.models  # noqa: F401
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.story_feed import StoryFeedItem
from app.regen_universe.service import RegenUniverseService


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


def test_announce_rising_stars_publishes_idempotently(session, monkeypatch) -> None:
    def _fake_rising(self, *, limit: int = 20, offset: int = 0, age_max: int = 21):
        del self, age_max
        return {
            "entries": [
                {
                    "player_id": "player-rising-1",
                    "momentum_label": "Breakout form",
                    "player": {
                        "name": "Kofi Ade",
                        "position": "ST",
                        "nationality": "Nigeria",
                        "nationality_code": "NG",
                    },
                },
                {
                    "player_id": "seed:skip-me",
                    "momentum_label": "High-upside prospect",
                    "player": {"name": "Seed Only"},
                },
            ][offset : offset + limit],
            "total": 2,
        }

    monkeypatch.setattr(RegenUniverseService, "list_rising_stars", _fake_rising)
    service = RegenUniverseService(session)

    first = service.announce_rising_stars_to_story_feed(limit=5)
    second = service.announce_rising_stars_to_story_feed(limit=5)
    session.commit()

    assert first["created"] == 1
    assert second["created"] == 0
    items = list(session.scalars(select(StoryFeedItem)).all())
    assert len(items) == 1
    assert items[0].story_type == "regen_rising_star"
    assert items[0].featured is True
    assert items[0].country_code == "NG"
