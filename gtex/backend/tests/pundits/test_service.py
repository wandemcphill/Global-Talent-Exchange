from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from app.pundits.service import PunditService
from backend.tests.match_engine.helpers import build_request


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[CompetitionMatch.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_pundit_service_builds_analysis_and_debate_lines() -> None:
    session_factory = _session_factory()
    payload = MatchSimulationService().build_replay_payload(build_request(seed=41, match_id="pundit-service"))
    settings = load_settings(environ={"DATABASE_URL": "sqlite+pysqlite:///:memory:"})

    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id=payload.match_id,
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                home_club_id=payload.summary.home_stats.team_id,
                away_club_id=payload.summary.away_stats.team_id,
                metadata_json={"replay_payload": payload.model_dump(mode="json")},
            )
        )
        session.commit()

        debate = PunditService(session=session, settings=settings).build_match_debate(payload.match_id)

    assert debate.personas
    assert debate.hot_takes
    assert len(debate.lines) >= 3
    assert debate.analysis.score == f"{payload.summary.home_score}-{payload.summary.away_score}"
