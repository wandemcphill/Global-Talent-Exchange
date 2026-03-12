from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.club_sponsorship_contract import ClubSponsorshipContract


class ClubSponsorshipAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_sponsorship_assets"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    contract_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_sponsorship_contracts.id", ondelete="SET NULL"),
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
    slot_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    moderation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    moderation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_required", server_default="not_required")
    rendered_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    asset_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    contract: Mapped["ClubSponsorshipContract | None"] = relationship(back_populates="assets")


__all__ = ["ClubSponsorshipAsset"]
