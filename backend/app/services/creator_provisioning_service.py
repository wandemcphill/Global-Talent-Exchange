from __future__ import annotations

from dataclasses import dataclass
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_infra_engine.service import ClubInfraService
from app.common.enums.creator_profile_status import CreatorProfileStatus
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.creator_application import CreatorApplication
from app.models.creator_profile import CreatorProfile
from app.models.creator_provisioning import CreatorClubProvisioning
from app.models.user import User
from app.services.creator_squad_service import CreatorSquadService


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
        creator_profile = self._ensure_creator_profile(application)
        club = self._ensure_creator_club(application)
        stadium, _, _ = ClubInfraService(self.session).ensure_defaults_for_club(club)
        creator_squad, creator_regen = CreatorSquadService(self.session).create_starter_squad(
            creator_profile=creator_profile,
            club=club,
            platform=application.platform,
            follower_count=application.follower_count,
        )

        metadata_json = {
            "approved_by_user_id": reviewer.id,
            "requested_handle": application.requested_handle,
            "platform": application.platform,
            "follower_count": application.follower_count,
            "identity_model": "creator_club",
            "asset_source": "creator_approval",
        }

        existing = self.session.scalar(
            select(CreatorClubProvisioning).where(CreatorClubProvisioning.application_id == application.id)
        )
        if existing is not None:
            existing.creator_profile_id = creator_profile.id
            existing.club_id = club.id
            existing.stadium_id = stadium.id
            existing.creator_squad_id = creator_squad.id
            existing.creator_regen_id = creator_regen.id
            existing.provision_status = "active"
            existing.metadata_json = {**(existing.metadata_json or {}), **metadata_json}
            self.session.flush()
            return existing

        provisioning = CreatorClubProvisioning(
            application_id=application.id,
            creator_profile_id=creator_profile.id,
            club_id=club.id,
            stadium_id=stadium.id,
            creator_squad_id=creator_squad.id,
            creator_regen_id=creator_regen.id,
            provision_status="active",
            metadata_json=metadata_json,
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

    def _ensure_creator_club(self, application: CreatorApplication) -> ClubProfile:
        existing = self.session.scalar(
            select(ClubProfile)
            .where(ClubProfile.owner_user_id == application.user_id)
            .order_by(ClubProfile.created_at.asc())
        )
        if existing is not None:
            return existing

        owner = self.session.get(User, application.user_id)
        base_name = application.display_name.strip()
        club_name = self._club_name(base_name)
        slug = self._unique_slug(f"{application.requested_handle}-fc")
        club = ClubProfile(
            owner_user_id=application.user_id,
            club_name=club_name,
            short_name=self._short_name(base_name),
            club_type=ClubType.COMMUNITY,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            slug=slug,
            primary_color="#112233",
            secondary_color="#F8FAFC",
            accent_color="#16A34A",
            home_venue_name=f"{base_name} Arena",
            country_code=self._country_code(owner),
            region_name=None,
            city_name=None,
            description=f"Creator-owned club provisioned for {application.display_name}.",
            visibility="public",
        )
        self.session.add(club)
        self.session.flush()
        return club

    @staticmethod
    def _resolve_tier(follower_count: int) -> str:
        if follower_count >= 1_000_000:
            return "elite"
        if follower_count >= 100_000:
            return "established"
        return "emerging"

    @staticmethod
    def _club_name(display_name: str) -> str:
        suffix = " FC"
        if display_name.lower().endswith((" fc", " football club")):
            suffix = ""
        return f"{display_name}{suffix}"[:120]

    @staticmethod
    def _short_name(display_name: str) -> str:
        words = re.findall(r"[A-Za-z0-9]+", display_name.upper())
        if not words:
            return "CRTR"
        if len(words) == 1:
            return words[0][:4]
        return "".join(word[0] for word in words)[:4]

    @staticmethod
    def _country_code(owner: User | None) -> str | None:
        if owner is None:
            return None
        candidate = (owner.country or owner.nationality or "").strip().upper()
        if 2 <= len(candidate) <= 3 and candidate.isalpha():
            return candidate
        return None

    def _unique_slug(self, value: str) -> str:
        base_slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-") or "creator-club"
        slug = base_slug[:120]
        suffix = 2
        while self.session.scalar(select(ClubProfile.id).where(ClubProfile.slug == slug)) is not None:
            suffix_text = f"-{suffix}"
            slug = f"{base_slug[: 120 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        return slug


__all__ = ["CreatorProvisioningError", "CreatorProvisioningService"]
