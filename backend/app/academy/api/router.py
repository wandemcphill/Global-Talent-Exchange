from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from backend.app.academy.api.schemas import (
    AcademyAwardsResponseView,
    AcademyFixturesResponseView,
    AcademyQualificationResponseView,
    AcademyRegistrationResponseView,
    AcademySeasonRequestView,
    AcademySeasonSummaryView,
    AcademyStandingsResponseView,
)
from backend.app.academy.models import (
    AcademyAwardsLeaders,
    AcademyClubRegistrationRequest,
    AcademyMatchResult,
    AcademySeasonRequest,
)
from backend.app.academy.services import AcademyCompetitionService

router = APIRouter(prefix="/academy", tags=["academy"])

_service = AcademyCompetitionService()


def _to_domain_request(payload: AcademySeasonRequestView) -> AcademySeasonRequest:
    return AcademySeasonRequest(
        season_id=payload.season_id,
        start_date=payload.start_date,
        clubs=tuple(
            AcademyClubRegistrationRequest(
                club_id=club.club_id,
                club_name=club.club_name,
                senior_buy_in_tier=club.senior_buy_in_tier,
                carry_over_from_previous_season=club.carry_over_from_previous_season,
            )
            for club in payload.clubs
        ),
        results=tuple(
            AcademyMatchResult(
                fixture_id=result.fixture_id,
                home_goals=result.home_goals,
                away_goals=result.away_goals,
            )
            for result in payload.results
        ),
        senior_world_super_cup_active=payload.senior_world_super_cup_active,
        awards_leaders=(
            AcademyAwardsLeaders(
                top_scorer_club_id=payload.awards_leaders.top_scorer_club_id,
                top_assist_club_id=payload.awards_leaders.top_assist_club_id,
            )
            if payload.awards_leaders is not None
            else None
        ),
    )


@router.post("/registration", response_model=AcademyRegistrationResponseView)
def preview_registration(payload: AcademySeasonRequestView) -> AcademyRegistrationResponseView:
    request = _to_domain_request(payload)
    projection = _service.build_season_projection(request)
    data = asdict(projection)
    return AcademyRegistrationResponseView.model_validate(
        {
            "season_id": request.season_id,
            "registrations": data["registrations"],
            "ledger_events": [event for event in data["ledger_events"] if event["event_type"] == "academy.registration.accepted"],
        }
    )


@router.post("/fixtures", response_model=AcademyFixturesResponseView)
def preview_fixtures(payload: AcademySeasonRequestView) -> AcademyFixturesResponseView:
    request = _to_domain_request(payload)
    projection = _service.build_season_projection(request)
    data = asdict(projection)
    return AcademyFixturesResponseView.model_validate(
        {
            "season_id": request.season_id,
            "fixtures": data["fixtures"],
            "ledger_events": [event for event in data["ledger_events"] if event["event_type"] == "academy.fixtures.generated"],
        }
    )


@router.post("/standings", response_model=AcademyStandingsResponseView)
def preview_standings(payload: AcademySeasonRequestView) -> AcademyStandingsResponseView:
    request = _to_domain_request(payload)
    projection = _service.build_season_projection(request)
    data = asdict(projection)
    return AcademyStandingsResponseView.model_validate(
        {
            "season_id": projection.season_id,
            "status": projection.status,
            "completed_fixture_count": projection.completed_fixture_count,
            "standings": data["standings"],
        }
    )


@router.post("/qualification", response_model=AcademyQualificationResponseView)
def preview_qualification(payload: AcademySeasonRequestView) -> AcademyQualificationResponseView:
    request = _to_domain_request(payload)
    projection = _service.build_season_projection(request)
    data = asdict(projection)
    return AcademyQualificationResponseView.model_validate(
        {
            "season_id": projection.season_id,
            "status": projection.status,
            "competition": data["champions_league"],
        }
    )


@router.post("/awards", response_model=AcademyAwardsResponseView)
def preview_awards(payload: AcademySeasonRequestView) -> AcademyAwardsResponseView:
    request = _to_domain_request(payload)
    projection = _service.build_season_projection(request)
    data = asdict(projection)
    return AcademyAwardsResponseView.model_validate(
        {
            "season_id": projection.season_id,
            "awards": data["awards"],
        }
    )


@router.post("/season-summary", response_model=AcademySeasonSummaryView)
def season_summary(payload: AcademySeasonRequestView) -> AcademySeasonSummaryView:
    request = _to_domain_request(payload)
    projection = _service.build_season_projection(request)
    return AcademySeasonSummaryView.model_validate(asdict(projection))
