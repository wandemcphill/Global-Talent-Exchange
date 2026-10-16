from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.history_engagement.schemas import (
    AchievementView,
    ClubCommunityResponse,
    EngagementSyncResponse,
    GoatRankingsResponse,
    HistoricalLeaderboardsResponse,
    HistoricalRecordView,
    HistoricalTimelineResponse,
    MilestoneProgressView,
    ObjectivesResponse,
    RivalryPageResponse,
    SeasonPassView,
    SeasonRewardClaimView,
    SocialActivityCreate,
    SocialActivityView,
    UserAchievementView,
    UserFollowCreate,
    UserFollowView,
    UserProfileView,
    WorkerRunResponse,
)
from app.history_engagement.service import HistoryEngagementError, HistoryEngagementService
from app.models.user import User

router = APIRouter(tags=["history-engagement"])
admin_router = APIRouter(prefix="/admin/history-engagement", tags=["admin-history-engagement"])


def get_service(session: Session = Depends(get_session)) -> HistoryEngagementService:
    return HistoryEngagementService(session)


def _raise(exc: HistoryEngagementError) -> None:
    detail = str(exc)
    if detail.endswith("not found.") or "was not found" in detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc


def _activity_view(item) -> SocialActivityView:
    return SocialActivityView.model_validate(item, from_attributes=True)


@router.get("/history/records", response_model=list[HistoricalRecordView])
def list_history_records(
    limit: int = Query(default=50, ge=1, le=200),
    record_type: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    service: HistoryEngagementService = Depends(get_service),
) -> list[HistoricalRecordView]:
    return [
        HistoricalRecordView.model_validate(item, from_attributes=True)
        for item in service.list_records(limit=limit, record_type=record_type, subject_type=subject_type, subject_id=subject_id)
    ]


@router.get("/history/leaderboards", response_model=HistoricalLeaderboardsResponse)
def get_history_leaderboards(
    limit: int = Query(default=20, ge=1, le=100),
    service: HistoryEngagementService = Depends(get_service),
) -> HistoricalLeaderboardsResponse:
    payload = service.history_leaderboards(limit=limit)
    return HistoricalLeaderboardsResponse(
        generated_at=payload["generated_at"],
        top_players_ever=[item for item in payload["top_players_ever"]],
        top_clubs_ever=[item for item in payload["top_clubs_ever"]],
        top_managers=[item for item in payload["top_managers"]],
        tracked_records=[HistoricalRecordView.model_validate(item, from_attributes=True) for item in payload["tracked_records"]],
    )


@router.get("/history/goat-rankings", response_model=GoatRankingsResponse)
def get_goat_rankings(
    entity_type: str = Query(pattern="^(player|club|manager)$"),
    limit: int = Query(default=20, ge=1, le=100),
    service: HistoryEngagementService = Depends(get_service),
) -> GoatRankingsResponse:
    try:
        payload = service.goat_rankings(entity_type=entity_type, limit=limit)
    except HistoryEngagementError as exc:
        _raise(exc)
    return GoatRankingsResponse(
        entity_type=payload["entity_type"],
        generated_at=payload["generated_at"],
        entries=[item for item in payload["entries"]],
    )


@router.get("/history/timeline/{subject_type}/{subject_id}", response_model=HistoricalTimelineResponse)
def get_history_timeline(
    subject_type: str,
    subject_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service: HistoryEngagementService = Depends(get_service),
) -> HistoricalTimelineResponse:
    try:
        payload = service.timeline(subject_type=subject_type, subject_id=subject_id, limit=limit)
    except HistoryEngagementError as exc:
        _raise(exc)
    return HistoricalTimelineResponse.model_validate(payload)


@router.get("/engagement/achievements", response_model=list[AchievementView])
def list_achievements(service: HistoryEngagementService = Depends(get_service)) -> list[AchievementView]:
    return [AchievementView.model_validate(item, from_attributes=True) for item in service.list_achievements()]


@router.get("/engagement/achievements/me", response_model=list[UserAchievementView])
def list_my_achievements(
    current_user: User = Depends(get_current_user),
    service: HistoryEngagementService = Depends(get_service),
) -> list[UserAchievementView]:
    service.reconcile_user(actor=current_user)
    return [UserAchievementView.model_validate(item, from_attributes=True) for item in service.achievements_for_user(actor=current_user)]


@router.get("/engagement/milestones/me", response_model=list[MilestoneProgressView])
def list_my_milestones(
    current_user: User = Depends(get_current_user),
    service: HistoryEngagementService = Depends(get_service),
) -> list[MilestoneProgressView]:
    return [MilestoneProgressView.model_validate(item, from_attributes=True) for item in service.milestones_for_user(actor=current_user)]


@router.post("/engagement/sync", response_model=EngagementSyncResponse)
def sync_engagement(
    current_user: User = Depends(get_current_user),
    service: HistoryEngagementService = Depends(get_service),
) -> EngagementSyncResponse:
    payload = service.reconcile_user(actor=current_user)
    return EngagementSyncResponse(
        profile=UserProfileView.model_validate(payload["profile"], from_attributes=True),
        streak=payload["streak"],
        unlocked_achievements=[UserAchievementView.model_validate(item, from_attributes=True) for item in payload["unlocked_achievements"]],
        daily_tasks=[item for item in payload["daily_tasks"]],
        weekly_tasks=[item for item in payload["weekly_tasks"]],
        season_pass=SeasonPassView.model_validate(payload["season_pass"]),
    )


@router.get("/social/profile/me", response_model=UserProfileView)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    service: HistoryEngagementService = Depends(get_service),
) -> UserProfileView:
    return UserProfileView.model_validate(service.profile_for_user(actor=current_user), from_attributes=True)


@router.post("/social/follows", response_model=UserFollowView, status_code=status.HTTP_201_CREATED)
def follow_target(
    payload: UserFollowCreate,
    current_user: User = Depends(get_current_user),
    service: HistoryEngagementService = Depends(get_service),
) -> UserFollowView:
    try:
        item = service.follow(actor=current_user, target_type=payload.target_type, target_id=payload.target_id)
    except HistoryEngagementError as exc:
        _raise(exc)
    return UserFollowView.model_validate(item, from_attributes=True)


@router.delete("/social/follows", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_target(
    payload: UserFollowCreate,
    current_user: User = Depends(get_current_user),
    service: HistoryEngagementService = Depends(get_service),
) -> None:
    try:
        service.unfollow(actor=current_user, target_type=payload.target_type, target_id=payload.target_id)
    except HistoryEngagementError as exc:
        _raise(exc)


@router.get("/social/feed", response_model=list[SocialActivityView])
def get_social_feed(
    limit: int = Query(default=40, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: HistoryEngagementService = Depends(get_service),
) -> list[SocialActivityView]:
    return [_activity_view(item) for item in service.list_feed(actor=current_user, limit=limit)]


@router.get("/social/clubs/{club_id}/community", response_model=ClubCommunityResponse)
def get_club_community(
    club_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    service: HistoryEngagementService = Depends(get_service),
) -> ClubCommunityResponse:
    try:
        payload = service.club_community(club_id=club_id, limit=limit)
    except HistoryEngagementError as exc:
        _raise(exc)
    return ClubCommunityResponse(
        club_id=payload["club_id"],
        follower_count=payload["follower_count"],
        fan_chat=[_activity_view(item) for item in payload["fan_chat"]],
        activity_wall=[_activity_view(item) for item in payload["activity_wall"]],
    )


@router.post("/social/clubs/{club_id}/community/messages", response_model=SocialActivityView, status_code=status.HTTP_201_CREATED)
def post_club_community_message(
    club_id: str,
    payload: SocialActivityCreate,
    current_user: User = Depends(get_current_user),
    service: HistoryEngagementService = Depends(get_service),
) -> SocialActivityView:
    try:
        item = service.post_club_message(actor=current_user, club_id=club_id, body=payload.body)
    except HistoryEngagementError as exc:
        _raise(exc)
    return _activity_view(item)


@router.get("/social/rivalries/{club_a_id}/{club_b_id}", response_model=RivalryPageResponse)
def get_rivalry_page(
    club_a_id: str,
    club_b_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    service: HistoryEngagementService = Depends(get_service),
) -> RivalryPageResponse:
    try:
        payload = service.rivalry_page(club_a_id=club_a_id, club_b_id=club_b_id, limit=limit)
    except HistoryEngagementError as exc:
        _raise(exc)
    return RivalryPageResponse(
        rivalry_key=payload["rivalry_key"],
        club_a_id=payload["club_a_id"],
        club_b_id=payload["club_b_id"],
        label=payload["label"],
        intensity_score=payload["intensity_score"],
        streak_length=payload["streak_length"],
        streak_holder_club_id=payload["streak_holder_club_id"],
        notable_moments=payload["notable_moments"],
        banter=[_activity_view(item) for item in payload["banter"]],
    )


@router.post("/social/rivalries/{club_a_id}/{club_b_id}/banter", response_model=SocialActivityView, status_code=status.HTTP_201_CREATED)
def post_rivalry_banter(
    club_a_id: str,
    club_b_id: str,
    payload: SocialActivityCreate,
    current_user: User = Depends(get_current_user),
    service: HistoryEngagementService = Depends(get_service),
) -> SocialActivityView:
    try:
        item = service.post_banter(actor=current_user, club_a_id=club_a_id, club_b_id=club_b_id, body=payload.body)
    except HistoryEngagementError as exc:
        _raise(exc)
    return _activity_view(item)


@router.get("/objectives/me", response_model=ObjectivesResponse)
def get_my_objectives(
    current_user: User = Depends(get_current_user),
    service: HistoryEngagementService = Depends(get_service),
) -> ObjectivesResponse:
    payload = service.objectives_for_user(actor=current_user)
    return ObjectivesResponse(
        streak=payload["streak"],
        daily_tasks=[item for item in payload["daily_tasks"]],
        weekly_tasks=[item for item in payload["weekly_tasks"]],
    )


@router.get("/season-pass/me", response_model=SeasonPassView)
def get_my_season_pass(
    current_user: User = Depends(get_current_user),
    service: HistoryEngagementService = Depends(get_service),
) -> SeasonPassView:
    payload = service.season_pass_for_user(actor=current_user)
    return SeasonPassView.model_validate(payload)


@router.post("/season-pass/rewards/{reward_id}/claim", response_model=SeasonRewardClaimView, status_code=status.HTTP_201_CREATED)
def claim_season_pass_reward(
    reward_id: str,
    current_user: User = Depends(get_current_user),
    service: HistoryEngagementService = Depends(get_service),
) -> SeasonRewardClaimView:
    try:
        claim = service.claim_season_reward(actor=current_user, reward_id=reward_id)
    except HistoryEngagementError as exc:
        _raise(exc)
    return SeasonRewardClaimView.model_validate(claim, from_attributes=True)


@admin_router.post("/run-workers", response_model=WorkerRunResponse)
def run_history_engagement_workers(
    _admin: User = Depends(get_current_admin),
    service: HistoryEngagementService = Depends(get_service),
) -> WorkerRunResponse:
    return WorkerRunResponse.model_validate(service.run_workers_once())
