from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.club_identity.models.reputation import ClubReputationProfile
from app.models.club_branding_asset import ClubBrandingAsset
from app.models.club_cosmetic_purchase import ClubCosmeticPurchase
from app.models.club_dynasty_progress import ClubDynastyProgress
from app.models.club_identity_theme import ClubIdentityTheme
from app.models.club_jersey_design import ClubJerseyDesign
from app.models.club_profile import ClubProfile
from app.models.club_trophy import ClubTrophy
from app.schemas.club_analytics import (
    ClubAnalyticsView,
    ClubLeaderboardEntry,
    ClubSummaryView,
    CosmeticRevenueSummary,
    ThemeUsageStat,
    TrophyIssuanceSummary,
)
from app.services.club_reputation_service import ClubReputationService


@dataclass(slots=True)
class ClubAnalyticsService:
    session: Session

    def get_summary(self) -> ClubSummaryView:
        pending_branding_reviews = self.session.scalar(
            select(func.count()).select_from(ClubBrandingAsset).where(
                ClubBrandingAsset.moderation_status == "pending_review"
            )
        ) or 0
        pending_branding_reviews += self.session.scalar(
            select(func.count()).select_from(ClubJerseyDesign).where(
                ClubJerseyDesign.moderation_status == "pending_review"
            )
        ) or 0
        return ClubSummaryView(
            total_clubs=self.session.scalar(select(func.count()).select_from(ClubProfile)) or 0,
            total_branding_assets=self.session.scalar(select(func.count()).select_from(ClubBrandingAsset)) or 0,
            total_jerseys=self.session.scalar(select(func.count()).select_from(ClubJerseyDesign)) or 0,
            total_trophies=self.session.scalar(select(func.count()).select_from(ClubTrophy)) or 0,
            pending_branding_reviews=pending_branding_reviews,
        )

    def get_analytics(self) -> ClubAnalyticsView:
        clubs = {club.id: club for club in self.session.scalars(select(ClubProfile)).all()}
        top_reputation = self.session.scalars(
            select(ClubReputationProfile).order_by(ClubReputationProfile.current_score.desc()).limit(5)
        ).all()
        top_dynasties = self.session.scalars(
            select(ClubDynastyProgress).order_by(ClubDynastyProgress.dynasty_score.desc()).limit(5)
        ).all()
        purchases = self.session.scalars(select(ClubCosmeticPurchase)).all()
        trophy_rows = self.session.execute(
            select(ClubTrophy.trophy_type, func.count()).group_by(ClubTrophy.trophy_type)
        ).all()
        theme_rows = self.session.execute(
            select(ClubIdentityTheme.name, func.count()).group_by(ClubIdentityTheme.name)
        ).all()
        return ClubAnalyticsView(
            top_reputation_clubs=[
                ClubLeaderboardEntry(
                    club_id=row.club_id,
                    club_name=clubs[row.club_id].club_name if row.club_id in clubs else row.club_id,
                    score=row.current_score,
                    label=ClubReputationService.to_api_tier(row.prestige_tier).value,
                )
                for row in top_reputation
            ],
            top_dynasties=[
                ClubLeaderboardEntry(
                    club_id=row.club_id,
                    club_name=clubs[row.club_id].club_name if row.club_id in clubs else row.club_id,
                    score=row.dynasty_score,
                    label=row.dynasty_title,
                )
                for row in top_dynasties
            ],
            cosmetic_revenue=CosmeticRevenueSummary(
                total_revenue_minor=sum(int(item.amount_minor) for item in purchases),
                total_service_fees_minor=sum(int(item.metadata_json.get("service_fee_minor", 0)) for item in purchases),
                currency_code="USD",
                purchase_count=len(purchases),
            ),
            trophy_issuance=[
                TrophyIssuanceSummary(trophy_type=trophy_type, count=count)
                for trophy_type, count in trophy_rows
            ],
            theme_usage=[ThemeUsageStat(theme_name=name, usage_count=count) for name, count in theme_rows],
        )
