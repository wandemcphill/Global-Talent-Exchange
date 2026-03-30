"""Add durable competition queue and outbox backbone.

Revision ID: 20260327_0046_event_backbone
Revises: 20260327_0045_broadcast_rights_and_ownership_groups
Create Date: 2026-03-27 09:35:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0046_event_backbone"
down_revision = "20260327_0045_broadcast_rights_and_ownership_groups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("competition_queue_records"):
        op.create_table(
            "competition_queue_records",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("queue_name", sa.String(length=64), nullable=False),
            sa.Column("job_name", sa.String(length=64), nullable=False),
            sa.Column("idempotency_key", sa.String(length=255), nullable=False),
            sa.Column("aggregate_id", sa.String(length=255), nullable=True),
            sa.Column("partition_key", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'queued'")),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("queue_name", "idempotency_key", name="uq_competition_queue_records_queue_key"),
        )
        op.create_index("ix_competition_queue_records_queue_name", "competition_queue_records", ["queue_name"], unique=False)
        op.create_index("ix_competition_queue_records_aggregate_id", "competition_queue_records", ["aggregate_id"], unique=False)
        op.create_index("ix_competition_queue_records_partition_key", "competition_queue_records", ["partition_key"], unique=False)
        op.create_index("ix_competition_queue_records_status", "competition_queue_records", ["status"], unique=False)
        op.create_index("ix_competition_queue_records_published_at", "competition_queue_records", ["published_at"], unique=False)

    if not inspector.has_table("event_outbox"):
        op.create_table(
            "event_outbox",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("event_id", sa.String(length=36), nullable=False),
            sa.Column("event_type", sa.String(length=128), nullable=False),
            sa.Column("aggregate_type", sa.String(length=128), nullable=True),
            sa.Column("aggregate_id", sa.String(length=255), nullable=True),
            sa.Column("partition_key", sa.String(length=255), nullable=True),
            sa.Column("producer", sa.String(length=128), nullable=False, server_default=sa.text("'gtex'")),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("headers_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'pending'")),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("relay_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_event_outbox_event_id", "event_outbox", ["event_id"], unique=True)
        op.create_index("ix_event_outbox_event_type", "event_outbox", ["event_type"], unique=False)
        op.create_index("ix_event_outbox_aggregate_type", "event_outbox", ["aggregate_type"], unique=False)
        op.create_index("ix_event_outbox_aggregate_id", "event_outbox", ["aggregate_id"], unique=False)
        op.create_index("ix_event_outbox_partition_key", "event_outbox", ["partition_key"], unique=False)
        op.create_index("ix_event_outbox_status", "event_outbox", ["status"], unique=False)
        op.create_index("ix_event_outbox_occurred_at", "event_outbox", ["occurred_at"], unique=False)
        op.create_index("ix_event_outbox_processed_at", "event_outbox", ["processed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_event_outbox_processed_at", table_name="event_outbox")
    op.drop_index("ix_event_outbox_occurred_at", table_name="event_outbox")
    op.drop_index("ix_event_outbox_status", table_name="event_outbox")
    op.drop_index("ix_event_outbox_partition_key", table_name="event_outbox")
    op.drop_index("ix_event_outbox_aggregate_id", table_name="event_outbox")
    op.drop_index("ix_event_outbox_aggregate_type", table_name="event_outbox")
    op.drop_index("ix_event_outbox_event_type", table_name="event_outbox")
    op.drop_index("ix_event_outbox_event_id", table_name="event_outbox")
    op.drop_table("event_outbox")

    op.drop_index("ix_competition_queue_records_published_at", table_name="competition_queue_records")
    op.drop_index("ix_competition_queue_records_status", table_name="competition_queue_records")
    op.drop_index("ix_competition_queue_records_partition_key", table_name="competition_queue_records")
    op.drop_index("ix_competition_queue_records_aggregate_id", table_name="competition_queue_records")
    op.drop_index("ix_competition_queue_records_queue_name", table_name="competition_queue_records")
    op.drop_table("competition_queue_records")
