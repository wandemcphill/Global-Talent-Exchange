from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.club_sponsorship_contract import ClubSponsorshipContract


class ClubSponsorshipPackage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_sponsorship_packages"
    __table_args__ = (
        UniqueConstraint("code", name="uq_club_sponsorship_packages_code"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_type: Mapped[SponsorshipAssetType] = mapped_column(
        Enum(
            SponsorshipAssetType,
            name="sponsorship_asset_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    base_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    default_duration_months: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    payout_schedule: Mapped[str] = mapped_column(String(24), nullable=False, default="monthly", server_default="monthly")
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    contracts: Mapped[list["ClubSponsorshipContract"]] = relationship(back_populates="package")


__all__ = ["ClubSponsorshipPackage"]
