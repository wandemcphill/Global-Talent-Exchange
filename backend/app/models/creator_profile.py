from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import Enum, ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.common.enums.creator_profile_status import CreatorProfileStatus
from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    handle: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default="community", server_default="community")
    status: Mapped[CreatorProfileStatus] = mapped_column(
        Enum(
            CreatorProfileStatus,
            name="creator_profile_status",
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
        default=CreatorProfileStatus.ACTIVE,
    )
    default_share_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_competition_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    revenue_share_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    payout_config_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
