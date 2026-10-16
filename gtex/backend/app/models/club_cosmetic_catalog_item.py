from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubCosmeticCatalogItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_cosmetic_catalog_items"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_club_cosmetic_catalog_items_sku"),
    )

    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    purchase_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    asset_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, default="USD", server_default="USD")
    service_fee_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    moderation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
