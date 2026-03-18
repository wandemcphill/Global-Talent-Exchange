from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.fan_predictions.schemas import (
    FanPredictionFixtureConfigRequest,
    FanPredictionFixtureView,
    FanPredictionLeaderboardEntryView,
    FanPredictionLeaderboardView,
    FanPredictionOutcomeOverrideRequest,
    FanPredictionOutcomeView,
    FanPredictionRewardGrantView,
    FanPredictionSubmissionRequest,
    FanPredictionSubmissionView,
    FanPredictionTokenLedgerView,
    FanPredictionTokenSummaryView,
)
from backend.app.fan_predictions.service import FanPredictionError, FanPredictionService
from backend.app.models.fan_prediction import FanPredictionFixture, FanPredictionOutcome, FanPredictionRewardGrant, FanPredictionSubmission
from backend.app.models.user import User

router = APIRouter(prefix="/fan-predictions", tags=["fan-predictions"])
admin_router = APIRouter(prefix="/admin/fan-predictions", tags=["admin-fan-predictions"])


def _submission_view(item: FanPredictionSubmission) -> FanPredictionSubmissionView:
    return FanPredictionSubmissionView(
        id=item.id,
        fixture_id=item.fixture_id,
        user_id=item.user_id,
        fan_segment_club_id=item.fan_segment_club_id,
        fan_group_id=item.fan_group_id,
        leaderboard_week_start=item.leaderboard_week_start,
        winner_club_id=item.winner_club_id,
        first_goal_scorer_player_id=item.first_goal_scorer_player_id,
        total_goals=item.total_goals,
        mvp_player_id=item.mvp_player_id,
        tokens_spent=item.tokens_spent,
        status=item.status.value,
        points_awarded=item.points_awarded,
        correct_pick_count=item.correct_pick_count,
        perfect_card=item.perfect_card,
        reward_rank=item.reward_rank,
        settled_at=item.settled_at,
        metadata_json=item.metadata_json,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _outcome_view(item: FanPredictionOutcome) -> FanPredictionOutcomeView:
    return FanPredictionOutcomeView(
        winner_club_id=item.winner_club_id,
        first_goal_scorer_player_id=item.first_goal_scorer_player_id,
        total_goals=item.total_goals,
        mvp_player_id=item.mvp_player_id,
        source=item.source,
        settled_by_user_id=item.settled_by_user_id,
        note=item.note,
        metadata_json=item.metadata_json,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _reward_grant_view(item: FanPredictionRewardGrant) -> FanPredictionRewardGrantView:
    return FanPredictionRewardGrantView(
        id=item.id,
        user_id=item.user_id,
        fixture_id=item.fixture_id,
        submission_id=item.submission_id,
        club_id=item.club_id,
        reward_settlement_id=item.reward_settlement_id,
        leaderboard_scope=item.leaderboard_scope.value,
        reward_type=item.reward_type.value,
        rank=item.rank,
        week_start=item.week_start,
        badge_code=item.badge_code,
        fancoin_amount=item.fancoin_amount,
        promo_pool_reference=item.promo_pool_reference,
        metadata_json=item.metadata_json,
        created_at=item.created_at,
    )


def _fixture_view(service: FanPredictionService, fixture: FanPredictionFixture, actor: User | None = None) -> FanPredictionFixtureView:
    outcome = service.get_outcome(fixture_id=fixture.id)
    my_submission = service.get_submission_for_user(fixture_id=fixture.id, user_id=actor.id) if actor is not None else None
    return FanPredictionFixtureView(
        id=fixture.id,
        match_id=fixture.match_id,
        competition_id=fixture.competition_id,
        season_id=fixture.season_id,
        home_club_id=fixture.home_club_id,
        away_club_id=fixture.away_club_id,
        created_by_user_id=fixture.created_by_user_id,
        title=fixture.title,
        description=fixture.description,
        status=fixture.status.value,
        opens_at=fixture.opens_at,
        locks_at=fixture.locks_at,
        settled_at=fixture.settled_at,
        rewards_disbursed_at=fixture.rewards_disbursed_at,
        token_cost=fixture.token_cost,
        promo_pool_fancoin=fixture.promo_pool_fancoin,
        reward_funding_source=fixture.reward_funding_source,
        badge_code=fixture.badge_code,
        max_reward_winners=fixture.max_reward_winners,
        allow_creator_club_segmentation=fixture.allow_creator_club_segmentation,
        settlement_rule_version=fixture.settlement_rule_version,
        metadata_json=fixture.metadata_json,
        scoring=service.scoring_payload(),
        outcome=_outcome_view(outcome) if outcome is not None else None,
        my_submission=_submission_view(my_submission) if my_submission is not None else None,
        reward_grants=[_reward_grant_view(item) for item in service.list_reward_grants(fixture_id=fixture.id)],
        created_at=fixture.created_at,
        updated_at=fixture.updated_at,
    )


def _leaderboard_view(payload: dict[str, object]) -> FanPredictionLeaderboardView:
    return FanPredictionLeaderboardView(
        scope=str(payload["scope"]),
        week_start=payload["week_start"],
        fixture_id=payload.get("fixture_id"),
        club_id=payload.get("club_id"),
        entries=[FanPredictionLeaderboardEntryView.model_validate(item) for item in payload["entries"]],
    )


@admin_router.put("/matches/{match_id}/fixture", response_model=FanPredictionFixtureView)
def configure_fixture(
    match_id: str,
    payload: FanPredictionFixtureConfigRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> FanPredictionFixtureView:
    service = FanPredictionService(session)
    try:
        fixture = service.ensure_fixture(
            match_id=match_id,
            actor=actor,
            title=payload.title,
            description=payload.description,
            opens_at=payload.opens_at,
            locks_at=payload.locks_at,
            token_cost=payload.token_cost,
            promo_pool_fancoin=payload.promo_pool_fancoin,
            badge_code=payload.badge_code,
            max_reward_winners=payload.max_reward_winners,
            allow_creator_club_segmentation=payload.allow_creator_club_segmentation,
            metadata_json=payload.metadata_json,
        )
        session.commit()
        session.refresh(fixture)
        return _fixture_view(service, fixture, actor)
    except FanPredictionError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@admin_router.post("/matches/{match_id}/settlement", response_model=FanPredictionFixtureView)
def settle_match_predictions(
    match_id: str,
    payload: FanPredictionOutcomeOverrideRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> FanPredictionFixtureView:
    service = FanPredictionService(session)
    try:
        fixture = service.attempt_match_settlement(
            match_id=match_id,
            actor=actor,
            winner_club_id=payload.winner_club_id,
            first_goal_scorer_player_id=payload.first_goal_scorer_player_id,
            total_goals=payload.total_goals,
            mvp_player_id=payload.mvp_player_id,
            note=payload.note,
            metadata_json=payload.metadata_json,
            disburse_rewards=payload.disburse_rewards,
            create_if_missing=True,
        )
        assert fixture is not None
        session.commit()
        session.refresh(fixture)
        return _fixture_view(service, fixture, actor)
    except FanPredictionError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.get("/matches/{match_id}", response_model=FanPredictionFixtureView)
def get_match_fixture(
    match_id: str,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FanPredictionFixtureView:
    service = FanPredictionService(session)
    try:
        fixture = service.get_fixture(match_id=match_id, actor=actor)
        return _fixture_view(service, fixture, actor)
    except FanPredictionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.post("/matches/{match_id}/submissions", response_model=FanPredictionSubmissionView, status_code=201)
def submit_match_prediction(
    match_id: str,
    payload: FanPredictionSubmissionRequest,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FanPredictionSubmissionView:
    service = FanPredictionService(session)
    try:
        submission = service.submit_prediction(
            actor=actor,
            match_id=match_id,
            winner_club_id=payload.winner_club_id,
            first_goal_scorer_player_id=payload.first_goal_scorer_player_id,
            total_goals=payload.total_goals,
            mvp_player_id=payload.mvp_player_id,
            fan_segment_club_id=payload.fan_segment_club_id,
            fan_group_id=payload.fan_group_id,
            metadata_json=payload.metadata_json,
        )
        session.commit()
        session.refresh(submission)
        return _submission_view(submission)
    except FanPredictionError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.get("/matches/{match_id}/leaderboard", response_model=FanPredictionLeaderboardView)
def get_match_leaderboard(
    match_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    _actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FanPredictionLeaderboardView:
    service = FanPredictionService(session)
    try:
        return _leaderboard_view(service.fixture_leaderboard(match_id=match_id, limit=limit))
    except FanPredictionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.get("/leaderboards/weekly", response_model=FanPredictionLeaderboardView)
def get_weekly_leaderboard(
    week_start: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    _actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FanPredictionLeaderboardView:
    service = FanPredictionService(session)
    parsed_week = date.fromisoformat(week_start) if week_start else None
    return _leaderboard_view(service.weekly_leaderboard(week_start=parsed_week, limit=limit))


@router.get("/creator-clubs/{club_id}/leaderboards/weekly", response_model=FanPredictionLeaderboardView)
def get_creator_club_weekly_leaderboard(
    club_id: str,
    week_start: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    _actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FanPredictionLeaderboardView:
    service = FanPredictionService(session)
    try:
        parsed_week = date.fromisoformat(week_start) if week_start else None
        return _leaderboard_view(service.creator_club_weekly_leaderboard(club_id=club_id, week_start=parsed_week, limit=limit))
    except FanPredictionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.get("/me/tokens", response_model=FanPredictionTokenSummaryView)
def get_my_prediction_tokens(
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FanPredictionTokenSummaryView:
    service = FanPredictionService(session)
    summary = service.token_summary(actor=actor)
    return FanPredictionTokenSummaryView(
        available_tokens=summary["available_tokens"],
        daily_refill_tokens=summary["daily_refill_tokens"],
        season_pass_bonus_tokens=summary["season_pass_bonus_tokens"],
        today_token_grants=summary["today_token_grants"],
        latest_effective_date=summary["latest_effective_date"],
        ledger=[
            FanPredictionTokenLedgerView(
                id=item.id,
                reason=item.reason.value,
                amount=item.amount,
                effective_date=item.effective_date,
                season_pass_id=item.season_pass_id,
                submission_id=item.submission_id,
                reference=item.reference,
                note=item.note,
                metadata_json=item.metadata_json,
                created_at=item.created_at,
            )
            for item in summary["ledger"]
        ],
    )


@router.get("/me/submissions", response_model=list[FanPredictionSubmissionView])
def list_my_submissions(
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[FanPredictionSubmissionView]:
    service = FanPredictionService(session)
    return [_submission_view(item) for item in service.list_submissions_for_user(actor=actor)]
