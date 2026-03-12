from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.club_branding_asset import ClubBrandingAsset
from backend.app.models.club_jersey_design import ClubJerseyDesign
from backend.app.schemas.club_admin import AdminClubDetailView, BrandingModerationResultView, ModerateBrandingRequest
from backend.app.schemas.club_branding_core import ClubJerseyDesignCore
from backend.app.schemas.club_identity_core import ClubBrandingAssetCore
from backend.app.services.club_branding_service import ClubBrandingService
from backend.app.services.club_dynasty_service import ClubDynastyService
from backend.app.services.club_jersey_service import ClubJerseyService
from backend.app.services.club_purchase_service import ClubPurchaseService
from backend.app.services.club_reputation_service import ClubReputationService
from backend.app.services.club_trophy_service import ClubTrophyService


@dataclass(slots=True)
class ClubAdminService:
    session: Session

    def moderate_branding(
        self,
        *,
        club_id: str,
        reviewer_user_id: str,
        payload: ModerateBrandingRequest,
    ) -> BrandingModerationResultView:
        updated_assets = self.session.scalars(
            select(ClubBrandingAsset).where(
                ClubBrandingAsset.club_id == club_id,
                ClubBrandingAsset.id.in_(payload.asset_ids or [""]),
            )
        ).all()
        for asset in updated_assets:
            asset.moderation_status = payload.moderation_status
            asset.moderation_reason = payload.reason
            asset.reviewed_by_user_id = reviewer_user_id
            asset.reviewed_at = datetime.now(timezone.utc)

        updated_jerseys = self.session.scalars(
            select(ClubJerseyDesign).where(
                ClubJerseyDesign.club_id == club_id,
                ClubJerseyDesign.id.in_(payload.jersey_ids or [""]),
            )
        ).all()
        for jersey in updated_jerseys:
            jersey.moderation_status = payload.moderation_status
            jersey.moderation_reason = payload.reason
            jersey.reviewed_by_user_id = reviewer_user_id
            jersey.reviewed_at = datetime.now(timezone.utc)

        self.session.commit()
        return BrandingModerationResultView(
            updated_assets=[ClubBrandingAssetCore.model_validate(item) for item in updated_assets],
            updated_jerseys=[ClubJerseyDesignCore.model_validate(item) for item in updated_jerseys],
        )

    def get_admin_detail(self, club_id: str) -> AdminClubDetailView:
        profile, theme, assets = ClubBrandingService(self.session).get_branding(club_id)
        reputation = ClubReputationService(self.session).get_reputation(club_id)
        dynasty, _ = ClubDynastyService(self.session).get_dynasty(club_id)
        _, trophies = ClubTrophyService(self.session).get_trophy_cabinet(club_id)
        jerseys = ClubJerseyService(self.session).list_jerseys(club_id)
        purchases = ClubPurchaseService(self.session).list_purchases(club_id=club_id)
        return AdminClubDetailView(
            profile=profile,
            reputation=reputation,
            dynasty=dynasty,
            trophies=trophies,
            branding_assets=assets,
            jerseys=jerseys,
            theme=theme,
            purchases=purchases,
        )
