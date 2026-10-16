"""Add real-player import batch tracking and row diagnostics tables.

Revision ID: 20260322_0030_real_player_import_ops
Revises: 20260322_0029_regen_universe_layer
Create Date: 2026-03-22 18:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260322_0030_real_player_import_ops"
down_revision = "20260322_0029_regen_universe_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "real_player_import_batches",
        sa.Column("batch_key", sa.String(length=64), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("provider_job_key", sa.String(length=128), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("requested_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("normalized_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matched_existing_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_player_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_player_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("authoritative_snapshot_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("summary_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_key", name="uq_rp_import_batches_key"),
        sa.UniqueConstraint("provider_name", "provider_job_key", name="uq_rp_import_batches_provider_job"),
    )
    op.create_index("ix_real_player_import_batches_provider", "real_player_import_batches", ["provider_name"], unique=False)
    op.create_index("ix_real_player_import_batches_status", "real_player_import_batches", ["status"], unique=False)
    op.create_index("ix_real_player_import_batches_requested_at", "real_player_import_batches", ["requested_at"], unique=False)
    op.create_index("ix_real_player_import_batches_requested_by", "real_player_import_batches", ["requested_by_user_id"], unique=False)

    op.create_table(
        "real_player_import_rows",
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("source_player_key", sa.String(length=128), nullable=False),
        sa.Column("canonical_name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("match_action", sa.String(length=32), nullable=True),
        sa.Column("import_action", sa.String(length=32), nullable=True),
        sa.Column("identity_confidence_score", sa.Float(), nullable=True),
        sa.Column("gtex_player_id", sa.String(length=36), nullable=True),
        sa.Column("source_link_id", sa.String(length=36), nullable=True),
        sa.Column("real_player_profile_id", sa.String(length=36), nullable=True),
        sa.Column("authoritative_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("player_import_item_id", sa.String(length=36), nullable=True),
        sa.Column("normalized_full_name", sa.String(length=192), nullable=True),
        sa.Column("normalized_display_name", sa.String(length=192), nullable=True),
        sa.Column("name_token_signature", sa.String(length=255), nullable=True),
        sa.Column("exact_identity_key", sa.String(length=255), nullable=True),
        sa.Column("name_birthyear_club_key", sa.String(length=255), nullable=True),
        sa.Column("name_birthyear_nationality_key", sa.String(length=255), nullable=True),
        sa.Column("normalized_nationality", sa.String(length=96), nullable=True),
        sa.Column("nationality_code", sa.String(length=12), nullable=True),
        sa.Column("primary_position_key", sa.String(length=64), nullable=True),
        sa.Column("secondary_position_keys_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("position_family", sa.String(length=32), nullable=True),
        sa.Column("dominant_foot", sa.String(length=16), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("club_reference_key", sa.String(length=160), nullable=True),
        sa.Column("league_reference_key", sa.String(length=160), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("normalized_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("import_metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("validation_errors_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("candidate_players_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("review_status", sa.String(length=32), nullable=False, server_default="resolved"),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("audit_findings_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["batch_id"], ["real_player_import_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_import_item_id"], ["player_import_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "row_number", name="uq_rp_import_rows_batch_row"),
        sa.UniqueConstraint("batch_id", "source_name", "source_player_key", name="uq_rp_import_rows_batch_source"),
    )
    op.create_index("ix_real_player_import_rows_batch_status", "real_player_import_rows", ["batch_id", "status"], unique=False)
    op.create_index("ix_real_player_import_rows_source_key", "real_player_import_rows", ["source_name", "source_player_key"], unique=False)
    op.create_index("ix_real_player_import_rows_player_id", "real_player_import_rows", ["gtex_player_id"], unique=False)
    op.create_index("ix_real_player_import_rows_snapshot", "real_player_import_rows", ["authoritative_snapshot_id"], unique=False)
    op.create_index("ix_real_player_import_rows_exact_identity_key", "real_player_import_rows", ["exact_identity_key"], unique=False)
    op.create_index("ix_real_player_import_rows_birthyear_club_key", "real_player_import_rows", ["name_birthyear_club_key"], unique=False)
    op.create_index("ix_real_player_import_rows_birthyear_nat_key", "real_player_import_rows", ["name_birthyear_nationality_key"], unique=False)
    op.create_index("ix_real_player_import_rows_review_status", "real_player_import_rows", ["review_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_real_player_import_rows_review_status", table_name="real_player_import_rows")
    op.drop_index("ix_real_player_import_rows_birthyear_nat_key", table_name="real_player_import_rows")
    op.drop_index("ix_real_player_import_rows_birthyear_club_key", table_name="real_player_import_rows")
    op.drop_index("ix_real_player_import_rows_exact_identity_key", table_name="real_player_import_rows")
    op.drop_index("ix_real_player_import_rows_snapshot", table_name="real_player_import_rows")
    op.drop_index("ix_real_player_import_rows_player_id", table_name="real_player_import_rows")
    op.drop_index("ix_real_player_import_rows_source_key", table_name="real_player_import_rows")
    op.drop_index("ix_real_player_import_rows_batch_status", table_name="real_player_import_rows")
    op.drop_table("real_player_import_rows")

    op.drop_index("ix_real_player_import_batches_requested_by", table_name="real_player_import_batches")
    op.drop_index("ix_real_player_import_batches_requested_at", table_name="real_player_import_batches")
    op.drop_index("ix_real_player_import_batches_status", table_name="real_player_import_batches")
    op.drop_index("ix_real_player_import_batches_provider", table_name="real_player_import_batches")
    op.drop_table("real_player_import_batches")
