"""Add canonical mapping registry for real-player references.

Revision ID: 20260322_0030_real_player_reference_mappings
Revises: 20260322_0029_regen_universe_layer
Create Date: 2026-03-22 12:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260322_0030_real_player_reference_mappings"
down_revision = "20260322_0029_regen_universe_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "real_player_reference_mappings",
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("provider_external_id", sa.String(length=160), nullable=True),
        sa.Column("provider_reference_key", sa.String(length=180), nullable=False),
        sa.Column("provider_label", sa.String(length=180), nullable=True),
        sa.Column("normalized_label", sa.String(length=180), nullable=True),
        sa.Column("canonical_country_id", sa.String(length=36), nullable=True),
        sa.Column("canonical_competition_id", sa.String(length=36), nullable=True),
        sa.Column("canonical_club_id", sa.String(length=36), nullable=True),
        sa.Column("team_identity_kind", sa.String(length=32), nullable=True),
        sa.Column("mapping_status", sa.String(length=32), nullable=False, server_default="resolved"),
        sa.Column("resolution_method", sa.String(length=64), nullable=False, server_default="manual"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["canonical_club_id"], ["ingestion_clubs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["canonical_competition_id"], ["ingestion_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["canonical_country_id"], ["ingestion_countries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_name",
            "entity_type",
            "provider_reference_key",
            name="uq_real_player_reference_mappings_source_entity_reference",
        ),
    )
    op.create_index(
        "ix_real_player_reference_mappings_entity_type",
        "real_player_reference_mappings",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_reference_mappings_status",
        "real_player_reference_mappings",
        ["mapping_status"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_reference_mappings_provider_external_id",
        "real_player_reference_mappings",
        ["source_name", "entity_type", "provider_external_id"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_reference_mappings_country_id",
        "real_player_reference_mappings",
        ["canonical_country_id"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_reference_mappings_competition_id",
        "real_player_reference_mappings",
        ["canonical_competition_id"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_reference_mappings_club_id",
        "real_player_reference_mappings",
        ["canonical_club_id"],
        unique=False,
    )

    op.create_table(
        "real_player_unresolved_references",
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("provider_external_id", sa.String(length=160), nullable=True),
        sa.Column("provider_reference_key", sa.String(length=180), nullable=False),
        sa.Column("raw_label", sa.String(length=180), nullable=True),
        sa.Column("normalized_label", sa.String(length=180), nullable=True),
        sa.Column("team_identity_kind", sa.String(length=32), nullable=True),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canonical_country_id", sa.String(length=36), nullable=True),
        sa.Column("canonical_competition_id", sa.String(length=36), nullable=True),
        sa.Column("canonical_club_id", sa.String(length=36), nullable=True),
        sa.Column("sample_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["canonical_club_id"], ["ingestion_clubs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["canonical_competition_id"], ["ingestion_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["canonical_country_id"], ["ingestion_countries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_name",
            "entity_type",
            "provider_reference_key",
            name="uq_real_player_unresolved_references_source_entity_reference",
        ),
    )
    op.create_index(
        "ix_real_player_unresolved_references_entity_type",
        "real_player_unresolved_references",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_unresolved_references_status",
        "real_player_unresolved_references",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_unresolved_references_last_seen_at",
        "real_player_unresolved_references",
        ["last_seen_at"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_unresolved_references_reason_code",
        "real_player_unresolved_references",
        ["reason_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_real_player_unresolved_references_reason_code",
        table_name="real_player_unresolved_references",
    )
    op.drop_index(
        "ix_real_player_unresolved_references_last_seen_at",
        table_name="real_player_unresolved_references",
    )
    op.drop_index(
        "ix_real_player_unresolved_references_status",
        table_name="real_player_unresolved_references",
    )
    op.drop_index(
        "ix_real_player_unresolved_references_entity_type",
        table_name="real_player_unresolved_references",
    )
    op.drop_table("real_player_unresolved_references")

    op.drop_index(
        "ix_real_player_reference_mappings_club_id",
        table_name="real_player_reference_mappings",
    )
    op.drop_index(
        "ix_real_player_reference_mappings_competition_id",
        table_name="real_player_reference_mappings",
    )
    op.drop_index(
        "ix_real_player_reference_mappings_country_id",
        table_name="real_player_reference_mappings",
    )
    op.drop_index(
        "ix_real_player_reference_mappings_provider_external_id",
        table_name="real_player_reference_mappings",
    )
    op.drop_index(
        "ix_real_player_reference_mappings_status",
        table_name="real_player_reference_mappings",
    )
    op.drop_index(
        "ix_real_player_reference_mappings_entity_type",
        table_name="real_player_reference_mappings",
    )
    op.drop_table("real_player_reference_mappings")
