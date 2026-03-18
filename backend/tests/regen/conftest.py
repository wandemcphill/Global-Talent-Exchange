from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models.base import Base

# Register only the tables required for regen market/legacy tests.
import backend.app.ingestion.models  # noqa: F401
import backend.app.models.club_profile  # noqa: F401
import backend.app.models.player_cards  # noqa: F401
import backend.app.models.player_career_entry  # noqa: F401
import backend.app.models.regen  # noqa: F401
import backend.app.models.user  # noqa: F401


@pytest.fixture()
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with SessionLocal() as db_session:
        yield db_session
