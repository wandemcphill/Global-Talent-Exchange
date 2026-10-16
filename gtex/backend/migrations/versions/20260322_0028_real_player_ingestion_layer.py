"""Add real-player ingestion identity and profile layer.

Revision ID: 20260322_0028_real_player_ingestion_layer
Revises: 20260321_0027_player_agency_authority
Create Date: 2026-03-22 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260322_0028_real_player_ingestion_layer"
down_revision = "20260321_0027_player_agency_authority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ingestion_players") as batch_op:
        batch_op.add_column(sa.Column("is_real_player", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("real_player_tier", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("canonical_display_name", sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column("identity_confidence_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("source_last_refreshed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("real_world_club_name", sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column("real_world_league_name", sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column("current_market_reference_value", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("market_reference_currency", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("normalization_profile_version", sa.String(length=32), nullable=True))
        batch_op.create_index("ix_ingestion_players_is_real_player", ["is_real_player"], unique=False)
        batch_op.create_index("ix_ingestion_players_canonical_display_name", ["canonical_display_name"], unique=False)

    op.create_table(
        "real_player_source_links",
        sa.Column("gtex_player_id", sa.String(length=36), nullable=False),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("source_player_key", sa.String(length=128), nullable=False),
        sa.Column("canonical_name", sa.String(length=160), nullable=False),
        sa.Column("known_aliases_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("nationality", sa.String(length=96), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("primary_position", sa.String(length=64), nullable=True),
        sa.Column("secondary_positions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("current_real_world_club", sa.String(length=160), nullable=True),
        sa.Column("identity_confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_verified_real_player", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("verification_state", sa.String(length=32), nullable=False, server_default="verified"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["gtex_player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_name", "source_player_key", name="uq_real_player_source_links_source_key"),
    )
    op.create_index("ix_real_player_source_links_player_id", "real_player_source_links", ["gtex_player_id"], unique=False)
    op.create_index("ix_real_player_source_links_canonical_name", "real_player_source_links", ["canonical_name"], unique=False)
    op.create_index("ix_real_player_source_links_verified_state", "real_player_source_links", ["verification_state"], unique=False)

    op.create_table(
        "real_player_profiles",
        sa.Column("gtex_player_id", sa.String(length=36), nullable=False),
        sa.Column("source_link_id", sa.String(length=36), nullable=False),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("source_player_key", sa.String(length=128), nullable=False),
        sa.Column("canonical_name", sa.String(length=160), nullable=False),
        sa.Column("known_aliases_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("nationality", sa.String(length=96), nullable=True),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("dominant_foot", sa.String(length=16), nullable=True),
        sa.Column("primary_position", sa.String(length=64), nullable=True),
        sa.Column("secondary_positions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Integer(), nullable=True),
        sa.Column("current_club_name", sa.String(length=160), nullable=True),
        sa.Column("current_league_name", sa.String(length=160), nullable=True),
        sa.Column("competition_level", sa.String(length=64), nullable=True),
        sa.Column("appearances", sa.Integer(), nullable=True),
        sa.Column("minutes_played", sa.Integer(), nullable=True),
        sa.Column("goals", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("clean_sheets", sa.Integer(), nullable=True),
        sa.Column("injury_status", sa.String(length=64), nullable=True),
        sa.Column("current_market_reference_value", sa.Float(), nullable=True),
        sa.Column("market_reference_currency", sa.String(length=8), nullable=True),
        sa.Column("source_last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("normalization_profile_version", sa.String(length=32), nullable=False, server_default="real_player_v1"),
        sa.Column("normalized_signals_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("ingestion_batch_id", sa.String(length=64), nullable=True),
        sa.Column("ingestion_source_version", sa.String(length=64), nullable=True),
        sa.Column("pricing_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["gtex_player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_link_id"], ["real_player_source_links.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_link_id", name="uq_real_player_profiles_source_link_id"),
    )
    op.create_index("ix_real_player_profiles_player_id", "real_player_profiles", ["gtex_player_id"], unique=False)
    op.create_index("ix_real_player_profiles_source_name_key", "real_player_profiles", ["source_name", "source_player_key"], unique=False)
    op.create_index("ix_real_player_profiles_refreshed_at", "real_player_profiles", ["source_last_refreshed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_real_player_profiles_refreshed_at", table_name="real_player_profiles")
    op.drop_index("ix_real_player_profiles_source_name_key", table_name="real_player_profiles")
    op.drop_index("ix_real_player_profiles_player_id", table_name="real_player_profiles")
    op.drop_table("real_player_profiles")

    op.drop_index("ix_real_player_source_links_verified_state", table_name="real_player_source_links")
    op.drop_index("ix_real_player_source_links_canonical_name", table_name="real_player_source_links")
    op.drop_index("ix_real_player_source_links_player_id", table_name="real_player_source_links")
    op.drop_table("real_player_source_links")

    with op.batch_alter_table("ingestion_players") as batch_op:
        batch_op.drop_index("ix_ingestion_players_canonical_display_name")
        batch_op.drop_index("ix_ingestion_players_is_real_player")
        batch_op.drop_column("normalization_profile_version")
        batch_op.drop_column("market_reference_currency")
        batch_op.drop_column("current_market_reference_value")
        batch_op.drop_column("real_world_league_name")
        batch_op.drop_column("real_world_club_name")
        batch_op.drop_column("source_last_refreshed_at")
        batch_op.drop_column("identity_confidence_score")
        batch_op.drop_column("canonical_display_name")
        batch_op.drop_column("real_player_tier")
        batch_op.drop_column("is_real_player")
