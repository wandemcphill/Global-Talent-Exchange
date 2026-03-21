from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from app.common.enums.sponsorship_status import SponsorshipStatus
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.club_sponsorship_asset import ClubSponsorshipAsset
    from app.models.club_sponsorship_package import ClubSponsorshipPackage
    from app.models.club_sponsorship_payout import ClubSponsorshipPayout


class ClubSponsorshipContract(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_sponsorship_contracts"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    package_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_sponsorship_packages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    asset_type: Mapped[SponsorshipAssetType] = mapped_column(
        Enum(
            SponsorshipAssetType,
            name="sponsorship_asset_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    sponsor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[SponsorshipStatus] = mapped_column(
        Enum(
            SponsorshipStatus,
            name="sponsorship_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    contract_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    payout_schedule: Mapped[str] = mapped_column(String(24), nullable=False, default="monthly", server_default="monthly")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    moderation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    moderation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_required", server_default="not_required")
    custom_copy: Mapped[str | None] = mapped_column(String(80), nullable=True)
    custom_logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    performance_bonus_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    settled_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    outstanding_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    package: Mapped["ClubSponsorshipPackage | None"] = relationship(back_populates="contracts")
    assets: Mapped[list["ClubSponsorshipAsset"]] = relationship(back_populates="contract")
    payouts: Mapped[list["ClubSponsorshipPayout"]] = relationship(back_populates="contract")


__all__ = ["ClubSponsorshipContract"]
