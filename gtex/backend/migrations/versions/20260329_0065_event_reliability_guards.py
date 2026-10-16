"""Add outbox claims, consumer checkpoints, and dead-letter storage.

Revision ID: 20260329_0065_event_reliability_guards
Revises: 20260329_0064_gtex_unified_economy
Create Date: 2026-03-29 11:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0065_event_reliability_guards"
down_revision = "20260329_0064_gtex_unified_economy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("event_outbox", sa.Column("claim_token", sa.String(length=36), nullable=True))
    op.add_column("event_outbox", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("event_outbox", sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_event_outbox_claim_token", "event_outbox", ["claim_token"], unique=False)
    op.create_index("ix_event_outbox_claimed_at", "event_outbox", ["claimed_at"], unique=False)
    op.create_index("ix_event_outbox_dead_lettered_at", "event_outbox", ["dead_lettered_at"], unique=False)

    op.create_table(
        "event_consumer_states",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("consumer_name", sa.String(length=128), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("aggregate_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="processing"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claim_token", sa.String(length=36), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("headers_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("consumer_name", "event_id", name="uq_event_consumer_states_consumer_event"),
    )
    op.create_index("ix_event_consumer_states_consumer_name", "event_consumer_states", ["consumer_name"], unique=False)
    op.create_index("ix_event_consumer_states_event_id", "event_consumer_states", ["event_id"], unique=False)
    op.create_index("ix_event_consumer_states_event_type", "event_consumer_states", ["event_type"], unique=False)
    op.create_index("ix_event_consumer_states_aggregate_id", "event_consumer_states", ["aggregate_id"], unique=False)
    op.create_index("ix_event_consumer_states_status", "event_consumer_states", ["status"], unique=False)
    op.create_index("ix_event_consumer_states_claim_token", "event_consumer_states", ["claim_token"], unique=False)
    op.create_index("ix_event_consumer_states_last_attempt_at", "event_consumer_states", ["last_attempt_at"], unique=False)
    op.create_index("ix_event_consumer_states_processed_at", "event_consumer_states", ["processed_at"], unique=False)
    op.create_index("ix_event_consumer_states_dead_lettered_at", "event_consumer_states", ["dead_lettered_at"], unique=False)
    op.create_index(
        "ix_event_consumer_states_status_updated_at",
        "event_consumer_states",
        ["status", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_event_consumer_states_event_type_status",
        "event_consumer_states",
        ["event_type", "status"],
        unique=False,
    )

    op.create_table(
        "event_dead_letters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("consumer_name", sa.String(length=128), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("aggregate_id", sa.String(length=255), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("headers_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("consumer_name", "event_id", name="uq_event_dead_letters_consumer_event"),
    )
    op.create_index("ix_event_dead_letters_consumer_name", "event_dead_letters", ["consumer_name"], unique=False)
    op.create_index("ix_event_dead_letters_event_id", "event_dead_letters", ["event_id"], unique=False)
    op.create_index("ix_event_dead_letters_event_type", "event_dead_letters", ["event_type"], unique=False)
    op.create_index("ix_event_dead_letters_aggregate_id", "event_dead_letters", ["aggregate_id"], unique=False)
    op.create_index("ix_event_dead_letters_dead_lettered_at", "event_dead_letters", ["dead_lettered_at"], unique=False)
    op.create_index(
        "ix_event_dead_letters_consumer_dead_lettered_at",
        "event_dead_letters",
        ["consumer_name", "dead_lettered_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_dead_letters_consumer_dead_lettered_at", table_name="event_dead_letters")
    op.drop_index("ix_event_dead_letters_dead_lettered_at", table_name="event_dead_letters")
    op.drop_index("ix_event_dead_letters_aggregate_id", table_name="event_dead_letters")
    op.drop_index("ix_event_dead_letters_event_type", table_name="event_dead_letters")
    op.drop_index("ix_event_dead_letters_event_id", table_name="event_dead_letters")
    op.drop_index("ix_event_dead_letters_consumer_name", table_name="event_dead_letters")
    op.drop_table("event_dead_letters")

    op.drop_index("ix_event_consumer_states_event_type_status", table_name="event_consumer_states")
    op.drop_index("ix_event_consumer_states_status_updated_at", table_name="event_consumer_states")
    op.drop_index("ix_event_consumer_states_dead_lettered_at", table_name="event_consumer_states")
    op.drop_index("ix_event_consumer_states_processed_at", table_name="event_consumer_states")
    op.drop_index("ix_event_consumer_states_last_attempt_at", table_name="event_consumer_states")
    op.drop_index("ix_event_consumer_states_claim_token", table_name="event_consumer_states")
    op.drop_index("ix_event_consumer_states_status", table_name="event_consumer_states")
    op.drop_index("ix_event_consumer_states_aggregate_id", table_name="event_consumer_states")
    op.drop_index("ix_event_consumer_states_event_type", table_name="event_consumer_states")
    op.drop_index("ix_event_consumer_states_event_id", table_name="event_consumer_states")
    op.drop_index("ix_event_consumer_states_consumer_name", table_name="event_consumer_states")
    op.drop_table("event_consumer_states")

    op.drop_index("ix_event_outbox_dead_lettered_at", table_name="event_outbox")
    op.drop_index("ix_event_outbox_claimed_at", table_name="event_outbox")
    op.drop_index("ix_event_outbox_claim_token", table_name="event_outbox")
    op.drop_column("event_outbox", "dead_lettered_at")
    op.drop_column("event_outbox", "claimed_at")
    op.drop_column("event_outbox", "claim_token")
