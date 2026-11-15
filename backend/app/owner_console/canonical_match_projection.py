from __future__ import annotations

"""Canonical CompetitionMatch -> living-club institutional consequence projections.

The module reads only completed canonical match rows, persisted events and replay
statistics. It does not invoke the match simulator or create legacy OwnerMatch rows.
"""

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.common.enums.match_status import MatchStatus
from app.models.club_profile import ClubProfile
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent
from app.owner_console import living_club_world, living_institution
from app.owner_console.models import OwnerClubEvent, OwnerClubState

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CanonicalInstitutionalMatch:
    id: str
    home_club_id: str
    away_club_id: str
    home_name: str
    away_name: str
    round_number: int
    events_json: list[dict[str, Any]]
    narrative_json: dict[str, Any]
    completed_at: datetime | None


@dataclass(slots=True)
class CanonicalInstitutionalCompetition:
    id: str
    name: str
    format: str


def _has_player_stats(value: Any) -> bool:
    return isinstance(value, list) and any(isinstance(row, dict) for row in value)


def _replay_summary(match: CompetitionMatch) -> dict[str, Any]:
    metadata = dict(match.metadata_json or {})
    summary = metadata.get("simulation_summary")
    if isinstance(summary, dict) and _has_player_stats(summary.get("player_stats")):
        return summary
    replay = metadata.get("replay_payload")
    replay_summary = replay.get("summary") if isinstance(replay, dict) else None
    if isinstance(replay_summary, dict) and _has_player_stats(replay_summary.get("player_stats")):
        return dict(replay_summary)
    return dict(summary) if isinstance(summary, dict) else {}


def normalize_authoritative_appearances(
    player_stats: list[dict[str, Any]] | None,
    club_id: str,
) -> list[dict[str, Any]]:
    """A starter or substitute appears only when the replay records positive minutes."""
    output: list[dict[str, Any]] = []
    for raw in player_stats or []:
        if not isinstance(raw, dict) or str(raw.get("team_id") or "") != str(club_id):
            continue
        minutes = max(0, int(raw.get("minutes_played") or 0))
        if minutes <= 0:
            continue
        output.append(
            {
                "player_id": str(raw.get("player_id") or ""),
                "player_name": str(raw.get("player_name") or ""),
                "team_id": str(raw.get("team_id") or ""),
                "started": bool(raw.get("started")),
                "minutes_played": minutes,
                "substituted_in_minute": raw.get("substituted_in_minute"),
                "substituted_out_minute": raw.get("substituted_out_minute"),
                "goals": max(0, int(raw.get("goals") or 0)),
                "assists": max(0, int(raw.get("assists") or 0)),
                "yellow_cards": max(0, int(raw.get("yellow_cards") or 0)),
                "red_card": bool(raw.get("red_card")),
            }
        )
    return output


def _club_name(session: Session, club_id: str) -> str:
    row = session.get(ClubProfile, club_id)
    return str(row.club_name) if row is not None else str(club_id)


def _prior_head_to_head(session: Session, match: CompetitionMatch, club_id: str, opponent_id: str) -> dict[str, int]:
    rows = list(
        session.scalars(
            select(CompetitionMatch).where(
                CompetitionMatch.status == MatchStatus.COMPLETED.value,
                CompetitionMatch.id != match.id,
                or_(
                    and_(CompetitionMatch.home_club_id == club_id, CompetitionMatch.away_club_id == opponent_id),
                    and_(CompetitionMatch.home_club_id == opponent_id, CompetitionMatch.away_club_id == club_id),
                ),
            )
        ).all()
    )
    summary = {
        "matches_played": 0,
        "significant_encounters": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
    }
    for previous in rows:
        home = previous.home_club_id == club_id
        gf = int(previous.home_score or 0) if home else int(previous.away_score or 0)
        ga = int(previous.away_score or 0) if home else int(previous.home_score or 0)
        summary["matches_played"] += 1
        summary["goals_for"] += gf
        summary["goals_against"] += ga
        if (
            bool(previous.requires_winner)
            or str(previous.stage or "").lower() in {"knockout", "final", "semi_final", "quarter_final"}
            or abs(gf - ga) >= 3
            or gf + ga >= 5
        ):
            summary["significant_encounters"] += 1
        if gf > ga:
            summary["wins"] += 1
        elif gf == ga:
            summary["draws"] += 1
        else:
            summary["losses"] += 1
    return summary


def _event_dicts(rows: list[CompetitionMatchEvent], home_id: str, away_id: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        metadata = dict(row.metadata_json or {})
        side = "home" if row.club_id == home_id else "away" if row.club_id == away_id else None
        output.append(
            {
                "id": str(row.id),
                "event_id": str(row.id),
                "type": str(row.event_type or "").lower(),
                "team": side,
                "team_id": row.club_id,
                "player_id": row.player_id,
                "secondary_player_id": row.secondary_player_id,
                "minute": row.minute,
                "added_time": row.added_time,
                "card_type": row.card_type,
                "text": str(metadata.get("commentary") or metadata.get("description") or row.event_type),
                "metadata": metadata,
                "metadata_json": metadata,
            }
        )
    return output


def _manager_context(context: dict[str, Any], side_key: str) -> tuple[dict[str, Any], bool]:
    item = context.get(side_key)
    if not isinstance(item, dict):
        return {}, False
    manager = item.get("manager")
    return (dict(manager) if isinstance(manager, dict) else {}), bool(item.get("manager_snapshot_supplied"))


def _source_event(
    session: Session,
    match: CompetitionMatch,
    competition: UserCompetition,
    anchor: OwnerClubState,
) -> OwnerClubEvent:
    projection_key = f"club:{anchor.club_id}:institutional_consequences"
    participants = [
        {
            "participant_type": "club",
            "club_id": str(match.home_club_id),
            "club_name": _club_name(session, match.home_club_id),
            "side": "home",
        },
        {
            "participant_type": "club",
            "club_id": str(match.away_club_id),
            "club_name": _club_name(session, match.away_club_id),
            "side": "away",
        },
    ]
    event, _ = living_club_world.emit_canonical_club_event(
        session,
        anchor_club_id=anchor.club_id,
        match_id=match.id,
        competition_id=match.competition_id,
        world_day=max(1, int(anchor.world_day or 1)),
        title=f"{competition.name}: {_club_name(session, match.home_club_id)} {int(match.home_score or 0)}-{int(match.away_score or 0)} {_club_name(session, match.away_club_id)}",
        description=(
            f"Canonical CompetitionMatch {match.id} completed in {competition.name}, "
            f"Round {match.round_number}. Persisted events and replay statistics are authoritative."
        ),
        participants=participants,
        required_projections=[projection_key],
    )
    return event


def _project_one_club(
    session: Session,
    *,
    source_event: OwnerClubEvent,
    match: CompetitionMatch,
    competition: UserCompetition,
    match_view: CanonicalInstitutionalMatch,
    competition_view: CanonicalInstitutionalCompetition,
    state: OwnerClubState,
    side_key: str,
    opponent_id: str,
    opponent_name: str,
    player_stats: list[dict[str, Any]],
    events: list[dict[str, Any]],
    context: dict[str, Any],
) -> dict[str, Any]:
    is_home = side_key == "home"
    gf = int(match.home_score or 0) if is_home else int(match.away_score or 0)
    ga = int(match.away_score or 0) if is_home else int(match.home_score or 0)
    projection_key = f"club:{state.club_id}:institutional_consequences"
    statuses = dict((source_event.consequences_json or {}).get("projection_status") or {})
    previous = statuses.get(projection_key)
    if isinstance(previous, dict) and previous.get("status") == "complete":
        return {"club_id": state.club_id, "status": "already_projected"}

    side_context = context.get(side_key) if isinstance(context.get(side_key), dict) else {}
    world_day = max(1, int(side_context.get("world_day") or state.world_day or 1))
    appearances = normalize_authoritative_appearances(player_stats, state.club_id)
    manager, manager_supplied = _manager_context(context, side_key)
    side = {
        "state": state,
        "world_day": world_day,
        "manager_snapshot": manager,
        "manager_snapshot_supplied": manager_supplied,
        "appearances": appearances,
        "xi": [item["player_id"] for item in appearances if item["started"]],
        "prior_head_to_head": _prior_head_to_head(session, match, state.club_id, opponent_id),
        "atmosphere_snapshot": side_context.get("atmosphere"),
        "projection_event_id": source_event.id,
        "source_event_id": source_event.id,
    }
    try:
        with session.begin_nested():
            impact = living_institution.record_match_institutional_impact(
                session, match_view, competition_view, side, {"state": None}, is_home, gf, ga
            )
            # Private HOYD intelligence is persisted as a staff-only club event.
            # It is separate from public academy debut coverage and does not expose
            # confidential academy assessment details.
            for debut in impact.get("debutant_records") or []:
                player_id = str(debut.get("player_id") or "")
                player_name = str(debut.get("player_name") or "Academy graduate")
                living_club_world.create_club_event(
                    session,
                    club_id=state.club_id,
                    category="academy",
                    event_type="academy_first_team_debut",
                    severity="important",
                    title=f"Academy Debut: {player_name}",
                    description=(
                        f"{player_name} made an actual first-team appearance against {opponent_name} "
                        f"in {competition.name}, playing {int(debut.get('minutes_played') or 0)} minutes."
                    ),
                    world_day=world_day,
                    source_type="canonical_match",
                    source_id=match.id,
                    participants=[
                        {
                            "participant_type": "staff_role",
                            "role_key": "head_of_youth_development",
                        },
                        {
                            "participant_type": "player",
                            "player_id": str(debut.get("canonical_player_id") or player_id),
                            "player_name": player_name,
                        },
                    ],
                    consequences={
                        "canonical_match_id": match.id,
                        "source_event_id": source_event.id,
                        "minutes_played": int(debut.get("minutes_played") or 0),
                        "goals": int(debut.get("goals") or 0),
                        "assists": int(debut.get("assists") or 0),
                        "confidentiality": "staff_intelligence",
                    },
                    idempotency_key=f"cma:{match.id}:{state.club_id}:{player_id}",
                    status="active",
                )
            living_club_world.record_canonical_projection(
                session,
                source_event,
                projection_key,
                {
                    "result": "win" if gf > ga else "draw" if gf == ga else "loss",
                    "goals_for": gf,
                    "goals_against": ga,
                    "supporter_sentiment": impact.get("supporter_sentiment"),
                    "rivalry_tier": impact.get("rivalry_tier"),
                    "debutants": impact.get("debutants") or [],
                    "manager_name": impact.get("manager_name"),
                },
            )
        return {"club_id": state.club_id, "status": "projected", "impact": impact}
    except Exception as exc:
        logger.exception(
            "canonical_match.institutional_projection_failed match_id=%s club_id=%s", match.id, state.club_id
        )
        try:
            session.refresh(source_event)
            consequences = dict(source_event.consequences_json or {})
            statuses = dict(consequences.get("projection_status") or {})
            statuses[projection_key] = {
                "status": "pending",
                "last_error_type": type(exc).__name__,
                "last_error": str(exc)[:240],
            }
            consequences["projection_status"] = statuses
            source_event.consequences_json = consequences
            source_event.status = "active"
            session.flush()
        except Exception:
            logger.exception(
                "canonical_match.projection_failure_marker_failed match_id=%s club_id=%s", match.id, state.club_id
            )
        return {"club_id": state.club_id, "status": "pending_retry", "error": type(exc).__name__}


def project_completed_canonical_match(session: Session, match_id: str) -> dict[str, Any]:
    """Project a completed canonical match; this function never calls the simulator."""
    match = session.scalar(
        select(CompetitionMatch)
        .where(CompetitionMatch.id == str(match_id))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if match is None:
        return {"match_id": str(match_id), "status": "not_found"}
    if match.status != MatchStatus.COMPLETED.value or match.completed_at is None:
        return {"match_id": str(match_id), "status": "not_completed"}
    competition = session.get(UserCompetition, match.competition_id)
    if competition is None:
        return {"match_id": match.id, "status": "competition_not_found"}
    states = {
        str(row.club_id): row
        for row in session.scalars(
            select(OwnerClubState).where(OwnerClubState.club_id.in_({str(match.home_club_id), str(match.away_club_id)}))
        ).all()
    }
    if not states:
        return {"match_id": match.id, "status": "no_living_clubs"}

    summary = _replay_summary(match)
    raw_stats = summary.get("player_stats")
    if not _has_player_stats(raw_stats):
        # Persist one independently retryable source event per participating
        # Living Club before deferring. This prevents a missing replay summary
        # from falling out of the bounded recent-match backfill window.
        awaiting: dict[str, Any] = {}
        for side_key, club_id in (
            ("home", str(match.home_club_id)),
            ("away", str(match.away_club_id)),
        ):
            state = states.get(club_id)
            if state is None:
                continue
            projection_key = f"club:{club_id}:institutional_consequences"
            source_event = _source_event(session, match, competition, state)
            consequences = dict(source_event.consequences_json or {})
            statuses = dict(consequences.get("projection_status") or {})
            current = statuses.get(projection_key)
            if not (isinstance(current, dict) and current.get("status") == "complete"):
                statuses[projection_key] = {
                    "status": "pending",
                    "reason": "awaiting_replay_statistics",
                }
                consequences["projection_status"] = statuses
                source_event.consequences_json = consequences
                source_event.status = "active"
                source_event.resolved_at = None
            awaiting[side_key] = {
                "club_id": club_id,
                "status": "awaiting_replay_statistics",
            }
        logger.warning(
            "canonical_match_projection.awaiting_player_stats match_id=%s",
            match.id,
        )
        return {
            "match_id": match.id,
            "status": "awaiting_replay_statistics",
            "clubs": awaiting,
        }
    player_stats = [dict(row) for row in raw_stats if isinstance(row, dict)]
    event_rows = list(
        session.scalars(
            select(CompetitionMatchEvent)
            .where(CompetitionMatchEvent.match_id == match.id)
            .order_by(
                CompetitionMatchEvent.minute.asc().nullsfirst(),
                CompetitionMatchEvent.created_at.asc(),
                CompetitionMatchEvent.id.asc(),
            )
        ).all()
    )
    events = _event_dicts(event_rows, match.home_club_id, match.away_club_id)
    metadata = dict(match.metadata_json or {})
    raw_context = metadata.get("institutional_match_context")
    context = dict(raw_context) if isinstance(raw_context, dict) else {}
    home_name = _club_name(session, match.home_club_id)
    away_name = _club_name(session, match.away_club_id)
    match_view = CanonicalInstitutionalMatch(
        id=match.id,
        home_club_id=match.home_club_id,
        away_club_id=match.away_club_id,
        home_name=home_name,
        away_name=away_name,
        round_number=int(match.round_number),
        events_json=events,
        narrative_json={},
        completed_at=match.completed_at,
    )
    is_knockout = bool(
        match.requires_winner
        or str(match.stage or "").lower() in {"knockout", "final", "semi_final", "quarter_final"}
        or str(competition.format or "").lower() in {"cup", "knockout"}
    )
    competition_view = CanonicalInstitutionalCompetition(
        id=competition.id, name=competition.name, format="knockout" if is_knockout else "league"
    )
    outcomes: dict[str, Any] = {"match_id": match.id, "status": "projected", "clubs": {}}
    if str(match.home_club_id) in states:
        home_source_event = _source_event(session, match, competition, states[str(match.home_club_id)])
        outcomes["clubs"]["home"] = _project_one_club(
            session,
            source_event=home_source_event,
            match=match,
            competition=competition,
            match_view=match_view,
            competition_view=competition_view,
            state=states[str(match.home_club_id)],
            side_key="home",
            opponent_id=str(match.away_club_id),
            opponent_name=away_name,
            player_stats=player_stats,
            events=events,
            context=context,
        )
    if str(match.away_club_id) in states:
        away_source_event = _source_event(session, match, competition, states[str(match.away_club_id)])
        outcomes["clubs"]["away"] = _project_one_club(
            session,
            source_event=away_source_event,
            match=match,
            competition=competition,
            match_view=match_view,
            competition_view=competition_view,
            state=states[str(match.away_club_id)],
            side_key="away",
            opponent_id=str(match.home_club_id),
            opponent_name=home_name,
            player_stats=player_stats,
            events=events,
            context=context,
        )
    if any(item.get("status") == "pending_retry" for item in outcomes["clubs"].values()):
        outcomes["status"] = "pending_retry"
    elif any(item.get("status") == "awaiting_replay_statistics" for item in outcomes["clubs"].values()):
        outcomes["status"] = "awaiting_replay_statistics"
    return outcomes


def reconcile_pending_canonical_match_projections(session: Session, *, limit: int = 100) -> dict[str, int]:
    """Retry durable pending events and backfill recently completed fixtures."""
    pending_ids = list(
        session.scalars(
            select(OwnerClubEvent.source_id)
            .where(
                OwnerClubEvent.source_type == "canonical_match",
                OwnerClubEvent.event_type == "canonical_match_completed",
                OwnerClubEvent.status != "resolved",
                OwnerClubEvent.source_id.is_not(None),
            )
            .order_by(OwnerClubEvent.created_at.asc())
            .limit(max(1, int(limit)))
        ).all()
    )
    recent_ids = list(
        session.scalars(
            select(CompetitionMatch.id)
            .where(CompetitionMatch.status == MatchStatus.COMPLETED.value)
            .order_by(CompetitionMatch.completed_at.desc().nullslast())
            .limit(max(1, int(limit)))
        ).all()
    )
    match_ids = list(dict.fromkeys(str(value) for value in pending_ids + recent_ids if value))
    projected = pending = considered = 0
    for match_id in match_ids:
        try:
            # Isolate failures outside the per-club savepoints too (for example,
            # source-event creation/flush errors) so the owner-world transaction
            # remains usable for later clubs and work in this tick.
            with session.begin_nested():
                result = project_completed_canonical_match(session, match_id)
        except Exception:
            logger.exception("canonical_match.reconciliation_attempt_failed match_id=%s", match_id)
            pending += 1
            continue
        if result.get("status") in {"projected", "pending_retry", "awaiting_replay_statistics"}:
            considered += 1
        club_results = result.get("clubs") or {}
        if result.get("status") in {"pending_retry", "awaiting_replay_statistics"} or any(
            item.get("status") == "pending_retry" for item in club_results.values()
        ):
            pending += 1
        elif club_results:
            projected += 1
    session.flush()
    return {"matches_considered": considered, "matches_projected": projected, "matches_pending_retry": pending}
