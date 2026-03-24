from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuthEmailTokenPurpose(StrEnum):
    SIGNUP_CONFIRMATION = "signup_confirmation"
    ACCOUNT_RECOVERY = "account_recovery"


class AuthEmailToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "auth_email_tokens"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    purpose: Mapped[AuthEmailTokenPurpose] = mapped_column(
        Enum(AuthEmailTokenPurpose, name="auth_email_token_purpose", native_enum=False),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
