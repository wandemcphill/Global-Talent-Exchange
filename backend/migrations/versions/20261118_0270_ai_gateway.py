"""Add OpenAI gateway settings, feature flags, request limits, and usage logs.

Revision ID: 20261118_0270_ai_gateway
Revises: 20261118_0269_merge_wonderkid_and_outbox

Provider secrets are not columns on these tables. GTEX authorizes admin access in
the API. Postgres RLS is not enabled: the API connects as the table owner, and
turning on RLS without a separate Supabase auth role would block that connection.
PUBLIC privileges are revoked on Postgres so the tables are not world-readable.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261118_0270_ai_gateway"
down_revision = "20261118_0269_merge_wonderkid_and_outbox"
branch_labels = None
depends_on = None

_TABLES = (
    "ai_provider_settings",
    "ai_feature_settings",
    "ai_request_limits",
    "ai_usage_logs",
)


def upgrade() -> None:
    op.create_table(
        "ai_provider_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("daily_budget_usd", sa.Numeric(12, 4), nullable=False),
        sa.Column("monthly_budget_usd", sa.Numeric(12, 4), nullable=False),
        sa.Column("max_input_tokens", sa.Integer(), nullable=False),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("user_requests_per_minute", sa.Integer(), nullable=False),
        sa.Column("global_requests_per_minute", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", name="uq_ai_provider_settings_provider"),
    )
    op.create_table(
        "ai_feature_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("model_override", sa.String(length=128), nullable=True),
        sa.Column("max_requests_per_day", sa.Integer(), nullable=False),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("cache_ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feature_key", name="uq_ai_feature_settings_feature_key"),
    )
    op.create_table(
        "ai_request_limits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subject_type", sa.String(length=16), nullable=False),
        sa.Column("subject_key", sa.String(length=64), nullable=False),
        sa.Column("max_requests", sa.Integer(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), server_default="60", nullable=False),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_type", "subject_key", name="uq_ai_request_limits_subject"),
    )
    op.create_index("ix_ai_request_limits_subject_type", "ai_request_limits", ["subject_type"])
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cache_hit", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_usage_logs_feature_key", "ai_usage_logs", ["feature_key"])
    op.create_index("ix_ai_usage_logs_user_id", "ai_usage_logs", ["user_id"])
    op.create_index("ix_ai_usage_logs_status", "ai_usage_logs", ["status"])
    op.create_index("ix_ai_usage_logs_created_at", "ai_usage_logs", ["created_at"])
    op.create_index("ix_ai_usage_logs_feature_created", "ai_usage_logs", ["feature_key", "created_at"])
    op.create_index("ix_ai_usage_logs_user_created", "ai_usage_logs", ["user_id", "created_at"])
    _lock_down_postgres()


def downgrade() -> None:
    op.drop_index("ix_ai_usage_logs_user_created", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_feature_created", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_created_at", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_status", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_user_id", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_feature_key", table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")
    op.drop_index("ix_ai_request_limits_subject_type", table_name="ai_request_limits")
    op.drop_table("ai_request_limits")
    op.drop_table("ai_feature_settings")
    op.drop_table("ai_provider_settings")


def _lock_down_postgres() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in _TABLES:
        op.execute(sa.text(f"REVOKE ALL ON TABLE {table} FROM PUBLIC"))
    op.execute(
        sa.text(
            "COMMENT ON TABLE ai_provider_settings IS "
            "'Admin AI configuration. Provider secrets are not stored in this table.'"
        )
    )
