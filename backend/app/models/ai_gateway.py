from __future__ import annotations

from sqlalchemy import Boolean, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AiProviderSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Admin-editable OpenAI controls. API keys are never stored here."""

    __tablename__ = "ai_provider_settings"

    provider: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    daily_budget_usd: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=25)
    monthly_budget_usd: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=400)
    max_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=800)
    user_requests_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    global_requests_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AiFeatureSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_feature_settings"

    feature_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    model_override: Mapped[str | None] = mapped_column(String(128), nullable=True)
    max_requests_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=400)
    cache_ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AiRequestLimit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_request_limits"
    __table_args__ = (UniqueConstraint("subject_type", "subject_key", name="uq_ai_request_limits_subject"),)

    subject_type: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(64), nullable=False)
    max_requests: Mapped[int] = mapped_column(Integer, nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AiUsageLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Usage metadata only. Prompts, secrets, and personal payloads are not stored."""

    __tablename__ = "ai_usage_logs"

    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="openai")
    feature_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
