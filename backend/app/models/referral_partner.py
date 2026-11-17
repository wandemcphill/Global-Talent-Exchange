from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReferralPartner(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An admin-managed referral partner who may not hold a GTEX account."""

    __tablename__ = "referral_partners"

    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    social_handle: Mapped[str | None] = mapped_column(String(120), nullable=True)
    campaign_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payout_method: Mapped[str] = mapped_column(String(32), nullable=False, default="manual", server_default="manual")
    # Store only a secure provider reference or a masked destination label, never raw bank credentials.
    payout_destination_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
