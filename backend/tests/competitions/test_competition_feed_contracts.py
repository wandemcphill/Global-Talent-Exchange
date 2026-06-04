from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.competition_visibility import CompetitionVisibility
from app.common.enums.match_status import MatchStatus
from app.models.base import Base, generate_uuid
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_playoff import CompetitionPlayoff
from app.models.competition_reward import CompetitionReward
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.services.competition_orchestrator import CompetitionOrchestrator


@pytest.fixture
def isolated_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as session:
        yield session
    engine.dispose()


def _add_competition(
    session: Session,
    *,
    name: str,
    format: str = CompetitionFormat.LEAGUE.value,
    status: str = CompetitionStatus.DRAFT.value,
    stage: str = "registration",
    min_participants: int = 2,
    max_participants: int = 4,
) -> Competition:
    competition = Competition(
        id=generate_uuid(),
        host_user_id=f"host-{name}",
        name=name,
        description=None,
        competition_type=format,
        source_type="user_hosted",
        source_id=None,
        format=format,
        visibility=CompetitionVisibility.PUBLIC.value,
        status=status,
        start_mode=CompetitionStartMode.SCHEDULED.value,
        scheduled_start_at=datetime(2035, 6, 3, tzinfo=timezone.utc),
        stage=stage,
        currency="credit",
        entry_fee_minor=0,
        platform_fee_bps=0,
        host_fee_bps=0,
        host_creation_fee_minor=0,
        gross_pool_minor=0,
        net_prize_pool_minor=0,
        metadata_json={},
    )
    rule_set = CompetitionRuleSet(
        id=generate_uuid(),
        competition_id=competition.id,
        format=format,
        min_participants=min_participants,
        max_participants=max_participants,
        league_win_points=3,
        league_draw_points=1,
        league_loss_points=0,
        league_tie_break_order=[],
        league_home_away=False,
        cup_single_elimination=True,
        cup_two_leg_tie=False,
        cup_extra_time=False,
        cup_penalties=True,
        cup_allowed_participant_sizes=[],
        group_stage_enabled=False,
        group_count=None,
        group_size=None,
        group_advance_count=None,
        knockout_bracket_size=None,
    )
    session.add_all([competition, rule_set])
    session.flush()
    return competition


def _add_participants(session: Session, competition: Competition, count: int) -> list[CompetitionParticipant]:
    participants = [
        CompetitionParticipant(
            id=generate_uuid(),
            competition_id=competition.id,
            club_id=f"club-{index}",
            entry_id=None,
            status="joined",
            seed=index,
            seed_locked=True,
            group_key=None,
            paid_entry_fee_minor=0,
            played=0,
            wins=0,
            draws=0,
            losses=0,
            goals_for=0,
            goals_against=0,
            goal_diff=0,
            points=0,
            advanced=False,
        )
        for index in range(1, count + 1)
    ]
    session.add_all(participants)
    session.flush()
    return participants


def _add_pending_knockout_match(
    session: Session,
    competition: Competition,
    participants: list[CompetitionParticipant],
) -> CompetitionMatch:
    round_entry = CompetitionRound(
        id=generate_uuid(),
        competition_id=competition.id,
        round_number=1,
        stage="knockout",
        group_key=None,
        name=None,
        status=MatchStatus.SCHEDULED.value,
        starts_at=None,
        ends_at=None,
        metadata_json={},
    )
    match = CompetitionMatch(
        id=generate_uuid(),
        competition_id=competition.id,
        round_id=round_entry.id,
        round_number=1,
        stage="knockout",
        group_key=None,
        home_club_id=participants[0].club_id,
        away_club_id=participants[1].club_id,
        scheduled_at=None,
        match_date=None,
        window=None,
        slot_sequence=1,
        status=MatchStatus.SCHEDULED.value,
        home_score=0,
        away_score=0,
        winner_club_id=None,
        decided_by_penalties=False,
        requires_winner=True,
        stats_applied=False,
        metadata_json={},
    )
    playoff = CompetitionPlayoff(
        id=generate_uuid(),
        competition_id=competition.id,
        round_id=round_entry.id,
        slot_index=1,
        home_seed=1,
        away_seed=2,
        match_id=match.id,
        winner_club_id=None,
        status=MatchStatus.SCHEDULED.value,
        metadata_json={},
    )
    session.add_all([round_entry, match, playoff])
    session.flush()
    return match


def _add_completed_league_match(
    session: Session,
    competition: Competition,
    participants: list[CompetitionParticipant],
) -> CompetitionMatch:
    participants[0].played = 1
    participants[0].wins = 1
    participants[0].goals_for = 2
    participants[0].goals_against = 1
    participants[0].goal_diff = 1
    participants[0].points = 3
    participants[1].played = 1
    participants[1].losses = 1
    participants[1].goals_for = 1
    participants[1].goals_against = 2
    participants[1].goal_diff = -1
    participants[1].points = 0
    round_entry = CompetitionRound(
        id=generate_uuid(),
        competition_id=competition.id,
        round_number=1,
        stage="league",
        group_key=None,
        name=None,
        status=MatchStatus.COMPLETED.value,
        starts_at=None,
        ends_at=datetime(2035, 6, 4, tzinfo=timezone.utc),
        metadata_json={},
    )
    match = CompetitionMatch(
        id=generate_uuid(),
        competition_id=competition.id,
        round_id=round_entry.id,
        round_number=1,
        stage="league",
        group_key=None,
        home_club_id=participants[0].club_id,
        away_club_id=participants[1].club_id,
        scheduled_at=datetime(2035, 6, 4, tzinfo=timezone.utc),
        match_date=None,
        window=None,
        slot_sequence=1,
        status=MatchStatus.COMPLETED.value,
        home_score=2,
        away_score=1,
        winner_club_id=participants[0].club_id,
        decided_by_penalties=False,
        requires_winner=False,
        stats_applied=True,
        completed_at=datetime(2035, 6, 4, tzinfo=timezone.utc),
        metadata_json={},
    )
    reward = CompetitionReward(
        id=generate_uuid(),
        competition_id=competition.id,
        reward_pool_id=None,
        participant_id=participants[0].id,
        club_id=participants[0].club_id,
        placement=1,
        reward_type="prize",
        currency="credit",
        amount_minor=123_400,
        status="settled",
        ledger_transaction_id="reward-ledger-1",
        settled_at=datetime(2035, 6, 5, tzinfo=timezone.utc),
        metadata_json={},
    )
    session.add_all([round_entry, match, reward])
    session.flush()
    return match


def _add_playoff_slot_without_match(
    session: Session,
    competition: Competition,
) -> CompetitionPlayoff:
    round_entry = CompetitionRound(
        id=generate_uuid(),
        competition_id=competition.id,
        round_number=1,
        stage="knockout",
        group_key=None,
        name="Final",
        status=MatchStatus.SCHEDULED.value,
        starts_at=None,
        ends_at=None,
        metadata_json={},
    )
    playoff = CompetitionPlayoff(
        id=generate_uuid(),
        competition_id=competition.id,
        round_id=round_entry.id,
        slot_index=1,
        home_seed=1,
        away_seed=2,
        match_id=None,
        winner_club_id=None,
        status=MatchStatus.SCHEDULED.value,
        metadata_json={},
    )
    session.add_all([round_entry, playoff])
    session.flush()
    return playoff


def test_prelaunch_contracts_are_explicit_and_do_not_return_placeholder_rows(isolated_session: Session) -> None:
    competition = _add_competition(isolated_session, name="Contract Prelaunch", format=CompetitionFormat.LEAGUE.value)
    service = CompetitionOrchestrator(isolated_session)

    fixtures = service.fixtures_contract(competition.id)
    standings = service.standings_contract(competition.id)
    bracket = service.bracket_contract(competition.id)

    assert fixtures is not None
    assert fixtures.status == "blocked"
    assert fixtures.state.blocked_reason == "minimum_participants_not_met"
    assert fixtures.items == ()

    assert standings is not None
    assert standings.status == "empty"
    assert standings.items == ()

    assert bracket is not None
    assert bracket.status == "empty"
    assert bracket.state.reason == "competition_has_no_bracket"
    assert bracket.rounds == ()


def test_live_contracts_degrade_when_authoritative_source_rows_are_missing(isolated_session: Session) -> None:
    competition = _add_competition(
        isolated_session,
        name="Contract Missing Rows",
        format=CompetitionFormat.CUP.value,
        status=CompetitionStatus.LIVE.value,
        stage="knockout",
    )
    _add_participants(isolated_session, competition, 2)
    service = CompetitionOrchestrator(isolated_session)

    fixtures = service.fixtures_contract(competition.id)
    standings = service.standings_contract(competition.id)
    bracket = service.bracket_contract(competition.id)

    assert fixtures is not None
    assert fixtures.status == "degraded"
    assert "fixtures" in fixtures.state.missing_data
    assert fixtures.items == ()

    assert standings is not None
    assert standings.status == "synced"
    assert standings.state.missing_data == ()
    assert len(standings.items) == 2

    assert bracket is not None
    assert bracket.status == "degraded"
    assert "bracket" in bracket.state.missing_data
    assert bracket.rounds == ()


def test_pending_bracket_match_does_not_publish_fake_zero_score(isolated_session: Session) -> None:
    competition = _add_competition(
        isolated_session,
        name="Contract Cup Bracket",
        format=CompetitionFormat.CUP.value,
        status=CompetitionStatus.LIVE.value,
        stage="knockout",
    )
    participants = _add_participants(isolated_session, competition, 2)
    _add_pending_knockout_match(isolated_session, competition, participants)
    service = CompetitionOrchestrator(isolated_session)

    bracket = service.bracket_contract(competition.id)
    fixtures = service.fixtures_contract(competition.id)

    assert bracket is not None
    assert bracket.status == "synced"
    assert bracket.lifecycle.bracket_published is True
    match = bracket.rounds[0].matches[0]
    assert match.status == MatchStatus.SCHEDULED.value
    assert match.home_score is None
    assert match.away_score is None
    assert match.home.score is None
    assert match.away.score is None

    assert fixtures is not None
    assert fixtures.status == "synced"
    assert fixtures.score_status == "pending_results"
    assert fixtures.items[0].home_score is None
    assert fixtures.items[0].away_score is None


def test_persisted_fixture_standing_and_reward_rows_sync_without_missing_dependencies(
    isolated_session: Session,
) -> None:
    competition = _add_competition(
        isolated_session,
        name="Contract Persisted League",
        format=CompetitionFormat.LEAGUE.value,
        status=CompetitionStatus.COMPLETED.value,
        stage="complete",
    )
    participants = _add_participants(isolated_session, competition, 2)
    _add_completed_league_match(isolated_session, competition, participants)
    service = CompetitionOrchestrator(isolated_session)

    fixtures = service.fixtures_contract(competition.id)
    standings = service.standings_contract(competition.id)

    assert fixtures is not None
    assert fixtures.status == "synced"
    assert fixtures.state.missing_data == ()
    assert fixtures.authoritative_scores is True
    assert fixtures.items[0].home_score == 2
    assert fixtures.items[0].away_score == 1

    assert standings is not None
    assert standings.status == "synced"
    assert standings.state.missing_data == ()
    assert standings.standings_complete is True
    assert [item.club_id for item in standings.items] == [participants[0].club_id, participants[1].club_id]
    assert standings.items[0].points == 3
    assert standings.items[0].reward_amount == Decimal("12.3400")
    assert standings.items[0].reward_currency == "credit"
    assert standings.items[0].reward_status == "settled"


def test_persisted_playoff_slot_without_match_publishes_bracket_without_fake_scores(
    isolated_session: Session,
) -> None:
    competition = _add_competition(
        isolated_session,
        name="Contract Persisted Playoff Slot",
        format=CompetitionFormat.CUP.value,
        status=CompetitionStatus.LIVE.value,
        stage="knockout",
    )
    _add_participants(isolated_session, competition, 2)
    playoff = _add_playoff_slot_without_match(isolated_session, competition)
    service = CompetitionOrchestrator(isolated_session)

    bracket = service.bracket_contract(competition.id)

    assert bracket is not None
    assert bracket.status == "synced"
    assert bracket.state.missing_data == ()
    match = bracket.rounds[0].matches[0]
    assert match.id == playoff.id
    assert match.live_match_id is None
    assert match.home.club_id == "club-1"
    assert match.away.club_id == "club-2"
    assert match.home_score is None
    assert match.away_score is None
