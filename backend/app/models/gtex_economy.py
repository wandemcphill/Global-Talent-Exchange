from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class GtexJackpotRoundStatus(StrEnum):
    OPEN = "open"
    TRIGGERED = "triggered"
    SETTLED = "settled"
    CANCELLED = "cancelled"


class GtexJackpotTriggerMode(StrEnum):
    THRESHOLD = "threshold"
    PROBABILITY = "probability"
    FAILSAFE = "failsafe"
    MANUAL = "manual"


class GtexJackpotDistributionMode(StrEnum):
    SINGLE_WINNER = "single_winner"
    TOP_SPLIT = "top_split"
    ACTIVITY_WEIGHTED = "activity_weighted"


class GtexContributionSourceType(StrEnum):
    FAST_MATCH = "fast_match"
    USER_HOSTED_COMPETITION = "user_hosted_competition"
    CREATOR_ROOM_ENTRY = "creator_room_entry"
    PLATFORM_ACTIVITY = "platform_activity"


class GtexAssetSubjectType(StrEnum):
    USER = "user"
    AI_CLUB = "ai_club"


class GtexTradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class GtexLeagueType(StrEnum):
    CASUAL = "casual"
    RANKED = "ranked"
    ELITE = "elite"


class GtexQueueEntryStatus(StrEnum):
    QUEUED = "queued"
    MATCHED = "matched"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class GtexMatchStatus(StrEnum):
    QUEUED = "queued"
    MATCHED = "matched"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class GtexParticipantType(StrEnum):
    HUMAN = "human"
    AI = "ai"


class GtexAiProfileType(StrEnum):
    CASUAL_BOT = "casual_bot"
    RANKED_BOT = "ranked_bot"
    ELITE_CLUB = "elite_club"


class GtexRiskFlagStatus(StrEnum):
    OPEN = "open"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"


class GtexJackpotRound(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gtex_jackpot_rounds"
    __table_args__ = (UniqueConstraint("pool_key", "round_number", name="uq_gtex_jackpot_rounds_pool_round"),)

    pool_key: Mapped[str] = mapped_column(String(64), nullable=False, default="global", index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[GtexJackpotRoundStatus] = mapped_column(
        Enum(GtexJackpotRoundStatus, name="gtex_jackpot_round_status", native_enum=False),
        nullable=False,
        default=GtexJackpotRoundStatus.OPEN,
        server_default=GtexJackpotRoundStatus.OPEN.value,
        index=True,
    )
    distribution_mode: Mapped[GtexJackpotDistributionMode] = mapped_column(
        Enum(GtexJackpotDistributionMode, name="gtex_jackpot_distribution_mode", native_enum=False),
        nullable=False,
        default=GtexJackpotDistributionMode.SINGLE_WINNER,
        server_default=GtexJackpotDistributionMode.SINGLE_WINNER.value,
    )
    threshold_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    max_probability_limit: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    probability_cap: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.5000"))
    contribution_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.1000"))
    current_balance: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    winner_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    top_split_percent: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.1000"))
    min_activity_score: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("1.0000"))
    trigger_mode: Mapped[GtexJackpotTriggerMode | None] = mapped_column(
        Enum(GtexJackpotTriggerMode, name="gtex_jackpot_trigger_mode", native_enum=False),
        nullable=True,
    )
    trigger_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    winning_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    failsafe_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    triggered_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    settled_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    contributions: Mapped[list["GtexJackpotContribution"]] = relationship(back_populates="round")
    payouts: Mapped[list["GtexJackpotPayout"]] = relationship(back_populates="round")


class GtexJackpotContribution(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "gtex_jackpot_contributions"

    round_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gtex_jackpot_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[GtexContributionSourceType] = mapped_column(
        Enum(GtexContributionSourceType, name="gtex_contribution_source_type", native_enum=False),
        nullable=False,
    )
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    entry_fee: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    contribution_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    eligibility_score: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("1.0000"))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    round: Mapped["GtexJackpotRound"] = relationship(back_populates="contributions")


class GtexJackpotPayout(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "gtex_jackpot_payouts"

    round_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gtex_jackpot_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    payout_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    payout_ratio: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("1.0000"))
    eligibility_weight: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("1.0000"))

    round: Mapped["GtexJackpotRound"] = relationship(back_populates="payouts")


class GtexCreatorAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gtex_creator_assets"

    subject_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    subject_type: Mapped[GtexAssetSubjectType] = mapped_column(
        Enum(GtexAssetSubjectType, name="gtex_asset_subject_type", native_enum=False),
        nullable=False,
    )
    subject_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subject_ai_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_ai_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    total_shares: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000")
    available_shares: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000")
    circulating_shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    demand_score: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    momentum_score: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    win_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    total_matches: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_volume: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    holdings: Mapped[list["GtexCreatorHolding"]] = relationship(back_populates="asset")
    trades: Mapped[list["GtexCreatorTrade"]] = relationship(back_populates="asset")
    price_history: Mapped[list["GtexCreatorPriceHistory"]] = relationship(back_populates="asset")


class GtexCreatorHolding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gtex_creator_holdings"
    __table_args__ = (UniqueConstraint("user_id", "player_id", name="uq_gtex_creator_holdings_user_player"),)

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gtex_creator_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shares_owned: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    reserved_shares: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    avg_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))

    asset: Mapped["GtexCreatorAsset"] = relationship(back_populates="holdings")


class GtexCreatorTrade(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "gtex_creator_trades"

    buyer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    seller_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gtex_creator_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    side: Mapped[GtexTradeSide] = mapped_column(
        Enum(GtexTradeSide, name="gtex_trade_side", native_enum=False),
        nullable=False,
    )
    shares: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    demand_impact: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    asset: Mapped["GtexCreatorAsset"] = relationship(back_populates="trades")


class GtexCreatorPriceHistory(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "gtex_creator_price_history"

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gtex_creator_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    win_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    demand_score: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    reason: Mapped[str] = mapped_column(String(128), nullable=False, default="revaluation")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    asset: Mapped["GtexCreatorAsset"] = relationship(back_populates="price_history")


class GtexLeague(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gtex_leagues"

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    league_type: Mapped[GtexLeagueType] = mapped_column(
        Enum(GtexLeagueType, name="gtex_league_type", native_enum=False),
        nullable=False,
    )
    min_elo: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_elo: Mapped[int] = mapped_column(Integer, nullable=False, default=4000, server_default="4000")
    default_entry_fee: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    ai_backfill_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    leaderboard_key: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    ai_profiles: Mapped[list["GtexAIProfile"]] = relationship(back_populates="league")


class GtexAIProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gtex_ai_profiles"

    league_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_leagues.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    profile_type: Mapped[GtexAiProfileType] = mapped_column(
        Enum(GtexAiProfileType, name="gtex_ai_profile_type", native_enum=False),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    skill_level: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    playstyle: Mapped[str] = mapped_column(String(64), nullable=False)
    adaptation_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    aggression: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    elo: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000", index=True)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    league: Mapped["GtexLeague | None"] = relationship(back_populates="ai_profiles")


class GtexMatchQueueEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gtex_match_queue_entries"

    requester_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    league_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gtex_leagues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[GtexQueueEntryStatus] = mapped_column(
        Enum(GtexQueueEntryStatus, name="gtex_queue_entry_status", native_enum=False),
        nullable=False,
        default=GtexQueueEntryStatus.QUEUED,
        server_default=GtexQueueEntryStatus.QUEUED.value,
        index=True,
    )
    entry_fee: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    expires_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    matched_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class GtexMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gtex_matches"

    league_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gtex_leagues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[GtexMatchStatus] = mapped_column(
        Enum(GtexMatchStatus, name="gtex_match_status", native_enum=False),
        nullable=False,
        default=GtexMatchStatus.QUEUED,
        server_default=GtexMatchStatus.QUEUED.value,
        index=True,
    )
    home_participant_type: Mapped[GtexParticipantType] = mapped_column(
        Enum(GtexParticipantType, name="gtex_participant_type", native_enum=False),
        nullable=False,
    )
    home_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    home_ai_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_ai_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    away_participant_type: Mapped[GtexParticipantType] = mapped_column(
        Enum(GtexParticipantType, name="gtex_participant_type", native_enum=False),
        nullable=False,
    )
    away_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    away_ai_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_ai_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entry_fee: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    effective_pot: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    jackpot_contribution: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    home_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    away_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    winner_participant_type: Mapped[GtexParticipantType | None] = mapped_column(
        Enum(GtexParticipantType, name="gtex_participant_type", native_enum=False),
        nullable=True,
    )
    winner_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    winner_ai_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_ai_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    queued_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    started_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0.0000"))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    events: Mapped[list["GtexMatchEvent"]] = relationship(back_populates="match")


class GtexMatchEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "gtex_match_events"
    __table_args__ = (UniqueConstraint("match_id", "event_index", name="uq_gtex_match_events_match_event_index"),)

    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gtex_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    match: Mapped["GtexMatch"] = relationship(back_populates="events")


class GtexLeagueStanding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gtex_league_standings"
    __table_args__ = (UniqueConstraint("league_id", "subject_key", name="uq_gtex_league_standings_league_subject"),)

    league_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gtex_leagues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    participant_type: Mapped[GtexParticipantType] = mapped_column(
        Enum(GtexParticipantType, name="gtex_participant_type", native_enum=False),
        nullable=False,
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ai_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gtex_ai_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    elo: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000")
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    win_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class GtexRiskFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gtex_risk_flags"

    category: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    subject_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    reference_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    signal_score: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0.0000"))
    status: Mapped[GtexRiskFlagStatus] = mapped_column(
        Enum(GtexRiskFlagStatus, name="gtex_risk_flag_status", native_enum=False),
        nullable=False,
        default=GtexRiskFlagStatus.OPEN,
        server_default=GtexRiskFlagStatus.OPEN.value,
    )
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "GtexAIProfile",
    "GtexAiProfileType",
    "GtexAssetSubjectType",
    "GtexContributionSourceType",
    "GtexCreatorAsset",
    "GtexCreatorHolding",
    "GtexCreatorPriceHistory",
    "GtexCreatorTrade",
    "GtexJackpotContribution",
    "GtexJackpotDistributionMode",
    "GtexJackpotPayout",
    "GtexJackpotRound",
    "GtexJackpotRoundStatus",
    "GtexJackpotTriggerMode",
    "GtexLeague",
    "GtexLeagueStanding",
    "GtexLeagueType",
    "GtexMatch",
    "GtexMatchEvent",
    "GtexMatchQueueEntry",
    "GtexMatchStatus",
    "GtexParticipantType",
    "GtexQueueEntryStatus",
    "GtexRiskFlag",
    "GtexRiskFlagStatus",
    "GtexTradeSide",
]
