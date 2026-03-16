from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SavedSearch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "saved_searches"
    __table_args__ = (
        UniqueConstraint("user_id", "query", name="uq_saved_search_user_query"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    query: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    entity_scope: Mapped[str] = mapped_column(String(48), nullable=False, default="all")
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FeaturedRail(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "featured_rails"
    __table_args__ = (
        UniqueConstraint("rail_key", name="uq_featured_rails_key"),
    )

    rail_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    rail_type: Mapped[str] = mapped_column(String(48), nullable=False, default="story")
    audience: Mapped[str] = mapped_column(String(32), nullable=False, default="public")
    query_hint: Mapped[str | None] = mapped_column(String(180), nullable=True)
    subtitle: Mapped[str] = mapped_column(Text, nullable=False, default="")
    display_order: Mapped[int] = mapped_column(nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
