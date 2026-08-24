from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import expression

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AgentRecord(TimestampMixin, Base):
    __tablename__ = "agents"
    __table_args__ = (
        Index("ix_agents_style", "style"),
        Index("ix_agents_last_generated_at", "last_generated_at"),
    )

    agent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    handle: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    style: Mapped[str] = mapped_column(String(48), nullable=False)
    target: Mapped[str] = mapped_column(String(64), nullable=False)
    last_generated_clip_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class AgentStrategyRecord(TimestampMixin, Base):
    __tablename__ = "agent_strategies"

    agent_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agents.agent_id", ondelete="CASCADE"),
        primary_key=True,
    )
    risk_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    avg_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=12, server_default="12")
    tempo: Mapped[str] = mapped_column(String(32), nullable=False, default="medium", server_default="medium")
    audience_bias: Mapped[str] = mapped_column(String(32), nullable=False, default="general", server_default="general")
    preferred_formats_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    event_focus_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    cadence_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=8, server_default="8")
    experimental_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.3, server_default="0.3")
    global_exposure_feedback: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    shared_brain: Mapped[str] = mapped_column(String(32), nullable=False, default="copilot", server_default="copilot")


class AgentLearningStateRecord(TimestampMixin, Base):
    __tablename__ = "agent_learning_state"

    agent_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agents.agent_id", ondelete="CASCADE"),
        primary_key=True,
    )
    exploration_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.35, server_default="0.35")
    last_reward: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    average_reward: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    win_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    loss_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_posts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_rewards: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    total_penalties: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    preferred_formats_json: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentWalletRecord(TimestampMixin, Base):
    __tablename__ = "agent_wallets"

    agent_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agents.agent_id", ondelete="CASCADE"),
        primary_key=True,
    )
    # Compatibility projection only. Canonical monetary authority is the ledger.
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    lifetime_earnings: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    boost_spend: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    roi: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    last_spend: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    last_earnings: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.8, server_default="0.8")
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.65, server_default="0.65")
    repetition_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    payout_eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=expression.false(),
    )
    last_block_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AgentPerformanceLogRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "agent_performance_logs"
    __table_args__ = (
        Index("ix_agent_performance_logs_agent_id", "agent_id"),
        Index("ix_agent_performance_logs_clip_id", "clip_id"),
        Index("ix_agent_performance_logs_created_at", "created_at"),
        Index("ix_agent_performance_logs_agent_format", "agent_id", "primary_format"),
    )

    agent_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agents.agent_id", ondelete="CASCADE"),
        nullable=False,
    )
    clip_id: Mapped[str] = mapped_column(String(200), nullable=False)
    primary_format: Mapped[str] = mapped_column(String(48), nullable=False)
    variant_formats_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reward_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    payout_eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=expression.false(),
    )
    payout_block_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    watch_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    share_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    comment_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    velocity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    penalties: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    earnings: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    skip_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    orchestrator_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    global_exposure_feedback: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    winner_variant_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "AgentLearningStateRecord",
    "AgentPerformanceLogRecord",
    "AgentRecord",
    "AgentStrategyRecord",
    "AgentWalletRecord",
]
