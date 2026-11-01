from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.eligibility import AccountEligibilityError, AccountEligibilityService
from app.models.base import utcnow
from app.models.creator_application import (
    CREATOR_APPLICATION_ADDITIONAL_INFO,
    CREATOR_APPLICATION_APPROVED,
    CREATOR_APPLICATION_NOT_APPLIED,
    CREATOR_APPLICATION_PENDING,
    CREATOR_APPLICATION_REJECTED,
    CREATOR_APPLICATION_SUSPENDED,
    CREATOR_APPLICATION_VERIFICATION_REQUESTED,
    CreatorApplication,
)
from app.models.creator_profile import CreatorProfile
from app.models.creator_provisioning import CreatorClubProvisioning
from app.models.user import PublicAccountType, User
from app.services.creator_provisioning_service import CreatorProvisioningError, CreatorProvisioningService


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
        """GTEX uses email confirmation tokens in AuthService."""
        del actor
        raise CreatorApplicationError("email_verification_must_use_auth_confirmation")

    def verify_phone(self, *, actor: User) -> User:
        """Phone challenge flow."""
        del actor
        raise CreatorApplicationError("secure_phone_verification_unavailable")

    def submit_application(self, *, actor: User, payload) -> CreatorApplication:
        try:
            AccountEligibilityService.assert_can_apply_for_creator(actor, self.session)
        except AccountEligibilityError as exc:
            raise CreatorApplicationConflictError(str(exc)) from exc

        if actor.email_verified_at is None:
            raise CreatorApplicationError("email_verification_required")

        if self.session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == actor.id)) is not None:
            raise CreatorApplicationConflictError("creator_already_approved")

        self._ensure_handle_available(payload.requested_handle, actor.id)
        social_links = list(payload.social_links) if payload.social_links else [payload.profile_url]

        now = utcnow()
        application = self.session.scalar(select(CreatorApplication).where(CreatorApplication.user_id == actor.id))
        if application is None:
            initial_history = [
                {
                    "action": "submitted",
                    "timestamp": now.isoformat(),
                    "platform": payload.platform,
                    "follower_count": payload.follower_count,
                    "profile_url": payload.profile_url,
                }
            ]
            application = CreatorApplication(
                user_id=actor.id,
                requested_handle=payload.requested_handle,
                display_name=payload.display_name,
                platform=payload.platform,
                follower_count=payload.follower_count,
                profile_url=payload.profile_url,
                selfie_attachment_id=payload.selfie_attachment_id,
                social_links_json=social_links,
                email_verified_at=actor.email_verified_at or now,
                phone_verified_at=actor.phone_verified_at or now,
                status=CREATOR_APPLICATION_PENDING,
                decision_history_json=initial_history,
                metadata_json={},
            )
            self.session.add(application)
        else:
            if application.status == CREATOR_APPLICATION_APPROVED:
                raise CreatorApplicationConflictError("creator_application_already_approved")
            history = list(application.decision_history_json or [])
            history.append(
                {
                    "action": "resubmitted",
                    "timestamp": now.isoformat(),
                    "platform": payload.platform,
                    "follower_count": payload.follower_count,
                    "profile_url": payload.profile_url,
                }
            )
            application.requested_handle = payload.requested_handle
            application.display_name = payload.display_name
            application.platform = payload.platform
            application.follower_count = payload.follower_count
            application.profile_url = payload.profile_url
            application.selfie_attachment_id = payload.selfie_attachment_id
            application.social_links_json = social_links
            application.email_verified_at = actor.email_verified_at or application.email_verified_at or now
            application.status = CREATOR_APPLICATION_PENDING
            application.decision_history_json = history
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

    def get_my_application_payload(self, *, actor: User) -> dict[str, object] | None:
        application = self.get_my_application(actor=actor)
        if application is not None:
            return self.serialize_application(application)
        if actor.account_type == PublicAccountType.CREATOR:
            profile = self.session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == actor.id))
            if profile is not None:
                verified_at = actor.email_verified_at or profile.created_at or utcnow()
                return {
                    "application_id": profile.id,
                    "user_id": actor.id,
                    "requested_handle": profile.handle,
                    "display_name": profile.display_name,
                    "platform": "gtex",
                    "follower_count": 20000,
                    "profile_url": None,
                    "selfie_attachment_id": None,
                    "social_links": [],
                    "email_verified_at": verified_at,
                    "phone_verified_at": None,
                    "status": CREATOR_APPLICATION_APPROVED,
                    "review_notes": None,
                    "decision_reason": "active_creator_account",
                    "decision_history": [],
                    "reviewed_by_user_id": None,
                    "reviewed_at": profile.created_at or utcnow(),
                    "verification_requested_at": None,
                    "approved_at": profile.created_at or utcnow(),
                    "rejected_at": None,
                    "created_at": profile.created_at or utcnow(),
                    "updated_at": profile.updated_at or profile.created_at or utcnow(),
                    "provisioning": None,
                }
        return None

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
            "verification_requested_count": (
                self._count_by_status(CREATOR_APPLICATION_VERIFICATION_REQUESTED)
                + self._count_by_status(CREATOR_APPLICATION_ADDITIONAL_INFO)
            ),
            "suspended_count": self._count_by_status(CREATOR_APPLICATION_SUSPENDED),
            "applications": [self.serialize_application(item) for item in applications],
        }

    def approve_application(
        self,
        *,
        application_id: str,
        reviewer: User,
        review_notes: str | None = None,
        reason: str | None = None,
    ) -> CreatorApplication:
        application = self._require_application(application_id)
        applicant = self.session.get(User, application.user_id)
        if applicant is not None:
            try:
                AccountEligibilityService.assert_can_apply_for_creator(applicant, self.session)
            except AccountEligibilityError as exc:
                raise CreatorApplicationConflictError(str(exc)) from exc

        now = utcnow()
        history = list(application.decision_history_json or [])
        history.append(
            {
                "decision": "approved",
                "reviewer_id": reviewer.id,
                "reviewed_at": now.isoformat(),
                "review_notes": review_notes,
                "reason": reason,
            }
        )
        application.decision_history_json = history
        application.status = CREATOR_APPLICATION_APPROVED
        application.review_notes = review_notes
        application.decision_reason = reason
        application.reviewed_by_user_id = reviewer.id
        application.reviewed_at = now
        application.approved_at = now
        application.rejected_at = None
        application.verification_requested_at = None

        try:
            CreatorProvisioningService(self.session).provision_application(
                application=application,
                reviewer=reviewer,
            )
        except CreatorProvisioningError as exc:
            if str(exc) in {
                "club_ownership_prevents_creator_promotion",
                "creator_promotion_requires_normal_account",
                "creator_applicant_account_not_found",
            }:
                raise CreatorApplicationConflictError(str(exc)) from exc
            raise
        self.session.flush()
        return application

    def reject_application(
        self,
        *,
        application_id: str,
        reviewer: User,
        review_notes: str | None = None,
        reason: str | None = None,
    ) -> CreatorApplication:
        application = self._require_application(application_id)
        now = utcnow()
        history = list(application.decision_history_json or [])
        history.append(
            {
                "decision": "rejected",
                "reviewer_id": reviewer.id,
                "reviewed_at": now.isoformat(),
                "review_notes": review_notes,
                "reason": reason,
            }
        )
        application.decision_history_json = history
        application.status = CREATOR_APPLICATION_REJECTED
        application.review_notes = review_notes
        application.decision_reason = reason
        application.reviewed_by_user_id = reviewer.id
        application.reviewed_at = now
        application.rejected_at = now
        application.approved_at = None
        application.verification_requested_at = None
        self.session.flush()
        return application

    def request_verification(
        self,
        *,
        application_id: str,
        reviewer: User,
        review_notes: str | None = None,
        reason: str | None = None,
    ) -> CreatorApplication:
        application = self._require_application(application_id)
        now = utcnow()
        history = list(application.decision_history_json or [])
        history.append(
            {
                "decision": "additional_info_required",
                "reviewer_id": reviewer.id,
                "reviewed_at": now.isoformat(),
                "review_notes": review_notes,
                "reason": reason,
            }
        )
        application.decision_history_json = history
        application.status = CREATOR_APPLICATION_VERIFICATION_REQUESTED
        application.review_notes = review_notes
        application.decision_reason = reason
        application.reviewed_by_user_id = reviewer.id
        application.reviewed_at = now
        application.verification_requested_at = now
        application.approved_at = None
        application.rejected_at = None
        self.session.flush()
        return application

    def suspend_application(
        self,
        *,
        application_id: str,
        reviewer: User,
        review_notes: str | None = None,
        reason: str | None = None,
    ) -> CreatorApplication:
        application = self._require_application(application_id)
        now = utcnow()
        history = list(application.decision_history_json or [])
        history.append(
            {
                "decision": "suspended",
                "reviewer_id": reviewer.id,
                "reviewed_at": now.isoformat(),
                "review_notes": review_notes,
                "reason": reason,
            }
        )
        application.decision_history_json = history
        application.status = CREATOR_APPLICATION_SUSPENDED
        application.review_notes = review_notes
        application.decision_reason = reason
        application.reviewed_by_user_id = reviewer.id
        application.reviewed_at = now
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
            "profile_url": getattr(application, "profile_url", None),
            "selfie_attachment_id": getattr(application, "selfie_attachment_id", None),
            "social_links": list(application.social_links_json or []),
            "email_verified_at": application.email_verified_at,
            "phone_verified_at": application.phone_verified_at,
            "status": application.status,
            "review_notes": application.review_notes,
            "decision_reason": application.decision_reason,
            "decision_history": list(getattr(application, "decision_history_json", []) or []),
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
                        CREATOR_APPLICATION_ADDITIONAL_INFO,
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
    "CREATOR_APPLICATION_ADDITIONAL_INFO",
    "CREATOR_APPLICATION_APPROVED",
    "CREATOR_APPLICATION_NOT_APPLIED",
    "CREATOR_APPLICATION_PENDING",
    "CREATOR_APPLICATION_REJECTED",
    "CREATOR_APPLICATION_SUSPENDED",
    "CREATOR_APPLICATION_VERIFICATION_REQUESTED",
    "CreatorApplicationConflictError",
    "CreatorApplicationError",
    "CreatorApplicationNotFoundError",
    "CreatorApplicationService",
]
