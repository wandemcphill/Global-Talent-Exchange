from __future__ import annotations

import re
from dataclasses import dataclass

from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.club_infra_engine.service import ClubInfraService
from backend.app.common.enums.club_identity_visibility import ClubIdentityVisibility
from backend.app.common.enums.creator_profile_status import CreatorProfileStatus
from backend.app.models.base import generate_uuid
from backend.app.models.club_profile import ClubProfile
from backend.app.models.creator_application import CreatorApplication
from backend.app.models.creator_profile import CreatorProfile
from backend.app.models.creator_provisioning import CreatorClubProvisioning
from backend.app.models.user import User
from backend.app.models.user_region import UserRegionProfile
from backend.app.services.club_dynasty_service import ClubDynastyService
from backend.app.services.club_reputation_service import ClubReputationService
from backend.app.services.club_trophy_service import ClubTrophyService
from backend.app.services.creator_squad_service import CreatorSquadService


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
        club = self._create_creator_club(application=application, creator_profile=creator_profile)
        stadium, _facilities, _token = ClubInfraService(self.session).ensure_defaults_for_club(club)
        squad, creator_regen = CreatorSquadService(self.session).create_starter_squad(
            creator_profile=creator_profile,
            club=club,
            platform=application.platform,
            follower_count=application.follower_count,
        )
        provisioning = CreatorClubProvisioning(
            application_id=application.id,
            creator_profile_id=creator_profile.id,
            club_id=club.id,
            stadium_id=stadium.id,
            creator_squad_id=squad.id,
            creator_regen_id=creator_regen.id,
            provision_status="active",
            metadata_json={
                "approved_by_user_id": reviewer.id,
                "requested_handle": application.requested_handle,
                "platform": application.platform,
                "follower_count": application.follower_count,
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

    def _create_creator_club(
        self,
        *,
        application: CreatorApplication,
        creator_profile: CreatorProfile,
    ) -> ClubProfile:
        slug = self._unique_slug(f"creator-{application.requested_handle}")
        display_name = application.display_name.strip()
        short_name = re.sub(r"[^A-Za-z]", "", display_name.upper())[:4] or "CRTR"
        region_profile = self.session.scalar(
            select(UserRegionProfile).where(UserRegionProfile.user_id == application.user_id)
        )
        club = ClubProfile(
            owner_user_id=creator_profile.user_id,
            club_name=f"{display_name} FC",
            short_name=short_name,
            slug=slug,
            crest_asset_ref=None,
            primary_color=self._color_for_seed(f"{application.requested_handle}:primary"),
            secondary_color=self._color_for_seed(f"{application.requested_handle}:secondary"),
            accent_color=self._color_for_seed(f"{application.requested_handle}:accent"),
            home_venue_name=f"{display_name} Arena",
            country_code=region_profile.region_code if region_profile is not None else None,
            region_name=None,
            city_name=None,
            description=f"Creator club provisioned for {display_name}.",
            visibility=ClubIdentityVisibility.PUBLIC.value,
            founded_at=None,
        )
        self.session.add(club)
        self.session.flush()
        ClubReputationService(self.session).ensure_profile(club.id)
        ClubDynastyService(self.session).ensure_progress(club.id)
        ClubTrophyService(self.session).ensure_cabinet(club.id)
        self.session.flush()
        return club

    def _unique_slug(self, base_slug: str) -> str:
        candidate = re.sub(r"[^a-z0-9-]+", "-", base_slug.lower()).strip("-")
        if not candidate:
            candidate = f"creator-{generate_uuid()[:8]}"
        resolved = candidate
        suffix = 1
        while self.session.scalar(select(ClubProfile).where(ClubProfile.slug == resolved)) is not None:
            resolved = f"{candidate}-{suffix}"
            suffix += 1
        return resolved

    @staticmethod
    def _resolve_tier(follower_count: int) -> str:
        if follower_count >= 1_000_000:
            return "elite"
        if follower_count >= 100_000:
            return "established"
        return "emerging"

    @staticmethod
    def _color_for_seed(seed: str) -> str:
        digest = sha256(seed.encode("utf-8")).hexdigest()
        return f"#{digest[:6]}"


__all__ = ["CreatorProvisioningError", "CreatorProvisioningService"]
