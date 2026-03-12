from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from backend.app.config.competition_constants import (
    WORLD_SUPER_CUP_DIRECT_SLOTS,
    WORLD_SUPER_CUP_PLAYOFF_TEAMS,
    WORLD_SUPER_CUP_PLAYOFF_WINNERS,
)
from backend.app.world_super_cup.api.schemas import (
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
)
from backend.app.world_super_cup.services.tournament import WorldSuperCupService

router = APIRouter(prefix="/world-super-cup", tags=["world-super-cup"])

_service = WorldSuperCupService()


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
def get_qualification_explanation(reference_at: datetime | None = None) -> QualificationExplanationView:
    plan = _service.build_demo_tournament(reference_at)
    qualification = plan.qualification
    return QualificationExplanationView(
        seasons_considered=qualification.seasons_considered,
        direct_slots=WORLD_SUPER_CUP_DIRECT_SLOTS,
        playoff_slots=WORLD_SUPER_CUP_PLAYOFF_TEAMS,
        playoff_winner_slots=WORLD_SUPER_CUP_PLAYOFF_WINNERS,
        coefficient_table=[CoefficientEntryView.model_validate(entry) for entry in qualification.coefficient_table],
        direct_qualifiers=[QualifiedClubView.model_validate(club) for club in qualification.direct_qualifiers],
        playoff_qualifiers=[QualifiedClubView.model_validate(club) for club in qualification.playoff_qualifiers],
    )


@router.get("/playoff/draw", response_model=PlayoffDrawView)
def get_playoff_draw(reference_at: datetime | None = None) -> PlayoffDrawView:
    plan = _service.build_demo_tournament(reference_at)
    qualification = plan.qualification
    return PlayoffDrawView(
        matches=[PlayoffMatchView.model_validate(match) for match in qualification.playoff_matches],
        winners=[QualifiedClubView.model_validate(club) for club in qualification.playoff_winners],
    )


@router.get("/groups/table", response_model=GroupStageTableView)
def get_group_stage_table(reference_at: datetime | None = None) -> GroupStageTableView:
    plan = _service.build_demo_tournament(reference_at)
    group_stage = plan.group_stage
    return GroupStageTableView(
        groups=[GroupView.model_validate(group) for group in group_stage.groups],
        tables=_build_tables(group_stage.tables),
        matches=[GroupMatchView.model_validate(match) for match in group_stage.matches],
        advancing_clubs=[QualifiedClubView.model_validate(club) for club in group_stage.advancing_clubs],
    )


@router.get("/knockout/bracket", response_model=KnockoutBracketView)
def get_knockout_bracket(reference_at: datetime | None = None) -> KnockoutBracketView:
    plan = _service.build_demo_tournament(reference_at)
    knockout = plan.knockout
    return KnockoutBracketView(
        rounds=[KnockoutRoundView.model_validate(round_view) for round_view in knockout.rounds],
        champion=QualifiedClubView.model_validate(knockout.champion),
        runner_up=QualifiedClubView.model_validate(knockout.runner_up),
        trophy_ceremony=TrophyCeremonyView.model_validate(knockout.ceremony),
    )


@router.get("/countdown", response_model=TournamentCountdownView)
def get_tournament_countdown(reference_at: datetime | None = None) -> TournamentCountdownView:
    plan = _service.build_demo_tournament(reference_at)
    return TournamentCountdownView.model_validate(plan.countdown)
