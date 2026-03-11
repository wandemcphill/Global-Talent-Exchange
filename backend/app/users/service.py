from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.models.user import KycStatus, User


class UserNotFoundError(LookupError):
    pass


class UserService:
    def get_by_id(self, session: Session, user_id: str) -> User:
        user = session.get(User, user_id)
        if user is None:
            raise UserNotFoundError(f"User {user_id} was not found.")
        return user

    def set_kyc_status(self, session: Session, user: User, *, kyc_status: KycStatus) -> User:
        user.kyc_status = kyc_status
        session.flush()
        return user
