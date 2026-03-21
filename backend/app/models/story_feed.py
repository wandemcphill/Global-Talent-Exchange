from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class StoryFeedItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "story_feed_items"

    story_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    audience: Mapped[str] = mapped_column(String(32), nullable=False, default="public", server_default="public")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    subject_type: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    subject_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    published_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    published_by_user: Mapped["User | None"] = relationship()
