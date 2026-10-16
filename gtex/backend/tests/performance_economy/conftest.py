from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.models  # noqa: F401
import app.players.read_models  # noqa: F401
import app.value_engine.read_models  # noqa: F401
from app.ingestion.models import Player
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from app.models.player_match_performance import PlayerMatchPerformance

KICKOFF = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)


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


@pytest.fixture()
def canonical_player(session) -> Player:
    player = Player(
        id="player-canonical",
        source_provider="test",
        provider_external_id="test:1",
        full_name="Canonical Footballer",
    )
    session.add(player)
    session.flush()
    return player


class FakePlayerStat:
    """Mirrors the shape of ``MatchPlayerStatsView`` from the match engine."""

    def __init__(
        self,
        *,
        player_id: str,
        rating: float | None = 7.5,
        minutes_played: int = 90,
        goals: int = 0,
        assists: int = 0,
        red_card: bool = False,
        started: bool = True,
        team_id: str | None = None,
        player_name: str = "Canonical Footballer",
    ) -> None:
        self.player_id = player_id
        self.player_name = player_name
        self.team_id = team_id
        self.rating = rating
        self.minutes_played = minutes_played
        self.goals = goals
        self.assists = assists
        self.saves = 0
        self.shots_on_target = 0
        self.key_passes = 0
        self.tackles_won = 0
        self.interceptions = 0
        self.yellow_cards = 0
        self.red_card = red_card
        self.started = started
        self.xg = 0.0


def make_match(session, *, match_id: str = "match-1", competition_id: str = "comp-1") -> CompetitionMatch:
    match = CompetitionMatch(
        id=match_id,
        competition_id=competition_id,
        round_id=f"round-{match_id}",
        round_number=1,
        home_club_id="club-home",
        away_club_id="club-away",
        completed_at=KICKOFF,
    )
    session.add(match)
    session.flush()
    return match


def add_performance(
    session,
    *,
    player_id: str = "player-canonical",
    rating: float,
    days_ago: int,
    competition_id: str = "comp-1",
    eligible: bool = True,
    minutes: int = 90,
) -> PlayerMatchPerformance:
    record = PlayerMatchPerformance(
        player_id=player_id,
        match_id=f"m-{competition_id}-{days_ago}",
        competition_id=competition_id,
        occurred_at=KICKOFF - timedelta(days=days_ago),
        rating=rating,
        minutes_played=minutes,
        eligible_for_valuation=eligible,
    )
    session.add(record)
    session.flush()
    return record
