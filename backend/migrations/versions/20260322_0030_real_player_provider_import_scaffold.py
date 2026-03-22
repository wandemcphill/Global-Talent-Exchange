"""Add real-player provider import staging scaffold.

Revision ID: 20260322_0030_real_player_provider_import_scaffold
Revises: 20260322_0029_regen_universe_layer
Create Date: 2026-03-22 16:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260322_0030_real_player_provider_import_scaffold"
down_revision = "20260322_0029_regen_universe_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "real_player_import_staging",
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("provider_player_id", sa.String(length=128), nullable=False),
        sa.Column("provider_club_id", sa.String(length=128), nullable=True),
        sa.Column("provider_club_name", sa.String(length=160), nullable=True),
        sa.Column("provider_competition_id", sa.String(length=128), nullable=True),
        sa.Column("provider_competition_name", sa.String(length=160), nullable=True),
        sa.Column("provider_season_id", sa.String(length=128), nullable=True),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=True),
        sa.Column("last_name", sa.String(length=120), nullable=True),
        sa.Column("short_name", sa.String(length=120), nullable=True),
        sa.Column("display_position", sa.String(length=64), nullable=True),
        sa.Column("nationality_name", sa.String(length=96), nullable=True),
        sa.Column("nationality_code", sa.String(length=16), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("provider_last_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_version", sa.String(length=64), nullable=True),
        sa.Column("import_state", sa.String(length=32), nullable=False, server_default="staged"),
        sa.Column("last_import_cursor", sa.String(length=255), nullable=True),
        sa.Column("source_payload_hash", sa.String(length=64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_import_run_id", sa.String(length=36), nullable=True),
        sa.Column("latest_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["last_import_run_id"],
            ["ingestion_provider_sync_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_real_player_import_staging_provider_player_id",
        "real_player_import_staging",
        ["provider_name", "provider_player_id"],
        unique=True,
    )
    op.create_index(
        "ix_real_player_import_staging_provider_state",
        "real_player_import_staging",
        ["provider_name", "import_state"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_import_staging_last_seen_at",
        "real_player_import_staging",
        ["last_seen_at"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_import_staging_provider_club_id",
        "real_player_import_staging",
        ["provider_club_id"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_import_staging_last_import_run_id",
        "real_player_import_staging",
        ["last_import_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_real_player_import_staging_last_import_run_id", table_name="real_player_import_staging")
    op.drop_index("ix_real_player_import_staging_provider_club_id", table_name="real_player_import_staging")
    op.drop_index("ix_real_player_import_staging_last_seen_at", table_name="real_player_import_staging")
    op.drop_index("ix_real_player_import_staging_provider_state", table_name="real_player_import_staging")
    op.drop_index("ix_real_player_import_staging_provider_player_id", table_name="real_player_import_staging")
    op.drop_table("real_player_import_staging")
