from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.creator_application import CreatorApplication
from app.models.creator_profile import CreatorProfile
from app.models.creator_provisioning import CreatorClubProvisioning
from app.models.user import User
from app.services.creator_provisioning_service import CreatorProvisioningService

CREATOR_APPLICATION_PENDING = "pending"
CREATOR_APPLICATION_APPROVED = "approved"
CREATOR_APPLICATION_REJECTED = "rejected"
CREATOR_APPLICATION_VERIFICATION_REQUESTED = "verification_requested"


class CreatorApplicationError(ValueError):
    pass


class CreatorApplicationNotFoundError(CreatorApplicationError):
    pass


class CreatorApplicationConflictError(CreatorApplicationError):
    pass


@dataclass(slots=True)
class CreatorApplicationService:
    session: Session

    def verify_email(self, *, actor: User) -> User:
        actor.email_verified_at = actor.email_verified_at or utcnow()
        self.session.flush()
        return actor

    def verify_phone(self, *, actor: User) -> User:
        if not actor.phone_number or actor.phone_number == "0000000000":
            raise CreatorApplicationError("phone_number_required_for_creator_verification")
        actor.phone_verified_at = actor.phone_verified_at or utcnow()
        self.session.flush()
        return actor

    def submit_application(self, *, actor: User, payload) -> CreatorApplication:
        if actor.email_verified_at is None:
            raise CreatorApplicationError("email_verification_required")
        if actor.phone_verified_at is None:
            raise CreatorApplicationError("phone_verification_required")
        if self.session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == actor.id)) is not None:
            raise CreatorApplicationConflictError("creator_already_approved")

        self._ensure_handle_available(payload.requested_handle, actor.id)
        application = self.session.scalar(select(CreatorApplication).where(CreatorApplication.user_id == actor.id))
        if application is None:
            application = CreatorApplication(
                user_id=actor.id,
                requested_handle=payload.requested_handle,
                display_name=payload.display_name,
                platform=payload.platform,
                follower_count=payload.follower_count,
                social_links_json=list(payload.social_links),
                email_verified_at=actor.email_verified_at,
                phone_verified_at=actor.phone_verified_at,
                status=CREATOR_APPLICATION_PENDING,
                metadata_json={},
            )
            self.session.add(application)
        else:
            if application.status == CREATOR_APPLICATION_APPROVED:
                raise CreatorApplicationConflictError("creator_application_already_approved")
            application.requested_handle = payload.requested_handle
            application.display_name = payload.display_name
            application.platform = payload.platform
            application.follower_count = payload.follower_count
            application.social_links_json = list(payload.social_links)
            application.email_verified_at = actor.email_verified_at
            application.phone_verified_at = actor.phone_verified_at
            application.status = CREATOR_APPLICATION_PENDING
            application.review_notes = None
            application.decision_reason = None
            application.reviewed_by_user_id = None
            application.reviewed_at = None
            application.verification_requested_at = None
            application.approved_at = None
            application.rejected_at = None
        self.session.flush()
        return application

    def get_my_application(self, *, actor: User) -> CreatorApplication | None:
        return self.session.scalar(select(CreatorApplication).where(CreatorApplication.user_id == actor.id))

    def list_applications(self, *, status_filter: str | None = None) -> list[CreatorApplication]:
        stmt = select(CreatorApplication).order_by(CreatorApplication.created_at.desc())
        if status_filter:
            stmt = stmt.where(CreatorApplication.status == status_filter)
        return list(self.session.scalars(stmt).all())

    def build_dashboard(self) -> dict[str, object]:
        applications = self.list_applications()
        return {
            "pending_count": self._count_by_status(CREATOR_APPLICATION_PENDING),
            "approved_count": self._count_by_status(CREATOR_APPLICATION_APPROVED),
            "rejected_count": self._count_by_status(CREATOR_APPLICATION_REJECTED),
            "verification_requested_count": self._count_by_status(CREATOR_APPLICATION_VERIFICATION_REQUESTED),
            "applications": [self.serialize_application(item) for item in applications],
        }

    def approve_application(
        self,
        *,
        application_id: str,
        reviewer: User,
        review_notes: str | None,
        reason: str | None,
    ) -> CreatorApplication:
        application = self._require_application(application_id)
        application.status = CREATOR_APPLICATION_APPROVED
        application.review_notes = review_notes
        application.decision_reason = reason
        application.reviewed_by_user_id = reviewer.id
        application.reviewed_at = utcnow()
        application.approved_at = application.reviewed_at
        application.rejected_at = None
        application.verification_requested_at = None
        CreatorProvisioningService(self.session).provision_application(application=application, reviewer=reviewer)
        self.session.flush()
        return application

    def reject_application(
        self,
        *,
        application_id: str,
        reviewer: User,
        review_notes: str | None,
        reason: str | None,
    ) -> CreatorApplication:
        application = self._require_application(application_id)
        application.status = CREATOR_APPLICATION_REJECTED
        application.review_notes = review_notes
        application.decision_reason = reason
        application.reviewed_by_user_id = reviewer.id
        application.reviewed_at = utcnow()
        application.rejected_at = application.reviewed_at
        application.approved_at = None
        application.verification_requested_at = None
        self.session.flush()
        return application

    def request_verification(
        self,
        *,
        application_id: str,
        reviewer: User,
        review_notes: str | None,
        reason: str | None,
    ) -> CreatorApplication:
        application = self._require_application(application_id)
        application.status = CREATOR_APPLICATION_VERIFICATION_REQUESTED
        application.review_notes = review_notes
        application.decision_reason = reason
        application.reviewed_by_user_id = reviewer.id
        application.reviewed_at = utcnow()
        application.verification_requested_at = application.reviewed_at
        application.approved_at = None
        application.rejected_at = None
        self.session.flush()
        return application

    def serialize_application(self, application: CreatorApplication) -> dict[str, object]:
        provisioning = self.session.scalar(
            select(CreatorClubProvisioning).where(CreatorClubProvisioning.application_id == application.id)
        )
        provisioning_payload = None
        if provisioning is not None:
            provisioning_payload = {
                "creator_profile_id": provisioning.creator_profile_id,
                "club_id": provisioning.club_id,
                "stadium_id": provisioning.stadium_id,
                "creator_squad_id": provisioning.creator_squad_id,
                "creator_regen_id": provisioning.creator_regen_id,
                "provision_status": provisioning.provision_status,
            }
        return {
            "application_id": application.id,
            "user_id": application.user_id,
            "requested_handle": application.requested_handle,
            "display_name": application.display_name,
            "platform": application.platform,
            "follower_count": application.follower_count,
            "social_links": list(application.social_links_json or []),
            "email_verified_at": application.email_verified_at,
            "phone_verified_at": application.phone_verified_at,
            "status": application.status,
            "review_notes": application.review_notes,
            "decision_reason": application.decision_reason,
            "reviewed_by_user_id": application.reviewed_by_user_id,
            "reviewed_at": application.reviewed_at,
            "verification_requested_at": application.verification_requested_at,
            "approved_at": application.approved_at,
            "rejected_at": application.rejected_at,
            "created_at": application.created_at,
            "updated_at": application.updated_at,
            "provisioning": provisioning_payload,
        }

    def _require_application(self, application_id: str) -> CreatorApplication:
        application = self.session.get(CreatorApplication, application_id)
        if application is None:
            raise CreatorApplicationNotFoundError("creator_application_not_found")
        return application

    def _ensure_handle_available(self, requested_handle: str, user_id: str) -> None:
        existing_profile = self.session.scalar(
            select(CreatorProfile).where(
                CreatorProfile.handle == requested_handle,
                CreatorProfile.user_id != user_id,
            )
        )
        if existing_profile is not None:
            raise CreatorApplicationConflictError("creator_handle_taken")
        conflicting_application = self.session.scalar(
            select(CreatorApplication).where(
                CreatorApplication.requested_handle == requested_handle,
                CreatorApplication.user_id != user_id,
                CreatorApplication.status.in_(
                    (
                        CREATOR_APPLICATION_PENDING,
                        CREATOR_APPLICATION_VERIFICATION_REQUESTED,
                        CREATOR_APPLICATION_APPROVED,
                    )
                ),
            )
        )
        if conflicting_application is not None:
            raise CreatorApplicationConflictError("creator_handle_taken")

    def _count_by_status(self, status_value: str) -> int:
        return int(
            self.session.scalar(
                select(func.count(CreatorApplication.id)).where(CreatorApplication.status == status_value)
            )
            or 0
        )


__all__ = [
    "CREATOR_APPLICATION_APPROVED",
    "CREATOR_APPLICATION_PENDING",
    "CREATOR_APPLICATION_REJECTED",
    "CREATOR_APPLICATION_VERIFICATION_REQUESTED",
    "CreatorApplicationConflictError",
    "CreatorApplicationError",
    "CreatorApplicationNotFoundError",
    "CreatorApplicationService",
]
