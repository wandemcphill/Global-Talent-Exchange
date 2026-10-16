from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session, sessionmaker

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.replay_visibility import ReplayVisibility
from app.common.schemas.competition import ScheduledFixture
from app.competition_engine.match_dispatcher import MatchDispatcher
from app.competition_engine.queue_contracts import DurableQueuePublisher
from app.core.event_backbone import defer_event_publish_until_commit
from app.core.events import DomainEvent, EventPublisher
from app.matches.schemas import MatchStartRequest
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_round import CompetitionRound


@dataclass(slots=True)
class LocalMatchCommandBridge:
    session_factory: sessionmaker[Session]
    event_publisher: EventPublisher
    producer_name: str = "match-command-bridge"

    def handle_event(self, event: DomainEvent) -> None:
        if event.name != "orchestrator.command.match.start":
            return

        request = _request_from_event(event)
        with self.session_factory() as session:
            match = session.get(CompetitionMatch, request.match_id)
            competition_id = request.competition_id or _optional_text(getattr(match, "competition_id", None))
            round_id = request.round_id or _optional_text(getattr(match, "round_id", None))
            round_record = session.get(CompetitionRound, round_id) if round_id is not None else None
            competition = session.get(Competition, competition_id) if competition_id is not None else None

            fixture = _build_fixture(
                request=request,
                match=match,
                competition=competition,
                round_record=round_record,
            )
            scheduled_start = _resolve_scheduled_start(request=request, match=match, fixture=fixture)
            competition_name = _competition_name(competition=competition, fixture=fixture)
            stage_name = fixture.stage_name or _stage_name(round_record=round_record, fixture=fixture)
            is_final = _is_final(stage_name)

            defer_event_publish_until_commit(
                session,
                publisher=self.event_publisher,
                event=_scheduled_event(
                    fixture=fixture,
                    competition_name=competition_name,
                    scheduled_start=scheduled_start,
                    stage_name=stage_name,
                    is_final=is_final,
                ),
            )

            dispatcher = MatchDispatcher(
                queue_publisher=DurableQueuePublisher(
                    session=session,
                    event_publisher=self.event_publisher,
                    producer_name=self.producer_name,
                )
            )
            dispatcher.dispatch_match_simulation(
                fixture,
                is_final=is_final,
                competition_name=competition_name,
                stage_name=stage_name,
                scheduled_kickoff_at=scheduled_start,
                home_club_name=fixture.home_club_id,
                away_club_name=fixture.away_club_id,
            )
            session.commit()


def _request_from_event(event: DomainEvent) -> MatchStartRequest:
    command = event.payload.get("command")
    if not isinstance(command, dict):
        raise ValueError("Match start command event is missing the nested command payload.")
    payload = command.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Match start command event is missing the request payload.")
    return MatchStartRequest.model_validate(payload)


def _build_fixture(
    *,
    request: MatchStartRequest,
    match: CompetitionMatch | None,
    competition: Competition | None,
    round_record: CompetitionRound | None,
) -> ScheduledFixture:
    match_id = request.match_id.strip()
    competition_id = request.competition_id or _optional_text(getattr(match, "competition_id", None))
    round_number = (
        request.round_number or getattr(match, "round_number", None) or getattr(round_record, "round_number", None)
    )
    home_club_id = request.home_club_id or _optional_text(getattr(match, "home_club_id", None))
    away_club_id = request.away_club_id or _optional_text(getattr(match, "away_club_id", None))
    stage_name = (
        _optional_text(request.stage)
        or _optional_text(getattr(match, "stage", None))
        or _optional_text(getattr(round_record, "name", None))
        or _optional_text(getattr(round_record, "stage", None))
    )
    match_date = request.match_date or getattr(match, "match_date", None)
    scheduled_at = request.scheduled_at or getattr(match, "scheduled_at", None)
    competition_type = _competition_type(
        competition=competition,
        stage_name=stage_name,
        requires_winner=bool(request.requires_winner),
    )
    resolved_match_date = match_date or _coerce_match_date(scheduled_at) or datetime.now(timezone.utc).date()
    fixture_window = _resolve_fixture_window(
        raw_window=request.window or _optional_text(getattr(match, "window", None)),
        competition_type=competition_type,
        match_date=resolved_match_date,
        scheduled_at=scheduled_at,
    )
    is_cup_match = _is_cup_match(stage_name=stage_name, requires_winner=bool(request.requires_winner))

    missing = [
        name
        for name, value in (
            ("competition_id", competition_id),
            ("round_number", round_number),
            ("home_club_id", home_club_id),
            ("away_club_id", away_club_id),
        )
        if value in {None, ""}
    ]
    if missing:
        raise ValueError(f"Match start command is missing required fields: {', '.join(sorted(missing))}.")

    return ScheduledFixture(
        fixture_id=match_id,
        competition_id=str(competition_id),
        competition_type=competition_type,
        round_number=int(round_number),
        home_club_id=str(home_club_id),
        away_club_id=str(away_club_id),
        match_date=resolved_match_date,
        window=fixture_window,
        slot_sequence=request.slot_sequence or getattr(match, "slot_sequence", None) or 1,
        stage_name=stage_name,
        replay_visibility=ReplayVisibility.COMPETITION,
        is_cup_match=is_cup_match,
        allow_penalties=is_cup_match and bool(request.requires_winner),
    )


def _resolve_scheduled_start(
    *,
    request: MatchStartRequest,
    match: CompetitionMatch | None,
    fixture: ScheduledFixture,
) -> datetime:
    scheduled_at = request.scheduled_at or getattr(match, "scheduled_at", None)
    if scheduled_at is not None:
        return _normalize_timestamp(scheduled_at)
    return fixture.window.kickoff_at(fixture.match_date)


def _competition_type(
    *,
    competition: Competition | None,
    stage_name: str | None,
    requires_winner: bool,
) -> CompetitionType:
    raw_value = _optional_text(getattr(competition, "competition_type", None))
    if raw_value is not None:
        try:
            return CompetitionType(raw_value)
        except ValueError:
            pass
    if _is_cup_match(stage_name=stage_name, requires_winner=requires_winner):
        return CompetitionType.FAST_CUP
    return CompetitionType.LEAGUE


def _resolve_fixture_window(
    *,
    raw_window: str | None,
    competition_type: CompetitionType,
    match_date,
    scheduled_at: datetime | None,
) -> FixtureWindow:
    if raw_window:
        try:
            return FixtureWindow(raw_window)
        except ValueError:
            pass

    if not competition_type.uses_senior_windows:
        return (
            FixtureWindow.ACADEMY_OPEN if competition_type is CompetitionType.ACADEMY else FixtureWindow.FAST_CUP_OPEN
        )

    if scheduled_at is None:
        return FixtureWindow.SENIOR_1

    scheduled_start = _normalize_timestamp(scheduled_at)
    return min(
        FixtureWindow.senior_windows(),
        key=lambda window: abs((window.kickoff_at(match_date, tzinfo=timezone.utc) - scheduled_start).total_seconds()),
    )


def _scheduled_event(
    *,
    fixture: ScheduledFixture,
    competition_name: str,
    scheduled_start: datetime,
    stage_name: str | None,
    is_final: bool,
) -> DomainEvent:
    return DomainEvent(
        name="competition.match.scheduled",
        payload={
            "fixture_id": fixture.fixture_id,
            "resource_id": fixture.fixture_id,
            "scheduled_start": scheduled_start,
            "home_club": {
                "club_id": fixture.home_club_id,
                "club_name": fixture.home_club_id,
            },
            "away_club": {
                "club_id": fixture.away_club_id,
                "club_name": fixture.away_club_id,
            },
            "competition_context": {
                "competition_id": fixture.competition_id,
                "competition_type": fixture.competition_type,
                "competition_name": competition_name,
                "season_id": None,
                "stage_name": stage_name,
                "round_number": fixture.round_number,
                "is_final": is_final,
                "is_cup_match": fixture.is_cup_match,
                "competition_allows_public": True,
                "allow_early_round_public": True,
                "replay_visibility": fixture.replay_visibility,
            },
        },
        aggregate_id=fixture.fixture_id,
        aggregate_type="competition_match",
        producer="match-command-bridge",
        partition_key=fixture.fixture_id,
    )


def _competition_name(*, competition: Competition | None, fixture: ScheduledFixture) -> str:
    return _optional_text(getattr(competition, "name", None)) or fixture.competition_id


def _stage_name(*, round_record: CompetitionRound | None, fixture: ScheduledFixture) -> str | None:
    return (
        _optional_text(getattr(round_record, "name", None))
        or _optional_text(getattr(round_record, "stage", None))
        or fixture.stage_name
    )


def _is_cup_match(*, stage_name: str | None, requires_winner: bool) -> bool:
    if requires_winner:
        return True
    normalized_stage = (stage_name or "").strip().lower()
    return normalized_stage not in {"", "league", "group", "regular"}


def _is_final(stage_name: str | None) -> bool:
    normalized_stage = (stage_name or "").strip().lower()
    return normalized_stage == "final"


def _coerce_match_date(value: datetime | None):
    if value is None:
        return None
    return _normalize_timestamp(value).date()


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    resolved = str(value).strip()
    return resolved or None


__all__ = ["LocalMatchCommandBridge"]
