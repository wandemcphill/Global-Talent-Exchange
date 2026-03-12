from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.leagues.models import LeagueClub
from backend.app.leagues.schemas import (
    LeagueFixturesView,
    LeagueQualificationView,
    LeagueRegisterRequest,
    LeagueRegistrationView,
    LeagueSeasonSummaryView,
    LeagueStandingRowView,
    LeagueStandingsView,
)
from backend.app.leagues.service import LeagueSeasonLifecycleService, LeagueSeasonNotFoundError, LeagueValidationError

router = APIRouter(tags=["leagues"])
legacy_router = APIRouter(prefix="/leagues")
api_router = APIRouter(prefix="/api/leagues")


def get_league_service() -> LeagueSeasonLifecycleService:
    return LeagueSeasonLifecycleService()


def _build_registration_view(state) -> LeagueRegistrationView:
    return LeagueRegistrationView(
        season_id=state.season_id,
        buy_in_tier=state.buy_in_tier,
        season_start=state.season_start,
        registered_club_count=len(state.clubs),
        group_size_target=state.group_size_target,
        group_is_full=state.group_is_full,
        scheduled_matches_per_club=state.scheduled_matches_per_club,
        target_matches_per_club=state.target_matches_per_club,
        total_fixture_count=state.total_fixture_count,
        total_pool=state.prize_pool.total_pool,
        status=state.status,
    )


def _build_standings_view(state) -> LeagueStandingsView:
    return LeagueStandingsView(
        season_id=state.season_id,
        status=state.status,
        rows=[LeagueStandingRowView.model_validate(row) for row in state.standings],
    )


@legacy_router.post("/register", response_model=LeagueRegistrationView, status_code=status.HTTP_201_CREATED)
@api_router.post("/register", response_model=LeagueRegistrationView, status_code=status.HTTP_201_CREATED)
def register_league(
    payload: LeagueRegisterRequest,
    service: LeagueSeasonLifecycleService = Depends(get_league_service),
) -> LeagueRegistrationView:
    try:
        state = service.register_season(
            season_id=payload.season_id,
            buy_in_tier=payload.buy_in_tier,
            season_start=payload.season_start,
            clubs=tuple(
                LeagueClub(
                    club_id=club.club_id,
                    club_name=club.club_name,
                    strength_rating=club.strength_rating,
                )
                for club in payload.clubs
            ),
        )
    except LeagueValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _build_registration_view(state)


@legacy_router.get("/{season_id}/standings", response_model=LeagueStandingsView)
@api_router.get("/{season_id}/standings", response_model=LeagueStandingsView)
def get_league_standings(
    season_id: str,
    service: LeagueSeasonLifecycleService = Depends(get_league_service),
) -> LeagueStandingsView:
    try:
        state = service.get_season_state(season_id)
    except LeagueSeasonNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_standings_view(state)


@legacy_router.get("/{season_id}/fixtures", response_model=LeagueFixturesView)
@api_router.get("/{season_id}/fixtures", response_model=LeagueFixturesView)
def get_league_fixtures(
    season_id: str,
    service: LeagueSeasonLifecycleService = Depends(get_league_service),
) -> LeagueFixturesView:
    try:
        state = service.get_season_state(season_id)
    except LeagueSeasonNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LeagueFixturesView(
        season_id=state.season_id,
        total_fixtures=state.total_fixture_count,
        day_count=max((fixture.day_number for fixture in state.fixtures), default=0),
        fixtures=list(state.fixtures),
    )


@legacy_router.get("/{season_id}/summary", response_model=LeagueSeasonSummaryView)
@api_router.get("/{season_id}/summary", response_model=LeagueSeasonSummaryView)
def get_league_summary(
    season_id: str,
    service: LeagueSeasonLifecycleService = Depends(get_league_service),
) -> LeagueSeasonSummaryView:
    try:
        state = service.get_season_state(season_id)
    except LeagueSeasonNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LeagueSeasonSummaryView(
        season_id=state.season_id,
        buy_in_tier=state.buy_in_tier,
        season_start=state.season_start,
        status=state.status,
        registered_club_count=len(state.clubs),
        group_size_target=state.group_size_target,
        group_is_full=state.group_is_full,
        scheduled_matches_per_club=state.scheduled_matches_per_club,
        target_matches_per_club=state.target_matches_per_club,
        completed_fixture_count=state.completed_fixture_count,
        total_fixture_count=state.total_fixture_count,
        prize_pool=state.prize_pool,
        champion_prize=state.champion_prize,
        top_scorer_award=state.top_scorer_award,
        top_assist_award=state.top_assist_award,
        auto_entry_slots=list(state.auto_entry_slots),
    )


@legacy_router.get("/{season_id}/qualification-markers", response_model=LeagueQualificationView)
@api_router.get("/{season_id}/qualification-markers", response_model=LeagueQualificationView)
def get_league_qualification_markers(
    season_id: str,
    service: LeagueSeasonLifecycleService = Depends(get_league_service),
) -> LeagueQualificationView:
    try:
        state = service.get_season_state(season_id)
    except LeagueSeasonNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LeagueQualificationView(
        season_id=state.season_id,
        opted_out_club_ids=list(state.opted_out_club_ids),
        auto_entry_slots=list(state.auto_entry_slots),
        rows=[LeagueStandingRowView.model_validate(row) for row in state.standings],
    )


router.include_router(legacy_router)
router.include_router(api_router)


__all__ = ["get_league_service", "router"]
