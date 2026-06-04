"""Add frictionless auth trust tables.

Revision ID: 20260531_0092_auth_trust_tables
Revises: 20260527_0091_trader_metrics_and_payment_windows
Create Date: 2026-05-31 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260531_0092_auth_trust_tables"
down_revision = "20260527_0091_trader_metrics_and_payment_windows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("country", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("date_of_birth", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("pin_hash", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("trust_score", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("verified_status", sa.String(length=40), nullable=False, server_default="basic"))

    op.create_table(
        "recovery_questions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(length=255), nullable=False),
        sa.Column("answer_hash", sa.String(length=255), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("position IN (1, 2)", name="ck_recovery_questions_position_two_slots"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "position", name="uq_recovery_questions_user_position"),
    )
    op.create_index("ix_recovery_questions_user_id", "recovery_questions", ["user_id"])

    op.create_table(
        "trusted_devices",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=120), nullable=False),
        sa.Column("install_id", sa.String(length=120), nullable=True),
        sa.Column("os", sa.String(length=80), nullable=True),
        sa.Column("device_model", sa.String(length=160), nullable=True),
        sa.Column("ip_region", sa.String(length=120), nullable=True),
        sa.Column("trusted", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("biometric_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trusted_device_token_hash", sa.String(length=128), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "device_id", name="uq_trusted_devices_user_device"),
    )
    op.create_index("ix_trusted_devices_user_id", "trusted_devices", ["user_id"])
    op.create_index("ix_trusted_devices_device_id", "trusted_devices", ["device_id"])
    op.create_index("ix_trusted_devices_trusted", "trusted_devices", ["trusted"])
    op.create_index("ix_trusted_devices_user_last_seen_at", "trusted_devices", ["user_id", "last_seen_at"])
    op.create_index("uq_trusted_devices_token_hash", "trusted_devices", ["trusted_device_token_hash"], unique=True)

    op.create_table(
        "login_attempts",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("device_id", sa.String(length=120), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_attempts_email_created_at", "login_attempts", ["email", "created_at"])
    op.create_index("ix_login_attempts_device_id_created_at", "login_attempts", ["device_id", "created_at"])
    op.create_index("ix_login_attempts_ip_created_at", "login_attempts", ["ip_address", "created_at"])

    op.create_table(
        "security_events",
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="info"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_events_user_id_created_at", "security_events", ["user_id", "created_at"])
    op.create_index(
        "ix_security_events_user_event_created_at",
        "security_events",
        ["user_id", "event_type", "created_at"],
    )
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_severity", "security_events", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_security_events_severity", table_name="security_events")
    op.drop_index("ix_security_events_event_type", table_name="security_events")
    op.drop_index("ix_security_events_user_event_created_at", table_name="security_events")
    op.drop_index("ix_security_events_user_id_created_at", table_name="security_events")
    op.drop_table("security_events")

    op.drop_index("ix_login_attempts_ip_created_at", table_name="login_attempts")
    op.drop_index("ix_login_attempts_device_id_created_at", table_name="login_attempts")
    op.drop_index("ix_login_attempts_email_created_at", table_name="login_attempts")
    op.drop_table("login_attempts")

    op.drop_index("uq_trusted_devices_token_hash", table_name="trusted_devices")
    op.drop_index("ix_trusted_devices_user_last_seen_at", table_name="trusted_devices")
    op.drop_index("ix_trusted_devices_trusted", table_name="trusted_devices")
    op.drop_index("ix_trusted_devices_device_id", table_name="trusted_devices")
    op.drop_index("ix_trusted_devices_user_id", table_name="trusted_devices")
    op.drop_table("trusted_devices")

    op.drop_index("ix_recovery_questions_user_id", table_name="recovery_questions")
    op.drop_table("recovery_questions")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("verified_status")
        batch_op.drop_column("trust_score")
        batch_op.drop_column("pin_hash")
        batch_op.drop_column("date_of_birth")
        batch_op.drop_column("country")
