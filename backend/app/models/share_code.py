from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.common.enums.share_code_type import ShareCodeType
from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ShareCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "share_codes"

    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    vanity_code: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True, index=True)
    code_type: Mapped[ShareCodeType] = mapped_column(
        Enum(
            ShareCodeType,
            name="share_code_type",
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    owner_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    owner_creator_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    linked_competition_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
