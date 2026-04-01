from __future__ import annotations

from sqlalchemy import ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerPersonality(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_personality_profiles"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_player_personality_profiles_player_id"),
        UniqueConstraint("regen_profile_id", name="uq_player_personality_profiles_regen_profile_id"),
        Index("ix_player_personality_profiles_target_band", "default_career_target_band"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    regen_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=True,
    )
    source_scope: Mapped[str] = mapped_column(String(24), nullable=False, default="regen", server_default="regen")
    ambition: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    loyalty: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    professionalism: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    greed: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    temperament: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    patience: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    adaptability: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    competitiveness: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    ego: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    development_focus: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    hometown_affinity: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    trophy_hunger: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    media_appetite: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")
    default_career_target_band: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="development-first",
        server_default="development-first",
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
