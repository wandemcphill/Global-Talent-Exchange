from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.config.competition_constants import (
    WORLD_SUPER_CUP_DIRECT_SLOTS,
    WORLD_SUPER_CUP_PLAYOFF_TEAMS,
    WORLD_SUPER_CUP_PLAYOFF_WINNERS,
)
from app.db import get_session
from app.models.user import User
from app.world_super_cup.api.schemas import (
    CoefficientEntryView,
    GroupMatchView,
    GroupStageTableView,
    GroupStandingView,
    GroupTableView,
    GroupView,
    KnockoutBracketView,
    KnockoutRoundView,
    PlayoffDrawView,
    PlayoffMatchView,
    QualificationExplanationView,
    QualifiedClubView,
    TournamentCountdownView,
    TrophyCeremonyView,
    WorldSuperCupFixturesView,
    WorldSuperCupFixtureView,
    WorldSuperCupSettlementRequest,
    WorldSuperCupSettlementView,
)
from app.world_super_cup.models import GroupMatch, KnockoutMatch, PlayoffMatch, WorldSuperCupFixtureSnapshot
from app.world_super_cup.services.persistence import WorldSuperCupAuthorityError, WorldSuperCupPersistenceService
from app.world_super_cup.services.tournament import WorldSuperCupService

router = APIRouter(prefix="/world-super-cup", tags=["world-super-cup"])

_service = WorldSuperCupService()


@dataclass(frozen=True, slots=True)
class _AuthorityPlanRead:
    plan: object
    markers: dict[str, object]


@dataclass(frozen=True, slots=True)
class _AuthorityFixtureRead:
    fixtures: tuple[WorldSuperCupFixtureSnapshot, ...]
    markers: dict[str, object]


def _is_protected_environment(request: Request) -> bool:
    settings = getattr(getattr(request, "app", None).state, "settings", None)
    app_env = str(getattr(settings, "app_env", "") or "").strip().lower()
    return app_env in {"production", "prod", "staging"}


def _session_factory(request: Request):
    return getattr(getattr(request, "app", None).state, "session_factory", None)


def _require_demo_tournament_enabled(request: Request) -> None:
    if _is_protected_environment(request):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "World Super Cup demo projections are disabled in protected environments. "
                "Mount a Competition OS-backed tournament before exposing this route."
            ),
        )
    demo_enabled = (os.getenv("GTE_ENABLE_WORLD_SUPER_CUP_DEMO") or "").strip().lower()
    if demo_enabled not in {"1", "true", "yes", "on"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "World Super Cup demo projections are disabled. "
                "Mount a Competition OS-backed tournament before exposing this route."
            ),
        )


def _authority_markers(tournament) -> dict[str, object]:
    if tournament is None:
        return {
            "source_of_truth": "local_projection",
            "authority": "local_projection",
            "no_demo_data": False,
            "tournament_id": None,
            "competition_id": None,
        }
    metadata = dict(getattr(tournament, "metadata_json", None) or {})
    source = str(metadata.get("source") or "").strip()
    competition_id = getattr(tournament, "competition_id", None)
    competition_backed = bool(competition_id) or source == "competition_os"
    return {
        "source_of_truth": "persisted_backend_authority",
        "authority": "competition_os" if competition_backed else "server_seed",
        "no_demo_data": competition_backed,
        "tournament_id": getattr(tournament, "id", None),
        "competition_id": competition_id,
    }


def _projection_markers(plan) -> dict[str, object]:
    return {
        "source_of_truth": "local_projection",
        "authority": "local_projection",
        "no_demo_data": False,
        "tournament_id": WorldSuperCupPersistenceService.tournament_id_for_plan(plan),
        "competition_id": None,
    }


def _with_markers(view, markers: dict[str, object]):
    return view.model_copy(update=markers)


def _authority_plan(
    request: Request,
    reference_at: datetime | None,
    tournament_id: str | None = None,
) -> _AuthorityPlanRead:
    session_factory = _session_factory(request)
    if session_factory is not None:
        with session_factory() as session:
            persistence = WorldSuperCupPersistenceService(session)
            plan = persistence.read_plan(tournament_id, reference_at=reference_at)
            if plan is not None:
                return _AuthorityPlanRead(
                    plan=plan,
                    markers=_authority_markers(persistence.get_tournament(tournament_id)),
                )
            if _is_protected_environment(request):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="No persisted World Super Cup tournament is mounted for this environment.",
                )
            seeded = _service.build_demo_tournament(reference_at)
            tournament = persistence.persist_plan(
                seeded,
                tournament_id=tournament_id,
                source="non_protected_server_seed",
            )
            session.commit()
            persisted = persistence.read_plan(tournament.id, reference_at=reference_at)
            return _AuthorityPlanRead(
                plan=persisted or seeded,
                markers=_authority_markers(tournament),
            )

    _require_demo_tournament_enabled(request)
    plan = _service.build_demo_tournament(reference_at)
    return _AuthorityPlanRead(plan=plan, markers=_projection_markers(plan))


def _authority_fixtures(
    request: Request,
    reference_at: datetime | None,
    tournament_id: str | None = None,
) -> _AuthorityFixtureRead:
    session_factory = _session_factory(request)
    if session_factory is not None:
        with session_factory() as session:
            persistence = WorldSuperCupPersistenceService(session)
            fixtures = persistence.fixtures(tournament_id)
            if fixtures:
                return _AuthorityFixtureRead(
                    fixtures=fixtures,
                    markers=_authority_markers(persistence.get_tournament(tournament_id)),
                )
            if _is_protected_environment(request):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="No persisted World Super Cup fixtures are mounted for this environment.",
                )
            seeded = _service.build_demo_tournament(reference_at)
            tournament = persistence.persist_plan(
                seeded,
                tournament_id=tournament_id,
                source="non_protected_server_seed",
            )
            session.commit()
            return _AuthorityFixtureRead(
                fixtures=persistence.fixtures(tournament.id),
                markers=_authority_markers(tournament),
            )

    _require_demo_tournament_enabled(request)
    plan = _service.build_demo_tournament(reference_at)
    return _AuthorityFixtureRead(
        fixtures=_fixture_snapshots_from_plan(plan),
        markers=_projection_markers(plan),
    )


def _fixture_snapshots_from_plan(plan) -> tuple[WorldSuperCupFixtureSnapshot, ...]:
    tournament_id = WorldSuperCupPersistenceService.tournament_id_for_plan(plan)
    snapshots: list[WorldSuperCupFixtureSnapshot] = []
    for match in plan.qualification.playoff_matches:
        snapshots.append(_fixture_snapshot_from_match(tournament_id, match, stage="playoff", status_value="completed"))
    for match in plan.group_stage.matches:
        snapshots.append(_fixture_snapshot_from_match(tournament_id, match, stage="group", status_value="completed"))
    for round_view in plan.knockout.rounds:
        for match in round_view.matches:
            snapshots.append(
                _fixture_snapshot_from_match(tournament_id, match, stage="knockout", status_value="completed")
            )
    return tuple(snapshots)


def _fixture_snapshot_from_match(
    tournament_id: str,
    match: PlayoffMatch | GroupMatch | KnockoutMatch,
    *,
    stage: str,
    status_value: str,
) -> WorldSuperCupFixtureSnapshot:
    return WorldSuperCupFixtureSnapshot(
        tournament_id=tournament_id,
        fixture_id=match.match_id,
        stage=stage,
        round_name=getattr(match, "round_name", None) or getattr(match, "stage", None),
        group_name=getattr(match, "group_name", None),
        matchday=getattr(match, "matchday", None),
        home_club=match.home_club,
        away_club=match.away_club,
        kickoff_at=match.kickoff_at,
        venue=match.venue,
        status=status_value,
        home_score=getattr(match, "home_score", None),
        away_score=getattr(match, "away_score", None),
        winner=getattr(match, "winner", None),
        decided_by=getattr(match, "decided_by", None),
    )


def _build_tables(rows: tuple[object, ...]) -> list[GroupTableView]:
    grouped: dict[str, list[GroupStandingView]] = {}
    for row in rows:
        standing = GroupStandingView.model_validate(row)
        grouped.setdefault(standing.group_name, []).append(standing)
    return [
        GroupTableView(
            group_name=group_name,
            standings=sorted(standings, key=lambda standing: standing.position),
        )
        for group_name, standings in sorted(grouped.items())
    ]


@router.get("/qualification/explanation", response_model=QualificationExplanationView)
def get_qualification_explanation(
    request: Request,
    reference_at: datetime | None = None,
    tournament_id: str | None = None,
) -> QualificationExplanationView:
    read = _authority_plan(request, reference_at, tournament_id)
    plan = read.plan
    qualification = plan.qualification
    return QualificationExplanationView(
        **read.markers,
        seasons_considered=qualification.seasons_considered,
        direct_slots=WORLD_SUPER_CUP_DIRECT_SLOTS,
        playoff_slots=WORLD_SUPER_CUP_PLAYOFF_TEAMS,
        playoff_winner_slots=WORLD_SUPER_CUP_PLAYOFF_WINNERS,
        coefficient_table=[CoefficientEntryView.model_validate(entry) for entry in qualification.coefficient_table],
        direct_qualifiers=[QualifiedClubView.model_validate(club) for club in qualification.direct_qualifiers],
        playoff_qualifiers=[QualifiedClubView.model_validate(club) for club in qualification.playoff_qualifiers],
    )


@router.get("/playoff/draw", response_model=PlayoffDrawView)
def get_playoff_draw(
    request: Request,
    reference_at: datetime | None = None,
    tournament_id: str | None = None,
) -> PlayoffDrawView:
    read = _authority_plan(request, reference_at, tournament_id)
    plan = read.plan
    qualification = plan.qualification
    return PlayoffDrawView(
        **read.markers,
        matches=[PlayoffMatchView.model_validate(match) for match in qualification.playoff_matches],
        winners=[QualifiedClubView.model_validate(club) for club in qualification.playoff_winners],
    )


@router.get("/groups/table", response_model=GroupStageTableView)
def get_group_stage_table(
    request: Request,
    reference_at: datetime | None = None,
    tournament_id: str | None = None,
) -> GroupStageTableView:
    read = _authority_plan(request, reference_at, tournament_id)
    plan = read.plan
    group_stage = plan.group_stage
    return GroupStageTableView(
        **read.markers,
        groups=[GroupView.model_validate(group) for group in group_stage.groups],
        tables=_build_tables(group_stage.tables),
        matches=[GroupMatchView.model_validate(match) for match in group_stage.matches],
        advancing_clubs=[QualifiedClubView.model_validate(club) for club in group_stage.advancing_clubs],
    )


@router.get("/knockout/bracket", response_model=KnockoutBracketView)
def get_knockout_bracket(
    request: Request,
    reference_at: datetime | None = None,
    tournament_id: str | None = None,
) -> KnockoutBracketView:
    read = _authority_plan(request, reference_at, tournament_id)
    plan = read.plan
    knockout = plan.knockout
    return KnockoutBracketView(
        **read.markers,
        rounds=[KnockoutRoundView.model_validate(round_view) for round_view in knockout.rounds],
        champion=QualifiedClubView.model_validate(knockout.champion),
        runner_up=QualifiedClubView.model_validate(knockout.runner_up),
        trophy_ceremony=TrophyCeremonyView.model_validate(knockout.ceremony),
    )


@router.get("/countdown", response_model=TournamentCountdownView)
def get_tournament_countdown(
    request: Request,
    reference_at: datetime | None = None,
    tournament_id: str | None = None,
) -> TournamentCountdownView:
    read = _authority_plan(request, reference_at, tournament_id)
    return _with_markers(TournamentCountdownView.model_validate(read.plan.countdown), read.markers)


@router.get("/fixtures", response_model=WorldSuperCupFixturesView)
def get_fixtures(
    request: Request,
    reference_at: datetime | None = None,
    tournament_id: str | None = None,
) -> WorldSuperCupFixturesView:
    read = _authority_fixtures(request, reference_at, tournament_id)
    return WorldSuperCupFixturesView(
        **read.markers, fixtures=[WorldSuperCupFixtureView.model_validate(fixture) for fixture in read.fixtures]
    )


@router.post("/fixtures/{fixture_id}/settlement", response_model=WorldSuperCupSettlementView)
def settle_fixture_result(
    fixture_id: str,
    payload: WorldSuperCupSettlementRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(get_current_admin),
) -> WorldSuperCupSettlementView:
    persistence = WorldSuperCupPersistenceService(session)
    try:
        result = persistence.settle_fixture(
            fixture_id=fixture_id,
            tournament_id=payload.tournament_id,
            competition_id=payload.competition_id,
            match_id=payload.match_id,
            home_score=payload.home_score,
            away_score=payload.away_score,
            winner_club_id=payload.winner_club_id,
            decided_by=payload.decided_by,
            idempotency_key=payload.idempotency_key,
            completed_at=payload.completed_at,
            metadata=payload.metadata,
        )
    except WorldSuperCupAuthorityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    markers = _authority_markers(persistence.get_tournament(result.tournament_id))
    session.commit()
    return _with_markers(WorldSuperCupSettlementView.model_validate(result), markers)
