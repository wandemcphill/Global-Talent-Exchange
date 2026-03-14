from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SponsorshipLead(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sponsorship_leads"
    __table_args__ = (
        UniqueConstraint("contract_id", name="uq_sponsorship_leads_contract_id"),
    )

    contract_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_sponsorship_contracts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requester_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sponsor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    sponsor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sponsor_company: Mapped[str | None] = mapped_column(String(120), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted", server_default="submitted")
    proposal_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(nullable=False, default=dict)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


__all__ = ["SponsorshipLead"]
