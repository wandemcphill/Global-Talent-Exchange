from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerMatchPerformance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single footballer's persisted performance in one completed competition match.

    This is the record that was previously missing. The match engine has always
    rated players (``PositionAwarePlayerRatingEngine``), but it did so entirely in
    memory: the ratings were attached to the HTTP response and discarded. Nothing
    downstream — form, valuation, the market, a portfolio — could ever see them.

    Rows are written only for *competition* matches, only for canonical
    ``ingestion_players`` ids, and only once per (player, match). Friendlies, fast
    matches, private/ad-hoc simulations and synthetic squad ids are deliberately
    excluded: they are ephemeral and must never reach valuation. See
    ``app.players.performance_recorder`` for the eligibility policy.

    ``player_id`` intentionally carries no foreign key. It is validated against
    ``ingestion_players`` before insert, which gives the same guarantee without
    letting one unrecognised id abort settlement of an otherwise valid match.
    """

    __tablename__ = "player_match_performances"
    __table_args__ = (
        UniqueConstraint("player_id", "match_id", name="uq_player_match_performances_player_match"),
        Index("ix_player_match_performances_player_occurred", "player_id", "occurred_at"),
        Index("ix_player_match_performances_eligible", "player_id", "eligible_for_valuation"),
    )

    player_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    player_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    rating: Mapped[float] = mapped_column(Float, nullable=False)
    started: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    minutes_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    saves: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    shots_on_target: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    key_passes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tackles_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    interceptions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    yellow_cards: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    red_card: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    xg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")

    #: Whether this row may contribute to the matchday valuation signal. Set once,
    #: at write time, by the recorder's eligibility policy so that the decision is
    #: auditable after the fact rather than re-derived at read time.
    eligible_for_valuation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    #: Machine-readable reason a row was ruled ineligible (``None`` when eligible).
    ineligibility_reason: Mapped[str | None] = mapped_column(String(48), nullable=True)


__all__ = ["PlayerMatchPerformance"]
