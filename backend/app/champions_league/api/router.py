from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.app.champions_league.api.schemas import (
    ClubCandidateRequest,
    ClubSeedRequest,
    KnockoutBracketRequest,
    KnockoutBracketView,
    LeagueMatchResultRequest,
    LeaguePhaseTableRequest,
    LeaguePhaseTableView,
    LeagueStandingRowRequest,
    PlayoffBracketRequest,
    PlayoffBracketView,
    PrizePoolPreviewRequest,
    PrizeSettlementPreviewView,
    QualificationMapRequest,
    QualificationMapView,
)
from backend.app.champions_league.models.domain import (
    ChampionsLeagueValidationError,
    ClubCandidate,
    ClubSeed,
    LeagueMatchResult,
    LeagueStandingRow,
)
from backend.app.champions_league.services.tournament import ChampionsLeagueService

router = APIRouter(prefix="/champions-league", tags=["champions-league"])


@router.post("/qualification-map", response_model=QualificationMapView)
def build_qualification_map(payload: QualificationMapRequest) -> QualificationMapView:
    try:
        result = ChampionsLeagueService().build_qualification_map(
            [_candidate_from_request(club) for club in payload.clubs]
        )
    except ChampionsLeagueValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return QualificationMapView.model_validate(result)


@router.post("/playoff-bracket", response_model=PlayoffBracketView)
def build_playoff_bracket(payload: PlayoffBracketRequest) -> PlayoffBracketView:
    try:
        result = ChampionsLeagueService().build_playoff_bracket(
            [_candidate_from_request(club) for club in payload.clubs],
            winner_overrides=payload.winner_overrides,
        )
    except ChampionsLeagueValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return PlayoffBracketView.model_validate(result)


@router.post("/league-phase/table", response_model=LeaguePhaseTableView)
def build_league_phase_table(payload: LeaguePhaseTableRequest) -> LeaguePhaseTableView:
    try:
        result = ChampionsLeagueService().build_league_phase_table(
            [_seed_from_request(club) for club in payload.clubs],
            [_match_from_request(match) for match in payload.matches],
        )
    except ChampionsLeagueValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return LeaguePhaseTableView.model_validate(result)


@router.post("/knockout-bracket", response_model=KnockoutBracketView)
def build_knockout_bracket(payload: KnockoutBracketRequest) -> KnockoutBracketView:
    try:
        result = ChampionsLeagueService().build_knockout_bracket(
            [_standing_from_request(row) for row in payload.standings],
            knockout_playoff_winners=payload.knockout_playoff_winners,
            round_of_16_winners=payload.round_of_16_winners,
            quarterfinal_winners=payload.quarterfinal_winners,
            semifinal_winners=payload.semifinal_winners,
            final_winner=payload.final_winner,
        )
    except ChampionsLeagueValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return KnockoutBracketView.model_validate(result)


@router.post("/prize-pool/preview", response_model=PrizeSettlementPreviewView)
def build_prize_pool_preview(payload: PrizePoolPreviewRequest) -> PrizeSettlementPreviewView:
    try:
        result = ChampionsLeagueService().build_prize_pool_preview(
            season_id=payload.season_id,
            league_leftover_allocation=payload.league_leftover_allocation,
            champion_club_id=payload.champion_club_id,
            champion_club_name=payload.champion_club_name,
            currency=payload.currency,
        )
    except ChampionsLeagueValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return PrizeSettlementPreviewView.model_validate(result)


def _candidate_from_request(club: ClubCandidateRequest) -> ClubCandidate:
    return ClubCandidate(
        club_id=club.club_id,
        club_name=club.club_name,
        region=club.region,
        tier=club.tier,
        ranking_points=club.ranking_points,
        domestic_rank=club.domestic_rank,
    )


def _seed_from_request(club: ClubSeedRequest) -> ClubSeed:
    return ClubSeed(
        club_id=club.club_id,
        club_name=club.club_name,
        seed=club.seed,
        region=club.region,
        tier=club.tier,
    )


def _match_from_request(match: LeagueMatchResultRequest) -> LeagueMatchResult:
    return LeagueMatchResult(
        match_id=match.match_id,
        home_club_id=match.home_club_id,
        away_club_id=match.away_club_id,
        home_goals=match.home_goals,
        away_goals=match.away_goals,
    )


def _standing_from_request(row: LeagueStandingRowRequest) -> LeagueStandingRow:
    return LeagueStandingRow(
        club_id=row.club_id,
        club_name=row.club_name,
        seed=row.seed,
        played=row.played,
        wins=row.wins,
        draws=row.draws,
        losses=row.losses,
        goals_for=row.goals_for,
        goals_against=row.goals_against,
        goal_difference=row.goal_difference,
        points=row.points,
        rank=row.rank,
        advancement_status=row.advancement_status,
    )
