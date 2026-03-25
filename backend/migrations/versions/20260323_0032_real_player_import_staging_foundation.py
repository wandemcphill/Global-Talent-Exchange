"""Add resumable staging-run foundation for bulk real-player imports.

Revision ID: 20260323_0032_real_player_import_staging_foundation
Revises: 20260322_0031_merge_real_player_heads
Create Date: 2026-03-23 19:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260323_0032_real_player_import_staging_foundation"
down_revision = "20260322_0031_merge_real_player_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "real_player_import_runs",
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("provider_sync_run_id", sa.String(length=36), nullable=True),
        sa.Column("configured_batch_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_rows_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_skipped_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unresolved_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("publish_ready_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("resume_cursor", sa.String(length=255), nullable=True),
        sa.Column("last_successful_batch_marker", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["provider_sync_run_id"],
            ["ingestion_provider_sync_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_sync_run_id", name="uq_real_player_import_runs_provider_sync_run_id"),
    )
    op.create_index(
        "ix_real_player_import_runs_provider_status",
        "real_player_import_runs",
        ["provider_name", "status"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_import_runs_source_reference",
        "real_player_import_runs",
        ["source_type", "source_reference"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_import_runs_started_at",
        "real_player_import_runs",
        ["started_at"],
        unique=False,
    )

    with op.batch_alter_table("real_player_import_staging") as batch_op:
        batch_op.add_column(sa.Column("import_run_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("import_batch_key", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("normalized_name", sa.String(length=192), nullable=True))
        batch_op.add_column(sa.Column("age", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("rough_market_value", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("rough_market_value_currency", sa.String(length=8), nullable=True))
        batch_op.add_column(
            sa.Column("processing_state", sa.String(length=32), nullable=False, server_default="pending")
        )
        batch_op.add_column(sa.Column("error_message", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("rejection_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_real_player_import_staging_import_run",
            "real_player_import_runs",
            ["import_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_real_player_import_staging_import_run_id",
            ["import_run_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_real_player_import_staging_import_batch_key",
            ["import_batch_key"],
            unique=False,
        )
        batch_op.create_index(
            "ix_real_player_import_staging_processing_state",
            ["provider_name", "processing_state"],
            unique=False,
        )
        batch_op.create_index(
            "ix_real_player_import_staging_normalized_name",
            ["normalized_name"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("real_player_import_staging") as batch_op:
        batch_op.drop_index("ix_real_player_import_staging_normalized_name")
        batch_op.drop_index("ix_real_player_import_staging_processing_state")
        batch_op.drop_index("ix_real_player_import_staging_import_batch_key")
        batch_op.drop_index("ix_real_player_import_staging_import_run_id")
        batch_op.drop_constraint(
            "fk_real_player_import_staging_import_run",
            type_="foreignkey",
        )
        batch_op.drop_column("last_processed_at")
        batch_op.drop_column("rejection_reason")
        batch_op.drop_column("error_message")
        batch_op.drop_column("processing_state")
        batch_op.drop_column("rough_market_value_currency")
        batch_op.drop_column("rough_market_value")
        batch_op.drop_column("age")
        batch_op.drop_column("normalized_name")
        batch_op.drop_column("import_batch_key")
        batch_op.drop_column("import_run_id")

    op.drop_index("ix_real_player_import_runs_started_at", table_name="real_player_import_runs")
    op.drop_index("ix_real_player_import_runs_source_reference", table_name="real_player_import_runs")
    op.drop_index("ix_real_player_import_runs_provider_status", table_name="real_player_import_runs")
    op.drop_table("real_player_import_runs")
