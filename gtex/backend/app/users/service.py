from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import KycStatus, User


class UserNotFoundError(LookupError):
    pass


class UserService:
    def get_by_id(self, session: Session, user_id: str) -> User:
        user = session.get(User, user_id)
        if user is None:
            raise UserNotFoundError(f"User {user_id} was not found.")
        return user

    def set_kyc_status(self, session: Session, user: User, *, kyc_status: KycStatus) -> User:
        """Reject direct KYC projection mutation.

        Verification must go through ``IdentityComplianceService`` so that a
        verified state always has provider evidence and an audit record.
        Non-verified state changes are also intentionally routed through the
        identity boundary to keep one authoritative decision path.
        """
        del session, user, kyc_status
        raise RuntimeError("Direct KYC status mutation is disabled; use IdentityComplianceService.")
