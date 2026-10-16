from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums.creator_profile_status import CreatorProfileStatus
from app.models.creator_application import CreatorApplication
from app.models.creator_profile import CreatorProfile
from app.models.creator_provisioning import CreatorClubProvisioning
from app.models.user import User


class CreatorProvisioningError(ValueError):
    pass


@dataclass(slots=True)
class CreatorProvisioningService:
    session: Session

    def provision_application(
        self,
        *,
        application: CreatorApplication,
        reviewer: User,
    ) -> CreatorClubProvisioning:
        existing = self.session.scalar(
            select(CreatorClubProvisioning).where(CreatorClubProvisioning.application_id == application.id)
        )
        if existing is not None:
            return existing

        creator_profile = self._ensure_creator_profile(application)
        provisioning = CreatorClubProvisioning(
            application_id=application.id,
            creator_profile_id=creator_profile.id,
            club_id=None,
            stadium_id=None,
            creator_squad_id=None,
            creator_regen_id=None,
            provision_status="active",
            metadata_json={
                "approved_by_user_id": reviewer.id,
                "requested_handle": application.requested_handle,
                "platform": application.platform,
                "follower_count": application.follower_count,
                "identity_model": "creator_only",
            },
        )
        self.session.add(provisioning)
        self.session.flush()
        return provisioning

    def _ensure_creator_profile(self, application: CreatorApplication) -> CreatorProfile:
        existing = self.session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == application.user_id))
        if existing is not None:
            existing.display_name = application.display_name
            existing.tier = self._resolve_tier(application.follower_count)
            existing.status = CreatorProfileStatus.ACTIVE
            self.session.flush()
            return existing

        conflicting_handle = self.session.scalar(
            select(CreatorProfile).where(CreatorProfile.handle == application.requested_handle)
        )
        if conflicting_handle is not None:
            raise CreatorProvisioningError("creator_handle_taken")

        creator_profile = CreatorProfile(
            user_id=application.user_id,
            handle=application.requested_handle,
            display_name=application.display_name,
            tier=self._resolve_tier(application.follower_count),
            status=CreatorProfileStatus.ACTIVE,
            payout_config_json={
                "platform": application.platform,
                "follower_count": application.follower_count,
                "social_links": list(application.social_links_json or []),
            },
        )
        self.session.add(creator_profile)
        self.session.flush()
        return creator_profile

    @staticmethod
    def _resolve_tier(follower_count: int) -> str:
        if follower_count >= 1_000_000:
            return "elite"
        if follower_count >= 100_000:
            return "established"
        return "emerging"


__all__ = ["CreatorProvisioningError", "CreatorProvisioningService"]
