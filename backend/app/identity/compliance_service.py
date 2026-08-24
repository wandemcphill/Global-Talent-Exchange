from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.risk_ops import AuditLog
from app.models.user import KycStatus, User


class IdentityComplianceError(ValueError):
    """Raised when an identity decision cannot be safely established."""


@dataclass(frozen=True)
class VerificationEvidence:
    provider: str
    provider_subject: str
    decision: str
    verified_at: datetime
    expires_at: datetime | None = None
    checks: dict[str, Any] | None = None
    reference: str | None = None

    def validate(self) -> None:
        if self.provider.strip().lower() != "didit":
            raise IdentityComplianceError("Unsupported identity verification provider.")
        if not self.provider_subject.strip():
            raise IdentityComplianceError("Provider subject is required.")
        if self.decision.strip().lower() != "verified":
            raise IdentityComplianceError("Only an explicit verified provider decision can establish KYC.")
        now = datetime.now(timezone.utc)
        verified_at = self.verified_at
        if verified_at.tzinfo is None:
            raise IdentityComplianceError("Verification timestamp must be timezone-aware.")
        if verified_at > now:
            raise IdentityComplianceError("Verification timestamp cannot be in the future.")
        if self.expires_at is not None:
            if self.expires_at.tzinfo is None:
                raise IdentityComplianceError("Verification expiry must be timezone-aware.")
            if self.expires_at <= now:
                raise IdentityComplianceError("Verification evidence has expired.")
        if not isinstance(self.checks, dict):
            raise IdentityComplianceError("Verification checks must be a structured mapping.")


class IdentityComplianceService:
    """Single authoritative path for persisted KYC decisions.

    A boolean/status field on ``User`` is only the resulting projection. A
    verified state requires provider evidence and an immutable audit record.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def verify(self, *, user: User, evidence: VerificationEvidence, actor_user_id: str | None = None) -> User:
        evidence.validate()
        user.kyc_status = KycStatus.VERIFIED
        self.session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action_key="identity.kyc.verify",
                resource_type="user",
                resource_id=user.id,
                outcome="success",
                detail="KYC verified from provider evidence.",
                metadata_json={
                    "provider": evidence.provider.strip().lower(),
                    "provider_subject": evidence.provider_subject,
                    "decision": evidence.decision.strip().lower(),
                    "verified_at": evidence.verified_at.isoformat(),
                    "expires_at": evidence.expires_at.isoformat() if evidence.expires_at else None,
                    "reference": evidence.reference,
                    "checks": evidence.checks or {},
                },
            )
        )
        self.session.flush()
        return user

    def reject(self, *, user: User, reason: str, actor_user_id: str | None = None) -> User:
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise IdentityComplianceError("A rejection reason is required.")
        user.kyc_status = KycStatus.REJECTED
        self.session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action_key="identity.kyc.reject",
                resource_type="user",
                resource_id=user.id,
                outcome="success",
                detail=normalized_reason,
                metadata_json={"decision": "rejected"},
            )
        )
        self.session.flush()
        return user

    @staticmethod
    def is_verified(user: User) -> bool:
        return user.kyc_status is KycStatus.VERIFIED
