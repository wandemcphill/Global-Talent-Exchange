from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.auth.dependencies import get_current_user
from app.leagues.models import LeagueClub
from app.leagues.repository import build_league_event_repository
from app.leagues.schemas import (
    LeagueFixturesView,
    LeagueQualificationView,
    LeagueRegisterRequest,
    LeagueRegistrationView,
    LeagueRolloverRequest,
    LeagueRolloverView,
    LeagueSeasonSummaryView,
    LeagueStandingRowView,
    LeagueStandingsView,
)
from app.leagues.service import LeagueSeasonLifecycleService, LeagueSeasonNotFoundError, LeagueValidationError
from app.models.user import User

router = APIRouter(tags=["leagues"])
legacy_router = APIRouter(prefix="/leagues")
api_router = APIRouter(prefix="/api/leagues")


def get_league_service(request: Request) -> LeagueSeasonLifecycleService:
    """Build the lifecycle service over durable storage when a database is wired.

    The repository is resolved once per application instance: choosing it probes
    the database for the event table, and repeating that on every league read
    would add a catalog round trip to each request.
    """
    repository = getattr(request.app.state, "league_event_repository", None)
    if repository is None:
        repository = build_league_event_repository(getattr(request.app.state, "session_factory", None))
        request.app.state.league_event_repository = repository
    return LeagueSeasonLifecycleService(repository=repository)


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


def _owner_divisions(request: Request, club_ids: list[str]) -> dict[str, str]:
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None or not club_ids:
        return {}
    try:
        from app.owner_console.models import OwnerClubState

        with session_factory() as session:
            rows = session.scalars(select(OwnerClubState).where(OwnerClubState.club_id.in_(club_ids))).all()
            return {row.club_id: row.division_level or "foundation" for row in rows}
    except SQLAlchemyError:
        return {}


def _shared_region(request: Request, club_ids: list[str]) -> str:
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None or not club_ids:
        return "UNASSIGNED"
    try:
        from app.models.club_profile import ClubProfile

        with session_factory() as session:
            rows = session.scalars(select(ClubProfile).where(ClubProfile.id.in_(club_ids))).all()
        regions = {str(row.continent_code or "UNASSIGNED").strip().upper() or "UNASSIGNED" for row in rows}
        if len(rows) < len(set(club_ids)):
            regions.add("UNASSIGNED")
        if len(regions) > 1:
            raise LeagueValidationError("A league season stays inside one region.")
        return next(iter(regions), "UNASSIGNED")
    except SQLAlchemyError:
        return "UNASSIGNED"


def _sync_owner_divisions(request: Request, seasons) -> None:
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        return
    try:
        from app.owner_console.service import apply_completed_season_divisions

        with session_factory() as session:
            for season in seasons:
                if not season.division_level or season.status != "completed":
                    continue
                apply_completed_season_divisions(session, season)
            session.commit()
    except SQLAlchemyError:
        return


@legacy_router.post("/register", response_model=LeagueRegistrationView, status_code=status.HTTP_201_CREATED)
@api_router.post("/register", response_model=LeagueRegistrationView, status_code=status.HTTP_201_CREATED)
def register_league(
    payload: LeagueRegisterRequest,
    request: Request,
    service: LeagueSeasonLifecycleService = Depends(get_league_service),
    current_user: User = Depends(get_current_user),
) -> LeagueRegistrationView:
    try:
        club_ids = [club.club_id for club in payload.clubs]
        divisions = _owner_divisions(request, club_ids)
        division_level = ""
        region_code = ""
        if divisions and len(divisions) == len(set(club_ids)):
            levels = {divisions[club_id] for club_id in club_ids}
            if len(levels) == 1:
                division_level = next(iter(levels))
                region_code = _shared_region(request, club_ids)
        state = service.register_season(
            season_id=payload.season_id,
            buy_in_tier=payload.buy_in_tier,
            season_start=payload.season_start,
            club_divisions=divisions or None,
            division_level=division_level,
            region_code=region_code,
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


@legacy_router.post("/rollover", response_model=LeagueRolloverView)
@api_router.post("/rollover", response_model=LeagueRolloverView)
def rollover_leagues(
    payload: LeagueRolloverRequest,
    request: Request,
    service: LeagueSeasonLifecycleService = Depends(get_league_service),
    current_user: User = Depends(get_current_user),
) -> LeagueRolloverView:
    try:
        seasons = [service.get_season_state(season_id) for season_id in payload.season_ids]
        opened, idle = service.open_next_regional_seasons(
            seasons,
            season_start=payload.season_start,
            season_label=payload.season_label,
        )
        _sync_owner_divisions(request, seasons)
    except LeagueSeasonNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LeagueValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LeagueRolloverView(
        opened_season_ids=[season.season_id for season in opened],
        idle_club_ids=[club.club_id for cohort in idle for club in cohort.clubs],
    )


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
