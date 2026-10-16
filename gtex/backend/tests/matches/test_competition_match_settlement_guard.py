"""Phase B regression tests for competition match settlement.

Two paths can settle a ``CompetitionMatch``: an operator command and the simulation
worker, which now persists the result before advancement is dispatched. They must
compose — a settled row must still get its standings applied exactly once, must never
be re-settled with a different scoreline, and an abandoned match must never settle.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Completing a match fans out to club-social, fan-prediction, engagement and live-ops
# side effects, so every model module has to be imported before ``create_all`` or those
# tables are missing from the metadata.
import app.models  # noqa: F401
import app.club_finance.models  # noqa: F401
import app.ingestion.models  # noqa: F401
import app.leaderboards.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.live_ops.models  # noqa: F401
import app.matching.models  # noqa: F401
import app.orders.models  # noqa: F401
import app.predictions.models  # noqa: F401
import app.regen_universe.models  # noqa: F401
import app.team_dynamics.models  # noqa: F401
from app.common.enums.match_status import MatchStatus
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_rule_set import CompetitionRuleSet
from app.services.competition_match_service import CompetitionMatchService

COMPETITION_ID = "competition-settle-1"
MATCH_ID = "match-settle-1"


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as open_session:
        yield open_session


def _rule_set() -> CompetitionRuleSet:
    return CompetitionRuleSet(
        id="rules-settle-1",
        competition_id=COMPETITION_ID,
        league_win_points=3,
        league_draw_points=1,
        league_loss_points=0,
    )


def _seed(session: Session, *, status: str = "scheduled", **overrides) -> CompetitionMatch:
    match = CompetitionMatch(
        id=MATCH_ID,
        competition_id=COMPETITION_ID,
        round_id="round-1",
        round_number=1,
        home_club_id="club-home",
        away_club_id="club-away",
        status=status,
        metadata_json={},
        **overrides,
    )
    session.add_all(
        [
            match,
            CompetitionParticipant(
                id="participant-home",
                competition_id=COMPETITION_ID,
                club_id="club-home",
                user_id="user-home",
            ),
            CompetitionParticipant(
                id="participant-away",
                competition_id=COMPETITION_ID,
                club_id="club-away",
                user_id="user-away",
            ),
        ]
    )
    session.flush()
    return match


def _participants(session: Session) -> dict[str, CompetitionParticipant]:
    return {
        item.club_id: item
        for item in session.query(CompetitionParticipant)
        .filter(CompetitionParticipant.competition_id == COMPETITION_ID)
        .all()
    }


def test_standings_apply_exactly_once_across_repeated_completion(session: Session) -> None:
    service = CompetitionMatchService(session=session)
    match = _seed(session)
    rules = _rule_set()

    service.complete_match(match=match, rule_set=rules, home_score=2, away_score=1)
    service.complete_match(match=match, rule_set=rules, home_score=2, away_score=1)

    people = _participants(session)
    assert people["club-home"].points == 3
    assert people["club-home"].played == 1
    assert people["club-away"].played == 1
    assert people["club-away"].points == 0


def test_standings_are_applied_when_the_worker_settled_the_row_first(session: Session) -> None:
    """The worker persists status/score before advancement; standings must still land."""
    service = CompetitionMatchService(session=session)
    match = _seed(
        session,
        status=MatchStatus.COMPLETED.value,
        home_score=3,
        away_score=0,
        winner_club_id="club-home",
    )

    service.complete_match(match=match, rule_set=_rule_set(), home_score=3, away_score=0)

    people = _participants(session)
    assert match.stats_applied is True
    assert people["club-home"].points == 3
    assert people["club-home"].goals_for == 3
    assert people["club-away"].goals_against == 3


def test_a_settled_match_cannot_be_re_settled_with_a_different_score(session: Session) -> None:
    service = CompetitionMatchService(session=session)
    match = _seed(session)
    rules = _rule_set()

    service.complete_match(match=match, rule_set=rules, home_score=2, away_score=1)

    with pytest.raises(ValueError, match="already settled"):
        service.complete_match(match=match, rule_set=rules, home_score=0, away_score=4)

    assert (match.home_score, match.away_score) == (2, 1)
    assert _participants(session)["club-home"].points == 3


@pytest.mark.parametrize("terminal", [MatchStatus.ABANDONED, MatchStatus.CANCELLED])
def test_terminal_non_completed_matches_never_settle(session: Session, terminal: MatchStatus) -> None:
    service = CompetitionMatchService(session=session)
    match = _seed(session, status=terminal.value)

    with pytest.raises(ValueError, match=terminal.value):
        service.complete_match(match=match, rule_set=_rule_set(), home_score=1, away_score=0)

    assert match.status == terminal.value
    assert (match.home_score, match.away_score) == (0, 0)
    assert _participants(session)["club-home"].played == 0
