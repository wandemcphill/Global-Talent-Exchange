from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.auth.dependencies import get_current_admin
from backend.app.models.user import User
from backend.app.schemas.club_ops_admin import ClubOpsSummaryView
from backend.app.schemas.club_ops_analytics import (
    ClubAcademyAnalyticsView,
    ClubFinanceAnalyticsView,
    ClubScoutingAnalyticsView,
    ClubSponsorshipAnalyticsView,
)
from backend.app.services.club_ops_admin_service import ClubOpsAdminService, get_club_ops_admin_service
from backend.app.services.club_ops_analytics_service import ClubOpsAnalyticsService, get_club_ops_analytics_service

router = APIRouter(prefix="/api/admin/clubs", tags=["admin-club-ops"])


@router.get("/ops-summary", response_model=ClubOpsSummaryView)
def get_ops_summary(
    _: User = Depends(get_current_admin),
    admin_service: ClubOpsAdminService = Depends(get_club_ops_admin_service),
) -> ClubOpsSummaryView:
    return admin_service.ops_summary()


@router.get("/finance-analytics", response_model=ClubFinanceAnalyticsView)
def get_finance_analytics(
    _: User = Depends(get_current_admin),
    analytics_service: ClubOpsAnalyticsService = Depends(get_club_ops_analytics_service),
) -> ClubFinanceAnalyticsView:
    return analytics_service.finance_analytics()


@router.get("/sponsorship-analytics", response_model=ClubSponsorshipAnalyticsView)
def get_sponsorship_analytics(
    _: User = Depends(get_current_admin),
    analytics_service: ClubOpsAnalyticsService = Depends(get_club_ops_analytics_service),
) -> ClubSponsorshipAnalyticsView:
    return analytics_service.sponsorship_analytics()


@router.get("/academy-analytics", response_model=ClubAcademyAnalyticsView)
def get_academy_analytics(
    _: User = Depends(get_current_admin),
    analytics_service: ClubOpsAnalyticsService = Depends(get_club_ops_analytics_service),
) -> ClubAcademyAnalyticsView:
    return analytics_service.academy_analytics()


@router.get("/scouting-analytics", response_model=ClubScoutingAnalyticsView)
def get_scouting_analytics(
    _: User = Depends(get_current_admin),
    analytics_service: ClubOpsAnalyticsService = Depends(get_club_ops_analytics_service),
) -> ClubScoutingAnalyticsView:
    return analytics_service.scouting_analytics()


__all__ = ["router"]
