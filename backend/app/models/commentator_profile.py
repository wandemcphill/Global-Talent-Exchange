from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CommentatorProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "commentator_profiles"
    __table_args__ = (
        UniqueConstraint("name", name="uq_commentator_profiles_name"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    style: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    tone_intensity: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    catchphrases: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    bias_rules: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    voice_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CommentaryProfileSelection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "commentary_profile_selections"
    __table_args__ = (
        UniqueConstraint("user_id", "selection_key", name="uq_commentary_profile_selections_user_key"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selection_key: Mapped[str] = mapped_column(String(80), nullable=False, default="default", server_default="default")
    match_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    primary_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("commentator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    secondary_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("commentator_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dual_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    voice_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    language: Mapped[str] = mapped_column(String(12), nullable=False, default="en", server_default="en")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CommentaryProfileSelection", "CommentatorProfile"]
